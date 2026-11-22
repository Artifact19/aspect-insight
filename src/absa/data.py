"""Loading MEMD-ABSA, building classification pairs, and converting quadruples to and from text."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from .constants import (DOMAINS, LABEL2ID, MARK_CLOSE, MARK_OPEN, NULL, PROCESSED_DIR, RAW_DIR,
                        SENTIMENT_WORDS, SPLITS, WORD2SENTIMENT)

ELEMENTS = {"a": 0, "c": 1, "o": 2, "s": 3}
SSEP = "[SSEP]"
QUAD_PATTERN = re.compile(r"\[A\](.*?)\[C\](.*?)\[O\](.*?)\[S\](.*)", flags=re.DOTALL)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip().lower()


@dataclass(frozen=True)
class Quad:
    aspect: str
    category: str
    opinion: str
    sentiment: str
    aspect_span: tuple[int, int] = field(default=(-1, -1), compare=False)
    opinion_span: tuple[int, int] = field(default=(-1, -1), compare=False)

    @property
    def implicit_aspect(self) -> bool:
        return self.aspect.upper() == NULL

    @property
    def implicit_opinion(self) -> bool:
        return self.opinion.upper() == NULL

    def key(self, elements: str = "acos") -> tuple[str, ...]:
        values = (normalize(self.aspect), category_to_text(self.category), normalize(self.opinion), self.sentiment)
        return tuple(values[ELEMENTS[e]] for e in elements)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["aspect_span"], d["opinion_span"] = list(self.aspect_span), list(self.opinion_span)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Quad":
        return cls(d["aspect"], d["category"], d["opinion"], d["sentiment"],
                   tuple(d.get("aspect_span", (-1, -1))), tuple(d.get("opinion_span", (-1, -1))))


# ----------------------------------------------------------------------------------------------- raw data
def read_raw_split(domain: str, split: str, raw_dir: Path = RAW_DIR) -> list[dict]:
    with open(Path(raw_dir) / domain / f"{split}.json", encoding="utf-8") as f:
        items = json.load(f)
    sentences = []
    for i, item in enumerate(items, 1):
        quads = []
        for q in item["quadruples"]:
            quads.append(Quad(
                aspect=" ".join(q["aspect"]["term"]),
                category=q["category"],
                opinion=" ".join(q["opinion"]["term"]),
                sentiment=q["sentiment"],
                aspect_span=(q["aspect"]["from"], q["aspect"]["to"]),
                opinion_span=(q["opinion"]["from"], q["opinion"]["to"]),
            ))
        sentences.append({"id": f"{domain}_{split}_{i:05d}", "domain": domain, "split": split,
                          "text": item["raw_words"], "quads": [q.to_dict() for q in quads]})
    return sentences


def quads_of(sentence: dict) -> list[Quad]:
    return [Quad.from_dict(q) for q in sentence["quads"]]


def is_conflicting(sentence: dict) -> bool:
    return len({q["sentiment"] for q in sentence["quads"]}) > 1


# ----------------------------------------------------------------------------------------------- jsonl io
def write_jsonl(rows: Iterable[dict], path: Path) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_sentences(domains: Sequence[str] = DOMAINS, split: str = "Train",
                   processed_dir: Path = PROCESSED_DIR) -> list[dict]:
    rows = []
    for d in domains:
        path = Path(processed_dir) / "sentences" / f"{d}_{split}.jsonl"
        rows.extend(read_jsonl(path) if path.exists() else read_raw_split(d, split))
    return rows


def load_pairs(domains: Sequence[str] = DOMAINS, split: str = "Train",
               processed_dir: Path = PROCESSED_DIR) -> list[dict]:
    rows = []
    for d in domains:
        path = Path(processed_dir) / "pairs" / f"{d}_{split}.jsonl"
        rows.extend(read_jsonl(path) if path.exists() else build_pairs(read_raw_split(d, split)))
    return rows


# ----------------------------------------------------------------------------------------------- categories
def category_to_text(category: str) -> str:
    return normalize(str(category).replace("#", " - ").replace("_", " "))


class CategoryVocab:
    """Bidirectional mapping between dataset category labels and their natural-language form.

    Labels that differ only in letter case or underscores share one text form; the first one is kept.
    """

    def __init__(self, categories: Iterable[str]):
        self.to_text = {c: category_to_text(c) for c in sorted(set(categories))}
        self.from_text: dict[str, str] = {}
        for c, t in self.to_text.items():
            self.from_text.setdefault(t, c)

    def decode(self, text: str) -> str:
        return self.from_text.get(normalize(text), normalize(text))

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(sorted(self.to_text), indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "CategoryVocab":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))


# ----------------------------------------------------------------------------------------------- quads <-> text
def linearize(quads: Sequence[Quad]) -> str:
    parts = []
    for q in quads:
        aspect = "null" if q.implicit_aspect else q.aspect
        opinion = "null" if q.implicit_opinion else q.opinion
        parts.append(f"[A] {aspect} [C] {category_to_text(q.category)} [O] {opinion} "
                     f"[S] {SENTIMENT_WORDS[q.sentiment]}")
    return f" {SSEP} ".join(parts)


def parse(text: str, vocab: CategoryVocab | None = None) -> tuple[list[Quad], int]:
    """Parse generated text into quadruples. Returns the quadruples and the number of malformed segments."""
    quads, malformed = [], 0
    for segment in str(text).split(SSEP):
        if not segment.strip():
            continue
        m = QUAD_PATTERN.search(segment)
        sentiment = WORD2SENTIMENT.get(normalize(m.group(4))) if m else None
        if not m or sentiment is None:
            malformed += 1
            continue
        aspect, category, opinion = (normalize(g) for g in m.group(1, 2, 3))
        quads.append(Quad(
            aspect=NULL if aspect in ("", "null") else aspect,
            category=vocab.decode(category) if vocab else category,
            opinion=NULL if opinion in ("", "null") else opinion,
            sentiment=sentiment,
        ))
    return list(dict.fromkeys(quads)), malformed


# ----------------------------------------------------------------------------------------------- classification pairs
def _mark_by_search(text: str, aspect: str) -> str:
    m = re.search(r"(?<!\w)" + re.escape(aspect) + r"(?!\w)", text, flags=re.IGNORECASE)
    if not m:
        return text
    return f"{text[:m.start()]}{MARK_OPEN} {m.group(0)} {MARK_CLOSE}{text[m.end():]}"


def mark_aspect(text: str, aspect: str, span: tuple[int, int] = (-1, -1)) -> str:
    if not aspect or aspect.upper() == NULL:
        return text
    words = text.split(" ")
    start, end = span
    if start >= 0 and words[start:end] == aspect.split(" "):
        return " ".join(words[:start] + [MARK_OPEN] + words[start:end] + [MARK_CLOSE] + words[end:])
    return _mark_by_search(text, aspect)


def target_text(aspect: str, category: str) -> str:
    category_str = category.replace("#", " - ")
    if not aspect or aspect.upper() == NULL:
        return category_str
    return f"{aspect} ({category_str})"


def build_pairs(sentences: Sequence[dict]) -> list[dict]:
    """One (target, sentence, label) example per quadruple, in the input format of the sentiment classifier."""
    pairs = []
    for s in sentences:
        conflicting = is_conflicting(s)
        for k, q in enumerate(quads_of(s)):
            pairs.append({
                "pair_id": f"{s['id']}_q{k + 1}", "sentence_id": s["id"], "domain": s["domain"], "split": s["split"],
                "sentence": s["text"], "marked_sentence": mark_aspect(s["text"], q.aspect, q.aspect_span),
                "aspect": q.aspect, "category": q.category, "opinion": q.opinion,
                "target": target_text(q.aspect, q.category), "label": LABEL2ID[q.sentiment],
                "is_implicit": q.implicit_aspect, "is_conflicting": conflicting,
            })
    return pairs


def all_categories(raw_dir: Path = RAW_DIR) -> list[str]:
    cats = set()
    for d in DOMAINS:
        for sp in SPLITS:
            for s in read_raw_split(d, sp, raw_dir):
                cats.update(q["category"] for q in s["quads"])
    return sorted(cats)
