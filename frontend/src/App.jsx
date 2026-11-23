import React, { useEffect, useState } from "react";
import { api } from "./lib.js";
import MainApp from "./main/MainApp.jsx";
import AdminApp from "./admin/AdminApp.jsx";

/** Waits for the models to load, then shows the main view ("/") or the admin console ("/admin"). */
export default function App() {
  const [health, setHealth] = useState(null);
  const [domains, setDomains] = useState([]);
  const isAdmin = window.location.pathname.replace(/\/+$/, "").endsWith("/admin");

  useEffect(() => {
    let stop = false;
    const poll = async () => {
      try {
        const [h, d] = await Promise.all([api.health(), api.domains()]);
        if (!stop) { setHealth(h); setDomains(d); }
      } catch {
        if (!stop) setTimeout(poll, 2000);
      }
    };
    poll();
    return () => { stop = true; };
  }, []);

  const refreshHealth = () => api.health().then(setHealth).catch(() => {});
  const props = { health, domains, ready: !!health, refreshHealth };
  return isAdmin ? <AdminApp {...props} /> : <MainApp {...props} />;
}
