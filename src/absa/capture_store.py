"""Local SQLite store for captured review sets and the reply / ticket drafts made from them.

Everything stays on this computer in `data/captures.db`: no accounts, no cloud database.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .constants import CAPTURES_DB

RE_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
RE_SPACE = re.compile(r"\s+")
# Text that review sites add around the review itself.
RE_BOILERPLATE = re.compile(r"\b(read more|show more|see more|helpful|report abuse|translate review)\b\.?$",
                            re.IGNORECASE)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_review_text(text: str) -> str:
    """Unescape HTML, drop links and trailing site buttons, collapse whitespace."""
    s = RE_URL.sub("", html.unescape(str(text or "")))
    s = RE_SPACE.sub(" ", s).strip()
    while True:
        t = RE_BOILERPLATE.sub("", s).strip()
        if t == s:
            return s
        s = t


def review_key(text: str, author: str = "") -> str:
    """Fingerprint used to drop the same review captured twice (pages often render a review more than once)."""
    norm = RE_SPACE.sub(" ", clean_review_text(text).lower())
    return hashlib.sha256(f"{norm}|{(author or '').strip().lower()}".encode("utf-8")).hexdigest()


RE_AMAZON_ASIN = re.compile(r"/(?:dp|gp/product|product-reviews)/([A-Z0-9]{10})", re.IGNORECASE)
RE_FLIPKART_PID = re.compile(r"[?&]pid=([A-Z0-9]+)", re.IGNORECASE)
# Sites whose path alone names the product or place; their query only holds paging, sorting or session values.
PATH_ONLY_HOSTS = ("zomato.", "goodreads.", "tripadvisor.", "booking.")
# Query parameters that never change which item a page is about (tracking, paging, sorting).
RE_IGNORED_PARAM = re.compile(r"^(utm(_\w+)?|ref|ref_|fbclid|gclid|msclkid|mc_[a-z]+|_ga|srsltid|"
                              r"page|pagenumber|p|sort|sortby|order|filter|lang|hl|currency)$", re.IGNORECASE)


def page_key(url: str) -> str:
    """The product or place a page is about, so reading the same thing again updates its report.

    Amazon pages share their ASIN, Flipkart pages their pid, and Zomato, Goodreads, Tripadvisor and Booking.com
    pages their path. Any other page is its host, path and the query parameters that can name an item (tracking,
    paging and sorting parameters dropped), so two different items on the same script never share a report.
    Empty for pasted text and demo files.
    """
    m = re.match(r"https?://(?:www\.|m\.)?([^/?#]+)([^?#]*)(?:\?([^#]*))?", (url or "").strip(), re.IGNORECASE)
    if not m:
        return ""
    host, path, query = m.group(1).lower(), m.group(2).rstrip("/"), m.group(3) or ""
    if "amazon." in host and (asin := RE_AMAZON_ASIN.search(url)):
        return f"{host}/asin/{asin.group(1).upper()}"
    if "flipkart." in host and (pid := RE_FLIPKART_PID.search(url)):
        return f"{host}/pid/{pid.group(1).upper()}"
    if "zomato." in host:
        path = re.sub(r"/(reviews|order|menu|photos|book)$", "", path)
    key = f"{host}{path.lower()}"
    if any(h in host for h in PATH_ONLY_HOSTS):
        return key
    params = sorted(p for p in query.split("&") if p and not RE_IGNORED_PARAM.match(p.partition("=")[0]))
    return f"{key}?{'&'.join(params)}" if params else key


def deduplicate(reviews: Sequence[dict]) -> tuple[list[dict], int]:
    """Cleaned, unique reviews and the number dropped as duplicates or too short."""
    kept, seen, skipped = [], set(), 0
    for r in reviews:
        text = clean_review_text(r.get("text", ""))
        key = review_key(text, r.get("author", ""))
        if len(text) < 5 or key in seen:
            skipped += 1
            continue
        seen.add(key)
        kept.append({**r, "text": text})
    return kept, skipped


SCHEMA = """
CREATE TABLE IF NOT EXISTS captures (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source TEXT NOT NULL,
    domain TEXT NOT NULL,
    created_at TEXT NOT NULL,
    raw_count INTEGER NOT NULL,
    review_count INTEGER NOT NULL,
    skipped INTEGER NOT NULL,
    summary_json TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
    id TEXT PRIMARY KEY,
    capture_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    target TEXT NOT NULL,
    source_review TEXT NOT NULL,
    policy_json TEXT NOT NULL,
    facts_json TEXT NOT NULL,
    draft_text TEXT NOT NULL,
    final_text TEXT NOT NULL,
    checks_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    decided_at TEXT
);
"""

LIST_FIELDS = ("id", "title", "source_url", "source", "domain", "created_at", "raw_count", "review_count", "skipped")


class CaptureStore:
    def __init__(self, db_path: Path = CAPTURES_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------ captures
    def find_by_page(self, source_url: str, domain: str) -> str | None:
        """Id of the latest report for the same product or place (see `page_key`) and domain, if any."""
        key = page_key(source_url)
        if not key:
            return None
        with self._connect() as conn:
            rows = conn.execute("SELECT id, source_url FROM captures WHERE domain = ? AND source_url != '' "
                                "ORDER BY created_at DESC", (domain,)).fetchall()
        return next((r["id"] for r in rows if page_key(r["source_url"]) == key), None)

    def save_capture(self, *, title: str, source_url: str, source: str, domain: str, raw_count: int,
                     review_count: int, skipped: int, payload: dict) -> dict:
        """Save a report. Reading the same page again replaces that page's report (same id, so links keep working)
        instead of adding another one; the result's `updated` says which happened."""
        existing = self.find_by_page(source_url, domain)
        cid = existing or uuid.uuid4().hex[:10]
        values = (title, source_url, source, domain, now_iso(), raw_count, review_count, skipped,
                  json.dumps(payload["summary"], ensure_ascii=False), json.dumps(payload, ensure_ascii=False))
        with self._connect() as conn:
            if existing:
                conn.execute("UPDATE captures SET title = ?, source_url = ?, source = ?, domain = ?, created_at = ?, "
                             "raw_count = ?, review_count = ?, skipped = ?, summary_json = ?, payload_json = ? "
                             "WHERE id = ?", (*values, cid))
            else:
                conn.execute("INSERT INTO captures VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (cid, *values))
        return {**self.get_capture(cid), "updated": bool(existing)}

    def list_captures(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(f"SELECT {', '.join(LIST_FIELDS)}, summary_json FROM captures "
                                "ORDER BY created_at DESC").fetchall()
        out = []
        for r in rows:
            s = json.loads(r["summary_json"])
            out.append({**{k: r[k] for k in LIST_FIELDS}, "opinions": s.get("opinions", 0),
                        "sentiment": s.get("sentiment", {}), "share": s.get("share", {})})
        return out

    def get_capture(self, capture_id: str) -> dict | None:
        with self._connect() as conn:
            r = conn.execute("SELECT * FROM captures WHERE id = ?", (capture_id,)).fetchone()
        if not r:
            return None
        return {**{k: r[k] for k in LIST_FIELDS}, **json.loads(r["payload_json"])}

    def update_payload(self, capture_id: str, **fields) -> None:
        """Add or replace fields of a saved capture (for example the written brief)."""
        with self._connect() as conn:
            r = conn.execute("SELECT payload_json FROM captures WHERE id = ?", (capture_id,)).fetchone()
            if r:
                payload = {**json.loads(r["payload_json"]), **fields}
                conn.execute("UPDATE captures SET payload_json = ? WHERE id = ?",
                             (json.dumps(payload, ensure_ascii=False), capture_id))

    def delete_capture(self, capture_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM captures WHERE id = ?", (capture_id,))
            conn.execute("DELETE FROM drafts WHERE capture_id = ?", (capture_id,))
        return cur.rowcount > 0

    # ------------------------------------------------------------------ drafts
    def save_draft(self, *, capture_id: str, kind: str, target: str, source_review: str, policy: dict,
                   facts: Sequence[str], text: str, checks: dict) -> dict:
        did = uuid.uuid4().hex[:10]
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO drafts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, NULL)",
                (did, capture_id, kind, target, source_review, json.dumps(policy), json.dumps(list(facts)),
                 text, text, json.dumps(checks), now_iso()))
        return self.get_draft(did)

    def decide_draft(self, draft_id: str, status: str, final_text: str | None = None) -> dict | None:
        if status not in ("approved", "rejected"):
            raise ValueError("status must be 'approved' or 'rejected'")
        current = self.get_draft(draft_id)
        if not current:
            return None
        with self._connect() as conn:
            conn.execute("UPDATE drafts SET status = ?, final_text = ?, decided_at = ? WHERE id = ?",
                         (status, final_text if final_text is not None else current["draft_text"], now_iso(),
                          draft_id))
        return self.get_draft(draft_id)

    def get_draft(self, draft_id: str) -> dict | None:
        with self._connect() as conn:
            r = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        return self._draft(r) if r else None

    def list_drafts(self, capture_id: str | None = None) -> list[dict]:
        sql, args = "SELECT * FROM drafts", ()
        if capture_id:
            sql, args = sql + " WHERE capture_id = ?", (capture_id,)
        with self._connect() as conn:
            rows = conn.execute(sql + " ORDER BY created_at DESC", args).fetchall()
        return [self._draft(r) for r in rows]

    @staticmethod
    def _draft(r: sqlite3.Row) -> dict:
        return {"id": r["id"], "capture_id": r["capture_id"], "kind": r["kind"], "target": r["target"],
                "source_review": r["source_review"], "policy": json.loads(r["policy_json"]),
                "facts": json.loads(r["facts_json"]), "draft_text": r["draft_text"], "final_text": r["final_text"],
                "checks": json.loads(r["checks_json"]), "status": r["status"], "created_at": r["created_at"],
                "decided_at": r["decided_at"]}
