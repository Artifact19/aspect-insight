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
        text, ms = self.writer().write(facts, task)
        return {"text": text, "facts": facts, "unsupported_numbers": check_numbers(text, facts),
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
    for s in sentences:
        for q in s["quads"]:
            sent, cat = q["sentiment"], q["category_text"]
            ent = entity(cat)
            by_sentiment[sent] += 1
            by_category[cat][sent] += 1
            by_entity[ent][sent] += 1
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


def comparison_facts(a: dict, b: dict, la: str, lb: str) -> list[str]:
    """The comparison is worked out here; the writer only has to phrase these conclusions."""
    na, nb = a["sentiment"]["negative"], b["sentiment"]["negative"]
    more, less = ((la, na), (lb, nb)) if na >= nb else ((lb, nb), (la, na))
    facts = [f"{la}: {a['reviews']} reviews with {a['sentiment']['positive']} positive and {na} negative opinions.",
             f"{lb}: {b['reviews']} reviews with {b['sentiment']['positive']} positive and {nb} negative opinions.",
             (f"{more[0]} has more negative opinions: {more[1]} vs {less[1]}." if na != nb else
              f"{la} and {lb} have the same number of negative opinions: {na} each.")]
    ca = {c["name"]: c["negative"] for c in groups(a)}
    cb = {c["name"]: c["negative"] for c in groups(b)}
    shared = set(ca) | set(cb)
    gap = max(shared, key=lambda n: abs(ca.get(n, 0) - cb.get(n, 0))) if shared else None
    if gap and ca.get(gap, 0) != cb.get(gap, 0):
        facts.append(f"The biggest difference in complaints is about {gap}: {ca.get(gap, 0)} at {la} vs "
                     f"{cb.get(gap, 0)} at {lb}.")
    for x, label in ((a, la), (b, lb)):
        worst = sorted([c for c in groups(x) if c["negative"]], key=lambda c: -c["negative"])[:1]
        if worst:
            aspects = ", ".join(worst[0].get("top_aspects", {}).get("negative", [])[:2])
            facts.append(f"{label} should fix {worst[0]['name']} first: {worst[0]['negative']} complaints"
                         + (f" (about {aspects})." if aspects else "."))
    return facts


OUT_OF = re.compile(r"\d+\s+out of\s+\d+(?:\s+stars?)?|\d+(?:\.\d+)?\s*stars?", re.IGNORECASE)
PAIR = re.compile(r"(\d+)\s*(?:vs\.?|versus|compared (?:to|with))\s*(\d+)", re.IGNORECASE)


FACT_PAIRS = (re.compile(r"([a-z][a-z ]*?): (\d+) (?:complaints|positive mentions)"),
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


def check_topic_numbers(text: str, facts: Sequence[str]) -> list[str]:
    """Each number is paired with the nearest topic named in the same sentence; the pair must be stated in the facts."""
    topics, pairs = topic_number_pairs(facts)
    bad = set()
    for sentence in re.split(r"(?<=[.!?])\s+", text.lower()):
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


def check_numbers(text: str, facts: Sequence[str]) -> list[str]:
    """Numbers in the generated text that occur nowhere in the facts, and "X vs Y" pairs that the facts do not state."""
    joined = " ".join(facts)
    allowed = set(NUMBER.findall(joined))
    pairs = {(x, y) for x, y in PAIR.findall(joined)}
    bad = {n for n in NUMBER.findall(text) if n not in allowed}
    bad |= {f"{x} vs {y}" for x, y in PAIR.findall(text) if (x, y) not in pairs and (y, x) not in pairs}
    bad |= {m.group(0) for m in OUT_OF.finditer(text) if m.group(0).lower() not in joined.lower()}
    bad |= set(check_topic_numbers(text, facts))
    return sorted(bad)


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
    def write(self, facts: Sequence[str], task: str) -> tuple[str, float]:
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
        out = self.model.generate(**enc, max_new_tokens=140, do_sample=False, temperature=None, top_p=None,
                                  top_k=None, repetition_penalty=1.05, pad_token_id=self.tokenizer.eos_token_id)
        sync()
        text = self.tokenizer.decode(out[0, enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        if text and text[-1] not in ".!?\"" and re.search(r"[.!?]", text):
            text = text[:max(text.rfind("."), text.rfind("!"), text.rfind("?")) + 1]
        return text, (time.perf_counter() - t0) * 1000


SINGLE_TASK = ("Write exactly 3 short sentences (under 70 words in total) for the owner: 1) what customers praise "
               "most, 2) what they complain about most, 3) what to fix first. Quote counts only as given, as "
               "'N complaints' or 'N positive mentions', giving each topic its own count. Never mention stars, ratings, "
               "'out of' or numbers of customers.")
COMPARE_TASK = ("Rewrite the last three facts as exactly 3 fluent sentences comparing {a} and {b}, under 70 words in "
                "total. Keep every number exactly as written and do not add any other numbers or claims.")
