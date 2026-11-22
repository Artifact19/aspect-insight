"""Published results from Cai et al. (2023), MEMD-ABSA, arXiv:2306.16956 (micro-F1, %, mean of three seeds).

Table 9 uses the full test sets including implicit aspects and opinions, the same setting as this project.
Table 8 (cross-domain AOS) uses explicit examples only, so comparisons with it are approximate.
"""

ORDER = ("Books", "Clothing", "Hotel", "Restaurant", "Laptop")


def _rows(values: dict[str, tuple]) -> dict[str, dict[str, float]]:
    return {model: dict(zip(ORDER, scores)) for model, scores in values.items()}


TABLE9_ACOS = _rows({
    "GAS-BART (extraction)": (36.60, 34.29, 64.00, 51.08, 40.60),
    "BART-Paraphrase": (37.00, 37.00, 67.17, 52.47, 41.60),
    "BART-index": (36.99, 37.41, 65.42, 54.28, 39.53),
    "GAS (extraction)": (38.94, 40.20, 64.44, 54.20, 43.15),
    "T5-Paraphrase": (39.00, 41.26, 66.89, 56.31, 43.57),
    "T5-index": (41.71, 37.55, 69.22, 56.49, 40.38),
})

TABLE9_AOS = _rows({
    "GAS-BART (extraction)": (47.10, 64.32, 71.60, 57.48, 63.74),
    "BART-Paraphrase": (50.56, 64.60, 75.18, 59.23, 65.31),
    "BART-index": (50.06, 67.32, 77.27, 63.26, 65.80),
    "GAS (extraction)": (50.79, 66.52, 72.59, 62.95, 67.22),
    "T5-Paraphrase": (52.00, 68.45, 75.84, 63.07, 67.88),
    "T5-index": (53.46, 69.63, 77.98, 65.12, 66.06),
})

# T5-Paraphrase, AOS, explicit examples only: trained on the other four domains, tested on the named domain.
TABLE8_AOS_LEAVE_ONE_OUT = {"Books": 51.78, "Clothing": 60.39, "Hotel": 72.60, "Restaurant": 61.47, "Laptop": 61.77}
# T5-Paraphrase, AOS, explicit examples only: trained and tested on the same domain.
TABLE8_AOS_IN_DOMAIN = {"Books": 58.68, "Clothing": 73.56, "Hotel": 79.21, "Restaurant": 67.15, "Laptop": 72.18}


def best_published(table: dict[str, dict[str, float]]) -> dict[str, tuple[str, float]]:
    """Best published model and score per domain."""
    return {d: max(((m, s[d]) for m, s in table.items()), key=lambda x: x[1]) for d in ORDER}
