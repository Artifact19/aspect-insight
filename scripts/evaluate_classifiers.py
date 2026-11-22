"""Aggregate classifier runs into result tables, significance tests and figures.

Usage:
    python scripts/evaluate_classifiers.py [--runs-dir outputs/runs/classifiers] [--out-dir outputs/results/classifiers]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from absa.constants import DOMAINS  # noqa: E402
from absa.data import load_pairs  # noqa: E402
from absa.metrics import (apply_temperature, bootstrap_ci, classification_scores, expected_calibration_error,  # noqa: E402
                          fit_temperature, macro_f1, mcnemar_exact)
from absa.plotting import BLUES, INK, INK_2, MUTED, SERIES, apply_style, plt, save  # noqa: E402
from absa.utils import load_json, save_json  # noqa: E402

METHOD_NAMES = {
    "none": "No handling",
    "class_weights": "Class weights",
    "oversample": "Random oversampling",
    "focal": "Focal loss",
    "bagging": "Balanced bagging (ensemble)",
    "bagging_single": "Balanced bagging (one member)",
    "augment": "LLM synthetic Neutral (verified)",
    "augment_noverify": "LLM synthetic Neutral (not verified)",
}
REFERENCE = "class_weights"


def load_run(run_dir: Path):
    """Dev and test probabilities per model, training seconds and inference ms/pair for a run or an ensemble."""
    if (run_dir / "test_probs.npy").exists():
        m = load_json(run_dir / "metrics.json")
        return [np.load(run_dir / "dev_probs.npy")], [np.load(run_dir / "test_probs.npy")], m["train_seconds"],             m["ms_per_pair"]
    members = sorted(d for d in run_dir.glob("member*") if (d / "test_probs.npy").exists())
    if not members:
        return None
    metrics = [load_json(d / "metrics.json") for d in members]
    return ([np.load(d / "dev_probs.npy") for d in members], [np.load(d / "test_probs.npy") for d in members],
            sum(m["train_seconds"] for m in metrics),
            sum(m["ms_per_pair"] for m in metrics))


def score(y, pred, probs, test, dev_probs=None, y_dev=None):
    s = classification_scores(y, pred)
    conf = np.array([r["is_conflicting"] for r in test])
    domains = np.array([r["domain"] for r in test])
    row = {"accuracy": s["accuracy"], "macro_f1": s["macro_f1"], "neg_f1": s["f1_per_class"][0],
           "neu_f1": s["f1_per_class"][1], "pos_f1": s["f1_per_class"][2],
           "conflicting_acc": float((pred[conf] == y[conf]).mean()) if conf.any() else np.nan,
           "conflicting_macro_f1": macro_f1(y[conf], pred[conf]) if conf.any() else np.nan,
           "ece": expected_calibration_error(probs, y)}
    if dev_probs is not None and y_dev is not None and len(dev_probs) == len(y_dev):
        row["temperature"] = fit_temperature(dev_probs, y_dev)
        row["ece_scaled"] = expected_calibration_error(apply_temperature(probs, row["temperature"]), y)
    for d in DOMAINS:
        mask = domains == d
        if mask.any():
            row[f"macro_f1_{d}"] = macro_f1(y[mask], pred[mask])
    return row, s["confusion"]


def fmt(mean, std, digits=3):
    return f"{mean:.{digits}f} ± {std:.{digits}f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs-dir", type=Path, default=ROOT / "outputs" / "runs" / "classifiers")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "results" / "classifiers")
    args = ap.parse_args()
    fig_dir = args.out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_json(args.runs_dir / "config.json")
    ids = load_json(args.runs_dir / "test_pair_ids.json")
    by_id = {r["pair_id"]: r for r in load_pairs(cfg["domains"], "Test")}
    test = [by_id[i] for i in ids]
    y = np.array([r["label"] for r in test])
    y_dev = np.array([r["label"] for r in load_pairs(cfg["domains"], "Dev")])

    rows, confusions, correct, preds, ensemble_curve = [], {}, {}, {}, []
    for method_dir in sorted(d for d in args.runs_dir.iterdir() if d.is_dir()):
        method = method_dir.name
        for seed_dir in sorted(method_dir.glob("seed*")):
            loaded = load_run(seed_dir)
            if loaded is None:
                continue
            member_dev, member_probs, train_s, ms = loaded
            seed = int(seed_dir.name[4:])
            variants = [(method, np.mean(member_probs, axis=0), np.mean(member_dev, axis=0), train_s, ms,
                         len(member_probs), True)]
            if method == "bagging":
                n = len(member_probs)
                variants += [("bagging_single", p, d, train_s / n, ms / n, 1, k == 0)
                             for k, (p, d) in enumerate(zip(member_probs, member_dev))]
                for k in range(1, len(member_probs) + 1):
                    pk = np.mean(member_probs[:k], axis=0).argmax(1)
                    ensemble_curve.append({"seed": seed, "members": k, "macro_f1": macro_f1(y, pk),
                                           "neu_f1": classification_scores(y, pk)["f1_per_class"][1]})
            for name, probs, dev_probs, t, latency, n_models, keep in variants:
                pred = probs.argmax(1)
                metrics, cm = score(y, pred, probs, test, dev_probs, y_dev)
                rows.append({"method": name, "seed": seed, **metrics, "train_minutes": t / 60,
                             "ms_per_pair": latency, "models": n_models})
                if keep:
                    confusions[(name, seed)] = cm
                    correct[(name, seed)] = pred == y
                    preds[(name, seed)] = pred
    if not rows:
        raise SystemExit(f"No completed runs in {args.runs_dir}")

    runs = pd.DataFrame(rows)
    runs.to_csv(args.out_dir / "runs.csv", index=False)
    order = [m for m in METHOD_NAMES if m in set(runs["method"])]
    metric_cols = ["accuracy", "macro_f1", "neu_f1", "neg_f1", "pos_f1", "conflicting_acc", "conflicting_macro_f1",
                   "ece", "ece_scaled", "temperature", "train_minutes", "ms_per_pair", "models"]
    metric_cols = [c for c in metric_cols if c in runs.columns]
    agg = runs.groupby("method")[metric_cols].agg(["mean", "std"]).reindex(order)
    agg.columns = [f"{a}_{b}" for a, b in agg.columns]
    agg["seeds"] = runs.groupby("method")["seed"].nunique().reindex(order)
    agg.to_csv(args.out_dir / "summary.csv")

    domain_cols = [c for c in runs.columns if c.startswith("macro_f1_")]
    per_domain = runs.groupby("method")[domain_cols].mean().reindex(order)
    per_domain.columns = [c.replace("macro_f1_", "") for c in domain_cols]
    per_domain.to_csv(args.out_dir / "per_domain_macro_f1.csv")

    # paired tests against the reference method, seed by seed
    sig_rows = []
    for (name, seed), c in correct.items():
        if name == REFERENCE or (REFERENCE, seed) not in correct:
            continue
        t = mcnemar_exact(c, correct[(REFERENCE, seed)])
        sig_rows.append({"method": name, "seed": seed, "only_method_correct": t["only_a"],
                         "only_reference_correct": t["only_b"], "p_value": t["p_value"]})
    significance = pd.DataFrame(sig_rows)
    if len(significance):
        significance.sort_values(["method", "seed"]).to_csv(args.out_dir / "significance_vs_class_weights.csv",
                                                             index=False)

    # bootstrap intervals for the first seed of each method
    ci_rows = []
    first_seed = min(runs["seed"])
    for name in order:
        if (name, first_seed) not in correct:
            continue
        sub = runs[(runs["method"] == name) & (runs["seed"] == first_seed)]
        pred = preds[(name, first_seed)]
        lo, hi = bootstrap_ci(lambda idx: macro_f1(y[idx], pred[idx]), len(y), n_boot=1000)
        nlo, nhi = bootstrap_ci(lambda idx: classification_scores(y[idx], pred[idx])["f1_per_class"][1],
                                len(y), n_boot=1000)
        ci_rows.append({"method": name, "seed": first_seed, "macro_f1": float(sub["macro_f1"].iloc[0]),
                        "macro_f1_ci": [lo, hi], "neu_f1": float(sub["neu_f1"].iloc[0]), "neu_f1_ci": [nlo, nhi]})

    curve = pd.DataFrame(ensemble_curve)
    if len(curve):
        curve.groupby("members")[["macro_f1", "neu_f1"]].agg(["mean", "std"]).to_csv(args.out_dir / "ensemble_size.csv")

    write_markdown(args.out_dir / "summary.md", agg, per_domain, significance, ci_rows, order, len(y))
    save_json({"n_test": len(y), "label_counts": np.bincount(y, minlength=3).tolist(), "methods": order,
               "summary": agg.reset_index().to_dict(orient="records"),
               "per_domain": per_domain.reset_index().to_dict(orient="records"),
               "bootstrap": ci_rows, "confusion": {f"{k[0]}|{k[1]}": v for k, v in confusions.items()}},
              args.out_dir / "results.json")
    make_figures(fig_dir, agg, curve, confusions, order, first_seed)
    print((args.out_dir / "summary.md").read_text(encoding="utf-8"))


def scaled(r):
    if "ece_scaled_mean" not in r or np.isnan(r["ece_scaled_mean"]):
        return "-"
    return f"{r['ece_scaled_mean']:.3f} ({r['temperature_mean']:.2f})"


def write_markdown(path, agg, per_domain, significance, ci_rows, order, n_test):
    lines = [f"# Aspect-level sentiment: class-imbalance study\n", f"Test pairs: {n_test:,} (all five domains). "
             f"Values are mean ± standard deviation over seeds.\n",
             "| Method | Seeds | Accuracy | Macro-F1 | Neutral F1 | Conflicting acc | ECE | ECE after T-scaling (T) | "
             "Models | Train (min) | ms/pair |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in order:
        r = agg.loc[m]
        sd = lambda c: 0.0 if np.isnan(r[f"{c}_std"]) else r[f"{c}_std"]  # noqa: E731
        lines.append(f"| {METHOD_NAMES[m]} | {int(r['seeds'])} | {fmt(r['accuracy_mean'], sd('accuracy'))} | "
                     f"{fmt(r['macro_f1_mean'], sd('macro_f1'))} | {fmt(r['neu_f1_mean'], sd('neu_f1'))} | "
                     f"{fmt(r['conflicting_acc_mean'], sd('conflicting_acc'))} | {r['ece_mean']:.3f} | "
                     f"{scaled(r)} | "
                     f"{int(r['models_mean'])} | {r['train_minutes_mean']:.1f} | {r['ms_per_pair_mean']:.2f} |")
    lines += ["", "Temperature scaling: one temperature T per model, fitted on the Dev set by minimising "
              "negative log-likelihood; predictions are unchanged, only confidences.", "",
              "## Macro-F1 per domain (mean over seeds)", "",
              "| Method | " + " | ".join(per_domain.columns) + " |", "|---|" + "---|" * len(per_domain.columns)]
    for m in order:
        lines.append(f"| {METHOD_NAMES[m]} | " + " | ".join(f"{v:.3f}" for v in per_domain.loc[m]) + " |")
    if len(significance):
        lines += ["", f"## McNemar test against {METHOD_NAMES[REFERENCE]} (per seed)", "",
                  "| Method | Seed | Only this method correct | Only class weights correct | p |", "|---|---|---|---|---|"]
        for _, r in significance.sort_values(["method", "seed"]).iterrows():
            lines.append(f"| {METHOD_NAMES[r['method']]} | {r['seed']} | {r['only_method_correct']} | "
                         f"{r['only_reference_correct']} | {r['p_value']:.3g} |")
    if ci_rows:
        lines += ["", f"## 95% bootstrap intervals (seed {ci_rows[0]['seed']})", "",
                  "| Method | Macro-F1 | Neutral F1 |", "|---|---|---|"]
        for r in ci_rows:
            lines.append(f"| {METHOD_NAMES[r['method']]} | {r['macro_f1']:.3f} [{r['macro_f1_ci'][0]:.3f}, "
                         f"{r['macro_f1_ci'][1]:.3f}] | {r['neu_f1']:.3f} [{r['neu_f1_ci'][0]:.3f}, "
                         f"{r['neu_f1_ci'][1]:.3f}] |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_figures(fig_dir, agg, curve, confusions, order, seed):
    apply_style()
    labels = [METHOD_NAMES[m] for m in order][::-1]
    fig, axes = plt.subplots(1, 2, figsize=(10, 0.55 * len(order) + 1.4), sharey=True)
    for ax, (col, title) in zip(axes, [("macro_f1", "Macro-F1"), ("neu_f1", "Neutral F1")]):
        means = agg[f"{col}_mean"].reindex(order).values[::-1]
        stds = np.nan_to_num(agg[f"{col}_std"].reindex(order).values[::-1])
        ax.barh(labels, means, xerr=stds, color=SERIES[0], height=0.55, error_kw={"ecolor": INK_2, "capsize": 3})
        for i, (m, s) in enumerate(zip(means, stds)):
            ax.text(m + s + 0.01, i, f"{m:.3f}", va="center", color=INK, fontsize=8.5)
        ax.set_title(title, loc="left")
        ax.set_xlim(0, min(1.0, max(means + stds) + 0.12))
        ax.grid(axis="y", visible=False)
    fig.suptitle("Class-imbalance methods, DeBERTa-v3-small, all domains (mean ± std over seeds)",
                 x=0.01, ha="left", color=INK, fontsize=10)
    save(fig, fig_dir / "imbalance_methods.png")

    if len(curve):
        g = curve.groupby("members")["macro_f1"].agg(["mean", "std"]).fillna(0)
        fig, ax = plt.subplots(figsize=(5.5, 3.4))
        ax.errorbar(g.index, g["mean"], yerr=g["std"], color=SERIES[0], marker="o", markersize=6, linewidth=2,
                    capsize=3)
        if "class_weights" in agg.index:
            ref = agg.loc["class_weights", "macro_f1_mean"]
            ax.axhline(ref, color=MUTED, linestyle="--", linewidth=1)
            ax.text(g.index.max(), ref, " class weights (single model)", color=MUTED, va="bottom", ha="right",
                    fontsize=8)
            ax.set_ylim(top=max(ref, (g["mean"] + g["std"]).max()) + 0.008)
        ax.set_xlabel("Ensemble members averaged")
        ax.set_ylabel("Test macro-F1")
        ax.set_xticks(list(g.index))
        ax.set_title("Balanced bagging: effect of ensemble size", loc="left")
        save(fig, fig_dir / "ensemble_size.png")

    shown = [m for m in ("class_weights", "focal", "bagging", "augment") if (m, seed) in confusions] or [order[0]]
    fig, axes = plt.subplots(1, len(shown), figsize=(4.2 * len(shown), 3.6), squeeze=False)
    names = ["Negative", "Neutral", "Positive"]
    for ax, m in zip(axes[0], shown):
        cm = np.array(confusions[(m, seed)])
        norm = cm / np.maximum(cm.sum(1, keepdims=True), 1)
        ax.imshow(norm, cmap=BLUES, vmin=0, vmax=1)
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{cm[i, j]}", ha="center", va="center", fontsize=10,
                        color="#ffffff" if norm[i, j] > 0.55 else INK)
        ax.set_xticks(range(3), names)
        ax.set_yticks(range(3), names)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.grid(False)
        ax.set_title(f"{METHOD_NAMES[m]} (seed {seed})", loc="left", fontsize=10)
    save(fig, fig_dir / "confusion_matrices.png")


if __name__ == "__main__":
    main()
