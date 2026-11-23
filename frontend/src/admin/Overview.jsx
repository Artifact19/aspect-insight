import React, { useEffect, useState } from "react";
import { SOURCES, api, shortTitle, timeAgo } from "../lib.js";
import { Card, Icon, Stat } from "../components/ui.jsx";

const PIPELINE = [
  { name: "Reviews", detail: "Chrome extension, pasted text or a demo file" },
  { name: "Flan-T5-base", detail: "writes every opinion as text, with the domain in its input" },
  { name: "Parser", detail: "turns the text into (aspect, category, opinion, sentiment)" },
  { name: "DeBERTa-v3-small", detail: "checks each sentiment, calibrated confidence" },
  { name: "Qwen2.5-1.5B-Instruct", detail: "writes the brief, answers and drafts from computed facts" },
  { name: "Checker", detail: "every number and claim must appear in the facts" },
];

const ROLES = {
  t5_domain: "Quadruple generator used by the app",
  t5_plain: "Same model without the domain, for the lab",
  qwen_domain: "LoRA fine-tuned LLM, for the lab",
};

export default function Overview({ health }) {
  const [captures, setCaptures] = useState([]);
  const [drafts, setDrafts] = useState([]);
  useEffect(() => {
    api.captures().then(setCaptures).catch(() => {});
    api.drafts().then(setDrafts).catch(() => {});
  }, []);
  const reviews = captures.reduce((a, c) => a + c.review_count, 0);
  const live = captures.filter((c) => !["demo", "pasted"].includes(c.source)).length;

  return (
    <>
      <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Reports saved" value={captures.length} hint={`${live} read from live pages`} />
        <Stat label="Reviews analysed" value={reviews} hint="across all reports" />
        <Stat label="Drafts approved" value={drafts.filter((d) => d.status === "approved").length} hint={`${drafts.length} drafted in total`} />
        <Stat label="Classifier temperature" value={health.classifier_temperature} hint="fitted on the Dev set" />
      </div>

      <Card title="How a review is processed" subtitle="Every step runs locally; no account or cloud service is involved">
        <ol className="grid gap-2.5 md:grid-cols-3 xl:grid-cols-6">
          {PIPELINE.map((p, i) => (
            <li key={p.name} className="well relative p-4">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-500 text-xs font-bold text-white">{i + 1}</div>
              <div className="mt-2 font-bold leading-snug">{p.name}</div>
              <div className="mt-0.5 text-xs text-muted">{p.detail}</div>
            </li>
          ))}
        </ol>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1.1fr_1fr]">
        <Card title="Models" subtitle={<span className="break-all font-mono text-xs">{health.models_dir}</span>}>
          <table className="w-full border-collapse">
            <thead><tr><th>Model</th><th>Role</th><th>Status</th></tr></thead>
            <tbody>
              {health.models.map((m) => (
                <tr key={m.key}>
                  <td className="font-semibold">{m.label}</td>
                  <td className="text-ink2">{ROLES[m.key]}</td>
                  <td>
                    <span className={`chip-soft ${m.loaded ? "bg-possoft" : m.available ? "" : "bg-negsoft"}`}>
                      {m.loaded ? "Loaded" : m.available ? "On disk" : "Missing"}
                    </span>
                  </td>
                </tr>
              ))}
              <tr><td className="font-semibold">DeBERTa-v3-small</td><td className="text-ink2">Sentiment check, temperature scaled</td><td><span className="chip-soft bg-possoft">Loaded</span></td></tr>
              <tr><td className="font-semibold">Qwen2.5-1.5B-Instruct</td><td className="text-ink2">Writes briefs, answers and drafts</td><td><span className="chip-soft">Loads on first use</span></td></tr>
            </tbody>
          </table>
        </Card>

        <Card title="Recent reports" right={<a href="#reports" className="btn-quiet py-1 text-xs">All reports<Icon name="arrow" className="h-3.5 w-3.5" /></a>}>
          {!captures.length ? <p className="text-sm text-muted">No reports yet.</p> : (
            <ul className="divide-y divide-[rgba(95,70,45,0.11)]">
              {captures.slice(0, 6).map((c) => (
                <li key={c.id}>
                  <a href={`#reports/${c.id}`} className="flex items-center gap-3 py-2.5 hover:text-brand-600">
                    <span className="chip-soft shrink-0">{SOURCES[c.source] || c.source}</span>
                    <span className="min-w-0 flex-1 truncate font-semibold">{shortTitle(c.title)}</span>
                    <span className="shrink-0 text-xs text-muted">{c.review_count} reviews · {timeAgo(c.created_at)}</span>
                  </a>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}
