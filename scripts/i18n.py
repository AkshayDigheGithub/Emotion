#!/usr/bin/env python3
"""Languages for Moodshop.

One catalogue per language in content/i18n/<code>.json. English is the
source of truth and the fallback: any key a translation hasn't got yet
falls back to en.json rather than disappearing from the page, so a
half-finished language still renders a whole site.

URL shape — English lives at the root, every other language under its own
prefix:

    /mood/calm/          en  (also the x-default)
    /es/mood/calm/       es
    /ar/mood/calm/       ar  (rtl)

Only the pages listed in LOCALIZED are translated. Everything else (the
tools, /today/, the free reader pages, the paid reader pages) is written
in English and stays at one URL — a link to one of those from a
translated page points at the English original instead of inventing a
translated URL that would 404. `u()` is the single place that decides.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
I18N_DIR = os.path.join(ROOT, "content", "i18n")

# Display order of the language picker — the order in the design.
ORDER = ["en", "de", "es", "fr", "pt", "hi", "zh", "ja", "ru", "ar"]

DEFAULT = "en"

# Paths that exist in every language. A path not in here (and not a mood
# page) keeps its single English URL.
LOCALIZED = {
    "/",
    "/moods/",
    "/collections/",
    "/about/",
    "/send/",
    "/for/",
    "/help/payment/",
    "/404.html",
}

MOOD_PATH = re.compile(r"^/mood/[a-z0-9-]+/$")

# Text fields of a mood that a translation may override. Everything else
# (price, theme, checkout URL, slug) is language-independent.
MOOD_TEXT = ("name", "tagline", "description", "whatThisIs", "teaserTitle",
             "teaser", "teaserTail", "shareLine", "seoTitle", "seoKeywords")


def _read(code):
    with open(os.path.join(I18N_DIR, code + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


_CATALOGS = {code: _read(code) for code in ORDER}
_EN = _CATALOGS[DEFAULT]


class _Keep(dict):
    """format_map() mapping that leaves an unknown {placeholder} alone."""

    def __missing__(self, key):
        return "{%s}" % key


def is_localized(path):
    return path in LOCALIZED or bool(MOOD_PATH.match(path))


class Lang(object):
    """One language: its strings, its URLs, its <html> attributes."""

    def __init__(self, code, moods, collections, writing_now):
        self.code = code
        self.data = _CATALOGS[code]
        meta = self.data["meta"]
        self.name = meta["name"]           # native name, for the picker
        self.english = meta["english"]     # English name, for alt text
        self.hreflang = meta["hreflang"]   # may differ from the code (zh-Hans)
        self.locale = meta["locale"]       # og:locale
        self.dir = meta.get("dir", "ltr")
        self.rtl = self.dir == "rtl"
        self.is_default = code == DEFAULT
        self.prefix = "" if self.is_default else "/" + code
        self._moods = moods
        self._collections = collections
        self._writing_now = writing_now

    # ---- strings ----------------------------------------------------

    def t(self, key, **fmt):
        """A UI string, formatted. Falls back to English, then to the key.

        A placeholder nobody passed a value for is left as it was rather
        than raising: a translation that mentions {price} where English
        doesn't should not take the build down.
        """
        s = self.data.get("ui", {}).get(key)
        if s is None:
            s = _EN["ui"].get(key, key)
        if "{" not in s:
            return s
        try:
            return s.format_map(_Keep(fmt))
        except (IndexError, ValueError):
            return s

    def js(self):
        """The client-side strings, English-filled."""
        out = dict(_EN["js"])
        out.update(self.data.get("js", {}))
        return out

    def page(self, name):
        """{title, description, ogTitle, ogDesc} for a page, English-filled."""
        out = dict(_EN["pages"].get(name, {}))
        out.update(self.data.get("pages", {}).get(name, {}))
        return out

    def faq(self):
        items = self.data.get("faq") or []
        return items if len(items) == len(_EN["faq"]) else _EN["faq"]

    def site(self, key):
        return self.data.get("site", {}).get(key) or _EN["site"][key]

    # ---- content ----------------------------------------------------

    def mood(self, slug_or_mood):
        """A mood with its text fields swapped for this language's."""
        m = slug_or_mood
        if isinstance(m, str):
            m = next(x for x in self._moods if x["slug"] == m)
        tr = self.data.get("moods", {}).get(m["slug"], {})
        out = dict(m)
        for k in MOOD_TEXT:
            if tr.get(k):
                out[k] = tr[k]
        return out

    def moods(self):
        return [self.mood(m) for m in self._moods]

    def collection(self, c):
        tr = self.data.get("collections", {}).get(c["slug"], {})
        out = dict(c)
        for k in ("name", "tagline"):
            if tr.get(k):
                out[k] = tr[k]
        return out

    def collections(self):
        return [self.collection(c) for c in self._collections]

    def writing_now(self):
        out = []
        for w in self._writing_now:
            tr = self.data.get("writingNow", {}).get(w["name"], {})
            out.append({"name": tr.get("name") or w["name"],
                        "tagline": tr.get("tagline") or w["tagline"]})
        return out

    def bundle(self, bundle):
        tr = self.data.get("bundle", {})
        out = dict(bundle)
        for k in ("name", "line", "blurb"):
            if tr.get(k):
                out[k] = tr[k]
        return out

    def finder(self, finder):
        """The one-question finder, translated, keyed by mood slug."""
        tr = self.data.get("finder", {})
        opts = tr.get("options", {})
        en_opts = _EN["finder"]["options"]
        out = {"question": tr.get("question") or _EN["finder"]["question"],
               "options": []}
        for o in finder["options"]:
            t = opts.get(o["mood"]) or en_opts.get(o["mood"], {})
            out["options"].append({
                "mood": o["mood"],
                "label": t.get("label") or o["label"],
                "because": t.get("because") or o["because"],
            })
        return out

    # ---- urls -------------------------------------------------------

    def u(self, path):
        """The path as this language serves it.

        Anchors and query strings ride along; a page that has no
        translation keeps its English URL.
        """
        base, sep, rest = _split(path)
        if not base.startswith("/") or not is_localized(base):
            return path
        return self.prefix + base + sep + rest

    def abs_u(self, origin, path):
        return origin + self.u(path)


def _split(path):
    for mark in ("#", "?"):
        i = path.find(mark)
        if i != -1:
            return path[:i], mark, path[i + 1:]
    return path, "", ""


def load(moods, collections, writing_now):
    """Every language, in picker order."""
    return [Lang(c, moods, collections, writing_now) for c in ORDER]


def alternates(origin, path):
    """(hreflang, href) for every language plus x-default.

    For a page that only exists in English this is empty: a one-language
    page shouldn't advertise alternates it doesn't have.
    """
    base, _, _ = _split(path)
    if not is_localized(base):
        return []
    out = []
    for code in ORDER:
        meta = _CATALOGS[code]["meta"]
        prefix = "" if code == DEFAULT else "/" + code
        out.append((meta["hreflang"], origin + prefix + base))
    out.append(("x-default", origin + base))
    return out
