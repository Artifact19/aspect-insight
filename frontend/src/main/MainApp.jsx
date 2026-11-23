import React, { useEffect, useState } from "react";
import { Icon, Logo, Spinner } from "../components/ui.jsx";
import Home from "./Home.jsx";
import NewReport from "./NewReport.jsx";
import Report from "./Report.jsx";

function route() {
  const h = window.location.hash.replace(/^#\/?/, "");
  if (h.startsWith("r/")) return { page: "report", id: h.slice(2) };
  if (h.startsWith("new")) return { page: "new" };
  return { page: "home" };
}

export function go(path) {
  window.location.hash = `#/${path}`;
  window.scrollTo({ top: 0 });
}

export default function MainApp({ health, domains, ready }) {
  const [r, setR] = useState(route());
  useEffect(() => {
    const on = () => setR(route());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);

  return (
    <div className="min-h-screen pb-16">
      <header className="sticky top-0 z-20 px-4 pt-4">
        <div className="glass mx-auto flex max-w-[960px] items-center gap-3 rounded-[22px] py-2.5 pl-3.5 pr-2.5 shadow-soft">
          <a href="#/" className="flex min-w-0 items-center gap-2.5">
            <Logo />
            <span className="min-w-0">
              <span className="block text-lg font-extrabold leading-tight tracking-tight">Aspect Insight</span>
              <span className="block truncate text-xs text-muted">What customers love and complain about, read from real reviews</span>
            </span>
          </a>
          <div className="ml-auto flex items-center gap-2">
            <span className={`hidden items-center gap-2 rounded-full border px-3.5 py-2 text-[13px] font-semibold sm:inline-flex ${ready ? "border-pos/30 text-[#2E6B4B]" : "border-line text-muted"}`}>
              <span className={`h-2 w-2 rounded-full ${ready ? "bg-pos" : "animate-pulse bg-muted"}`} />
              {ready ? `Models ready · ${health.device.toUpperCase()}` : "Loading models…"}
            </span>
            <button className="btn-ghost" onClick={() => go("new")}><Icon name="plus" />New report</button>
          </div>
        </div>
      </header>

      <main className="mx-auto mt-6 max-w-[960px] px-4">
        {!ready ? (
          <div className="card p-10"><Spinner text="Loading the models (about 30 seconds on first start)…" /></div>
        ) : r.page === "report" ? (
          <Report id={r.id} key={r.id} />
        ) : r.page === "new" ? (
          <NewReport domains={domains} />
        ) : (
          <Home />
        )}
      </main>

      <footer className="mx-auto mt-10 max-w-[960px] px-4 text-center text-xs text-muted">
        Runs entirely on this computer · <a className="font-semibold hover:text-ink" href="/admin">Admin console</a>
      </footer>
    </div>
  );
}
