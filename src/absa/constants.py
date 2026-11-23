import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw" / "MEMD-ABSA"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
CAPTURES_DB = DATA_DIR / "captures.db"

# Training scripts write every run here (one folder per experiment and seed).
RUNS_DIR = Path(os.environ.get("ABSA_RUNS_DIR") or OUTPUT_DIR / "runs")


def _resolve_models_dir() -> Path:
    """The four trained models the app uses. Looked up in ABSA_MODELS_DIR, then models/ inside the project, then the
    submission's 2_Dataset_Models/Models folder next to the project."""
    env = os.environ.get("ABSA_MODELS_DIR")
    if env:
        return Path(env)
    for cand in (PROJECT_ROOT / "models", PROJECT_ROOT.parent / "2_Dataset_Models" / "Models"):
        if (cand / "Flan_T5_Domain").exists():
            return cand
    return PROJECT_ROOT / "models"


MODELS_DIR = _resolve_models_dir()

DOMAINS = ("Books", "Clothing", "Hotel", "Laptop", "Restaurant")
SPLITS = ("Train", "Dev", "Test")

SENTIMENTS = ("NEG", "NEU", "POS")
LABEL2ID = {s: i for i, s in enumerate(SENTIMENTS)}
ID2LABEL = {i: s for s, i in LABEL2ID.items()}
SENTIMENT_WORDS = {"NEG": "negative", "NEU": "neutral", "POS": "positive"}
WORD2SENTIMENT = {w: s for s, w in SENTIMENT_WORDS.items()}

NULL = "NULL"
MARK_OPEN, MARK_CLOSE = "<t>", "</t>"
