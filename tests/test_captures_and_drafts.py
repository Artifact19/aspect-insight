import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from absa.actions import verify_action_draft  # noqa: E402
from absa.capture_store import CaptureStore, clean_review_text, deduplicate, review_key  # noqa: E402


def test_cleaning_and_duplicates():
    assert clean_review_text("Great battery! https://t.co/xyz  Read more") == "Great battery!"
    assert clean_review_text("Fits well &amp; looks good. Helpful") == "Fits well & looks good."
    assert review_key("Great battery!", "Alice") == review_key("great   battery!", "alice")
    assert review_key("Great battery!", "Alice") != review_key("Great battery!", "Bob")
    kept, skipped = deduplicate([{"text": "Great battery!", "author": "A"}, {"text": "Great battery!", "author": "A"},
                                 {"text": "ok", "author": "B"}, {"text": "Screen is dim.", "author": "C"}])
    assert [r["text"] for r in kept] == ["Great battery!", "Screen is dim."]
    assert skipped == 2


def test_policy_guardrails_block_refunds_and_invented_numbers():
    facts = ["Complaint topic: battery with 3 complaints out of 5 mentions."]
    policy = {"no_refund": True, "no_discount": True, "no_replacement": True}
    bad = verify_action_draft("Sorry about the battery! Here is a 20% discount and full refund.", facts, policy, ["battery"])
    assert bad["passed"] is False
    assert any("Unverified numbers" in v for v in bad["violations"])
    assert any("refunds" in v.lower() for v in bad["violations"])
    assert any("discounts" in v.lower() for v in bad["violations"])

    good = verify_action_draft("Sorry about the battery issue mentioned in your review; our team is inspecting this.", facts, policy, ["battery"])
    assert good["passed"] is True


class DummyWriter:
    name = "dummy-qwen"

    def write(self, facts, task, sample=False):
        if "customer support reply" in task.lower():
            return "Thank you for flagging the battery life issue; our engineering team is investigating.", 12.0
        return "Customers reported 2 negative mentions about battery life in this capture.", 10.0


class DummyAnalyzer:
    device = "cpu"
    domain_categories = {"Laptop": {"battery - operation performance", "display - general"}}

    class classifier:
        temperature = 1.83

    def available(self):
        return [{"key": "t5_domain", "label": "Flan-T5-base + domain", "note": "", "with_domain": True,
                 "available": True, "loaded": True}]

    def writer(self):
        return DummyWriter()

    def analyze(self, texts, domain, model="t5_domain", decoding="greedy", temperature=0.7, top_p=0.9,
                check_domain=True, constrained=False):
        sentences = []
        for idx, text in enumerate(texts):
            sentences.append({
                "review": idx,
                "text": text,
                "model_input": text.lower(),
                "raw_output": "[A] battery life [C] battery - operation performance [O] short [S] negative",
                "quads": [{
                    "aspect": "battery life",
                    "category": "BATTERY#OPERATION_PERFORMANCE",
                    "category_text": "battery - operation performance",
                    "opinion": "short",
                    "sentiment": "negative",
                    "aspect_span": [0, 7],
                    "opinion_span": None,
                    "probabilities": {"positive": 0.1, "negative": 0.6, "neutral": 0.3},
                    "confidence": 0.6,
                    "classifier_sentiment": "positive" if idx == 0 else "negative",
                    "agrees": idx != 0,
                }],
                "discarded": [],
                "malformed": 0,
            })
        return {
            "domain": domain,
            "model": "Flan-T5-base + domain",
            "model_key": model,
            "decoding": decoding,
            "constrained": constrained,
            "sentences": sentences,
            "summary": {
                "opinions": len(texts),
                "sentences": len(texts),
                "reviews": len(texts),
                "sentiment": {"positive": 0, "negative": len(texts), "neutral": 0},
                "share": {"positive": 0.0, "negative": 1.0, "neutral": 0.0},
                "categories": [{"name": "battery - operation performance", "positive": 0, "negative": len(texts),
                                "neutral": 0, "total": len(texts), "examples": {"negative": [texts[0]]},
                                "top_aspects": {"negative": ["battery life"]}}],
                "aspects": [],
                "entities": [{"name": "battery", "positive": 0, "negative": len(texts), "neutral": 0,
                              "total": len(texts), "subtopics": ["operation performance"],
                              "top_aspects": {"negative": ["battery life"]},
                              "examples": {"negative": [texts[0]]}}],
                "top_opinions": {"positive": [], "negative": [{"word": "short", "count": len(texts)}], "neutral": []},
            },
            "timing": {"total_ms": 15.0, "generation_ms_per_sentence": 7.5, "classifier_ms": 2.0, "sentences": len(texts)},
            "device": "cpu",
            "classifier_temperature": 1.83,
        }


def test_capture_brief_ask_and_draft_api(tmp_path):
    import backend.app as app_mod

    app_mod.state["store"] = CaptureStore(tmp_path / "captures.db")
    app_mod.state["analyzer"] = DummyAnalyzer()
    client = TestClient(app_mod.app)

    resp = client.post("/api/captures", json={
        "title": "Test Laptop Page", "source_url": "https://example.com/laptop", "source": "amazon",
        "domain": "Laptop",
        "reviews": [
            {"text": "Battery life is too short for travel.", "author": "Bob", "dom_id": "ai-rev-1"},
            {"text": "Battery life is too short for travel.", "author": "Bob", "dom_id": "ai-rev-2"},
            {"text": "Battery life drains quickly under load.", "author": "Sue", "dom_id": "ai-rev-3"},
        ],
    })
    assert resp.status_code == 200
    cap = resp.json()
    assert cap["review_count"] == 2 and cap["skipped"] == 1
    assert len(cap["page_marks"]) == 2
    cid = cap["id"]
    assert client.get("/api/captures").json()[0]["id"] == cid

    rag = client.post(f"/api/captures/{cid}/ask", json={"question": "How is the battery life?"}).json()
    assert rag["verified"] is True
    assert "battery" in rag["matched_topics"]

    draft = client.post("/api/drafts", json={"capture_id": cid, "kind": "reply", "review_index": 0}).json()
    assert draft["checks"]["passed"] is True and draft["status"] == "pending"
    decided = client.post(f"/api/drafts/{draft['id']}/decide", json={"status": "approved"}).json()
    assert decided["status"] == "approved"
    assert client.get(f"/api/drafts?capture_id={cid}").json()[0]["status"] == "approved"

    assert client.delete(f"/api/captures/{cid}").status_code == 200
    assert client.get(f"/api/captures/{cid}").status_code == 404
