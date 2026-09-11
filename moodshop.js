/*
  Moodshop — shared behaviour for the public shop pages.

  Everything in here is optional: each block looks for its own hook in the
  DOM and does nothing if it isn't there, so one file serves the homepage,
  the mood pages, /send, /for and /collections without any per-page cost
  beyond the bytes.

  Reads window.MOODSHOP (see /moods-data.js, generated from
  content/moods.json by tools/build.py). No framework, no build step.
*/
(function () {
  "use strict";

  var DATA = window.MOODSHOP || { moods: [], finder: { options: [] } };
  var MOODS = DATA.moods || [];
  var ORIGIN = (DATA.site && DATA.site.origin) || "https://www.moodshop.lol";
  var REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function track(name, props) { if (window.msTrack) window.msTrack(name, props); }
  /** @param {string} id @returns {any} The caller knows the element type; casting each use would be noise. */
  function byId(id) { return document.getElementById(id); }
  function bySlug(slug) {
    for (var i = 0; i < MOODS.length; i++) if (MOODS[i].slug === slug) return MOODS[i];
    return null;
  }
  function money(n) { return "$" + n; }

  /* ================= url-safe base64 over utf-8 ================= */
  /* Same encoding gift.js uses on the reader pages, so a link made here
     and a link made there are the same shape. */

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
  function clamp(s, n) {
    s = String(s == null ? "" : s).replace(/\s+/g, " ").trim();
    return s.length > n ? s.slice(0, n) : s;
  }

  /* ================= scroll reveal ================= */

  var revealables = document.querySelectorAll(".reveal");
  if (revealables.length) {
    if (REDUCED || !("IntersectionObserver" in window)) {
      Array.prototype.forEach.call(revealables, function (el) { el.classList.add("in"); });
    } else {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) { entry.target.classList.add("in"); io.unobserve(entry.target); }
        });
      }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
      Array.prototype.forEach.call(revealables, function (el) { io.observe(el); });
      // Safety net: nothing may stay invisible because an observer never fired
      // (bfcache restore, zero-height layout, odd viewport).
      setTimeout(function () {
        Array.prototype.forEach.call(revealables, function (el) { el.classList.add("in"); });
      }, 2500);
    }
  }

  /* ================= accent theming ================= */
  /* The whole page borrows the colour of whatever feeling is in focus. */

  function paint(mood) {
    if (!mood || !mood.theme) return;
    var root = document.documentElement.style;
    root.setProperty("--accent", mood.theme.accent);
    root.setProperty("--accent-2", mood.theme.accent2);
  }
  var pagemood = document.body.getAttribute("data-mood");
  if (pagemood) paint(bySlug(pagemood));

  /* ================= named page views ================= */
  /* Both providers count their own pageviews; these are the named events the
     funnel is measured on, so they exist under the same names everywhere. */

  if (pagemood) track("mood_page_view", { mood: pagemood });
  else if (location.pathname === "/" || /\/index\.html$/.test(location.pathname)) track("homepage_view", {});

  /* ================= teaser_view ================= */

  var teaser = document.querySelector(".teaser-box");
  if (teaser) {
    var slug = teaser.getAttribute("data-mood") || pagemood || "";
    if ("IntersectionObserver" in window) {
      var tio = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) { track("teaser_view", { mood: slug }); tio.disconnect(); }
        });
      }, { threshold: 0.4 });
      tio.observe(teaser);
    } else {
      track("teaser_view", { mood: slug });
    }
  }

  /* ================= mood of the day ================= */
  /* Deterministic from the date, so everyone sees the same feeling today and
     a different one tomorrow. No storage, no server, no database. */

  function moodOfTheDay() {
    if (!MOODS.length) return null;
    var d = new Date();
    var day = Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 86400000);
    return MOODS[((day % MOODS.length) + MOODS.length) % MOODS.length];
  }

  var todayFace = byId("today-face");
  if (todayFace) {
    var t = moodOfTheDay();
    if (t) {
      todayFace.style.background = "linear-gradient(150deg," + t.theme.colors[0] + " 0%," +
        t.theme.colors[1] + " 58%," + t.theme.colors[2] + " 100%)";
      todayFace.style.color = t.theme.ink;
      byId("today-name").textContent = t.name;
      byId("today-quote").textContent = "“" + t.shareLine + "”";
      var tl = byId("today-link");
      tl.href = "/mood/" + t.slug + "/";
      tl.setAttribute("data-track-mood", t.slug);
      tl.textContent = "Read today’s mood — " + t.name;
      var tw = byId("today-what");
      if (tw) tw.textContent = t.tagline;
    }
  }

  /* ================= mood finder ================= */

  var finder = byId("finder-options");
  if (finder) {
    var result = byId("finder-result");
    var started = false;

    (DATA.finder.options || []).forEach(function (opt) {
      var li = document.createElement("li");
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = opt.label;
      b.addEventListener("click", function () {
        if (!started) { started = true; track("mood_finder_started", {}); }
        answer(opt);
      });
      li.appendChild(b);
      finder.appendChild(li);
    });

    function answer(opt) {
      var mood = bySlug(opt.mood);
      if (!mood || !result) return;

      byId("finder-verdict").textContent = "You might need " + mood.name + ".";
      byId("finder-why").textContent = opt.because;

      var cta = byId("finder-cta");
      cta.href = "/mood/" + mood.slug + "/";
      cta.textContent = "Enter " + mood.name + " →";
      cta.setAttribute("data-track-mood", mood.slug);

      result.hidden = false;
      paint(mood);
      track("mood_finder_completed", { mood: mood.slug });

      if (!REDUCED) result.scrollIntoView({ behavior: "smooth", block: "nearest" });
      cta.focus({ preventScroll: true });
    }

    var again = byId("finder-again");
    if (again) {
      again.addEventListener("click", function () {
        if (result) result.hidden = true;
        var first = finder.querySelector("button");
        if (first) first.focus();
      });
    }
  }

  /* ================= share ================= */

  function wrapText(ctx, text, maxWidth) {
    var words = text.split(" "), lines = [], line = "";
    for (var i = 0; i < words.length; i++) {
      var test = line ? line + " " + words[i] : words[i];
      if (ctx.measureText(test).width > maxWidth && line) { lines.push(line); line = words[i]; }
      else { line = test; }
    }
    if (line) lines.push(line);
    return lines;
  }

  // A 1080x1080 card: the one line, the feeling, the domain. Never the piece.
  function buildCard(mood) {
    var ready = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    return ready.then(function () {
      var size = 1080;
      var canvas = document.createElement("canvas");
      canvas.width = size; canvas.height = size;
      var ctx = canvas.getContext("2d");

      var grad = ctx.createLinearGradient(0, 0, size, size);
      grad.addColorStop(0, mood.theme.colors[0]);
      grad.addColorStop(0.55, mood.theme.colors[1]);
      grad.addColorStop(1, mood.theme.colors[2]);
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, size, size);

      ctx.fillStyle = mood.theme.ink;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.font = "600 64px 'Cormorant Garamond', Georgia, serif";
      var lines = wrapText(ctx, "“" + mood.shareLine + "”", size - 200);
      var lineHeight = 84;
      var startY = size / 2 - ((lines.length - 1) * lineHeight) / 2;
      lines.forEach(function (l, i) { ctx.fillText(l, size / 2, startY + i * lineHeight); });

      ctx.font = "700 28px 'Nunito Sans', sans-serif";
      ctx.globalAlpha = 0.85;
      ctx.fillText(mood.name.toUpperCase() + "  ·  MOODSHOP.LOL", size / 2, size - 92);
      ctx.globalAlpha = 1;

      return new Promise(function (resolve) { canvas.toBlob(resolve, "image/png"); });
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll("[data-share]"), function (box) {
    var mood = bySlug(box.getAttribute("data-share"));
    if (!mood) return;

    var url = ORIGIN + "/mood/" + mood.slug + "/";
    var caption = "“" + mood.shareLine + "”";
    var status = box.querySelector(".share-status");
    function say(msg) { if (status) status.textContent = msg; }

    box.querySelectorAll("[data-share-to]").forEach(function (el) {
      var to = el.getAttribute("data-share-to");

      if (to === "x") {
        el.href = "https://twitter.com/intent/tweet?text=" +
          encodeURIComponent(caption + " — Moodshop") + "&url=" + encodeURIComponent(url);
        el.target = "_blank"; el.rel = "noopener";
      }
      if (to === "whatsapp") {
        el.href = "https://wa.me/?text=" + encodeURIComponent(caption + "\n" + url);
        el.target = "_blank"; el.rel = "noopener";
      }
      if (to === "x" || to === "whatsapp") {
        el.addEventListener("click", function () {
          track("share_clicked", { mood: mood.slug, from: to });
          track("share_completed", { mood: mood.slug, from: to });
        });
        return;
      }

      el.addEventListener("click", function (ev) {
        ev.preventDefault();
        track("share_clicked", { mood: mood.slug, from: to });

        if (to === "copy") {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(url).then(function () {
              say("Link copied — paste it wherever you like.");
              track("share_completed", { mood: mood.slug, from: "copy" });
            }).catch(function () { say(url); });
          } else { say(url); }
          return;
        }

        if (to === "native") {
          if (navigator.share) {
            navigator.share({ title: "Moodshop — " + mood.name, text: caption, url: url })
              .then(function () { say(""); track("share_completed", { mood: mood.slug, from: "native" }); })
              .catch(function () { say(""); });
          } else if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(caption + " " + url).then(function () {
              say("Copied — your device can’t share directly, so paste it instead.");
              track("share_completed", { mood: mood.slug, from: "native-fallback" });
            }).catch(function () { say(url); });
          } else { say(url); }
          return;
        }

        if (to === "image") {
          say("Making the card…");
          buildCard(mood).then(function (blob) {
            var file = new File([blob], "moodshop-" + mood.slug + ".png", { type: "image/png" });
            if (navigator.canShare && navigator.canShare({ files: [file] })) {
              navigator.share({ files: [file], title: "Moodshop — " + mood.name, text: caption + " " + url })
                .then(function () { say(""); track("share_completed", { mood: mood.slug, from: "image" }); })
                .catch(function () { say(""); });
              return;
            }
            var href = URL.createObjectURL(blob);
            var a = document.createElement("a");
            a.href = href; a.download = "moodshop-" + mood.slug + ".png";
            document.body.appendChild(a); a.click(); document.body.removeChild(a);
            setTimeout(function () { URL.revokeObjectURL(href); }, 4000);
            say("Saved — it’s square, ready for a story.");
            track("share_completed", { mood: mood.slug, from: "image" });
          }).catch(function () { say("Couldn’t make the card — try the link instead."); });
        }
      });
    });
  });

  /* ================= send a feeling ================= */

  var sendForm = byId("send-form");
  if (sendForm) {
    var MAX_NAME = 40, MAX_NOTE = 240;
    var picker = byId("send-mood");
    var out = byId("send-out");
    var linkEl = byId("send-link");
    var sendStatus = byId("send-status");

    MOODS.forEach(function (m) {
      var o = document.createElement("option");
      o.value = m.slug;
      o.textContent = m.name + " — " + m.tagline;
      picker.appendChild(o);
    });

    var pre = new URLSearchParams(location.search).get("mood");
    if (pre && bySlug(pre)) picker.value = pre;
    paint(bySlug(picker.value));
    picker.addEventListener("change", function () { paint(bySlug(picker.value)); });

    sendForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var mood = bySlug(picker.value);
      if (!mood) return;

      var payload = {
        m: mood.slug,
        t: clamp(byId("send-to").value, MAX_NAME),
        f: clamp(byId("send-from").value, MAX_NAME),
        n: clamp(byId("send-note").value, MAX_NOTE)
      };

      var url;
      try { url = ORIGIN + "/for/#" + encode(payload); }
      catch (e) { sendStatus.textContent = "Couldn’t build the link — try shorter text."; return; }

      out.hidden = false;
      linkEl.textContent = url;
      track("send_feeling_clicked", { mood: mood.slug });

      if (navigator.share) {
        navigator.share({ title: "Moodshop", text: payload.t ? payload.t + " — I sent you something." : "I sent you something.", url: url })
          .then(function () { sendStatus.textContent = "Sent."; })
          .catch(function () { sendStatus.textContent = "Link ready — copy it below."; });
        return;
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () {
          sendStatus.textContent = "Link copied — paste it wherever you talk to them.";
        }).catch(function () { sendStatus.textContent = "Copy the link below and send it to them."; });
        return;
      }
      sendStatus.textContent = "Copy the link below and send it to them.";
    });
  }

  /* ================= the receiving end ================= */

  var forPage = byId("for-page");
  if (forPage) {
    var gift = null;
    try {
      var raw = (location.hash || "").replace(/^#/, "");
      if (raw) gift = decode(raw);
    } catch (e) { gift = null; }

    var mood = gift && bySlug(gift.m);
    if (!mood) {
      // A link with nothing in it, or a mangled one. Say so plainly rather
      // than showing an empty page.
      byId("for-empty").hidden = false;
    } else {
      var card = byId("for-card");
      card.hidden = false;
      card.style.background = "linear-gradient(150deg," + mood.theme.colors[0] + " 0%," +
        mood.theme.colors[1] + " 58%," + mood.theme.colors[2] + " 100%)";
      card.style.color = mood.theme.ink;

      var to = clamp(gift.t, 40), from = clamp(gift.f, 40), note = clamp(gift.n, 240);
      byId("for-to").textContent = to ? "For " + to + "." : "For you.";
      var noteEl = byId("for-note");
      if (note) { noteEl.textContent = "“" + note + "”"; }
      else { noteEl.textContent = "I didn’t always know how to say it. So I sent you this instead."; }
      var fromEl = byId("for-from");
      if (from) { fromEl.textContent = "— " + from; fromEl.hidden = false; }

      var open = byId("for-open");
      open.href = "/mood/" + mood.slug + "/";
      open.textContent = "Open the feeling →";
      open.setAttribute("data-track-mood", mood.slug);
      document.title = (to ? "For " + to : "For you") + " — Moodshop";
    }
  }

  /* ================= the honest unlock counter ================= */

  var counter = byId("unlock-count");
  if (counter) {
    fetch("/api/counter?action=total")
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (data) {
        if (!data.ok) return;
        var total = data.total;
        counter.innerHTML = '<span class="pulse"></span>' + (total > 0
          ? total.toLocaleString() + (total === 1 ? " feeling opened so far" : " feelings opened so far")
          : "No one has opened a feeling yet — be the first.");
        counter.classList.add("visible");
      })
      .catch(function () {});
  }

  /* ================= headline rotator ================= */

  var rotator = byId("rotator");
  if (rotator && !REDUCED) {
    var words = ["feel?", "feel today?", "feel tonight?", "feel right now?"];
    var idx = 0;
    setInterval(function () {
      rotator.classList.add("swap");
      setTimeout(function () {
        idx = (idx + 1) % words.length;
        rotator.textContent = words[idx];
        rotator.classList.remove("swap");
      }, 360);
    }, 3400);
  }
})();
