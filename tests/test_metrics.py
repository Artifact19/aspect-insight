import numpy as np
import pytest

from absa.data import NULL, Quad
from absa.metrics import (apply_temperature, bootstrap_ci, classification_scores, extraction_scores, fit_temperature,
                          macro_f1, mcnemar_exact, prf, sentence_correct)

GOLD = [[Quad("food", "Food#Quality", "great", "POS"), Quad("staff", "Service#General", "rude", "NEG")],
        [Quad(NULL, "Restaurant#Prices", "pricey", "NEG")]]


def test_perfect_prediction_scores_one():
    scores = extraction_scores(GOLD, GOLD)
    assert all(s["f1"] == 1.0 for s in scores.values())


def test_partial_prediction():
    pred = [[Quad("Food", "food#quality", "great", "POS"), Quad("staff", "Service#General", "rude", "POS")], []]
    scores = extraction_scores(GOLD, pred)
    assert scores["ACOS"]["tp"] == 1 and scores["ACOS"]["n_pred"] == 2 and scores["ACOS"]["n_gold"] == 3
    assert scores["ACOS"]["f1"] == pytest.approx(2 * 0.5 * (1 / 3) / (0.5 + 1 / 3))
    assert scores["AE"]["tp"] == 2
    assert list(sentence_correct(GOLD, pred)) == [False, False]


def test_prf_multiset():
    assert prf([[("a",), ("a",)]], [[("a",)]])["tp"] == 1


def test_macro_f1_ignores_absent_classes():
    assert macro_f1([0, 2, 2], [0, 2, 2]) == 1.0
    scores = classification_scores([0, 1, 2], [0, 2, 2])
    assert scores["confusion"][1][2] == 1 and scores["accuracy"] == pytest.approx(2 / 3)


def test_f1_matches_scikit_learn():
    from sklearn.metrics import f1_score
    rng = np.random.default_rng(0)
    y, p = rng.integers(0, 3, 500), rng.integers(0, 3, 500)
    p[:50] = y[:50]
    expected = f1_score(y, p, labels=[0, 1, 2], average=None, zero_division=0)
    assert classification_scores(y, p)["f1_per_class"] == pytest.approx(list(expected))
    assert macro_f1(y, p) == pytest.approx(f1_score(y, p, average="macro"))


def test_mcnemar():
    r = mcnemar_exact([True] * 10 + [False] * 2, [False] * 10 + [True] * 2)
    assert (r["only_a"], r["only_b"]) == (10, 2) and r["p_value"] < 0.05
    assert mcnemar_exact([True], [True])["p_value"] == 1.0


def test_bootstrap_ci_contains_point_estimate():
    correct = np.array([1] * 80 + [0] * 20)
    lo, hi = bootstrap_ci(lambda idx: correct[idx].mean(), len(correct), n_boot=300)
    assert lo < 0.8 < hi


def test_temperature_scaling():
    rng = np.random.default_rng(0)
    logits = rng.normal(size=(2000, 3)) * 2
    true_p = np.exp(logits) / np.exp(logits).sum(1, keepdims=True)
    y = np.array([rng.choice(3, p=row) for row in true_p])
    overconfident = apply_temperature(true_p, 0.5)
    assert apply_temperature(true_p, 1.0) == pytest.approx(true_p)
    assert (overconfident.argmax(1) == true_p.argmax(1)).all()
    assert fit_temperature(overconfident, y) == pytest.approx(2.0, rel=0.15)
