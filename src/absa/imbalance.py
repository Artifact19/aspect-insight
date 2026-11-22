"""Class-imbalance handling: loss functions and resampling of training pairs."""
from __future__ import annotations

from typing import Sequence

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

N_CLASSES = 3


def class_counts(labels: Sequence[int], n_classes: int = N_CLASSES) -> np.ndarray:
    return np.bincount(np.asarray(labels, dtype=int), minlength=n_classes)


def balanced_class_weights(labels: Sequence[int], clamp: float | None = 3.0) -> torch.Tensor:
    """Weights n / (k * n_c), optionally clamped from above to avoid extreme weights for very rare classes."""
    counts = class_counts(labels).astype(float)
    weights = len(labels) / (len(counts) * np.maximum(counts, 1.0))
    if clamp is not None:
        weights = np.minimum(weights, clamp)
    return torch.tensor(weights, dtype=torch.float)


class FocalLoss(nn.Module):
    """Focal loss (Lin et al., 2017): cross-entropy scaled by (1 - p_t)^gamma to down-weight easy examples."""

    def __init__(self, gamma: float = 2.0, weight: torch.Tensor | None = None):
        super().__init__()
        self.gamma = gamma
        self.register_buffer("weight", weight if weight is not None else None)

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        log_p = F.log_softmax(logits, dim=-1)
        log_pt = log_p.gather(1, target[:, None]).squeeze(1)
        loss = -((1 - log_pt.exp()) ** self.gamma) * log_pt
        if self.weight is not None:
            loss = loss * self.weight[target]
        return loss.mean()


def build_loss(method: str, labels: Sequence[int], cfg: dict) -> nn.Module:
    if method in ("class_weights", "augment", "augment_noverify"):
        return nn.CrossEntropyLoss(weight=balanced_class_weights(labels, cfg.get("weight_clamp", 3.0)))
    if method == "focal":
        return FocalLoss(gamma=cfg.get("focal_gamma", 2.0))
    return nn.CrossEntropyLoss()


def random_oversample(rows: list[dict], ratio: float, rng: np.random.Generator) -> list[dict]:
    """Duplicate minority-class rows at random until each class has at least ratio x the majority-class count."""
    labels = np.array([r["label"] for r in rows])
    counts = class_counts(labels)
    target = int(ratio * counts.max())
    out = list(rows)
    for c in range(len(counts)):
        idx = np.flatnonzero(labels == c)
        if 0 < len(idx) < target:
            out.extend(rows[i] for i in rng.choice(idx, target - len(idx), replace=True))
    return out


def bagging_partitions(rows: list[dict], n_members: int, rng: np.random.Generator,
                       majority_label: int | None = None) -> list[list[dict]]:
    """Balanced bagging without discarding data.

    The majority class is shuffled and split into n_members disjoint parts. Member k receives every
    minority-class row plus majority part k, so each majority row is used by exactly one member.
    """
    labels = np.array([r["label"] for r in rows])
    if majority_label is None:
        majority_label = int(np.argmax(class_counts(labels)))
    majority = rng.permutation(np.flatnonzero(labels == majority_label))
    minority = [r for r, y in zip(rows, labels) if y != majority_label]
    return [minority + [rows[i] for i in part] for part in np.array_split(majority, n_members)]


def oversample_conflicting(rows: list[dict], times: int) -> list[dict]:
    """Repeat rows from sentences with mixed sentiments; times=1 leaves the data unchanged."""
    if times <= 1:
        return list(rows)
    return list(rows) + [r for r in rows if r["is_conflicting"]] * (times - 1)
