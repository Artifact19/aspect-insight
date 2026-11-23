import React, { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { MODEL_COLORS, MODEL_NAMES, api } from "../lib.js";
import { Card, ErrorBox, Spinner, Stat } from "../components/ui.jsx";

const AXIS = { tick: { fontSize: 12, fill: "#8C8176" }, axisLine: false, tickLine: false };
const GRID = <CartesianGrid vertical={false} stroke="#E6DCCD" />;
const fmt = (v) => (v === null || v === undefined ? "–" : Number(v).toFixed(1));

function Takeaway({ children }) {
  return <p className="mt-4 rounded-2xl bg-brand-50/80 px-4 py-2.5 text-sm text-brand-700">{children}</p>;
}

export default function Evaluation() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.results().then(setData).catch((e) => setError(e.message)); }, []);
  if (error) return <ErrorBox error={error} />;
  if (!data) return <div className="card p-8"><Spinner text="Loading results…" /></div>;

  const series = ["paper", "t5_per_domain", "t5_plain", "t5_domain", "qwen_domain"];
  const domains = data.domains.map((d) => ({ ...d, paper: d.paper_best }));
  const laptop = data.domains.find((d) => d.domain === "Laptop");
  const tasks = ["AE", "ASPE", "CS", "AOS", "ACS", "ACOS"];
  const overallKeys = { "Flan-T5, no domain": "t5_plain", "Flan-T5 + domain": "t5_domain", "Qwen2.5-1.5B LoRA + domain": "qwen_domain" };
  const subtasks = tasks.map((t) => Object.fromEntries([["task", t], ...Object.entries(data.overall).map(([k, v]) => [overallKeys[k], v[t]])]));

  const promptRuns = data.prompting.map((p) => ({
    name: `${p.model.replace("-Instruct", "").replace("Qwen2.5-", "Qwen ")}, ${p.shots ? `${p.shots} ${p.selection === "similar" ? "retrieved" : "random"} examples` : "zero-shot"}`,
    acos: p.acos, ms: p.ms, kind: "prompting",
  }));
  const approaches = [
    { name: "Flan-T5 + domain (fine-tuned)", acos: data.overall["Flan-T5 + domain"]?.ACOS, ms: data.speed_ms["Flan-T5 + domain"], kind: "t5_domain" },
    { name: "Qwen 1.5B LoRA + domain (fine-tuned)", acos: data.overall["Qwen2.5-1.5B LoRA + domain"]?.ACOS, ms: data.speed_ms["Qwen2.5-1.5B LoRA + domain"], kind: "qwen_domain" },
    ...promptRuns.sort((a, b) => b.acos - a.acos),
  ];
  const wrong = ["Books", "Clothing", "Hotel", "Restaurant", "Laptop"].map((d) => ({
    domain: d,
    t5_plain: data.wrong_domain.find((w) => w.domain === d && w.model === "One model, no domain")?.share,
    t5_domain: data.wrong_domain.find((w) => w.domain === d && w.model === "One model + domain")?.share,
  }));
  const classifiers = data.classifiers.filter((c) => c.key !== "bagging_single");
  const errors = data.errors ? Object.entries(data.errors.missed_by_type).map(([k, v]) => ({ name: k, value: v })) : [];

  return (
    <div className="space-y-6">

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Flan-T5 + domain, ACOS F1" value={fmt(data.overall["Flan-T5 + domain"]?.ACOS)} hint={`${data.speed_ms["Flan-T5 + domain"]} ms per sentence (A100)`} color={MODEL_COLORS.t5_domain} />
        <Stat label="Qwen LoRA + domain, ACOS F1" value={fmt(data.overall["Qwen2.5-1.5B LoRA + domain"]?.ACOS)} hint="Tied with T5; 3× slower" color={MODEL_COLORS.qwen_domain} />
        <Stat label="Laptop with the domain fix" value={`${fmt(laptop?.t5_plain)} → ${fmt(laptop?.t5_domain)}`} hint="ACOS F1, one T5 model" />
        <Stat label="Best prompting (7B, retrieved)" value={fmt(Math.max(...data.prompting.map((p) => p.acos)))} hint="No training; about 20 points lower" />
      </div>

      <Card title="ACOS F1 by domain, compared with the paper" subtitle="Paper: best published model per domain (Table 9 of Cai et al., 2023)">
        <ResponsiveContainer width="100%" height={340}>
          <BarChart data={domains} barCategoryGap="18%" barGap={2}>
            {GRID}
            <XAxis dataKey="domain" {...AXIS} />
            <YAxis {...AXIS} domain={[0, 80]} />
            <Tooltip formatter={(v, n) => [fmt(v), MODEL_NAMES[n] || n]} cursor={{ fill: "#EEE6DA" }} />
            <Legend formatter={(v) => <span className="text-ink">{MODEL_NAMES[v]}</span>} wrapperStyle={{ fontSize: 13 }} />
            {series.map((k) => <Bar key={k} dataKey={k} fill={MODEL_COLORS[k]} radius={[4, 4, 0, 0]} maxBarSize={22} />)}
          </BarChart>
        </ResponsiveContainer>
        <Takeaway>One Flan-T5 model with the domain in its input is within 2.5 points of the paper on four domains and beats five separate per-domain models everywhere. Qwen LoRA exceeds the paper on Restaurant.</Takeaway>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Every sub-task, all test sentences" subtitle="F1 for progressively stricter matches">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={subtasks} barGap={2}>
              {GRID}
              <XAxis dataKey="task" {...AXIS} />
              <YAxis {...AXIS} domain={[0, 100]} />
              <Tooltip formatter={(v, n) => [fmt(v), MODEL_NAMES[n]]} cursor={{ fill: "#EEE6DA" }} />
              <Legend formatter={(v) => <span className="text-ink">{MODEL_NAMES[v]}</span>} wrapperStyle={{ fontSize: 12 }} />
              {["t5_plain", "t5_domain", "qwen_domain"].map((k) => <Bar key={k} dataKey={k} fill={MODEL_COLORS[k]} radius={[4, 4, 0, 0]} maxBarSize={18} />)}
            </BarChart>
          </ResponsiveContainer>
          <Takeaway>Finding the aspect (AE) reaches about 80 F1; requiring all four elements to match exactly (ACOS) brings it down to about 50. Naming the domain mainly fixes the category (CS +5 points).</Takeaway>
        </Card>

        <Card title="Categories from the wrong domain" subtitle="% of predicted quadruples whose category exists only in another domain">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={wrong} barGap={2}>
              {GRID}
              <XAxis dataKey="domain" {...AXIS} />
              <YAxis {...AXIS} unit="%" />
              <Tooltip formatter={(v, n) => [`${fmt(v)}%`, MODEL_NAMES[n]]} cursor={{ fill: "#EEE6DA" }} />
              <Legend formatter={(v) => <span className="text-ink">{MODEL_NAMES[v]}</span>} wrapperStyle={{ fontSize: 12 }} />
              {["t5_plain", "t5_domain"].map((k) => <Bar key={k} dataKey={k} fill={MODEL_COLORS[k]} radius={[4, 4, 0, 0]} maxBarSize={26} />)}
            </BarChart>
          </ResponsiveContainer>
          <Takeaway>Without the domain, 26% of Laptop predictions borrowed another domain's category. With it, 0.4%.</Takeaway>
        </Card>
      </div>

      <Card title="Fine-tuning versus prompting" subtitle="ACOS F1 on all test sentences; prompting uses no training at all">
        <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
          <ResponsiveContainer width="100%" height={approaches.length * 46 + 30}>
            <BarChart data={approaches} layout="vertical" margin={{ right: 40 }}>
              <CartesianGrid horizontal={false} stroke="#E6DCCD" />
              <XAxis type="number" {...AXIS} domain={[0, 60]} />
              <YAxis type="category" dataKey="name" width={250} tick={{ fontSize: 12, fill: "#2F2923" }} axisLine={false} tickLine={false} />
              <Tooltip formatter={(v) => fmt(v)} cursor={{ fill: "#EEE6DA" }} />
              <Bar dataKey="acos" radius={[0, 4, 4, 0]} maxBarSize={22}>
                {approaches.map((a, i) => <Cell key={i} fill={MODEL_COLORS[a.kind] || "#A39A92"} />)}
                <LabelList dataKey="acos" position="right" formatter={fmt} style={{ fontSize: 12, fill: "#2F2923" }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <table className="h-fit w-full border-collapse">
            <thead><tr><th>Approach</th><th className="text-right">ms / sentence</th></tr></thead>
            <tbody>{approaches.map((a) => <tr key={a.name}><td className="text-xs">{a.name}</td><td className="text-right">{fmt(a.ms)}</td></tr>)}</tbody>
          </table>
        </div>
        <Takeaway>Choosing similar training sentences as examples (retrieval) nearly doubles prompting accuracy over random ones, but a small fine-tuned model is still about 20 points better and over 20 times faster.</Takeaway>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Decoding strategies" subtitle="Flan-T5, all domains, seed 42">
          <table className="w-full border-collapse">
            <thead><tr><th>Strategy</th><th className="text-right">ACOS F1</th><th className="text-right">Precision</th><th className="text-right">ms</th></tr></thead>
            <tbody>{data.decoding.map((d) => (
              <tr key={d.strategy}><td>{d.strategy}</td><td className="text-right font-semibold">{fmt(d.acos)}</td><td className="text-right">{fmt(d.precision)}</td><td className="text-right">{fmt(d.ms)}</td></tr>
            ))}</tbody>
          </table>
          <Takeaway>Randomness hurts extraction; voting over 5 samples (self-consistency) is best by 0.5 points at 5× the cost, so the app uses greedy decoding.</Takeaway>
        </Card>

        <Card title="Why quadruples are missed" subtitle="Flan-T5, all domains, seed 42">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={errors} layout="vertical" margin={{ right: 40 }}>
              <CartesianGrid horizontal={false} stroke="#E6DCCD" />
              <XAxis type="number" {...AXIS} />
              <YAxis type="category" dataKey="name" width={200} tick={{ fontSize: 12, fill: "#2F2923" }} axisLine={false} tickLine={false} />
              <Tooltip cursor={{ fill: "#EEE6DA" }} />
              <Bar dataKey="value" fill={MODEL_COLORS.t5_domain} radius={[0, 4, 4, 0]} maxBarSize={20}>
                <LabelList dataKey="value" position="right" style={{ fontSize: 12, fill: "#2F2923" }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <Takeaway>Most misses are aspects never found at all; a wrong sentiment alone causes only 2%.</Takeaway>
        </Card>
      </div>

      <Card title="Sentiment classifier: handling the rare Neutral class" subtitle={`DeBERTa-v3-small, ${data.classifier_test_pairs?.toLocaleString() || ""} test pairs, mean of 3 seeds`}>
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <ResponsiveContainer width="100%" height={classifiers.length * 44 + 60}>
            <BarChart data={classifiers} layout="vertical" barGap={2} margin={{ right: 40 }}>
              <CartesianGrid horizontal={false} stroke="#E6DCCD" />
              <XAxis type="number" {...AXIS} domain={[0, 1]} />
              <YAxis type="category" dataKey="method" width={190} tick={{ fontSize: 12, fill: "#2F2923" }} axisLine={false} tickLine={false} />
              <Tooltip formatter={(v) => Number(v).toFixed(3)} cursor={{ fill: "#EEE6DA" }} />
              <Legend formatter={(v) => <span className="text-ink">{v === "macro_f1" ? "Macro-F1" : "Neutral F1"}</span>} wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="macro_f1" fill="#4757CF" radius={[0, 4, 4, 0]} maxBarSize={14} />
              <Bar dataKey="neutral_f1" fill="#C0683F" radius={[0, 4, 4, 0]} maxBarSize={14} />
            </BarChart>
          </ResponsiveContainer>
          <table className="h-fit w-full border-collapse">
            <thead><tr><th>Method</th><th className="text-right">Macro-F1</th><th className="text-right">ECE</th><th className="text-right">after scaling</th></tr></thead>
            <tbody>{classifiers.map((c) => (
              <tr key={c.key}><td className="text-xs">{c.method}</td><td className="text-right font-semibold">{c.macro_f1?.toFixed(3)}</td>
                <td className="text-right">{c.ece?.toFixed(3)}</td><td className="text-right">{c.ece_scaled?.toFixed(3)}</td></tr>
            ))}</tbody>
          </table>
        </div>
        <Takeaway>Class weights and focal loss are tied; balanced bagging and LLM-written Neutral data are significantly worse. Temperature scaling halves the calibration error, so the confidences shown in this app are honest.</Takeaway>
      </Card>

      {data.constrained?.runs?.length > 0 && (
        <Card title="Constrained decoding (no retraining)" subtitle="Flan-T5 may only write categories of the chosen domain; 3,583 test sentences, seed 42">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th>Model</th><th>Decoding</th>
                  <th className="text-right">ACOS F1</th>
                  <th className="text-right">Laptop ACOS F1</th>
                  <th className="text-right">Laptop wrong-domain</th>
                  <th className="text-right">All wrong-domain</th>
                  <th className="text-right">ms / sentence</th>
                </tr>
              </thead>
              <tbody>
                {data.constrained.runs.flatMap((r) => [
                  { label: r.label, mode: "Unconstrained", m: r.unconstrained },
                  { label: r.label, mode: "Constrained", m: r.constrained },
                ]).map((row, i) => (
                  <tr key={i}>
                    <td className="font-semibold">{row.label}</td>
                    <td>{row.mode}</td>
                    <td className="text-right font-bold">{fmt(row.m.overall_acos_f1)}</td>
                    <td className="text-right font-bold">{fmt(row.m.by_domain?.Laptop?.acos_f1)}</td>
                    <td className="text-right">{fmt(row.m.by_domain?.Laptop?.wrong_domain_share)}%</td>
                    <td className="text-right">{fmt(row.m.wrong_domain_share)}%</td>
                    <td className="text-right">{fmt(row.m.ms_per_sentence)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Takeaway>Constraining helps the model trained without the domain (+3.1 ACOS F1, Laptop +9.5) but changes nothing for the deployed model, which already names the domain, and is about 10x slower. So the app leaves it off; the lab can switch it on.</Takeaway>
        </Card>
      )}
    </div>
  );
}
