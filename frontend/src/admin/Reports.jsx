import React, { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { SENTIMENT_COLORS, SENTIMENTS, SOURCES, api, download, hostOf, shortTitle, timeAgo, titleCase, toCsv } from "../lib.js";
import { Card, ErrorBox, Icon, SentimentBadge, SentimentSplit, Spinner, Stat, Tabs } from "../components/ui.jsx";
import DownloadReport from "../components/DownloadReport.jsx";

function Detail({ id, onDeleted }) {
  const [cap, setCap] = useState(null);
  const [tab, setTab] = useState("opinions");
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { setCap(null); api.capture(id).then(setCap).catch((e) => setError(e.message)); }, [id]);

  const rows = useMemo(() => (cap ? cap.sentences.flatMap((s) => s.quads.map((q) => ({
    review: s.review + 1, sentence: s.text, aspect: q.aspect || "(implied)", category: q.category_text,
    opinion: q.opinion || "(implied)", sentiment: q.sentiment, confidence: q.confidence,
    checker: q.classifier_sentiment, agrees: q.agrees,
  }))) : []), [cap]);

  if (error) return <ErrorBox error={error} />;
  if (!cap) return <div className="card p-8"><Spinner text="Loading…" /></div>;
  const s = cap.summary;
  const shown = rows.filter((r) => (filter === "all" || r.sentiment === filter) &&
    (!query || `${r.aspect} ${r.category} ${r.opinion} ${r.sentence}`.toLowerCase().includes(query.toLowerCase())));
  const categories = s.categories.slice(0, 12).map((c) => ({ ...c, name: titleCase(c.name) }));
  const disagree = rows.filter((r) => r.agrees === false).length;

  const remove = async () => {
    if (!window.confirm(`Delete the report "${cap.title}"? This cannot be undone.`)) return;
    await api.deleteCapture(cap.id);
    onDeleted();
  };

  return (
    <div className="space-y-5">
      <Card>
        <div className="flex flex-wrap items-start gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="chip-soft">{SOURCES[cap.source] || cap.source}</span><span className="chip-soft">{cap.domain}</span>
              <span className="text-muted">{timeAgo(cap.created_at)} · id {cap.id}</span>
            </div>
            <h2 className="mt-2 text-lg font-extrabold leading-snug">{cap.title}</h2>
            {cap.source_url && <a href={cap.source_url} target="_blank" rel="noreferrer" className="text-sm font-semibold text-brand-500 hover:underline">{hostOf(cap.source_url)}</a>}
          </div>
          <a className="btn-ghost" href={`/#/r/${cap.id}`}>Open report</a>
          <DownloadReport capture={cap} />
          <button className="btn-ghost text-neg" onClick={remove}><Icon name="trash" className="h-4 w-4" />Delete</button>
        </div>
        <div className="mt-4"><SentimentSplit counts={s.sentiment} /></div>
      </Card>

      <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Reviews" value={cap.review_count} hint={`${cap.raw_count} read, ${cap.skipped} skipped`} />
        <Stat label="Opinions" value={s.opinions} hint={`${(s.opinions / Math.max(1, cap.review_count)).toFixed(1)} per review`} />
        <Stat label="Checker disagrees" value={disagree} hint="DeBERTa vs Flan-T5 sentiment" color={disagree ? "#AD6F2B" : undefined} />
        <Stat label="Time" value={`${(cap.timing.total_ms / 1000).toFixed(1)} s`} hint={`${cap.timing.generation_ms_per_sentence} ms per sentence`} />
      </div>

      <Tabs value={tab} onChange={setTab} tabs={[{ id: "opinions", label: `All opinions (${rows.length})` }, { id: "charts", label: "Categories" }]} />

      {tab === "charts" && (
        <div className="grid gap-5 xl:grid-cols-[2fr_1fr]">
          <Card title="Sentiment by category" subtitle="Opinions per category (top 12)">
            <ResponsiveContainer width="100%" height={Math.max(220, categories.length * 34 + 60)}>
              <BarChart data={categories} layout="vertical" margin={{ left: 8, right: 16 }} barCategoryGap={8}>
                <CartesianGrid horizontal={false} stroke="#E6DCCD" />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12, fill: "#8C8176" }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" width={220} tick={{ fontSize: 12, fill: "#2F2923" }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: "#EEE6DA" }} />
                <Legend formatter={(v) => <span className="text-ink">{titleCase(v)}</span>} />
                {SENTIMENTS.map((k, i) => (
                  <Bar key={k} dataKey={k} stackId="s" fill={SENTIMENT_COLORS[k]} stroke="#F9F4EC" strokeWidth={2} radius={i === 2 ? [0, 4, 4, 0] : 0} name={k} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </Card>
          <Card title="Most used opinion words">
            {SENTIMENTS.map((k) => s.top_opinions[k].length > 0 && (
              <div key={k} className="mb-4">
                <div className="label mb-1.5">{k}</div>
                <div className="flex flex-wrap gap-1.5">
                  {s.top_opinions[k].slice(0, 10).map((o) => (
                    <span key={o.word} className="rounded-lg px-2 py-0.5 text-xs font-semibold" style={{ background: `${SENTIMENT_COLORS[k]}1f` }}>{o.word} · {o.count}</span>
                  ))}
                </div>
              </div>
            ))}
          </Card>
        </div>
      )}

      {tab === "opinions" && (
        <Card title="Every extracted quadruple" subtitle={`${shown.length} of ${rows.length} shown`}
          right={<button className="btn-ghost" onClick={() => download(`report_${cap.id}.csv`, toCsv(rows))}>Download CSV</button>}>
          <div className="mb-3 flex flex-wrap gap-2">
            {["all", ...SENTIMENTS].map((k) => (
              <button key={k} onClick={() => setFilter(k)}
                className={`chip text-xs ${filter === k ? "border-brand-500 bg-brand-50 text-brand-700" : "border-line bg-surface text-muted"}`}>{titleCase(k)}</button>
            ))}
            <input className="input ml-auto max-w-xs py-1.5 text-sm" placeholder="Search…" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          <div className="max-h-[560px] overflow-auto">
            <table className="w-full border-collapse">
              <thead className="sticky top-0 bg-surface"><tr><th>#</th><th>Aspect</th><th>Category</th><th>Opinion</th><th>Sentiment</th><th>Check</th><th>Sentence</th></tr></thead>
              <tbody>
                {shown.slice(0, 500).map((r, i) => (
                  <tr key={i}>
                    <td className="text-muted">{r.review}</td>
                    <td className="font-semibold">{r.aspect}</td>
                    <td>{titleCase(r.category)}</td>
                    <td>{r.opinion}</td>
                    <td><SentimentBadge sentiment={r.sentiment} /></td>
                    <td className="whitespace-nowrap text-xs">{r.agrees ? <span className="text-muted">{Math.round(100 * r.confidence)}%</span> : <span className="font-semibold text-neu">says {r.checker}</span>}</td>
                    <td className="max-w-md text-muted">{r.sentence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

export default function Reports({ arg }) {
  const [captures, setCaptures] = useState(null);
  const load = () => api.captures().then(setCaptures).catch(() => setCaptures([]));
  useEffect(() => { load(); }, []);
  const active = arg || captures?.[0]?.id;

  return (
    <div className="grid gap-5 xl:grid-cols-[300px_minmax(0,1fr)]">
      <Card pad="p-3" className="h-fit xl:sticky xl:top-3.5">
        {!captures ? <Spinner /> : !captures.length ? <p className="p-3 text-sm text-muted">No reports yet.</p> : (
          <ul className="max-h-[75vh] space-y-1 overflow-auto">
            {captures.map((c) => (
              <li key={c.id}>
                <a href={`#reports/${c.id}`} className={`block rounded-2xl px-3 py-2.5 transition ${c.id === active ? "bg-brand-50" : "hover:bg-surface"}`}>
                  <div className="line-clamp-2 text-sm font-semibold leading-snug">{shortTitle(c.title)}</div>
                  <div className="mt-0.5 text-xs text-muted">{SOURCES[c.source] || c.source} · {c.review_count} reviews · {timeAgo(c.created_at)}</div>
                </a>
              </li>
            ))}
          </ul>
        )}
      </Card>
      {active ? <Detail id={active} onDeleted={() => { window.location.hash = "#reports"; load(); }} /> : <div />}
    </div>
  );
}
