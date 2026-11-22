import React, { useEffect, useState } from "react";
import { SENTIMENT_COLORS, api, pct, titleCase } from "../lib.js";
import { Card, ErrorBox, Spinner } from "./ui.jsx";

export function DemoPicker({ onLoad, disabled, filterDomain }) {
  const [files, setFiles] = useState([]);
  useEffect(() => { api.demoList().then(setFiles).catch(() => setFiles([])); }, []);
  const shown = filterDomain ? files.filter((f) => f.domain === filterDomain) : files;
  if (!shown.length) return null;
  return (
    <select className="input w-auto py-2 text-sm" disabled={disabled} value=""
      onChange={async (e) => { if (e.target.value) onLoad(await api.demoFile(e.target.value)); }}>
      <option value="">Load a demo file…</option>
      {shown.map((f) => <option key={f.name} value={f.name}>{f.label} · {f.reviews} reviews</option>)}
    </select>
  );
}

export function Highlights({ summary, sentiment, title, subtitle, onShow, limit = 5 }) {
  const rows = (summary.entities || summary.categories).filter((c) => c[sentiment] > 0)
    .sort((a, b) => b[sentiment] - a[sentiment]).slice(0, limit);
  const color = SENTIMENT_COLORS[sentiment];
  return (
    <Card title={title} subtitle={subtitle}>
      {!rows.length ? <p className="text-sm text-muted">Nothing found.</p> : (
        <ol className="space-y-4">
          {rows.map((c, i) => (
            <li key={c.name} className={i ? "border-t border-line pt-4" : ""}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-bold">{titleCase(c.name)}</div>
                  {c.top_aspects?.[sentiment]?.length > 0 && (
                    <div className="mt-0.5 text-xs text-muted">mentioned as: {c.top_aspects[sentiment].join(", ")}</div>
                  )}
                  {c.subtopics?.length > 1 && (
                    <div className="mt-0.5 text-xs text-muted">covers: {c.subtopics.join(", ")}</div>
                  )}
                </div>
                <div className="text-right">
                  <div className="text-xl font-extrabold" style={{ color }}>{c[sentiment]}</div>
                  <div className="text-xs text-muted">{pct(c[sentiment] / c.total)} of {c.total} mention{c.total === 1 ? "" : "s"}</div>
                </div>
              </div>
              {c.examples?.[sentiment]?.[0] && (
                <blockquote className="mt-2 border-l-[3px] pl-3 text-sm italic text-ink/80" style={{ borderColor: color }}>
                  “{c.examples[sentiment][0]}”
                </blockquote>
              )}
              {onShow && (
                <button className="mt-2 text-xs font-bold text-brand-500 hover:underline" onClick={() => onShow(c.name, sentiment)}>
                  See all {c[sentiment]} →
                </button>
              )}
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

export function SummaryCard({ domain, batches, title = "Summary for the owner" }) {
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showFacts, setShowFacts] = useState(false);
  const key = batches.map((b) => `${b.label}:${b.summary.opinions}`).join("|");
  useEffect(() => { setResult(null); setError(""); }, [key]);

  const run = async () => {
    setBusy(true); setError("");
    try { setResult(await api.summary(domain, batches.map((b) => ({ label: b.label, summary: b.summary })))); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  const ok = result && result.unsupported_numbers.length === 0;

  return (
    <Card title={title} subtitle="Written by an LLM (Qwen2.5-1.5B-Instruct) using only the extracted facts; every number is checked automatically"
      right={<button className="btn-primary" onClick={run} disabled={busy}>{result ? "Write again" : "Write summary"}</button>}>
      {busy && <Spinner text="Writing the summary (the first time loads the model, up to a minute)…" />}
      <ErrorBox error={error} />
      {!result && !busy && <p className="text-sm text-muted">Press “Write summary” to turn the analysis into a short paragraph.</p>}
      {result && (
        <div className="space-y-3">
          <p className="text-[16px] leading-8">{result.text}</p>
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className={`rounded-full px-2.5 py-1 font-bold ${ok ? "bg-[#E3F3EF] text-[#0B6B59]" : "bg-[#FBECE8] text-[#8E3B2A]"}`}>
              {ok ? "✓ Every number matches the extracted data" : `⚠ Not in the data: ${result.unsupported_numbers.join(", ")}`}
            </span>
            <span className="text-muted">{(result.ms / 1000).toFixed(1)} s · {result.model}</span>
            <button className="font-bold text-brand-500 hover:underline" onClick={() => setShowFacts((v) => !v)}>
              {showFacts ? "Hide" : "Show"} the facts it was given
            </button>
          </div>
          {showFacts && (
            <ul className="space-y-1 rounded-lg bg-panel p-3 text-sm text-muted">
              {result.facts.map((f, i) => <li key={i}>• {f}</li>)}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}
