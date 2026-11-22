"""Train Flan-T5 quadruple generators for the experiments in a config. Completed runs are skipped.

Usage:
    python scripts/train_t5.py --config configs/t5_generator.yaml [--experiments all_domains] [--seeds 42]
    python scripts/train_t5.py --limit 200 --epochs 2 --experiments all_domains --seeds 42 --output-dir outputs/smoke
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from absa.constants import DOMAINS, PROCESSED_DIR  # noqa: E402
from absa.data import CategoryVocab, load_sentences  # noqa: E402
from absa.models.generator import train_generator  # noqa: E402
from absa.utils import device_name, load_config, save_json  # noqa: E402


def expand(experiment: dict) -> list[tuple[str, list[str], list[str]]]:
    """(run name, training domains, test domains) for every model an experiment needs."""
    if experiment.get("per_domain"):
        return [(d, [d], [d]) for d in DOMAINS]
    if experiment.get("leave_one_out"):
        return [(f"without_{d}", [x for x in DOMAINS if x != d], [d]) for d in DOMAINS]
    return [("model", experiment["train"], experiment["test"])]


def limited(rows, n):
    return rows if not n else rows[:n]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "t5_generator.yaml")
    ap.add_argument("--experiments", nargs="*")
    ap.add_argument("--seeds", nargs="*", type=int)
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--limit", type=int, help="use only this many sentences per domain and split (smoke tests)")
    ap.add_argument("--output-dir", type=Path)
    args = ap.parse_args()

    cfg = load_config(args.config)
    out_dir = args.output_dir or ROOT / cfg["output_dir"]
    vocab = CategoryVocab.load(PROCESSED_DIR / "categories.json")
    save_json({**cfg, "limit": args.limit, "device": device_name()}, out_dir / "config.json")
    print(f"Device: {device_name()}")

    for experiment in cfg["experiments"]:
        if args.experiments and experiment["name"] not in args.experiments:
            continue
        run_cfg = {**cfg, **{k: v for k, v in experiment.items() if k not in ("name", "train", "test", "seeds")}}
        if args.epochs:
            run_cfg["epochs"] = args.epochs
            run_cfg["eval_from_epoch"] = 1
        for seed in args.seeds or experiment["seeds"]:
            for run_name, train_domains, test_domains in expand(experiment):
                run_dir = out_dir / experiment["name"] / run_name / f"seed{seed}"
                label = f"{experiment['name']}/{run_name} seed {seed}"
                if (run_dir / "metrics.json").exists():
                    print(f"[{label}] already complete, skipped")
                    continue
                train = [s for d in train_domains for s in limited(load_sentences([d], "Train"), args.limit)]
                dev = [s for d in train_domains for s in limited(load_sentences([d], "Dev"), args.limit)]
                test = [s for d in test_domains for s in limited(load_sentences([d], "Test"), args.limit)]
                print(f"[{label}] train {len(train):,} | dev {len(dev):,} | test {len(test):,} sentences "
                      f"({', '.join(train_domains)} -> {', '.join(test_domains)})")
                save_json({"experiment": experiment["name"], "run": run_name, "train_domains": train_domains,
                           "test_domains": test_domains, "seed": seed}, run_dir / "run.json")
                save = seed in experiment.get("save_model_seeds", [])
                r = train_generator(train, dev, test, vocab, run_cfg, seed, run_dir, save_model=save)
                print(f"[{label}] test ACOS F1 {r['test']['ACOS']['f1']:.4f} | AOS {r['test']['AOS']['f1']:.4f} | "
                      f"best epoch {r['best_epoch']} | {r['train_seconds'] / 60:.1f} min")


if __name__ == "__main__":
    main()
