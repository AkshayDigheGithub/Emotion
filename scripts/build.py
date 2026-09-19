#!/usr/bin/env python3
"""Build every public Moodshop page from content/moods.json.

Moodshop has no framework and no build step on the host — Vercel serves this
repo as plain files. This script is the "framework": it runs on a laptop, and
what it writes is committed. Adding a 50th mood means adding a 50th entry to
content/moods.json and running:

    python3 scripts/build.py

Every page is generated once per language (see scripts/i18n.py):
English at the root, the other nine under /<code>/.

Generated (do not hand-edit — your edits are overwritten):
    [<lang>/]moods-data.js         the same data, for the client
    [<lang>/]mood/<slug>/index.html  one sales + SEO page per feeling
    [<lang>/]moods/index.html      every feeling
    [<lang>/]collections/index.html  themed collections
    [<lang>/]about|send|for|help/payment/index.html, 404.html, index.html
    tools/…, today/            English only, for now
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

import i18n
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
MIN_PRICE = min(m["price"] for m in MOODS)
MAX_PRICE = max(m["price"] for m in MOODS)

# Ten languages. English is the source and the x-default; the other nine
# live under /<code>/ and are generated from content/i18n/<code>.json.
LANGS = i18n.load(MOODS, COLLECTIONS, DATA.get("writingNow", []))
EN = LANGS[0]


def e(s):
    return html.escape(str(s), quote=True)


def write(relpath, text):
    path = os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote", relpath)


def out(lang, relpath):
    """Where a page for this language goes on disk: English at the root,
    everything else under its own directory."""
    return relpath if lang.is_default else "%s/%s" % (lang.code, relpath)


# --------------------------------------------------------------------------
# shell
# --------------------------------------------------------------------------

NAV_ITEMS = [
    ("/moods/", "nav.moods", "moods"),
    ("/tools/", "nav.tools", "tools"),
    ("/collections/", "nav.collections", "collections"),
    ("/today/", "nav.today", "today"),
    ("/about/", "nav.about", "about"),
]


def lang_menu(lang, path, *, inline=False):
    """The language picker.

    `path` is the logical (English) path of the page being rendered, so
    every entry points at the same page in its own language. A page that
    exists only in English links to the English URL — see i18n.u().
    """
    # On an English-only page (the tools, /today/) every entry would
    # otherwise point back at this same URL, so send the reader to that
    # language's home instead of to ten copies of one link.
    target = path if i18n.is_localized(path) else "/"
    items = []
    for other in LANGS:
        cur = ' aria-current="true"' if other.code == lang.code else ""
        items.append(
            '      <li><a href="%s" hreflang="%s" lang="%s" dir="%s"%s>%s</a></li>'
            % (e(other.u(target)), other.hreflang, other.hreflang, other.dir, cur, e(other.name))
        )
    body = """  <p class="lang-label">%s</p>
  <ul class="lang-grid">
%s
  </ul>""" % (e(lang.t("shell.langLabel")), "\n".join(items))

    if inline:
        return ('<section class="wrap lang-pick" aria-label="%s">\n%s\n  <p class="hint">%s</p>\n</section>'
                % (e(lang.t("shell.langAria")), body, e(lang.t("shell.langNote"))))

    return """<details class="langbox">
  <summary aria-label="%s"><span class="globe" aria-hidden="true">🌐</span> <span>%s</span></summary>
  <div class="langmenu">
%s
  </div>
</details>""" % (e(lang.t("shell.langAria")), e(lang.name), body)


def nav(lang, path, active=""):
    links = []
    for href, key, active_key in NAV_ITEMS:
        cur = ' aria-current="page"' if active_key == active else ""
        links.append('      <li><a href="%s"%s>%s</a></li>'
                     % (e(lang.u(href)), cur, e(lang.t(key))))
    return """<nav class="nav" aria-label="{aria}">
  <div class="nav-in">
    <a class="brand" href="{home}"><span class="dot" aria-hidden="true"></span> Moodshop</a>
    <ul class="nav-links">
{links}
    </ul>
    <div class="nav-end">
{lang}
      <a class="nav-cta" href="{finder}" data-track="mood_finder_started" data-track-from="nav">{cta}</a>
    </div>
  </div>
</nav>""".format(aria=e(lang.t("nav.aria")), home=e(lang.u("/")), links="\n".join(links),
                 lang=lang_menu(lang, path), finder=e(lang.u("/tools/mood-finder/")),
                 cta=e(lang.t("nav.cta")))


def footer(lang):
    mood_links = "\n".join(
        '        <li><a href="%s">%s</a></li>' % (e(lang.u("/mood/%s/" % m["slug"])), e(m["name"]))
        for m in lang.moods()[:4]
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
          <li><a href="https://www.buymeacoffee.com/digheakshaf" rel="nofollow noopener">{contact}</a></li>
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
        feelings=e(lang.t("foot.feelings")), mood_links=mood_links,
        moods=e(lang.u("/moods/")), all_eight=e(lang.t("foot.allEight")),
        shop=e(lang.t("foot.shop")),
        about=e(lang.u("/about/")), about_l=e(lang.t("foot.about")),
        collections=e(lang.u("/collections/")), collections_l=e(lang.t("foot.collections")),
        tools=e(lang.u("/tools/")), tools_l=e(lang.t("foot.tools")),
        today=e(lang.u("/today/")), today_l=e(lang.t("foot.today")),
        send=e(lang.u("/send/")), send_l=e(lang.t("foot.send")),
        free=e(lang.u("/free/")), free_l=e(lang.t("foot.free")),
        payhelp=e(lang.t("foot.payHelp")),
        help=e(lang.u("/help/payment/")), help_l=e(lang.t("foot.paymentDidnt")),
        contact=e(lang.t("foot.contact")),
        terms=e(lang.u("/about/#terms")), terms_l=e(lang.t("foot.terms")),
        privacy=e(lang.u("/about/#privacy")), privacy_l=e(lang.t("foot.privacy")),
        tagline=e(lang.site("tagline")), payments=e(lang.t("foot.payments")),
    )


# `extra_head` is emitted last: deferred scripts execute in document
# order, and a page-specific script always builds on the shared ones.
def head(lang, path, title, description, *, og_title=None, og_desc=None, og_image=None,
         og_type="website", robots="index, follow", extra_head="", jsonld=(), theme="#0e0e15",
         keywords=""):
    """The <head>.

    The canonical is always this language's own URL for `path` — a
    Spanish page points at itself, not at the English one, and the
    rel=alternate set below tells a crawler about the other nine. A page
    that exists in one language only gets no alternates at all.
    """
    canonical = lang.abs_u(ORIGIN, path)
    og_image = og_image or (ORIGIN + "/og-image.jpg")
    blocks = "\n".join(
        '<script type="application/ld+json">\n%s\n</script>' % json.dumps(b, indent=2, ensure_ascii=False)
        for b in jsonld
    )
    alts = "\n".join(
        '<link rel="alternate" hreflang="%s" href="%s">' % (code, e(href))
        for code, href in i18n.alternates(ORIGIN, path)
    )
    og_alts = "\n".join(
        '<meta property="og:locale:alternate" content="%s">' % other.locale
        for other in LANGS if other.code != lang.code
    ) if i18n.is_localized(path) else ""

    return """<!DOCTYPE html>
<html lang="{htmllang}" dir="{dir}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
{alts}
<meta name="robots" content="{robots}">
<meta name="theme-color" content="{theme}">
{keywords}
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{og_desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="Moodshop">
<meta property="og:locale" content="{locale}">
{og_alts}
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
{extra_head}
</head>""".format(
        htmllang=lang.hreflang, dir=lang.dir,
        title=e(title), description=e(description), canonical=e(canonical), robots=robots,
        alts=alts, og_alts=og_alts, locale=lang.locale,
        keywords=('<meta name="keywords" content="%s">\n' % e(keywords)) if keywords else "",
        theme=theme, og_type=og_type, og_title=e(og_title or title), og_desc=e(og_desc or description),
        og_image=e(og_image), favicon=FAVICON, fonts=FONTS,
        data_js=(lang.prefix + "/moods-data.js") or "/moods-data.js",
        extra_head=extra_head, blocks=blocks,
    )


def page(lang, path, *, title, description, body, active="", body_attrs="", **kw):
    return ("%s\n<body%s>\n<script>document.documentElement.className+=' js';</script>\n"
            "<a class=\"skip\" href=\"#main\">%s</a>\n<div class=\"aura\" aria-hidden=\"true\"></div>\n"
            "%s\n%s\n%s\n</body>\n</html>\n") % (
        head(lang, path, title, description, **kw), body_attrs, e(lang.t("shell.skip")),
        nav(lang, path, active), body, footer(lang)
    )


# --------------------------------------------------------------------------
# reusable body chunks
# --------------------------------------------------------------------------

def mood_card(lang, m, *, track_from):
    m = lang.mood(m)
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
    </li>""".format(href=e(lang.u("/mood/%s/" % m["slug"])), slug=m["slug"], card=t["card"],
                    ink=t["cardInk"], name=e(m["name"]), tagline=e(m["tagline"]),
                    price=m["price"], src=track_from, enter=e(lang.t("card.enter")))


def mood_grid(lang, track_from):
    cards = "\n".join(mood_card(lang, m, track_from=track_from) for m in MOODS)
    soon = ""
    for w in lang.writing_now():
        soon += """
    <li>
      <div class="mood-card soon">
        <span>
          <span class="name">%s</span>
          <span class="tag">%s</span>
        </span>
        <span class="foot"><span class="go">%s</span></span>
      </div>
    </li>""" % (e(w["name"]), e(w["tagline"]), e(lang.t("card.soon")))
    return '  <ul class="mood-grid reveal">\n%s%s\n  </ul>' % (cards, soon)


def bundle_block(lang, track_from):
    """The pack. Renders a real checkout button only once a Buy Me a Coffee
    Extra exists for it — until then it is a price anchor that points at the
    shelf, never a button that would take money and deliver nothing."""
    saving = INDIVIDUAL_TOTAL - BUNDLE["price"]
    b = lang.bundle(BUNDLE)
    if BUNDLE.get("checkoutUrl"):
        cta = ('<a class="btn btn-primary" href="%s" rel="nofollow noopener" '
               'data-track="bundle_clicked" data-track-from="%s">%s</a>'
               % (e(BUNDLE["checkoutUrl"]), track_from,
                  e(lang.t("bundle.cta", price=BUNDLE["price"]))))
        badge = '<span class="badge hot">%s</span>' % e(lang.t("bundle.badgeBest"))
        note = '<p class="hint">%s</p>' % e(lang.t("bundle.note"))
    else:
        cta = ('<a class="btn btn-ghost" href="%s" data-track="bundle_clicked" '
               'data-track-from="%s">%s</a>'
               % (e(lang.u("/moods/")), track_from, e(lang.t("bundle.ctaSoon", price=MIN_PRICE))))
        badge = '<span class="badge">%s</span>' % e(lang.t("bundle.badgeSoon"))
        note = '<p class="hint">%s</p>' % e(lang.t("bundle.noteSoon", price=BUNDLE["price"]))
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
                   price=BUNDLE["price"], once=e(lang.t("bundle.once")),
                   was=lang.t("bundle.was", total=INDIVIDUAL_TOTAL, saving=saving),
                   tick1=e(lang.t("bundle.tick1")), tick2=e(lang.t("bundle.tick2")),
                   tick3=e(lang.t("bundle.tick3")), tick4=e(lang.t("bundle.tick4")),
                   cta=cta, note=note)


def share_block(lang, slug):
    return """  <div class="share-row-wrap" data-share="{slug}">
    <ul class="share-row">
      <li><button type="button" data-share-to="native">{native}</button></li>
      <li><button type="button" data-share-to="copy">{copy}</button></li>
      <li><a data-share-to="x" href="#">{x}</a></li>
      <li><a data-share-to="whatsapp" href="#">{wa}</a></li>
      <li><button type="button" data-share-to="image">{img}</button></li>
    </ul>
    <p class="share-status" aria-live="polite"></p>
  </div>""".format(slug=slug, native=e(lang.t("share.native")), copy=e(lang.t("share.copy")),
                   x=e(lang.t("share.x")), wa=e(lang.t("share.whatsapp")),
                   img=e(lang.t("share.image")))


def trust(lang):
    return '  <ul class="trust">\n%s\n  </ul>' % "\n".join(
        "    <li>%s</li>" % e(lang.t("trust.%d" % i)) for i in (1, 2, 3, 4)
    )


# --------------------------------------------------------------------------
# moods-data.js
# --------------------------------------------------------------------------

def build_data_js(lang):
    """One data file per language.

    Same shape in every language, so moodshop.js stays one file: the
    moods carry this language's text, `base` is the prefix its links
    need, and `i18n` holds the strings the script writes into the DOM.
    """
    payload = {
        "site": SITE,
        "lang": lang.code,
        "dir": lang.dir,
        "base": lang.prefix,
        "bundle": {k: v for k, v in lang.bundle(BUNDLE).items() if k != "comment"},
        "moods": [
            {k: m[k] for k in ("slug", "name", "tagline", "teaserTitle", "teaser", "teaserTail",
                               "shareLine", "words", "readingTime", "price", "checkoutUrl", "theme")}
            for m in lang.moods()
        ],
        "collections": lang.collections(),
        "finder": lang.finder(DATA["finder"]),
        "testimonials": DATA["testimonials"],
        "i18n": lang.js(),
    }
    write(("%s/moods-data.js" % lang.prefix).lstrip("/") if lang.prefix else "moods-data.js",
          "/* Generated by scripts/build.py from content/moods.json + content/i18n/%s.json. "
          "Do not edit. */\n"
          "window.MOODSHOP=%s;\n" % (lang.code, json.dumps(payload, separators=(",", ":"),
                                                           ensure_ascii=False)))


# --------------------------------------------------------------------------
# /mood/<slug>/
# --------------------------------------------------------------------------

def build_mood_pages(lang):
    for base in MOODS:
        m = lang.mood(base)
        slug, t = m["slug"], m["theme"]
        path = "/mood/%s/" % slug
        url = lang.abs_u(ORIGIN, path)
        product = {
            "@context": "https://schema.org",
            "@type": "Product",
            "@id": url + "#product",
            "name": "%s — Moodshop" % m["name"],
            "description": m["description"],
            "image": "%s/img/og/%s.jpg" % (ORIGIN, slug),
            "url": url,
            "sku": "moodshop-" + slug,
            "inLanguage": lang.hreflang,
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
                 "item": lang.abs_u(ORIGIN, "/")},
                {"@type": "ListItem", "position": 2, "name": lang.t("moodpage.crumb"),
                 "item": lang.abs_u(ORIGIN, "/moods/")},
                {"@type": "ListItem", "position": 3, "name": m["name"], "item": url},
            ],
        }

        others = [x for x in MOODS if x["slug"] != slug][:3]
        more = "\n".join(mood_card(lang, x, track_from="mood-page") for x in others)

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

<section class="wrap">
{bundle}
</section>

{langpick}

</main>""".format(
            name=e(m["name"]), tagline=e(m["tagline"]), slug=slug, price=m["price"],
            checkout=e(m["checkoutUrl"]),
            teaser_title=e(m["teaserTitle"]), teaser=e(m["teaser"]), tail=e(m["teaserTail"]),
            what=e(m["whatThisIs"]), description=e(m["description"]),
            c0=t["colors"][0], c1=t["colors"][1], c2=t["colors"][2], ink=t["ink"],
            light=" light" if t["light"] else "",
            moods_url=e(lang.u("/moods/")), help_url=e(lang.u("/help/payment/")),
            send_url=e(lang.u("/send/?mood=%s" % slug)), finder_url=e(lang.u("/#finder")),
            crumb=e(lang.t("moodpage.crumb")),
            min_read=e(lang.t("moodpage.minRead", n=m["readingTime"])),
            word_count=e(lang.t("moodpage.words", n=m["words"])),
            no_account=e(lang.t("moodpage.noAccount")),
            free_look=e(lang.t("moodpage.freeLook", name=m["name"])),
            kicker=e(lang.t("moodpage.kicker", name=m["name"])),
            unlock=e(lang.t("moodpage.unlock", price=m["price"])),
            continue_=e(lang.t("moodpage.continue", n=m["readingTime"])),
            real_opening=e(lang.t("moodpage.realOpening")),
            payment_link=e(lang.t("moodpage.paymentLink")),
            what_h=e(lang.t("moodpage.whatH")), keep_h=e(lang.t("moodpage.keepH")),
            keep_lede=e(lang.t("moodpage.keepLede", name=m["name"])),
            send_cta=e(lang.t("moodpage.sendCta", name=m["name"])),
            more_h=e(lang.t("moodpage.moreH")), more_lede=e(lang.t("moodpage.moreLede")),
            all_eight=e(lang.t("moodpage.allEight")), not_sure=e(lang.t("moodpage.notSure")),
            trust=trust(lang), share=share_block(lang, slug), more=more,
            bundle=bundle_block(lang, "mood-page"),
            langpick=lang_menu(lang, path, inline=True),
        )

        meta = lang.page("mood")
        write(out(lang, "mood/%s/index.html" % slug), page(
            lang, path,
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

def build_moods_index(lang):
    path = "/moods/"
    meta = lang.page("moods")
    itemlist = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": meta["ogTitle"],
        "inLanguage": lang.hreflang,
        "numberOfItems": len(MOODS),
        "itemListOrder": "https://schema.org/ItemListOrderAscending",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "url": lang.abs_u(ORIGIN, "/mood/%s/" % m["slug"]),
                "name": m["name"],
            }
            for i, m in enumerate(lang.moods())
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

<section class="wrap">
{bundle}
</section>

{langpick}
</main>""".format(eyebrow=e(lang.t("moodsidx.eyebrow")), h1=e(lang.t("moodsidx.h1")),
                  lede=e(lang.t("moodsidx.lede")), finder=e(lang.u("/#finder")),
                  not_sure=e(lang.t("moodsidx.notSure")), free=e(lang.u("/free/")),
                  free_l=e(lang.t("moodsidx.free")),
                  grid=mood_grid(lang, "moods-index"), bundle=bundle_block(lang, "moods-index"),
                  langpick=lang_menu(lang, path, inline=True))

    write(out(lang, "moods/index.html"), page(
        lang, path,
        title=meta["title"], description=meta["description"],
        og_title=meta["ogTitle"], og_desc=meta["ogDesc"],
        jsonld=(itemlist,), body=body, active="moods",
    ))


# --------------------------------------------------------------------------
# /collections/
# --------------------------------------------------------------------------

def build_collections(lang):
    path = "/collections/"
    meta = lang.page("collections")
    cards = "\n".join("""    <li class="collection-card" style="background:{card};color:{ink};">
      <span>
        <span class="name">{name}</span>
        <span class="tag">{tag}</span>
      </span>
      <p class="state">{state}</p>
    </li>""".format(card=c["theme"]["card"], ink=c["theme"]["cardInk"], name=e(c["name"]),
                    tag=e(c["tagline"]),
                    state=e(lang.t("coll.soon")) if c["status"] == "coming-soon" else e(c["status"]))
                     for c in lang.collections())

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

{langpick}
</main>""".format(cards=cards, grid=mood_grid(lang, "collections"),
                  bundle=bundle_block(lang, "collections"),
                  eyebrow=e(lang.t("coll.eyebrow")), h1=e(lang.t("coll.h1")),
                  lede=e(lang.t("coll.lede")), hint=e(lang.t("coll.hint")),
                  open_h=e(lang.t("coll.openH")),
                  open_lede=e(lang.t("coll.openLede", price=MIN_PRICE)),
                  langpick=lang_menu(lang, path, inline=True))

    write(out(lang, "collections/index.html"), page(
        lang, path,
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


def template(lang, name, **subs):
    """A hand-written body, localised.

    `{{t:key}}` becomes the (escaped) string for this language and
    `{{u:/path/}}` becomes the path this language serves — so one
    template file is the source for all ten copies of the page.
    """
    raw = open(os.path.join(ROOT, "templates", name), encoding="utf-8").read()
    raw = TPL_T.sub(lambda mo: e(lang.t(mo.group(1), **MONEY)), raw)
    raw = TPL_U.sub(lambda mo: e(lang.u(mo.group(1))), raw)
    for k, v in subs.items():
        raw = raw.replace("{{%s}}" % k, str(v))
    return raw


def build_static_pages(lang):
    # ---- homepage ----
    faq = [(f["q"], f["a"]) for f in lang.faq()]
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
        "url": lang.abs_u(ORIGIN, "/"),
        "inLanguage": lang.hreflang,
        "description": lang.site("promise"),
        "publisher": {"@type": "Person", "name": SITE["author"]},
    }
    itemlist_ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": lang.page("moods")["ogTitle"],
        "inLanguage": lang.hreflang,
        "numberOfItems": len(MOODS),
        "itemListOrder": "https://schema.org/ItemListOrderAscending",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "item": {
                    "@type": "Product",
                    "@id": lang.abs_u(ORIGIN, "/mood/%s/" % m["slug"]) + "#product",
                    "name": m["name"],
                    "description": m["description"],
                    "image": "%s/img/og/%s.jpg" % (ORIGIN, m["slug"]),
                    "url": lang.abs_u(ORIGIN, "/mood/%s/" % m["slug"]),
                    "sku": "moodshop-" + m["slug"],
                    "inLanguage": lang.hreflang,
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
            for i, m in enumerate(lang.moods())
        ],
    }

    def meta_of(name):
        m = lang.page(name)
        return dict(title=m["title"], description=m["description"],
                    og_title=m["ogTitle"], og_desc=m["ogDesc"])

    write(out(lang, "index.html"), page(
        lang, "/",
        jsonld=(website_ld, itemlist_ld, faq_ld),
        body=template(lang, "home.html",
                      GRID=mood_grid(lang, "home"), BUNDLE=bundle_block(lang, "home"),
                      FAQ=faq_html, TRUST=trust(lang),
                      TODAY_NAME=e(lang.mood(MOODS[0])["name"]),
                      LANGPICK=lang_menu(lang, "/", inline=True)),
        **meta_of("home")
    ))

    # ---- about ----
    write(out(lang, "about/index.html"), page(
        lang, "/about/",
        body=template(lang, "about.html", LANGPICK=lang_menu(lang, "/about/", inline=True)),
        active="about", **meta_of("about")
    ))

    # ---- send ----
    write(out(lang, "send/index.html"), page(
        lang, "/send/",
        body=template(lang, "send.html", LANGPICK=lang_menu(lang, "/send/", inline=True)),
        **meta_of("send")
    ))

    # ---- for (the receiving end) ----
    write(out(lang, "for/index.html"), page(
        lang, "/for/",
        robots="noindex, follow",
        body=template(lang, "for.html"), **meta_of("for")
    ))

    # ---- payment help ----
    write(out(lang, "help/payment/index.html"), page(
        lang, "/help/payment/",
        robots="noindex, follow",
        body=template(lang, "payment-help.html"), **meta_of("help")
    ))

    # ---- 404 ----
    write(out(lang, "404.html"), page(
        lang, "/404.html",
        robots="noindex, nofollow",
        body=template(lang, "404.html", GRID=mood_grid(lang, "404")), **meta_of("404")
    ))


# --------------------------------------------------------------------------
# sitemap + robots
# --------------------------------------------------------------------------

def build_sitemap():
    """One entry per URL, and for a translated page every language's copy
    carries the full xhtml:link set — that is what tells a crawler the ten
    URLs are one page in ten languages rather than ten thin duplicates."""
    paths = [
        ("/", "weekly", "1.0"),
        ("/moods/", "weekly", "0.9"),
        ("/collections/", "monthly", "0.6"),
        ("/about/", "monthly", "0.5"),
        ("/send/", "monthly", "0.6"),
        ("/tools/", "weekly", "0.9"),
        ("/today/", "daily", "0.7"),
        ("/free/", "monthly", "0.8"),
        ("/free/cant-sleep.html", "yearly", "0.7"),
        ("/free/waiting-for-news.html", "yearly", "0.7"),
        ("/free/the-strong-one.html", "yearly", "0.7"),
    ]
    paths += [("/mood/%s/" % m["slug"], "monthly", "0.9") for m in MOODS]
    paths += [("/tools/%s/" % t["slug"], "monthly", "0.8") for t in tools_pages.TOOLS]

    entries = []
    for path, cf, pr in paths:
        alts = i18n.alternates(ORIGIN, path)
        links = "".join(
            '\n    <xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (code, e(href))
            for code, href in alts
        )
        for lang in (LANGS if alts else [EN]):
            entries.append(
                "  <url>\n    <loc>%s</loc>%s\n    <changefreq>%s</changefreq>"
                "\n    <priority>%s</priority>\n  </url>"
                % (lang.abs_u(ORIGIN, path), links, cf, pr)
            )

    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
          '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n%s\n</urlset>\n'
          % "\n".join(entries))

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
        return page(EN, path, **kw)

    tools_pages.build({
        "origin": ORIGIN,
        "author": SITE["author"],
        "page": en_page,
        "write": write,
        "mood_card": lambda m, *, track_from: mood_card(EN, m, track_from=track_from),
        "bundle_block": lambda track_from: bundle_block(EN, track_from),
        "mood": lambda s: by_slug[s],
        "min_price": MIN_PRICE,
        "feelings": FEELINGS_DATA,
        "wheel": WHEEL_DATA,
        "tool_content": TOOL_CONTENT,
        "product_of": lambda s: feel_by_slug[s]["product"],
        "feeling_name": lambda s: feel_by_slug[s]["name"],
    })


def main():
    for lang in LANGS:
        build_data_js(lang)
        build_mood_pages(lang)
        build_moods_index(lang)
        build_collections(lang)
        build_static_pages(lang)
    build_tool_pages()
    build_sitemap()
    build_og_images()
    print("\ndone — %d moods in %d languages (%s), individual total $%d, pack $%d"
          % (len(MOODS), len(LANGS), ", ".join(l.code for l in LANGS),
             INDIVIDUAL_TOTAL, BUNDLE["price"]))


if __name__ == "__main__":
    main()
