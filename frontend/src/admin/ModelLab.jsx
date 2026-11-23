import React, { useState } from "react";
import { MODEL_COLORS, api, titleCase } from "../lib.js";
import { Card, DomainPicker, ErrorBox, QuadTable, Spinner } from "../components/ui.jsx";

const DECODING = [
  { id: "greedy", label: "Greedy", help: "Always take the most likely next token." },
  { id: "beam", label: "Beam search (4)", help: "Keep the 4 best partial answers at every step." },
  { id: "sampling", label: "Sampling", help: "Pick tokens at random, weighted by probability." },
];

export default function Lab({ domains, domain, setDomain, health }) {
  const models = health?.models || [];
  const [text, setText] = useState("The battery dies fast and the fan is loud, but the screen is gorgeous.");
  const [selected, setSelected] = useState(models.filter((m) => m.available).map((m) => m.key));
  const [decoding, setDecoding] = useState("greedy");
  const [temperature, setTemperature] = useState(0.7);
  const [topP, setTopP] = useState(0.9);
  const [constrained, setConstrained] = useState(false);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const toggle = (k) => setSelected((s) => (s.includes(k) ? s.filter((x) => x !== k) : [...s, k]));
  const run = async () => {
    setBusy(true); setError("");
    try {
      setResult(await api.compare({ text, domain, models: models.map((m) => m.key).filter((k) => selected.includes(k)),
        decoding, temperature, top_p: topP, constrained }));
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  const qwenCold = selected.includes("qwen_domain") && !models.find((m) => m.key === "qwen_domain")?.loaded;

  return (
    <div className="space-y-6">

      <Card>
        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
          <div className="space-y-4">
            <div><div className="label mb-2">Domain</div><DomainPicker domains={domains} value={domain} onChange={setDomain} /></div>
            <div><div className="label mb-2">Sentence</div>
              <textarea className="input min-h-[90px]" value={text} onChange={(e) => setText(e.target.value)} /></div>
            <div>
              <div className="label mb-2">Models</div>
              <div className="flex flex-wrap gap-2">
                {models.map((m) => (
                  <label key={m.key} className={`chip cursor-pointer gap-2 ${selected.includes(m.key) ? "border-brand-500 bg-brand-50" : "border-line bg-surface"} ${m.available ? "" : "opacity-40"}`}>
                    <input type="checkbox" className="accent-brand-500" disabled={!m.available}
                      checked={selected.includes(m.key)} onChange={() => toggle(m.key)} />
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: MODEL_COLORS[m.key] }} />
                    {m.label}
                  </label>
                ))}
              </div>
            </div>
          </div>
          <div className="space-y-4 rounded-2xl bg-panel/60 p-4">
            <div>
              <div className="label mb-2">Decoding</div>
              <div className="space-y-2">
                {DECODING.map((d) => (
                  <label key={d.id} className="flex cursor-pointer items-start gap-2 text-sm">
                    <input type="radio" name="decoding" className="mt-1 accent-brand-500" checked={decoding === d.id} onChange={() => setDecoding(d.id)} />
                    <span><b>{d.label}</b><br /><span className="text-muted">{d.help}</span></span>
                  </label>
                ))}
              </div>
            </div>
            {decoding === "sampling" && (
              <div className="space-y-3">
                <label className="block text-sm"><span className="flex justify-between"><b>Temperature</b><span>{temperature.toFixed(2)}</span></span>
                  <input type="range" min="0.1" max="1.5" step="0.05" value={temperature} onChange={(e) => setTemperature(+e.target.value)} className="w-full accent-brand-500" /></label>
                <label className="block text-sm"><span className="flex justify-between"><b>Top-p</b><span>{topP.toFixed(2)}</span></span>
                  <input type="range" min="0.5" max="1" step="0.05" value={topP} onChange={(e) => setTopP(+e.target.value)} className="w-full accent-brand-500" /></label>
                <p className="text-xs text-muted">Run several times: sampling gives a different answer each time.</p>
              </div>
            )}
            <div className="border-t border-line pt-3">
              <label className="flex cursor-pointer items-start gap-2 text-sm">
                <input type="checkbox" className="mt-1 accent-brand-500" checked={constrained} onChange={(e) => setConstrained(e.target.checked)} />
                <span><b>Constrained decoding</b><br /><span className="text-xs text-muted">Flan-T5 may only write categories that exist in {domain}. About 10x slower; no retraining.</span></span>
              </label>
            </div>
          </div>
        </div>
        <div className="mt-5 flex items-center gap-4">
          <button className="btn-primary" onClick={run} disabled={busy || !text.trim() || !selected.length}>Compare</button>
          {busy && <Spinner text={qwenCold ? "Loading Qwen for the first time (up to a minute)…" : "Generating…"} />}
        </div>
        <div className="mt-3"><ErrorBox error={error} /></div>
      </Card>

      {result && (
        <div className="grid gap-6">
          {result.models.map((m) => {
            const r = m.result;
            const quads = r ? r.sentences.flatMap((s) => s.quads) : [];
            const discarded = r ? r.sentences.flatMap((s) => s.discarded) : [];
            return (
              <Card key={m.key} title={<span className="flex items-center gap-2"><span className="h-3 w-3 rounded-full" style={{ background: MODEL_COLORS[m.key] }} />{m.label}{r?.constrained && <span className="chip-soft bg-possoft">constrained</span>}</span>}
                subtitle={m.note}
                right={r && <div className="text-right text-sm"><div className="text-2xl font-extrabold">{r.timing.generation_ms_per_sentence} ms</div><div className="text-muted">per sentence</div></div>}>
                {m.error ? <ErrorBox error={m.error} /> : (
                  <div className="space-y-4">
                    <div>
                      <div className="label mb-1">Raw generated text</div>
                      <div className="rounded-2xl bg-panel/60 p-3 font-mono text-[12.5px] leading-relaxed">
                        {r.sentences.map((s, i) => <div key={i}>{s.raw_output || "∅"}</div>)}
                      </div>
                    </div>
                    <div><div className="label mb-1">Parsed quadruples</div><QuadTable quads={quads} /></div>
                    {discarded.length > 0 && (
                      <div className="rounded-2xl bg-neusoft px-4 py-3 text-sm">
                        <b>{discarded.length} discarded</b> because the category belongs to another domain:{" "}
                        {discarded.map((d, i) => <span key={i} className="font-mono text-xs">{i ? ", " : ""}{titleCase(d.category_text)}</span>)}
                      </div>
                    )}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
