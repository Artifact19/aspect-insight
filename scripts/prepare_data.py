"""Convert raw MEMD-ABSA JSON into processed sentence and pair files, the category inventory and dataset statistics.

Usage:
    python scripts/prepare_data.py [--raw-dir data/raw/MEMD-ABSA] [--out-dir data/processed]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from absa.constants import DOMAINS, PROCESSED_DIR, RAW_DIR, SPLITS  # noqa: E402
from absa.data import (CategoryVocab, build_pairs, is_conflicting, linearize, parse, quads_of,  # noqa: E402
                       read_raw_split, write_jsonl)


def split_stats(sentences, pairs):
    quads = [q for s in sentences for q in quads_of(s)]
    sentiment = Counter(q.sentiment for q in quads)
    return {
        "sentences": len(sentences),
        "quads": len(quads),
        "NEG": sentiment["NEG"], "NEU": sentiment["NEU"], "POS": sentiment["POS"],
        "implicit_aspect": sum(q.implicit_aspect for q in quads),
        "implicit_opinion": sum(q.implicit_opinion for q in quads),
        "conflicting_sentences": sum(is_conflicting(s) for s in sentences),
        "conflicting_pairs": sum(p["is_conflicting"] for p in pairs),
        "categories": len({q.category for q in quads}),
        "mean_words": round(sum(len(s["text"].split()) for s in sentences) / max(1, len(sentences)), 1),
        "unmarked_explicit_pairs": sum(not p["is_implicit"] and "<t>" not in p["marked_sentence"] for p in pairs),
    }


def roundtrip_errors(sentences, vocab):
    errors = 0
    for s in sentences:
        gold = quads_of(s)
        parsed, malformed = parse(linearize(gold), vocab)
        if malformed or {q.key() for q in parsed} != {q.key() for q in gold}:
            errors += 1
    return errors


def markdown_table(stats):
    cols = ["sentences", "quads", "NEG", "NEU", "POS", "implicit_aspect", "implicit_opinion",
            "conflicting_sentences", "categories", "mean_words"]
    lines = ["| Domain | Split | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 2)]
    for key, row in stats.items():
        domain, split = key.split("/")
        lines.append(f"| {domain} | {split} | " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--out-dir", type=Path, default=PROCESSED_DIR)
    args = parser.parse_args()

    data = {(d, sp): read_raw_split(d, sp, args.raw_dir) for d in DOMAINS for sp in SPLITS}
    vocab = CategoryVocab(q["category"] for sents in data.values() for s in sents for q in s["quads"])
    args.out_dir.mkdir(parents=True, exist_ok=True)
    vocab.save(args.out_dir / "categories.json")

    stats = {}
    for (domain, split), sentences in data.items():
        pairs = build_pairs(sentences)
        write_jsonl(sentences, args.out_dir / "sentences" / f"{domain}_{split}.jsonl")
        write_jsonl(pairs, args.out_dir / "pairs" / f"{domain}_{split}.jsonl")
        stats[f"{domain}/{split}"] = split_stats(sentences, pairs)
        stats[f"{domain}/{split}"]["roundtrip_errors"] = roundtrip_errors(sentences, vocab)
        print(f"{domain:10s} {split:5s} sentences {len(sentences):5d} | pairs {len(pairs):5d} | "
              f"round-trip errors {stats[f'{domain}/{split}']['roundtrip_errors']}")

    (args.out_dir / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    (args.out_dir / "stats.md").write_text(markdown_table(stats), encoding="utf-8")
    print(f"Categories: {len(vocab.to_text)} labels, {len(vocab.from_text)} distinct text forms")
    print(f"Wrote {args.out_dir}")


if __name__ == "__main__":
    main()
