"""Evaluate quadruple-generation runs: per-domain scores, comparison with published results, cross-domain transfer,
implicit-element recall and error analysis.

Usage:
    python scripts/evaluate_generators.py --runs-dir outputs/runs/t5 --out-dir outputs/results/t5 --label "Flan-T5-base"
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from absa.analysis import ERROR_TYPES, error_taxonomy, recall_by_group  # noqa: E402
from absa.constants import DOMAINS, PROCESSED_DIR  # noqa: E402
from absa.data import CategoryVocab, category_to_text, load_sentences, parse, quads_of, read_jsonl  # noqa: E402
from absa.metrics import EXTRACTION_TASKS, extraction_scores  # noqa: E402
from absa.plotting import INK, INK_2, MUTED, SERIES, apply_style, plt, save  # noqa: E402
from absa.reference_results import (ORDER, TABLE8_AOS_LEAVE_ONE_OUT, TABLE9_ACOS, TABLE9_AOS,  # noqa: E402
                                    best_published)
from absa.utils import load_json, save_json  # noqa: E402

TASKS = list(EXTRACTION_TASKS)
OWN = [("in_domain", "Ours: per-domain models"), ("all_domains", "Ours: one model, all domains"),
       ("all_domains_tagged", "Ours: one model, domain in input")]
SINGLE_MODEL = ("all_domains", "all_domains_tagged")


def domain_categories():
    return {d: {category_to_text(q.category) for s in load_sentences([d], "Train") for q in quads_of(s)}
            for d in DOMAINS}


def wrong_domain_rows(run, allowed):
    """Share of predicted quadruples whose category belongs to another domain, and ACOS F1 once they are removed."""
    rows = []
    domains = [s["domain"] for s in run["sentences"]]
    for d in sorted(set(domains)):
        idx = [i for i, x in enumerate(domains) if x == d]
        pred = [run["pred"][i] for i in idx]
        n = sum(len(p) for p in pred)
        wrong = sum(category_to_text(q.category) not in allowed[d] for p in pred for q in p)
        kept = [[q for q in p if category_to_text(q.category) in allowed[d]] for p in pred]
        gold = [run["gold"][i] for i in idx]
        rows.append({"experiment": run["experiment"], "seed": run["seed"], "domain": d,
                     "wrong_domain_share": 100 * wrong / max(1, n),
                     "ACOS": 100 * extraction_scores(gold, pred, {"ACOS": "acos"})["ACOS"]["f1"],
                     "ACOS_filtered": 100 * extraction_scores(gold, kept, {"ACOS": "acos"})["ACOS"]["f1"]})
    return rows


def explicit_only(sentences):
    return [i for i, s in enumerate(sentences) if all(not q.implicit_aspect and not q.implicit_opinion
                                                      for q in quads_of(s))]


def load_runs(runs_dir: Path, vocab: CategoryVocab):
    gold_by_id = {s["id"]: s for d in DOMAINS for s in load_sentences([d], "Test")}
    runs = []
    for run_file in sorted(runs_dir.rglob("run.json")):
        run_dir = run_file.parent
        if not (run_dir / "test_predictions.jsonl").exists():
            continue
        info = load_json(run_file)
        preds = read_jsonl(run_dir / "test_predictions.jsonl")
        sentences = [gold_by_id[p["id"]] for p in preds]
        parsed = [parse(p["output"], vocab) for p in preds]
        metrics = load_json(run_dir / "metrics.json") if (run_dir / "metrics.json").exists() else {}
        runs.append({**info, "dir": run_dir, "sentences": sentences, "gold": [quads_of(s) for s in sentences],
                     "pred": [p[0] for p in parsed], "malformed": sum(p[1] for p in parsed),
                     "metrics": metrics})
    return runs


def score_rows(run):
    rows = []
    domains = np.array([s["domain"] for s in run["sentences"]])
    for d in sorted(set(domains)) + ["ALL"]:
        idx = np.arange(len(domains)) if d == "ALL" else np.flatnonzero(domains == d)
        g, p = [run["gold"][i] for i in idx], [run["pred"][i] for i in idx]
        scores = extraction_scores(g, p)
        row = {"experiment": run["experiment"], "run": run["run"], "seed": run["seed"], "domain": d}
        row.update({t: 100 * scores[t]["f1"] for t in TASKS})
        row.update({f"{t}_P": 100 * scores[t]["precision"] for t in ("ACOS",)})
        row.update({f"{t}_R": 100 * scores[t]["recall"] for t in ("ACOS",)})
        sub = [run["sentences"][i] for i in idx]
        ex = explicit_only(sub)
        ex_scores = extraction_scores([g[i] for i in ex], [p[i] for i in ex], {"AOS": "aos"})
        row["AOS_explicit_sentences"] = 100 * ex_scores["AOS"]["f1"]
        row["sentences"] = len(idx)
        rows.append(row)
    return rows


def ms(series):
    vals = series.dropna().values
    if len(vals) == 0:
        return ""
    return f"{vals.mean():.2f}" if len(vals) == 1 else f"{vals.mean():.2f} ± {vals.std(ddof=1):.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs-dir", type=Path, default=ROOT / "outputs" / "runs" / "t5")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "results" / "t5")
    ap.add_argument("--label", default="Flan-T5-base")
    args = ap.parse_args()
    fig_dir = args.out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    vocab = CategoryVocab.load(PROCESSED_DIR / "categories.json")
    runs = load_runs(args.runs_dir, vocab)
    if not runs:
        raise SystemExit(f"No completed runs in {args.runs_dir}")
    table = pd.DataFrame([r for run in runs for r in score_rows(run)])
    table.to_csv(args.out_dir / "scores_all_runs.csv", index=False)
    md = [f"# {args.label}: quadruple extraction results", "",
          "Micro-F1 (%) with exact matching. Mean ± standard deviation over seeds where several seeds were run.", ""]
    report = {"label": args.label}

    # ---- main comparison with the published results (paper order of domains)
    pub_acos, pub_aos = best_published(TABLE9_ACOS), best_published(TABLE9_AOS)
    own_cols = [(e, n) for e, n in OWN if e in set(table.experiment)] or [(e, n) for e, n in OWN[:2]]
    lines = ["## Comparison with published results (ACOS, Table 9 of the MEMD-ABSA paper)", "",
             "| Domain | Best published | T5-Paraphrase | T5-index | " + " | ".join(n for _, n in own_cols) + " |",
             "|---|---|---|---|" + "---|" * len(own_cols)]
    comparison = []
    for d in ORDER:
        own = {e: table[(table.experiment == e) & (table.domain == d)]["ACOS"] for e, _ in own_cols}
        lines.append(f"| {d} | {pub_acos[d][1]:.2f} ({pub_acos[d][0]}) | {TABLE9_ACOS['T5-Paraphrase'][d]:.2f} | "
                     f"{TABLE9_ACOS['T5-index'][d]:.2f} | " + " | ".join(ms(own[e]) for e, _ in own_cols) + " |")
        comparison.append({"domain": d, "best_published": pub_acos[d][1], "best_published_model": pub_acos[d][0],
                           **{f"ours_{e}": float(v.mean()) if len(v) else None for e, v in own.items()}})
    md += lines + ["", "## Comparison with published results (AOS, Table 9)", "",
                   "| Domain | Best published | " + " | ".join(n for _, n in own_cols) + " |",
                   "|---|---|" + "---|" * len(own_cols)]
    for d in ORDER:
        own = {e: table[(table.experiment == e) & (table.domain == d)]["AOS"] for e, _ in own_cols}
        md.append(f"| {d} | {pub_aos[d][1]:.2f} ({pub_aos[d][0]}) | " + " | ".join(ms(own[e]) for e, _ in own_cols) + " |")
    report["comparison_acos"] = comparison

    # ---- sub-tasks for the single models trained on all domains
    single = [(e, n) for e, n in OWN if e in SINGLE_MODEL and e in set(table.experiment)]
    if single:
        md += ["", "## One model for all domains: every sub-task (all test sentences)", "",
               "| Model | " + " | ".join(TASKS) + " | ACOS precision | ACOS recall |", "|---|" + "---|" * (len(TASKS) + 2)]
        for e, name in single:
            overall = table[(table.experiment == e) & (table.domain == "ALL")]
            md.append(f"| {name.replace('Ours: ', '')} | " + " | ".join(ms(overall[t]) for t in TASKS) +
                      f" | {ms(overall['ACOS_P'])} | {ms(overall['ACOS_R'])} |")
            report[f"{e}_subtasks"] = {t: float(overall[t].mean()) for t in TASKS}

        allowed = domain_categories()
        wd = pd.DataFrame([r for run in runs if run["experiment"] in SINGLE_MODEL for r in wrong_domain_rows(run, allowed)])
        wd.to_csv(args.out_dir / "wrong_domain_categories.csv", index=False)
        md += ["", "## Categories from the wrong domain (single models)", "",
               "Share of predicted quadruples whose category exists only in another domain, and ACOS F1 before and "
               "after such quadruples are removed.", "",
               "| Model | Domain | Wrong-domain categories (%) | ACOS F1 | ACOS F1, wrong-domain removed |",
               "|---|---|---|---|---|"]
        for e, name in single:
            for d in ORDER:
                sub = wd[(wd.experiment == e) & (wd.domain == d)]
                if len(sub):
                    md.append(f"| {name.replace('Ours: ', '')} | {d} | {ms(sub['wrong_domain_share'])} | "
                              f"{ms(sub['ACOS'])} | {ms(sub['ACOS_filtered'])} |")

    # ---- cross-domain transfer
    settings = [("in_domain", "Trained on the same domain"), ("all_domains", "Trained on all five domains"),
                ("all_domains_tagged", "Trained on all five domains, domain in input"),
                ("cross_laptop_restaurant", "Trained on Laptop + Restaurant"),
                ("leave_one_out", "Trained on the other four domains")]
    present = [(e, n) for e, n in settings if e in set(table.experiment)]
    if any(e in ("cross_laptop_restaurant", "leave_one_out") for e, _ in present):
        for task in ("ACOS", "AOS"):
            md += ["", f"## Transfer to other domains ({task} F1)", "", "| Training data | " + " | ".join(ORDER) + " |",
                   "|---|" + "---|" * len(ORDER)]
            for e, name in present:
                md.append(f"| {name} | " + " | ".join(ms(table[(table.experiment == e) & (table.domain == d)][task])
                                                       for d in ORDER) + " |")
        loo = table[table.experiment == "leave_one_out"]
        if len(loo):
            md += ["", "### Leave-one-domain-out vs the paper (AOS, sentences with explicit elements only; approximate)",
                   "", "| Held-out domain | Paper (T5-Paraphrase) | Ours |", "|---|---|---|"]
            for d in ORDER:
                md.append(f"| {d} | {TABLE8_AOS_LEAVE_ONE_OUT[d]:.2f} | "
                          f"{ms(loo[loo.domain == d]['AOS_explicit_sentences'])} |")

    # ---- implicit elements and error analysis for the all-domain model
    main_runs = ([r for r in runs if r["experiment"] == "all_domains"]
                 or [r for r in runs if r["experiment"] == "all_domains_tagged"] or runs)
    groups = [recall_by_group(r["gold"], r["pred"]) for r in main_runs]
    md += ["", "## ACOS recall by element type (one model, all domains)", "", "| Gold quadruples with | Count | Recall (%) |",
           "|---|---|---|"]
    for g in groups[0]:
        md.append(f"| {g} | {groups[0][g]['n']:,} | {ms(pd.Series([100 * x[g]['recall'] for x in groups]))} |")
    report["recall_by_group"] = {g: float(np.mean([x[g]["recall"] for x in groups])) for g in groups[0]}

    first = sorted(main_runs, key=lambda r: r["seed"])[0]
    errors = error_taxonomy(first["gold"], first["pred"])
    md += ["", f"## Error analysis ({first['experiment']}, seed {first['seed']})", "",
           f"{errors['missed_total']:,} gold quadruples were not produced exactly; {errors['spurious']:,} predictions "
           "had no matching gold quadruple.", "", "| Missed because of | Count | Share |", "|---|---|---|"]
    for t in ERROR_TYPES:
        n = errors["missed_by_type"][t]
        md.append(f"| {t} | {n:,} | {100 * n / max(1, errors['missed_total']):.1f}% |")
    report["errors"] = errors

    # ---- run cost and format validity
    md += ["", "## Runs", "", "| Experiment | Run | Seed | Best epoch | Train (min) | ms/sentence | Malformed segments |",
           "|---|---|---|---|---|---|---|"]
    for r in sorted(runs, key=lambda r: (r["experiment"], r["run"], r["seed"])):
        m = r["metrics"]
        md.append(f"| {r['experiment']} | {r['run']} | {r['seed']} | {m.get('best_epoch', '')} | "
                  f"{m.get('train_seconds', 0) / 60:.1f} | {m.get('ms_per_sentence', '')} | {r['malformed']} |")

    (args.out_dir / "results.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    save_json(report, args.out_dir / "results.json")
    make_figures(fig_dir, table, comparison, errors, first, args.label)
    print("\n".join(md))


def make_figures(fig_dir, table, comparison, errors, first, label):
    apply_style()
    series = [("best_published", "Best published (paper)", MUTED)]
    if any(c.get("ours_in_domain") is not None for c in comparison):
        series.append(("ours_in_domain", f"{label}, per-domain models", SERIES[0]))
    if any(c.get("ours_all_domains") is not None for c in comparison):
        series.append(("ours_all_domains", f"{label}, one model", SERIES[1]))
    if any(c.get("ours_all_domains_tagged") is not None for c in comparison):
        series.append(("ours_all_domains_tagged", f"{label}, one model + domain", SERIES[2]))
    x = np.arange(len(ORDER))
    width = 0.8 / len(series)
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    for k, (key, name, color) in enumerate(series):
        vals = [c[key] if c.get(key) is not None else np.nan for c in comparison]
        bars = ax.bar(x + (k - (len(series) - 1) / 2) * width, vals, width * 0.92, color=color, label=name)
        for b, v in zip(bars, vals):
            if not np.isnan(v):
                ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f"{v:.1f}", ha="center", fontsize=7.5, color=INK_2)
    ax.set_xticks(x, ORDER)
    ax.set_ylabel("ACOS F1 (%)")
    ax.set_title("Quadruple extraction vs published results", loc="left")
    ax.legend(loc="upper left", ncols=min(len(series), 2), fontsize=8)
    ax.set_ylim(0, max(80, np.nanmax([c.get(k) or 0 for c in comparison for k, _, _ in series]) + 18))
    ax.grid(axis="x", visible=False)
    save(fig, fig_dir / "acos_vs_published.png")

    fig, ax = plt.subplots(figsize=(6.5, 2.8))
    names = list(ERROR_TYPES)[::-1]
    vals = [errors["missed_by_type"][n] for n in names]
    ax.barh(names, vals, color=SERIES[0], height=0.55)
    for i, v in enumerate(vals):
        ax.text(v, i, f" {v:,}", va="center", fontsize=8, color=INK)
    ax.set_xlabel("Missed gold quadruples")
    ax.set_title(f"Why quadruples were missed ({first['experiment']}, seed {first['seed']})", loc="left")
    ax.grid(axis="y", visible=False)
    save(fig, fig_dir / "error_types.png")

    log = [e for e in first["metrics"].get("log", []) if "dev_acos_f1" in e]
    if log:
        fig, ax = plt.subplots(figsize=(5.5, 3.2))
        ax.plot([e["epoch"] for e in log], [100 * e["dev_acos_f1"] for e in log], color=SERIES[0], marker="o",
                markersize=5, linewidth=2)
        best = first["metrics"]["best_epoch"]
        ax.axvline(best, color=MUTED, linestyle="--", linewidth=1)
        ax.text(best, ax.get_ylim()[0], f" kept: epoch {best}", color=MUTED, fontsize=8, va="bottom")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Dev ACOS F1 (%)")
        ax.set_title("Validation score during training", loc="left")
        save(fig, fig_dir / "dev_curve.png")


if __name__ == "__main__":
    main()
