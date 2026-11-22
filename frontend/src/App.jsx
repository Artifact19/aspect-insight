import React, { useEffect, useState } from "react";
import { api } from "./lib.js";
import Analyze from "./pages/Analyze.jsx";
import Batch from "./pages/Batch.jsx";
import Compare from "./pages/Compare.jsx";
import Lab from "./pages/Lab.jsx";
import Evaluation from "./pages/Evaluation.jsx";
import { Spinner } from "./components/ui.jsx";

const PAGES = [
  { id: "analyze", label: "Analyze", Component: Analyze },
  { id: "batch", label: "Batch insights", Component: Batch },
  { id: "compare", label: "Compare", Component: Compare },
  { id: "lab", label: "Model lab", Component: Lab },
  { id: "evaluation", label: "Evaluation", Component: Evaluation },
];

function currentPage() {
  const id = window.location.hash.replace("#", "");
  return PAGES.some((p) => p.id === id) ? id : "analyze";
}

export default function App() {
  const [page, setPage] = useState(currentPage());
  const [health, setHealth] = useState(null);
  const [domains, setDomains] = useState([]);
  const [domain, setDomain] = useState("Laptop");
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    const onHash = () => setPage(currentPage());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    let stop = false;
    const poll = async () => {
      try {
        const [h, d] = await Promise.all([api.health(), api.domains()]);
        if (stop) return;
        setHealth(h);
        setDomains(d);
        setStatus("ready");
      } catch {
        if (!stop) { setStatus("loading"); setTimeout(poll, 2000); }
      }
    };
    poll();
    return () => { stop = true; };
  }, []);

  const Page = PAGES.find((p) => p.id === page).Component;
  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <img src="/favicon.svg" alt="" className="h-9 w-9" />
            <div>
              <h1 className="text-lg font-extrabold leading-tight text-brand-700">Aspect Insight</h1>
              <p className="text-xs text-muted">Generative aspect-based sentiment analysis on MEMD-ABSA</p>
            </div>
          </div>
          <nav className="flex flex-wrap gap-1">
            {PAGES.map((p) => (
              <a key={p.id} href={`#${p.id}`}
                className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${page === p.id ? "bg-brand-50 text-brand-700" : "text-muted hover:text-ink"}`}>
                {p.label}
              </a>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        {status !== "ready" && page !== "evaluation" ? (
          <div className="card p-8"><Spinner text="Loading models (about 30 seconds on first start)…" /></div>
        ) : (
          <Page domains={domains} domain={domain} setDomain={setDomain} health={health} />
        )}
      </main>
      <footer className="mx-auto max-w-6xl px-4 pb-10 text-xs text-muted sm:px-6">
        {health ? `Running on ${health.device.toUpperCase()} · classifier temperature ${health.classifier_temperature}` : ""}
      </footer>
    </div>
  );
}
