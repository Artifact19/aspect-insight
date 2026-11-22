"""Generate synthetic Neutral aspect-sentiment pairs with an instruction-tuned LLM.

Steps: (1) for a real aspect and category from a domain, the LLM writes a new sentence with a neutral opinion on that
aspect, guided by real Neutral sentences from the same domain; (2) format filters: the aspect appears verbatim,
English characters only, length, no duplicates, no copies of training sentences; (3) verification: the same LLM labels the sentiment towards
the aspect without seeing the request, and only sentences it labels neutral are kept.

Writes data/processed/synthetic/neutral_pairs.jsonl (verified) and neutral_pairs_unverified.jsonl (format filters
only), candidates.jsonl (every filtered candidate with the verifier's answer), generation statistics and examples.
--refilter re-applies the format filters to existing output files without generating again.

Usage:
    python scripts/generate_neutral.py [--total 3000]
    python scripts/generate_neutral.py --refilter
    python scripts/generate_neutral.py --total 30 --model Qwen/Qwen2.5-0.5B-Instruct --out-dir outputs/smoke/synthetic
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from absa.constants import DOMAINS, LABEL2ID, NULL, PROCESSED_DIR  # noqa: E402
from absa.data import load_pairs, mark_aspect, read_jsonl, target_text, write_jsonl  # noqa: E402
from absa.models.llm import generate, load_causal_lm  # noqa: E402
from absa.utils import device_name, load_json, save_json, set_seed  # noqa: E402

PUNCT = re.compile(r"\w+|[^\w\s]")
PRONOUNS = {"it", "they", "them", "this", "that", "these", "those", "he", "she", "her", "him", "its", "one", "ones"}


def dataset_style(text: str, lowercase: bool) -> str:
    """Tokenise like the dataset: punctuation separated by spaces; lower-cased for domains stored in lower case."""
    text = text.strip().strip('"').strip()
    text = " ".join(PUNCT.findall(text))
    return text.lower() if lowercase else text


ENGLISH = re.compile(r"^[\x00-\x7F\u00C0-\u00FF\u2013\u2014\u2018\u2019\u201C\u201D]*$")


def is_english(text: str) -> bool:
    """Rejects sentences in which the generator switched script, e.g. into Chinese."""
    return ENGLISH.match(text) is not None


def contains(text: str, aspect: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(aspect) + r"(?!\w)", text, flags=re.IGNORECASE) is not None


def writer_messages(domain, aspect, examples):
    shown = "\n".join(f"- {e['sentence']} (aspect: {e['aspect'] if e['aspect'] != NULL else 'not named'})"
                      for e in examples)
    return [
        {"role": "system", "content": "You write realistic customer review sentences."},
        {"role": "user", "content":
            f"These sentences come from {domain.lower()} reviews. In each, the writer's opinion about the aspect is "
            f"neutral: neither positive nor negative.\n{shown}\n\n"
            f"Write one new {domain.lower()} review sentence that contains the words \"{aspect}\" exactly and "
            f"expresses a neutral opinion about {aspect}: a factual remark, a plain description, an expectation or "
            "an acceptable-but-unremarkable judgement, with no praise and no complaint about it. "
            "Write only the sentence."},
    ]


def verifier_messages(sentence, aspect):
    return [
        {"role": "system", "content": "You are an aspect-based sentiment annotator."},
        {"role": "user", "content":
            f"Sentence: {sentence}\nAspect: {aspect}\n"
            "What sentiment does the writer express towards the aspect? Answer with one word: positive, negative or "
            "neutral."},
    ]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--total", type=int, default=3000, help="candidate sentences, split across domains by size")
    ap.add_argument("--shots", type=int, default=4)
    ap.add_argument("--temperature", type=float, default=0.9)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out-dir", type=Path, default=PROCESSED_DIR / "synthetic")
    ap.add_argument("--force", action="store_true", help="generate again even if the output already exists")
    ap.add_argument("--refilter", action="store_true", help="re-apply the format filters to existing outputs")
    args = ap.parse_args()
    if args.refilter:
        refilter(args.out_dir, args.seed)
        return
    if (args.out_dir / "neutral_pairs.jsonl").exists() and not args.force:
        print(f"{args.out_dir / 'neutral_pairs.jsonl'} already exists, skipped (use --force to regenerate)")
        return
    set_seed(args.seed)
    rng = np.random.default_rng(args.seed)

    train = load_pairs(list(DOMAINS), "Train")
    by_domain = {d: [p for p in train if p["domain"] == d] for d in DOMAINS}
    known = {p["sentence"].lower() for p in train}
    sizes = np.array([len(by_domain[d]) for d in DOMAINS], dtype=float)
    quota = dict(zip(DOMAINS, np.maximum(1, np.round(args.total * sizes / sizes.sum())).astype(int)))
    print(f"Device: {device_name()} | model {args.model} | candidates {quota}")

    tokenizer, model = load_causal_lm(args.model)
    template = lambda msgs: tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)  # noqa: E731

    requests = []
    for d in DOMAINS:
        rows = by_domain[d]
        lowercase = np.mean([r["sentence"] == r["sentence"].lower() for r in rows]) > 0.5
        neutral = [r for r in rows if r["label"] == LABEL2ID["NEU"]]
        explicit = [r for r in rows if not r["is_implicit"] and len(r["aspect"].split()) <= 4
                    and r["aspect"].lower() not in PRONOUNS]
        for _ in range(quota[d]):
            src = explicit[rng.integers(len(explicit))]
            shots = [neutral[i] for i in rng.choice(len(neutral), min(args.shots, len(neutral)), replace=False)]
            requests.append({"domain": d, "aspect": src["aspect"], "category": src["category"], "lowercase": lowercase,
                             "prompt": template(writer_messages(d, src["aspect"], shots))})

    outputs, ms = generate(model, tokenizer, [r["prompt"] for r in requests], max_new_tokens=60,
                           batch_size=args.batch_size, do_sample=True, temperature=args.temperature, top_p=0.95)
    print(f"generated {len(outputs):,} candidates ({ms:.0f} ms each)")

    funnel = Counter()
    candidates, seen = [], set()
    for r, out in zip(requests, outputs):
        funnel["generated"] += 1
        text = dataset_style(out.splitlines()[0] if out.strip() else "", r["lowercase"])
        n_words = len(text.split())
        if not contains(text, r["aspect"]):
            funnel["rejected: aspect missing"] += 1
            continue
        if not is_english(text):
            funnel["rejected: not English"] += 1
            continue
        if not 5 <= n_words <= 60:
            funnel["rejected: length"] += 1
            continue
        key = text.lower()
        if key in seen or key in known:
            funnel["rejected: duplicate"] += 1
            continue
        seen.add(key)
        candidates.append({**r, "sentence": text})
    funnel["passed format filters"] = len(candidates)

    verdicts, _ = generate(model, tokenizer, [template(verifier_messages(c["sentence"], c["aspect"])) for c in candidates],
                           max_new_tokens=4, batch_size=args.batch_size * 2)
    for c, v in zip(candidates, verdicts):
        c["verdict"] = v.strip().lower().strip(".")
    verified = [c for c in candidates if c["verdict"].startswith("neutral")]
    funnel["verified neutral"] = len(verified)
    funnel["verifier said positive"] = sum(c["verdict"].startswith("positive") for c in candidates)
    funnel["verifier said negative"] = sum(c["verdict"].startswith("negative") for c in candidates)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(({k: c[k] for k in ("domain", "aspect", "category", "sentence", "verdict")} for c in candidates),
                args.out_dir / "candidates.jsonl")
    write_jsonl(to_pairs(verified, ""), args.out_dir / "neutral_pairs.jsonl")
    write_jsonl(to_pairs(candidates, "U"), args.out_dir / "neutral_pairs_unverified.jsonl")
    stats = {"model": args.model, "temperature": args.temperature, "shots": args.shots, "funnel": dict(funnel),
             "verified_by_domain": dict(Counter(c["domain"] for c in verified)),
             "unverified_by_domain": dict(Counter(c["domain"] for c in candidates)),
             "real_neutral_train_pairs": sum(p["label"] == LABEL2ID["NEU"] for p in train)}
    save_json(stats, args.out_dir / "generation_stats.json")
    rejected = [c for c in candidates if not c["verdict"].startswith("neutral")]
    write_report(args.out_dir, stats, verified, rejected, by_domain, rng)


def to_pairs(rows, tag):
    out = []
    for i, c in enumerate(rows):
        out.append({"pair_id": f"{c['domain']}_Synthetic{tag}_{i:05d}_q1",
                    "sentence_id": f"{c['domain']}_Synthetic{tag}_{i:05d}", "domain": c["domain"],
                    "split": "Train", "sentence": c["sentence"],
                    "marked_sentence": mark_aspect(c["sentence"], c["aspect"]), "aspect": c["aspect"],
                    "category": c["category"], "opinion": NULL, "target": target_text(c["aspect"], c["category"]),
                    "label": LABEL2ID["NEU"], "is_implicit": False, "is_conflicting": False, "synthetic": True})
    return out


def write_report(out_dir, stats, verified, rejected, by_domain, rng, rejected_block=None):
    lines = ["# Synthetic Neutral pairs", "", f"Generator and verifier: `{stats['model']}`, temperature "
             f"{stats['temperature']}, {stats['shots']} real Neutral examples per request.", "",
             "| Step | Sentences |", "|---|---|"]
    lines += [f"| {k} | {v:,} |" for k, v in stats["funnel"].items()]
    lines += ["", "| Domain | Real Neutral (train) | Synthetic, verified | Synthetic, format filters only |",
              "|---|---|---|---|"]
    for d in DOMAINS:
        lines.append(f"| {d} | {sum(p['label'] == LABEL2ID['NEU'] for p in by_domain[d])} | "
                     f"{stats['verified_by_domain'].get(d, 0)} | {stats['unverified_by_domain'].get(d, 0)} |")
    lines += ["", "## Examples (verified)", ""]
    for c in [verified[i] for i in rng.permutation(len(verified))[:15]]:
        lines.append(f"- *{c['domain']}*, aspect **{c['aspect']}**: {c['sentence']}")
    lines += ["", "## Examples rejected by the verifier", ""]
    if rejected_block is not None:
        lines += rejected_block
    else:
        for c in [rejected[i] for i in rng.permutation(len(rejected))[:8]]:
            lines.append(f"- *{c['domain']}*, aspect **{c['aspect']}**, verifier: {c['verdict']}: {c['sentence']}")
    (out_dir / "generation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:22]))


def refilter(out_dir, seed):
    """Re-applies the English filter to existing outputs, renumbers the pairs and updates the statistics."""
    stats = load_json(out_dir / "generation_stats.json")
    funnel = stats["funnel"]
    files = {"verified": out_dir / "neutral_pairs.jsonl", "unverified": out_dir / "neutral_pairs_unverified.jsonl"}
    kept = {}
    for name, path in files.items():
        rows = read_jsonl(path)
        kept[name] = [r for r in rows if is_english(r["sentence"])]
        print(f"{path.name}: {len(rows):,} -> {len(kept[name]):,} after the English filter")
    removed = funnel["passed format filters"] - len(kept["unverified"])
    if removed:
        stats.setdefault("before_refilter", dict(funnel))
        new_funnel = {}
        for k, v in funnel.items():
            if k == "passed format filters":
                new_funnel["rejected: not English"] = funnel.get("rejected: not English", 0) + removed
                new_funnel[k] = len(kept["unverified"])
            elif k == "verified neutral":
                new_funnel[k] = len(kept["verified"])
                new_funnel["rejected by verifier"] = len(kept["unverified"]) - len(kept["verified"])
            elif k not in ("rejected: not English", "rejected by verifier") and not k.startswith("verifier said"):
                new_funnel[k] = v
        stats["funnel"] = new_funnel
    stats["verified_by_domain"] = dict(Counter(r["domain"] for r in kept["verified"]))
    stats["unverified_by_domain"] = dict(Counter(r["domain"] for r in kept["unverified"]))
    write_jsonl(to_pairs(kept["verified"], ""), files["verified"])
    write_jsonl(to_pairs(kept["unverified"], "U"), files["unverified"])
    save_json(stats, out_dir / "generation_stats.json")
    old = (out_dir / "generation_report.md").read_text(encoding="utf-8").splitlines()
    marker = "## Examples rejected by the verifier"
    block = [x for x in old[old.index(marker) + 1:] if x.strip() and is_english(x)] if marker in old else []
    train = load_pairs(list(DOMAINS), "Train")
    by_domain = {d: [p for p in train if p["domain"] == d] for d in DOMAINS}
    write_report(out_dir, stats, kept["verified"], [], by_domain, np.random.default_rng(seed), rejected_block=block)


if __name__ == "__main__":
    main()
