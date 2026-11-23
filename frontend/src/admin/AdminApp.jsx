import React, { useEffect, useState } from "react";
import { Icon, Logo, Spinner } from "../components/ui.jsx";
import Overview from "./Overview.jsx";
import Reports from "./Reports.jsx";
import Analyze from "./Analyze.jsx";
import Compare from "./Compare.jsx";
import ModelLab from "./ModelLab.jsx";
import Evaluation from "./Evaluation.jsx";

const SECTIONS = [
  { id: "overview", label: "Overview", icon: "grid", title: "Admin console", hint: "The models, the pipeline and everything saved on this computer", Component: Overview },
  { id: "reports", label: "Reports", icon: "database", title: "Reports", hint: "Every captured review set: categories, all extracted opinions and timing", Component: Reports },
  { id: "analyze", label: "Analyze", icon: "search", title: "Analyze one review", hint: "The quadruples for a single review, with the raw model input and output", Component: Analyze },
  { id: "compare", label: "Compare", icon: "scale", title: "Compare two products", hint: "Topic by topic, as a share of each side's reviews", Component: Compare },
  { id: "lab", label: "Model lab", icon: "flask", title: "Model lab", hint: "One sentence through several generators and decoding strategies", Component: ModelLab },
  { id: "evaluation", label: "Evaluation", icon: "chart", title: "Evaluation", hint: "Test-set results against the published MEMD-ABSA baselines", Component: Evaluation },
];

function route() {
  const [id, ...rest] = window.location.hash.replace(/^#\/?/, "").split("/");
  return { id: SECTIONS.some((s) => s.id === id) ? id : "overview", arg: rest.join("/") };
}

export default function AdminApp({ health, domains, ready, refreshHealth }) {
  const [r, setR] = useState(route());
  const [domain, setDomain] = useState("Laptop");
  useEffect(() => {
    const on = () => setR(route());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  const section = SECTIONS.find((s) => s.id === r.id);
  const Page = section.Component;
  const needsModels = r.id !== "evaluation";

  return (
    <div className="grid min-h-screen gap-3.5 p-3.5 lg:grid-cols-[208px_minmax(0,1fr)]">
      <aside className="glass flex flex-col gap-1 rounded-[26px] px-3 py-4 lg:sticky lg:top-3.5 lg:h-[calc(100vh-28px)]">
        <a href="/admin" className="flex items-center gap-2.5 px-2 pb-4">
          <Logo className="h-9 w-9" />
          <span className="text-[16px] font-extrabold tracking-tight">Aspect Insight</span>
        </a>
        <nav className="flex flex-row flex-wrap gap-1 lg:flex-col">
          {SECTIONS.map((s) => (
            <a key={s.id} href={`#${s.id}`}
              className={`flex items-center gap-3 rounded-2xl px-3.5 py-2.5 text-[14px] font-semibold transition ${r.id === s.id ? "bg-brand-50 text-brand-700" : "text-ink2 hover:bg-surface"}`}>
              <Icon name={s.icon} />{s.label}
            </a>
          ))}
        </nav>
        <a href="/" className="mt-auto hidden items-center gap-3 rounded-2xl px-3.5 py-2.5 text-[14px] font-semibold text-ink2 hover:bg-surface lg:flex">
          <Icon name="external" />Main view
        </a>
      </aside>

      <div className="flex min-w-0 flex-col gap-3.5">
        <header className="glass flex flex-wrap items-center gap-3 rounded-[22px] px-5 py-3.5">
          <div className="min-w-0">
            <h1 className="text-xl font-extrabold tracking-tight">{section.title}</h1>
            <p className="text-sm text-muted">{section.hint}</p>
          </div>
          <span className={`ml-auto inline-flex items-center gap-2 rounded-full border px-3.5 py-2 text-[13px] font-semibold ${ready ? "border-pos/30 text-[#2E6B4B]" : "border-line text-muted"}`}>
            <span className={`h-2 w-2 rounded-full ${ready ? "bg-pos" : "animate-pulse bg-muted"}`} />
            {ready ? `Flan-T5 + DeBERTa · ${health.device.toUpperCase()}` : "Loading models…"}
          </span>
        </header>
        <main className="min-w-0 space-y-5 pb-8">
          {needsModels && !ready ? (
            <div className="card p-10"><Spinner text="Loading the models (about 30 seconds on first start)…" /></div>
          ) : (
            <Page key={r.id} arg={r.arg} health={health} domains={domains} domain={domain} setDomain={setDomain} refreshHealth={refreshHealth} />
          )}
        </main>
      </div>
    </div>
  );
}
