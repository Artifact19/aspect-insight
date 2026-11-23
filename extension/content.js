// Content script: finds the reviews on the page and, after analysis, marks each aspect in its sentiment colour.
(() => {
  if (window.__aspectInsightLoaded) return;
  window.__aspectInsightLoaded = true;

  const STYLE_ID = "aspect-insight-style";
  const MAX_REVIEWS = 60;
  const BOILERPLATE = /\b(read more|read less|helpful|report abuse|verified purchase|fewer returns than average|customers say|translate review|see more reviews|sign in to|cookie|privacy policy|all rights reserved)\b/i;

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

  // One entry per review: the card, the elements holding its text (title and body), and its metadata.
  function collect(platform) {
    const found = [];
    const add = (card, textEls, meta = {}) => {
      let parts = textEls.filter(Boolean).map(textOf).filter(Boolean);
      if (parts.length === 2 && parts[1].toLowerCase().startsWith(parts[0].toLowerCase().replace(/[.!?]+$/, ""))) parts = [parts[1]];
      const text = parts.map((p) => (/[.!?]$/.test(p) ? p : `${p}.`)).join(" ");
      if (text.length < 15 || text.length > 4000 || BOILERPLATE.test(text.slice(0, 60)) && text.length < 80) return;
      if (found.some((f) => f.text === text)) return;
      const id = `ai-rev-${found.length + 1}`;
      card.setAttribute("data-ai-review-id", id);
      textEls.filter(Boolean).forEach((t) => t.setAttribute("data-ai-text", ""));
      found.push({ dom_id: id, text, author: clean(meta.author?.textContent), date: clean(meta.date?.textContent), rating: rating(meta.rating || "") });
    };

    if (platform === "amazon") {
      document.querySelectorAll('[data-hook="review"]').forEach((card) => {
        const body = card.querySelector('[data-hook="reviewRichContentContainer"], [data-hook="review-body"] span, [data-hook="review-collapsed"]');
        const title = card.querySelector('[data-hook="reviewTitle"], [data-hook="review-title"] > span:last-child');
        add(card, [title, body], {
          author: card.querySelector(".a-profile-name"),
          date: card.querySelector('[data-hook="review-date"]'),
          rating: card.querySelector('[data-hook="review-star-rating"], [data-hook="cmps-review-star-rating"]')?.textContent,
        });
      });
    } else if (platform === "flipkart") {
      document.querySelectorAll(".ZmyHeo, .t-ZTKy, div[class*='review-text']").forEach((el) => {
        const card = el.closest("div.col, div._27M-vq, div.RcXBOT") || el.parentElement;
        add(card, [el], { author: card?.querySelector("p._2sc7ZR, p._2V5EHH"), rating: card?.textContent });
      });
    } else if (platform === "google_maps") {
      document.querySelectorAll(".wiI7pd").forEach((el) => {
        const card = el.closest("[data-review-id], .jftiEf") || el.parentElement;
        add(card, [el], { author: card?.querySelector(".d4r55"), date: card?.querySelector(".rsqaWe"),
          rating: card?.querySelector("[aria-label*='star']")?.getAttribute("aria-label") });
      });
    } else if (platform === "goodreads") {
      document.querySelectorAll(".ReviewText__content").forEach((el) => {
        const card = el.closest("article, .ReviewCard") || el.parentElement;
        add(card, [el], { author: card?.querySelector(".ReviewerProfile__name") });
      });
    } else if (platform === "tripadvisor" || platform === "booking") {
      document.querySelectorAll('[data-automation="reviewCard"] q, [data-testid="review-card"] [data-testid="review-text"], .c-review__body').forEach((el) => {
        add(el.closest('[data-automation="reviewCard"], [data-testid="review-card"]') || el, [el]);
      });
    } else if (platform === "zomato") {
      document.querySelectorAll("section p").forEach((el) => {
        if (clean(el.textContent).length >= 30) add(el, [el]);
      });
    }

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
      const reviews = collect(platform);
      const title = (document.title || "").replace(/\s*[:|-]\s*(Amazon\.in|Amazon\.com|Amazon|Flipkart\.com|Flipkart|Zomato|Google Maps|Goodreads|Tripadvisor).*$/i, "").trim();
      reply({ title: title || document.title || "Web page", source_url: location.href, platform,
        domain: detectDomain(location.href, document.title, reviews.slice(0, 5).map((r) => r.text).join(" ")), reviews });
    } else if (msg?.type === "MARK_ASPECTS") {
      reply({ count: applyMarks(msg.marks) });
    } else if (msg?.type === "CLEAR_MARKS") {
      clearMarks();
      reply({ ok: true });
    }
    return false;
  });
})();
