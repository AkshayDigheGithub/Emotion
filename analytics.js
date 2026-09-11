/*
  Moodshop analytics — a thin shim over the two providers already on the site.

  Vercel Web Analytics  -> window.va('event', {name, data})
  Datafast              -> window.datafast(goal, props)

  Both are loaded `defer` and either may be blocked by a content blocker, so
  every call is wrapped: a missing provider is a no-op, never an exception.
  Nothing personal is collected — event names and a mood slug, that's it.

  Usage:
    msTrack('mood_selected', {mood: 'grief'});

  Or declaratively, on any element:
    <a data-track="bundle_clicked" data-track-mood="pack">…</a>
*/
(function () {
  "use strict";

  // Queue anything fired before the providers' deferred scripts have run.
  var queue = [];
  var flushed = false;

  function send(name, props) {
    var ok = false;
    try {
      if (typeof window.va === "function") {
        window.va("event", { name: name, data: props || {} });
        ok = true;
      }
    } catch (e) { /* provider blocked */ }
    try {
      if (typeof window.datafast === "function") {
        window.datafast(name, props || {});
        ok = true;
      }
    } catch (e) { /* provider blocked */ }
    return ok;
  }

  function flush() {
    if (flushed) return;
    var pending = queue.slice();
    queue.length = 0;
    for (var i = 0; i < pending.length; i++) send(pending[i][0], pending[i][1]);
    flushed = true;
  }

  function track(name, props) {
    if (!name) return;
    if (!send(name, props)) queue.push([name, props]);
  }

  window.msTrack = track;

  // Providers are `defer`, so they are ready by DOMContentLoaded at the latest.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", flush);
  } else {
    flush();
  }
  window.addEventListener("load", flush);

  /* ---------- declarative tracking ---------- */
  document.addEventListener("click", function (ev) {
    var el = ev.target && ev.target.closest && ev.target.closest("[data-track]");
    if (!el) return;
    var props = {};
    if (el.getAttribute("data-track-mood")) props.mood = el.getAttribute("data-track-mood");
    if (el.getAttribute("data-track-from")) props.from = el.getAttribute("data-track-from");
    track(el.getAttribute("data-track"), props);
  }, true);

  /* ---------- every outbound checkout, however it was reached ---------- */
  document.addEventListener("click", function (ev) {
    var a = ev.target && ev.target.closest && ev.target.closest("a[href]");
    if (!a) return;
    var href = a.getAttribute("href") || "";
    if (href.indexOf("buymeacoffee.com") === -1) return;
    if (a.getAttribute("data-track") === "checkout_started") return; // already counted
    track("checkout_started", { mood: a.getAttribute("data-track-mood") || "tip" });
  }, true);
})();
