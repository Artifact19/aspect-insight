import React from "react";
import { SENTIMENT_COLORS, SENTIMENT_SOFT, SENTIMENTS, pct, titleCase } from "../lib.js";

const ICONS = {
  spark: <><path d="M12 3v4M12 17v4M3 12h4M17 12h4" /><path d="m6.3 6.3 2.1 2.1M15.6 15.6l2.1 2.1M6.3 17.7l2.1-2.1M15.6 8.4l2.1-2.1" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  back: <path d="M15 18l-6-6 6-6" />,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  external: <><path d="M14 4h6v6" /><path d="M20 4l-9 9" /><path d="M19 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h4" /></>,
  heart: <path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" />,
  alert: <><path d="M12 3 2 20h20L12 3z" /><path d="M12 10v4M12 17h.01" /></>,
  chat: <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" />,
  send: <path d="M5 12h14M13 6l6 6-6 6" />,
  puzzle: <path d="M10 3h4v3a2 2 0 1 0 4 0V3h3v7h-3a2 2 0 1 0 0 4h3v7h-7v-3a2 2 0 1 0-4 0v3H3v-7h3a2 2 0 1 0 0-4H3V3h7z" />,
  paste: <><rect x="6" y="4" width="12" height="17" rx="2" /><path d="M9 4V3h6v1M9 10h6M9 14h6M9 18h3" /></>,
  box: <><path d="M3 7l9-4 9 4-9 4-9-4z" /><path d="M3 7v10l9 4 9-4V7" /><path d="M12 11v10" /></>,
  check: <path d="M5 12l5 5 9-10" />,
  download: <><path d="M12 4v11M7 10l5 5 5-5" /><path d="M5 20h14" /></>,
  x: <path d="M6 6l12 12M18 6 6 18" />,
  trash: <><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" /></>,
  grid: <><rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" /><rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></>,
  layers: <><path d="M12 3 2 8l10 5 10-5-10-5z" /><path d="m2 16 10 5 10-5M2 12l10 5 10-5" /></>,
  scale: <><path d="M12 3v18M5 7h14M7 7l-3 7a3 3 0 0 0 6 0L7 7zM17 7l-3 7a3 3 0 0 0 6 0l-3-7z" /></>,
  flask: <><path d="M9 3h6M10 3v6L4 19a1 1 0 0 0 .9 1.5h14.2A1 1 0 0 0 20 19L14 9V3" /><path d="M7 14h10" /></>,
  mail: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" /></>,
  chart: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
  database: <><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5" /><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" /></>,
  home: <><path d="M3 11 12 4l9 7" /><path d="M5 10v10h14V10" /></>,
  refresh: <><path d="M20 11a8 8 0 0 0-14.7-4.3L4 8" /><path d="M4 3v5h5" /><path d="M4 13a8 8 0 0 0 14.7 4.3L20 16" /><path d="M20 21v-5h-5" /></>,
};

export function Icon({ name, className = "h-[18px] w-[18px]" }) {
  return (
    <svg viewBox="0 0 24 24" className={`flex-none ${className}`} fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{ICONS[name]}</svg>
  );
}

export function Logo({ className = "h-10 w-10" }) {
  return <img src="/favicon.svg" alt="" className={`${className} drop-shadow-[0_6px_10px_rgba(58,79,224,.25)]`} />;
}

export function Card({ title, subtitle, right, children, className = "", pad = "p-6" }) {
  return (
    <section className={`card ${pad} ${className}`}>
      {(title || right) && (
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            {title && <h3 className="text-[17px] font-bold tracking-tight text-ink">{title}</h3>}
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
      <div className="mt-1 text-3xl font-extrabold tracking-tight" style={{ color: color || "#2F2923" }}>{value}</div>
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
  return <div className="rounded-2xl bg-negsoft px-4 py-3 text-sm text-[#8A3A2D]">{error}</div>;
}

export function DomainPicker({ domains, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-2">
      {domains.map((d) => (
        <button key={d.name} onClick={() => onChange(d.name)}
          className={`chip ${value === d.name ? "border-brand-500 bg-brand-500 text-white" : "border-line bg-surface text-ink hover:border-brand-500"}`}>
          {d.name}
        </button>
      ))}
    </div>
  );
}

export function SentimentBadge({ sentiment }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-bold"
      style={{ background: SENTIMENT_SOFT[sentiment], color: "#2F2923" }}>
      <span className="h-2 w-2 rounded-full" style={{ background: SENTIMENT_COLORS[sentiment] }} />
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

/** A sentence with each aspect highlighted in its sentiment colour and opinion words underlined. */
export function Highlighted({ text, quads, size = "text-[17px] leading-9" }) {
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
      <mark key={`m${i}`} className="rounded-md px-1 py-0.5 font-semibold text-ink"
        style={{ background: SENTIMENT_SOFT[m.q.sentiment], boxShadow: `inset 0 -2px 0 ${color}` }}
        title={`${m.q.category_text} · ${m.q.sentiment}`}>{text.slice(m.start, m.end)}</mark>
    ) : (
      <span key={`m${i}`} className="font-semibold" style={{ textDecoration: `underline wavy ${color}`, textUnderlineOffset: 4 }}
        title={`opinion · ${m.q.sentiment}`}>{text.slice(m.start, m.end)}</span>
    ));
    pos = m.end;
  });
  if (pos < text.length) parts.push(<span key="end">{text.slice(pos)}</span>);
  return size === "inline" ? <span>{parts}</span> : <p className={size}>{parts}</p>;
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

/** Stacked bar of positive / neutral / negative opinions with a legend. */
export function SentimentSplit({ counts, big = false }) {
  const order = ["positive", "neutral", "negative"];
  const total = order.reduce((a, s) => a + (counts[s] || 0), 0);
  if (!total) return null;
  return (
    <div>
      <div className={`flex gap-1 overflow-hidden rounded-full ${big ? "h-4" : "h-3"}`}>
        {order.filter((s) => counts[s]).map((s) => (
          <div key={s} className="rounded-full" style={{ width: `${(100 * counts[s]) / total}%`, background: SENTIMENT_COLORS[s] }} />
        ))}
      </div>
      <div className="mt-2.5 flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink2">
        {order.map((s) => (
          <span key={s} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: SENTIMENT_COLORS[s] }} />
            {titleCase(s)} <b className="text-ink">{pct((counts[s] || 0) / total)}</b>
            <span className="text-muted">({counts[s] || 0})</span>
          </span>
        ))}
      </div>
    </div>
  );
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="inline-flex flex-wrap gap-1 rounded-full border border-line bg-surface/70 p-1">
      {tabs.map((t) => (
        <button key={t.id} onClick={() => onChange(t.id)}
          className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${value === t.id ? "bg-white text-ink shadow-soft" : "text-muted hover:text-ink"}`}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function PageHeader({ title, children }) {
  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight">{title}</h2>
      {children && <p className="mt-1 max-w-3xl text-muted">{children}</p>}
    </div>
  );
}
