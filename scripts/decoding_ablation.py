"""Compare decoding strategies for a trained quadruple generator on the test set.

Strategies: greedy, beam search, temperature/top-p sampling, and self-consistency (several samples, majority vote).

Usage:
    python scripts/decoding_ablation.py --model-dir outputs/runs/t5/all_domains/model/seed42/model
"""
import argparse
import sys
from pathlib import Path

import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from absa.analysis import majority_vote  # noqa: E402
from absa.constants import DOMAINS, PROCESSED_DIR  # noqa: E402
from absa.data import CategoryVocab, load_sentences, parse, quads_of  # noqa: E402
from absa.metrics import extraction_scores  # noqa: E402
from absa.models.generator import DEFAULT_PREFIX, generate, load_generator, source_text  # noqa: E402
from absa.utils import device_name, load_json, save_json, set_seed  # noqa: E402

STRATEGIES = [
    ("Greedy", {"num_beams": 1, "do_sample": False}, 1),
    ("Beam search (4 beams)", {"num_beams": 4, "do_sample": False}, 1),
    ("Sampling, T=0.7, top-p=0.9", {"do_sample": True, "temperature": 0.7, "top_p": 0.9}, 1),
    ("Sampling, T=1.0, top-p=1.0", {"do_sample": True, "temperature": 1.0, "top_p": 1.0}, 1),
    ("Self-consistency (5 samples, T=0.7, majority vote)", {"do_sample": True, "temperature": 0.7, "top_p": 0.9}, 5),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model-dir", type=Path, default=ROOT / "outputs/runs/t5/all_domains/model/seed42/model")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "results" / "t5")
    ap.add_argument("--domains", nargs="*", default=list(DOMAINS))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--prefix", default=DEFAULT_PREFIX)
    ap.add_argument("--batch-size", type=int, default=64)
    args = ap.parse_args()

    vocab = CategoryVocab.load(PROCESSED_DIR / "categories.json")
    tokenizer, model = load_generator(args.model_dir)
    sentences = [s for d in args.domains for s in load_sentences([d], "Test")[:args.limit or None]]
    settings = load_json(args.model_dir / "absa_config.json") if (args.model_dir / "absa_config.json").exists() else {}
    sources = [source_text(s, settings.get("source_prefix", args.prefix), settings.get("domain_in_source", False))
               for s in sentences]
    gold = [quads_of(s) for s in sentences]
    print(f"Device: {device_name()} | {len(sentences):,} test sentences")

    rows = []
    for name, kwargs, n_samples in STRATEGIES:
        set_seed(0)
        samples, total_ms = [], 0.0
        for _ in range(n_samples):
            outputs, ms = generate(model, tokenizer, sources, batch_size=args.batch_size, **kwargs)
            samples.append([parse(o, vocab) for o in outputs])
            total_ms += ms
        if n_samples == 1:
            pred = [p[0] for p in samples[0]]
        else:
            pred = [majority_vote([s[i][0] for s in samples], n_samples // 2 + 1) for i in range(len(sentences))]
        malformed = sum(p[1] for s in samples for p in s) / n_samples
        scores = extraction_scores(gold, pred)
        rows.append({"strategy": name, "ACOS_F1": 100 * scores["ACOS"]["f1"], "ACOS_P": 100 * scores["ACOS"]["precision"],
                     "ACOS_R": 100 * scores["ACOS"]["recall"], "AOS_F1": 100 * scores["AOS"]["f1"],
                     "malformed_segments": malformed, "ms_per_sentence": total_ms})
        print(f"{name:55s} ACOS F1 {rows[-1]['ACOS_F1']:.2f} | {total_ms:.1f} ms/sentence")
        torch.cuda.empty_cache() if torch.cuda.is_available() else None

    df = pd.DataFrame(rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_dir / "decoding_ablation.csv", index=False)
    lines = ["# Decoding strategies", "", f"{len(sentences):,} test sentences, model `{args.model_dir.name}`.", "",
             "| Strategy | ACOS F1 | Precision | Recall | AOS F1 | Malformed segments | ms/sentence |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['strategy']} | {r['ACOS_F1']:.2f} | {r['ACOS_P']:.2f} | {r['ACOS_R']:.2f} | "
                     f"{r['AOS_F1']:.2f} | {r['malformed_segments']:.1f} | {r['ms_per_sentence']:.1f} |")
    (args.out_dir / "decoding_ablation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    save_json(rows, args.out_dir / "decoding_ablation.json")


if __name__ == "__main__":
    main()
