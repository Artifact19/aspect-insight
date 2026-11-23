import React, { useEffect, useState } from "react";
import { SENTIMENT_COLORS, SOURCES, api, hostOf, pct, shortTitle, timeAgo } from "../lib.js";
import { ErrorBox, Icon } from "../components/ui.jsx";
import { go } from "./MainApp.jsx";

const SITES = ["Amazon", "Flipkart", "Zomato", "Google Maps", "Goodreads", "Tripadvisor"];

function MiniSplit({ s }) {
  const total = (s.positive || 0) + (s.neutral || 0) + (s.negative || 0);
  if (!total) return <div className="h-1.5 rounded-full bg-panel" />;
  return (
    <div className="flex h-1.5 gap-0.5 overflow-hidden rounded-full">
      {["positive", "neutral", "negative"].filter((k) => s[k]).map((k) => (
        <div key={k} style={{ width: `${(100 * s[k]) / total}%`, background: SENTIMENT_COLORS[k] }} />
      ))}
    </div>
  );
}

export default function Home() {
  const [captures, setCaptures] = useState(null);
  const [error, setError] = useState("");
  const [showSetup, setShowSetup] = useState(false);
  useEffect(() => { api.captures().then(setCaptures).catch((e) => setError(e.message)); }, []);

  const tile = "well group flex flex-col gap-2 p-5 text-left transition hover:border-brand-500/40 hover:bg-white";
  return (
    <div className="space-y-6">
      <section className="card p-7 sm:p-9">
        <div className="flex items-center gap-1.5 text-sm font-semibold text-brand-500"><Icon name="spark" className="h-4 w-4" />Generative aspect-based sentiment analysis</div>
        <h1 className="mt-2 text-[32px] font-extrabold leading-tight tracking-tight sm:text-[38px]">See what customers really think.</h1>
        <p className="mt-2 max-w-2xl text-[16px] text-ink2">
          Open a product, restaurant or hotel page and click the Aspect Insight button. Every opinion in its reviews is
          pulled out, grouped by topic and checked by a second model, all on this computer.
        </p>

        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <button className={tile} onClick={() => setShowSetup((v) => !v)}>
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-500"><Icon name="puzzle" /></span>
            <span className="font-bold">From a live page</span>
            <span className="text-sm text-muted">Use the Chrome extension on {SITES.slice(0, 3).join(", ")} and more</span>
          </button>
          <button className={tile} onClick={() => go("new")}>
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-possoft text-pos"><Icon name="paste" /></span>
            <span className="font-bold">Paste reviews</span>
            <span className="text-sm text-muted">One review per line, or upload a .txt or .csv file</span>
          </button>
          <button className={tile} onClick={() => go("new?demo")}>
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-neusoft text-neu"><Icon name="box" /></span>
            <span className="font-bold">Try a demo product</span>
            <span className="text-sm text-muted">Simulated reviews of 19 well-known products</span>
          </button>
        </div>

        {showSetup && (
          <div className="mt-4 rounded-2xl bg-panel/70 p-5 text-sm">
            <div className="font-bold">Set up the extension once (about 15 seconds)</div>
            <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-ink2">
              <li>In Chrome, open <code className="rounded bg-surface px-1.5 py-0.5 font-mono text-xs">chrome://extensions</code> and turn on <b>Developer mode</b>.</li>
              <li>Click <b>Load unpacked</b> and pick the <code className="rounded bg-surface px-1.5 py-0.5 font-mono text-xs">extension</code> folder of this project.</li>
              <li>Open a product page with reviews, click the Aspect Insight icon and press <b>Read the reviews</b>. The report appears here.</li>
            </ol>
            <div className="mt-3 flex flex-wrap gap-1.5">{SITES.map((s) => <span key={s} className="chip-soft bg-surface">{s}</span>)}</div>
          </div>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-baseline justify-between px-1">
          <h2 className="text-lg font-bold tracking-tight">Your reports</h2>
          {captures?.length > 0 && <span className="text-sm text-muted">{captures.length} saved on this computer</span>}
        </div>
        <ErrorBox error={error} />
        {captures && !captures.length && (
          <div className="card p-8 text-center text-muted">No reports yet. Read a live page with the extension, or paste some reviews.</div>
        )}
        <div className="grid gap-3 sm:grid-cols-2">
          {(captures || []).map((c) => {
            const total = c.opinions || 1;
            return (
              <a key={c.id} href={`#/r/${c.id}`} className="card group flex flex-col gap-3 p-5 transition hover:-translate-y-0.5 hover:bg-white/80">
                <div className="flex items-center gap-2 text-xs">
                  <span className="chip-soft">{SOURCES[c.source] || c.source}</span>
                  <span className="chip-soft">{c.domain}</span>
                  <span className="ml-auto text-muted">{timeAgo(c.created_at)}</span>
                </div>
                <div className="line-clamp-2 font-bold leading-snug">{shortTitle(c.title)}</div>
                <MiniSplit s={c.sentiment} />
                <div className="flex items-center gap-3 text-sm text-ink2">
                  <span>{c.review_count} reviews</span>
                  <span className="text-muted">·</span>
                  <span><b className="text-pos">{pct((c.sentiment.positive || 0) / total)}</b> positive</span>
                  <span className="text-muted">·</span>
                  <span><b className="text-neg">{pct((c.sentiment.negative || 0) / total)}</b> negative</span>
                  {hostOf(c.source_url) && <span className="ml-auto hidden truncate text-xs text-muted sm:inline">{hostOf(c.source_url)}</span>}
                </div>
              </a>
            );
          })}
        </div>
      </section>
    </div>
  );
}
