import React from "react";
import { SENTIMENT_COLORS, SENTIMENTS, pct, titleCase } from "../lib.js";

export function Card({ title, subtitle, right, children, className = "" }) {
  return (
    <section className={`card p-5 ${className}`}>
      {(title || right) && (
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            {title && <h3 className="text-base font-bold text-ink">{title}</h3>}
            {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
          </div>
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value, hint, color }) {
  return (
    <div className="card px-5 py-4">
      <div className="label">{label}</div>
      <div className="mt-1 text-3xl font-extrabold tracking-tight" style={{ color: color || "#2E2A27" }}>{value}</div>
      {hint && <div className="mt-1 text-sm text-muted">{hint}</div>}
    </div>
  );
}

export function Spinner({ text = "Working…" }) {
  return (
    <div className="flex items-center gap-3 text-sm text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-100 border-t-brand-500" />
      {text}
    </div>
  );
}

export function ErrorBox({ error }) {
  if (!error) return null;
  return <div className="rounded-lg border border-[#F1C7BC] bg-[#FBECE8] px-4 py-3 text-sm text-[#8E3B2A]">{error}</div>;
}

export function DomainPicker({ domains, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-2">
      {domains.map((d) => (
        <button key={d.name} onClick={() => onChange(d.name)}
          className={`chip ${value === d.name ? "border-brand-500 bg-brand-500 text-white" : "border-line bg-white text-ink hover:border-brand-500"}`}>
          {d.name}
        </button>
      ))}
    </div>
  );
}

export function SentimentBadge({ sentiment }) {
  const color = SENTIMENT_COLORS[sentiment];
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-bold"
      style={{ background: `${color}1a`, color: "#2E2A27" }}>
      <span className="h-2 w-2 rounded-full" style={{ background: color }} />
      {titleCase(sentiment)}
    </span>
  );
}

const SHORT = { positive: "Pos", negative: "Neg", neutral: "Neu" };

export function ConfidenceBar({ probabilities }) {
  if (!probabilities) return null;
  return (
    <div className="w-44">
      <div className="flex h-2 overflow-hidden rounded-full bg-sand">
        {SENTIMENTS.map((s) => (
          <div key={s} title={`${titleCase(s)} ${pct(probabilities[s], 1)}`}
            style={{ width: pct(probabilities[s], 2), background: SENTIMENT_COLORS[s] }} />
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-muted">
        {SENTIMENTS.map((s) => <span key={s}>{SHORT[s]} {pct(probabilities[s])}</span>)}
      </div>
    </div>
  );
}

export function Highlighted({ text, quads }) {
  const marks = [];
  quads.forEach((q) => {
    if (q.aspect_span) marks.push({ start: q.aspect_span[0], end: q.aspect_span[1], kind: "aspect", q });
    if (q.opinion_span) marks.push({ start: q.opinion_span[0], end: q.opinion_span[1], kind: "opinion", q });
  });
  marks.sort((a, b) => a.start - b.start || b.end - a.end);
  const parts = [];
  let pos = 0;
  marks.forEach((m, i) => {
    if (m.start < pos) return;
    if (m.start > pos) parts.push(<span key={`t${i}`}>{text.slice(pos, m.start)}</span>);
    const color = SENTIMENT_COLORS[m.q.sentiment];
    parts.push(m.kind === "aspect" ? (
      <mark key={`m${i}`} className="rounded px-1 py-0.5 font-semibold text-ink"
        style={{ background: `${color}2e`, boxShadow: `inset 0 -2px 0 ${color}` }}
        title={`${m.q.category_text} · ${m.q.sentiment}`}>{text.slice(m.start, m.end)}</mark>
    ) : (
      <span key={`m${i}`} className="font-semibold" style={{ textDecoration: `underline wavy ${color}`, textUnderlineOffset: 4 }}
        title={`opinion · ${m.q.sentiment}`}>{text.slice(m.start, m.end)}</span>
    ));
    pos = m.end;
  });
  if (pos < text.length) parts.push(<span key="end">{text.slice(pos)}</span>);
  return <p className="text-[17px] leading-9">{parts}</p>;
}

export function QuadTable({ quads, showConfidence = true }) {
  if (!quads.length) return <p className="text-sm text-muted">No opinions found in this sentence.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th>Aspect</th><th>Category</th><th>Opinion</th><th>Sentiment</th>
            {showConfidence && <th>Classifier check</th>}
          </tr>
        </thead>
        <tbody>
          {quads.map((q, i) => (
            <tr key={i}>
              <td className="font-semibold">{q.aspect || <span className="italic text-muted">implied</span>}</td>
              <td>{titleCase(q.category_text)}</td>
              <td>{q.opinion || <span className="italic text-muted">implied</span>}</td>
              <td><SentimentBadge sentiment={q.sentiment} /></td>
              {showConfidence && (
                <td>
                  <div className="flex items-center gap-3">
                    <ConfidenceBar probabilities={q.probabilities} />
                    {q.agrees === false && <span className="text-xs font-semibold text-neg">disagrees</span>}
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SentimentSplit({ counts }) {
  const total = SENTIMENTS.reduce((a, s) => a + (counts[s] || 0), 0);
  if (!total) return null;
  return (
    <div>
      <div className="flex h-3 gap-0.5 overflow-hidden rounded-full">
        {SENTIMENTS.filter((s) => counts[s]).map((s) => (
          <div key={s} style={{ width: `${(100 * counts[s]) / total}%`, background: SENTIMENT_COLORS[s] }} />
        ))}
      </div>
      <div className="mt-2 flex gap-4 text-sm">
        {SENTIMENTS.map((s) => (
          <span key={s} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: SENTIMENT_COLORS[s] }} />
            {titleCase(s)} <b>{counts[s] || 0}</b>
          </span>
        ))}
      </div>
    </div>
  );
}
