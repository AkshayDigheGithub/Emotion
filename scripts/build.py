#!/usr/bin/env python3
"""Build every public Moodshop page from content/moods.json.

Moodshop has no framework and no build step on the host — Vercel serves this
repo as plain files. This script is the "framework": it runs on a laptop, and
what it writes is committed. Adding a 50th mood means adding a 50th entry to
content/moods.json and running:

    python3 scripts/build.py

Generated (do not hand-edit — your edits are overwritten):
    moods-data.js              the same data, for the client
    mood/<slug>/index.html     one sales + SEO page per feeling
    moods/index.html           every feeling
    collections/index.html     themed collections
    about|send|for|help/payment/index.html, 404.html, index.html
    sitemap.xml, robots.txt
    img/og/<slug>.jpg          per-mood social preview (needs Pillow)

NOT generated, and deliberately left alone: the paid reader pages
(calm.html and friends) and bundle.html. Those are what people paid for and
what Buy Me a Coffee redirects to; nothing here may break them.
"""

import html
import json
import os
import re
import sys

import tools_pages

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _load(name):
    return json.load(open(os.path.join(ROOT, "content", name), encoding="utf-8"))


DATA = _load("moods.json")
FEELINGS_DATA = _load("feelings.json")
WHEEL_DATA = _load("wheel.json")
TOOL_CONTENT = _load("tool-content.json")

SITE = DATA["site"]
ORIGIN = SITE["origin"]
MOODS = DATA["moods"]
BUNDLE = DATA["bundle"]
COLLECTIONS = DATA["collections"]

FONTS = ("https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400"
         "&family=Nunito+Sans:wght@300;400;600;700&display=swap")

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'"
           "%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%8E%AD%3C/text%3E%3C/svg%3E")

INDIVIDUAL_TOTAL = sum(m["price"] for m in MOODS)


def e(s):
    return html.escape(str(s), quote=True)


def write(relpath, text):
    path = os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote", relpath)


# --------------------------------------------------------------------------
# shell
# --------------------------------------------------------------------------

NAV_ITEMS = [
    ("/moods/", "Moods", "moods"),
    ("/tools/", "Tools", "tools"),
    ("/collections/", "Collections", "collections"),
    ("/today/", "Today", "today"),
    ("/about/", "About", "about"),
]


def nav(active=""):
    links = []
    for href, label, key in NAV_ITEMS:
        cur = ' aria-current="page"' if key == active else ""
        links.append('      <li><a href="%s"%s>%s</a></li>' % (href, cur, label))
    return """<nav class="nav" aria-label="Main">
  <div class="nav-in">
    <a class="brand" href="/"><span class="dot" aria-hidden="true"></span> Moodshop</a>
    <ul class="nav-links">
%s
    </ul>
    <a class="nav-cta" href="/tools/mood-finder/" data-track="mood_finder_started" data-track-from="nav">Find my mood</a>
  </div>
</nav>""" % "\n".join(links)


def footer():
    mood_links = "\n".join(
        '        <li><a href="/mood/%s/">%s</a></li>' % (m["slug"], e(m["name"])) for m in MOODS[:4]
    )
    return """<footer class="site-foot">
  <div class="wrap">
    <div class="cols">
      <div>
        <h2>Feelings</h2>
        <ul>
%s
          <li><a href="/moods/">All eight →</a></li>
        </ul>
      </div>
      <div>
        <h2>Moodshop</h2>
        <ul>
          <li><a href="/about/">About</a></li>
          <li><a href="/collections/">Collections</a></li>
          <li><a href="/tools/">Tools for feelings</a></li>
          <li><a href="/today/">Today’s mood</a></li>
          <li><a href="/send/">Send a feeling</a></li>
          <li><a href="/free/">Free to read</a></li>
        </ul>
      </div>
      <div>
        <h2>Paying &amp; help</h2>
        <ul>
          <li><a href="/help/payment/">If a payment didn’t open</a></li>
          <li><a href="https://www.buymeacoffee.com/digheakshaf" rel="nofollow noopener">Contact</a></li>
          <li><a href="/about/#terms">Terms</a></li>
          <li><a href="/about/#privacy">Privacy</a></li>
        </ul>
      </div>
    </div>
    <div class="base">
      <span class="wordmark">Moodshop.lol</span>
      <p>A place to go when you want to feel something.</p>
      <p>Payments run through Buy Me a Coffee. No accounts, no email list, nothing follows you after you close the tab.</p>
    </div>
  </div>
</footer>""" % mood_links


# `extra_head` is emitted last: deferred scripts execute in document
# order, and a page-specific script always builds on the shared ones.
def head(title, description, canonical, *, og_title=None, og_desc=None, og_image=None,
         og_type="website", robots="index, follow", extra_head="", jsonld=(), theme="#0e0e15"):
    og_image = og_image or (ORIGIN + "/og-image.jpg")
    blocks = "\n".join(
        '<script type="application/ld+json">\n%s\n</script>' % json.dumps(b, indent=2, ensure_ascii=False)
        for b in jsonld
    )
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="{theme}">

<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{og_desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="Moodshop">
<meta property="og:locale" content="en_US">
<meta property="og:image" content="{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{og_title}">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{og_desc}">
<meta name="twitter:image" content="{og_image}">

<link rel="icon" href="{favicon}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="{fonts}">
<link rel="stylesheet" href="{fonts}" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="{fonts}"></noscript>
<link rel="stylesheet" href="/moodshop.css">
{blocks}
<script defer src="/_vercel/insights/script.js"></script>
<script defer data-website-id="dfid_6nLSJ7Yb6pX8SrM441xsu" data-domain="moodshop.lol" src="https://datafa.st/js/script.js"></script>
<script defer src="/analytics.js"></script>
<script defer src="/moods-data.js"></script>
<script defer src="/moodshop.js"></script>
{extra_head}
</head>""".format(
        title=e(title), description=e(description), canonical=e(canonical), robots=robots,
        theme=theme, og_type=og_type, og_title=e(og_title or title), og_desc=e(og_desc or description),
        og_image=e(og_image), favicon=FAVICON, fonts=FONTS,
        extra_head=extra_head, blocks=blocks,
    )


def page(*, title, description, canonical, body, active="", body_attrs="", **kw):
    return "%s\n<body%s>\n<script>document.documentElement.className+=' js';</script>\n<a class=\"skip\" href=\"#main\">Skip to content</a>\n<div class=\"aura\" aria-hidden=\"true\"></div>\n%s\n%s\n%s\n</body>\n</html>\n" % (
        head(title, description, canonical, **kw), body_attrs, nav(active), body, footer()
    )


# --------------------------------------------------------------------------
# reusable body chunks
# --------------------------------------------------------------------------

def mood_card(m, *, track_from):
    t = m["theme"]
    return """    <li>
      <a class="mood-card" href="/mood/{slug}/" style="background:{card};color:{ink};"
         data-track="mood_selected" data-track-mood="{slug}" data-track-from="{src}">
        <span>
          <span class="name">{name}</span>
          <span class="tag">{tagline}</span>
        </span>
        <span class="foot"><span class="go">Enter the feeling →</span><span class="cost">${price}</span></span>
      </a>
    </li>""".format(slug=m["slug"], card=t["card"], ink=t["cardInk"], name=e(m["name"]),
                    tagline=e(m["tagline"]), price=m["price"], src=track_from)


def mood_grid(track_from):
    cards = "\n".join(mood_card(m, track_from=track_from) for m in MOODS)
    soon = ""
    for w in DATA.get("writingNow", []):
        soon += """
    <li>
      <div class="mood-card soon">
        <span>
          <span class="name">%s</span>
          <span class="tag">%s</span>
        </span>
        <span class="foot"><span class="go">Being written now</span></span>
      </div>
    </li>""" % (e(w["name"]), e(w["tagline"]))
    return '  <ul class="mood-grid reveal">\n%s%s\n  </ul>' % (cards, soon)


def bundle_block(track_from):
    """The pack. Renders a real checkout button only once a Buy Me a Coffee
    Extra exists for it — until then it is a price anchor that points at the
    shelf, never a button that would take money and deliver nothing."""
    saving = INDIVIDUAL_TOTAL - BUNDLE["price"]
    if BUNDLE.get("checkoutUrl"):
        cta = ('<a class="btn btn-primary" href="%s" rel="nofollow noopener" '
               'data-track="bundle_clicked" data-track-from="%s">Get the complete collection — $%s</a>'
               % (e(BUNDLE["checkoutUrl"]), track_from, BUNDLE["price"]))
        badge = '<span class="badge hot">Best value</span>'
        note = '<p class="hint">One payment, one link, all eight. No account.</p>'
    else:
        cta = ('<a class="btn btn-ghost" href="/moods/" data-track="bundle_clicked" '
               'data-track-from="%s">Start with one feeling — from $%s</a>' % (track_from, min(m["price"] for m in MOODS)))
        badge = '<span class="badge">Opening soon</span>'
        note = ('<p class="hint">The pack isn’t buyable yet — there’s no checkout behind it, '
                'and a button that takes $%s and delivers nothing isn’t a button. '
                'Single feelings are open now.</p>' % BUNDLE["price"])
    return """  <div class="bundle reveal">
    {badge}
    <h2>{name}</h2>
    <p class="line">{blurb}</p>
    <div class="price-row">
      <p class="price">${price} <small>once</small></p>
      <p class="was"><s>${total}</s> one at a time — save ${saving}</p>
    </div>
    <ul class="ticks">
      <li>All eight feelings, one payment</li>
      <li>One link that opens every one</li>
      <li>New feelings added to the shelf, free</li>
      <li>Send any of them on, as often as you like</li>
    </ul>
    <div class="cta-row">{cta}</div>
    {note}
  </div>""".format(badge=badge, name=e(BUNDLE["name"]), blurb=e(BUNDLE["blurb"]),
                   price=BUNDLE["price"], total=INDIVIDUAL_TOTAL, saving=saving,
                   cta=cta, note=note)


def share_block(slug, heading="Send this feeling"):
    return """  <div class="share-row-wrap" data-share="{slug}">
    <ul class="share-row">
      <li><button type="button" data-share-to="native">Send this feeling</button></li>
      <li><button type="button" data-share-to="copy">Copy link</button></li>
      <li><a data-share-to="x" href="#">Post on X</a></li>
      <li><a data-share-to="whatsapp" href="#">WhatsApp</a></li>
      <li><button type="button" data-share-to="image">Save the card</button></li>
    </ul>
    <p class="share-status" aria-live="polite"></p>
  </div>""".format(slug=slug)


TRUST = """  <ul class="trust">
    <li>No account required</li>
    <li>Opens the second you pay</li>
    <li>A tiny experience, not a subscription</li>
    <li>Paid through Buy Me a Coffee</li>
  </ul>"""


# --------------------------------------------------------------------------
# moods-data.js
# --------------------------------------------------------------------------

def build_data_js():
    payload = {
        "site": SITE,
        "bundle": {k: v for k, v in BUNDLE.items() if k != "comment"},
        "moods": [
            {k: m[k] for k in ("slug", "name", "tagline", "teaserTitle", "teaser", "teaserTail",
                               "shareLine", "words", "readingTime", "price", "checkoutUrl", "theme")}
            for m in MOODS
        ],
        "collections": COLLECTIONS,
        "finder": DATA["finder"],
        "testimonials": DATA["testimonials"],
    }
    write("moods-data.js",
          "/* Generated by scripts/build.py from content/moods.json. Do not edit. */\n"
          "window.MOODSHOP=%s;\n" % json.dumps(payload, separators=(",", ":"), ensure_ascii=False))


# --------------------------------------------------------------------------
# /mood/<slug>/
# --------------------------------------------------------------------------

def build_mood_pages():
    for m in MOODS:
        slug, t = m["slug"], m["theme"]
        url = "%s/mood/%s/" % (ORIGIN, slug)
        product = {
            "@context": "https://schema.org",
            "@type": "Product",
            "@id": url + "#product",
            "name": "%s — Moodshop" % m["name"],
            "description": m["description"],
            "image": "%s/img/og/%s.jpg" % (ORIGIN, slug),
            "url": url,
            "sku": "moodshop-" + slug,
            "brand": {"@type": "Brand", "name": "Moodshop"},
            "category": "Digital writing",
            "offers": {
                "@type": "Offer",
                "url": m["checkoutUrl"],
                "price": "%.2f" % m["price"],
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock",
                "itemCondition": "https://schema.org/NewCondition",
                "priceValidUntil": "2027-12-31",
                "seller": {"@type": "Person", "name": SITE["author"]},
            },
        }
        crumbs = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Moodshop", "item": ORIGIN + "/"},
                {"@type": "ListItem", "position": 2, "name": "Moods", "item": ORIGIN + "/moods/"},
                {"@type": "ListItem", "position": 3, "name": m["name"], "item": url},
            ],
        }

        others = [x for x in MOODS if x["slug"] != slug][:3]
        more = "\n".join(mood_card(x, track_from="mood-page") for x in others)

        body = """<main id="main">

<header class="wrap" style="padding-top:clamp(2.5rem,8vw,4rem);">
  <p class="eyebrow"><a href="/moods/" style="color:inherit;text-decoration:none;">Moods</a> · {name}</p>
  <h1>{name}</h1>
  <p class="lede" style="font-size:clamp(1.1rem,2.6vw,1.35rem);color:var(--ink);opacity:0.9;max-width:24ch;">{tagline}</p>
  <ul class="chips" style="justify-content:flex-start;margin:0 0 2rem 0;">
    <li>{mins} min read</li>
    <li>{words} words</li>
    <li>${price}</li>
    <li>No account</li>
  </ul>
</header>

<section class="wrap" style="padding-top:0;" aria-labelledby="teaser-h">
  <h2 id="teaser-h" class="sr-only">A free look at {name}</h2>
  <article class="teaser-box{light}" data-mood="{slug}"
     style="background:linear-gradient(160deg,{c0} 0%,{c1} 58%,{c2} 100%);color:{ink};">
    <p class="kicker">{name} · the real opening, free</p>
    <p class="t-title">{teaser_title}</p>
    <p class="excerpt">{teaser}</p>
    <div class="fade-out" aria-hidden="true">{tail}</div>
    <div class="teaser-foot">
      <a class="btn btn-unlock" href="{checkout}" rel="nofollow noopener"
         data-track="checkout_started" data-track-mood="{slug}" data-track-from="mood-page">Enter this feeling — ${price}</a>
      <span class="teaser-meta">Continue into the full experience · about {mins} minutes</span>
    </div>
  </article>
{trust}
  <p class="hint" style="margin-top:0.8rem;">That opening is the real first lines of the piece, not a summary written to sell it. <a href="/help/payment/" style="color:var(--sub);">If a payment doesn’t open the page →</a></p>
</section>

<section class="wrap narrow">
  <h2>What this feeling is</h2>
  <p class="lede">{what}</p>
  <p class="lede" style="margin-bottom:0;">{description}</p>
</section>

<section class="wrap narrow">
  <h2>Keep this moment</h2>
  <p class="lede">One line from {name}, as a link or a square card. Nothing you paid for travels with it.</p>
{share}
  <div class="cta-row" style="margin-top:1.6rem;">
    <a class="btn btn-ghost btn-sm" href="/send/?mood={slug}" data-track="send_feeling_clicked" data-track-mood="{slug}" data-track-from="mood-page">Send {name} to someone →</a>
  </div>
</section>

<section class="wrap">
  <h2>Find another feeling</h2>
  <p class="lede">Eight in total. This is where most people end up next.</p>
  <ul class="mood-grid">
{more}
  </ul>
  <div class="cta-row" style="margin-top:1.6rem;">
    <a class="btn btn-ghost" href="/moods/">All eight feelings →</a>
    <a class="btn btn-ghost" href="/#finder">Not sure? Find my mood</a>
  </div>
</section>

<section class="wrap">
{bundle}
</section>

</main>""".format(
            name=e(m["name"]), tagline=e(m["tagline"]), slug=slug, price=m["price"],
            words=m["words"], mins=m["readingTime"], checkout=e(m["checkoutUrl"]),
            teaser_title=e(m["teaserTitle"]), teaser=e(m["teaser"]), tail=e(m["teaserTail"]),
            what=e(m["whatThisIs"]), description=e(m["description"]),
            c0=t["colors"][0], c1=t["colors"][1], c2=t["colors"][2], ink=t["ink"],
            light=" light" if t["light"] else "",
            trust=TRUST, share=share_block(slug), more=more, bundle=bundle_block("mood-page"),
        )

        write("mood/%s/index.html" % slug, page(
            title="%s — %s | Moodshop" % (m["name"], m["seoTitle"]),
            description=m["description"] + " About %d minutes, $%d, no account." % (m["readingTime"], m["price"]),
            canonical=url,
            og_title="Moodshop — %s" % m["name"].upper(),
            og_desc=m["tagline"],
            og_image="%s/img/og/%s.jpg" % (ORIGIN, slug),
            og_type="product",
            theme=t["colors"][1],
            jsonld=(product, crumbs),
            body=body,
            active="moods",
            body_attrs=' data-mood="%s"' % slug,
        ))


# --------------------------------------------------------------------------
# /moods/
# --------------------------------------------------------------------------

def build_moods_index():
    url = ORIGIN + "/moods/"
    itemlist = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Every feeling in the Moodshop",
        "numberOfItems": len(MOODS),
        "itemListOrder": "https://schema.org/ItemListOrderAscending",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "url": "%s/mood/%s/" % (ORIGIN, m["slug"]),
                "name": m["name"],
            }
            for i, m in enumerate(MOODS)
        ],
    }
    body = """<main id="main">
<header class="wrap" style="padding-top:clamp(2.5rem,8vw,4rem);">
  <p class="eyebrow">All moods</p>
  <h1>Maybe you’re feeling…</h1>
  <p class="lede">Eight short pieces of writing, each built to do exactly one thing. Every one opens with its real first lines, free, before anything is asked of you.</p>
  <div class="cta-row"><a class="btn btn-ghost btn-sm" href="/#finder">Not sure? Find my mood</a><a class="btn btn-ghost btn-sm" href="/free/">Read three for free</a></div>
</header>

<section class="wrap" style="padding-top:clamp(1.5rem,4vw,2.5rem);">
{grid}
</section>

<section class="wrap">
{bundle}
</section>
</main>""".format(grid=mood_grid("moods-index"), bundle=bundle_block("moods-index"))

    write("moods/index.html", page(
        title="Every feeling — Moodshop",
        description="Eight short pieces of writing for very specific feelings: calm, nostalgia, happiness, hope, hurt, sorrow, grief, rage. From $1, no account.",
        canonical=url,
        og_title="Moodshop — every feeling",
        og_desc="Tiny pieces of writing for very specific feelings.",
        jsonld=(itemlist,), body=body, active="moods",
    ))


# --------------------------------------------------------------------------
# /collections/
# --------------------------------------------------------------------------

def build_collections():
    url = ORIGIN + "/collections/"
    cards = "\n".join("""    <li class="collection-card" style="background:{card};color:{ink};">
      <span>
        <span class="name">{name}</span>
        <span class="tag">{tag}</span>
      </span>
      <p class="state">{state}</p>
    </li>""".format(card=c["theme"]["card"], ink=c["theme"]["cardInk"], name=e(c["name"]),
                    tag=e(c["tagline"]),
                    state="Coming soon" if c["status"] == "coming-soon" else e(c["status"]))
                     for c in COLLECTIONS)

    body = """<main id="main">
<header class="wrap" style="padding-top:clamp(2.5rem,8vw,4rem);">
  <p class="eyebrow">Collections</p>
  <h1>Feelings that arrive together.</h1>
  <p class="lede">Single feelings are on the shelf now. These are the sets being written — each one a handful of pieces for a single kind of night. Nothing here is on sale yet, and nothing here pretends to be.</p>
</header>

<section class="wrap" style="padding-top:clamp(1.5rem,4vw,2.5rem);">
  <ul class="cards reveal">
{cards}
  </ul>
  <p class="hint" style="margin-top:1.6rem;">No dates, because I’d rather not give you one I’d miss. There’s no list to join — check back, or follow whatever brought you here.</p>
</section>

<section class="wrap">
  <h2>Open now</h2>
  <p class="lede">The eight single feelings, from $1 each.</p>
{grid}
</section>

<section class="wrap">
{bundle}
</section>
</main>""".format(cards=cards, grid=mood_grid("collections"), bundle=bundle_block("collections"))

    write("collections/index.html", page(
        title="Collections — Moodshop",
        description="Themed sets of short emotional writing, being written now: heartbreak, 2AM, I miss you, healing, Sunday night. The eight single feelings are open today.",
        canonical=url,
        og_title="Moodshop — collections",
        og_desc="Feelings that arrive together. Coming soon.",
        body=body, active="collections",
    ))


# --------------------------------------------------------------------------
# hand-written pages (body lives in templates/)
# --------------------------------------------------------------------------

def template(name, **subs):
    raw = open(os.path.join(ROOT, "templates", name), encoding="utf-8").read()
    for k, v in subs.items():
        raw = raw.replace("{{%s}}" % k, str(v))
    return raw


def build_static_pages():
    # ---- homepage ----
    faq = [
        ("What exactly am I paying for?",
         "One web page with one short piece of writing on it — around 200 words, set in its own colour and typography for that one feeling. It opens in your browser the second you pay. There's no file, no app, no account."),
        ("Two hundred words? That's short.",
         "On purpose. These are meant to be read slowly, once, and felt — not skimmed and filed away. A piece that takes two minutes and actually moves you beats one that takes twenty and doesn't."),
        ("Can I read something before I pay?",
         "Yes — every one of the eight. Each mood page opens with the real first lines of that piece, not a teaser written to sell it. Three other pieces are free in full."),
        ("Can I send one to someone else?",
         "Yes, and it's the best thing here. You can send a feeling to someone before you've bought anything — pick the mood, write a line, and the link carries your note. Nothing is stored anywhere; the note lives in the link itself."),
        ("Do I need an account?",
         "No. Payment happens on Buy Me a Coffee and their redirect takes you straight to the piece. Moodshop stores nothing about you and can't email you even if it wanted to."),
        ("Can I come back to it later?",
         "Yes. The link stays live — bookmark it after you pay and reopen it whenever the feeling comes back around."),
        ("What if it doesn't do anything for me?",
         "Then it cost you a dollar or two and you should tell me so. Message me through Buy Me a Coffee — refunds on a $2 piece of writing aren't worth anyone's afternoon, so I'd rather just send you a different one."),
    ]
    faq_html = "\n".join(
        "    <details>\n      <summary>%s</summary>\n      <p>%s</p>\n    </details>" % (e(q), e(a))
        for q, a in faq
    )
    faq_ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faq
        ],
    }
    website_ld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Moodshop",
        "url": ORIGIN + "/",
        "description": "Tiny pieces of writing for very specific feelings.",
        "publisher": {"@type": "Person", "name": SITE["author"]},
    }
    itemlist_ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "The Moodshop shelf",
        "numberOfItems": len(MOODS),
        "itemListOrder": "https://schema.org/ItemListOrderAscending",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "item": {
                    "@type": "Product",
                    "@id": "%s/mood/%s/#product" % (ORIGIN, m["slug"]),
                    "name": m["name"],
                    "description": m["description"],
                    "image": "%s/img/og/%s.jpg" % (ORIGIN, m["slug"]),
                    "url": "%s/mood/%s/" % (ORIGIN, m["slug"]),
                    "sku": "moodshop-" + m["slug"],
                    "brand": {"@type": "Brand", "name": "Moodshop"},
                    "category": "Digital writing",
                    "offers": {
                        "@type": "Offer",
                        "url": m["checkoutUrl"],
                        "price": "%.2f" % m["price"],
                        "priceCurrency": "USD",
                        "availability": "https://schema.org/InStock",
                        "itemCondition": "https://schema.org/NewCondition",
                        "priceValidUntil": "2027-12-31",
                        "seller": {"@type": "Person", "name": SITE["author"]},
                    },
                },
            }
            for i, m in enumerate(MOODS)
        ],
    }

    write("index.html", page(
        title="Moodshop — How do you want to feel?",
        description="Tiny pieces of writing for very specific feelings. Read the real opening of every one free, then enter the feeling for $1. No account, no email.",
        canonical=ORIGIN + "/",
        og_title="Moodshop — How do you want to feel?",
        og_desc="Tiny pieces of writing for very specific feelings.",
        jsonld=(website_ld, itemlist_ld, faq_ld),
        body=template("home.html", GRID=mood_grid("home"), BUNDLE=bundle_block("home"),
                      FAQ=faq_html, TRUST=TRUST, MIN_PRICE=min(m["price"] for m in MOODS)),
    ))

    # ---- about ----
    write("about/index.html", page(
        title="About Moodshop — why the feeling is the product",
        description="Moodshop is one person making tiny pieces of writing for moments that are hard to put into words. Why they're short, why there are no accounts, and what you can expect.",
        canonical=ORIGIN + "/about/",
        og_title="About Moodshop",
        og_desc="We make tiny pieces of writing for moments that are difficult to put into words.",
        body=template("about.html"), active="about",
    ))

    # ---- send ----
    write("send/index.html", page(
        title="Send a feeling to someone — Moodshop",
        description="Pick a feeling, write a line, send the link. Sometimes words are easier to send than to say. No account, nothing stored.",
        canonical=ORIGIN + "/send/",
        og_title="Send someone a feeling",
        og_desc="Sometimes words are easier to send than to say.",
        body=template("send.html"),
    ))

    # ---- for (the receiving end) ----
    write("for/index.html", page(
        title="Someone sent you a feeling — Moodshop",
        description="Someone sent you something to read.",
        canonical=ORIGIN + "/for/",
        robots="noindex, follow",
        og_title="Someone sent you a feeling",
        og_desc="Open it when you have two quiet minutes.",
        body=template("for.html"),
    ))

    # ---- payment help ----
    write("help/payment/index.html", page(
        title="If a payment didn’t open your feeling — Moodshop",
        description="What to do if a Moodshop payment was cancelled, failed, or finished without opening the piece.",
        canonical=ORIGIN + "/help/payment/",
        robots="noindex, follow",
        og_title="Payment help — Moodshop",
        og_desc="Cancelled, failed, or paid and nothing opened.",
        body=template("payment-help.html"),
    ))

    # ---- 404 ----
    write("404.html", page(
        title="This feeling got lost — Moodshop",
        description="That page isn’t here.",
        canonical=ORIGIN + "/404.html",
        robots="noindex, nofollow",
        og_title="Moodshop",
        og_desc="A place to go when you want to feel something.",
        body=template("404.html", GRID=mood_grid("404")),
    ))


# --------------------------------------------------------------------------
# sitemap + robots
# --------------------------------------------------------------------------

def build_sitemap():
    urls = [
        (ORIGIN + "/", "weekly", "1.0"),
        (ORIGIN + "/moods/", "weekly", "0.9"),
        (ORIGIN + "/collections/", "monthly", "0.6"),
        (ORIGIN + "/about/", "monthly", "0.5"),
        (ORIGIN + "/send/", "monthly", "0.6"),
        (ORIGIN + "/tools/", "weekly", "0.9"),
        (ORIGIN + "/today/", "daily", "0.7"),
        (ORIGIN + "/free/", "monthly", "0.8"),
        (ORIGIN + "/free/cant-sleep.html", "yearly", "0.7"),
        (ORIGIN + "/free/waiting-for-news.html", "yearly", "0.7"),
        (ORIGIN + "/free/the-strong-one.html", "yearly", "0.7"),
    ]
    urls += [("%s/mood/%s/" % (ORIGIN, m["slug"]), "monthly", "0.9") for m in MOODS]
    urls += [("%s/tools/%s/" % (ORIGIN, t["slug"]), "monthly", "0.8") for t in tools_pages.TOOLS]

    body = "\n".join(
        "  <url>\n    <loc>%s</loc>\n    <changefreq>%s</changefreq>\n    <priority>%s</priority>\n  </url>"
        % (u, cf, pr) for u, cf, pr in urls
    )
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n' % body)

    # The reader pages are what people pay for: unlisted, and kept that way.
    disallow = "\n".join("Disallow: %s" % m["readerPage"] for m in MOODS)
    write("robots.txt",
          "User-agent: *\nAllow: /\n\n"
          "# The pages below are what a payment opens. Nothing links to them,\n"
          "# so Disallow keeps them out without risking a bare-URL listing.\n"
          "# /for/ and /help/payment/ ARE linked, so they rely on their own\n"
          "# noindex instead — a crawler has to be let in to read that.\n"
          "%s\nDisallow: %s\n\n"
          "Sitemap: %s/sitemap.xml\n" % (disallow, BUNDLE["deliveryPage"], ORIGIN))


# --------------------------------------------------------------------------
# per-mood Open Graph images
# --------------------------------------------------------------------------

def build_og_images():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("! Pillow not installed — skipping img/og/*.jpg (run: pip install Pillow)")
        return

    serif = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
    serif_it = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
    sans = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    for f in (serif, serif_it, sans):
        if not os.path.exists(f):
            print("! font missing (%s) — skipping OG images" % f)
            return

    W, H = 1200, 630

    def rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def wrap(draw, text, font, max_w):
        words, lines, line = text.split(), [], ""
        for w in words:
            test = (line + " " + w).strip()
            if draw.textlength(test, font=font) > max_w and line:
                lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)
        return lines

    os.makedirs(os.path.join(ROOT, "img", "og"), exist_ok=True)

    for m in MOODS:
        t = m["theme"]
        a, b, c = (rgb(s) for s in t["colors"])
        strip = Image.new("RGB", (1, H))
        px = strip.load()
        for y in range(H):
            k = y / (H - 1)
            if k <= 0.58:
                s, eC, kk = a, b, k / 0.58
            else:
                s, eC, kk = b, c, (k - 0.58) / 0.42
            px[0, y] = tuple(round(s[i] + (eC[i] - s[i]) * kk) for i in range(3))
        img = strip.resize((W, H))
        d = ImageDraw.Draw(img)
        ink = rgb(t["ink"])

        d.text((70, 60), "MOODSHOP", font=ImageFont.truetype(sans, 26), fill=ink)
        name_f = ImageFont.truetype(serif, 118)
        d.text((70, 130), m["name"].upper(), font=name_f, fill=ink)
        d.line([(70, 300), (190, 300)], fill=ink, width=3)

        tag_f = ImageFont.truetype(serif_it, 46)
        y = 340
        for line in wrap(d, m["tagline"], tag_f, W - 200):
            d.text((70, y), line, font=tag_f, fill=ink)
            y += 62

        foot = ImageFont.truetype(sans, 24)
        d.text((70, H - 70), "moodshop.lol  ·  %d min read  ·  $%d" % (m["readingTime"], m["price"]),
               font=foot, fill=ink)

        path = "img/og/%s.jpg" % m["slug"]
        img.save(os.path.join(ROOT, path), "JPEG", quality=80, optimize=True, progressive=True)
        print("wrote", path)


def build_tool_pages():
    """Hand the shared page furniture to scripts/tools_pages.py so the tools
    get exactly the same nav, footer and <head> as the rest of the site."""
    by_slug = {m["slug"]: m for m in MOODS}
    feel_by_slug = {f["slug"]: f for f in FEELINGS_DATA["feelings"]}

    tools_pages.build({
        "origin": ORIGIN,
        "author": SITE["author"],
        "page": page,
        "write": write,
        "mood_card": mood_card,
        "bundle_block": bundle_block,
        "mood": lambda s: by_slug[s],
        "min_price": min(m["price"] for m in MOODS),
        "feelings": FEELINGS_DATA,
        "wheel": WHEEL_DATA,
        "tool_content": TOOL_CONTENT,
        "product_of": lambda s: feel_by_slug[s]["product"],
        "feeling_name": lambda s: feel_by_slug[s]["name"],
    })


def main():
    build_data_js()
    build_mood_pages()
    build_moods_index()
    build_collections()
    build_static_pages()
    build_tool_pages()
    build_sitemap()
    build_og_images()
    print("\ndone — %d moods, individual total $%d, pack $%d"
          % (len(MOODS), INDIVIDUAL_TOTAL, BUNDLE["price"]))


if __name__ == "__main__":
    main()
