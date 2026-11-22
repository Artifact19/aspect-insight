"""Fine-tune Qwen2.5 with LoRA to generate quadruples, for the experiments in a config. Completed runs are skipped.

Usage:
    python scripts/train_qwen.py --config configs/qwen_generator.yaml [--experiments all_domains] [--seeds 42]
    python scripts/train_qwen.py --limit 40 --epochs 1 --seeds 42 --output-dir outputs/smoke/qwen
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from absa.constants import PROCESSED_DIR  # noqa: E402
from absa.data import CategoryVocab, load_sentences  # noqa: E402
from absa.experiments import expand, limited  # noqa: E402
from absa.models.llm import train_llm_generator  # noqa: E402
from absa.utils import device_name, load_config, save_json  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "qwen_generator.yaml")
    ap.add_argument("--experiments", nargs="*")
    ap.add_argument("--seeds", nargs="*", type=int)
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--batch-size", type=int)
    ap.add_argument("--gradient-checkpointing", action="store_true")
    ap.add_argument("--limit", type=int, help="use only this many sentences per domain and split (smoke tests)")
    ap.add_argument("--output-dir", type=Path)
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.batch_size:
        cfg["batch_size"] = args.batch_size
        cfg["eval_batch_size"] = max(args.batch_size, 8)
    if args.gradient_checkpointing:
        cfg["gradient_checkpointing"] = True
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
                r = train_llm_generator(train, dev, test, vocab, run_cfg, seed, run_dir, save_model=save)
                print(f"[{label}] test ACOS F1 {r['test']['ACOS']['f1']:.4f} | AOS {r['test']['AOS']['f1']:.4f} | "
                      f"best epoch {r['best_epoch']} | {r['train_seconds'] / 60:.1f} min | "
                      f"{r['trainable_parameters'] / 1e6:.1f}M trainable parameters")


if __name__ == "__main__":
    main()
