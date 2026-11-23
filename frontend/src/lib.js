export const SENTIMENT_COLORS = { positive: "#3F8660", negative: "#B9503F", neutral: "#AD6F2B" };
export const SENTIMENT_SOFT = { positive: "#E2ECDC", negative: "#F6E0D6", neutral: "#F5E6CF" };
export const SENTIMENTS = ["positive", "negative", "neutral"];

export const MODEL_COLORS = {
  paper: "#A39A92",
  t5_domain: "#4757CF",
  qwen_domain: "#C0683F",
  t5_plain: "#3F8660",
  t5_per_domain: "#B48A2C",
};

export const MODEL_NAMES = {
  paper: "Paper (best published)",
  t5_domain: "Flan-T5 + domain",
  qwen_domain: "Qwen2.5-1.5B LoRA + domain",
  t5_plain: "Flan-T5, no domain",
  t5_per_domain: "Flan-T5, one model per domain",
};

export const SOURCES = {
  amazon: "Amazon", flipkart: "Flipkart", zomato: "Zomato", google_maps: "Google Maps", tripadvisor: "Tripadvisor",
  booking: "Booking.com", goodreads: "Goodreads", web: "Web page", pasted: "Pasted", demo: "Demo · simulated",
};

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {}
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

export const api = {
  health: () => request("/api/health"),
  domains: () => request("/api/domains"),
  samples: (domain, n = 50, seed = 0) => request(`/api/samples?domain=${domain}&n=${n}&seed=${seed}`),
  analyze: (text, domain, constrained = false) =>
    request("/api/analyze", { method: "POST", body: { text, domain, constrained } }),
  batch: (reviews, domain) => request("/api/batch", { method: "POST", body: { reviews, domain } }),
  compare: (body) => request("/api/compare", { method: "POST", body }),
  results: () => request("/api/results"),
  demoList: () => request("/api/demo"),
  demoFile: (name) => request(`/api/demo/${name}`),
  summary: (domain, batches) => request("/api/summary", { method: "POST", body: { domain, batches } }),
  captures: () => request("/api/captures"),
  capture: (id) => request(`/api/captures/${id}`),
  createCapture: (body) => request("/api/captures", { method: "POST", body }),
  deleteCapture: (id) => request(`/api/captures/${id}`, { method: "DELETE" }),
  brief: (id, refresh = false) => request(`/api/captures/${id}/brief${refresh ? "?refresh=true" : ""}`, { method: "POST" }),
  ask: (id, question) => request(`/api/captures/${id}/ask`, { method: "POST", body: { question } }),
};

export function timeAgo(iso) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (!isFinite(s)) return "";
  if (s < 60) return "just now";
  const units = [[60, "minute"], [3600, "hour"], [86400, "day"], [604800, "week"]];
  let out = `${Math.floor(s / 60)} minutes ago`;
  for (const [sec, name] of units) {
    const n = Math.floor(s / sec);
    if (n >= 1) out = `${n} ${name}${n === 1 ? "" : "s"} ago`;
  }
  return out;
}

export function hostOf(url) {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return ""; }
}

export function hashParams() {
  const q = window.location.hash.split("?")[1] || "";
  return new URLSearchParams(q);
}

export function pct(x, digits = 0) {
  return `${(100 * (x || 0)).toFixed(digits)}%`;
}

export function titleCase(s) {
  return (s || "").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function toCsv(rows) {
  const esc = (v) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  if (!rows.length) return "";
  const keys = Object.keys(rows[0]);
  return [keys.join(","), ...rows.map((r) => keys.map((k) => esc(r[k])).join(","))].join("\n");
}

export function download(name, text, type = "text/csv") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}

export function parseReviewFile(text, name) {
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  if (!name.toLowerCase().endsWith(".csv")) return lines;
  const split = (line) => {
    const out = [];
    let cur = "", quoted = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (c === '"' && line[i + 1] === '"' && quoted) { cur += '"'; i++; }
      else if (c === '"') quoted = !quoted;
      else if (c === "," && !quoted) { out.push(cur); cur = ""; }
      else cur += c;
    }
    out.push(cur);
    return out;
  };
  const header = split(lines[0]).map((h) => h.trim().toLowerCase());
  const col = Math.max(0, header.findIndex((h) => ["review", "text", "comment", "sentence", "body"].includes(h)));
  const hasHeader = header.some((h) => ["review", "text", "comment", "sentence", "body"].includes(h));
  return lines.slice(hasHeader ? 1 : 0).map((l) => (split(l)[col] || "").trim()).filter(Boolean);
}

/** Product name without the specification list shops append: "Apple MacBook Air: M5 chip, 16GB ..." -> "Apple MacBook Air". */
export function shortTitle(title, limit = 50) {
  const t = (title || "").trim();
  let head = t.split(/\s*[:|([,–—]\s*|\s+-\s+/)[0].trim() || t;
  if (head.length > limit) head = head.slice(0, limit).replace(/\s+\S*$/, "");
  return head.replace(/(\s+(with|and|for|of|the|in|by|to))+$/i, "");
}
