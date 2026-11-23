import React, { useEffect, useMemo, useRef, useState } from "react";
import { SENTIMENT_COLORS, SOURCES, api, hostOf, shortTitle, titleCase, timeAgo } from "../lib.js";
import { ErrorBox, Highlighted, Icon, SentimentBadge, SentimentSplit, Spinner } from "../components/ui.jsx";
import { HighlightedSummary, MARKS } from "../components/insights.jsx";

const STARTERS = {
  Laptop: ["How is the battery life?", "What do people complain about most?", "Is it good for gaming?"],
  Restaurant: ["How is the food?", "What do people complain about most?", "Is it good value for money?"],
  Hotel: ["How clean are the rooms?", "What do guests complain about most?", "How is the location?"],
  Clothing: ["Does it fit true to size?", "What do people complain about most?", "How is the fabric quality?"],
  Books: ["How is the writing?", "What do readers dislike?", "Is the ending good?"],
};

function TopicColumn({ summary, sentiment, title, icon, onPick }) {
  const rows = (summary.entities || []).filter((e) => e[sentiment] > 0).sort((a, b) => b[sentiment] - a[sentiment]).slice(0, 3);
  const color = SENTIMENT_COLORS[sentiment];
  return (
    <section className="card p-6">
      <div className="mb-4 flex items-center gap-2.5">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl" style={{ background: `${color}1f`, color }}><Icon name={icon} /></span>
        <h3 className="text-[17px] font-bold tracking-tight">{title}</h3>
      </div>
      {!rows.length ? <p className="text-sm text-muted">Nothing here yet.</p> : (
        <ol className="space-y-5">
          {rows.map((e) => (
            <li key={e.name}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-bold">{titleCase(e.name)}</span>
                <span className="text-sm text-muted"><b style={{ color }}>{e[sentiment]}</b> of {e.total} mentions</span>
              </div>
              <div className="mt-1.5 h-1.5 rounded-full bg-panel">
                <div className="h-1.5 rounded-full" style={{ width: `${(100 * e[sentiment]) / e.total}%`, background: color }} />
              </div>
              {e.top_aspects?.[sentiment]?.length > 0 && (
                <div className="mt-1.5 text-xs text-muted">about {e.top_aspects[sentiment].slice(0, 3).join(", ")}</div>
              )}
              {e.examples?.[sentiment]?.[0] && (
                <blockquote className="mt-2 rounded-xl bg-surface px-3 py-2 text-sm italic text-ink2">“{e.examples[sentiment][0]}”</blockquote>
              )}
              <button className="mt-1.5 text-xs font-bold text-brand-500 hover:underline" onClick={() => onPick(e.name, sentiment)}>
                Show these reviews
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function Brief({ capture }) {
  const [brief, setBrief] = useState(capture.brief);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const run = async (refresh = false) => {
    setBusy(true); setError("");
    try { setBrief(await api.brief(capture.id, refresh)); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  useEffect(() => { if (!capture.brief && capture.summary.opinions) run(); }, []);
  const ok = brief && !brief.unsupported_numbers.length;
  return (
    <section className="card p-6">
      <div className="mb-3 flex items-center gap-2">
        <Icon name="spark" className="h-4 w-4 text-brand-500" />
        <span className="text-sm font-semibold text-brand-500">In short</span>
        {brief && !busy && <button className="btn-quiet ml-auto py-1 text-xs" onClick={() => run(true)}><Icon name="refresh" className="h-3.5 w-3.5" />Rewrite</button>}
      </div>
      {busy && <Spinner text="Writing a short summary (the first one loads the language model, up to a minute)…" />}
      <ErrorBox error={error} />
      {brief && !busy && (
        <>
          <HighlightedSummary text={brief.text} spans={brief.highlights} />
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
            {Object.entries(MARKS).map(([k, m]) => (
              <span key={k} className="inline-flex items-center gap-1.5"><span className="h-3 w-5 rounded" style={{ background: m.color }} />{m.label}</span>
            ))}
            <span className={`ml-auto inline-flex items-center gap-1 font-semibold ${ok ? "text-pos" : "text-neg"}`}>
              <Icon name={ok ? "check" : "alert"} className="h-3.5 w-3.5" />
              {ok ? "Every number checked against the reviews" : `Not supported by the data: ${brief.unsupported_numbers.join(", ")}`}
            </span>
          </div>
        </>
      )}
    </section>
  );
}

function Ask({ capture }) {
  const [q, setQ] = useState("");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const run = async (text) => {
    const question = (text ?? q).trim();
    if (!question) return;
    setQ(question); setBusy(true); setError("");
    try { setRes(await api.ask(capture.id, question)); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  return (
    <section className="card p-6">
      <div className="mb-3 flex items-center gap-2.5">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-50 text-brand-500"><Icon name="chat" /></span>
        <div>
          <h3 className="text-[17px] font-bold tracking-tight">Ask these reviews</h3>
          <p className="text-xs text-muted">Answers use only what the reviews say, and point to them</p>
        </div>
      </div>
      <div className="mb-3 flex flex-wrap gap-2">
        {(STARTERS[capture.domain] || STARTERS.Laptop).map((s) => (
          <button key={s} className="chip border-line bg-surface text-[13px] text-ink2 hover:border-brand-500" disabled={busy} onClick={() => run(s)}>{s}</button>
        ))}
      </div>
      <form className="flex items-center gap-2 rounded-full border border-line bg-surface py-1.5 pl-4 pr-1.5 focus-within:border-brand-500"
        onSubmit={(e) => { e.preventDefault(); run(); }}>
        <Icon name="search" className="h-4 w-4 text-muted" />
        <input className="min-w-0 flex-1 bg-transparent py-1 outline-none placeholder:text-muted" value={q} maxLength={300}
          onChange={(e) => setQ(e.target.value)} placeholder="Ask anything, e.g. does it overheat?" />
        <button className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-500 text-white shadow-accent disabled:opacity-50" disabled={busy || !q.trim()} aria-label="Ask">
          <Icon name="send" className="h-4 w-4" />
        </button>
      </form>
      <div className="mt-3"><ErrorBox error={error} /></div>
      {busy && <div className="mt-3"><Spinner text="Finding the reviews that answer this…" /></div>}
      {res && !busy && (
        <div className="mt-4 space-y-3">
          <p className="text-[16px] leading-relaxed">{res.answer}</p>
          <div className={`text-xs font-semibold ${res.verified ? "text-pos" : "text-neg"}`}>
            {res.verified ? "✓ Every number checked against the reviews" : `Not supported by the data: ${res.unsupported_numbers.join(", ")}`}
          </div>
          {res.citations.length > 0 && (
            <div className="grid gap-2 sm:grid-cols-2">
              {res.citations.map((c, i) => (
                <div key={i} className="well p-3 text-sm">
                  <div className="mb-1 flex items-center justify-between gap-2 text-xs">
                    <span className="font-bold text-ink2">Review {c.review} · {c.aspect}</span>
                    <SentimentBadge sentiment={c.sentiment} />
                  </div>
                  <p className="italic text-ink2">“{c.text}”</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function Reviews({ capture, filter, setFilter, listRef }) {
  const [all, setAll] = useState(false);
  const byReview = useMemo(() => {
    const m = new Map();
    capture.sentences.forEach((s) => m.set(s.review, [...(m.get(s.review) || []), s]));
    return m;
  }, [capture]);
  const entityOf = (q) => q.category_text.split(" - ")[0].replace("&", " and ");
  const shown = (capture.reviews || []).filter((r) => {
    const qs = r.quads || [];
    if (filter.topic) return qs.some((q) => q.sentiment === filter.sentiment && entityOf(q) === filter.topic);
    if (filter.kind === "complaints") return qs.some((q) => q.sentiment === "negative");
    if (filter.kind === "praise") return qs.some((q) => q.sentiment === "positive");
    return true;
  });
  const list = all ? shown : shown.slice(0, 6);
  return (
    <section className="card p-6" ref={listRef}>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <h3 className="mr-2 text-[17px] font-bold tracking-tight">The reviews</h3>
        {[["all", "All"], ["complaints", "With a complaint"], ["praise", "With praise"]].map(([k, l]) => (
          <button key={k} onClick={() => setFilter({ kind: k })}
            className={`chip text-[13px] ${!filter.topic && filter.kind === k ? "border-brand-500 bg-brand-50 text-brand-700" : "border-line bg-surface text-ink2"}`}>{l}</button>
        ))}
        {filter.topic && (
          <button className="chip border-brand-500 bg-brand-50 text-[13px] text-brand-700" onClick={() => setFilter({ kind: "all" })}>
            {filter.sentiment === "negative" ? "Complaints" : "Praise"} about {filter.topic}<Icon name="x" className="h-3.5 w-3.5" />
          </button>
        )}
        <span className="ml-auto text-sm text-muted">{shown.length} of {capture.reviews.length}</span>
      </div>
      <div className="space-y-3">
        {list.map((r) => (
          <article key={r.index} className="well p-4">
            <div className="mb-1 flex items-center gap-2 text-xs text-muted">
              <span className="font-semibold text-ink2">Review {r.index + 1}</span>
              {r.author && <span>· {r.author}</span>}
              {r.rating != null && <span>· {r.rating}★</span>}
              {r.date && <span className="truncate">· {r.date.replace(/^Reviewed in .+? on /i, "")}</span>}
            </div>
            <div className="text-[15px] leading-8">
              {(byReview.get(r.index) || []).map((s, i) => (
                <React.Fragment key={i}>{i > 0 && " "}<Highlighted text={s.text} quads={s.quads} size="inline" /></React.Fragment>
              ))}
            </div>
          </article>
        ))}
      </div>
      {shown.length > 6 && (
        <button className="btn-ghost mt-4 w-full" onClick={() => setAll((v) => !v)}>{all ? "Show fewer" : `Show all ${shown.length} reviews`}</button>
      )}
      <p className="mt-4 text-xs text-muted">
        Aspects are shaded in their sentiment colour and opinion words are underlined. Hover a word for its category.
      </p>
    </section>
  );
}

export default function Report({ id }) {
  const [cap, setCap] = useState(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState({ kind: "all" });
  const listRef = useRef(null);
  useEffect(() => { api.capture(id).then(setCap).catch((e) => setError(e.message)); }, [id]);

  if (error) return <ErrorBox error={error} />;
  if (!cap) return <div className="card p-10"><Spinner text="Opening the report…" /></div>;

  const s = cap.summary;
  const pick = (topic, sentiment) => {
    setFilter({ topic, sentiment });
    setTimeout(() => listRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 30);
  };
  const host = hostOf(cap.source_url);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <a href="#/" className="btn-quiet -ml-3"><Icon name="back" />All reports</a>
        <a href={`/admin#reports/${cap.id}`} className="btn-quiet">Details<Icon name="arrow" className="h-4 w-4" /></a>
      </div>

      <section className="card p-6 sm:p-7">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="chip-soft">{SOURCES[cap.source] || cap.source}</span>
          <span className="chip-soft">{cap.domain}</span>
          {cap.source === "demo" && <span className="chip-soft bg-neusoft">Simulated reviews</span>}
          <span className="ml-auto text-muted">{timeAgo(cap.created_at)}</span>
        </div>
        <h1 className="mt-3 text-[28px] font-extrabold leading-tight tracking-tight">{shortTitle(cap.title)}</h1>
        {shortTitle(cap.title) !== cap.title && <p className="mt-1 line-clamp-2 text-sm text-muted">{cap.title}</p>}
        <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
          <span><b className="text-ink">{cap.review_count}</b> reviews</span>
          <span><b className="text-ink">{s.opinions}</b> opinions found</span>
          {cap.skipped > 0 && <span>{cap.skipped} duplicates skipped</span>}
          {host && <a href={cap.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-brand-500 hover:underline">{host}<Icon name="external" className="h-3.5 w-3.5" /></a>}
        </div>
        <div className="mt-5"><SentimentSplit counts={s.sentiment} big /></div>
      </section>

      {s.opinions > 0 && <Brief capture={cap} />}

      <div className="grid gap-5 md:grid-cols-2">
        <TopicColumn summary={s} sentiment="positive" title="What people love" icon="heart" onPick={pick} />
        <TopicColumn summary={s} sentiment="negative" title="What needs fixing" icon="alert" onPick={pick} />
      </div>

      <Ask capture={cap} />
      <Reviews capture={cap} filter={filter} setFilter={setFilter} listRef={listRef} />
    </div>
  );
}
