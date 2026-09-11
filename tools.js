/*
  Moodshop tools — all the interaction for /tools/*.

  No AI, no API, no backend. Every result is composed client-side from
  curated content (content/tool-content.json) using the deterministic rules
  in recommend.js. Each block below looks for its own hook in the DOM and
  does nothing if it isn't there, so this one file serves all eight tools.

  Nothing typed into a tool is transmitted anywhere. The journal lives in
  localStorage, a sent feeling lives in a URL fragment, and analytics only
  ever sees an event name and a feeling slug — never the text.
*/
(function () {
  "use strict";

  var R = window.MoodshopRecommend;
  var C = window.MOODSHOP_TOOLCONTENT || {};
  var W = (window.MOODSHOP_FEELINGS && window.MOODSHOP_FEELINGS.wheel) || { categories: [] };
  if (!R) return;

  var REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var ORIGIN = location.origin.indexOf("moodshop") > -1 ? location.origin : "https://www.moodshop.lol";

  function track(n, p) { if (window.msTrack) window.msTrack(n, p); }
  /** @param {string} id @returns {any} The caller knows the element type; casting each use would be noise. */
  function byId(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  /** @param {any} f a feeling, or anything carrying a .theme.accent */
  function paint(f) {
    if (!f || !f.theme) return;
    document.documentElement.style.setProperty("--accent", f.theme.accent);
  }

  /* ===================================================================
     Shared: the mood result block (§5) — one renderer, four tools use it
     =================================================================== */

  /**
   * @param {HTMLElement} host
   * @param {Object} f            the feeling
   * @param {Object[]} seconds    related feelings to offer
   * @param {?string} explanation "Why this might fit", or null to omit
   * @param {string} source       analytics label for where this came from
   */
  function renderResult(host, f, seconds, explanation, source) {
    host.innerHTML = "";
    var prod = R.resolveProduct(f);

    var card = el("div", "result-card");
    card.style.background = f.theme.card;
    card.style.color = f.theme.cardInk;

    card.appendChild(el("p", "result-lede", "You might be feeling…"));
    var emoji = el("p", "result-emoji", f.emoji);
    emoji.setAttribute("aria-hidden", "true");
    card.appendChild(emoji);
    card.appendChild(el("h3", "result-name", f.name));
    card.appendChild(el("p", "result-desc", f.shortDescription));
    host.appendChild(card);

    if (explanation) {
      var why = el("div", "result-why");
      why.appendChild(el("h4", null, "Why this might fit"));
      why.appendChild(el("p", null, explanation));
      host.appendChild(why);
    }

    if (seconds && seconds.length) {
      var also = el("div", "result-also");
      also.appendChild(el("h4", null, "You may also want"));
      var row = el("ul", "chip-row");
      seconds.forEach(function (s) {
        if (!s) return;
        var li = el("li");
        var a = el("a", "chip-link", s.emoji + " " + s.name);
        a.href = "/mood/" + R.resolveProduct(s).mood + "/";
        a.setAttribute("data-track", "mood_recommendation_clicked");
        a.setAttribute("data-track-mood", s.slug);
        a.setAttribute("data-track-from", source);
        li.appendChild(a);
        row.appendChild(li);
      });
      also.appendChild(row);
      host.appendChild(also);
    }

    var actions = el("div", "cta-row");
    actions.style.marginTop = "1.6rem";

    if (prod) {
      var go = el("a", "btn btn-primary", "Explore " + f.name + " →");
      go.href = prod.href;
      go.setAttribute("data-track", "mood_recommendation_clicked");
      go.setAttribute("data-track-mood", f.slug);
      go.setAttribute("data-track-from", source);
      actions.appendChild(go);
    }
    host.appendChild(actions);

    if (prod && prod.note) {
      host.appendChild(el("p", "hint", prod.note));
    }

    paint(f);
    track("mood_selected", { mood: f.slug, from: source });
    host.hidden = false;
  }

  /* ===================================================================
     Tool 1 — Find My Mood (§4)
     =================================================================== */

  var quizHost = byId("quiz");
  if (quizHost) {
    var qs = R.quiz.questions;
    var answers = {};
    var step = 0;

    var stage = byId("quiz-stage");
    var progress = byId("quiz-progress");
    var resultHost = byId("quiz-result");
    var started = false;

    function renderStep() {
      var q = qs[step];
      stage.innerHTML = "";
      progress.textContent = "Question " + (step + 1) + " of " + qs.length;

      var fs = el("fieldset", "quiz-fieldset");
      var lg = el("legend", "quiz-legend", q.prompt);
      fs.appendChild(lg);

      var list = el("ul", "option-list");
      q.options.forEach(function (opt, i) {
        var li = el("li");
        var b = el("button", "option-btn", opt.label);
        b.type = "button";
        b.addEventListener("click", function () {
          if (!started) { started = true; track("mood_finder_started", {}); }
          answers[q.id] = i;
          if (step < qs.length - 1) { step++; renderStep(); }
          else finish();
        });
        li.appendChild(b);
        list.appendChild(li);
      });
      fs.appendChild(list);
      stage.appendChild(fs);

      var nav = el("div", "quiz-nav");
      if (step > 0) {
        var back = el("button", "link-btn", "← Previous question");
        back.type = "button";
        back.addEventListener("click", function () { step--; renderStep(); });
        nav.appendChild(back);
      }
      stage.appendChild(nav);

      var first = list.querySelector("button");
      if (first && started) first.focus();
    }

    function finish() {
      var rec = R.getMoodRecommendation(answers);
      if (!rec) return;
      quizHost.hidden = true;
      renderResult(resultHost, rec.primaryMood, rec.secondaryMoods, rec.explanation, "mood-finder");
      byId("quiz-again").hidden = false;
      track("mood_finder_completed", { mood: rec.primaryMood.slug });
      if (!REDUCED) resultHost.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    byId("quiz-again").addEventListener("click", function () {
      answers = {}; step = 0;
      resultHost.hidden = true;
      resultHost.innerHTML = "";
      byId("quiz-again").hidden = true;
      quizHost.hidden = false;
      renderStep();
      quizHost.scrollIntoView({ behavior: REDUCED ? "auto" : "smooth", block: "nearest" });
    });

    renderStep();
  }

  /* ===================================================================
     Tool 2 — Emotion Wheel (§6)
     =================================================================== */

  var wheelHost = byId("wheel");
  if (wheelHost) {
    var path = [];   // [categoryIndex, branchIndex, leafIndex]
    var crumb = byId("wheel-crumb");
    var wheelResult = byId("wheel-result");

    function crumbs() {
      crumb.innerHTML = "";
      if (!path.length) { crumb.hidden = true; return; }
      crumb.hidden = false;
      var parts = ["All feelings"];
      if (path.length >= 1) parts.push(W.categories[path[0]].name);
      if (path.length >= 2) parts.push(W.categories[path[0]].branches[path[1]].name);
      parts.forEach(function (p, i) {
        if (i) crumb.appendChild(el("span", "crumb-sep", "›"));
        if (i < parts.length - 1) {
          var b = el("button", "link-btn", p);
          b.type = "button";
          b.addEventListener("click", function () { path = path.slice(0, i); draw(); });
          crumb.appendChild(b);
        } else {
          crumb.appendChild(el("span", "crumb-here", p));
        }
      });
    }

    function options(items, label, onPick, accent) {
      wheelHost.innerHTML = "";
      var h = el("p", "wheel-prompt", label);
      wheelHost.appendChild(h);
      var list = el("ul", "option-list wheel-list");
      items.forEach(function (item, i) {
        var li = el("li");
        var b = /** @type {any} */ (el("button", "option-btn", (item.emoji ? item.emoji + " " : "") + (item.name || item.phrase)));
        b.type = "button";
        if (accent) b.style.borderColor = accent;
        b.addEventListener("click", function () { onPick(i); });
        li.appendChild(b);
        list.appendChild(li);
      });
      wheelHost.appendChild(list);
      var f = list.querySelector("button");
      if (f && path.length) f.focus();
    }

    function draw() {
      wheelResult.hidden = true;
      wheelResult.innerHTML = "";
      crumbs();

      if (path.length === 0) {
        options(W.categories, "Start broad. Which one is closest?", function (i) {
          path = [i]; track("emotion_wheel_used", { step: "category" }); draw();
        });
      } else if (path.length === 1) {
        var cat = W.categories[path[0]];
        paint({ theme: { accent: cat.accent } });
        options(cat.branches, "And which shape does it take?", function (i) {
          path = [path[0], i]; track("emotion_wheel_used", { step: "branch" }); draw();
        }, cat.accent);
      } else {
        var br = W.categories[path[0]].branches[path[1]];
        options(br.leaves, "Last one. Which of these is true tonight?", function (i) {
          land(br.leaves[i]);
        }, W.categories[path[0]].accent);
      }
    }

    function land(leaf) {
      var f = R.feeling(leaf.feeling);
      if (!f) return;
      wheelHost.innerHTML = "";
      var named = el("p", "wheel-named", "This feeling has a name.");
      wheelHost.appendChild(named);
      var said = el("p", "wheel-said", "“" + leaf.phrase + "”");
      wheelHost.appendChild(said);

      renderResult(wheelResult, f, (f.related || []).map(R.feeling), null, "emotion-wheel");
      track("emotion_wheel_used", { step: "result", mood: f.slug });

      var again = el("button", "btn btn-ghost btn-sm", "Start again");
      again.type = "button";
      again.addEventListener("click", function () { path = []; draw(); });
      wheelResult.appendChild(again);
      if (!REDUCED) wheelResult.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    draw();
  }

  /* ===================================================================
     Tool 3 — Message I Can't Send (§7)
     =================================================================== */

  var msgForm = byId("msg-form");
  if (msgForm && C.messages) {
    var M = C.messages;
    var variant = 0;
    var out = byId("msg-out");
    var textarea = byId("msg-text");
    var msgStatus = byId("msg-status");

    function fill(sel, items, labelKey) {
      items.forEach(function (it, i) {
        var o = el("option", null, it[labelKey || "label"]);
        o.value = it.id;
        sel.appendChild(o);
      });
    }
    fill(byId("msg-who"), M.recipients);
    fill(byId("msg-what"), M.intents);
    fill(byId("msg-tone"), M.tones);

    function find(list, id) {
      for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
      return list[0];
    }

    function compose() {
      var who = find(M.recipients, byId("msg-who").value);
      var what = byId("msg-what").value;
      var tone = byId("msg-tone").value;

      var opening = R.cycle(who.openings, variant);
      var body = (M.bodies[what] || {})[tone] || "";
      var closing = R.cycle(M.closings[tone] || [""], variant);

      return [opening, body, closing].filter(Boolean).join("\n\n");
    }

    function show() {
      textarea.value = compose();
      out.hidden = false;
      msgStatus.textContent = "";
      track("message_generator_used", {});   // never the text, only that it happened
    }

    msgForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      variant = 0;
      show();
      if (!REDUCED) out.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });

    byId("msg-another").addEventListener("click", function () { variant++; show(); });

    byId("msg-edit").addEventListener("click", function () {
      textarea.focus();
      textarea.setSelectionRange(textarea.value.length, textarea.value.length);
      msgStatus.textContent = "It’s yours — change anything you like.";
    });

    byId("msg-copy").addEventListener("click", function () {
      copy(textarea.value, msgStatus, "Copied. It’s yours to send, or not to.");
    });
  }

  /* ===================================================================
     Tool 4 — Mood Journal (§8) — localStorage only, never leaves the device
     =================================================================== */

  var journal = byId("journal-form");
  if (journal) {
    var KEY = "moodshop.journal.v1";
    var jText = byId("j-text");
    var jCount = byId("j-count");
    var jMood = byId("j-mood");
    var jList = byId("j-list");
    var jEmpty = byId("j-empty");
    var jFilters = byId("j-filters");
    var jSearch = byId("j-search");
    var jStatus = byId("j-status");
    var filter = "all";
    var MAX = 4000;

    R.feelings.forEach(function (f) {
      var o = el("option", null, f.emoji + "  " + f.name);
      o.value = f.slug;
      jMood.appendChild(o);
    });

    function load() {
      try {
        var raw = localStorage.getItem(KEY);
        var arr = raw ? JSON.parse(raw) : [];
        return Array.isArray(arr) ? arr : [];
      } catch (e) { return []; }   // private mode, quota, corrupted value
    }
    function save(arr) {
      try { localStorage.setItem(KEY, JSON.stringify(arr)); return true; }
      catch (e) { return false; }
    }

    function when(ts) {
      var d = new Date(ts);
      try {
        return d.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }) +
          " · " + d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
      } catch (e) { return d.toDateString(); }
    }

    function drawFilters(entries) {
      jFilters.innerHTML = "";
      var used = {};
      entries.forEach(function (e) { used[e.feeling] = (used[e.feeling] || 0) + 1; });
      var opts = [{ slug: "all", name: "All", emoji: "" }].concat(
        R.feelings.filter(function (f) { return used[f.slug]; })
      );
      if (opts.length === 1) { jFilters.hidden = true; return; }
      jFilters.hidden = false;
      opts.forEach(function (f) {
        var b = el("button", "filter-btn", (f.emoji ? f.emoji + " " : "") + f.name +
          (used[f.slug] ? " (" + used[f.slug] + ")" : ""));
        b.type = "button";
        b.setAttribute("aria-pressed", filter === f.slug ? "true" : "false");
        b.addEventListener("click", function () { filter = f.slug; draw(); });
        jFilters.appendChild(b);
      });
    }

    function draw() {
      var entries = load().sort(function (a, b) { return b.ts - a.ts; });
      drawFilters(entries);

      var q = (jSearch.value || "").trim().toLowerCase();
      var shown = entries.filter(function (e) {
        if (filter !== "all" && e.feeling !== filter) return false;
        if (q && e.text.toLowerCase().indexOf(q) === -1) return false;
        return true;
      });

      jList.innerHTML = "";
      jEmpty.hidden = shown.length > 0;
      if (!shown.length) {
        jEmpty.textContent = entries.length
          ? "Nothing matches that. Try another mood or clear the search."
          : "Nothing here yet. The first one is the hard one.";
        return;
      }

      shown.forEach(function (e) {
        // An entry can outlive the feeling it was tagged with (data edit,
        // older export): fall back to the raw slug rather than dropping it.
        var f = /** @type {any} */ (R.feeling(e.feeling) || { name: e.feeling, emoji: "", theme: {} });
        var item = el("li", "j-entry");

        var head = el("div", "j-head");
        head.appendChild(el("span", "j-date", when(e.ts)));
        var tag = el("span", "j-tag", (f.emoji ? f.emoji + " " : "") + f.name);
        if (f.theme && f.theme.accent) tag.style.borderColor = f.theme.accent;
        head.appendChild(tag);
        item.appendChild(head);

        var det = el("details", "j-body");
        var sum = el("summary");
        sum.appendChild(el("span", "j-preview", e.text.slice(0, 90) + (e.text.length > 90 ? "…" : "")));
        det.appendChild(sum);
        var full = el("p", "j-full");
        full.textContent = e.text;
        det.appendChild(full);
        item.appendChild(det);

        var del = el("button", "link-btn j-del", "Delete");
        del.type = "button";
        del.setAttribute("aria-label", "Delete the entry from " + when(e.ts));
        del.addEventListener("click", function () {
          if (!window.confirm("Delete this entry? It can't be undone.")) return;
          save(load().filter(function (x) { return x.id !== e.id; }));
          jStatus.textContent = "Entry deleted.";
          draw();
        });
        item.appendChild(del);

        jList.appendChild(item);
      });
    }

    jText.addEventListener("input", function () {
      jCount.textContent = jText.value.length + " / " + MAX;
    });
    jSearch.addEventListener("input", draw);

    journal.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var text = jText.value.trim();
      if (!text) { jStatus.textContent = "Write something first — anything."; jText.focus(); return; }
      var arr = load();
      arr.push({ id: String(Date.now()) + "-" + arr.length, ts: Date.now(), feeling: jMood.value, text: text.slice(0, MAX) });
      if (!save(arr)) {
        jStatus.textContent = "This browser won’t let the page store anything — private mode, usually. Copy the text somewhere before you close the tab.";
        return;
      }
      jText.value = "";
      jCount.textContent = "0 / " + MAX;
      jStatus.textContent = "Saved on this device.";
      track("journal_entry_created", { mood: jMood.value });   // slug only, never the writing
      draw();
    });

    // 2AM mode hands a prompt over in the URL; nothing is stored by the hop.
    var pre = new URLSearchParams(location.search);
    if (pre.get("mood") && R.feeling(pre.get("mood"))) jMood.value = pre.get("mood");
    if (pre.get("prompt")) {
      var p = byId("j-prompt");
      p.textContent = pre.get("prompt").slice(0, 120);
      p.hidden = false;
      jText.focus();
    }

    jCount.textContent = "0 / " + MAX;
    draw();
  }

  /* ===================================================================
     Tool 5 — Send a Feeling (§9, §10)
     =================================================================== */

  var sendTool = byId("sf-form");
  if (sendTool && C.sendFeelings) {
    var picked = C.sendFeelings[0];
    var sfStyle = "sweet";
    var sfCard = byId("sf-card");
    var sfOut = byId("sf-out");
    var sfStatus = byId("sf-status");
    var sfGrid = byId("sf-grid");

    C.sendFeelings.forEach(function (sf, i) {
      var f = R.feeling(sf.feeling);
      var b = el("button", "sf-choice");
      b.type = "button";
      b.setAttribute("aria-pressed", i === 0 ? "true" : "false");
      b.style.background = f.theme.card;
      b.style.color = f.theme.cardInk;
      b.appendChild(el("span", "sf-emoji", sf.emoji));
      b.appendChild(el("span", "sf-label", sf.label));
      b.addEventListener("click", function () {
        picked = sf;
        Array.prototype.forEach.call(sfGrid.querySelectorAll("button"), function (x, j) {
          x.setAttribute("aria-pressed", j === i ? "true" : "false");
        });
        paint(f);
        preview();
      });
      var li = el("li");
      li.appendChild(b);
      sfGrid.appendChild(li);
    });

    Array.prototype.forEach.call(sendTool.querySelectorAll("[name=sf-style]"), function (r) {
      r.addEventListener("change", function () { sfStyle = r.value; preview(); });
    });
    byId("sf-name").addEventListener("input", preview);

    function line() { return picked.lines[sfStyle] || picked.lines.sweet; }
    function forName() { return (byId("sf-name").value || "").replace(/\s+/g, " ").trim().slice(0, 40); }

    function preview() {
      var f = R.feeling(picked.feeling);
      sfCard.style.background = f.theme.card;
      sfCard.style.color = f.theme.cardInk;
      byId("sf-for").textContent = forName() ? "For " + forName() : "For you";
      byId("sf-line").textContent = line();
      sfOut.hidden = true;
    }

    sendTool.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var f = R.feeling(picked.feeling);
      var prod = R.resolveProduct(f);
      // The note travels in the fragment, which browsers never send to a
      // server — so a recipient's name never reaches Vercel or analytics.
      var payload = { m: prod.mood, t: forName(), f: "", n: line() };
      var url;
      try {
        url = ORIGIN + "/for/#" + b64(JSON.stringify(payload));
      } catch (e) {
        sfStatus.textContent = "Couldn’t build the link — try a shorter name.";
        return;
      }
      byId("sf-link").textContent = url;
      sfOut.hidden = false;
      track("send_feeling_started", { mood: f.slug });
      wireShare(url, line() + " — Moodshop", sfStatus, f.slug);
    });

    preview();
  }

  /* ===================================================================
     Tool 6 — Thought Generator (§11)
     =================================================================== */

  var tg = byId("tg-grid");
  if (tg && C.thoughts) {
    var tgFeel = null;
    var tgN = 0;
    var tgOut = byId("tg-out");
    var tgStatus = byId("tg-status");

    R.feelings.forEach(function (f, i) {
      var b = el("button", "chip-btn", f.emoji + " " + f.name);
      b.type = "button";
      b.setAttribute("aria-pressed", "false");
      b.addEventListener("click", function () {
        tgFeel = f;
        tgN = Math.floor(Math.random() * (C.thoughts[f.slug] || [""]).length);
        Array.prototype.forEach.call(tg.querySelectorAll("button"), function (x, j) {
          x.setAttribute("aria-pressed", j === i ? "true" : "false");
        });
        showThought();
      });
      var li = el("li");
      li.appendChild(b);
      tg.appendChild(li);
    });

    function showThought() {
      if (!tgFeel) return;
      var list = C.thoughts[tgFeel.slug] || [];
      var text = R.cycle(list, tgN);
      var box = byId("tg-card");
      box.style.background = tgFeel.theme.card;
      box.style.color = tgFeel.theme.cardInk;
      byId("tg-kicker").textContent = tgFeel.emoji + "  " + tgFeel.name;
      byId("tg-text").textContent = text;

      var prod = R.resolveProduct(tgFeel);
      var go = byId("tg-explore");
      go.href = prod.href;
      go.textContent = "Explore " + tgFeel.name + " →";
      go.setAttribute("data-track-mood", tgFeel.slug);

      var note = byId("tg-note");
      note.textContent = prod.note || "";
      note.hidden = !prod.note;

      tgOut.hidden = false;
      paint(tgFeel);
      tgStatus.textContent = "";
      track("thought_generated", { mood: tgFeel.slug });
    }

    byId("tg-another").addEventListener("click", function () { tgN++; showThought(); });
    byId("tg-copy").addEventListener("click", function () {
      copy(byId("tg-text").textContent + "\n\n— Moodshop.lol", tgStatus, "Copied.");
    });
    byId("tg-share").addEventListener("click", function () {
      var t = byId("tg-text").textContent;
      nativeShare("“" + t + "”", ORIGIN + "/mood/" + R.resolveProduct(tgFeel).mood + "/", tgStatus, tgFeel.slug, "thought-generator");
    });
  }

  /* ===================================================================
     Tool 7 — 2AM Mode (§12)
     =================================================================== */

  var am = byId("am-prompt");
  if (am && C.prompts2am) {
    var amN = Math.floor(Math.random() * C.prompts2am.length);
    track("2am_mode_started", {});

    var hour = byId("am-hour");
    if (hour) {
      var h = new Date().getHours();
      hour.textContent =
        h < 5 ? "It’s late. You’re still awake." :
        h < 12 ? "It’s morning, but the questions don’t only come at night." :
        h < 18 ? "It’s the middle of the day. These still work." :
        h < 22 ? "The evening, then." : "It’s late. You’re still awake.";
    }

    function showPrompt() {
      var p = R.cycle(C.prompts2am, amN);
      var f = R.feeling(p.feeling);
      am.textContent = p.text;

      var write = byId("am-write");
      write.href = "/tools/mood-journal/?mood=" + f.slug + "&prompt=" + encodeURIComponent(p.text);
      var read = byId("am-read");
      read.href = R.resolveProduct(f).href;
      read.textContent = "Read " + f.name + " →";
      read.setAttribute("data-track-mood", f.slug);
      var send = byId("am-send");
      send.href = "/tools/send-a-feeling/";
      paint(f);
    }

    byId("am-another").addEventListener("click", function () { amN++; showPrompt(); });
    showPrompt();
  }

  /* ===================================================================
     Today's mood page (§13) — same pick as the homepage section
     =================================================================== */

  var todayHost = byId("today-page");
  if (todayHost && window.MOODSHOP) {
    var pool = window.MOODSHOP.moods || [];
    var t = R.ofTheDay(pool);
    if (t) {
      var f2 = /** @type {any} */ (R.feeling(t.slug) || { emoji: "", theme: t.theme, name: t.name, slug: t.slug });
      var face = byId("today-page-face");
      face.style.background = "linear-gradient(150deg," + t.theme.colors[0] + " 0%," +
        t.theme.colors[1] + " 58%," + t.theme.colors[2] + " 100%)";
      face.style.color = t.theme.ink;
      byId("today-page-name").textContent = t.name;
      byId("today-page-tag").textContent = t.tagline;

      var thoughts = (C.thoughts && C.thoughts[t.slug]) || [];
      var thought = R.ofTheDay(thoughts);
      if (thought) byId("today-page-thought").textContent = "“" + thought + "”";

      var link = byId("today-page-link");
      link.href = "/mood/" + t.slug + "/";
      link.textContent = "Read today’s mood — " + t.name;
      link.setAttribute("data-track-mood", t.slug);
      document.title = "Today’s mood: " + t.name + " — Moodshop";
      paint(f2);
    }
  }

  /* ===================================================================
     shared clipboard + share helpers
     =================================================================== */

  function b64(str) {
    var bytes = new TextEncoder().encode(str);
    var bin = "";
    for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function copy(text, status, ok) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text)
        .then(function () { if (status) status.textContent = ok; })
        .catch(function () { if (status) status.textContent = "Couldn’t copy — select the text and copy it yourself."; });
    } else if (status) {
      status.textContent = "Select the text above and copy it.";
    }
  }

  function nativeShare(text, url, status, mood, from) {
    track("share_clicked", { mood: mood, from: from });
    if (navigator.share) {
      navigator.share({ title: "Moodshop", text: text, url: url })
        .then(function () { if (status) status.textContent = ""; track("share_completed", { mood: mood, from: from }); })
        .catch(function () { if (status) status.textContent = ""; });
      return;
    }
    copy(text + " " + url, status, "Copied — paste it wherever you like.");
  }

  /** Points the four share controls in a [data-sharebox] at a built link. */
  function wireShare(url, text, status, mood) {
    var box = /** @type {any} */ (document.querySelector("[data-sharebox]"));
    if (!box) return;
    box.hidden = false;
    var x = box.querySelector("[data-sb=x]");
    var wa = box.querySelector("[data-sb=whatsapp]");
    if (x) {
      x.href = "https://twitter.com/intent/tweet?text=" + encodeURIComponent(text) + "&url=" + encodeURIComponent(url);
      x.target = "_blank"; x.rel = "noopener";
      x.onclick = function () { track("share_clicked", { mood: mood, from: "x" }); track("share_completed", { mood: mood, from: "x" }); };
    }
    if (wa) {
      wa.href = "https://wa.me/?text=" + encodeURIComponent(text + "\n" + url);
      wa.target = "_blank"; wa.rel = "noopener";
      wa.onclick = function () { track("share_clicked", { mood: mood, from: "whatsapp" }); track("share_completed", { mood: mood, from: "whatsapp" }); };
    }
    var cp = box.querySelector("[data-sb=copy]");
    if (cp) cp.onclick = function () { track("share_clicked", { mood: mood, from: "copy" }); copy(url, status, "Link copied."); };
    var nv = box.querySelector("[data-sb=native]");
    if (nv) nv.onclick = function () { nativeShare(text, url, status, mood, "native"); };
    var cm = box.querySelector("[data-sb=copytext]");
    if (cm) cm.onclick = function () { track("share_clicked", { mood: mood, from: "message" }); copy(text, status, "Message copied."); };
  }
})();
