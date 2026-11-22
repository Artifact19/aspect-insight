"""In-context prompting baselines for quadruple extraction: zero-shot, random k-shot and retrieved (similar) k-shot.

Usage:
    python scripts/prompting_baseline.py --config configs/prompting.yaml [--runs qwen7b_5shot_similar]
    python scripts/prompting_baseline.py --limit 20 --model Qwen/Qwen2.5-0.5B-Instruct --output-dir outputs/smoke/prompting
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from absa.constants import DOMAINS, PROCESSED_DIR  # noqa: E402
from absa.data import CategoryVocab, category_to_text, linearize, load_sentences, quads_of, write_jsonl  # noqa: E402
from absa.experiments import limited  # noqa: E402
from absa.models.generator import score_outputs  # noqa: E402
from absa.models.llm import chat_prompt, clean_output, generate, load_causal_lm  # noqa: E402
from absa.retrieval import TfidfIndex  # noqa: E402
from absa.utils import device_name, free_memory, load_config, load_json, save_json  # noqa: E402


def domain_categories(train):
    counts = Counter(category_to_text(q.category) for s in train for q in quads_of(s))
    return [c for c, _ in counts.most_common()]


def build_prompts(tokenizer, run, test, train_by_domain, seed):
    """Prompts for every test sentence; retrieved examples are ordered so the most similar comes last."""
    rng = np.random.default_rng(seed)
    prompts = [""] * len(test)
    k = run.get("shots", 0)
    for d in sorted({s["domain"] for s in test}):
        train = train_by_domain[d]
        idx = [i for i, s in enumerate(test) if s["domain"] == d]
        if k and run.get("selection", "random") == "similar":
            chosen = TfidfIndex([s["text"] for s in train]).search([test[i]["text"] for i in idx], k)[:, ::-1]
        elif k:
            chosen = np.stack([rng.choice(len(train), k, replace=False) for _ in idx])
        else:
            chosen = np.zeros((len(idx), 0), dtype=int)
        categories = domain_categories(train)
        for i, row in zip(idx, chosen):
            examples = [(train[j]["text"], linearize(quads_of(train[j]))) for j in row]
            prompts[i] = chat_prompt(tokenizer, test[i]["text"], examples, categories, domain=d)
    return prompts


def summarize(out_dir, results_dir):
    rows = []
    for run_file in sorted(out_dir.glob("*/seed*/metrics.json")):
        m, info = load_json(run_file), load_json(run_file.parent / "run.json")
        t = m["test"]
        row = {"run": info["run"], "model": info["model_name"].split("/")[-1], "shots": info.get("shots", 0),
               "selection": info.get("selection", "random") if info.get("shots", 0) else "-",
               "ACOS_F1": 100 * t["ACOS"]["f1"], "ACOS_P": 100 * t["ACOS"]["precision"],
               "ACOS_R": 100 * t["ACOS"]["recall"], "AOS_F1": 100 * t["AOS"]["f1"], "AE_F1": 100 * t["AE"]["f1"],
               "malformed_segments": t["malformed_segments"], "ms_per_sentence": m["ms_per_sentence"],
               "prompt_tokens": m["mean_prompt_tokens"]}
        for d, v in m["test_by_domain"].items():
            row["ACOS_" + d] = 100 * v["ACOS"]["f1"]
        rows.append(row)
    if not rows:
        return
    results_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(results_dir / "prompting.csv", index=False)
    lines = ["# In-context prompting baselines (no training)", "",
             "| Run | Model | Shots | Examples | ACOS F1 | P | R | AOS F1 | AE F1 | Malformed | Prompt tokens | ms/sentence |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['run']} | {r['model']} | {r['shots']} | {r['selection']} | {r['ACOS_F1']:.2f} | "
                     f"{r['ACOS_P']:.2f} | {r['ACOS_R']:.2f} | {r['AOS_F1']:.2f} | {r['AE_F1']:.2f} | "
                     f"{r['malformed_segments']} | {r['prompt_tokens']:.0f} | {r['ms_per_sentence']:.1f} |")
    domains = [d for d in DOMAINS if any("ACOS_" + d in r for r in rows)]
    lines += ["", "## ACOS F1 per domain", "", "| Run | " + " | ".join(domains) + " |",
              "|---|" + "---|" * len(domains)]
    for r in rows:
        cells = [f"{r['ACOS_' + d]:.2f}" if "ACOS_" + d in r else "" for d in domains]
        lines.append(f"| {r['run']} | " + " | ".join(cells) + " |")
    (results_dir / "prompting.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "prompting.yaml")
    ap.add_argument("--runs", nargs="*")
    ap.add_argument("--model", help="override the model of every run (smoke tests)")
    ap.add_argument("--limit", type=int, help="use only this many test sentences per domain")
    ap.add_argument("--batch-size", type=int)
    ap.add_argument("--output-dir", type=Path)
    ap.add_argument("--results-dir", type=Path)
    args = ap.parse_args()

    cfg = load_config(args.config)
    out_dir = args.output_dir or ROOT / cfg["output_dir"]
    results_dir = args.results_dir or ROOT / "outputs" / "results" / "prompting"
    vocab = CategoryVocab.load(PROCESSED_DIR / "categories.json")
    test = [s for d in DOMAINS for s in limited(load_sentences([d], "Test"), args.limit)]
    train_by_domain = {d: load_sentences([d], "Train") for d in DOMAINS}
    batch_size = args.batch_size or cfg.get("batch_size", 16)
    seed = cfg.get("seed", 0)
    print(f"Device: {device_name()} | {len(test):,} test sentences")

    runs = [r for r in cfg["runs"] if not args.runs or r["name"] in args.runs]
    loaded_name, tokenizer, model = None, None, None
    for run in sorted(runs, key=lambda r: r["model_name"]):
        run = {**run, "model_name": args.model or run["model_name"]}
        run_dir = out_dir / run["name"] / f"seed{seed}"
        if (run_dir / "metrics.json").exists():
            print(f"[{run['name']}] already complete, skipped")
            continue
        if run["model_name"] != loaded_name:
            model = None
            free_memory()
            tokenizer, model = load_causal_lm(run["model_name"])
            loaded_name = run["model_name"]
        prompts = build_prompts(tokenizer, run, test, train_by_domain, seed)
        n_tokens = [len(tokenizer(p, add_special_tokens=False)["input_ids"]) for p in prompts]
        print(f"[{run['name']}] {run['model_name']} | {run.get('shots', 0)} shots | "
              f"mean prompt {np.mean(n_tokens):.0f} tokens")
        raw, ms = generate(model, tokenizer, prompts, cfg.get("max_new_tokens", 200), batch_size)
        outputs = [clean_output(o) for o in raw]
        save_json({"experiment": "prompting", "run": run["name"], "seed": seed, "train_domains": [],
                   "test_domains": list(DOMAINS), **run}, run_dir / "run.json")
        write_jsonl(({"id": s["id"], "domain": s["domain"], "output": o, "raw": r}
                     for s, o, r in zip(test, outputs, raw)), run_dir / "test_predictions.jsonl")
        by_domain = {}
        for d in DOMAINS:
            idx = [i for i, s in enumerate(test) if s["domain"] == d]
            by_domain[d] = score_outputs([test[i] for i in idx], [outputs[i] for i in idx], vocab)
        result = {"ms_per_sentence": round(ms, 2), "mean_prompt_tokens": float(np.mean(n_tokens)),
                  "test": score_outputs(test, outputs, vocab), "test_by_domain": by_domain}
        save_json(result, run_dir / "metrics.json")
        print(f"[{run['name']}] test ACOS F1 {result['test']['ACOS']['f1']:.4f} | "
              f"AOS {result['test']['AOS']['f1']:.4f} | {ms:.1f} ms/sentence")
    summarize(out_dir, results_dir)


if __name__ == "__main__":
    main()
