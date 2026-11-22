"""Evaluation metrics for tuple extraction and aspect-level sentiment classification."""
from __future__ import annotations

from collections import Counter
from typing import Callable, Sequence

import numpy as np
from scipy.stats import binomtest

from .data import Quad

EXTRACTION_TASKS = {
    "AE": "a",        # aspect terms
    "ASPE": "as",     # aspect-sentiment pairs
    "CS": "cs",       # category-sentiment pairs
    "AOS": "aos",     # aspect-opinion-sentiment triples
    "ACS": "acs",     # aspect-category-sentiment triples
    "ACOS": "acos",   # full quadruples
}


# ----------------------------------------------------------------------------------------------- extraction
def prf(gold: Sequence[Sequence[tuple]], pred: Sequence[Sequence[tuple]]) -> dict:
    """Micro precision, recall and F1 with exact matching; duplicates are counted as a multiset."""
    if len(gold) != len(pred):
        raise ValueError("gold and pred must have the same number of sentences")
    tp = n_gold = n_pred = 0
    for g, p in zip(gold, pred):
        g_count, p_count = Counter(g), Counter(p)
        tp += sum((g_count & p_count).values())
        n_gold += sum(g_count.values())
        n_pred += sum(p_count.values())
    precision = tp / n_pred if n_pred else 0.0
    recall = tp / n_gold if n_gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "n_gold": n_gold, "n_pred": n_pred}


def extraction_scores(gold: Sequence[Sequence[Quad]], pred: Sequence[Sequence[Quad]],
                      tasks: dict[str, str] = EXTRACTION_TASKS) -> dict[str, dict]:
    """Scores every sub-task from one set of predicted quadruples.

    Lower-order tuples are deduplicated per sentence, as a sentence that mentions an aspect twice
    with the same sentiment contains one aspect-sentiment pair.
    """
    out = {}
    for name, elements in tasks.items():
        g = [list(dict.fromkeys(q.key(elements) for q in qs)) for qs in gold]
        p = [list(dict.fromkeys(q.key(elements) for q in qs)) for qs in pred]
        out[name] = prf(g, p)
    return out


def sentence_correct(gold: Sequence[Sequence[Quad]], pred: Sequence[Sequence[Quad]],
                     elements: str = "acos") -> np.ndarray:
    """Per-sentence indicator that the predicted tuple set equals the gold tuple set."""
    return np.array([set(q.key(elements) for q in g) == set(q.key(elements) for q in p)
                     for g, p in zip(gold, pred)])


# ----------------------------------------------------------------------------------------------- classification
def confusion_matrix(y_true: Sequence[int], y_pred: Sequence[int], n_classes: int = 3) -> np.ndarray:
    """Rows are gold labels, columns are predicted labels."""
    y_true, y_pred = np.asarray(y_true, dtype=int), np.asarray(y_pred, dtype=int)
    return np.bincount(y_true * n_classes + y_pred, minlength=n_classes * n_classes).reshape(n_classes, n_classes)


def f1_per_class(y_true: Sequence[int], y_pred: Sequence[int], n_classes: int = 3) -> np.ndarray:
    """F1 for each class; 0 for a class that is neither present nor predicted."""
    cm = confusion_matrix(y_true, y_pred, n_classes)
    tp = np.diag(cm).astype(float)
    denom = cm.sum(0) + cm.sum(1)
    return np.divide(2 * tp, denom, out=np.zeros(n_classes), where=denom > 0)


def macro_f1(y_true: Sequence[int], y_pred: Sequence[int], n_classes: int = 3) -> float:
    """Macro-F1 over the classes present in the gold labels."""
    present = np.unique(np.asarray(y_true, dtype=int))
    return float(f1_per_class(y_true, y_pred, n_classes)[present].mean()) if len(present) else 0.0


def classification_scores(y_true: Sequence[int], y_pred: Sequence[int], n_classes: int = 3) -> dict:
    y_true, y_pred = np.asarray(y_true, dtype=int), np.asarray(y_pred, dtype=int)
    return {
        "accuracy": float((y_true == y_pred).mean()) if len(y_true) else 0.0,
        "macro_f1": macro_f1(y_true, y_pred, n_classes),
        "f1_per_class": [float(x) for x in f1_per_class(y_true, y_pred, n_classes)],
        "confusion": confusion_matrix(y_true, y_pred, n_classes).tolist(),
        "n": int(len(y_true)),
    }


def expected_calibration_error(probs: np.ndarray, y_true: Sequence[int], n_bins: int = 15) -> float:
    """Weighted mean gap between confidence and accuracy over equal-width confidence bins."""
    probs, y_true = np.asarray(probs), np.asarray(y_true)
    conf, pred = probs.max(1), probs.argmax(1)
    bins = np.minimum((conf * n_bins).astype(int), n_bins - 1)
    ece = 0.0
    for b in range(n_bins):
        mask = bins == b
        if mask.any():
            ece += mask.mean() * abs((pred[mask] == y_true[mask]).mean() - conf[mask].mean())
    return float(ece)


def apply_temperature(probs: np.ndarray, temperature: float) -> np.ndarray:
    """Rescales probabilities as softmax(log p / T), which equals softmax(logits / T)."""
    z = np.log(np.clip(np.asarray(probs, dtype=float), 1e-12, 1.0)) / temperature
    z -= z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


def fit_temperature(probs: np.ndarray, y_true: Sequence[int], bounds: tuple[float, float] = (0.05, 10.0)) -> float:
    """Temperature that minimises the negative log-likelihood of held-out labels."""
    from scipy.optimize import minimize_scalar
    y = np.asarray(y_true, dtype=int)
    nll = lambda t: -np.log(apply_temperature(probs, t)[np.arange(len(y)), y] + 1e-12).mean()  # noqa: E731
    return float(minimize_scalar(nll, bounds=bounds, method="bounded").x)


# ----------------------------------------------------------------------------------------------- significance
def mcnemar_exact(correct_a: Sequence[bool], correct_b: Sequence[bool]) -> dict:
    """Exact McNemar test on paired correctness indicators."""
    a, b = np.asarray(correct_a, dtype=bool), np.asarray(correct_b, dtype=bool)
    only_a, only_b = int(np.sum(a & ~b)), int(np.sum(~a & b))
    n = only_a + only_b
    p = 1.0 if n == 0 else float(binomtest(only_a, n, 0.5).pvalue)
    return {"only_a": only_a, "only_b": only_b, "p_value": p}


def bootstrap_ci(metric: Callable[[np.ndarray], float], n_items: int, n_boot: int = 1000,
                 alpha: float = 0.05, seed: int = 0) -> tuple[float, float]:
    """Percentile bootstrap interval; `metric` receives an index array that resamples the evaluation items."""
    rng = np.random.default_rng(seed)
    stats = [metric(rng.integers(0, n_items, n_items)) for _ in range(n_boot)]
    return float(np.quantile(stats, alpha / 2)), float(np.quantile(stats, 1 - alpha / 2))


def mean_std(values: Sequence[float]) -> tuple[float, float]:
    v = np.asarray(values, dtype=float)
    return float(v.mean()), float(v.std(ddof=1)) if len(v) > 1 else 0.0
