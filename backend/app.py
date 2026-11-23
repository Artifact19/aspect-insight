"""FastAPI service: quadruple extraction, captured review reports, grounded Q&A, reply drafts and evaluation results.

Run from the project folder:
    python -m uvicorn backend.app:app --port 8000
"""
from __future__ import annotations

import csv
import re
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from absa.actions import answer_review_question, draft_issue_ticket, draft_owner_reply  # noqa: E402
from absa.capture_store import CaptureStore, deduplicate  # noqa: E402
from absa.constants import CAPTURES_DB, DOMAINS, MODELS_DIR  # noqa: E402
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
    state["store"] = CaptureStore(CAPTURES_DB)
    state["analyzer"] = Analyzer()
    yield
    state.clear()


app = FastAPI(title="Aspect Insight", version="3.0.0", lifespan=lifespan)
# The Chrome extension calls the API from review pages, so other origins must be allowed. The server only listens on
# 127.0.0.1, so nothing outside this computer can reach it.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---------------------------------------------------------------------- request bodies
class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)
    domain: str
    constrained: bool = False


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
    constrained: bool = False


class CapturedReview(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    author: str = ""
    date: str = ""
    rating: float | None = None
    dom_id: str = ""


class CaptureRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    source_url: str = ""
    source: str = "web"
    domain: str
    reviews: list[CapturedReview] = Field(..., min_length=1, max_length=300)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)


class DraftRequest(BaseModel):
    capture_id: str
    kind: str = Field(..., pattern="^(reply|ticket)$")
    topic: str = ""
    review_index: int | None = None
    policy: dict = Field(default_factory=lambda: {"no_refund": True, "no_discount": True, "no_replacement": True})


class DecisionRequest(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    final_text: str | None = None


# ---------------------------------------------------------------------- helpers
def analyzer() -> Analyzer:
    if "analyzer" not in state:
        raise HTTPException(503, "models are still loading")
    return state["analyzer"]


def store() -> CaptureStore:
    if "store" not in state:
        state["store"] = CaptureStore(CAPTURES_DB)
    return state["store"]


def check_domain(domain: str) -> None:
    if domain not in DOMAINS:
        raise HTTPException(422, f"domain must be one of {', '.join(DOMAINS)}")


def short_title(title: str, limit: int = 50) -> str:
    """Product name without the specification list shops append ("Apple MacBook Air: M5 chip, 16GB ..." -> "Apple
    MacBook Air"), so the written summary stays readable."""
    head = re.split(r"\s*[:|(\[,–—]\s*|\s+-\s+", title.strip(), maxsplit=1)[0].strip() or title.strip()
    if len(head) > limit:
        head = head[:limit].rsplit(" ", 1)[0]
    return re.sub(r"(\s+(with|and|for|of|the|in|by|to))+$", "", head, flags=re.IGNORECASE)


def capture_or_404(capture_id: str) -> dict:
    cap = store().get_capture(capture_id)
    if not cap:
        raise HTTPException(404, f"no capture {capture_id}")
    return cap


# ---------------------------------------------------------------------- models and single reviews
@app.get("/api/health")
def health():
    a = analyzer()
    return {"status": "ok", "device": str(a.device), "models": a.available(), "models_dir": str(MODELS_DIR),
            "classifier_temperature": round(a.classifier.temperature, 3), "max_sentences": MAX_SENTENCES,
            "captures": len(store().list_captures())}


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
        return analyzer().analyze([req.text], req.domain, constrained=req.constrained)


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
    """Model lab: one sentence through several generators."""
    check_domain(req.domain)
    a = analyzer()
    out = []
    for key in req.models:
        if key not in a.specs:
            raise HTTPException(422, f"unknown model {key}")
        try:
            with lock:
                r = a.analyze([req.text], req.domain, model=key, decoding=req.decoding, temperature=req.temperature,
                              top_p=req.top_p, constrained=req.constrained)
            out.append({"key": key, "label": a.specs[key].label, "note": a.specs[key].note, "result": r})
        except FileNotFoundError as e:
            out.append({"key": key, "label": a.specs[key].label, "error": str(e)})
    return {"domain": req.domain, "decoding": req.decoding, "constrained": req.constrained, "models": out}


@app.post("/api/summary")
def summary(req: SummaryRequest):
    check_domain(req.domain)
    with lock:
        return analyzer().summary([b.model_dump() for b in req.batches], req.domain)


@app.get("/api/results")
def results():
    return collect()


# ---------------------------------------------------------------------- demo files (simulated reviews)
DEMO_DIR = ROOT / "data" / "demo"
DEMO_DOMAINS = {"restaurant": "Restaurant", "laptop": "Laptop", "hotel": "Hotel", "clothing": "Clothing",
                "books": "Books"}


def demo_files() -> list[dict]:
    out = []
    for path in sorted(DEMO_DIR.glob("*.csv")):
        with path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if rows:
            out.append({"name": path.stem, "domain": DEMO_DOMAINS.get(path.stem.split("_")[0]),
                        "label": rows[0].get("business", path.stem), "reviews": len(rows), "rows": rows})
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


# ---------------------------------------------------------------------- captures
@app.post("/api/captures")
def create_capture(req: CaptureRequest):
    """Analyse a set of reviews (from the Chrome extension, pasted text or a demo file) and save it as a report."""
    check_domain(req.domain)
    raw = [r.model_dump() for r in req.reviews]
    reviews, skipped = deduplicate(raw)
    if not reviews:
        raise HTTPException(422, "no usable reviews after removing duplicates and empty text")
    with lock:
        analysis = analyzer().analyze([r["text"] for r in reviews], req.domain)

    quads_by_review: dict[int, list[dict]] = {}
    for sent in analysis["sentences"]:
        quads_by_review.setdefault(sent["review"], []).extend(sent["quads"])
    records, page_marks = [], []
    for i, r in enumerate(reviews):
        quads = quads_by_review.get(i, [])
        records.append({"index": i, "text": r["text"], "author": r.get("author", ""), "date": r.get("date", ""),
                        "rating": r.get("rating"), "dom_id": r.get("dom_id", ""), "quads": quads})
        if r.get("dom_id") and quads:
            page_marks.append({"dom_id": r["dom_id"], "quads": [
                {k: q.get(k) for k in ("aspect", "opinion", "category_text", "sentiment", "confidence")}
                for q in quads]})

    payload = {"sentences": analysis["sentences"], "summary": analysis["summary"], "timing": analysis["timing"],
               "model": analysis["model"], "reviews": records, "page_marks": page_marks, "brief": None}
    return store().save_capture(title=req.title.strip(), source_url=req.source_url.strip(),
                                source=req.source.strip().lower() or "web", domain=req.domain, raw_count=len(raw),
                                review_count=len(reviews), skipped=skipped, payload=payload)


@app.get("/api/captures")
def list_captures():
    return store().list_captures()


@app.get("/api/captures/{capture_id}")
def get_capture(capture_id: str):
    return capture_or_404(capture_id)


@app.delete("/api/captures/{capture_id}")
def delete_capture(capture_id: str):
    if not store().delete_capture(capture_id):
        raise HTTPException(404, f"no capture {capture_id}")
    return {"deleted": capture_id}


@app.post("/api/captures/{capture_id}/brief")
def capture_brief(capture_id: str, refresh: bool = False):
    """Grounded three-sentence brief for a capture, written once and kept with it."""
    cap = capture_or_404(capture_id)
    if cap.get("brief") and not refresh:
        return cap["brief"]
    with lock:
        brief = analyzer().summary([{"label": short_title(cap["title"]), "summary": cap["summary"]}], cap["domain"])
    store().update_payload(capture_id, brief=brief)
    return brief


@app.post("/api/captures/{capture_id}/ask")
def ask(capture_id: str, req: AskRequest):
    """Answer a question about one capture from its extracted opinions, citing the reviews used."""
    cap = capture_or_404(capture_id)
    with lock:
        return answer_review_question(analyzer().writer(), question=req.question.strip(), capture=cap)


# ---------------------------------------------------------------------- reply and ticket drafts (human approves)
@app.post("/api/drafts")
def create_draft(req: DraftRequest):
    cap = capture_or_404(req.capture_id)
    if req.kind == "reply":
        reviews = cap.get("reviews") or []
        if req.review_index is not None:
            review = next((r for r in reviews if r["index"] == req.review_index), None)
        else:
            review = next((r for r in reviews if any(q["sentiment"] == "negative" for q in r["quads"])),
                          reviews[0] if reviews else None)
        if not review:
            raise HTTPException(422, "this capture has no reviews")
        with lock:
            res = draft_owner_reply(analyzer().writer(), review_text=review["text"], quads=review["quads"],
                                    domain=cap["domain"], business_name=cap["title"], policy=req.policy)
        target, source = f"Review {review['index'] + 1}", review["text"]
    else:
        topics = cap["summary"].get("entities") or []
        if req.topic:
            row = next((e for e in topics if e["name"].lower() == req.topic.lower()), None)
        else:
            row = max((e for e in topics if e["negative"]), key=lambda e: e["negative"], default=None)
        if not row:
            raise HTTPException(422, "this capture has no complaint topic")
        with lock:
            res = draft_issue_ticket(analyzer().writer(), entity_row=row, domain=cap["domain"],
                                     product_name=cap["title"], policy=req.policy)
        target, source = row["name"], (row.get("examples", {}).get("negative") or [""])[0]
    return store().save_draft(capture_id=cap["id"], kind=req.kind, target=target, source_review=source,
                              policy=req.policy, facts=res["facts"], text=res["draft"], checks=res["guardrail"])


@app.post("/api/drafts/{draft_id}/decide")
def decide_draft(draft_id: str, req: DecisionRequest):
    updated = store().decide_draft(draft_id, req.status, req.final_text)
    if not updated:
        raise HTTPException(404, f"no draft {draft_id}")
    return updated


@app.get("/api/drafts")
def list_drafts(capture_id: str | None = None):
    return store().list_drafts(capture_id)


# ---------------------------------------------------------------------- web app
DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    @app.get("/admin")
    @app.get("/admin/")
    def admin_page():
        return FileResponse(DIST / "index.html")

    app.mount("/", StaticFiles(directory=DIST, html=True), name="site")
