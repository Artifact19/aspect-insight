import React, { useEffect, useMemo, useState } from "react";
import { api, parseReviewFile } from "../lib.js";
import { DomainPicker, ErrorBox, Icon, Spinner, Tabs } from "../components/ui.jsx";
import { go } from "./MainApp.jsx";

export default function NewReport({ domains }) {
  const [mode, setMode] = useState(window.location.hash.includes("demo") ? "demo" : "paste");
  const [title, setTitle] = useState("");
  const [domain, setDomain] = useState("Laptop");
  const [text, setText] = useState("");
  const [demos, setDemos] = useState([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const reviews = useMemo(() => text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean), [text]);
  useEffect(() => { api.demoList().then(setDemos).catch(() => setDemos([])); }, []);

  const create = async (body) => {
    setError(""); setBusy(`Reading ${body.reviews.length} reviews…`);
    try { go(`r/${(await api.createCapture(body)).id}`); }
    catch (e) { setError(e.message); setBusy(""); }
  };

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setText(parseReviewFile(await file.text(), file.name).join("\n"));
    if (!title) setTitle(file.name.replace(/\.(csv|txt)$/i, ""));
    e.target.value = "";
  };

  const openDemo = async (d) => {
    setBusy(`Reading ${d.reviews} reviews of ${d.label}…`); setError("");
    try {
      const f = await api.demoFile(d.name);
      await create({ title: f.label, source: "demo", domain: f.domain, reviews: f.reviews.map((r) => ({ text: r })) });
    } catch (e) { setError(e.message); setBusy(""); }
  };

  const byDomain = demos.reduce((acc, d) => ({ ...acc, [d.domain]: [...(acc[d.domain] || []), d] }), {});

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <a href="#/" className="btn-quiet -ml-3"><Icon name="back" />All reports</a>
        <Tabs value={mode} onChange={setMode} tabs={[{ id: "paste", label: "Paste reviews" }, { id: "demo", label: "Demo product" }]} />
      </div>

      {busy ? (
        <div className="card flex flex-col items-center gap-3 p-12 text-center">
          <Spinner text={busy} />
          <p className="max-w-md text-sm text-muted">Flan-T5 writes every opinion as a quadruple, then DeBERTa checks each sentiment. This takes a second or two per review on a laptop GPU.</p>
        </div>
      ) : mode === "paste" ? (
        <section className="card space-y-5 p-6 sm:p-7">
          <div>
            <h2 className="text-xl font-extrabold tracking-tight">Paste reviews</h2>
            <p className="text-sm text-muted">One review per line. A review can have several sentences.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-[1fr_auto]">
            <label className="block">
              <span className="label">Product or place</span>
              <input className="input mt-1.5" placeholder="e.g. Lenovo IdeaPad Slim 5" value={title} onChange={(e) => setTitle(e.target.value)} />
            </label>
            <div>
              <span className="label">Kind</span>
              <div className="mt-1.5"><DomainPicker domains={domains} value={domain} onChange={setDomain} /></div>
            </div>
          </div>
          <textarea className="input min-h-[220px] text-[14px]" value={text} onChange={(e) => setText(e.target.value)}
            placeholder={"The battery easily lasts a full day.\nThe keyboard is great but the trackpad feels cheap.\n…"} />
          <ErrorBox error={error} />
          <div className="flex flex-wrap items-center gap-3">
            <button className="btn-primary px-5" disabled={!reviews.length}
              onClick={() => create({ title: title.trim() || "Pasted reviews", source: "pasted", domain, reviews: reviews.map((r) => ({ text: r })) })}>
              <Icon name="spark" />Analyze {reviews.length || ""} review{reviews.length === 1 ? "" : "s"}
            </button>
            <label className="btn-ghost cursor-pointer">Upload .txt or .csv<input type="file" accept=".txt,.csv" className="hidden" onChange={onFile} /></label>
          </div>
        </section>
      ) : (
        <section className="card space-y-5 p-6 sm:p-7">
          <div>
            <h2 className="text-xl font-extrabold tracking-tight">Demo products</h2>
            <p className="text-sm text-muted">Simulated reviews that describe traits widely reported for each product. They are not real customer reviews.</p>
          </div>
          <ErrorBox error={error} />
          {Object.entries(byDomain).map(([d, items]) => (
            <div key={d}>
              <div className="label mb-2">{d}</div>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                {items.map((x) => (
                  <button key={x.name} onClick={() => openDemo(x)}
                    className="well px-4 py-3 text-left transition hover:border-brand-500/40 hover:bg-white">
                    <div className="font-semibold leading-snug">{x.label}</div>
                    <div className="text-xs text-muted">{x.reviews} reviews</div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
