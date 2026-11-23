import React, { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, hashParams, parseReviewFile, pct, titleCase } from "../lib.js";
import { Card, DomainPicker, ErrorBox, Spinner, Tabs } from "../components/ui.jsx";
import { DemoPicker, Highlights, SummaryCard } from "../components/insights.jsx";

const COLORS = { a: "#4757CF", b: "#C0683F" };
const TEXT_COLORS = { a: "#2F3A96", b: "#9A4F2C" };
const SIMILAR = 10;
const PAIRS = [
  { title: "MacBook Air vs Dell XPS", domain: "Laptop", a: "laptop_macbook_air_m3", b: "laptop_dell_xps_13", la: "MacBook Air M3", lb: "Dell XPS 13" },
  { title: "Domino's vs Pizza Hut", domain: "Restaurant", a: "restaurant_dominos", b: "restaurant_pizza_hut", la: "Domino's", lb: "Pizza Hut" },
  { title: "Taj vs Marina Bay Sands", domain: "Hotel", a: "hotel_taj_mahal_palace_mumbai", b: "hotel_marina_bay_sands", la: "Taj Mahal Palace", lb: "Marina Bay Sands" },
  { title: "Air Force 1 vs Crocs", domain: "Clothing", a: "clothing_nike_air_force_1", b: "clothing_crocs_classic_clog", la: "Nike Air Force 1", lb: "Crocs" },
  { title: "Atomic Habits vs The Alchemist", domain: "Books", a: "books_atomic_habits", b: "books_the_alchemist", la: "Atomic Habits", lb: "The Alchemist" },
];

function Side({ id, side, setSide, domain, disabled, captures, onPickCapture }) {
  const count = side.text.split(/\r?\n/).filter((l) => l.trim()).length;
  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSide({ label: file.name.replace(/\.(csv|txt)$/i, ""), text: parseReviewFile(await file.text(), file.name).join("\n") });
    e.target.value = "";
  };
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-full text-sm font-extrabold text-white" style={{ background: COLORS[id] }}>{id.toUpperCase()}</span>
        <input className="input py-1.5 font-bold" value={side.label} onChange={(e) => setSide({ ...side, label: e.target.value })} />
      </div>
      <textarea className="input min-h-[110px] font-mono text-[12.5px]" value={side.text} placeholder="One review per line…"
        onChange={(e) => setSide({ ...side, text: e.target.value })} />
      <div className="flex flex-wrap items-center gap-2">
        <label className="btn-ghost cursor-pointer py-1.5">Upload<input type="file" accept=".txt,.csv" className="hidden" onChange={onFile} /></label>
        <DemoPicker filterDomain={domain} disabled={disabled} placeholder="Demo product…" onLoad={(d) => setSide({ label: d.label, text: d.reviews.join("\n") })} />
        {captures?.length > 0 && (
          <select className="input w-auto py-1.5 text-sm font-semibold" disabled={disabled} value=""
            onChange={(e) => { if (e.target.value) onPickCapture(e.target.value); }}>
            <option value="">Saved report…</option>
            {captures.map((c) => <option key={c.id} value={c.id}>{c.title.slice(0, 60)} ({c.review_count})</option>)}
          </select>
        )}
        <span className="ml-auto text-xs text-muted">{count} reviews</span>
      </div>
    </div>
  );
}

export default function Compare({ domains, domain, setDomain }) {
  const [a, setA] = useState({ label: "A", text: "" });
  const [b, setB] = useState({ label: "B", text: "" });
  const [captures, setCaptures] = useState([]);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [tab, setTab] = useState("overview");

  const loadCaptureIntoSide = async (id, sideSetter, syncDomain = false) => {
    const cap = await api.capture(id);
    if (syncDomain && cap.domain) setDomain(cap.domain);
    sideSetter({
      label: cap.title,
      text: (cap.reviews || []).map((r) => r.text).join("\n"),
    });
    return cap;
  };

  useEffect(() => {
    api.captures().then(setCaptures).catch(() => setCaptures([]));
    const params = hashParams();
    const aId = params.get("a");
    const bId = params.get("b");
    if (aId && bId) {
      setBusy("Loading the two reports…");
      Promise.all([api.capture(aId), api.capture(bId)])
        .then(([ca, cb]) => {
          setDomain(ca.domain || cb.domain || domain);
          setA({ label: ca.title, text: (ca.reviews || []).map((r) => r.text).join("\n") });
          setB({ label: cb.title, text: (cb.reviews || []).map((r) => r.text).join("\n") });
          setResult({
            a: { label: ca.title, summary: ca.summary, reviews: ca.review_count },
            b: { label: cb.title, summary: cb.summary, reviews: cb.review_count },
          });
        })
        .catch((e) => setError(e.message))
        .finally(() => setBusy(""));
    } else if (aId) {
      loadCaptureIntoSide(aId, setA, true).catch(() => {});
    }
  }, []);

  const lines = (x) => x.text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);

  const loadPair = async (pair) => {
    setBusy("Loading demo files…"); setError(""); setResult(null);
    try {
      const [da, db] = await Promise.all([api.demoFile(pair.a), api.demoFile(pair.b)]);
      setDomain(pair.domain);
      setA({ label: pair.la, text: da.reviews.join("\n") });
      setB({ label: pair.lb, text: db.reviews.join("\n") });
    } catch (e) { setError(e.message); }
    finally { setBusy(""); }
  };

  const run = async () => {
    setError(""); setResult(null);
    try {
      setBusy(`Analyzing ${a.label}…`);
      const ra = await api.batch(lines(a), domain);
      setBusy(`Analyzing ${b.label}…`);
      const rb = await api.batch(lines(b), domain);
      setTab("overview");
      setResult({ a: { label: a.label, summary: ra.summary, reviews: ra.reviews }, b: { label: b.label, summary: rb.summary, reviews: rb.reviews } });
    } catch (e) { setError(e.message); }
    finally { setBusy(""); }
  };

  const topics = useMemo(() => {
    if (!result) return null;
    const by = (s) => Object.fromEntries((s.entities || s.categories).map((c) => [c.name, c]));
    const ca = by(result.a.summary), cb = by(result.b.summary);
    const ra = result.a.reviews, rb = result.b.reviews;
    const share = (c, k, n) => (c ? Math.round((100 * ((c.reviews_with || {})[k] ?? c[k])) / Math.max(1, n)) : 0);
    const names = [...new Set([...Object.keys(ca), ...Object.keys(cb)])];
    const rows = names.map((n) => {
      const x = ca[n], y = cb[n];
      return { name: titleCase(n), a_neg: share(x, "negative", ra), b_neg: share(y, "negative", rb),
        a_pos: share(x, "positive", ra), b_pos: share(y, "positive", rb),
        a_count: x?.negative || 0, b_count: y?.negative || 0, diff: share(y, "negative", rb) - share(x, "negative", ra) };
    });
    return {
      complaints: [...rows].filter((r) => r.a_neg || r.b_neg).sort((p, q) => Math.max(q.a_neg, q.b_neg) - Math.max(p.a_neg, p.b_neg)).slice(0, 8),
      praise: [...rows].filter((r) => r.a_pos || r.b_pos).sort((p, q) => Math.max(q.a_pos, q.b_pos) - Math.max(p.a_pos, p.b_pos)).slice(0, 8),
      differences: [...rows].filter((r) => r.diff).sort((p, q) => Math.abs(q.diff) - Math.abs(p.diff)).slice(0, 6),
    };
  }, [result]);

  const chart = (data, ka, kb, title, subtitle) => (
    <Card title={title} subtitle={subtitle}>
      <ResponsiveContainer width="100%" height={Math.max(200, data.length * 52 + 50)}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 34 }} barGap={2} barCategoryGap={10}>
          <CartesianGrid horizontal={false} stroke="#E6DCCD" />
          <XAxis type="number" allowDecimals={false} unit="%" tick={{ fontSize: 12, fill: "#8C8176" }} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="name" width={190} tick={{ fontSize: 12, fill: "#2F2923" }} axisLine={false} tickLine={false} />
          <Tooltip cursor={{ fill: "#EEE6DA" }} formatter={(v, k) => [`${v}% of reviews`, k === ka ? result.a.label : result.b.label]} />
          <Legend formatter={(v) => <span className="text-ink">{v === ka ? result.a.label : result.b.label}</span>} />
          <Bar dataKey={ka} fill={COLORS.a} radius={[0, 4, 4, 0]} maxBarSize={16}>
            <LabelList dataKey={ka} position="right" formatter={(v) => `${v}%`} style={{ fontSize: 11, fill: "#2F2923" }} />
          </Bar>
          <Bar dataKey={kb} fill={COLORS.b} radius={[0, 4, 4, 0]} maxBarSize={16}>
            <LabelList dataKey={kb} position="right" formatter={(v) => `${v}%`} style={{ fontSize: 11, fill: "#2F2923" }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );

  const glance = result && [
    ["Reviews", result.a.reviews, result.b.reviews],
    ["Opinions", result.a.summary.opinions, result.b.summary.opinions],
    ["Positive share", pct(result.a.summary.share.positive), pct(result.b.summary.share.positive)],
    ["Negative share", pct(result.a.summary.share.negative), pct(result.b.summary.share.negative)],
  ];

  return (
    <div className="space-y-6">

      <Card>
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="label mr-1">Try a pair</span>
            {PAIRS.map((p) => <button key={p.title} className="chip border-line bg-surface text-sm hover:border-brand-500" disabled={!!busy} onClick={() => loadPair(p)}>{p.title}</button>)}
          </div>
          <div><div className="label mb-2">Domain</div><DomainPicker domains={domains} value={domain} onChange={(d) => { setDomain(d); setResult(null); }} /></div>
          <div className="grid gap-6 lg:grid-cols-2">
            <Side id="a" side={a} setSide={setA} domain={domain} disabled={!!busy} captures={captures} onPickCapture={(id) => loadCaptureIntoSide(id, setA, true)} />
            <Side id="b" side={b} setSide={setB} domain={domain} disabled={!!busy} captures={captures} onPickCapture={(id) => loadCaptureIntoSide(id, setB, false)} />
          </div>
          <div className="flex items-center gap-4">
            <button className="btn-primary" onClick={run} disabled={!!busy || !lines(a).length || !lines(b).length}>Compare</button>
            {busy && <Spinner text={busy} />}
          </div>
          <ErrorBox error={error} />
        </div>
      </Card>

      {result && topics && (
        <>
          <Tabs value={tab} onChange={setTab} tabs={[
            { id: "overview", label: "Overview" }, { id: "charts", label: "Charts" }, { id: "fix", label: "Fix first" },
          ]} />

          {tab === "overview" && <>
          <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
            <Card title="At a glance">
              <table className="w-full border-collapse">
                <thead><tr><th></th>
                  {[["a", result.a.label], ["b", result.b.label]].map(([k, l]) => (
                    <th key={k} className="text-right"><span className="inline-flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: COLORS[k] }} />{l}</span></th>
                  ))}</tr></thead>
                <tbody>{glance.map(([k, x, y]) => (
                  <tr key={k}><td className="text-muted">{k}</td><td className="text-right font-bold">{x}</td><td className="text-right font-bold">{y}</td></tr>
                ))}</tbody>
              </table>
            </Card>
            <SummaryCard domain={domain} title="Comparison summary"
              labelColors={{ [result.a.label]: TEXT_COLORS.a, [result.b.label]: TEXT_COLORS.b }}
              batches={[{ label: result.a.label, summary: result.a.summary }, { label: result.b.label, summary: result.b.summary }]} />
          </div>

          <Card title="Biggest differences in complaints"
            subtitle={`Share of each side's reviews that complain about the topic, so sets of different sizes compare fairly. Gaps under ${SIMILAR} points are marked similar.`}>
            <table className="w-full border-collapse">
              <thead><tr><th>Topic</th><th className="text-right">{result.a.label}</th><th className="text-right">{result.b.label}</th><th className="text-right">Gap</th><th>Worse at</th></tr></thead>
              <tbody>{topics.differences.map((r) => (
                <tr key={r.name}>
                  <td className="font-semibold">{r.name}</td>
                  <td className="text-right">{r.a_neg}% <span className="text-xs text-muted">({r.a_count})</span></td>
                  <td className="text-right">{r.b_neg}% <span className="text-xs text-muted">({r.b_count})</span></td>
                  <td className="text-right font-bold">{Math.abs(r.diff)} pts</td>
                  <td>{Math.abs(r.diff) < SIMILAR ? <span className="text-sm text-muted">Similar</span> : (
                    <span className="inline-flex items-center gap-1.5 text-sm font-semibold">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: r.diff > 0 ? COLORS.b : COLORS.a }} />
                      {r.diff > 0 ? result.b.label : result.a.label}</span>)}</td>
                </tr>
              ))}</tbody>
            </table>
            <p className="mt-3 text-xs text-muted">
              Brackets show the number of complaints. With {Math.min(result.a.reviews, result.b.reviews)} reviews on the smaller side, one review changes a share by about {Math.round(100 / Math.max(1, Math.min(result.a.reviews, result.b.reviews)))} points.
            </p>
          </Card>
          </>}

          {tab === "charts" && (
          <div className="grid gap-6 lg:grid-cols-2">
            {chart(topics.complaints, "a_neg", "b_neg", "Complaints by topic", "% of reviews with a complaint about the topic")}
            {chart(topics.praise, "a_pos", "b_pos", "Praise by topic", "% of reviews praising the topic")}
          </div>
          )}

          {tab === "fix" && (
          <div className="grid gap-6 lg:grid-cols-2">
            <Highlights summary={result.a.summary} sentiment="negative" limit={3} title={`Fix first: ${result.a.label}`} />
            <Highlights summary={result.b.summary} sentiment="negative" limit={3} title={`Fix first: ${result.b.label}`} />
          </div>
          )}
        </>
      )}
    </div>
  );
}
