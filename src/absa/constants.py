from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw" / "MEMD-ABSA"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

DOMAINS = ("Books", "Clothing", "Hotel", "Laptop", "Restaurant")
SPLITS = ("Train", "Dev", "Test")

SENTIMENTS = ("NEG", "NEU", "POS")
LABEL2ID = {s: i for i, s in enumerate(SENTIMENTS)}
ID2LABEL = {i: s for s, i in LABEL2ID.items()}
SENTIMENT_WORDS = {"NEG": "negative", "NEU": "neutral", "POS": "positive"}
WORD2SENTIMENT = {w: s for s, w in SENTIMENT_WORDS.items()}

NULL = "NULL"
MARK_OPEN, MARK_CLOSE = "<t>", "</t>"
