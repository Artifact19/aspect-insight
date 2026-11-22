import numpy as np
import pytest
import torch
import torch.nn.functional as F

from absa.imbalance import (FocalLoss, bagging_partitions, balanced_class_weights, class_counts, oversample_conflicting,
                            random_oversample)


def make_rows(neg=20, neu=3, pos=77):
    labels = [0] * neg + [1] * neu + [2] * pos
    return [{"id": i, "label": y, "is_conflicting": i % 10 == 0} for i, y in enumerate(labels)]


def test_bagging_uses_every_majority_row_exactly_once():
    rows = make_rows()
    parts = bagging_partitions(rows, 5, np.random.default_rng(0))
    majority_ids = [r["id"] for p in parts for r in p if r["label"] == 2]
    assert sorted(majority_ids) == [r["id"] for r in rows if r["label"] == 2]
    for p in parts:
        assert class_counts([r["label"] for r in p])[:2].tolist() == [20, 3]


def test_random_oversample_reaches_ratio():
    rows = random_oversample(make_rows(), 0.3, np.random.default_rng(0))
    counts = class_counts([r["label"] for r in rows])
    assert counts[2] == 77 and counts[0] >= 23 and counts[1] == int(0.3 * 77)


def test_class_weights_are_clamped():
    w = balanced_class_weights([r["label"] for r in make_rows()], clamp=3.0)
    assert w[1] == pytest.approx(3.0) and w[2] < 1.0


def test_focal_loss_reduces_to_cross_entropy():
    logits, target = torch.randn(8, 3), torch.randint(0, 3, (8,))
    assert FocalLoss(gamma=0.0)(logits, target).item() == pytest.approx(F.cross_entropy(logits, target).item(), abs=1e-6)
    assert FocalLoss(gamma=2.0)(logits, target) < F.cross_entropy(logits, target)


def test_oversample_conflicting():
    rows = make_rows()
    assert len(oversample_conflicting(rows, 1)) == 100
    assert len(oversample_conflicting(rows, 2)) == 110
