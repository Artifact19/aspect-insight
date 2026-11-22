"""Train aspect-level sentiment classifiers for every (method, seed) in a config. Completed runs are skipped.

Usage:
    python scripts/train_classifiers.py --config configs/classifiers.yaml [--methods focal bagging] [--seeds 42]
    python scripts/train_classifiers.py --config configs/classifiers.yaml --limit 300 --epochs 1 --output-dir outputs/smoke
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from absa.data import load_pairs, read_jsonl  # noqa: E402
from absa.imbalance import (bagging_partitions, build_loss, class_counts, oversample_conflicting,  # noqa: E402
                            random_oversample)
from absa.models.classifier import train_classifier  # noqa: E402
from absa.utils import device_name, load_config, save_json  # noqa: E402


def subsample(rows, n, seed=0):
    if not n or n >= len(rows):
        return rows
    idx = np.random.default_rng(seed).choice(len(rows), n, replace=False)
    return [rows[i] for i in sorted(idx)]


def describe(rows):
    neg, neu, pos = class_counts([r["label"] for r in rows])
    return f"{len(rows):,} pairs (NEG {neg:,} / NEU {neu:,} / POS {pos:,})"


def run_one(name, run_dir, train_rows, dev, test, method, cfg, seed, save):
    if (run_dir / "metrics.json").exists():
        print(f"[{name}] already complete, skipped")
        return
    print(f"[{name}] training on {describe(train_rows)}")
    loss = build_loss(method, [r["label"] for r in train_rows], cfg)
    result = train_classifier(train_rows, dev, test, loss, cfg, seed, run_dir, save_model=save)
    t = result["test"]
    print(f"[{name}] test accuracy {t['accuracy']:.4f} | macro-F1 {t['macro_f1']:.4f} | "
          f"neutral F1 {t['f1_per_class'][1]:.4f} | {result['train_seconds']:.0f}s")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--config", type=Path, default=ROOT / "configs" / "classifiers.yaml")
    p.add_argument("--methods", nargs="*")
    p.add_argument("--seeds", nargs="*", type=int)
    p.add_argument("--epochs", type=int)
    p.add_argument("--limit", type=int, help="subsample every split to this many pairs (smoke tests)")
    p.add_argument("--output-dir", type=Path)
    args = p.parse_args()

    cfg = load_config(args.config)
    if args.epochs:
        cfg["epochs"] = args.epochs
    out_dir = args.output_dir or ROOT / cfg["output_dir"]
    methods, seeds = args.methods or cfg["methods"], args.seeds or cfg["seeds"]
    save_cfg = cfg.get("save_models", {})

    train = subsample(load_pairs(cfg["domains"], "Train"), args.limit)
    dev = subsample(load_pairs(cfg["domains"], "Dev"), args.limit)
    test = subsample(load_pairs(cfg["domains"], "Test"), args.limit)
    print(f"Device: {device_name()}\nTrain {describe(train)}\nDev   {describe(dev)}\nTest  {describe(test)}")
    save_json({**cfg, "limit": args.limit, "device": device_name()}, out_dir / "config.json")
    save_json([r["pair_id"] for r in test], out_dir / "test_pair_ids.json")

    for seed in seeds:
        for method in methods:
            save = seed in save_cfg.get("seeds", []) and method in save_cfg.get("methods", [])
            rng = np.random.default_rng(seed)
            base = out_dir / method / f"seed{seed}"
            if method == "bagging":
                parts = bagging_partitions(train, cfg["bagging_members"], rng)
                for k, part in enumerate(parts):
                    rows = oversample_conflicting(part, cfg["conflict_oversample"])
                    run_one(f"{method} seed {seed} member {k + 1}/{len(parts)}", base / f"member{k}", rows, dev,
                            test, method, cfg, seed * 10 + k, save)
                continue
            if method == "oversample":
                rows = random_oversample(train, cfg["oversample_ratio"], rng)
            elif method in cfg.get("synthetic_pairs", {}):
                path = ROOT / cfg["synthetic_pairs"][method]
                if not path.exists():
                    raise SystemExit(f"{path} not found: run scripts/generate_neutral.py first")
                rows = train + subsample(read_jsonl(path), args.limit)
            else:
                rows = train
            rows = oversample_conflicting(rows, cfg["conflict_oversample"])
            run_one(f"{method} seed {seed}", base, rows, dev, test, method, cfg, seed, save)


if __name__ == "__main__":
    main()
