// Side panel: reads the reviews on the active tab, sends them to the local app and shows a short result.
const APP = "http://127.0.0.1:8000";
const COLORS = { positive: "#3f8660", neutral: "#ad6f2b", negative: "#b9503f" };
const SITES = {
  amazon: "Amazon", flipkart: "Flipkart", zomato: "Zomato", google_maps: "Google Maps", tripadvisor: "Tripadvisor",
  booking: "Booking.com", goodreads: "Goodreads", web: "Web page",
};

const $ = (id) => document.getElementById(id);
let tabId = null;
let page = null;
let capture = null;
let marked = false;
let loading = false;

async function api(path, body) {
  const res = await fetch(`${APP}${path}`, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let msg = res.statusText;
    try { const d = await res.json(); msg = typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail); } catch {}
    throw new Error(msg);
  }
  return res.json();
}

function show(id, on) { $(id).classList.toggle("hidden", !on); }
function setError(msg) { $("error").textContent = msg || ""; show("error", !!msg); }
function setBusy(msg) { $("busy-text").textContent = msg || ""; show("busy", !!msg); $("read").disabled = !!msg; }
function setNote(msg) { $("note").textContent = msg || ""; show("note", !!msg); }
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

async function checkApp() {
  const s = $("status");
  try {
    const h = await api("/api/health");
    s.className = "status ok";
    s.lastElementChild.textContent = `Ready · ${h.device.toUpperCase()}`;
    return true;
  } catch {
    s.className = "status bad";
    s.lastElementChild.textContent = "App not running";
    return false;
  }
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  return tab || null;
}

async function askPage(type, extra = {}) {
  const msg = { type, ...extra };
  try {
    return await chrome.tabs.sendMessage(tabId, msg);
  } catch {
    await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
    return chrome.tabs.sendMessage(tabId, msg);
  }
}

async function inspectPage() {
  if (loading) return;
  const tab = await activeTab();
  if (!tab?.id) return;
  if (tab.id !== tabId) { capture = null; show("result", false); setNote(""); }
  tabId = tab.id;
  const url = tab.url || "";
  if (!/^https?:/i.test(url)) {
    page = null;
    $("page-title").textContent = "Open a product, restaurant or hotel page";
    $("site").textContent = "Browser page";
    $("found").textContent = "";
    return;
  }
  try {
    page = await askPage("EXTRACT_REVIEWS");
    $("page-title").textContent = page.title || tab.title;
    $("site").textContent = SITES[page.platform] || "Web page";
    $("domain").value = page.domain;
    const n = page.reviews.length;
    $("found").textContent = n ? `${n} review${n === 1 ? "" : "s"} found` : "No reviews found yet";
  } catch {
    page = null;
    $("page-title").textContent = tab.title || "Reload the page to read it";
    $("found").textContent = "Reload the page once";
  }
}

function renderResult(cap) {
  const s = cap.summary;
  const total = s.opinions || 1;
  $("meta").textContent = `${cap.review_count} reviews · ${s.opinions} opinions${cap.updated ? " · updated this page's earlier report" : ""}`;
  $("bar").innerHTML = ["positive", "neutral", "negative"].filter((k) => s.sentiment[k])
    .map((k) => `<div style="width:${(100 * s.sentiment[k]) / total}%;background:${COLORS[k]}"></div>`).join("");
  $("legend").innerHTML = ["positive", "neutral", "negative"]
    .map((k) => `<span><i style="background:${COLORS[k]}"></i>${k[0].toUpperCase() + k.slice(1)} <b>${Math.round((100 * (s.sentiment[k] || 0)) / total)}%</b></span>`).join("");
  const topics = (kind) => {
    const rows = (s.entities || []).filter((e) => e[kind]).sort((a, b) => b[kind] - a[kind]).slice(0, 3);
    if (!rows.length) return `<li class="none">None found</li>`;
    return rows.map((e) => `<li><span>${e.name.replace(/\b\w/g, (c) => c.toUpperCase())}</span><b>${e[kind]}</b></li>`).join("");
  };
  $("loved").innerHTML = topics("positive");
  $("complaints").innerHTML = topics("negative");
  marked = false;
  $("mark").textContent = "Show on page";
  show("result", true);
}

async function read() {
  setError("");
  if (!(await checkApp())) {
    setError("Start the app first: double-click Start.bat in the project folder, then try again.");
    return;
  }
  setNote("");
  await inspectPage();
  if (!page) { setError("This tab is not a web page the extension can read."); return; }
  if ($("auto").checked) await loadMore();
  if (!page.reviews.length) { setError("No reviews found. Open the page's reviews section, or select some review text, then press the button again."); return; }
  setBusy(`Reading ${page.reviews.length} reviews with the local models…`);
  try {
    capture = await api("/api/captures", {
      title: page.title, source_url: page.source_url, source: page.platform, domain: $("domain").value,
      reviews: page.reviews,
    });
    renderResult(capture);
  } catch (e) {
    setError(e.message);
  } finally {
    setBusy("");
  }
}

// Asks the page to scroll, open "show more" buttons and fetch further review pages, then uses what it collected.
async function loadMore() {
  loading = true;
  setBusy("Loading more reviews from the page…");
  try {
    const res = await askPage("LOAD_AND_EXTRACT", { pages: true });
    if (res?.error) throw new Error(res.error);
    if (res?.reviews?.length >= page.reviews.length) page = res;
    const n = page.reviews.length;
    $("found").textContent = n ? `${plural(n, "review")} found` : "No reviews found yet";
    const fromPages = n - (page.on_page ?? n);
    const parts = [];
    if (fromPages > 0) parts.push(`${page.on_page} on this page and ${fromPages} from ${plural(page.pages, "more review page")}. Only the ones on this page can be marked.`);
    if (page.note) parts.push(`Stopped early: ${page.note}.`);
    setNote(parts.join(" "));
  } catch (e) {
    setNote(`Could not load more reviews (${e.message}), so only the ones already on the page were read.`);
  } finally {
    loading = false;
    setBusy("");
  }
}

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg?.type === "LOAD_PROGRESS" && loading && sender.tab?.id === tabId) {
    setBusy(`Loading more reviews… ${msg.count} so far`);
  }
});

async function toggleMarks() {
  if (!capture) return;
  if (marked) {
    await askPage("CLEAR_MARKS");
    marked = false;
    $("mark").textContent = "Show on page";
  } else {
    const res = await askPage("MARK_ASPECTS", { marks: capture.page_marks });
    marked = true;
    $("mark").textContent = res?.count ? `Hide marks (${res.count})` : "Hide marks";
  }
}

try { $("auto").checked = localStorage.getItem("autoLoad") !== "0"; } catch {}
$("auto").addEventListener("change", () => { try { localStorage.setItem("autoLoad", $("auto").checked ? "1" : "0"); } catch {} });
$("read").addEventListener("click", read);
$("mark").addEventListener("click", toggleMarks);
$("open").addEventListener("click", () => capture && chrome.tabs.create({ url: `${APP}/#/r/${capture.id}` }));
chrome.tabs.onActivated.addListener(inspectPage);
chrome.tabs.onUpdated.addListener((id, info) => { if (id === tabId && info.status === "complete") inspectPage(); });

checkApp();
inspectPage();
setInterval(checkApp, 15000);
