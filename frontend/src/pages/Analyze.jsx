import React, { useState } from "react";
import { api } from "../lib.js";
import { Card, DomainPicker, ErrorBox, Highlighted, QuadTable, SentimentSplit, Spinner, Stat } from "../components/ui.jsx";

export default function Analyze({ domains, domain, setDomain }) {
  const examples = domains.find((d) => d.name === domain)?.examples || [];
  const [text, setText] = useState(examples[0] || "");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    setBusy(true); setError("");
    try { setResult(await api.analyze(text, domain)); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const pickDomain = (d) => {
    setDomain(d);
    const ex = domains.find((x) => x.name === d)?.examples || [];
    setText(ex[0] || "");
    setResult(null);
  };

  const quads = result ? result.sentences.flatMap((s) => s.quads) : [];
  const discarded = result ? result.sentences.reduce((a, s) => a + s.discarded.length, 0) : 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-extrabold tracking-tight">Analyze a review</h2>
        <p className="mt-1 max-w-3xl text-muted">
          Paste a review and choose its domain. The generator writes every opinion as an (aspect, category, opinion, sentiment)
          quadruple; a separate classifier double-checks each sentiment with a calibrated confidence.
        </p>
      </div>

      <Card>
        <div className="space-y-4">
          <div>
            <div className="label mb-2">Domain</div>
            <DomainPicker domains={domains} value={domain} onChange={pickDomain} />
          </div>
          <div>
            <div className="label mb-2">Review</div>
            <textarea className="input min-h-[120px]" value={text} onChange={(e) => setText(e.target.value)}
              placeholder="Type or paste a review…" />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button className="btn-primary" onClick={run} disabled={busy || !text.trim()}>Extract opinions</button>
            <span className="ml-2 text-sm text-muted">Try:</span>
            {examples.map((ex, i) => (
              <button key={i} className="chip border-line bg-white text-xs font-semibold text-muted hover:border-brand-500 hover:text-ink"
                onClick={() => { setText(ex); setResult(null); }}>Example {i + 1}</button>
            ))}
          </div>
          {busy && <Spinner text="Generating quadruples…" />}
          <ErrorBox error={error} />
        </div>
      </Card>

      {result && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Opinions found" value={quads.length} hint={`${result.sentences.length} sentence${result.sentences.length === 1 ? "" : "s"}`} />
            <Stat label="Positive" value={result.summary.sentiment.positive} color="#0F8C74" />
            <Stat label="Negative" value={result.summary.sentiment.negative} color="#D0533C" />
            <Stat label="Time" value={`${(result.timing.total_ms / 1000).toFixed(2)} s`}
              hint={`${result.timing.generation_ms_per_sentence} ms per sentence to generate`} />
          </div>

          <Card title="What the review says" subtitle="Aspects are highlighted in their sentiment colour; opinion words are underlined. Hover for details.">
            <div className="space-y-5">
              {result.sentences.map((s, i) => (
                <div key={i} className={i ? "border-t border-line pt-5" : ""}>
                  <Highlighted text={s.text} quads={s.quads} />
                  <div className="mt-3"><QuadTable quads={s.quads} /></div>
                  {s.discarded.length > 0 && (
                    <p className="mt-2 text-xs text-muted">
                      {s.discarded.length} generated quadruple{s.discarded.length > 1 ? "s" : ""} discarded: category belongs to another domain.
                    </p>
                  )}
                </div>
              ))}
            </div>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Overall sentiment"><SentimentSplit counts={result.summary.sentiment} /></Card>
            <Card title="Under the hood" subtitle="What the model actually received and wrote">
              <div className="space-y-3 text-sm">
                {result.sentences.slice(0, 3).map((s, i) => (
                  <div key={i} className="rounded-lg bg-panel p-3 font-mono text-[12.5px] leading-relaxed">
                    <div><span className="text-muted">input&nbsp; </span>extract quadruples ({domain.toLowerCase()}): {s.model_input}</div>
                    <div className="mt-1"><span className="text-muted">output </span>{s.raw_output || "∅"}</div>
                  </div>
                ))}
                <p className="text-xs text-muted">
                  Model: {result.model} · greedy decoding · {discarded} discarded · classifier {result.timing.classifier_ms} ms
                </p>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
