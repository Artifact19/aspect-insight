import React, { useEffect, useState } from "react";
import { api, titleCase, timeAgo } from "../lib.js";
import { Card, ErrorBox, Icon, Spinner } from "../components/ui.jsx";

const RULES = [
  ["no_refund", "No refunds or money back"],
  ["no_discount", "No discounts, coupons or freebies"],
  ["no_replacement", "No free replacements"],
];

const STATUS = { approved: "bg-possoft text-[#2E6B4B]", rejected: "bg-negsoft text-[#8A3A2D]", pending: "bg-panel text-ink2" };

export default function Drafts() {
  const [captures, setCaptures] = useState([]);
  const [capId, setCapId] = useState("");
  const [cap, setCap] = useState(null);
  const [kind, setKind] = useState("reply");
  const [reviewIdx, setReviewIdx] = useState(0);
  const [topic, setTopic] = useState("");
  const [policy, setPolicy] = useState({ no_refund: true, no_discount: true, no_replacement: true });
  const [draft, setDraft] = useState(null);
  const [text, setText] = useState("");
  const [log, setLog] = useState([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.captures().then((list) => { setCaptures(list); if (list[0]) setCapId(list[0].id); }).catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (!capId) return;
    setDraft(null);
    Promise.all([api.capture(capId), api.drafts(capId)]).then(([c, d]) => {
      setCap(c); setLog(d);
      const neg = c.reviews.find((r) => r.quads.some((q) => q.sentiment === "negative"));
      setReviewIdx(neg ? neg.index : 0);
      const ent = (c.summary.entities || []).filter((e) => e.negative).sort((a, b) => b.negative - a.negative)[0];
      setTopic(ent?.name || "");
    }).catch((e) => setError(e.message));
  }, [capId]);

  const make = async () => {
    setBusy("Qwen2.5-1.5B is writing the draft, then the rules check it…"); setError("");
    try {
      const d = await api.createDraft({ capture_id: capId, kind, review_index: Number(reviewIdx), topic, policy });
      setDraft(d); setText(d.draft_text); setLog(await api.drafts(capId));
    } catch (e) { setError(e.message); }
    finally { setBusy(""); }
  };
  const decide = async (status) => {
    const d = await api.decideDraft(draft.id, { status, final_text: text });
    setDraft(d); setLog(await api.drafts(capId));
  };

  const complaints = (cap?.summary.entities || []).filter((e) => e.negative);
  return (
    <>
      <div className="grid gap-5 xl:grid-cols-[1fr_1.1fr]">
        <Card title="What to draft">
          <div className="space-y-4">
            <label className="block">
              <span className="label">Report</span>
              <select className="input mt-1.5 text-sm" value={capId} onChange={(e) => setCapId(e.target.value)}>
                {captures.map((c) => <option key={c.id} value={c.id}>{c.title.slice(0, 90)}</option>)}
              </select>
            </label>
            <div className="flex gap-2">
              {[["reply", "Reply to a customer"], ["ticket", "Ticket for the team"]].map(([k, l]) => (
                <button key={k} onClick={() => setKind(k)} className={`chip ${kind === k ? "border-brand-500 bg-brand-500 text-white" : "border-line bg-surface"}`}>{l}</button>
              ))}
            </div>
            {cap && (kind === "reply" ? (
              <label className="block">
                <span className="label">Review</span>
                <select className="input mt-1.5 text-sm" value={reviewIdx} onChange={(e) => setReviewIdx(e.target.value)}>
                  {cap.reviews.map((r) => (
                    <option key={r.index} value={r.index}>
                      {r.index + 1}. {r.quads.some((q) => q.sentiment === "negative") ? "[complaint] " : ""}{r.text.slice(0, 90)}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label className="block">
                <span className="label">Complaint topic</span>
                <select className="input mt-1.5 text-sm" value={topic} onChange={(e) => setTopic(e.target.value)}>
                  {complaints.map((e) => <option key={e.name} value={e.name}>{titleCase(e.name)} · {e.negative} complaints of {e.total}</option>)}
                </select>
              </label>
            ))}
            <div>
              <span className="label">Business rules the draft must follow</span>
              <div className="mt-1.5 space-y-2 rounded-2xl bg-panel/60 p-3.5 text-sm">
                {RULES.map(([k, l]) => (
                  <label key={k} className="flex cursor-pointer items-center gap-2.5">
                    <input type="checkbox" className="h-4 w-4 accent-brand-500" checked={!!policy[k]} onChange={(e) => setPolicy({ ...policy, [k]: e.target.checked })} />{l}
                  </label>
                ))}
              </div>
            </div>
            <button className="btn-primary" onClick={make} disabled={!!busy || !cap}><Icon name="spark" />Write draft</button>
            {busy && <Spinner text={busy} />}
            <ErrorBox error={error} />
          </div>
        </Card>

        <Card title="Draft for approval" subtitle="Nothing is sent anywhere; an approved draft is only saved here">
          {!draft ? <p className="text-sm text-muted">Pick a review or topic and press Write draft.</p> : (
            <div className="space-y-4">
              <div className="space-y-1.5">
                {draft.checks.checks.map((c, i) => (
                  <div key={i} className="flex items-center justify-between gap-3 text-sm">
                    <span className="inline-flex items-center gap-2 font-semibold">
                      <span className={`flex h-5 w-5 items-center justify-center rounded-full ${c.passed ? "bg-possoft text-pos" : "bg-negsoft text-neg"}`}>
                        <Icon name={c.passed ? "check" : "x"} className="h-3 w-3" />
                      </span>{c.rule}
                    </span>
                    <span className={`text-xs ${c.passed ? "text-muted" : "font-semibold text-neg"}`}>{c.detail}</span>
                  </div>
                ))}
              </div>
              <textarea className="input min-h-[140px] text-[15px]" value={text} onChange={(e) => setText(e.target.value)} disabled={draft.status !== "pending"} />
              {draft.status === "pending" ? (
                <div className="flex gap-2">
                  <button className="btn-primary" onClick={() => decide("approved")}><Icon name="check" />Approve</button>
                  <button className="btn-ghost" onClick={() => decide("rejected")}>Reject</button>
                </div>
              ) : <span className={`chip-soft ${STATUS[draft.status]}`}>{titleCase(draft.status)}</span>}
              <details className="text-sm">
                <summary className="cursor-pointer font-semibold text-muted">Facts given to the model</summary>
                <ul className="mt-2 space-y-1 rounded-2xl bg-panel/60 p-3 text-xs text-ink2">{draft.facts.map((f, i) => <li key={i}>• {f}</li>)}</ul>
              </details>
            </div>
          )}
        </Card>
      </div>

      {log.length > 0 && (
        <Card title="History for this report">
          <ul className="space-y-2.5">
            {log.map((d) => (
              <li key={d.id} className="well p-3.5 text-sm">
                <div className="mb-1 flex flex-wrap items-center gap-2 text-xs">
                  <span className="chip-soft">{d.kind === "reply" ? "Reply" : "Ticket"}</span>
                  <span className="font-semibold">{titleCase(d.target)}</span>
                  <span className="text-muted">{timeAgo(d.created_at)}</span>
                  <span className={`chip-soft ml-auto ${STATUS[d.status]}`}>{titleCase(d.status)}</span>
                </div>
                <p className="text-ink2">{d.final_text}</p>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}
