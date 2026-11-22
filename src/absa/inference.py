"""Inference for the web application: quadruple generators, the calibrated sentiment classifier and aggregation."""
from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np
import torch
from transformers import AutoModelForSeq2SeqLM, AutoModelForSequenceClassification, AutoTokenizer

from .constants import DOMAINS, ID2LABEL, NULL, OUTPUT_DIR, PROCESSED_DIR, SENTIMENT_WORDS
from .data import CategoryVocab, category_to_text, load_pairs, load_sentences, mark_aspect, parse, quads_of, target_text
from .metrics import apply_temperature, fit_temperature
from .utils import free_memory, get_device, load_json, sync

TOKEN = re.compile(r"\w+|[^\w\s]")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])|\n+")
MAX_SENTENCES = 400
PRIMARY = "t5_domain"
MAX_CHARS = 600

DECODING = {
    "greedy": {"num_beams": 1, "do_sample": False},
    "beam": {"num_beams": 4, "do_sample": False},
    "sampling": {"do_sample": True},
}


@dataclass
class GeneratorSpec:
    key: str
    label: str
    kind: str
    path: Path
    base: str
    with_domain: bool
    note: str = ""


def default_specs(runs: Path = OUTPUT_DIR / "runs") -> list[GeneratorSpec]:
    return [
        GeneratorSpec("t5_domain", "Flan-T5-base + domain", "seq2seq",
                      runs / "t5/all_domains_tagged/model/seed42/model", "google/flan-t5-base", True,
                      "Deployed model: full fine-tuning, domain named in the input"),
        GeneratorSpec("t5_plain", "Flan-T5-base, no domain", "seq2seq",
                      runs / "t5/all_domains/model/seed42/model", "google/flan-t5-base", False,
                      "Same model trained without the domain in the input"),
        GeneratorSpec("qwen_domain", "Qwen2.5-1.5B LoRA + domain", "causal",
                      runs / "qwen/all_domains_tagged/model/seed42/model", "Qwen/Qwen2.5-1.5B-Instruct", True,
                      "Decoder-only LLM with a LoRA adapter"),
    ]


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in SENTENCE_END.split(text or "") if p and p.strip()]
    return [p[:MAX_CHARS] for p in parts][:MAX_SENTENCES]


def to_model_text(sentence: str, lowercase: bool) -> str:
    """Tokenise like the training data: punctuation separated by spaces; lower case where the domain is."""
    text = " ".join(TOKEN.findall(sentence))
    return text.lower() if lowercase else text


def find_span(sentence: str, phrase: str) -> list[int] | None:
    """Character span of a phrase in the user's sentence, tolerant to the spacing changes of tokenisation."""
    if not phrase or phrase == NULL:
        return None
    tokens = TOKEN.findall(phrase)
    if not tokens:
        return None
    pattern = r"\s*".join(re.escape(t) for t in tokens)
    m = re.search(r"(?<!\w)" + pattern + r"(?!\w)", sentence, flags=re.IGNORECASE)
    return [m.start(), m.end()] if m else None


class Generator:
    """A loaded quadruple generator (Flan-T5 or Qwen with a LoRA adapter)."""

    def __init__(self, spec: GeneratorSpec, device: torch.device):
        self.spec, self.device = spec, device
        self.dtype = torch.bfloat16 if device.type == "cuda" and torch.cuda.is_bf16_supported() else None
        if spec.kind == "seq2seq":
            self.tokenizer = AutoTokenizer.from_pretrained(spec.base)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(spec.path, tie_word_embeddings=False).float()
            if self.dtype is not None:
                self.model = self.model.to(self.dtype)
        else:
            from peft import PeftModel
            from transformers import AutoModelForCausalLM
            self.tokenizer = AutoTokenizer.from_pretrained(spec.base)
            self.tokenizer.pad_token = self.tokenizer.pad_token or self.tokenizer.eos_token
            base = AutoModelForCausalLM.from_pretrained(spec.base, dtype=self.dtype or torch.float32)
            self.model = PeftModel.from_pretrained(base, str(spec.path)).merge_and_unload()
        self.model.to(device).eval()

    def prompts(self, sentences: Sequence[str], domain: str) -> list[str]:
        if self.spec.kind == "seq2seq":
            from .models.generator import source_text
            return [source_text(s, with_domain=self.spec.with_domain, domain=domain) for s in sentences]
        from .models.llm import chat_prompt
        return [chat_prompt(self.tokenizer, s, domain=domain if self.spec.with_domain else None) for s in sentences]

    @torch.no_grad()
    def generate(self, sentences: Sequence[str], domain: str, decoding: str = "greedy", temperature: float = 0.7,
                 top_p: float = 0.9, batch_size: int | None = None) -> tuple[list[str], float]:
        kwargs = dict(DECODING.get(decoding, DECODING["greedy"]))
        if kwargs.get("do_sample"):
            kwargs.update(temperature=max(0.05, float(temperature)), top_p=float(top_p))
        prompts = self.prompts(sentences, domain)
        batch_size = batch_size or (64 if self.spec.kind == "seq2seq" else 16)
        if self.spec.kind == "seq2seq":
            from .models.generator import generate
            return generate(self.model, self.tokenizer, prompts, max_new_tokens=160, batch_size=batch_size, **kwargs)
        from .models.llm import clean_output, generate
        with torch.autocast(device_type=self.device.type, dtype=self.dtype or torch.float32,
                            enabled=self.dtype is not None):
            outputs, ms = generate(self.model, self.tokenizer, prompts, max_new_tokens=160, batch_size=batch_size,
                                   **kwargs)
        return [clean_output(o) for o in outputs], ms


class Classifier:
    """DeBERTa-v3-small aspect-sentiment classifier with temperature scaling fitted on the Dev set."""

    def __init__(self, path: Path, device: torch.device, base: str = "microsoft/deberta-v3-small"):
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(base, use_fast=False)
        self.model = AutoModelForSequenceClassification.from_pretrained(path).float().to(device).eval()
        self.temperature = 1.0
        dev_probs = path.parent / "dev_probs.npy"
        if dev_probs.exists():
            labels = np.array([r["label"] for r in load_pairs(list(DOMAINS), "Dev")])
            probs = np.load(dev_probs)
            if len(probs) == len(labels):
                self.temperature = fit_temperature(probs, labels)

    @torch.no_grad()
    def predict(self, rows: Sequence[dict], batch_size: int = 32) -> np.ndarray:
        if not rows:
            return np.zeros((0, 3))
        out = []
        for i in range(0, len(rows), batch_size):
            chunk = rows[i:i + batch_size]
            enc = self.tokenizer([r["target"] for r in chunk], [r["marked_sentence"] for r in chunk], truncation=True,
                                 max_length=128, padding=True, return_tensors="pt").to(self.device)
            logits = self.model(**{k: v for k, v in enc.items() if k in ("input_ids", "attention_mask",
                                                                         "token_type_ids")}).logits
            out.append(torch.softmax(logits.float(), -1).cpu().numpy())
        return apply_temperature(np.concatenate(out), self.temperature)


@dataclass
class Analyzer:
    runs: Path = OUTPUT_DIR / "runs"
    device: torch.device = field(default_factory=get_device)

    def __post_init__(self):
        self.vocab = CategoryVocab.load(PROCESSED_DIR / "categories.json")
        self.specs = {s.key: s for s in default_specs(self.runs)}
        self.small_gpu = self.device.type == "cuda" and torch.cuda.get_device_properties(0).total_memory < 10e9
        self.generators: dict[str, Generator] = {}
        train = {d: load_sentences([d], "Train") for d in DOMAINS}
        self.domain_categories = {d: {category_to_text(q.category) for s in rows for q in quads_of(s)}
                                  for d, rows in train.items()}
        self.lowercase = {d: np.mean([s["text"] == s["text"].lower() for s in rows]) > 0.5 for d, rows in train.items()}
        self.classifier = Classifier(self.runs / "classifiers/class_weights/seed42/model", torch.device("cpu"))
        self.get(PRIMARY)

    # ------------------------------------------------------------------ models
    def available(self) -> list[dict]:
        return [{"key": s.key, "label": s.label, "note": s.note, "with_domain": s.with_domain,
                 "available": s.path.exists(), "loaded": s.key in self.generators} for s in self.specs.values()]

    def get(self, key: str) -> Generator:
        if key not in self.generators:
            spec = self.specs[key]
            if not spec.path.exists():
                raise FileNotFoundError(f"model files not found: {spec.path}")
            if self.small_gpu:
                for other in [k for k in self.generators if k != PRIMARY]:
                    del self.generators[other]
                free_memory()
            self.generators[key] = Generator(spec, self.device)
        return self.generators[key]

    # ------------------------------------------------------------------ analysis
    def _quads(self, sentence: str, model_text: str, raw: str, domain: str, check_domain: bool):
        quads, malformed = parse(raw, self.vocab)
        kept, discarded = [], []
        for q in quads:
            item = {"aspect": None if q.implicit_aspect else q.aspect, "category": q.category,
                    "category_text": category_to_text(q.category),
                    "opinion": None if q.implicit_opinion else q.opinion,
                    "sentiment": SENTIMENT_WORDS[q.sentiment],
                    "aspect_span": find_span(sentence, q.aspect if not q.implicit_aspect else ""),
                    "opinion_span": find_span(sentence, q.opinion if not q.implicit_opinion else ""),
                    "target": target_text(q.aspect, q.category),
                    "marked_sentence": mark_aspect(model_text, q.aspect)}
            if check_domain and item["category_text"] not in self.domain_categories[domain]:
                discarded.append({**item, "reason": "category belongs to another domain"})
            else:
                kept.append(item)
        return kept, discarded, malformed

    def _score(self, items: list[dict]) -> float:
        sync()
        t0 = time.perf_counter()
        probs = self.classifier.predict(items)
        sync()
        for item, p in zip(items, probs):
            item["probabilities"] = {SENTIMENT_WORDS[ID2LABEL[k]]: round(float(p[k]), 4) for k in range(3)}
            item["confidence"] = item["probabilities"][item["sentiment"]]
            item["classifier_sentiment"] = SENTIMENT_WORDS[ID2LABEL[int(p.argmax())]]
            item["agrees"] = item["classifier_sentiment"] == item["sentiment"]
            item.pop("target", None)
            item.pop("marked_sentence", None)
        return (time.perf_counter() - t0) * 1000

    def analyze(self, texts: Sequence[str], domain: str, model: str = "t5_domain", decoding: str = "greedy",
                temperature: float = 0.7, top_p: float = 0.9, check_domain: bool = True) -> dict:
        if domain not in DOMAINS:
            raise ValueError(f"unknown domain {domain}")
        t_start = time.perf_counter()
        units = [(r, s) for r, text in enumerate(texts) for s in split_sentences(text)][:MAX_SENTENCES]
        sentences = [s for _, s in units]
        model_texts = [to_model_text(s, self.lowercase[domain]) for s in sentences]
        gen = self.get(model)
        raw, gen_ms = gen.generate(model_texts, domain, decoding, temperature, top_p) if sentences else ([], 0.0)
        out, all_items = [], []
        for (review, sentence), model_text, text in zip(units, model_texts, raw):
            kept, discarded, malformed = self._quads(sentence, model_text, text, domain, check_domain)
            all_items += kept
            out.append({"review": review, "text": sentence, "model_input": model_text, "raw_output": text,
                        "quads": kept, "discarded": discarded, "malformed": malformed})
        cls_ms = self._score(all_items)
        for s in out:
            for d in s["discarded"]:
                d.pop("target", None)
                d.pop("marked_sentence", None)
        return {"domain": domain, "model": gen.spec.label, "model_key": model, "decoding": decoding,
                "sentences": out, "summary": summarize(out),
                "timing": {"total_ms": round((time.perf_counter() - t_start) * 1000, 1),
                           "generation_ms_per_sentence": round(gen_ms, 1),
                           "classifier_ms": round(cls_ms, 1), "sentences": len(out)},
                "device": str(self.device), "classifier_temperature": round(self.classifier.temperature, 3)}

    def writer(self) -> "SummaryWriter":
        if "summary_writer" not in self.generators:
            if self.small_gpu:
                for other in [k for k in self.generators if k != PRIMARY]:
                    del self.generators[other]
                free_memory()
            self.generators["summary_writer"] = SummaryWriter(self.device)
        return self.generators["summary_writer"]

    def summary(self, batches: Sequence[dict], domain: str) -> dict:
        """Grounded summary of one or two analysed batches; every number in it is checked against the facts."""
        if len(batches) == 1:
            facts = summary_facts(batches[0]["summary"], batches[0]["label"], domain)
        else:
            facts = comparison_facts(batches[0]["summary"], batches[1]["summary"], batches[0]["label"],
                                     batches[1]["label"])
        task = SINGLE_TASK if len(batches) == 1 else COMPARE_TASK.format(a=batches[0]["label"], b=batches[1]["label"])
        best, total_ms = None, 0.0
        for attempt in range(3):
            text, ms = self.writer().write(facts, task, sample=attempt > 0)
            total_ms += ms
            bad = check_numbers(text, facts)
            if best is None or len(bad) < len(best[1]):
                best = (text, bad)
            if not bad:
                break
        text, ms = best[0], total_ms
        return {"text": text, "facts": facts, "unsupported_numbers": best[1],
                "highlights": highlight_spans(text, facts),
                "model": SummaryWriter.name, "ms": round(ms)}

    def samples(self, domain: str, n: int = 50, seed: int = 0) -> list[str]:
        rows = load_sentences([domain], "Test")
        idx = np.random.default_rng(seed).choice(len(rows), min(n, len(rows)), replace=False)
        return [rows[i]["text"] for i in sorted(idx)]


def entity(category_text: str) -> str:
    """Main topic of a category: "battery - operation performance" -> "battery"."""
    return category_text.partition(" - ")[0].replace("&", " and ")


def summarize(sentences: Sequence[dict], examples: int = 3) -> dict:
    """Counts per sentiment, category and aspect, the most frequent opinion words, and example sentences as evidence."""
    by_sentiment = Counter()
    by_category = defaultdict(Counter)
    by_aspect = defaultdict(Counter)
    opinions = defaultdict(Counter)
    cat_aspects = defaultdict(lambda: defaultdict(Counter))
    candidates = defaultdict(lambda: defaultdict(dict))
    by_entity = defaultdict(Counter)
    entity_subs = defaultdict(Counter)
    entity_reviews = defaultdict(lambda: defaultdict(set))
    for s in sentences:
        for q in s["quads"]:
            sent, cat = q["sentiment"], q["category_text"]
            ent = entity(cat)
            by_sentiment[sent] += 1
            by_category[cat][sent] += 1
            by_entity[ent][sent] += 1
            entity_reviews[ent][sent].add(s["review"])
            entity_subs[ent][cat.partition(" - ")[2] or "general"] += 1
            by_aspect[(q["aspect"] or "(implied) " + cat).lower()][sent] += 1
            if q["aspect"]:
                cat_aspects[cat][sent][q["aspect"].lower()] += 1
                cat_aspects["@" + ent][sent][q["aspect"].lower()] += 1
            if q["opinion"]:
                opinions[sent][q["opinion"].lower()] += 1
            score = (q.get("agrees", True), q.get("confidence", 0.0))
            for key in (cat, "@" + ent):
                if score > candidates[key][sent].get(s["text"], (False, -1.0)):
                    candidates[key][sent][s["text"]] = score

    evidence = {cat: {t: [text for text, _ in sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:examples]]
                      for t, d in by_sent.items()} for cat, by_sent in candidates.items()}

    def rows(d, limit=None, with_evidence=False, prefix=""):
        items = []
        for k, v in d.items():
            row = {"name": k, "positive": v["positive"], "negative": v["negative"], "neutral": v["neutral"],
                   "total": sum(v.values())}
            if with_evidence:
                row["examples"] = {t: evidence.get(prefix + k, {}).get(t, []) for t in ("positive", "negative", "neutral")}
                row["top_aspects"] = {t: [a for a, _ in cat_aspects[prefix + k][t].most_common(4)]
                                      for t in ("positive", "negative", "neutral")}
            if prefix:
                row["subtopics"] = [x for x, _ in entity_subs[k].most_common()]
                row["reviews_with"] = {t: len(entity_reviews[k][t]) for t in ("positive", "negative", "neutral")}
            items.append(row)
        items.sort(key=lambda r: -r["total"])
        return items[:limit] if limit else items

    total = sum(by_sentiment.values())
    return {"opinions": total, "sentences": len(sentences),
            "reviews": len({s["review"] for s in sentences}),
            "sentiment": {k: by_sentiment[k] for k in ("positive", "negative", "neutral")},
            "share": {k: round(by_sentiment[k] / total, 4) if total else 0 for k in ("positive", "negative", "neutral")},
            "categories": rows(by_category, with_evidence=True), "aspects": rows(by_aspect, 40),
            "entities": rows(by_entity, with_evidence=True, prefix="@"),
            "top_opinions": {k: [{"word": w, "count": c} for w, c in opinions[k].most_common(12)]
                             for k in ("positive", "negative", "neutral")}}


# ---------------------------------------------------------------------- grounded summaries
NUMBER = re.compile(r"\d+(?:\.\d+)?")


SUB_NAMES = {"general": "", "miscellaneous": "", "operation performance": "performance", "design features": "design",
             "prices": "prices", "price": "price", "style options": "options"}


def topic(category_text: str) -> str:
    """Short topic name for a category: "service - general" -> "service", "battery - operation performance" ->
    "battery performance"."""
    main, _, sub = category_text.partition(" - ")
    main = main.replace("&", " and ")
    sub = SUB_NAMES.get(sub, sub)
    return f"{main} {sub}".strip() if sub and sub not in main else main


def summary_facts(summary: dict, label: str, domain: str, top: int = 3) -> list[str]:
    """Short, unambiguous facts about one batch: the only material the summary writer may use."""
    c = summary["sentiment"]
    facts = [f"{label}: {summary['reviews']} {domain.lower()} reviews with {summary['opinions']} opinions "
             f"({c['positive']} positive, {c['negative']} negative, {c['neutral']} neutral)."]
    for sentiment, word, unit in (("negative", "Complaints", "complaints"), ("positive", "Praise", "positive mentions")):
        ranked = sorted([x for x in groups(summary) if x[sentiment]], key=lambda x: -x[sentiment])[:top]
        if ranked:
            parts = []
            for x in ranked:
                aspects = ", ".join(x.get("top_aspects", {}).get(sentiment, [])[:2])
                parts.append(f"{x['name']}: {x[sentiment]} {unit}" + (f" (about {aspects})" if aspects else ""))
            facts.append(f"{word} at {label}: " + "; ".join(parts) + ".")
    worst = sorted([x for x in groups(summary) if x["negative"]], key=lambda x: -x["negative"])[:1]
    if worst and worst[0].get("examples", {}).get("negative"):
        facts.append(f'{label} example complaint: "{worst[0]["examples"]["negative"][0]}"')
    return facts


def groups(summary: dict) -> list[dict]:
    """Main-topic rows when available (older results only have categories)."""
    return summary.get("entities") or [{**c, "name": topic(c["name"])} for c in summary["categories"]]


def percent(n: int, total: int) -> int:
    return int(100 * n / total + 0.5) if total else 0


SIMILAR_POINTS = 5


def complaint_rates(summary: dict) -> dict[str, int]:
    """Percentage of reviews with at least one complaint about each topic, so that sets of different sizes compare
    fairly."""
    return {g["name"]: percent(g.get("reviews_with", {}).get("negative", g["negative"]), summary["reviews"])
            for g in groups(summary) if g["negative"]}


def comparison_facts(a: dict, b: dict, la: str, lb: str) -> list[str]:
    """The comparison is worked out here, on shares rather than raw counts; the writer only has to phrase it."""
    sa, sb = (percent(x["sentiment"]["negative"], x["opinions"]) for x in (a, b))
    facts = [f"{la}: {a['reviews']} reviews with {a['opinions']} opinions, {sa}% of them negative.",
             f"{lb}: {b['reviews']} reviews with {b['opinions']} opinions, {sb}% of them negative."]
    if abs(sa - sb) < SIMILAR_POINTS:
        facts.append(f"{la} and {lb} have a similar share of negative opinions: {sa}% and {sb}%.")
    else:
        (hi, x), (lo, y) = ((la, sa), (lb, sb)) if sa > sb else ((lb, sb), (la, sa))
        facts.append(f"{hi} has a higher share of negative opinions than {lo}: {x}% vs {y}%.")
    ra, rb = complaint_rates(a), complaint_rates(b)
    names = set(ra) | set(rb)
    gap = max(names, key=lambda n: (abs(ra.get(n, 0) - rb.get(n, 0)), n)) if names else None
    if gap and abs(ra.get(gap, 0) - rb.get(gap, 0)) >= 2 * SIMILAR_POINTS:
        (hi, x), (lo, y) = (((la, ra.get(gap, 0)), (lb, rb.get(gap, 0))) if ra.get(gap, 0) > rb.get(gap, 0)
                            else ((lb, rb.get(gap, 0)), (la, ra.get(gap, 0))))
        facts.append(f"The biggest difference is {gap}: complaints in {x}% of {hi} reviews vs {y}% of {lo} reviews.")
    for x, label, rates in ((a, la, ra), (b, lb, rb)):
        if not rates:
            continue
        name = max(rates, key=lambda n: (rates[n], n))
        row = next(g for g in groups(x) if g["name"] == name)
        aspects = ", ".join(row.get("top_aspects", {}).get("negative", [])[:2])
        facts.append(f"{label} should fix {name} first: complaints in {rates[name]}% of its reviews"
                     + (f" (about {aspects})." if aspects else "."))
    return facts


OUT_OF = re.compile(r"\d+\s+out of\s+\d+(?:\s+stars?)?|\d+(?:\.\d+)?\s*stars?", re.IGNORECASE)
PAIR = re.compile(r"(\d+)\s*(?:vs\.?|versus|compared (?:to|with))\s*(\d+)", re.IGNORECASE)


FACT_PAIRS = (re.compile(r"([a-z][a-z ]*?): (\d+) (?:complaints|positive mentions)"),
              re.compile(r"biggest difference is ([a-z][a-z ]*?): complaints in (\d+)% of .+? vs (\d+)%"),
              re.compile(r"should fix ([a-z][a-z ]*?) first: complaints in (\d+)%"),
              re.compile(r"about ([a-z][a-z ]*?): (\d+) at .+? vs (\d+) at"),
              re.compile(r"should fix ([a-z][a-z ]*?) first: (\d+) complaints"))


def topic_number_pairs(facts: Sequence[str]) -> tuple[set[str], set[tuple[str, str]]]:
    """Topics named in the facts and the (topic, count) pairs the facts state."""
    topics, pairs = set(), set()
    for fact in facts:
        for pattern in FACT_PAIRS:
            for m in pattern.finditer(fact.lower()):
                name = m.group(1).strip()
                topics.add(name)
                pairs.update((name, n) for n in m.groups()[1:])
    return topics, pairs


CLAUSES = re.compile(r"(?<=[.!?])\s+|[,;]\s+(?=(?:but|while|whereas|although|however)\b)", re.IGNORECASE)


def check_topic_numbers(text: str, facts: Sequence[str]) -> list[str]:
    """Each number is paired with the nearest topic named in the same sentence; the pair must be stated in the facts."""
    topics, pairs = topic_number_pairs(facts)
    bad = set()
    for sentence in CLAUSES.split(text.lower()):
        mentions = sorted((m.start(), t) for t in topics for m in re.finditer(r"\b" + re.escape(t) + r"\b", sentence))
        numbers = [(m.start(), m.group(0)) for m in NUMBER.finditer(sentence)]
        if not mentions or not numbers:
            continue
        claimed = []
        resp = sentence.find("respectively")
        if resp >= 0:
            listed = [n for n in numbers if n[0] < resp]
            before = [t for pos, t in mentions if pos < listed[0][0]] if listed else []
            claimed += list(zip(before[-len(listed):], [n for _, n in listed])) if len(before) >= len(listed) else []
            numbers = [n for n in numbers if n[0] > resp]
        if re.search(r"\beach\b", sentence):
            for pos, n in numbers:
                claimed += [(t, n) for p_, t in mentions if p_ < pos]
        else:
            for pos, n in numbers:
                claimed.append((min(mentions, key=lambda x: abs(x[0] - pos))[1], n))
        bad |= {f"{t} {n}" for t, n in claimed if (t, n) not in pairs}
    return sorted(bad)


MORE_NEGATIVE = re.compile(r"\b(more|higher|fewer|lower|less)\b(?=[^.!?]{0,50}\b(?:negative|complaints?|criticism|"
                           r"issues?|problems?)\b)", re.IGNORECASE)


def check_direction(text: str, facts: Sequence[str]) -> list[str]:
    """A sentence that says one side has more (or fewer) complaints must name the side the facts say."""
    labels = [m.group(1).strip() for m in (re.match(r"([^:]+): \d+ (?:[a-z]+ )?reviews", f) for f in facts) if m]
    if len(labels) != 2:
        return []
    higher = next((m.group(1) for m in (re.match(r"(.+?) has a higher share of negative opinions", f) for f in facts)
                   if m), None)
    similar = any("similar share of negative opinions" in f for f in facts)
    bad = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        for m in MORE_NEGATIVE.finditer(sentence):
            if re.search(r"\b(?:topic|about|of)\b", sentence[m.start():m.start() + 60], re.IGNORECASE) and \
                    "share" not in sentence[m.start():m.start() + 60] and "opinions" not in sentence[m.start():m.start() + 60]:
                continue
            named = [(sentence.find(x), x) for x in labels if 0 <= sentence.find(x) < m.start()]
            if not named:
                continue
            subject = min(named)[1]
            word = m.group(1).lower()
            more = word in ("more", "higher")
            if similar or (higher and (subject != higher) == more):
                bad.append(f"{subject} has {word} complaints")
    return bad


def check_numbers(text: str, facts: Sequence[str]) -> list[str]:
    """Numbers in the generated text that occur nowhere in the facts, and "X vs Y" pairs that the facts do not state."""
    joined = " ".join(facts)
    allowed = set(NUMBER.findall(joined))
    pairs = {(x, y) for x, y in PAIR.findall(joined)}
    bad = {n for n in NUMBER.findall(text) if n not in allowed}
    bad |= {f"{x} vs {y}" for x, y in PAIR.findall(text) if (x, y) not in pairs and (y, x) not in pairs}
    bad |= {m.group(0) for m in OUT_OF.finditer(text) if m.group(0).lower() not in joined.lower()}
    bad |= set(check_topic_numbers(text, facts))
    bad |= set(check_direction(text, facts))
    return sorted(bad)


FACT_TERMS = (("complaint", re.compile(r"complaints at [^:]+: (.+)\.$", re.IGNORECASE)),
              ("praise", re.compile(r"praise at [^:]+: (.+)\.$", re.IGNORECASE)),
              ("complaint", re.compile(r"should fix (.+?) first: complaints in \d+% of its reviews(?: \(about (.+?)\))?",
                                       re.IGNORECASE)),
              ("complaint", re.compile(r"biggest difference is (.+?): complaints", re.IGNORECASE)))
NEGATIVE_CUES = re.compile(r"complain|negative|fix|issue|problem|critic|concern|poor|weak|worse|unhappy|disappoint",
                           re.IGNORECASE)
POSITIVE_CUES = re.compile(r"prais|positive|love|like|strength|best|enjoy|happy|appreciat|good|great", re.IGNORECASE)
COUNT = re.compile(r"\b\d+(?:\.\d+)?(?:\s*%(?:\s+of\s+(?:its\s+)?(?:[\w']+\s+){0,3}reviews)?|\s+(?:positive|negative|"
                   r"neutral)?\s*(?:complaints?|mentions?|comments?|opinions?|reviews?))", re.IGNORECASE)
SHARE_CLAIM = re.compile(r"(?:higher|lower|similar|bigger|smaller) share of negative opinions[^.!?]*?\d+%(?:\s*(?:vs\.?|"
                         r"and|compared (?:to|with))\s*\d+%)?", re.IGNORECASE)
ATTACH = 40


def fact_terms(facts: Sequence[str]) -> tuple[dict, dict, list[str]]:
    """Topic names and aspect phrases named in the facts, grouped by praise or complaint, and the batch labels."""
    topics = {"complaint": set(), "praise": set()}
    details = {"complaint": set(), "praise": set()}
    labels = []
    for fact in facts:
        head = re.match(r"([^:]+): \d+ (?:[a-z]+ )?reviews", fact)
        if head:
            labels.append(head.group(1).strip())
        for i, (kind, pattern) in enumerate(FACT_TERMS):
            m = pattern.search(fact)
            if not m:
                continue
            if i < 2:
                for part in m.group(1).split("; "):
                    name, _, rest = part.partition(":")
                    topics[kind].add(name.strip())
                    about = re.search(r"\(about (.+?)\)", rest)
                    if about:
                        details[kind].update(x.strip() for x in about.group(1).split(","))
            else:
                topics[kind].add(m.group(1).strip())
                if m.lastindex and m.lastindex > 1 and m.group(2):
                    details[kind].update(x.strip() for x in m.group(2).split(","))
    for d in (topics, details):
        for kind in d:
            d[kind] = {t for t in d[kind] if len(t) > 2}
    return topics, details, labels


def highlight_spans(text: str, facts: Sequence[str]) -> list[dict]:
    """Claims to highlight in the summary. A topic is joined with the count that belongs to it ("service, with 4
    complaints") and coloured as praise or complaint; counts that belong to no topic are not highlighted on their own,
    and the batch labels are returned so each product can be shown in its own colour."""
    topics, details, labels = fact_terms(facts)
    spans = []
    for sentence in re.finditer(r"[^.!?]+[.!?]?", text):
        s, offset = sentence.group(0), sentence.start()
        neg, pos = bool(NEGATIVE_CUES.search(s)), bool(POSITIVE_CUES.search(s))
        found = []
        for strength, table in (("topic", topics), ("detail", details)):
            for name in sorted(table["complaint"] | table["praise"], key=len, reverse=True):
                for m in re.finditer(r"\b" + re.escape(name) + r"\b", s, re.IGNORECASE):
                    if neg != pos:
                        kind = "complaint" if neg else "praise"
                    elif name in table["complaint"] and name in table["praise"]:
                        kind = "complaint" if neg else "praise"
                    else:
                        kind = "complaint" if name in table["complaint"] else "praise"
                    found.append([m.start(), m.end(), kind, strength])
        for m in SHARE_CLAIM.finditer(s):
            found.append([m.start(), m.end(), "complaint", "topic"])
        found.sort(key=lambda x: (x[0], -(x[1] - x[0])))
        terms = []
        for item in found:
            if terms and item[0] < terms[-1][1]:
                continue
            terms.append(item)
        for m in COUNT.finditer(s):
            if any(t[0] <= m.start() < t[1] for t in terms):
                continue
            before = [t for t in terms if t[1] <= m.start() and m.start() - t[1] <= ATTACH
                      and not re.search(r"\d", s[t[1]:m.start()])]
            after = [t for t in terms if t[0] >= m.end() and t[0] - m.end() <= ATTACH // 2
                     and not re.search(r"\d", s[m.end():t[0]])]
            if before:
                t = max(before, key=lambda x: x[1])
                t[1], t[3] = m.end(), "topic"
            elif after:
                t = min(after, key=lambda x: x[0])
                t[0], t[3] = m.start(), "topic"
        for start, end, kind, strength in terms:
            spans.append({"start": offset + start, "end": offset + end,
                          "kind": kind if strength == "topic" else f"{kind}_detail"})
    for i, label in enumerate(sorted({x for x in labels if len(x) > 1}, key=len, reverse=True)):
        for m in re.finditer(r"(?<!\w)" + re.escape(label) + r"(?!\w)", text):
            if not any(x["start"] < m.end() and m.start() < x["end"] for x in spans):
                spans.append({"start": m.start(), "end": m.end(), "kind": "label", "label": label})
    return sorted(spans, key=lambda x: x["start"])


class SummaryWriter:
    """Instruction-tuned LLM that turns extracted facts into a short summary for a business owner."""

    name = "Qwen/Qwen2.5-1.5B-Instruct"

    def __init__(self, device: torch.device):
        from transformers import AutoModelForCausalLM
        self.device = device
        self.dtype = torch.bfloat16 if device.type == "cuda" and torch.cuda.is_bf16_supported() else torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(self.name)
        self.model = AutoModelForCausalLM.from_pretrained(self.name, dtype=self.dtype).to(device).eval()

    @torch.no_grad()
    def write(self, facts: Sequence[str], task: str, sample: bool = False) -> tuple[str, float]:
        messages = [
            {"role": "system", "content": "You write short, factual summaries of customer feedback for a business "
                                          "owner. Use only the facts provided. Never invent numbers, aspects or "
                                          "quotes. Write plain sentences, no headings or bullet points."},
            {"role": "user", "content": "Facts:\n" + "\n".join(f"- {f}" for f in facts) + f"\n\n{task}"},
        ]
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        enc = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        sync()
        t0 = time.perf_counter()
        out = self.model.generate(**enc, max_new_tokens=140, do_sample=sample,
                                  temperature=0.7 if sample else None, top_p=0.9 if sample else None, top_k=None, repetition_penalty=1.05, pad_token_id=self.tokenizer.eos_token_id)
        sync()
        text = self.tokenizer.decode(out[0, enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        text = re.sub(r"(?:(?<=^)|(?<=[.!?]\s))\s*\(?\d\)\s*", "", text).strip()
        if text and text[-1] not in ".!?\"" and re.search(r"[.!?]", text):
            text = text[:max(text.rfind("."), text.rfind("!"), text.rfind("?")) + 1]
        return text, (time.perf_counter() - t0) * 1000


SINGLE_TASK = ("Write exactly 3 short sentences (under 70 words in total) for the owner. The first says what customers "
               "praise most, the second what they complain about most, and the third what to fix first. Do not number "
               "the sentences. Quote counts only as given, as 'N complaints' or 'N positive mentions', giving each topic "
               "its own count. Never mention stars, ratings, 'out of' or numbers of customers.")
COMPARE_TASK = ("Write one fluent sentence for each fact from the third fact on, comparing {a} and {b}, under 80 words "
                "in total. Keep every number and percent sign exactly as written, keep which side is higher or lower "
                "exactly as stated, and do not add any other numbers or claims. Do not number the sentences.")