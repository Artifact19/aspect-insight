"""Collects the evaluation results written by the training notebooks into one JSON document for the dashboard."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from absa.constants import OUTPUT_DIR
from absa.reference_results import ORDER, TABLE9_ACOS, best_published

RESULTS = OUTPUT_DIR / "results"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _num(v):
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None


def collect() -> dict:
    t5, qwen = _json(RESULTS / "t5/results.json"), _json(RESULTS / "qwen/results.json")
    published = best_published(TABLE9_ACOS)
    domains = []
    for d in ORDER:
        row = {"domain": d, "paper_best": published[d][1], "paper_best_model": published[d][0]}
        for src, keys in ((t5, {"ours_in_domain": "t5_per_domain", "ours_all_domains": "t5_plain",
                                "ours_all_domains_tagged": "t5_domain"}),
                          (qwen, {"ours_all_domains_tagged": "qwen_domain"})):
            comp = {c["domain"]: c for c in (src or {}).get("comparison_acos", [])}
            for k, name in keys.items():
                row[name] = _num(comp.get(d, {}).get(k))
        domains.append(row)

    scores = _csv(RESULTS / "t5/scores_all_runs.csv") + _csv(RESULTS / "qwen/scores_all_runs.csv")
    overall = {}
    for label, path, exp in (("Flan-T5 + domain", "t5", "all_domains_tagged"), ("Flan-T5, no domain", "t5", "all_domains"),
                             ("Qwen2.5-1.5B LoRA + domain", "qwen", "all_domains_tagged")):
        rows = [r for r in _csv(RESULTS / f"{path}/scores_all_runs.csv") if r["experiment"] == exp and r["domain"] == "ALL"]
        if rows:
            overall[label] = {t: round(sum(float(r[t]) for r in rows) / len(rows), 2)
                              for t in ("AE", "ASPE", "CS", "AOS", "ACS", "ACOS")}

    speed = {}
    for label, path, exp in (("Flan-T5 + domain", "t5", "all_domains_tagged"),
                             ("Qwen2.5-1.5B LoRA + domain", "qwen", "all_domains_tagged")):
        ms = [m["ms_per_sentence"] for m in (_json(p) for p in (OUTPUT_DIR / f"runs/{path}/{exp}/model").glob(
            "seed*/metrics.json")) if m]
        if ms:
            speed[label] = round(sum(ms) / len(ms), 1)

    prompting = [{"run": r["run"], "model": r["model"], "shots": int(r["shots"]), "selection": r["selection"],
                  "acos": _num(r["ACOS_F1"]), "aos": _num(r["AOS_F1"]), "ms": _num(r["ms_per_sentence"]),
                  "malformed": int(float(r["malformed_segments"]))}
                 for r in _csv(RESULTS / "prompting/prompting.csv")]

    decoding = [{"strategy": r["strategy"], "acos": round(r["ACOS_F1"], 2), "precision": round(r["ACOS_P"], 2),
                 "recall": round(r["ACOS_R"], 2), "ms": round(r["ms_per_sentence"], 1)}
                for r in (_json(RESULTS / "t5/decoding_ablation.json") or [])]

    cls = _json(RESULTS / "classifiers/results.json") or {}
    names = {"none": "No handling", "class_weights": "Class weights", "oversample": "Random oversampling",
             "focal": "Focal loss", "bagging": "Balanced bagging (5 models)", "bagging_single": "Bagging, one member",
             "augment": "LLM Neutral data (verified)", "augment_noverify": "LLM Neutral data (not verified)"}
    classifiers = [{"method": names.get(r["method"], r["method"]), "key": r["method"],
                    "macro_f1": _num(r["macro_f1_mean"]), "macro_f1_std": _num(r.get("macro_f1_std")),
                    "neutral_f1": _num(r["neu_f1_mean"]), "accuracy": _num(r["accuracy_mean"]),
                    "ece": _num(r["ece_mean"]), "ece_scaled": _num(r.get("ece_scaled_mean")),
                    "ms": _num(r["ms_per_pair_mean"]), "models": int(r["models_mean"])}
                   for r in cls.get("summary", [])]

    wrong = [{"model": "One model, no domain" if r["experiment"] == "all_domains" else "One model + domain",
              "domain": r["domain"], "share": _num(r["wrong_domain_share"])}
             for r in _csv(RESULTS / "t5/wrong_domain_categories.csv")]
    wrong_mean = {}
    for r in wrong:
        wrong_mean.setdefault((r["model"], r["domain"]), []).append(r["share"])
    wrong_domain = [{"model": m, "domain": d, "share": round(sum(v) / len(v), 2)} for (m, d), v in wrong_mean.items()]

    errors = (t5 or {}).get("errors")
    return {"domains": domains, "overall": overall, "speed_ms": speed, "prompting": prompting, "decoding": decoding,
            "classifiers": classifiers, "wrong_domain": wrong_domain, "errors": errors,
            "recall_by_group": {"Flan-T5, no domain": (t5 or {}).get("recall_by_group"),
                                "Qwen2.5-1.5B LoRA + domain": (qwen or {}).get("recall_by_group")},
            "classifier_test_pairs": cls.get("n_test"), "available": bool(t5)}
