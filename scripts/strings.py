#!/usr/bin/env python3
"""The site's text, in English.

Every string the pages are built from lives in content/strings.json:
the UI labels, the per-page titles and descriptions, the FAQ, and the
English wording of the moods, collections, bundle and finder that
overrides the language-neutral facts in content/moods.json (price,
slug, theme, checkout URL).

This used to be scripts/i18n.py, which held ten catalogues and served
English at the root with the other nine under /<code>/. The site is
English-only now: one catalogue, one URL per page, no prefixes and no
hreflang. The overlay over moods.json stays, because that split is
still useful — facts in one file, wording in another.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGUE = os.path.join(ROOT, "content", "strings.json")

# Text fields of a mood that the catalogue may override. Everything else
# (price, theme, checkout URL, slug) is not wording and stays in moods.json.
MOOD_TEXT = ("name", "tagline", "description", "whatThisIs", "teaserTitle",
             "teaser", "teaserTail", "shareLine", "seoTitle", "seoKeywords")


class _Keep(dict):
    """format_map() mapping that leaves an unknown {placeholder} alone."""

    def __missing__(self, key):
        return "{%s}" % key


class Strings(object):
    """The catalogue, and the content it dresses."""

    def __init__(self, moods, collections, writing_now):
        with open(CATALOGUE, encoding="utf-8") as fh:
            self.data = json.load(fh)
        meta = self.data["meta"]
        self.code = meta["code"]
        self.hreflang = meta["hreflang"]   # the <html lang> and og:locale pair
        self.locale = meta["locale"]
        self.dir = meta.get("dir", "ltr")
        self._moods = moods
        self._collections = collections
        self._writing_now = writing_now

    # ---- strings ----------------------------------------------------

    def t(self, key, **fmt):
        """A UI string, formatted; the key itself if there isn't one.

        A placeholder nobody passed a value for is left as it was rather
        than raising, so a stray {price} cannot take the build down.
        """
        s = self.data.get("ui", {}).get(key, key)
        if "{" not in s:
            return s
        try:
            return s.format_map(_Keep(fmt))
        except (IndexError, ValueError):
            return s

    def js(self):
        """The client-side strings."""
        return dict(self.data.get("js", {}))

    def page(self, name):
        """{title, description, ogTitle, ogDesc} for a page."""
        return dict(self.data.get("pages", {}).get(name, {}))

    def faq(self):
        return self.data.get("faq") or []

    def site(self, key):
        return self.data["site"][key]

    # ---- content ----------------------------------------------------

    def mood(self, slug_or_mood):
        """A mood, with its wording from the catalogue."""
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
        """The one-question finder, keyed by mood slug."""
        tr = self.data.get("finder", {})
        opts = tr.get("options", {})
        out = {"question": tr.get("question") or finder.get("question"),
               "options": []}
        for o in finder["options"]:
            t = opts.get(o["mood"], {})
            out["options"].append({
                "mood": o["mood"],
                "label": t.get("label") or o["label"],
                "because": t.get("because") or o["because"],
            })
        return out


def load(moods, collections, writing_now):
    return Strings(moods, collections, writing_now)
