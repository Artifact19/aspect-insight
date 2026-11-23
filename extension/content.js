// Content script: finds the reviews on the page, can load more of them (scrolling, "show more" buttons, further review
// pages) and, after analysis, marks each aspect in its sentiment colour.
(() => {
  if (window.__aspectInsightLoaded) return;
  window.__aspectInsightLoaded = true;

  const STYLE_ID = "aspect-insight-style";
  const MAX_REVIEWS = 100;
  // Further review pages fetched in the background, per site (Zomato shows only 5 reviews a page).
  const MAX_PAGES = { amazon: 5, flipkart: 5, zomato: 15 };
  const LOAD_BUDGET_MS = 25000; // longest time spent scrolling the open page
  const BOILERPLATE = /\b(read more|read less|helpful|report abuse|verified purchase|fewer returns than average|customers say|translate review|see more reviews|sign in to|cookie|privacy policy|all rights reserved)\b/i;
  const EXPAND = /^(read more|see more|more|show more|read full review)$/i;
  const LOAD_MORE = /^((show|load|see|view)\s+(\d+\s+)?more\s+(reviews?|comments?|ratings?)|(show|load)\s+\d+\s+more|load more|more reviews)$/i;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      mark.ai-mark { color: inherit; padding: 0 3px; border-radius: 4px; font-weight: 600; cursor: help; }
      mark.ai-pos { background: #e2ecdc; box-shadow: inset 0 -2px 0 #3f8660; }
      mark.ai-neg { background: #f6e0d6; box-shadow: inset 0 -2px 0 #b9503f; }
      mark.ai-neu { background: #f5e6cf; box-shadow: inset 0 -2px 0 #ad6f2b; }
      .ai-badge { display: inline-block; margin: 4px 0; padding: 2px 9px; border-radius: 999px; font: 600 11px/1.6 system-ui, sans-serif; background: #4757cf; color: #fff; }
    `;
    document.head.appendChild(style);
  }

  function detectPlatform(url) {
    const u = (url || "").toLowerCase();
    if (u.includes("amazon.")) return "amazon";
    if (u.includes("flipkart.")) return "flipkart";
    if (u.includes("zomato.")) return "zomato";
    if (u.includes("google.") && u.includes("/maps")) return "google_maps";
    if (u.includes("tripadvisor.")) return "tripadvisor";
    if (u.includes("booking.com")) return "booking";
    if (u.includes("goodreads.")) return "goodreads";
    return "web";
  }

  function detectDomain(url, title, sample) {
    const blob = `${url} ${title} ${sample}`.toLowerCase();
    const rules = [
      ["Restaurant", /\b(zomato|swiggy|restaurant|cafe|bistro|pizza|biryani|dining|menu|waiter|chef|dish|food)\b/],
      ["Hotel", /\b(hotel|resort|booking\.com|check-in|room service|hostel|stay|tripadvisor)\b/],
      ["Books", /\b(goodreads|novel|paperback|hardcover|kindle edition|author|plot|chapters?)\b/],
      ["Clothing", /\b(shirt|t-shirt|jeans|kurta|dress|sneakers|shoes|hoodie|jacket|fabric|apparel|clothing)\b/],
      ["Laptop", /\b(laptop|macbook|thinkpad|ideapad|inspiron|xps|zenbook|vivobook|pavilion|rog|ryzen|ssd|gpu|trackpad)\b/],
    ];
    return (rules.find(([, re]) => re.test(blob)) || ["Laptop"])[0];
  }

  const clean = (s) => (s || "").replace(/\s+/g, " ").replace(/\s*(Read more|Read less)\s*/gi, " ").trim();
  const textOf = (el) => {
    if (!el) return "";
    const paras = el.querySelectorAll("p");
    return clean(paras.length ? [...paras].map((p) => p.textContent).join(" ") : el.textContent);
  };
  const rating = (s) => { const m = (s || "").match(/(\d+(?:\.\d+)?)\s*(?:out of\s*5|\/\s*5|stars?)/i); return m ? parseFloat(m[1]) : null; };
  // A link that does not leave the page (no href, "#…" or "javascript:…"), so clicking it is safe.
  const inertLink = (a) => { const h = (a.getAttribute("href") || "").trim(); return !h || /^(#|javascript:)/i.test(h); };
  const safeToClick = (el) => { const a = el.closest("a"); return !a || inertLink(a); };
  const visible = (el) => el.getClientRects().length > 0;
  const label = (el) => (el.textContent || "").replace(/\s+/g, " ").trim() || el.getAttribute("aria-label") || "";

  // One entry per review: the card, the elements holding its text (title and body), and its metadata.
  // `root` is the open page (live) or a review page fetched in the background (not live: nothing to mark later).
  function collect(platform, root = document, live = true) {
    const found = [];
    if (live) {
      root.querySelectorAll("[data-ai-review-id]").forEach((el) => el.removeAttribute("data-ai-review-id"));
      root.querySelectorAll("[data-ai-text]").forEach((el) => el.removeAttribute("data-ai-text"));
    }
    const add = (card, textEls, meta = {}) => {
      let parts = textEls.filter(Boolean).map(textOf).filter(Boolean);
      if (parts.length === 2 && parts[1].toLowerCase().startsWith(parts[0].toLowerCase().replace(/[.!?]+$/, ""))) parts = [parts[1]];
      const text = parts.map((p) => (/[.!?]$/.test(p) ? p : `${p}.`)).join(" ");
      if (text.length < 15 || text.length > 4000 || BOILERPLATE.test(text.slice(0, 60)) && text.length < 80) return;
      if (found.some((f) => f.text === text)) return;
      const id = live ? `ai-rev-${found.length + 1}` : "";
      if (live) {
        card.setAttribute("data-ai-review-id", id);
        textEls.filter(Boolean).forEach((t) => t.setAttribute("data-ai-text", ""));
      }
      found.push({ dom_id: id, text, author: clean(meta.author?.textContent), date: clean(meta.date?.textContent), rating: rating(meta.rating || "") });
    };

    if (platform === "amazon") {
      root.querySelectorAll('[data-hook="review"]').forEach((card) => {
        const body = card.querySelector('[data-hook="reviewRichContentContainer"], [data-hook="review-body"] span, [data-hook="review-collapsed"]');
        const title = card.querySelector('[data-hook="reviewTitle"], [data-hook="review-title"] > span:last-child');
        add(card, [title, body], {
          author: card.querySelector(".a-profile-name"),
          date: card.querySelector('[data-hook="review-date"]'),
          rating: card.querySelector('[data-hook="review-star-rating"], [data-hook="cmps-review-star-rating"]')?.textContent,
        });
      });
    } else if (platform === "flipkart") {
      root.querySelectorAll(".ZmyHeo, .t-ZTKy, div[class*='review-text']").forEach((el) => {
        const card = el.closest("div.col, div._27M-vq, div.RcXBOT") || el.parentElement;
        add(card, [el], { author: card?.querySelector("p._2sc7ZR, p._2V5EHH"), rating: card?.textContent });
      });
    } else if (platform === "google_maps") {
      root.querySelectorAll(".wiI7pd").forEach((el) => {
        const card = el.closest("[data-review-id], .jftiEf") || el.parentElement;
        add(card, [el], { author: card?.querySelector(".d4r55"), date: card?.querySelector(".rsqaWe"),
          rating: card?.querySelector("[aria-label*='star']")?.getAttribute("aria-label") });
      });
    } else if (platform === "goodreads") {
      root.querySelectorAll(".ReviewText__content").forEach((el) => {
        const card = el.closest("article, .ReviewCard") || el.parentElement;
        add(card, [el], { author: card?.querySelector(".ReviewerProfile__name") });
      });
    } else if (platform === "tripadvisor" || platform === "booking") {
      root.querySelectorAll('[data-automation="reviewCard"] q, [data-testid="review-card"] [data-testid="review-text"], .c-review__body').forEach((el) => {
        add(el.closest('[data-automation="reviewCard"], [data-testid="review-card"]') || el, [el]);
      });
    } else if (platform === "zomato") {
      // Class names are generated and all reviews share one container, but each review is a run of siblings:
      // author section, header (rating and "time-stamp"), then the text paragraph, which serves as the card.
      root.querySelectorAll("p.time-stamp").forEach((stamp) => {
        const header = stamp.parentElement;
        const body = header?.nextElementSibling;
        if (!body || body.tagName !== "P") return;
        const stars = (header.textContent.match(/^\s*(\d(?:\.\d)?)/) || [])[1];
        add(body, [body], { author: header.previousElementSibling?.querySelector("p"), date: stamp,
          rating: stars ? `${stars} stars` : "" });
      });
    }
    if (!live) return found;

    // Text the user selected on the page.
    if (!found.length) {
      const sel = window.getSelection()?.toString() || "";
      sel.split(/\n+/).map(clean).filter((s) => s.length >= 20).forEach((s) => found.push({ dom_id: "", text: s, author: "", date: "", rating: null }));
    }
    // Any other site: paragraphs inside review-like containers.
    if (!found.length) {
      document.querySelectorAll("[class*='review' i] p, [class*='comment' i] p, article p").forEach((el) => {
        if (found.length >= MAX_REVIEWS || el.closest("nav, header, footer, aside")) return;
        const t = clean(el.textContent);
        if (t.length >= 40 && t.length <= 1500 && !BOILERPLATE.test(t)) add(el, [el]);
      });
    }
    return found.slice(0, MAX_REVIEWS);
  }

  // ------------------------------------------------------------------ loading more reviews
  // Opens "More" / "Read more" on truncated reviews so their full text is read.
  function expandTruncated(platform) {
    const sel = platform === "google_maps"
      ? "button.w8nwRe, button[aria-label='See more']"
      : "[data-ai-review-id] button, [data-ai-review-id] [role='button'], [data-ai-review-id] a, [data-ai-review-id] span";
    let n = 0;
    document.querySelectorAll(sel).forEach((el) => {
      // A "Read more" link and the span inside it are one control: clicking both would collapse the review again.
      if (el.closest("[data-ai-expanded]") || el.querySelector("[data-ai-expanded]")) return;
      if (el.children.length > 1 || !EXPAND.test(label(el))) return;
      if (!safeToClick(el) || !visible(el)) return;
      el.dataset.aiExpanded = "1";
      el.click();
      n += 1;
    });
    return n;
  }

  // Clicks one "Show 10 more reviews" / "Load more" style button that stays on the page (never a link to elsewhere).
  function clickLoadMore() {
    for (const el of document.querySelectorAll("button, [role='button'], a, span")) {
      const t = label(el);
      if (!t || t.length > 40 || !LOAD_MORE.test(t)) continue;
      if (!safeToClick(el) || !visible(el) || el.disabled || el.closest("nav, header, footer")) continue;
      el.click();
      return true;
    }
    return false;
  }

  // Scrolls through the open page until no new reviews appear, the cap is reached or the time budget runs out.
  async function loadOnPage(platform, progress) {
    const start = Date.now();
    const [sx, sy] = [window.scrollX, window.scrollY];
    let last = -1;
    let stable = 0;
    while (Date.now() - start < LOAD_BUDGET_MS) {
      const expanded = expandTruncated(platform);
      const n = collect(platform).length;
      progress(n);
      if (n >= MAX_REVIEWS) break;
      const atBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4;
      if (n === last && !expanded && (n > 0 || atBottom)) { if (++stable >= 3) break; } else stable = 0;
      last = n;
      const clicked = clickLoadMore();
      const cards = document.querySelectorAll("[data-ai-review-id]");
      // Scrolling the last review into view also scrolls inner review lists (Google Maps) and triggers lazy loading.
      if (cards.length) cards[cards.length - 1].scrollIntoView({ block: "end" });
      else window.scrollBy(0, window.innerHeight * 0.9);
      await sleep(clicked ? 1500 : 1000);
    }
    window.scrollTo(sx, sy);
  }

  const absolute = (href, base) => { try { const u = new URL(href, base); u.hash = ""; return u.href; } catch { return ""; } };

  // The next page of reviews: the "Next" pagination link, or from a product page its "See all reviews" link.
  function nextPageUrl(platform, doc, base) {
    let a = null;
    if (platform === "amazon") {
      a = doc.querySelector(".a-pagination .a-last:not(.a-disabled) a[href]")
        || doc.querySelector('a[data-hook="see-all-reviews-link-foot"][href], a[data-hook="see-all-reviews-link"][href]');
    } else if (platform === "flipkart") {
      const links = [...doc.querySelectorAll("a[href]")];
      a = links.find((l) => clean(l.textContent).toUpperCase() === "NEXT")
        || (!/\/product-reviews\//.test(base) && links.find((l) => /\/product-reviews\//.test(l.getAttribute("href"))));
    } else if (platform === "zomato") {
      // The numbered page links all point to page 1, so follow the "next" arrow; from the restaurant page, its Reviews tab.
      const links = [...doc.querySelectorAll("a[href]")];
      a = links.find((l) => /page=\d+/.test(l.getAttribute("href")) && /chevron-right/i.test(l.textContent))
        || (!/\/reviews(\?|$)/.test(base) && links.find((l) => /\/reviews\/?$/.test(l.getAttribute("href"))));
    }
    return a ? absolute(a.getAttribute("href"), base) : "";
  }

  async function fetchPage(url) {
    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) return { stop: `the next review page answered ${res.status}` };
    const doc = new DOMParser().parseFromString(await res.text(), "text/html");
    if (/\/(ap\/signin|account\/login)/i.test(res.url) || doc.querySelector("form[name='signIn'], #ap_email")) {
      return { stop: "sign in to the site to let it show more review pages" };
    }
    if (doc.querySelector("form[action*='validateCaptcha'], #captchacharacters")) {
      return { stop: "the site asked for a check, so only this page was read" };
    }
    return { doc, url: res.url };
  }

  // Reads further review pages in the background without leaving the open page.
  async function loadOtherPages(platform, reviews, progress) {
    const maxPages = MAX_PAGES[platform] || 0;
    if (!maxPages) return { reviews, note: "", pages: 0 };
    const seen = new Set([absolute(location.href, location.href)]);
    let url = nextPageUrl(platform, document, location.href);
    let pages = 0;
    let note = "";
    while (url && !seen.has(url) && pages < maxPages && reviews.length < MAX_REVIEWS) {
      seen.add(url);
      await sleep(pages ? 800 : 200);
      let got;
      try { got = await fetchPage(url); } catch { note = "the next review page could not be loaded"; break; }
      if (got.stop) { note = got.stop; break; }
      pages += 1;
      const known = new Set(reviews.map((r) => r.text));
      const fresh = collect(platform, got.doc, false).filter((r) => !known.has(r.text));
      if (!fresh.length && pages > 1) break; // the site is repeating itself: no further pages
      reviews.push(...fresh);
      progress(reviews.length);
      url = nextPageUrl(platform, got.doc, got.url);
    }
    return { reviews: reviews.slice(0, MAX_REVIEWS), note, pages };
  }

  function pageInfo(platform, reviews, extra = {}) {
    const title = (document.title || "").replace(/\s*[:|-]\s*(Amazon\.in|Amazon\.com|Amazon|Flipkart\.com|Flipkart|Zomato|Google Maps|Goodreads|Tripadvisor).*$/i, "").trim();
    return { title: title || document.title || "Web page", source_url: location.href, platform,
      domain: detectDomain(location.href, document.title, reviews.slice(0, 5).map((r) => r.text).join(" ")), reviews, ...extra };
  }

  // ------------------------------------------------------------------ marking aspects
  function clearMarks() {
    document.querySelectorAll(".ai-badge").forEach((b) => b.remove());
    document.querySelectorAll("mark.ai-mark").forEach((m) => {
      const parent = m.parentNode;
      parent.replaceChild(document.createTextNode(m.textContent), m);
      parent.normalize();
    });
  }

  function markPhrase(card, quad) {
    const phrase = (quad.aspect || "").trim();
    if (!phrase) return false;
    const re = new RegExp(`(?<!\\w)${phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\s+/g, "\\s+")}(?!\\w)`, "i");
    const roots = card.querySelectorAll("[data-ai-text]").length ? card.querySelectorAll("[data-ai-text]") : [card];
    for (const root of roots) {
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let node;
      while ((node = walker.nextNode())) {
        if (node.parentElement.closest("mark.ai-mark, script, style")) continue;
        const m = re.exec(node.nodeValue);
        if (!m) continue;
        const mark = document.createElement("mark");
        mark.className = `ai-mark ai-${quad.sentiment.slice(0, 3)}`;
        mark.title = `${quad.category_text} · ${quad.sentiment}${quad.opinion ? ` · "${quad.opinion}"` : ""}`;
        const rest = node.splitText(m.index);
        rest.splitText(m[0].length);
        mark.textContent = rest.nodeValue;
        rest.parentNode.replaceChild(mark, rest);
        return true;
      }
    }
    return false;
  }

  function applyMarks(items) {
    ensureStyles();
    clearMarks();
    let count = 0;
    for (const item of items || []) {
      const card = document.querySelector(`[data-ai-review-id="${CSS.escape(item.dom_id)}"]`);
      if (!card) continue;
      let any = false;
      for (const q of item.quads) any = markPhrase(card, q) || any;
      if (!any && item.quads.length) {
        const badge = document.createElement("div");
        badge.className = "ai-badge";
        badge.textContent = item.quads.slice(0, 2).map((q) => `${q.category_text}: ${q.sentiment}`).join(" · ");
        (card.querySelector("[data-ai-text]") || card).prepend(badge);
      }
      count += 1;
    }
    return count;
  }

  chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
    if (msg?.type === "EXTRACT_REVIEWS") {
      const platform = detectPlatform(location.href);
      reply(pageInfo(platform, collect(platform)));
    } else if (msg?.type === "LOAD_AND_EXTRACT") {
      const platform = detectPlatform(location.href);
      const progress = (count) => chrome.runtime.sendMessage({ type: "LOAD_PROGRESS", count }).catch(() => {});
      (async () => {
        await loadOnPage(platform, progress);
        const onPage = collect(platform);
        const more = msg.pages ? await loadOtherPages(platform, [...onPage], progress) : { reviews: onPage, note: "", pages: 0 };
        reply(pageInfo(platform, more.reviews, { on_page: onPage.length, pages: more.pages, note: more.note }));
      })().catch((e) => reply({ error: String(e?.message || e) }));
      return true; // the reply is sent after loading finishes
    } else if (msg?.type === "MARK_ASPECTS") {
      reply({ count: applyMarks(msg.marks) });
    } else if (msg?.type === "CLEAR_MARKS") {
      clearMarks();
      reply({ ok: true });
    }
    return false;
  });
})();
