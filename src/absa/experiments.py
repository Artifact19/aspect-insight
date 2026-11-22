"""Expansion of experiment definitions in the generator configs into individual training runs."""
from __future__ import annotations

from .constants import DOMAINS


def expand(experiment: dict) -> list[tuple[str, list[str], list[str]]]:
    """(run name, training domains, test domains) for every model an experiment needs."""
    if experiment.get("per_domain"):
        return [(d, [d], [d]) for d in DOMAINS]
    if experiment.get("leave_one_out"):
        return [(f"without_{d}", [x for x in DOMAINS if x != d], [d]) for d in DOMAINS]
    return [("model", experiment["train"], experiment["test"])]


def limited(rows: list, n: int | None) -> list:
    return rows if not n else rows[:n]
