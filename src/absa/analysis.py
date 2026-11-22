"""Error analysis for tuple extraction."""
from __future__ import annotations

from collections import Counter
from typing import Sequence

from .data import Quad

ERROR_TYPES = ("category", "opinion", "sentiment", "aspect found, several elements wrong", "aspect missed")


def _match_unmatched(gold: list[Quad], pred: list[Quad]) -> tuple[list[Quad], list[Quad]]:
    """Remove exact matches (as a multiset) and return the unmatched gold and predicted quadruples."""
    remaining = Counter(q.key() for q in pred)
    unmatched_gold = []
    for q in gold:
        if remaining[q.key()] > 0:
            remaining[q.key()] -= 1
        else:
            unmatched_gold.append(q)
    unmatched_pred = []
    for q in pred:
        if remaining[q.key()] > 0:
            remaining[q.key()] -= 1
            unmatched_pred.append(q)
    return unmatched_gold, unmatched_pred


def error_taxonomy(gold: Sequence[Sequence[Quad]], pred: Sequence[Sequence[Quad]]) -> dict:
    """Classify every missed gold quadruple by the closest unmatched prediction in the same sentence.

    A miss is attributed to a single element when a prediction agrees on the other three. Predictions left
    unmatched after this step are counted as spurious.
    """
    counts = Counter()
    spurious = 0
    for g_list, p_list in zip(gold, pred):
        missed, extra = _match_unmatched(list(g_list), list(p_list))
        used = set()
        for g in missed:
            kind = "aspect missed"
            for j, p in enumerate(extra):
                if j in used:
                    continue
                if p.key("aos") == g.key("aos"):
                    kind = "category"
                elif p.key("acs") == g.key("acs"):
                    kind = "opinion"
                elif p.key("aco") == g.key("aco"):
                    kind = "sentiment"
                elif p.key("a") == g.key("a"):
                    kind = "aspect found, several elements wrong"
                else:
                    continue
                used.add(j)
                break
            counts[kind] += 1
        spurious += len(extra) - len(used)
    return {"missed_by_type": {t: counts[t] for t in ERROR_TYPES}, "spurious": spurious,
            "missed_total": sum(counts.values())}


def majority_vote(samples: Sequence[Sequence[Quad]], min_votes: int) -> list[Quad]:
    """Quadruples that appear in at least min_votes of the sampled outputs (self-consistency)."""
    votes = Counter(k for quads in samples for k in {q.key() for q in quads})
    first: dict[tuple, Quad] = {}
    for quads in samples:
        for q in quads:
            first.setdefault(q.key(), q)
    return [first[k] for k in first if votes[k] >= min_votes]


def recall_by_group(gold: Sequence[Sequence[Quad]], pred: Sequence[Sequence[Quad]]) -> dict:
    """ACOS recall split by whether the gold aspect / opinion is explicit or implicit."""
    hits, totals = Counter(), Counter()
    for g_list, p_list in zip(gold, pred):
        pred_keys = Counter(q.key() for q in p_list)
        for q in g_list:
            groups = ["implicit aspect" if q.implicit_aspect else "explicit aspect",
                      "implicit opinion" if q.implicit_opinion else "explicit opinion"]
            found = pred_keys[q.key()] > 0
            if found:
                pred_keys[q.key()] -= 1
            for grp in groups:
                totals[grp] += 1
                hits[grp] += found
    return {g: {"recall": hits[g] / totals[g], "n": totals[g]} for g in sorted(totals)}
