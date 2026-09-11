#!/usr/bin/env python3
"""The free tools: /tools and its seven pages, plus /today.

Imported by build.py, which hands over the page shell it already owns
(`ctx`) so there is exactly one nav, one footer and one <head> builder for
the whole site. Nothing here talks to a model or a server: every page is
static HTML, and the interaction on top of it is tools.js composing curated
blocks from content/tool-content.json in the browser.
"""

import html
import json


def e(s):
    return html.escape(str(s), quote=True)


# --------------------------------------------------------------------------
# the seven tools, in the order they appear on the hub
# --------------------------------------------------------------------------

TOOLS = [
    {
        "slug": "mood-finder", "icon": "🧭", "name": "Find My Mood",
        "hub": "Answer a few questions and discover a feeling that might fit.",
        "h1": "How are you feeling?",
        "sub": "You don’t have to know exactly. We’ll help you narrow it down.",
        "seo_title": "Mood Finder — Discover What You’re Feeling",
        "seo_desc": "Not sure what you’re feeling? Answer three questions and find a short Moodshop experience that fits. No account, no AI, nothing stored.",
        "related": ["sorrow", "nostalgia", "hope"],
    },
    {
        "slug": "emotion-wheel", "icon": "🎡", "name": "Emotion Wheel",
        "hub": "Explore the many ways we can feel.",
        "h1": "Start broad. Get specific.",
        "sub": "Nine ways of feeling, and a hundred smaller ones underneath them.",
        "seo_title": "Emotion Wheel — Find the Word for What You’re Feeling",
        "seo_desc": "Work from a broad feeling down to the precise one. An interactive emotion wheel with 108 specific feelings, and a full list for keyboard and screen-reader use.",
        "related": ["grief", "hurt", "calm"],
    },
    {
        "slug": "message-i-cant-send", "icon": "✍️", "name": "Message I Can’t Send",
        "hub": "Find the words for something you’ve never said.",
        "h1": "What do you wish you could say?",
        "sub": "Sometimes the hardest words are the ones we never send.",
        "seo_title": "Message I Can’t Send — Find the Words",
        "seo_desc": "Pick who it’s for, what you want to say and the tone, and get a written message you can keep, edit or send. Hand-written templates, no AI.",
        "related": ["hurt", "grief", "nostalgia"],
    },
    {
        "slug": "mood-journal", "icon": "📓", "name": "Mood Journal",
        "hub": "Put what’s in your head onto a page.",
        "h1": "Get it out of your head.",
        "sub": "You don’t have to make it make sense.",
        "seo_title": "Mood Journal — Private, On This Device Only",
        "seo_desc": "A simple mood journal that saves to your own browser and nowhere else. No account, no server, no one reading it. Tag entries by feeling and search them back.",
        "related": ["sorrow", "calm", "rage"],
    },
    {
        "slug": "send-a-feeling", "icon": "💌", "name": "Send a Feeling",
        "hub": "Turn a feeling into something you can share.",
        "h1": "Some feelings are easier to send than say.",
        "sub": "Pick one, and we’ll find the words. Your message travels inside the link — never through a server.",
        "seo_title": "Send a Feeling — Say It Without Having to Write It",
        "seo_desc": "Pick a feeling, add a name, and send someone a small card that says the thing you couldn’t. No account, nothing stored, nothing sent to a server.",
        "related": ["nostalgia", "hurt", "hope"],
    },
    {
        "slug": "thought-generator", "icon": "💭", "name": "Thought Generator",
        "hub": "Pick a feeling. Get a thought worth keeping.",
        "h1": "Give us a feeling.",
        "sub": "Eighty-four original lines, written for one feeling each. Not quotes from anyone else.",
        "seo_title": "Thought Generator — One Line for What You’re Feeling",
        "seo_desc": "Choose a feeling and get an original short thought written for it. Copy it, share it, or go deeper into that feeling.",
        "related": ["nostalgia", "hope", "grief"],
    },
    {
        "slug": "2am", "icon": "🌙", "name": "2AM Mode",
        "hub": "For thoughts that only show up late at night.",
        "h1": "Still awake?",
        "sub": "Maybe there’s something you need to feel.",
        "seo_title": "2AM Mode — For Thoughts That Only Come at Night",
        "seo_desc": "One question at a time, for the hour when everyone else is asleep. Write it down, read something, or send it to someone.",
        "related": ["sorrow", "calm", "grief"],
        "dark": True,
    },
]


# --------------------------------------------------------------------------
# shared page furniture
# --------------------------------------------------------------------------

def tool_head(t):
    return """<header class="wrap narrow tool-head">
  <a class="back-link" href="/tools/">← All tools</a>
  <span class="ico" aria-hidden="true">{icon}</span>
  <h1>{h1}</h1>
  <p class="lede">{sub}</p>
</header>""".format(icon=t["icon"], h1=e(t["h1"]), sub=e(t["sub"]))


def tool_foot(ctx, t):
    """Related paid experiences, the pack, then the other tools (§22)."""
    cards = "\n".join(
        ctx["mood_card"](ctx["mood"](s), track_from="tool-" + t["slug"]) for s in t["related"]
    )
    others = "\n".join(
        '      <li><a class="chip-link" href="/tools/{s}/">{i} {n}</a></li>'.format(
            s=o["slug"], i=o["icon"], n=e(o["name"]))
        for o in TOOLS if o["slug"] != t["slug"]
    )
    return """
<section class="wrap" aria-labelledby="rel-{slug}">
  <p class="eyebrow">Go deeper</p>
  <h2 id="rel-{slug}">Related Moodshop experiences</h2>
  <p class="lede">The tools are free. These are the short pieces they point at — two minutes each, from ${minp}.</p>
  <ul class="mood-grid">
{cards}
  </ul>
</section>

<section class="wrap">
{bundle}
</section>

<section class="wrap tool-foot" aria-labelledby="other-{slug}">
  <p class="eyebrow">Keep going</p>
  <h2 id="other-{slug}">Explore another tool</h2>
  <ul class="tool-links" style="margin-top:1.2rem;">
{others}
  </ul>
</section>
""".format(slug=t["slug"], cards=cards, bundle=ctx["bundle_block"]("tool-" + t["slug"]),
           others=others, minp=ctx["min_price"])


# --------------------------------------------------------------------------
# the tool bodies
# --------------------------------------------------------------------------

def body_mood_finder(ctx, t):
    return """<main id="main">
{head}
<section class="wrap narrow" style="padding-top:0;">
  <div class="tool-stage">
    <p class="hint" style="margin:0 0 1.4rem 0;">{intro}</p>
    <div id="quiz">
      <p class="quiz-progress" id="quiz-progress"></p>
      <div id="quiz-stage"></div>
    </div>
    <div id="quiz-result" hidden></div>
    <button class="btn btn-ghost btn-sm" type="button" id="quiz-again" hidden style="margin-top:1.4rem;">Try again</button>
    <noscript>
      <p class="lede" style="margin:0;">The quiz needs JavaScript to add up your answers — it does the scoring in your browser so nothing has to be sent anywhere. With JS off, <a href="/moods/" style="color:var(--ink);">the eight feelings are all here</a> to read through instead.</p>
    </noscript>
  </div>
  <p class="hint">This is a weighted score over your three answers, not a diagnosis. It says <em>might</em> on purpose.</p>
</section>
{foot}
</main>""".format(head=tool_head(t), intro=e(ctx["feelings"]["quiz"]["intro"]), foot=tool_foot(ctx, t))


def body_emotion_wheel(ctx, t):
    """The interactive wheel, plus the full nested list underneath it — the
    list is the accessible route (§6) and also the version that works with
    JavaScript off."""
    groups = []
    for cat in ctx["wheel"]["categories"]:
        items = []
        for br in cat["branches"]:
            leaves = "\n".join(
                '        <li><a href="/mood/{m}/">{p} → {n}</a></li>'.format(
                    m=ctx["product_of"](lf["feeling"]), p=e(lf["phrase"]),
                    n=e(ctx["feeling_name"](lf["feeling"])))
                for lf in br["leaves"])
            items.append('      <h3>{c} · {b}</h3>\n      <ul>\n{l}\n      </ul>'.format(
                c=e(cat["name"]), b=e(br["name"]), l=leaves))
        groups.append("\n".join(items))
    full = "\n".join(groups)

    return """<main id="main">
{head}
<section class="wrap" style="padding-top:0;">
  <div class="tool-stage">
    <nav class="wheel-crumb" id="wheel-crumb" aria-label="Where you are in the wheel" hidden></nav>
    <div id="wheel" aria-live="polite"></div>
    <div id="wheel-result" hidden></div>
  </div>
</section>

<section class="wrap narrow">
  <details class="wheel-all">
    <summary>Every feeling, as a list</summary>
    <p class="hint">The same 108 feelings as the wheel above, laid out flat. Faster with a keyboard or a screen reader, and it works with JavaScript off.</p>
{full}
  </details>
</section>
{foot}
</main>""".format(head=tool_head(t), full=full, foot=tool_foot(ctx, t))


def body_message(ctx, t):
    return """<main id="main">
{head}
<section class="wrap narrow" style="padding-top:0;">
  <form class="tool-stage" id="msg-form" novalidate>
    <label class="field" for="msg-who"><span>Who is this for?</span>
      <select id="msg-who" name="who"></select></label>
    <label class="field" for="msg-what"><span>What do you want to say?</span>
      <select id="msg-what" name="what"></select></label>
    <label class="field" for="msg-tone"><span>Tone</span>
      <select id="msg-tone" name="tone"></select></label>
    <div class="cta-row">
      <button class="btn btn-primary" type="submit">Find the words</button>
    </div>

    <div class="msg-out" id="msg-out" hidden style="margin-top:1.8rem;">
      <label class="field" for="msg-text"><span>Your message — edit anything</span>
        <textarea id="msg-text" rows="10"></textarea></label>
      <div class="cta-row">
        <button class="btn btn-ghost btn-sm" type="button" id="msg-copy">Copy</button>
        <button class="btn btn-ghost btn-sm" type="button" id="msg-edit">Edit</button>
        <button class="btn btn-ghost btn-sm" type="button" id="msg-another">Try another</button>
        <a class="btn btn-ghost btn-sm" href="/tools/send-a-feeling/" data-track="send_feeling_started" data-track-from="message-tool">Send this feeling</a>
      </div>
      <p class="share-status" id="msg-status" aria-live="polite"></p>
    </div>

    <p class="hint">Every sentence here was written by hand and picked by your three choices — nothing is generated by a model, and nothing you choose leaves this page. Whether you send it is entirely up to you.</p>
    <noscript><p class="lede" style="margin:1rem 0 0 0;">This one needs JavaScript — it assembles the message in your browser rather than on a server.</p></noscript>
  </form>
</section>
{foot}
</main>""".format(head=tool_head(t), foot=tool_foot(ctx, t))


def body_journal(ctx, t):
    return """<main id="main">
{head}
<section class="wrap narrow" style="padding-top:0;">
  <p class="privacy-note"><span aria-hidden="true">🔒</span> <span>Your journal stays on this device. It’s saved in this browser’s own storage — there is no account and no server holding it, which also means clearing your browser data clears it.</span></p>

  <form class="tool-stage" id="journal-form" novalidate>
    <p class="j-prompt" id="j-prompt" hidden></p>
    <label class="field" for="j-mood"><span>How does today feel?</span>
      <select id="j-mood" name="mood"></select></label>
    <label class="field" for="j-text"><span>Write it down</span>
      <textarea id="j-text" name="text" rows="8" placeholder="It doesn’t have to be tidy."></textarea></label>
    <p class="hint" id="j-count" aria-live="off">0 / 4000</p>
    <div class="cta-row">
      <button class="btn btn-primary" type="submit">Save entry</button>
    </div>
    <p class="share-status" id="j-status" aria-live="polite"></p>
  </form>
</section>

<section class="wrap narrow">
  <h2>Your entries</h2>
  <label class="field" for="j-search"><span>Search what you’ve written</span>
    <input id="j-search" type="search" placeholder="A word you remember using"></label>
  <div class="j-filters" id="j-filters" role="group" aria-label="Filter entries by feeling" hidden></div>
  <p class="lede" id="j-empty"></p>
  <ul class="j-list" id="j-list"></ul>
  <noscript><p class="lede">The journal needs JavaScript — it writes to your browser’s own storage, which is the reason nothing has to be sent anywhere.</p></noscript>
</section>
{foot}
</main>""".format(head=tool_head(t), foot=tool_foot(ctx, t))


def body_send(ctx, t):
    return """<main id="main">
{head}
<section class="wrap narrow" style="padding-top:0;">
  <form class="tool-stage" id="sf-form" novalidate>
    <p class="field"><span style="display:block;font-size:0.7rem;letter-spacing:0.14em;text-transform:uppercase;font-weight:700;color:var(--sub);margin:0 0 0.5rem 0;">Which feeling?</span></p>
    <ul class="sf-grid" id="sf-grid"></ul>

    <label class="field" for="sf-name"><span>For someone?</span>
      <input id="sf-name" type="text" maxlength="40" autocomplete="off" placeholder="Their name — optional"></label>

    <fieldset class="radio-row" style="margin-bottom:1.6rem;">
      <legend>Message style</legend>
      <label><input type="radio" name="sf-style" value="short"><span>Short</span></label>
      <label><input type="radio" name="sf-style" value="sweet" checked><span>Sweet</span></label>
      <label><input type="radio" name="sf-style" value="emotional"><span>Emotional</span></label>
      <label><input type="radio" name="sf-style" value="deep"><span>Deep</span></label>
    </fieldset>

    <div class="send-card" id="sf-card">
      <p class="for" id="sf-for">For you</p>
      <p class="line" id="sf-line"></p>
      <p class="sig">— MOODSHOP.LOL</p>
    </div>

    <div class="cta-row" style="margin-top:1.6rem;">
      <button class="btn btn-primary" type="submit">Make the link</button>
    </div>

    <div id="sf-out" hidden style="margin-top:1.4rem;">
      <div data-sharebox hidden>
        <ul class="share-row">
          <li><button type="button" data-sb="copytext">Copy message</button></li>
          <li><button type="button" data-sb="native">Share</button></li>
          <li><a data-sb="whatsapp" href="#">WhatsApp</a></li>
          <li><a data-sb="x" href="#">X</a></li>
          <li><button type="button" data-sb="copy">Copy link</button></li>
        </ul>
      </div>
      <div class="out">
        <p style="margin:0 0 0.5rem 0;color:var(--ink);font-weight:700;">Their link</p>
        <p id="sf-link" style="margin:0;"></p>
      </div>
    </div>
    <p class="share-status" id="sf-status" aria-live="polite"></p>

    <p class="hint">The name and the line are encoded into the link itself. Browsers never send the part after the <code>#</code> to a server, so nothing you type here reaches Moodshop, Vercel or any analytics — it only exists in your browser and theirs.</p>
    <noscript><p class="lede" style="margin:1rem 0 0 0;">This needs JavaScript to build the link in your browser. <a href="/send/" style="color:var(--ink);">The write-your-own version is here.</a></p></noscript>
  </form>

  <p class="hint" style="margin-top:1.4rem;">Want to use your own words instead? <a href="/send/" style="color:var(--sub);">Write the note yourself →</a></p>
</section>
{foot}
</main>""".format(head=tool_head(t), foot=tool_foot(ctx, t))


def body_thought(ctx, t):
    return """<main id="main">
{head}
<section class="wrap narrow" style="padding-top:0;">
  <div class="tool-stage">
    <ul class="chip-row" id="tg-grid" style="margin-bottom:1.6rem;"></ul>

    <div id="tg-out" hidden>
      <div class="tg-card" id="tg-card">
        <p class="tg-kicker" id="tg-kicker"></p>
        <p class="tg-text" id="tg-text"></p>
      </div>
      <div class="cta-row" style="margin-top:1.4rem;">
        <button class="btn btn-ghost btn-sm" type="button" id="tg-another">Another thought</button>
        <button class="btn btn-ghost btn-sm" type="button" id="tg-copy">Copy</button>
        <button class="btn btn-ghost btn-sm" type="button" id="tg-share">Share</button>
        <a class="btn btn-primary btn-sm" id="tg-explore" href="/moods/" data-track="mood_recommendation_clicked" data-track-from="thought-generator">Explore this feeling →</a>
      </div>
      <p class="hint" id="tg-note" hidden></p>
      <p class="share-status" id="tg-status" aria-live="polite"></p>
    </div>

    <p class="hint" id="tg-hint">Pick a feeling above. Every line is original Moodshop writing — no quotes borrowed from anyone else, and nothing generated by a model.</p>
    <noscript><p class="lede" style="margin:1rem 0 0 0;">This one shuffles its lines in your browser, so it needs JavaScript. <a href="/free/" style="color:var(--ink);">Three full pieces are free to read without it.</a></p></noscript>
  </div>
</section>
{foot}
</main>""".format(head=tool_head(t), foot=tool_foot(ctx, t))


def body_2am(ctx, t):
    return """<main id="main">
<section class="wrap narrow am-stage">
  <a class="back-link" href="/tools/">← All tools</a>
  <p class="am-hour" id="am-hour"></p>
  <h1>Still awake?</h1>
  <p class="lede">Maybe there’s something you need to feel.</p>
  <p class="am-prompt" id="am-prompt">Who do you miss tonight?</p>
  <div class="cta-row">
    <a class="btn btn-primary" id="am-write" href="/tools/mood-journal/">Write</a>
    <a class="btn btn-ghost" id="am-read" href="/moods/" data-track="mood_recommendation_clicked" data-track-from="2am">Read</a>
    <a class="btn btn-ghost" id="am-send" href="/tools/send-a-feeling/" data-track="send_feeling_started" data-track-from="2am">Send</a>
  </div>
  <div class="cta-row" style="margin-top:1rem;">
    <button class="link-btn" type="button" id="am-another">Another question</button>
  </div>
  <noscript><p class="lede" style="margin-top:2rem;">The questions rotate in your browser. With JavaScript off, that one above is yours for tonight.</p></noscript>
</section>
{foot}
</main>""".format(foot=tool_foot(ctx, t))


BODIES = {
    "mood-finder": body_mood_finder,
    "emotion-wheel": body_emotion_wheel,
    "message-i-cant-send": body_message,
    "mood-journal": body_journal,
    "send-a-feeling": body_send,
    "thought-generator": body_thought,
    "2am": body_2am,
}


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def build(ctx):
    origin = ctx["origin"]
    page, write = ctx["page"], ctx["write"]

    # ---- client data ----
    payload = {
        "feelings": ctx["feelings"]["feelings"],
        "quiz": ctx["feelings"]["quiz"],
        "wheel": ctx["wheel"],
    }
    write("feelings-data.js",
          "/* Generated by scripts/build.py from content/feelings.json + content/wheel.json. Do not edit. */\n"
          "window.MOODSHOP_FEELINGS=%s;\n" % json.dumps(payload, separators=(",", ":"), ensure_ascii=False))

    content = {k: v for k, v in ctx["tool_content"].items() if not k.startswith("_")}
    if "messages" in content:
        content["messages"] = {k: v for k, v in content["messages"].items() if not k.startswith("_")}
    write("tool-content.js",
          "/* Generated by scripts/build.py from content/tool-content.json. Do not edit. */\n"
          "window.MOODSHOP_TOOLCONTENT=%s;\n" % json.dumps(content, separators=(",", ":"), ensure_ascii=False))

    scripts = ('<script defer src="/feelings-data.js"></script>\n'
               '<script defer src="/tool-content.js"></script>\n'
               '<script defer src="/recommend.js"></script>\n'
               '<script defer src="/tools.js"></script>')

    # ---- /tools ----
    cards = "\n".join("""    <li>
      <a class="tool-card" href="/tools/{slug}/" data-track="tools_viewed" data-track-from="hub">
        <span class="ico" aria-hidden="true">{icon}</span>
        <span class="name">{name}</span>
        <span class="desc">{desc}</span>
        <span class="try">Try it →</span>
      </a>
    </li>""".format(slug=t["slug"], icon=t["icon"], name=e(t["name"]), desc=e(t["hub"]))
        for t in TOOLS)

    itemlist = {
        "@context": "https://schema.org", "@type": "ItemList",
        "name": "Moodshop tools",
        "numberOfItems": len(TOOLS),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": t["name"],
             "url": "%s/tools/%s/" % (origin, t["slug"])}
            for i, t in enumerate(TOOLS)
        ],
    }

    hub_body = """<main id="main">
<header class="wrap narrow tool-head">
  <p class="eyebrow">Free</p>
  <h1>Tools for feelings</h1>
  <p class="lede">Not sure what you’re feeling? Start somewhere.</p>
</header>

<section class="wrap" style="padding-top:clamp(1rem,4vw,2rem);">
  <ul class="tool-grid reveal">
{cards}
  </ul>
  <p class="hint" style="margin-top:1.8rem;">All seven are free and none of them need an account. Nothing you type into any of them is sent to a server — the journal lives in your own browser, and a sent feeling travels inside the link. There’s no model behind any of this: every result is written by hand and picked by what you choose.</p>
</section>

<section class="wrap">
  <p class="eyebrow">Where they lead</p>
  <h2>The tools are free. The feelings cost a dollar.</h2>
  <p class="lede">Each tool ends by pointing at a short piece of writing built for that one feeling — two minutes, no account, and you read its real opening before paying anything.</p>
  <div class="cta-row">
    <a class="btn btn-primary" href="/tools/mood-finder/" data-track="mood_finder_started" data-track-from="tools-hub">Start with Find My Mood</a>
    <a class="btn btn-ghost" href="/moods/">See the eight feelings</a>
  </div>
</section>

<section class="wrap">
{bundle}
</section>
</main>""".format(cards=cards, bundle=ctx["bundle_block"]("tools-hub"))

    write("tools/index.html", page(
        title="Tools for feelings — Moodshop",
        description="Seven free tools for working out what you're feeling: a mood finder, an emotion wheel, a private journal, a message composer and more. No account, no AI, nothing stored.",
        canonical=origin + "/tools/",
        og_title="Moodshop — tools for feelings",
        og_desc="Not sure what you’re feeling? Start somewhere.",
        jsonld=(itemlist,), body=hub_body, active="tools",
    ))

    # ---- the seven ----
    for t in TOOLS:
        body = BODIES[t["slug"]](ctx, t)
        attrs = ' class="mode-2am"' if t.get("dark") else ""
        crumbs = {
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Moodshop", "item": origin + "/"},
                {"@type": "ListItem", "position": 2, "name": "Tools", "item": origin + "/tools/"},
                {"@type": "ListItem", "position": 3, "name": t["name"],
                 "item": "%s/tools/%s/" % (origin, t["slug"])},
            ],
        }
        app = {
            "@context": "https://schema.org", "@type": "WebApplication",
            "name": t["name"] + " — Moodshop",
            "url": "%s/tools/%s/" % (origin, t["slug"]),
            "applicationCategory": "LifestyleApplication",
            "operatingSystem": "Any web browser",
            "description": t["seo_desc"],
            "isAccessibleForFree": True,
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "publisher": {"@type": "Person", "name": ctx["author"]},
        }
        write("tools/%s/index.html" % t["slug"], page(
            title="%s | Moodshop" % t["seo_title"],
            description=t["seo_desc"],
            canonical="%s/tools/%s/" % (origin, t["slug"]),
            og_title="Moodshop — %s" % t["name"],
            og_desc=t["hub"],
            theme="#05050a" if t.get("dark") else "#0e0e15",
            jsonld=(app, crumbs),
            extra_head=scripts,
            body=body, active="tools", body_attrs=attrs,
        ))

    # ---- /today ----
    today_body = """<main id="main">
<span id="today-page" hidden></span>
<header class="wrap narrow tool-head">
  <p class="eyebrow">Today’s mood</p>
  <h1>One feeling a day.</h1>
  <p class="lede">Chosen by the date, not by you — everyone sees the same one today, and it changes at midnight. Come back tomorrow for a different one.</p>
</header>

<section class="wrap" style="padding-top:0;">
  <div class="result-card" id="today-page-face">
    <p class="result-lede">Today</p>
    <p class="result-name" id="today-page-name">—</p>
    <p class="result-desc" id="today-page-tag"></p>
    <p class="result-desc" id="today-page-thought" style="font-style:italic;margin-top:1.4rem;opacity:0.85;"></p>
  </div>
  <div class="cta-row" style="margin-top:1.6rem;">
    <a class="btn btn-primary" id="today-page-link" href="/moods/" data-track="mood_selected" data-track-from="today-page">Read today’s mood</a>
    <a class="btn btn-ghost" href="/tools/mood-finder/" data-track="mood_finder_started" data-track-from="today-page">Not today’s? Find my mood</a>
  </div>
  <noscript><p class="lede" style="margin-top:1.6rem;">Today’s pick is worked out in your browser from the date. With JavaScript off, <a href="/moods/" style="color:var(--ink);">all eight are here</a>.</p></noscript>
</section>

<section class="wrap">
{bundle}
</section>
</main>""".format(bundle=ctx["bundle_block"]("today-page"))

    write("today/index.html", page(
        title="Today’s mood — Moodshop",
        description="One feeling a day, the same one for everybody, changing at midnight. A short piece of writing for whatever today turned out to be.",
        canonical=origin + "/today/",
        og_title="Moodshop — today’s mood",
        og_desc="One feeling a day. It changes at midnight.",
        extra_head=scripts,
        body=today_body, active="today",
    ))

    return [t["slug"] for t in TOOLS]
