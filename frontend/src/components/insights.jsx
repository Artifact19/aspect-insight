import React, { useEffect, useState } from "react";
import { SENTIMENT_COLORS, api, pct, titleCase } from "../lib.js";
import { Card, ErrorBox, Spinner } from "./ui.jsx";

export function DemoPicker({ onLoad, disabled, filterDomain, placeholder = "Load a demo product…" }) {
  const [files, setFiles] = useState([]);
  useEffect(() => { api.demoList().then(setFiles).catch(() => setFiles([])); }, []);
  const shown = filterDomain ? files.filter((f) => f.domain === filterDomain) : files;
  if (!shown.length) return null;
  const domains = [...new Set(shown.map((f) => f.domain))];
  return (
    <select className="input w-auto py-2 pr-8 text-sm font-semibold" disabled={disabled} value=""
      onChange={async (e) => { if (e.target.value) onLoad(await api.demoFile(e.target.value)); }}>
      <option value="">{placeholder}</option>
      {domains.map((d) => (
        <optgroup key={d} label={d}>
          {shown.filter((f) => f.domain === d).map((f) => <option key={f.name} value={f.name}>{f.label}</option>)}
        </optgroup>
      ))}
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

export const MARKS = {
  praise: { color: "#CDE5C6", label: "Praised" },
  complaint: { color: "#F5CDBF", label: "Complaint" },
};

function marker(color) {
  return { background: `linear-gradient(104deg, transparent 0.25em, ${color} 0.25em, ${color} calc(100% - 0.25em), transparent calc(100% - 0.25em))`,
    padding: "0.1em 0.3em", margin: "0 -0.1em", borderRadius: "0.35em", boxDecorationBreak: "clone", WebkitBoxDecorationBreak: "clone" };
}

function underMarker(color) {
  return { background: `linear-gradient(transparent 62%, ${color} 62%, ${color} 92%, transparent 92%)`, padding: "0 0.05em" };
}

export function HighlightedSummary({ text, spans = [], labelColors = {} }) {
  const parts = [];
  let pos = 0;
  spans.forEach((h, i) => {
    if (h.start < pos) return;
    if (h.start > pos) parts.push(text.slice(pos, h.start));
    const piece = text.slice(h.start, h.end);
    if (h.kind === "label") {
      parts.push(<b key={i} className="font-extrabold" style={{ color: labelColors[h.label] || "#2F2923" }}>{piece}</b>);
    } else if (h.kind.endsWith("_detail")) {
      parts.push(<span key={i} style={underMarker(MARKS[h.kind.replace("_detail", "")].color)}>{piece}</span>);
    } else {
      parts.push(<mark key={i} className="font-semibold text-ink" style={marker(MARKS[h.kind].color)}>{piece}</mark>);
    }
    pos = h.end;
  });
  if (pos < text.length) parts.push(text.slice(pos));
  return <p className="text-[17px] leading-9">{parts}</p>;
}

export function SummaryCard({ domain, batches, title = "Summary", labelColors = {} }) {
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
    <Card title={title} subtitle="Written by an LLM from the extracted facts, with every number checked"
      right={<button className={result ? "btn-ghost" : "btn-primary"} onClick={run} disabled={busy}>{result ? "Write again" : "Write summary"}</button>}>
      {busy && <Spinner text="Writing the summary (the first time loads the model, up to a minute)…" />}
      <ErrorBox error={error} />
      {!result && !busy && <p className="text-sm text-muted">Press “Write summary” for a short paragraph about these reviews.</p>}
      {result && (
        <div className="space-y-4">
          <HighlightedSummary text={result.text} spans={result.highlights} labelColors={labelColors} />
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-line pt-3 text-xs">
            {Object.entries(MARKS).map(([k, m]) => (
              <span key={k} className="inline-flex items-center gap-1.5 text-muted">
                <span className="h-3 w-5 rounded" style={{ background: m.color }} />{m.label}
              </span>
            ))}
            {Object.entries(labelColors).map(([l, c]) => (
              <span key={l} className="inline-flex items-center gap-1.5 font-bold" style={{ color: c }}>
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: c }} />{l}
              </span>
            ))}
            <span className={`ml-auto rounded-full px-2.5 py-1 font-bold ${ok ? "bg-possoft text-[#2E6B4B]" : "bg-negsoft text-[#8A3A2D]"}`}>
              {ok ? "✓ Every number matches the data" : `⚠ Not in the data: ${result.unsupported_numbers.join(", ")}`}
            </span>
            <button className="font-bold text-brand-500 hover:underline" onClick={() => setShowFacts((v) => !v)}>
              {showFacts ? "Hide facts" : "Show facts"}
            </button>
          </div>
          {showFacts && (
            <div className="rounded-2xl bg-panel p-3 text-sm text-muted">
              <ul className="space-y-1">{result.facts.map((f, i) => <li key={i}>• {f}</li>)}</ul>
              <div className="mt-2 text-xs">{(result.ms / 1000).toFixed(1)} s · {result.model}</div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
