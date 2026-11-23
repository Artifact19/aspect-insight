/**
 * Printable product report: a plain, self-contained HTML document built from one capture, printed from a hidden
 * frame so the browser's "Save as PDF" turns it into a file. No charts library and nothing loaded from the network.
 */
import { SOURCES, shortTitle, titleCase } from "./lib.js";

const SENT = ["positive", "negative", "neutral"];
const TONE = { positive: "#5E8A72", negative: "#A86A5E", neutral: "#A48A62" };

const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (n, total) => (total ? Math.round((100 * n) / total) : 0);
const nice = (t) => titleCase(String(t || "").replace(/\s*&\s*/g, " & "));
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

function dateLabel(d = new Date()) {
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}

function bar(counts, total) {
  return `<div class="bar">${SENT.filter((k) => counts[k]).map((k) =>
    `<span style="width:${(100 * counts[k]) / total}%;background:${TONE[k]}"></span>`).join("")}</div>`;
}

function topicLine(e, sentiment) {
  const aspects = (e.top_aspects?.[sentiment] || []).slice(0, 3);
  const quote = e.examples?.[sentiment]?.[0];
  return `<li>
    <div class="row"><b>${esc(nice(e.name))}</b><span class="muted">${e[sentiment]} of ${plural(e.total, "mention")}</span></div>
    ${aspects.length ? `<div class="muted small">About ${esc(aspects.join(", "))}</div>` : ""}
    ${quote ? `<blockquote>“${esc(quote)}”</blockquote>` : ""}
  </li>`;
}

function findings(entities, sentiment, empty) {
  const rows = entities.filter((e) => e[sentiment] > 0).sort((a, b) => b[sentiment] - a[sentiment]).slice(0, 3);
  return rows.length ? `<ol class="findings">${rows.map((e) => topicLine(e, sentiment)).join("")}</ol>` : `<p class="muted">${empty}</p>`;
}

function countTable(rows, label, limit) {
  const shown = limit ? rows.slice(0, limit) : rows;
  return `<table class="counts">
    <thead><tr><th>${label}</th><th class="num">Mentions</th><th class="num">Positive</th><th class="num">Negative</th><th class="num">Neutral</th><th class="split">Split</th></tr></thead>
    <tbody>${shown.map((r) => `<tr>
      <td>${esc(nice(r.name))}</td><td class="num">${r.total}</td>
      ${SENT.map((k) => `<td class="num">${r[k]} <span class="muted">(${pct(r[k], r.total)}%)</span></td>`).join("")}
      <td class="split">${bar(r, r.total)}</td></tr>`).join("")}</tbody>
  </table>${limit && rows.length > limit ? `<p class="muted small">Top ${limit} of ${rows.length} shown, by number of mentions.</p>` : ""}`;
}

export function reportHtml(cap, generatedAt = new Date()) {
  const s = cap.summary;
  const total = s.opinions || 0;
  const name = shortTitle(cap.title);
  const entities = s.entities || [];
  const quads = cap.sentences.flatMap((sen) => sen.quads.map((q) => ({ ...q, review: sen.review + 1, sentence: sen.text })));
  const agree = quads.filter((q) => q.agrees !== false).length;
  const ratings = (cap.reviews || []).map((r) => r.rating).filter((r) => typeof r === "number");
  const avgRating = ratings.length ? (ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(1) : null;
  const brief = cap.brief;
  const source = SOURCES[cap.source] || cap.source;

  const glance = [
    ["Reviews analysed", cap.review_count + (cap.skipped ? ` <span class="muted">(${cap.skipped} duplicates removed)</span>` : "")],
    ["Opinions extracted", `${total} <span class="muted">(${(total / Math.max(1, cap.review_count)).toFixed(1)} per review)</span>`],
    ...SENT.map((k) => [titleCase(k), `${s.sentiment[k]} <span class="muted">(${pct(s.sentiment[k], total)}%)</span>`]),
    ...(avgRating ? [["Average star rating", `${avgRating} <span class="muted">from ${plural(ratings.length, "rated review")}</span>`]] : []),
    ["Sentiment check agreement", `${pct(agree, quads.length)}% <span class="muted">(${quads.length - agree} of ${quads.length} opinions disputed)</span>`],
  ];

  const words = SENT.filter((k) => s.top_opinions?.[k]?.length).map((k) =>
    `<p><span class="label">${titleCase(k)}</span> ${s.top_opinions[k].slice(0, 10).map((o) => `${esc(o.word)} <span class="muted">${o.count}</span>`).join(" · ")}</p>`).join("");

  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>${esc(`Review report - ${name}`)}</title>
<style>
  @page { size: A4; margin: 18mm 16mm 18mm 16mm;
    @bottom-left { content: "${name.replace(/["\\<>\r\n]/g, "")} · review analysis"; font: 8pt system-ui, sans-serif; color: #8a8a8a; }
    @bottom-right { content: counter(page) " / " counter(pages); font: 8pt system-ui, sans-serif; color: #8a8a8a; } }
  * { box-sizing: border-box; }
  html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { margin: 0; font: 10pt/1.5 "Segoe UI", system-ui, -apple-system, Helvetica, Arial, sans-serif; color: #262626; background: #fff; }
  main { max-width: 178mm; margin: 0 auto; }
  h1 { font-size: 19pt; font-weight: 600; margin: 2px 0 2px; letter-spacing: -0.01em; }
  h2 { font-size: 11pt; font-weight: 600; margin: 22px 0 8px; padding-bottom: 4px; border-bottom: 1px solid #dcdcdc; break-after: avoid; }
  h3 { font-size: 10pt; font-weight: 600; margin: 0 0 6px; }
  p { margin: 0 0 6px; }
  .eyebrow { font-size: 8pt; letter-spacing: 0.08em; text-transform: uppercase; color: #8a8a8a; }
  .muted { color: #7a7a7a; }
  .small { font-size: 8.5pt; }
  .label { display: inline-block; min-width: 62px; font-size: 8pt; text-transform: uppercase; letter-spacing: 0.06em; color: #7a7a7a; }
  .meta { color: #6a6a6a; font-size: 9pt; }
  .note { font-size: 8.5pt; color: #7a7a7a; margin-top: 4px; }
  .bar { display: flex; height: 6px; border-radius: 3px; overflow: hidden; background: #eee; }
  .bar span { display: block; height: 100%; }
  .legend { display: flex; gap: 14px; font-size: 8.5pt; color: #6a6a6a; margin-top: 5px; }
  .legend i { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 4px; vertical-align: 0; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; font-size: 8pt; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #7a7a7a; padding: 4px 6px; border-bottom: 1px solid #cfcfcf; }
  td { padding: 4px 6px; border-bottom: 1px solid #ececec; vertical-align: top; }
  tr { break-inside: avoid; }
  thead { display: table-header-group; }
  .num { text-align: right; white-space: nowrap; }
  .split { width: 22%; vertical-align: middle; }
  .glance td:first-child { color: #555; width: 45%; }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; break-inside: avoid; }
  .keep { break-inside: avoid; }
  .findings { margin: 0; padding: 0; list-style: none; }
  .findings li { margin-bottom: 10px; break-inside: avoid; }
  .row { display: flex; justify-content: space-between; gap: 8px; }
  blockquote { margin: 4px 0 0; padding: 2px 0 2px 9px; border-left: 2px solid #dcdcdc; color: #555; font-style: italic; font-size: 9pt; }
  .brief { font-size: 10.5pt; line-height: 1.6; }
  .opinions td { font-size: 8.5pt; }
  .opinions .sentence { color: #7a7a7a; max-width: 62mm; }
  .appendix { break-before: page; }
  @media screen { body { padding: 24px 16px; background: #f4f4f4; } main { background: #fff; padding: 18mm 16mm; box-shadow: 0 1px 4px rgba(0,0,0,.08); } }
</style></head>
<body><main>
  <div class="eyebrow">Review analysis report · ${esc(cap.domain)}</div>
  <h1>${esc(name)}</h1>
  ${name !== cap.title ? `<p class="meta">${esc(cap.title)}</p>` : ""}
  <p class="meta">${esc(source)}${cap.source === "demo" ? " (simulated reviews)" : ""} · ${plural(cap.review_count, "review")} · generated ${dateLabel(generatedAt)}${cap.source_url ? `<br>${esc(cap.source_url)}` : ""}</p>

  ${brief?.text ? `<h2>Summary</h2>
  <p class="brief">${esc(brief.text)}</p>
  <p class="note">Written by ${esc(brief.model || "the language model")} from counts computed in code. ${brief.unsupported_numbers?.length
    ? `These numbers could not be matched to the data: ${esc(brief.unsupported_numbers.join(", "))}.`
    : "Every number in it was checked against the extracted opinions."}</p>` : ""}

  <h2>At a glance</h2>
  ${total ? `${bar(s.sentiment, total)}
  <div class="legend">${SENT.map((k) => `<span><i style="background:${TONE[k]}"></i>${titleCase(k)} ${pct(s.sentiment[k], total)}%</span>`).join("")}</div>` : ""}
  <table class="glance" style="margin-top:10px"><tbody>${glance.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("")}</tbody></table>

  <div class="keep"><h2>Key findings</h2>
  <div class="cols">
    <section><h3>Strengths</h3>${findings(entities, "positive", "No praise was found.")}</section>
    <section><h3>Concerns</h3>${findings(entities, "negative", "No complaints were found.")}</section>
  </div></div>

  ${entities.length ? `<h2>Topics</h2>
  <p class="muted small">Each opinion is counted once under its main topic. Percentages are shares of that topic's mentions.</p>
  ${countTable(entities, "Topic")}` : ""}

  ${s.categories?.length ? `<h2>Categories</h2>
  ${countTable(s.categories, "Category", 15)}` : ""}

  ${words ? `<h2>Most frequent opinion words</h2>${words}` : ""}

  <h2>How this report was made</h2>
  <p>Each review was split into sentences. ${esc(cap.model || "A fine-tuned Flan-T5-base model")} wrote every opinion as an
  (aspect, category, opinion, sentiment) quadruple, using the ${esc(cap.domain.toLowerCase())} category set. A separate
  DeBERTa-v3-small classifier then re-checked each sentiment; it agreed on ${pct(agree, quads.length)}% of opinions.
  The models were trained on the MEMD-ABSA dataset.</p>
  <p class="muted small">Limitations: counts are of opinions, not of reviewers, so one long review can contribute several.
  Aspects marked "implied" were inferred without an explicit word in the text. Extraction is automatic and can miss or
  misread sarcasm, comparisons and mixed opinions${cap.source === "demo" ? "; the reviews in this report are simulated for demonstration" : ""}.</p>

  ${quads.length ? `<section class="appendix">
  <h2>Appendix: every extracted opinion</h2>
  <table class="opinions">
    <thead><tr><th class="num">Review</th><th>Aspect</th><th>Opinion</th><th>Category</th><th>Sentiment</th><th>Sentence</th></tr></thead>
    <tbody>${quads.map((q) => `<tr>
      <td class="num muted">${q.review}</td><td>${esc(q.aspect || "(implied)")}</td><td>${esc(q.opinion || "(implied)")}</td>
      <td>${esc(nice(q.category_text))}</td>
      <td>${titleCase(q.sentiment)}${q.agrees === false ? ` <span class="muted">(checker: ${esc(q.classifier_sentiment)})</span>` : ""}</td>
      <td class="sentence">${esc(q.sentence)}</td></tr>`).join("")}</tbody>
  </table></section>` : ""}
</main></body></html>`;
}

/** Opens the print dialog for one report; choosing "Save as PDF" there downloads it. */
export function printReport(cap) {
  const frame = document.createElement("iframe");
  frame.setAttribute("aria-hidden", "true");
  frame.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0;";
  const pageTitle = document.title;
  frame.onload = () => {
    // Chrome names the PDF after the page title.
    document.title = frame.contentDocument.title;
    frame.contentWindow.focus();
    frame.contentWindow.print();
    setTimeout(() => { document.title = pageTitle; frame.remove(); }, 500);
  };
  frame.srcdoc = reportHtml(cap);
  document.body.appendChild(frame);
}
