"""FastAPI application: quadruple extraction, batch insights, model comparison and evaluation results.

Run from the project root:
    python -m uvicorn backend.app:app --port 8000
"""
from __future__ import annotations

import csv
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from absa.constants import DOMAINS  # noqa: E402
from absa.inference import MAX_SENTENCES, Analyzer  # noqa: E402
from backend.results import collect  # noqa: E402

EXAMPLES = {
    "Laptop": ["The battery life is stellar, but the plastic build feels cheap.",
               "Setup took five minutes and the keyboard is a joy to type on. The trackpad is okay.",
               "It overheats when gaming and customer support never answered my emails."],
    "Restaurant": ["The pasta was cold and the waiter was rude, but the dessert saved the evening.",
                   "Great margaritas, fair food, and the prices are reasonable for the area.",
                   "We waited forty minutes for a table and nobody apologised."],
    "Hotel": ["The room was spotless and the staff were lovely, but breakfast was overpriced.",
              "A little cramped with four people but doable.",
              "Perfect location near the station, although the walls are thin and it gets noisy at night."],
    "Books": ["The plot drags in the middle, but the characters are wonderfully written.",
              "A gripping thriller that I could not put down.",
              "The author clearly did her research, though the ending felt rushed."],
    "Clothing": ["The fabric is soft and the colour is exactly as pictured, but it runs small.",
                 "These shoes are comfortable enough for all-day walking.",
                 "The zipper broke after two washes."],
}

state: dict = {}
lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    state["analyzer"] = Analyzer()
    yield
    state.clear()


app = FastAPI(title="Aspect-Based Sentiment Analysis", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    domain: str


class BatchRequest(BaseModel):
    reviews: list[str] = Field(..., min_length=1, max_length=2000)
    domain: str


class Batch(BaseModel):
    label: str = Field(..., min_length=1, max_length=80)
    summary: dict


class SummaryRequest(BaseModel):
    domain: str
    batches: list[Batch] = Field(..., min_length=1, max_length=2)


class CompareRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    domain: str
    models: list[str] = Field(default_factory=lambda: ["t5_domain", "t5_plain", "qwen_domain"])
    decoding: str = "greedy"
    temperature: float = Field(0.7, ge=0.05, le=2.0)
    top_p: float = Field(0.9, gt=0.0, le=1.0)


def analyzer() -> Analyzer:
    if "analyzer" not in state:
        raise HTTPException(503, "models are still loading")
    return state["analyzer"]


def check_domain(domain: str) -> None:
    if domain not in DOMAINS:
        raise HTTPException(422, f"domain must be one of {', '.join(DOMAINS)}")


@app.get("/api/health")
def health():
    a = analyzer()
    return {"status": "ok", "device": str(a.device), "models": a.available(),
            "classifier_temperature": round(a.classifier.temperature, 3), "max_sentences": MAX_SENTENCES}


@app.get("/api/domains")
def domains():
    a = analyzer()
    return [{"name": d, "examples": EXAMPLES[d], "categories": len(a.domain_categories[d])} for d in DOMAINS]


@app.get("/api/samples")
def samples(domain: str, n: int = 50, seed: int = 0):
    check_domain(domain)
    return {"domain": domain, "reviews": analyzer().samples(domain, max(1, min(n, 300)), seed)}


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    check_domain(req.domain)
    with lock:
        return analyzer().analyze([req.text], req.domain)


@app.post("/api/batch")
def batch(req: BatchRequest):
    check_domain(req.domain)
    reviews = [r.strip() for r in req.reviews if r and r.strip()]
    if not reviews:
        raise HTTPException(422, "no reviews given")
    with lock:
        result = analyzer().analyze(reviews, req.domain)
    result["reviews"] = len(reviews)
    return result


@app.post("/api/compare")
def compare(req: CompareRequest):
    check_domain(req.domain)
    a = analyzer()
    out = []
    for key in req.models:
        if key not in a.specs:
            raise HTTPException(422, f"unknown model {key}")
        try:
            with lock:
                r = a.analyze([req.text], req.domain, model=key, decoding=req.decoding, temperature=req.temperature,
                              top_p=req.top_p)
            out.append({"key": key, "label": a.specs[key].label, "note": a.specs[key].note, "result": r})
        except FileNotFoundError as e:
            out.append({"key": key, "label": a.specs[key].label, "error": str(e)})
    return {"domain": req.domain, "decoding": req.decoding, "models": out}


DEMO_DIR = ROOT / "data" / "demo"
DEMO_DOMAINS = {"restaurant": "Restaurant", "laptop": "Laptop", "hotel": "Hotel", "clothing": "Clothing",
                "books": "Books"}


def demo_files() -> list[dict]:
    out = []
    for path in sorted(DEMO_DIR.glob("*.csv")):
        with path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            continue
        domain = DEMO_DOMAINS.get(path.stem.split("_")[0])
        out.append({"name": path.stem, "domain": domain, "label": rows[0].get("business", path.stem),
                    "reviews": len(rows), "rows": rows})
    return out


@app.get("/api/demo")
def demo_list():
    return [{k: v for k, v in d.items() if k != "rows"} for d in demo_files()]


@app.get("/api/demo/{name}")
def demo_file(name: str):
    for d in demo_files():
        if d["name"] == name:
            return {"name": name, "domain": d["domain"], "label": d["label"],
                    "reviews": [r["review"] for r in d["rows"] if r.get("review")]}
    raise HTTPException(404, f"no demo file {name}")


@app.post("/api/summary")
def summary(req: SummaryRequest):
    check_domain(req.domain)
    with lock:
        return analyzer().summary([b.model_dump() for b in req.batches], req.domain)


@app.get("/api/results")
def results():
    return collect()


DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="site")
