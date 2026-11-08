#!/usr/bin/env python3
"""Build every public Moodshop page from content/moods.json.

Moodshop has no framework and no build step on the host — Vercel serves this
repo as plain files. This script is the "framework": it runs on a laptop, and
what it writes is committed. Adding a 50th mood means adding a 50th entry to
content/moods.json and running:

    python3 scripts/build.py

The site is English throughout; its words live in content/strings.json
(see scripts/strings.py). One URL per page, no language prefixes.

Generated (do not hand-edit — your edits are overwritten):
    moods-data.js              the same data, for the client
    mood/<slug>/index.html     one sales + SEO page per feeling
    moods/index.html           every feeling
    collections/index.html     themed collections
    about|send|for|help/payment/index.html, 404.html, index.html
    shop/, tools/…, today/
    sitemap.xml, robots.txt
    img/og/<slug>.jpg          per-mood social preview (needs Pillow)

NOT generated, and deliberately left alone: the paid reader pages
(calm.html and friends) and bundle.html. Those are what people paid for and
what Buy Me a Coffee redirects to; nothing here may break them.
"""

import datetime
import html
import json
import os
import re
import subprocess
import sys

import strings
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
PRODUCTS = DATA.get("products", [])
COLLECTIONS = DATA["collections"]

FONTS = ("https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400"
         "&family=Nunito+Sans:wght@300;400;600;700&display=swap")

# Google AdSense. One tag, site-wide: the loader is all that Auto ads
# need, and the placements themselves are configured in the AdSense
# account rather than here. Deliberately absent from the paid reader
# pages (calm.html and friends, bundle.html) — nobody pays to read
# something and then gets served ads inside it — and from 404.html,
# because a page with no content of its own is not a place for ads.
ADSENSE = ('<script async src="https://pagead2.googlesyndication.com/pagead/js/'
           'adsbygoogle.js?client=ca-pub-1650962715407503"\n'
           '     crossorigin="anonymous"></script>')

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'"
           "%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%8E%AD%3C/text%3E%3C/svg%3E")

INDIVIDUAL_TOTAL = sum(m["price"] for m in MOODS)
MIN_PRICE = min(m["price"] for m in MOODS)
MAX_PRICE = max(m["price"] for m in MOODS)

# One language. Every string comes from content/strings.json.
EN = strings.load(MOODS, COLLECTIONS, DATA.get("writingNow", []))


def e(s):
    return html.escape(str(s), quote=True)


def write(relpath, text):
    path = os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote", relpath)


# --------------------------------------------------------------------------
# when a page last actually changed
# --------------------------------------------------------------------------
#
# <lastmod> is the one hint in a sitemap that Google still leans on, which
# is exactly why it has to be true. The mtime of a generated file is no use
# — every build rewrites every file — so the date comes from the last commit
# that touched the *sources* of that page's words: the content JSON, the
# language catalogue, the template. A source with uncommitted edits counts
# as today, because it is about to be.
#
# Deliberately not included: scripts/build.py itself. Changing the page
# furniture does not mean 143 pages changed for a reader, and a sitemap
# that claims everything changed on every build is one nobody believes.

TODAY = datetime.date.today().isoformat()
_DATES = {}

# A date we are not entitled to state. See _boundary() below.
UNDATABLE = object()


def _git(args):
    try:
        r = subprocess.run(["git"] + args, cwd=ROOT, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


_BOUNDARY = None


def _boundary():
    """The graft point of a shallow clone, as (commit hashes, its date).

    In a shallow clone git holds no parent for the oldest commit it fetched,
    so it cannot diff that commit against anything. Every file whose real
    last edit happened before the graft therefore looks to `git log` as
    though it were introduced *by* the graft, and asking when it last
    changed returns the graft's date instead of the truth.

    That is not a corner case here: cloud build sessions clone shallow by
    default, and a build in one once stamped eleven URLs with a boundary
    date seven weeks newer than the real edit. So when the history is
    shallow we find the graft and refuse to quote its date as fact.

    ("" for a full clone, where the root commit really did add its files.)
    """
    global _BOUNDARY
    if _BOUNDARY is None:
        if _git(["rev-parse", "--is-shallow-repository"]) == "true":
            heads = _git(["rev-list", "--max-parents=0", "HEAD"]).split()
            dates = [_git(["log", "-1", "--format=%cs", h]) for h in heads]
            _BOUNDARY = (frozenset(heads), max([d for d in dates if d] or [""]))
        else:
            _BOUNDARY = (frozenset(), "")
    return _BOUNDARY


def _file_date(rel):
    """When this one source last really changed, or UNDATABLE."""
    if not os.path.exists(os.path.join(ROOT, rel)):
        return ""
    if _git(["status", "--porcelain", "--", rel]):
        return TODAY                          # edited, not yet committed
    last = _git(["log", "-1", "--format=%H %cs", "--", rel])
    if not last:
        return TODAY                          # no commit records it yet
    commit, _, date = last.partition(" ")
    if commit in _boundary()[0]:
        return UNDATABLE
    return date or TODAY


def source_date(*relpaths):
    """The newest 'last really changed' date across these source files.

    None when the honest answer is "no idea" — the caller then leaves
    <lastmod> out altogether, which the sitemap spec allows and which
    costs far less trust than a date that is wrong.
    """
    best = ""
    capped = False
    for rel in relpaths:
        if rel not in _DATES:
            _DATES[rel] = _file_date(rel)
        if _DATES[rel] is UNDATABLE:
            capped = True
        else:
            best = max(best, _DATES[rel])
    # An undatable source last changed at *or before* the graft, so a known
    # sibling at least that recent still settles the newest date between
    # them. Only when nothing known reaches the graft is the answer unknown.
    if capped and (not best or best < _boundary()[1]):
        return None
    return best or TODAY


# --------------------------------------------------------------------------
# shell
# --------------------------------------------------------------------------

NAV_ITEMS = [
    ("/moods/", "nav.moods", "moods"),
    ("/shop/", "nav.shop", "shop"),
    ("/tools/", "nav.tools", "tools"),
    ("/collections/", "nav.collections", "collections"),
    ("/today/", "nav.today", "today"),
    ("/about/", "nav.about", "about"),
]


def nav(path, active=""):
    links = []
    for href, key, active_key in NAV_ITEMS:
        cur = ' aria-current="page"' if active_key == active else ""
        links.append('      <li><a href="%s"%s>%s</a></li>'
                     % (e(href), cur, e(EN.t(key))))
    return """<nav class="nav" aria-label="{aria}">
  <div class="nav-in">
    <a class="brand" href="{home}"><span class="dot" aria-hidden="true"></span> Moodshop</a>
    <ul class="nav-links">
{links}
    </ul>
    <div class="nav-end">
      <a class="nav-cta" href="{finder}" data-track="mood_finder_started" data-track-from="nav">{cta}</a>
    </div>
  </div>
</nav>""".format(aria=e(EN.t("nav.aria")), home=e("/"), links="\n".join(links),
                 finder="/tools/mood-finder/", cta=e(EN.t("nav.cta")))


def footer():
    mood_links = "\n".join(
        '        <li><a href="%s">%s</a></li>' % (e("/mood/%s/" % m["slug"]), e(m["name"]))
        for m in EN.moods()[:4]
    )
    return """<footer class="site-foot">
  <div class="wrap">
    <div class="cols">
      <div>
        <h2>{feelings}</h2>
        <ul>
{mood_links}
          <li><a href="{moods}">{all_eight}</a></li>
        </ul>
      </div>
      <div>
        <h2>{shop}</h2>
        <ul>
          <li><a href="{shop_u}">{shop_l}</a></li>
          <li><a href="{about}">{about_l}</a></li>
          <li><a href="{collections}">{collections_l}</a></li>
          <li><a href="{tools}">{tools_l}</a></li>
          <li><a href="{today}">{today_l}</a></li>
          <li><a href="{send}">{send_l}</a></li>
          <li><a href="{free}">{free_l}</a></li>
        </ul>
      </div>
      <div>
        <h2>{payhelp}</h2>
        <ul>
          <li><a href="{help}">{help_l}</a></li>
          <li><a href="{contact_u}" rel="noopener">{contact}</a></li>
          <li><a href="{terms}">{terms_l}</a></li>
          <li><a href="{privacy}">{privacy_l}</a></li>
        </ul>
      </div>
    </div>
    <div class="base">
      <span class="wordmark">Moodshop.lol</span>
      <p>{tagline}</p>
      <p>{payments}</p>
    </div>
  </div>
</footer>""".format(
        feelings=e(EN.t("foot.feelings")), mood_links=mood_links,
        moods=e("/moods/"), all_eight=e(EN.t("foot.allEight")),
        shop=e(EN.t("foot.shop")),
        shop_u=e("/shop/"), shop_l=e(EN.t("nav.shop")),
        about=e("/about/"), about_l=e(EN.t("foot.about")),
        collections=e("/collections/"), collections_l=e(EN.t("foot.collections")),
        tools=e("/tools/"), tools_l=e(EN.t("foot.tools")),
        today=e("/today/"), today_l=e(EN.t("foot.today")),
        send=e("/send/"), send_l=e(EN.t("foot.send")),
        free=e("/free/"), free_l=e(EN.t("foot.free")),
        payhelp=e(EN.t("foot.payHelp")),
        help=e("/help/payment/"), help_l=e(EN.t("foot.paymentDidnt")),
        contact=e(EN.t("foot.contact")), contact_u=e(SITE["contact"]),
        terms=e("/about/#terms"), terms_l=e(EN.t("foot.terms")),
        privacy=e("/about/#privacy"), privacy_l=e(EN.t("foot.privacy")),
        tagline=e(EN.site("tagline")), payments=e(EN.t("foot.payments")),
    )


# `extra_head` is emitted last: deferred scripts execute in document
# order, and a page-specific script always builds on the shared ones.
def head(path, title, description, *, og_title=None, og_desc=None, og_image=None,
         og_type="website", robots="index, follow", extra_head="", jsonld=(), theme="#0e0e15",
         keywords="", ads=True):
    """The <head>. The canonical is this page's own URL."""
    canonical = ORIGIN + path
    og_image = og_image or (ORIGIN + "/og-image.jpg")
    blocks = "\n".join(
        '<script type="application/ld+json">\n%s\n</script>' % json.dumps(b, indent=2, ensure_ascii=False)
        for b in jsonld
    )
    return """<!DOCTYPE html>
<html lang="{htmllang}" dir="{dir}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="{theme}">
{keywords}
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{og_desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="Moodshop">
<meta property="og:locale" content="{locale}">
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
<script defer src="{data_js}"></script>
<script defer src="/moodshop.js"></script>
{adsense}{extra_head}
</head>""".format(
        htmllang=EN.hreflang, dir=EN.dir,
        title=e(title), description=e(description), canonical=e(canonical), robots=robots,
        locale=EN.locale,
        keywords=('<meta name="keywords" content="%s">\n' % e(keywords)) if keywords else "",
        theme=theme, og_type=og_type, og_title=e(og_title or title), og_desc=e(og_desc or description),
        og_image=e(og_image), favicon=FAVICON, fonts=FONTS,
        data_js="/moods-data.js",
        adsense=(ADSENSE + "\n") if ads else "",
        extra_head=extra_head, blocks=blocks,
    )


def page(path, *, title, description, body, active="", body_attrs="", **kw):
    return ("%s\n<body%s>\n<script>document.documentElement.className+=' js';</script>\n"
            "<a class=\"skip\" href=\"#main\">%s</a>\n<div class=\"aura\" aria-hidden=\"true\"></div>\n"
            "%s\n%s\n%s\n</body>\n</html>\n") % (
        head(path, title, description, **kw), body_attrs, e(EN.t("shell.skip")),
        nav(path, active), body, footer()
    )


# --------------------------------------------------------------------------
# reusable body chunks
# --------------------------------------------------------------------------

def mood_card(m, *, track_from):
    m = EN.mood(m)
    t = m["theme"]
    return """    <li>
      <a class="mood-card" href="{href}" style="background:{card};color:{ink};"
         data-track="mood_selected" data-track-mood="{slug}" data-track-from="{src}">
        <span>
          <span class="name">{name}</span>
          <span class="tag">{tagline}</span>
        </span>
        <span class="foot"><span class="go">{enter}</span><span class="cost">${price}</span></span>
      </a>
    </li>""".format(href=e("/mood/%s/" % m["slug"]), slug=m["slug"], card=t["card"],
                    ink=t["cardInk"], name=e(m["name"]), tagline=e(m["tagline"]),
                    price=m["price"], src=track_from, enter=e(EN.t("card.enter")))


def mood_grid(track_from):
    cards = "\n".join(mood_card(m, track_from=track_from) for m in MOODS)
    soon = ""
    for w in EN.writing_now():
        soon += """
    <li>
      <div class="mood-card soon">
        <span>
          <span class="name">%s</span>
          <span class="tag">%s</span>
        </span>
        <span class="foot"><span class="go">%s</span></span>
      </div>
    </li>""" % (e(w["name"]), e(w["tagline"]), e(EN.t("card.soon")))
    return '  <ul class="mood-grid reveal">\n%s%s\n  </ul>' % (cards, soon)


def bundle_block(track_from):
    """The pack. Renders a real checkout button only once a Buy Me a Coffee
    Extra exists for it — until then it is a price anchor that points at the
    shelf, never a button that would take money and deliver nothing."""
    saving = INDIVIDUAL_TOTAL - BUNDLE["price"]
    b = EN.bundle(BUNDLE)
    if BUNDLE.get("checkoutUrl"):
        cta = ('<a class="btn btn-primary" href="%s" rel="nofollow noopener" '
               'data-track="bundle_clicked" data-track-from="%s">%s</a>'
               % (e(BUNDLE["checkoutUrl"]), track_from,
                  e(EN.t("bundle.cta", price=BUNDLE["price"]))))
        badge = '<span class="badge hot">%s</span>' % e(EN.t("bundle.badgeBest"))
        note = '<p class="hint">%s</p>' % e(EN.t("bundle.note"))
    else:
        cta = ('<a class="btn btn-ghost" href="%s" data-track="bundle_clicked" '
               'data-track-from="%s">%s</a>'
               % (e("/moods/"), track_from, e(EN.t("bundle.ctaSoon", price=MIN_PRICE))))
        badge = '<span class="badge">%s</span>' % e(EN.t("bundle.badgeSoon"))
        note = '<p class="hint">%s</p>' % e(EN.t("bundle.noteSoon", price=BUNDLE["price"]))
    return """  <div class="bundle reveal">
    {badge}
    <h2>{name}</h2>
    <p class="line">{blurb}</p>
    <div class="price-row">
      <p class="price">${price} <small>{once}</small></p>
      <p class="was">{was}</p>
    </div>
    <ul class="ticks">
      <li>{tick1}</li>
      <li>{tick2}</li>
      <li>{tick3}</li>
      <li>{tick4}</li>
    </ul>
    <div class="cta-row">{cta}</div>
    {note}
  </div>""".format(badge=badge, name=e(b["name"]), blurb=e(b["blurb"]),
                   price=BUNDLE["price"], once=e(EN.t("bundle.once")),
                   was=EN.t("bundle.was", total=INDIVIDUAL_TOTAL, saving=saving),
                   tick1=e(EN.t("bundle.tick1")), tick2=e(EN.t("bundle.tick2")),
                   tick3=e(EN.t("bundle.tick3")), tick4=e(EN.t("bundle.tick4")),
                   cta=cta, note=note)


def product_card(p, track_from):
    """One shop product. Sold through its own checkout link (Gumroad for
    now), never through the Buy Me a Coffee redirect the pieces use."""
    ticks = "\n".join("      <li>%s</li>" % e(t) for t in p.get("ticks", []))
    return """  <div class="bundle guide reveal" id="product-{slug}">
    <span class="badge hot">{kind}</span>
    <h2>{name}</h2>
    <p class="line">{line} {blurb}</p>
    <div class="price-row">
      <p class="price">${price} <small>{once}</small></p>
      <p class="was">{details}</p>
    </div>
    <ul class="ticks">
{ticks}
    </ul>
    <div class="cta-row"><a class="btn btn-primary" href="{url}" rel="noopener"
       data-track="guide_clicked" data-track-mood="{slug}" data-track-from="{src}">{cta}</a></div>
    <p class="hint">{note}</p>
  </div>""".format(
        slug=e(p["slug"]), kind=e(p["kind"]), name=e(p["name"]),
        line=e(p["line"]), blurb=e(p["blurb"]), price=e(p["price"]),
        once=e(EN.t("bundle.once")), details=e(p["details"]), ticks=ticks,
        url=e(p["checkoutUrl"]), src=track_from,
        cta=e(EN.t("guide.cta", price=p["price"])),
        note=e(EN.t("guide.note", seller=p.get("seller", "Gumroad"))))


def guide_block(track_from, *, mood=None):
    """Shop products, cross-sold on the homepage (the `featured` ones) or on
    a mood page (the ones that list that mood under `moods`). Ends with a
    link to the whole shop."""
    if mood is None:
        picked = [p for p in PRODUCTS if p.get("featured")]
    else:
        picked = [p for p in PRODUCTS if mood in p.get("moods", [])]
    if not picked:
        return ""
    inner = "\n".join(product_card(p, track_from) for p in picked)
    # Trailing blank line included, so an empty block leaves no trace in
    # the pages it is skipped on.
    return """<section class="wrap" id="guides" aria-labelledby="guides-h">
  <div class="reveal">
    <p class="eyebrow">{eyebrow}</p>
    <h2 id="guides-h">{h}</h2>
  </div>
{inner}
  <div class="cta-row" style="margin-top:1.6rem;"><a class="btn btn-ghost" href="{shop}">{to_shop}</a></div>
</section>

""".format(eyebrow=e(EN.t("guide.eyebrow")), h=e(EN.t("guide.h")), inner=inner,
           shop=e("/shop/"), to_shop=e(EN.t("guide.toShop")))


def share_block(slug):
    return """  <div class="share-row-wrap" data-share="{slug}">
    <ul class="share-row">
      <li><button type="button" data-share-to="native">{native}</button></li>
      <li><button type="button" data-share-to="copy">{copy}</button></li>
      <li><a data-share-to="x" href="#">{x}</a></li>
      <li><a data-share-to="whatsapp" href="#">{wa}</a></li>
      <li><button type="button" data-share-to="image">{img}</button></li>
    </ul>
    <p class="share-status" aria-live="polite"></p>
  </div>""".format(slug=slug, native=e(EN.t("share.native")), copy=e(EN.t("share.copy")),
                   x=e(EN.t("share.x")), wa=e(EN.t("share.whatsapp")),
                   img=e(EN.t("share.image")))


def trust():
    return '  <ul class="trust">\n%s\n  </ul>' % "\n".join(
        "    <li>%s</li>" % e(EN.t("trust.%d" % i)) for i in (1, 2, 3, 4)
    )


# --------------------------------------------------------------------------
# moods-data.js
# --------------------------------------------------------------------------

def build_data_js():
    """The data moodshop.js reads: the moods, the finder, the strings."""
    payload = {
        "site": SITE,
        "lang": EN.code,
        "dir": EN.dir,
        "base": "",
        "bundle": {k: v for k, v in EN.bundle(BUNDLE).items() if k != "comment"},
        "moods": [
            {k: m[k] for k in ("slug", "name", "tagline", "teaserTitle", "teaser", "teaserTail",
                               "shareLine", "words", "readingTime", "price", "checkoutUrl", "theme")}
            for m in EN.moods()
        ],
        "collections": EN.collections(),
        "finder": EN.finder(DATA["finder"]),
        "testimonials": DATA["testimonials"],
        "i18n": EN.js(),
    }
    write("moods-data.js",
          "/* Generated by scripts/build.py from content/moods.json + "
          "content/strings.json. Do not edit. */\n"
          "window.MOODSHOP=%s;\n" % json.dumps(payload, separators=(",", ":"),
                                               ensure_ascii=False))


# --------------------------------------------------------------------------
# /mood/<slug>/
# --------------------------------------------------------------------------

def build_mood_pages():
    for base in MOODS:
        m = EN.mood(base)
        slug, t = m["slug"], m["theme"]
        path = "/mood/%s/" % slug
        url = ORIGIN + path
        product = {
            "@context": "https://schema.org",
            "@type": "Product",
            "@id": url + "#product",
            "name": "%s — Moodshop" % m["name"],
            "description": m["description"],
            "image": "%s/img/og/%s.jpg" % (ORIGIN, slug),
            "url": url,
            "sku": "moodshop-" + slug,
            "inLanguage": EN.hreflang,
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
                {"@type": "ListItem", "position": 1, "name": "Moodshop",
                 "item": ORIGIN + "/"},
                {"@type": "ListItem", "position": 2, "name": EN.t("moodpage.crumb"),
                 "item": ORIGIN + "/moods/"},
                {"@type": "ListItem", "position": 3, "name": m["name"], "item": url},
            ],
        }

        others = [x for x in MOODS if x["slug"] != slug][:3]
        more = "\n".join(mood_card(x, track_from="mood-page") for x in others)

        body = """<main id="main">

<header class="wrap" style="padding-top:clamp(2.5rem,8vw,4rem);">
  <p class="eyebrow"><a href="{moods_url}" style="color:inherit;text-decoration:none;">{crumb}</a> · {name}</p>
  <h1>{name}</h1>
  <p class="lede" style="font-size:clamp(1.1rem,2.6vw,1.35rem);color:var(--ink);opacity:0.9;max-width:24ch;">{tagline}</p>
  <ul class="chips" style="justify-content:flex-start;margin:0 0 2rem 0;">
    <li>{min_read}</li>
    <li>{word_count}</li>
    <li>${price}</li>
    <li>{no_account}</li>
  </ul>
</header>

<section class="wrap" style="padding-top:0;" aria-labelledby="teaser-h">
  <h2 id="teaser-h" class="sr-only">{free_look}</h2>
  <article class="teaser-box{light}" data-mood="{slug}"
     style="background:linear-gradient(160deg,{c0} 0%,{c1} 58%,{c2} 100%);color:{ink};">
    <p class="kicker">{kicker}</p>
    <p class="t-title">{teaser_title}</p>
    <p class="excerpt">{teaser}</p>
    <div class="fade-out" aria-hidden="true">{tail}</div>
    <div class="teaser-foot">
      <a class="btn btn-unlock" href="{checkout}" rel="nofollow noopener"
         data-track="checkout_started" data-track-mood="{slug}" data-track-from="mood-page">{unlock}</a>
      <span class="teaser-meta">{continue_}</span>
    </div>
  </article>
{trust}
  <p class="hint" style="margin-top:0.8rem;">{real_opening} <a href="{help_url}" style="color:var(--sub);">{payment_link}</a></p>
</section>

<section class="wrap narrow">
  <h2>{what_h}</h2>
  <p class="lede">{what}</p>
  <p class="lede" style="margin-bottom:0;">{description}</p>
</section>

<section class="wrap narrow">
  <h2>{keep_h}</h2>
  <p class="lede">{keep_lede}</p>
{share}
  <div class="cta-row" style="margin-top:1.6rem;">
    <a class="btn btn-ghost btn-sm" href="{send_url}" data-track="send_feeling_clicked" data-track-mood="{slug}" data-track-from="mood-page">{send_cta}</a>
  </div>
</section>

<section class="wrap">
  <h2>{more_h}</h2>
  <p class="lede">{more_lede}</p>
  <ul class="mood-grid">
{more}
  </ul>
  <div class="cta-row" style="margin-top:1.6rem;">
    <a class="btn btn-ghost" href="{moods_url}">{all_eight}</a>
    <a class="btn btn-ghost" href="{finder_url}">{not_sure}</a>
  </div>
</section>

{guide}<section class="wrap">
{bundle}
</section>
</main>""".format(
            name=e(m["name"]), tagline=e(m["tagline"]), slug=slug, price=m["price"],
            checkout=e(m["checkoutUrl"]),
            teaser_title=e(m["teaserTitle"]), teaser=e(m["teaser"]), tail=e(m["teaserTail"]),
            what=e(m["whatThisIs"]), description=e(m["description"]),
            c0=t["colors"][0], c1=t["colors"][1], c2=t["colors"][2], ink=t["ink"],
            light=" light" if t["light"] else "",
            moods_url=e("/moods/"), help_url=e("/help/payment/"),
            send_url=e("/send/?mood=%s" % slug), finder_url=e("/#finder"),
            crumb=e(EN.t("moodpage.crumb")),
            min_read=e(EN.t("moodpage.minRead", n=m["readingTime"])),
            word_count=e(EN.t("moodpage.words", n=m["words"])),
            no_account=e(EN.t("moodpage.noAccount")),
            free_look=e(EN.t("moodpage.freeLook", name=m["name"])),
            kicker=e(EN.t("moodpage.kicker", name=m["name"])),
            unlock=e(EN.t("moodpage.unlock", price=m["price"])),
            continue_=e(EN.t("moodpage.continue", n=m["readingTime"])),
            real_opening=e(EN.t("moodpage.realOpening")),
            payment_link=e(EN.t("moodpage.paymentLink")),
            what_h=e(EN.t("moodpage.whatH")), keep_h=e(EN.t("moodpage.keepH")),
            keep_lede=e(EN.t("moodpage.keepLede", name=m["name"])),
            send_cta=e(EN.t("moodpage.sendCta", name=m["name"])),
            more_h=e(EN.t("moodpage.moreH")), more_lede=e(EN.t("moodpage.moreLede")),
            all_eight=e(EN.t("moodpage.allEight")), not_sure=e(EN.t("moodpage.notSure")),
            trust=trust(), share=share_block(slug), more=more,
            bundle=bundle_block("mood-page"),
            guide=guide_block("mood-page", mood=slug),
        )

        meta = EN.page("mood")
        write(("mood/%s/index.html" % slug), page(
            path,
            title=meta["title"].format(name=m["name"], seoTitle=m["seoTitle"]),
            description=meta["description"].format(
                description=m["description"], mins=m["readingTime"], price=m["price"]),
            keywords=m.get("seoKeywords", ""),
            og_title=meta["ogTitle"].format(upper=m["name"].upper()),
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
    path = "/moods/"
    meta = EN.page("moods")
    itemlist = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": meta["ogTitle"],
        "inLanguage": EN.hreflang,
        "numberOfItems": len(MOODS),
        "itemListOrder": "https://schema.org/ItemListOrderAscending",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "url": ORIGIN + "/mood/%s/" % m["slug"],
                "name": m["name"],
            }
            for i, m in enumerate(EN.moods())
        ],
    }
    body = """<main id="main">
<header class="wrap" style="padding-top:clamp(2.5rem,8vw,4rem);">
  <p class="eyebrow">{eyebrow}</p>
  <h1>{h1}</h1>
  <p class="lede">{lede}</p>
  <div class="cta-row"><a class="btn btn-ghost btn-sm" href="{finder}">{not_sure}</a><a class="btn btn-ghost btn-sm" href="{free}">{free_l}</a></div>
</header>

<section class="wrap" style="padding-top:clamp(1.5rem,4vw,2.5rem);">
{grid}
</section>

{guide}<section class="wrap">
{bundle}
</section>
</main>""".format(eyebrow=e(EN.t("moodsidx.eyebrow")), h1=e(EN.t("moodsidx.h1")),
                  lede=e(EN.t("moodsidx.lede")), finder=e("/#finder"),
                  not_sure=e(EN.t("moodsidx.notSure")), free=e("/free/"),
                  free_l=e(EN.t("moodsidx.free")),
                  grid=mood_grid("moods-index"), bundle=bundle_block("moods-index"),
                  guide=guide_block("moods-index"))

    write(("moods/index.html"), page(
        path,
        title=meta["title"], description=meta["description"],
        og_title=meta["ogTitle"], og_desc=meta["ogDesc"],
        jsonld=(itemlist,), body=body, active="moods",
    ))


# --------------------------------------------------------------------------
# /shop/ — the digital products
# --------------------------------------------------------------------------

def build_shop():
    """Every product in content/moods.json `products`, then a pointer back
    to the $1-$5 pieces. A new product is one JSON entry and a rebuild."""
    path = "/shop/"
    title = "Shop — guides and downloads for how you feel | Moodshop"
    description = ("Longer guides and downloads from Moodshop, for the feelings that "
                   "stay. One payment, instant download, no account.")
    itemlist = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Moodshop shop",
        "numberOfItems": len(PRODUCTS),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "item": {
                    "@type": "Product",
                    "name": p["name"],
                    "description": p["blurb"],
                    "url": "%s/shop/#product-%s" % (ORIGIN, p["slug"]),
                    "brand": {"@type": "Brand", "name": SITE["name"]},
                    "offers": {
                        "@type": "Offer",
                        "url": p["checkoutUrl"],
                        "price": p["price"],
                        "priceCurrency": "USD",
                        "availability": "https://schema.org/InStock",
                    },
                },
            }
            for i, p in enumerate(PRODUCTS)
        ],
    }
    cards = "\n".join(product_card(p, "shop") for p in PRODUCTS)
    body = """<main id="main">
<header class="wrap" style="padding-top:clamp(2.5rem,8vw,4rem);">
  <p class="eyebrow">{eyebrow}</p>
  <h1>{h1}</h1>
  <p class="lede">{lede}</p>
</header>

<section class="wrap" style="padding-top:clamp(1.5rem,4vw,2.5rem);">
  <div class="shop-list">
{cards}
  </div>
</section>

<section class="wrap narrow">
  <h2>{small_h}</h2>
  <p class="lede">{small_lede}</p>
  <div class="cta-row"><a class="btn btn-ghost" href="{moods}" data-track="mood_selected" data-track-from="shop">{small_cta}</a></div>
</section>

<section class="wrap narrow">
  <h2>{soon_h}</h2>
  <p class="lede" style="margin-bottom:0;">{soon_lede} <a href="{free}" style="color:var(--ink);">{free_l}</a></p>
</section>
</main>""".format(eyebrow=e(EN.t("shop.eyebrow")), h1=e(EN.t("shop.h1")),
                  lede=e(EN.t("shop.lede")), cards=cards,
                  small_h=e(EN.t("shop.smallH")),
                  small_lede=e(EN.t("shop.smallLede", price=MIN_PRICE)),
                  small_cta=e(EN.t("shop.smallCta")), moods=e("/moods/"),
                  soon_h=e(EN.t("shop.soonH")), soon_lede=e(EN.t("shop.soonLede")),
                  free=e("/free/"), free_l=e(EN.t("foot.free")))

    write("shop/index.html", page(
        path, title=title, description=description,
        og_title="Moodshop — the shop", og_desc=description,
        jsonld=(itemlist,), body=body, active="shop",
    ))


# --------------------------------------------------------------------------
# /collections/
# --------------------------------------------------------------------------

def build_collections():
    path = "/collections/"
    meta = EN.page("collections")
    cards = "\n".join("""    <li class="collection-card" style="background:{card};color:{ink};">
      <span>
        <span class="name">{name}</span>
        <span class="tag">{tag}</span>
      </span>
      <p class="state">{state}</p>
    </li>""".format(card=c["theme"]["card"], ink=c["theme"]["cardInk"], name=e(c["name"]),
                    tag=e(c["tagline"]),
                    state=e(EN.t("coll.soon")) if c["status"] == "coming-soon" else e(c["status"]))
                     for c in EN.collections())

    body = """<main id="main">
<header class="wrap" style="padding-top:clamp(2.5rem,8vw,4rem);">
  <p class="eyebrow">{eyebrow}</p>
  <h1>{h1}</h1>
  <p class="lede">{lede}</p>
</header>

<section class="wrap" style="padding-top:clamp(1.5rem,4vw,2.5rem);">
  <ul class="cards reveal">
{cards}
  </ul>
  <p class="hint" style="margin-top:1.6rem;">{hint}</p>
</section>

<section class="wrap">
  <h2>{open_h}</h2>
  <p class="lede">{open_lede}</p>
{grid}
</section>

<section class="wrap">
{bundle}
</section>
</main>""".format(cards=cards, grid=mood_grid("collections"),
                  bundle=bundle_block("collections"),
                  eyebrow=e(EN.t("coll.eyebrow")), h1=e(EN.t("coll.h1")),
                  lede=e(EN.t("coll.lede")), hint=e(EN.t("coll.hint")),
                  open_h=e(EN.t("coll.openH")),
                  open_lede=e(EN.t("coll.openLede", price=MIN_PRICE)))

    write(("collections/index.html"), page(
        path,
        title=meta["title"], description=meta["description"],
        og_title=meta["ogTitle"], og_desc=meta["ogDesc"],
        body=body, active="collections",
    ))


# --------------------------------------------------------------------------
# hand-written pages (body lives in templates/)
# --------------------------------------------------------------------------

# Every price a template string can mention. Currency placement is part of
# the translation, so the catalogue writes "$" or "USD" where its language
# wants it and only the number comes from here.
MONEY = {
    "price": MIN_PRICE,
    "min": MIN_PRICE,
    "max": MAX_PRICE,
    "total": INDIVIDUAL_TOTAL,
    "saving": INDIVIDUAL_TOTAL - BUNDLE["price"],
}

TPL_T = re.compile(r"\{\{t:([a-zA-Z0-9_.]+)\}\}")
TPL_U = re.compile(r"\{\{u:([^}]+)\}\}")


def template(name, **subs):
    """A hand-written body. `{{t:key}}` becomes the (escaped) string."""
    raw = open(os.path.join(ROOT, "templates", name), encoding="utf-8").read()
    raw = TPL_T.sub(lambda mo: e(EN.t(mo.group(1), **MONEY)), raw)
    raw = TPL_U.sub(lambda mo: e(mo.group(1)), raw)
    for k, v in subs.items():
        raw = raw.replace("{{%s}}" % k, str(v))
    return raw


def build_static_pages():
    # ---- homepage ----
    faq = [(f["q"], f["a"]) for f in EN.faq()]
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
        "inLanguage": EN.hreflang,
        "description": EN.site("promise"),
        "publisher": {"@type": "Person", "name": SITE["author"]},
    }
    itemlist_ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": EN.page("moods")["ogTitle"],
        "inLanguage": EN.hreflang,
        "numberOfItems": len(MOODS),
        "itemListOrder": "https://schema.org/ItemListOrderAscending",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "item": {
                    "@type": "Product",
                    "@id": ORIGIN + "/mood/%s/" % m["slug"] + "#product",
                    "name": m["name"],
                    "description": m["description"],
                    "image": "%s/img/og/%s.jpg" % (ORIGIN, m["slug"]),
                    "url": ORIGIN + "/mood/%s/" % m["slug"],
                    "sku": "moodshop-" + m["slug"],
                    "inLanguage": EN.hreflang,
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
            for i, m in enumerate(EN.moods())
        ],
    }

    def meta_of(name):
        m = EN.page(name)
        return dict(title=m["title"], description=m["description"],
                    og_title=m["ogTitle"], og_desc=m["ogDesc"])

    write(("index.html"), page(
        "/",
        jsonld=(website_ld, itemlist_ld, faq_ld),
        body=template("home.html",
                      GRID=mood_grid("home"), BUNDLE=bundle_block("home"),
                      GUIDE=guide_block("home"),
                      FAQ=faq_html, TRUST=trust(),
                      TODAY_NAME=e(EN.mood(MOODS[0])["name"])),
        **meta_of("home")
    ))

    # ---- about ----
    write(("about/index.html"), page(
        "/about/",
        body=template("about.html"),
        active="about", **meta_of("about")
    ))

    # ---- send ----
    write(("send/index.html"), page(
        "/send/",
        body=template("send.html"),
        **meta_of("send")
    ))

    # ---- for (the receiving end) ----
    write(("for/index.html"), page(
        "/for/",
        robots="noindex, follow",
        body=template("for.html"), **meta_of("for")
    ))

    # ---- payment help ----
    write(("help/payment/index.html"), page(
        "/help/payment/",
        robots="noindex, follow",
        body=template("payment-help.html"), **meta_of("help")
    ))

    # ---- 404 ----
    write(("404.html"), page(
        "/404.html",
        robots="noindex, nofollow", ads=False,
        body=template("404.html", GRID=mood_grid("404")), **meta_of("404")
    ))


# --------------------------------------------------------------------------
# sitemap + robots
# --------------------------------------------------------------------------

def build_sitemap():
    """One entry per URL."""
    SHELF = "content/moods.json"
    TOOLS_SRC = ("content/tool-content.json", "content/feelings.json",
                 "content/wheel.json", "scripts/tools_pages.py")

    # (path, changefreq, priority, sources whose last change dates the page)
    paths = [
        ("/", "weekly", "1.0", (SHELF, "templates/home.html")),
        ("/moods/", "weekly", "0.9", (SHELF,)),
        ("/shop/", "weekly", "0.9", (SHELF,)),
        ("/collections/", "monthly", "0.6", (SHELF,)),
        ("/about/", "monthly", "0.5", ("templates/about.html",)),
        ("/send/", "monthly", "0.6", ("templates/send.html",)),
        ("/tools/", "weekly", "0.9", TOOLS_SRC),
        ("/today/", "daily", "0.7", (SHELF,) + TOOLS_SRC),
        ("/free/", "monthly", "0.8", ("free/index.html",)),
        ("/free/cant-sleep.html", "yearly", "0.7", ("free/cant-sleep.html",)),
        ("/free/waiting-for-news.html", "yearly", "0.7", ("free/waiting-for-news.html",)),
        ("/free/the-strong-one.html", "yearly", "0.7", ("free/the-strong-one.html",)),
    ]
    paths += [("/mood/%s/" % m["slug"], "monthly", "0.9", (SHELF,)) for m in MOODS]
    paths += [("/tools/%s/" % t["slug"], "monthly", "0.8", TOOLS_SRC)
              for t in tools_pages.TOOLS]

    entries = []
    undated = []
    for path, cf, pr, sources in paths:
        loc = ORIGIN + path
        changed = source_date(*(sources + ("content/strings.json",)))
        lastmod = "\n    <lastmod>%s</lastmod>" % changed if changed else ""
        if not changed:
            undated.append(loc)
        entries.append(
            "  <url>\n    <loc>%s</loc>%s"
            "\n    <changefreq>%s</changefreq>\n    <priority>%s</priority>\n  </url>"
            % (loc, lastmod, cf, pr)
        )

    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n'
          % "\n".join(entries))

    if undated:
        graft = _boundary()[1]
        print("! %d of %d sitemap URLs have no <lastmod>: shallow clone "
              "grafted at %s, so when their sources really changed is not in "
              "the history (run: git fetch --unshallow)"
              % (len(undated), len(entries), graft))

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

    # The tools are English-only for now: one URL each, no hreflang set,
    # and the language picker on a translated page links straight to them.
    def en_page(*, canonical, **kw):
        path = canonical[len(ORIGIN):] or "/"
        return page(path, **kw)

    tools_pages.build({
        "origin": ORIGIN,
        "author": SITE["author"],
        "page": en_page,
        "write": write,
        "mood_card": lambda m, *, track_from: mood_card(m, track_from=track_from),
        "bundle_block": lambda track_from: bundle_block(track_from),
        "mood": lambda s: by_slug[s],
        "min_price": MIN_PRICE,
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
    build_shop()
    build_tool_pages()
    build_sitemap()
    build_og_images()
    print("\ndone — %d moods in English, individual total $%d, pack $%d"
          % (len(MOODS), INDIVIDUAL_TOTAL, BUNDLE["price"]))


if __name__ == "__main__":
    main()
