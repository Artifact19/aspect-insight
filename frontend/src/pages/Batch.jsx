import React, { useMemo, useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { SENTIMENT_COLORS, SENTIMENTS, api, download, parseReviewFile, pct, titleCase, toCsv } from "../lib.js";
import { Card, DomainPicker, ErrorBox, SentimentBadge, SentimentSplit, Spinner, Stat, Tabs } from "../components/ui.jsx";
import { DemoPicker, Highlights, SummaryCard } from "../components/insights.jsx";

export default function Batch({ domains, domain, setDomain }) {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [label, setLabel] = useState("These reviews");
  const [tab, setTab] = useState("overview");
  const tableRef = useRef(null);
  const reviews = useMemo(() => text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean), [text]);

  const loadSample = async (n = 40) => {
    setBusy("Loading test reviews…"); setError("");
    try { setText((await api.samples(domain, n, Math.floor(Math.random() * 1000))).reviews.join("\n")); setLabel("Test-set reviews"); setResult(null); setTab("overview"); }
    catch (e) { setError(e.message); }
    finally { setBusy(""); }
  };

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setText(parseReviewFile(await file.text(), file.name).join("\n"));
    setLabel(file.name.replace(/\.(csv|txt)$/i, ""));
    setResult(null); setTab("overview");
    e.target.value = "";
  };

  const loadDemo = (d) => {
    setDomain(d.domain);
    setText(d.reviews.join("\n"));
    setLabel(d.label);
    setResult(null); setTab("overview");
  };

  const showEvidence = (category, sentiment) => {
    setFilter(sentiment);
    setQuery(category);
    setTab("opinions");
    setTimeout(() => tableRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  };

  const run = async () => {
    setBusy(`Analyzing ${reviews.length} reviews…`); setError("");
    try { setResult(await api.batch(reviews, domain)); setTab("overview"); setFilter("all"); setQuery(""); }
    catch (e) { setError(e.message); }
    finally { setBusy(""); }
  };

  const rows = useMemo(() => (result ? result.sentences.flatMap((s) => s.quads.map((q) => ({
    review: s.review + 1, sentence: s.text, aspect: q.aspect || "(implied)", category: q.category_text,
    opinion: q.opinion || "(implied)", sentiment: q.sentiment, confidence: q.confidence,
  }))) : []), [result]);
  const shown = rows.filter((r) => (filter === "all" || r.sentiment === filter) &&
    (!query || `${r.aspect} ${r.category.replace("&", " and ")} ${r.opinion} ${r.sentence}`.toLowerCase().includes(query.toLowerCase())));

  const s = result?.summary;
  const categories = s ? s.categories.slice(0, 12).map((c) => ({ ...c, name: titleCase(c.name) })) : [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-extrabold tracking-tight">Batch insights</h2>
        <p className="mt-1 max-w-3xl text-muted">
          See what customers praise and criticise across many reviews. Pick a demo product, upload a file, or paste one review per line.
        </p>
      </div>

      <Card>
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <DemoPicker onLoad={loadDemo} disabled={!!busy} />
            <span className="text-sm text-muted">or</span>
            <label className="btn-ghost cursor-pointer">Upload .txt / .csv<input type="file" accept=".txt,.csv" className="hidden" onChange={onFile} /></label>
            <button className="btn-ghost" onClick={() => loadSample()} disabled={!!busy}>Test-set sample</button>
          </div>
          <div><div className="label mb-2">Domain</div><DomainPicker domains={domains} value={domain} onChange={(d) => { setDomain(d); setResult(null); }} /></div>
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="label">Reviews{label !== "These reviews" ? ` · ${label}` : ""}</span>
              <span className="text-xs text-muted">{reviews.length} review{reviews.length === 1 ? "" : "s"}</span>
            </div>
            <textarea className="input min-h-[130px] font-mono text-[13px]" value={text} onChange={(e) => setText(e.target.value)}
              placeholder="One review per line…" />
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button className="btn-primary" onClick={run} disabled={!!busy || !reviews.length}>Analyze {reviews.length || ""} reviews</button>
            {busy && <Spinner text={busy} />}
          </div>
          <ErrorBox error={error} />
        </div>
      </Card>

      {s && (
        <>
          <Tabs value={tab} onChange={setTab} tabs={[
            { id: "overview", label: "Overview" }, { id: "charts", label: "Charts" }, { id: "opinions", label: `All opinions (${rows.length})` },
          ]} />

          {tab === "overview" && <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Reviews" value={result.reviews} hint={`${s.sentences} sentences`} />
            <Stat label="Opinions" value={s.opinions} hint={`${(s.opinions / Math.max(1, result.reviews)).toFixed(1)} per review`} />
            <Stat label="Positive share" value={pct(s.share.positive)} color="#0F8C74" />
            <Stat label="Negative share" value={pct(s.share.negative)} color="#D0533C" />
          </div>

          <SummaryCard domain={domain} batches={[{ label, summary: s }]} />

          <div className="grid gap-6 lg:grid-cols-2">
            <Highlights summary={s} sentiment="negative" title="Fix first" onShow={showEvidence}
              limit={3} subtitle="Topics with the most complaints" />
            <Highlights summary={s} sentiment="positive" title="Keep doing" onShow={showEvidence} limit={3}
              subtitle="What customers praise most" />
          </div>
          </>}

          {tab === "charts" && (
          <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
            <Card title="Sentiment by category" subtitle="Number of opinions per category, split by sentiment (top 12 categories)">
              <ResponsiveContainer width="100%" height={Math.max(220, categories.length * 34 + 60)}>
                <BarChart data={categories} layout="vertical" margin={{ left: 8, right: 16 }} barCategoryGap={8}>
                  <CartesianGrid horizontal={false} stroke="#EFE7DB" />
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12, fill: "#7A716A" }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="name" width={210} tick={{ fontSize: 12, fill: "#2E2A27" }} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: "#F3EBDF" }} />
                  <Legend formatter={(v) => <span className="text-ink">{titleCase(v)}</span>} />
                  {SENTIMENTS.map((k, i) => (
                    <Bar key={k} dataKey={k} stackId="s" fill={SENTIMENT_COLORS[k]} stroke="#fff" strokeWidth={2}
                      radius={i === 2 ? [0, 4, 4, 0] : 0} name={k} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </Card>
            <Card title="Overall and opinion words">
              <SentimentSplit counts={s.sentiment} />
              {SENTIMENTS.map((k) => s.top_opinions[k].length > 0 && (
                <div key={k} className="mt-4">
                  <div className="label mb-1.5">{k}</div>
                  <div className="flex flex-wrap gap-1.5">
                    {s.top_opinions[k].slice(0, 8).map((o) => (
                      <span key={o.word} className="rounded-md px-2 py-0.5 text-xs font-semibold"
                        style={{ background: `${SENTIMENT_COLORS[k]}1f` }}>{o.word} · {o.count}</span>
                    ))}
                  </div>
                </div>
              ))}
            </Card>
          </div>

          )}

          <div ref={tableRef} />
          {tab === "opinions" && (
          <Card title="All extracted opinions" subtitle={`${shown.length} of ${rows.length} shown`}
            right={<button className="btn-ghost" onClick={() => download(`opinions_${domain.toLowerCase()}.csv`, toCsv(rows))}>Download CSV</button>}>
            <div className="mb-3 flex flex-wrap gap-2">
              {["all", ...SENTIMENTS].map((k) => (
                <button key={k} onClick={() => setFilter(k)}
                  className={`chip text-xs ${filter === k ? "border-brand-500 bg-brand-50 text-brand-700" : "border-line bg-white text-muted"}`}>{titleCase(k)}</button>
              ))}
              <input className="input ml-auto max-w-xs py-1.5 text-sm" placeholder="Search…" value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
            <div className="max-h-[520px] overflow-auto">
              <table className="w-full border-collapse">
                <thead className="sticky top-0"><tr><th>#</th><th>Aspect</th><th>Category</th><th>Opinion</th><th>Sentiment</th><th>Sentence</th></tr></thead>
                <tbody>
                  {shown.slice(0, 400).map((r, i) => (
                    <tr key={i}>
                      <td className="text-muted">{r.review}</td>
                      <td className="font-semibold">{r.aspect}</td>
                      <td>{titleCase(r.category)}</td>
                      <td>{r.opinion}</td>
                      <td><SentimentBadge sentiment={r.sentiment} /></td>
                      <td className="max-w-md text-muted">{r.sentence}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          )}
        </>
      )}
    </div>
  );
}
