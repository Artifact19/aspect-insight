"""Reply and ticket drafts checked against business rules, and grounded question answering over captured reviews.

Both reuse the Qwen2.5-1.5B-Instruct summary writer that the Analyzer already loads; nothing is retrained.
"""
from __future__ import annotations

import re
from typing import Sequence

import numpy as np

from .inference import check_numbers
from .retrieval import TfidfIndex

POLICY_RULES = {
    "no_refund": (
        "No unauthorized refunds",
        re.compile(r"\b(refunds?|money\s+back|reimburs\w*|chargeback)\b", re.IGNORECASE),
    ),
    "no_discount": (
        "No unauthorized discounts or vouchers",
        re.compile(r"\b(discounts?|coupons?|vouchers?|promo\s*codes?|freebies?|complimentary|\d+\s*%\s*off)\b", re.IGNORECASE),
    ),
    "no_replacement": (
        "No unauthorized free replacements",
        re.compile(r"\b(free\s+replacement|replace\s+(?:it|your\s+\w+)\s+for\s+free|send\s+(?:a\s+)?new\s+one)\b", re.IGNORECASE),
    ),
}

REPLY_TASK = (
    "Write a polite, concise customer support reply (2 to 3 sentences, under 70 words). "
    "Address ONLY the exact aspects mentioned in the facts. "
    "{policy_notes} Never invent numbers, dates, order IDs, or promises not in the facts."
)

TICKET_TASK = (
    "Write a crisp engineering/operations action ticket in 3 short sentences (under 75 words): "
    "what is failing, the exact complaint count and quoted issue from the facts, and one concrete investigation step. "
    "{policy_notes} Keep every number exact and never invent extra statistics."
)

RAG_TASK = (
    "Answer the customer's question in 2 to 4 plain sentences (under 85 words) using ONLY the facts and quotes above. "
    "Keep every count and percentage exact as written, cite which topic/aspect the evidence comes from, and if the "
    "facts do not cover part of the question, state that honestly."
)


def _policy_notes(policy: dict) -> str:
    notes = []
    if policy.get("no_refund", True):
        notes.append("Do NOT offer or mention refunds or money back.")
    if policy.get("no_discount", True):
        notes.append("Do NOT offer discounts, coupons, vouchers, or freebies.")
    if policy.get("no_replacement", True):
        notes.append("Do NOT promise a free replacement.")
    return " ".join(notes)


def verify_action_draft(draft: str, facts: Sequence[str], policy: dict,
                        allowed_aspects: Sequence[str]) -> dict:
    """Deterministic guardrail verification: numbers, policy prohibitions, and aspect grounding."""
    checks: list[dict] = []
    violations: list[str] = []

    bad_nums = check_numbers(draft, facts)
    nums_ok = len(bad_nums) == 0
    checks.append({
        "rule": "No invented numbers",
        "passed": nums_ok,
        "detail": "All numbers match computed facts" if nums_ok else f"Unverified: {', '.join(bad_nums)}",
    })
    if not nums_ok:
        violations.append(f"Unverified numbers: {', '.join(bad_nums)}")

    for key, (label, pattern) in POLICY_RULES.items():
        if not policy.get(key, True):
            continue
        m = pattern.search(draft or "")
        ok = m is None
        checks.append({
            "rule": label,
            "passed": ok,
            "detail": "Compliant" if ok else f"Blocked phrase: '{m.group(0)}'",
        })
        if not ok:
            violations.append(f"{label} violated ('{m.group(0)}')")

    aspects_clean = [a.strip().lower() for a in allowed_aspects if a and len(a.strip()) > 2]
    if aspects_clean:
        low = (draft or "").lower()
        grounded = any(
            any(tok in low for tok in re.findall(r"[a-z0-9]+", a) if len(tok) > 2)
            for a in aspects_clean
        )
        checks.append({
            "rule": "Grounded to extracted aspects",
            "passed": grounded,
            "detail": "Mentions extracted aspect/topic" if grounded else "Does not reference extracted aspect",
        })
        if not grounded:
            violations.append("Draft does not reference any extracted aspect")

    return {"passed": len(violations) == 0, "violations": violations, "checks": checks}


def draft_owner_reply(writer, *, review_text: str, quads: Sequence[dict], domain: str,
                      business_name: str, policy: dict) -> dict:
    neg = [q for q in quads if q.get("sentiment") == "negative"]
    pos = [q for q in quads if q.get("sentiment") == "positive"]
    target_quads = neg or list(quads)
    aspects = [q.get("aspect") or q.get("category_text", "").split(" - ")[0] for q in target_quads]
    facts = [
        f"Business/Product: {business_name} ({domain}).",
        f"Customer review: \"{review_text[:320]}\"",
        "Negative aspects extracted: " + (
            "; ".join(f"{q.get('aspect') or q.get('category_text')} (opinion: {q.get('opinion') or 'implied'})"
                      for q in neg[:4]) if neg else "none"
        ),
        "Positive aspects extracted: " + (
            "; ".join(f"{q.get('aspect') or q.get('category_text')} (opinion: {q.get('opinion') or 'implied'})"
                      for q in pos[:3]) if pos else "none"
        ),
    ]
    task = REPLY_TASK.format(policy_notes=_policy_notes(policy))
    return _generate_with_guardrail(writer, facts, task, policy, aspects)


def draft_issue_ticket(writer, *, entity_row: dict, domain: str, product_name: str, policy: dict) -> dict:
    name = entity_row["name"]
    subtopics = ", ".join(entity_row.get("subtopics", [])[:3])
    aspects = entity_row.get("top_aspects", {}).get("negative", [])[:4]
    quote = (entity_row.get("examples", {}).get("negative") or [""])[0]
    facts = [
        f"Product/Business: {product_name} ({domain}).",
        f"Complaint topic: {name} with {entity_row['negative']} complaints out of {entity_row['total']} mentions.",
        f"Specific aspects reported: {', '.join(aspects) if aspects else name}.",
    ]
    if subtopics:
        facts.append(f"Sub-categories affected: {subtopics}.")
    if quote:
        facts.append(f"Top verified customer quote: \"{quote[:260]}\"")
    task = TICKET_TASK.format(policy_notes=_policy_notes(policy))
    return _generate_with_guardrail(writer, facts, task, policy, [name, *aspects])


def _generate_with_guardrail(writer, facts: Sequence[str], task: str, policy: dict,
                             allowed_aspects: Sequence[str]) -> dict:
    best = None
    total_ms = 0.0
    for attempt in range(3):
        draft, ms = writer.write(facts, task, sample=attempt > 0)
        total_ms += ms
        guardrail = verify_action_draft(draft, facts, policy, allowed_aspects)
        if best is None or len(guardrail["violations"]) < len(best[1]["violations"]):
            best = (draft, guardrail)
        if guardrail["passed"]:
            break
    assert best is not None
    return {
        "draft": best[0],
        "facts": list(facts),
        "guardrail": best[1],
        "model": getattr(writer, "name", "Qwen/Qwen2.5-1.5B-Instruct"),
        "ms": round(total_ms),
    }


def retrieve_aspect_context(question: str, capture: dict, top_k_entities: int = 3,
                            top_k_quotes: int = 4) -> tuple[list[str], list[dict], list[str]]:
    """Retrieve matching extracted entities and verified quotes for a user question."""
    summary = capture.get("summary") or {}
    entities = summary.get("entities") or []
    sentences = capture.get("sentences") or []
    q_low = (question or "").lower()
    q_tokens = set(re.findall(r"[a-z0-9]+", q_low))

    # Score entities by direct mention + subtopics + top aspects overlap
    scored_entities = []
    for e in entities:
        blob = " ".join([
            e.get("name", ""),
            " ".join(e.get("subtopics", [])),
            " ".join(e.get("top_aspects", {}).get("positive", [])),
            " ".join(e.get("top_aspects", {}).get("negative", [])),
            " ".join(e.get("top_aspects", {}).get("neutral", [])),
        ]).lower()
        e_tokens = set(re.findall(r"[a-z0-9]+", blob))
        overlap = len(q_tokens & e_tokens)
        if e.get("name", "").lower() in q_low:
            overlap += 3
        scored_entities.append((overlap, e.get("total", 0), e))

    scored_entities.sort(key=lambda x: (x[0], x[1]), reverse=True)
    matched = [e for ov, _, e in scored_entities if ov > 0][:top_k_entities]
    if not matched:
        matched = [e for _, _, e in scored_entities[:top_k_entities]]

    # TF-IDF retrieve most relevant sentences that contain extracted quadruples
    sent_entries = [s for s in sentences if s.get("quads")]
    citations: list[dict] = []
    if sent_entries:
        corpus = [
            s["text"] + " " + " ".join(
                f"{q.get('aspect') or ''} {q.get('category_text', '')} {q.get('opinion') or ''}"
                for q in s["quads"]
            )
            for s in sent_entries
        ]
        idx = TfidfIndex(corpus)
        # Search returns indices sorted by similarity
        top_idx = idx.search([question], min(top_k_quotes * 2, len(corpus)))[0]
        seen_texts: set[str] = set()
        for i in top_idx:
            s = sent_entries[int(i)]
            if s["text"] in seen_texts:
                continue
            seen_texts.add(s["text"])
            best_q = max(s["quads"], key=lambda q: q.get("confidence", 0.0))
            citations.append({
                "review": s.get("review", 0) + 1,
                "text": s["text"],
                "aspect": best_q.get("aspect") or "(implied)",
                "category": best_q.get("category_text", ""),
                "sentiment": best_q.get("sentiment", "neutral"),
                "confidence": best_q.get("confidence", 0.0),
            })
            if len(citations) >= top_k_quotes:
                break

    sent_counts = summary.get("sentiment", {})
    facts = [
        f"Subject: {capture.get('title', 'Product')} ({capture.get('domain', '')}) — "
        f"{summary.get('reviews', 0)} reviews, {summary.get('opinions', 0)} extracted opinions "
        f"({sent_counts.get('positive', 0)} positive, {sent_counts.get('negative', 0)} negative, "
        f"{sent_counts.get('neutral', 0)} neutral).",
    ]
    for e in matched:
        pos_asp = ", ".join(e.get("top_aspects", {}).get("positive", [])[:2])
        neg_asp = ", ".join(e.get("top_aspects", {}).get("negative", [])[:2])
        line = (f"Topic {e['name']}: {e['total']} mentions ({e['positive']} positive, "
                f"{e['negative']} negative, {e['neutral']} neutral)")
        if neg_asp:
            line += f"; complaints mention {neg_asp}"
        if pos_asp:
            line += f"; praise mentions {pos_asp}"
        facts.append(line + ".")
    for c in citations[:3]:
        facts.append(f"Quote [{c['sentiment']} on {c['aspect']}]: \"{c['text'][:220]}\"")

    return facts, citations, [e["name"] for e in matched]


def answer_review_question(writer, *, question: str, capture: dict) -> dict:
    facts, citations, matched_topics = retrieve_aspect_context(question, capture)
    best = None
    total_ms = 0.0
    prompt_facts = facts + [f"User question: {question}"]
    for attempt in range(3):
        text, ms = writer.write(prompt_facts, RAG_TASK, sample=attempt > 0)
        total_ms += ms
        bad = check_numbers(text, facts)
        if best is None or len(bad) < len(best[1]):
            best = (text, bad)
        if not bad:
            break
    assert best is not None
    return {
        "question": question,
        "answer": best[0],
        "facts": facts,
        "citations": citations,
        "matched_topics": matched_topics,
        "unsupported_numbers": best[1],
        "verified": len(best[1]) == 0,
        "model": getattr(writer, "name", "Qwen/Qwen2.5-1.5B-Instruct"),
        "ms": round(total_ms),
    }
