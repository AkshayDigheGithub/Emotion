/*
  Moodshop gifting — no backend, no database, no accounts.

  The buyer writes a short note; it is encoded into the link's #fragment and
  they send that link themselves. A fragment is never transmitted to the
  server, so the note exists only in the two people's browsers. Nothing here
  talks to an API, and the page works exactly as before if this file fails
  to load.
*/
(function () {
  "use strict";

  var MAX_NAME = 40;
  var MAX_NOTE = 240;
  var STORE_URL = "https://moodshop.lol/";

  var emotion = (document.body && document.body.getAttribute("data-emotion")) || "this";

  function clamp(s, n) {
    s = String(s == null ? "" : s).replace(/\s+/g, " ").trim();
    return s.length > n ? s.slice(0, n) : s;
  }

  /* ---------- url-safe base64 over utf-8 ---------- */

  function encode(obj) {
    var bytes = new TextEncoder().encode(JSON.stringify(obj));
    var bin = "";
    for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function decode(str) {
    var s = str.replace(/-/g, "+").replace(/_/g, "/");
    while (s.length % 4) s += "=";
    var bin = atob(s);
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return JSON.parse(new TextDecoder().decode(bytes));
  }

  /* ---------- styles (themed off each page's own CSS vars) ---------- */

  var css =
    ".gift-note{" +
      "margin:0 0 2.6rem 0;padding:1.2rem 1.4rem;border-radius:14px;" +
      "background:rgba(255,255,255,0.22);border:1px solid rgba(255,255,255,0.3);" +
      "backdrop-filter:blur(3px);" +
    "}" +
    ".gift-note p{font-family:'Nunito Sans',sans-serif;margin:0;}" +
    ".gift-note .gift-for{" +
      "font-size:0.7rem;letter-spacing:0.18em;text-transform:uppercase;" +
      "font-weight:700;opacity:0.65;margin-bottom:0.5rem;" +
    "}" +
    ".gift-note .gift-msg{" +
      "font-family:'Cormorant Garamond',serif;font-size:1.15rem;line-height:1.7;" +
    "}" +
    ".gift-note .gift-from{font-size:0.85rem;opacity:0.7;margin-top:0.6rem;}" +
    ".gift-open{margin-top:0.8rem;}" +
    ".gift-btn{" +
      "font-family:'Nunito Sans',sans-serif;font-size:0.8rem;letter-spacing:0.06em;" +
      "text-transform:uppercase;background:none;border:1px solid currentColor;" +
      "border-radius:999px;padding:0.55rem 1.3rem;color:inherit;opacity:0.65;" +
      "cursor:pointer;transition:opacity 0.2s ease;" +
    "}" +
    ".gift-btn:hover{opacity:1;}" +
    ".gift-form{" +
      "margin-top:1.2rem;padding:1.2rem 1.3rem;border-radius:14px;max-width:34rem;" +
      "background:rgba(255,255,255,0.14);border:1px solid rgba(255,255,255,0.22);" +
    "}" +
    ".gift-form label{" +
      "display:block;font-family:'Nunito Sans',sans-serif;font-size:0.72rem;" +
      "letter-spacing:0.12em;text-transform:uppercase;font-weight:700;" +
      "opacity:0.6;margin:0 0 0.35rem 0;" +
    "}" +
    ".gift-form input,.gift-form textarea{" +
      "width:100%;font-family:'Nunito Sans',sans-serif;font-size:0.95rem;" +
      "color:inherit;background:rgba(255,255,255,0.28);border:1px solid rgba(128,128,128,0.4);" +
      "border-radius:9px;padding:0.55rem 0.7rem;margin:0 0 0.9rem 0;" +
    "}" +
    ".gift-form textarea{resize:vertical;min-height:4.5rem;line-height:1.6;}" +
    ".gift-form ::placeholder{color:inherit;opacity:0.55;}" +
    ".gift-form input:focus,.gift-form textarea:focus{outline:2px solid currentColor;outline-offset:1px;}" +
    ".gift-row{display:flex;gap:0.8rem;flex-wrap:wrap;align-items:center;}" +
    ".gift-count{font-family:'Nunito Sans',sans-serif;font-size:0.74rem;opacity:0.55;}" +
    ".gift-link{" +
      "margin-top:0.9rem;font-family:'Nunito Sans',sans-serif;font-size:0.78rem;" +
      "line-height:1.5;word-break:break-all;opacity:0.75;" +
    "}" +
    ".gift-status{" +
      "font-family:'Nunito Sans',sans-serif;font-size:0.78rem;opacity:0.75;" +
      "margin:0.7rem 0 0 0;min-height:1.1em;" +
    "}" +
    "@media (prefers-reduced-motion: reduce){.gift-btn{transition:none;}}";

  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  /* ---------- if this page was opened as a gift, show the note ---------- */

  function readGift() {
    var m = /(?:^#|[#&])g=([A-Za-z0-9\-_]+)/.exec(location.hash || "");
    if (!m) return null;
    try {
      var data = decode(m[1]);
      if (!data || typeof data !== "object") return null;
      return {
        to: clamp(data.t, MAX_NAME),
        from: clamp(data.f, MAX_NAME),
        note: clamp(data.n, MAX_NOTE)
      };
    } catch (e) {
      return null;
    }
  }

  function renderGift(gift) {
    var main = document.querySelector("main");
    if (!main) return;

    var box = document.createElement("aside");
    box.className = "gift-note";

    var head = document.createElement("p");
    head.className = "gift-for";
    head.textContent = gift.to ? "For " + gift.to : "Someone sent you this";
    box.appendChild(head);

    if (gift.note) {
      var msg = document.createElement("p");
      msg.className = "gift-msg";
      msg.textContent = "“" + gift.note + "”";
      box.appendChild(msg);
    }

    if (gift.from) {
      var sig = document.createElement("p");
      sig.className = "gift-from";
      sig.textContent = "— " + gift.from;
      box.appendChild(sig);
    }

    main.insertBefore(box, main.firstChild);

    // The footer line assumes you bought this yourself. A recipient didn't.
    var more = document.querySelector(".more p");
    if (more) {
      more.textContent = "";
      more.appendChild(document.createTextNode(
        "Someone paid to send you this. There are seven other feelings on the shelf, from $1. "
      ));
      var a = document.createElement("a");
      a.href = STORE_URL + "#shelf";
      a.textContent = "See the shelf →";
      more.appendChild(a);
    }
  }

  /* ---------- composer ---------- */

  function buildComposer(share) {
    var open = document.createElement("div");
    open.className = "gift-open";

    var trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "gift-btn";
    trigger.textContent = "Send this to someone";
    trigger.setAttribute("aria-expanded", "false");
    open.appendChild(trigger);

    var form = document.createElement("form");
    form.className = "gift-form";
    form.hidden = true;

    function field(labelText, tag, name, maxLength, placeholder) {
      var id = "gift-" + name;
      var label = document.createElement("label");
      label.setAttribute("for", id);
      label.textContent = labelText;
      var input = document.createElement(tag);
      input.id = id;
      input.maxLength = maxLength;
      if (placeholder) input.placeholder = placeholder;
      form.appendChild(label);
      form.appendChild(input);
      return input;
    }

    var toEl = field("Who is it for?", "input", "to", MAX_NAME, "Their name");
    var noteEl = field("Say something", "textarea", "note", MAX_NOTE, "Thought of you.");
    var fromEl = field("From", "input", "from", MAX_NAME, "Your name");

    var row = document.createElement("div");
    row.className = "gift-row";

    var make = document.createElement("button");
    make.type = "submit";
    make.className = "gift-btn";
    make.textContent = "Create the link";
    row.appendChild(make);

    var count = document.createElement("span");
    count.className = "gift-count";
    row.appendChild(count);
    form.appendChild(row);

    var status = document.createElement("p");
    status.className = "gift-status";
    status.setAttribute("aria-live", "polite");
    form.appendChild(status);

    var linkOut = document.createElement("p");
    linkOut.className = "gift-link";
    linkOut.hidden = true;
    form.appendChild(linkOut);

    open.appendChild(form);

    function updateCount() {
      var left = MAX_NOTE - noteEl.value.length;
      count.textContent = left < 60 ? left + " characters left" : "";
    }
    noteEl.addEventListener("input", updateCount);

    trigger.addEventListener("click", function () {
      form.hidden = !form.hidden;
      trigger.setAttribute("aria-expanded", form.hidden ? "false" : "true");
      if (!form.hidden) toEl.focus();
    });

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();

      var payload = {
        t: clamp(toEl.value, MAX_NAME),
        f: clamp(fromEl.value, MAX_NAME),
        n: clamp(noteEl.value, MAX_NOTE)
      };

      var url;
      try {
        url = location.origin + location.pathname + "#g=" + encode(payload);
      } catch (e) {
        status.textContent = "Could not build the link — try shorter text.";
        return;
      }

      var caption = payload.t
        ? payload.t + " — I sent you something to read."
        : "I sent you something to read.";

      linkOut.hidden = false;
      linkOut.textContent = url;

      if (navigator.share) {
        navigator.share({ title: "Moodshop — " + emotion, text: caption, url: url })
          .then(function () { status.textContent = "Sent."; })
          .catch(function () { status.textContent = "Link ready — copy it below."; });
        return;
      }

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () {
          status.textContent = "Link copied — paste it wherever you talk to them.";
        }).catch(function () {
          status.textContent = "Copy the link below and send it to them.";
        });
        return;
      }

      status.textContent = "Copy the link below and send it to them.";
    });

    share.appendChild(open);
  }

  /* ---------- go ---------- */

  var gift = readGift();
  if (gift && (gift.to || gift.from || gift.note)) renderGift(gift);

  var share = document.querySelector(".share");
  if (share) buildComposer(share);
})();
