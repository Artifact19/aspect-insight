"""Inference-only evaluation of Constrained Domain Decoding on MEMD-ABSA Test (seed 42).

Evaluates `t5_plain` and `t5_domain` with constrained decoding OFF vs ON across all 3,583
official test sentences, measuring overall ACOS F1, Laptop ACOS F1, wrong-domain category share,
malformed segments, and generation latency. Zero retraining required.

Usage:
    python scripts/evaluate_constrained.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from absa.constants import DOMAINS, MODELS_DIR, OUTPUT_DIR, PROCESSED_DIR  # noqa: E402
from absa.constrained import DomainCategoryConstraint  # noqa: E402
from absa.data import CategoryVocab, category_to_text, load_sentences, parse, quads_of  # noqa: E402
from absa.inference import Generator, default_specs  # noqa: E402
from absa.metrics import extraction_scores  # noqa: E402
from absa.utils import free_memory, get_device, save_json  # noqa: E402


def evaluate_model(gen: Generator, test_by_domain: dict[str, list[dict]],
                   domain_cats: dict[str, set[str]], vocab: CategoryVocab,
                   constrained: bool) -> dict:
    all_gold, all_pred = [], []
    by_domain = {}
    total_ms = 0.0
    total_sents = 0
    total_malformed = 0

    vocab_size = getattr(gen.model.config, "vocab_size", len(gen.tokenizer))
    for d in DOMAINS:
        sents = test_by_domain[d]
        texts = [s["text"] for s in sents]
        constraint = DomainCategoryConstraint(gen.tokenizer, domain_cats[d], vocab_size) if constrained else None
        outputs, ms_per = gen.generate(
            texts, d, decoding="greedy", batch_size=64,
            prefix_allowed_tokens_fn=constraint.prefix_allowed_tokens_fn if constraint else None,
        )
        total_ms += ms_per * len(sents)
        total_sents += len(sents)
        parsed = [parse(o, vocab) for o in outputs]
        preds = [p[0] for p in parsed]
        malformed = sum(p[1] for p in parsed)
        total_malformed += malformed
        gold = [quads_of(s) for s in sents]
        n_pred_quads = sum(len(p) for p in preds)
        wrong = sum(category_to_text(q.category) not in domain_cats[d] for p in preds for q in p)
        scores = extraction_scores(gold, preds, {"ACOS": "acos", "AOS": "aos", "CS": "cs"})
        by_domain[d] = {
            "acos_f1": round(100 * scores["ACOS"]["f1"], 2),
            "aos_f1": round(100 * scores["AOS"]["f1"], 2),
            "cs_f1": round(100 * scores["CS"]["f1"], 2),
            "wrong_domain_share": round(100 * wrong / max(1, n_pred_quads), 2),
            "malformed": malformed,
            "sentences": len(sents),
        }
        all_gold.extend(gold)
        all_pred.extend(preds)

    overall = extraction_scores(all_gold, all_pred, {"ACOS": "acos", "AOS": "aos", "CS": "cs"})
    total_wrong = sum(
        category_to_text(q.category) not in domain_cats[d]
        for d in DOMAINS
        for p in all_pred[sum(len(test_by_domain[x]) for x in DOMAINS[:DOMAINS.index(d)]):
                          sum(len(test_by_domain[x]) for x in DOMAINS[:DOMAINS.index(d) + 1])]
        for q in p
    )
    total_quads = sum(len(p) for p in all_pred)
    return {
        "constrained": constrained,
        "overall_acos_f1": round(100 * overall["ACOS"]["f1"], 2),
        "overall_aos_f1": round(100 * overall["AOS"]["f1"], 2),
        "overall_cs_f1": round(100 * overall["CS"]["f1"], 2),
        "wrong_domain_share": round(100 * total_wrong / max(1, total_quads), 2),
        "malformed": total_malformed,
        "ms_per_sentence": round(total_ms / max(1, total_sents), 2),
        "by_domain": by_domain,
    }


def main():
    device = get_device()
    vocab = CategoryVocab.load(PROCESSED_DIR / "categories.json")
    domain_cats = {
        d: {category_to_text(q.category) for s in load_sentences([d], "Train") for q in quads_of(s)}
        for d in DOMAINS
    }
    test_by_domain = {d: load_sentences([d], "Test") for d in DOMAINS}
    specs = {s.key: s for s in default_specs(MODELS_DIR)}

    results = {"device": str(device), "runs": []}
    for key in ("t5_plain", "t5_domain"):
        spec = specs[key]
        print(f"Evaluating {spec.label} on {device}...")
        gen = Generator(spec, device)
        off = evaluate_model(gen, test_by_domain, domain_cats, vocab, constrained=False)
        on = evaluate_model(gen, test_by_domain, domain_cats, vocab, constrained=True)
        entry = {"key": key, "label": spec.label, "unconstrained": off, "constrained": on}
        results["runs"].append(entry)
        print(f"  OFF -> ACOS {off['overall_acos_f1']:.2f} | Laptop {off['by_domain']['Laptop']['acos_f1']:.2f} "
              f"| Laptop wrong-domain {off['by_domain']['Laptop']['wrong_domain_share']:.2f}%")
        print(f"  ON  -> ACOS {on['overall_acos_f1']:.2f} | Laptop {on['by_domain']['Laptop']['acos_f1']:.2f} "
              f"| Laptop wrong-domain {on['by_domain']['Laptop']['wrong_domain_share']:.2f}%")
        del gen
        free_memory()

    out_dir = OUTPUT_DIR / "results" / "t5"
    out_dir.mkdir(parents=True, exist_ok=True)
    save_json(results, out_dir / "constrained_decoding.json")

    lines = [
        "# Constrained Domain Decoding Evaluation (Seed 42, Zero Retraining)",
        "",
        "| Model | Mode | Overall ACOS F1 | Laptop ACOS F1 | Laptop Wrong-Domain (%) | Overall Wrong-Domain (%) | ms/sentence |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in results["runs"]:
        for tag, m in (("Unconstrained", r["unconstrained"]), ("Constrained", r["constrained"])):
            lines.append(
                f"| {r['label']} | {tag} | {m['overall_acos_f1']:.2f} | "
                f"{m['by_domain']['Laptop']['acos_f1']:.2f} | "
                f"{m['by_domain']['Laptop']['wrong_domain_share']:.2f} | "
                f"{m['wrong_domain_share']:.2f} | {m['ms_per_sentence']:.2f} |"
            )
    (out_dir / "constrained_decoding.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved {out_dir / 'constrained_decoding.json'}")


if __name__ == "__main__":
    main()
