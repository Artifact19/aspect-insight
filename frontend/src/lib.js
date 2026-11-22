export const SENTIMENT_COLORS = { positive: "#0F8C74", negative: "#D0533C", neutral: "#D9A136" };
export const SENTIMENTS = ["positive", "negative", "neutral"];

export const MODEL_COLORS = {
  paper: "#A39A92",
  t5_domain: "#7B58A6",
  qwen_domain: "#E07155",
  t5_plain: "#00897B",
  t5_per_domain: "#BF8B1F",
};

export const MODEL_NAMES = {
  paper: "Paper (best published)",
  t5_domain: "Flan-T5 + domain",
  qwen_domain: "Qwen2.5-1.5B LoRA + domain",
  t5_plain: "Flan-T5, no domain",
  t5_per_domain: "Flan-T5, one model per domain",
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
  analyze: (text, domain) => request("/api/analyze", { method: "POST", body: { text, domain } }),
  batch: (reviews, domain) => request("/api/batch", { method: "POST", body: { reviews, domain } }),
  compare: (body) => request("/api/compare", { method: "POST", body }),
  results: () => request("/api/results"),
  demoList: () => request("/api/demo"),
  demoFile: (name) => request(`/api/demo/${name}`),
  summary: (domain, batches) => request("/api/summary", { method: "POST", body: { domain, batches } }),
};

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
