# Moodshop

A no-login static site. Each page is a short piece of writing built to make the
reader feel one specific emotion. Payment happens on Buy Me a Coffee (BMC);
BMC's post-payment redirect *is* the delivery mechanism — there is no backend,
no database, no email.

## Structure

```
index.html       landing page — grid of emotion cards, linked, indexable
happiness.html   $2  (linked nowhere except the BMC redirect for this listing)
sorrow.html      $5
hurt.html        $4
calm.html        $1
nostalgia.html   $1
rage.html        $3
hope.html        $2
grief.html       $5
robots.txt       blocks crawlers from the emotion pages, allows the landing page
sitemap.xml      lists only index.html, on purpose
api/counter.js   Vercel serverless function — see "Unlock counter" below
```

The pricing table in the original spec also mentioned "Longing" at $3, but the
site structure only calls for these 8 pages. Add a `longing.html` the same way
as the others (copy `rage.html`'s structure, swap palette/copy) if you want a 9th.

## Live deployment

Deployed on Vercel, live at **https://moodshop.lol**

### Vercel Web Analytics

Every page loads `<script defer src="/_vercel/insights/script.js"></script>`
— the standard way to add Vercel Web Analytics to a plain static site with
no build step (no `@vercel/analytics` npm package needed, since there's no
bundler here).

Confirmed working: the Analytics API returns real (currently 0/0, since
there's no traffic yet) data for this project rather than an "enabled"
error, so tracking is live on the Vercel side — no dashboard toggle needed.
Once real visitors show up, numbers appear in Project → Analytics in the
Vercel dashboard within a few minutes.

`index.html`, `robots.txt`, `sitemap.xml`, and every emotion page's share
script all point at this domain now (canonical, Open Graph, JSON-LD, the
share caption link).

### Deployment protection — read this before setting BMC redirects

The Vercel project has **SSO/deployment protection enabled on its
`*.vercel.app` URLs** (`moodshop-delta.vercel.app`,
`moodshop-akshay-d111.vercel.app`) — visiting those shows a Vercel login
wall to anyone who isn't logged into this Vercel account. **Custom domains
are exempt from this**, so `moodshop.lol` / `www.moodshop.lol` are the only
publicly reachable URLs.

This matters a lot for the BMC redirects below: if any Extra's "redirect to
a URL" field points at a `.vercel.app` URL instead of `moodshop.lol`,
paying customers get sent to a login page instead of their piece.
**Double-check every one of the 8 Extras uses `moodshop.lol`, not
`vercel.app`, in its redirect URL** — earlier setup guidance (including
from me, before the custom domain was connected) suggested `.vercel.app`
URLs, so this is worth verifying even if it "worked" during testing while
logged into Vercel yourself.

## BMC Extras (live)

All 8 Extras are created and wired into `index.html`:

| Emotion | Extra URL |
|---|---|
| Calm | https://buymeacoffee.com/digheakshaf/e/569310 |
| Nostalgia | https://buymeacoffee.com/digheakshaf/e/569313 |
| Happiness | https://buymeacoffee.com/digheakshaf/e/569314 |
| Hope | https://buymeacoffee.com/digheakshaf/e/569315 |
| Rage | https://buymeacoffee.com/digheakshaf/e/569316 |
| Hurt | https://buymeacoffee.com/digheakshaf/e/569317 |
| Sorrow | https://buymeacoffee.com/digheakshaf/e/569318 |
| Grief | https://buymeacoffee.com/digheakshaf/e/569319 |

Each Extra's **Success page** must be set to "Redirect to a URL after
purchase" pointing at that emotion's page on the live domain (e.g. Calm →
`https://moodshop.lol/calm.html`) — "Confirmation message" (BMC's default)
does not deliver anything, it just shows a thank-you message on BMC's own
site. See "Deployment protection" above — use `moodshop.lol`, not a
`vercel.app` URL.

## Before this goes fully live

1. **Optional: add social share art.** The Open Graph/Twitter tags on
   `index.html` currently omit an image since none exists yet. To add one,
   drop `og-image.png` (1200×630 works well) in the repo root and add back
   `<meta property="og:image">` / `<meta name="twitter:image">` pointing at
   `/og-image.png`, then redeploy.

## Why the emotion pages aren't linked anywhere

This is the spec's "unlisted, not locked" approach: the only way to reach
`sorrow.html` etc. is the BMC redirect after payment. To keep it that way:

- `index.html` never links to the emotion pages directly, only out to BMC.
- Each emotion page ships `<meta name="robots" content="noindex, nofollow">`.
- `robots.txt` explicitly disallows them.
- `sitemap.xml` lists only the landing page.

It's a soft gate, not real security — anyone with the direct URL can still
open the page. That's the intended tradeoff (no backend, no auth).

## SEO notes

- `index.html` carries title/description, canonical, Open Graph, Twitter
  Card, and JSON-LD (`WebSite` + `ItemList` of `Product`/`Offer`) so it can
  show up well in search and when shared on social.
- Emotion pages are intentionally `noindex` — they're the paid product, not
  content you want ranking or showing up in search results out of context.
- Consider adding a few backlinks / a short blog post around "Moodshop"
  once the domain is live — the JSON-LD alone won't rank an empty domain.

## Deploying

Deployed on Vercel specifically because it now needs one small serverless
function (see below) — a pure static host (GitHub Pages, Netlify's static
tier) would no longer be enough. Any host with lightweight function support
would still work.

## Unlock counter

The landing page shows an honest running total: "N pieces unlocked so far."
It's real, not decorative — no number moves unless someone actually loads
an emotion page.

How it works: each emotion page fires a silent `fetch()` to `/api/counter`
(a Vercel serverless function, `api/counter.js`) on load, which server-side
proxies to [Abacus](https://abacus.jasoncameron.dev) (a free, keyless public
counter API) and increments that emotion's key under the
`moodshop-digheakshaf` namespace. `index.html` calls the same function
(`?action=total`) to sum all 8 keys and show the total — or "No one has
unlocked a piece yet — be the first." at zero. If anything fails, the stat
line just stays hidden rather than showing a stale or wrong number.

This goes through a same-origin API route rather than calling Abacus
directly from the browser **specifically to avoid ad blockers.** A direct
client-side `fetch()` to a third-party "hit counter" domain is exactly the
kind of cross-site request tools like uBlock Origin and Brave Shields block
by default — which was silently hiding the counter for real visitors. The
proxy makes it a same-origin call, which those tools don't touch.

Known limitations, worth knowing before you rely on this:

- **It's a third-party free service**, not Vercel infrastructure — no SLA,
  could go down or get rate-limited, and the count isn't yours to export or
  guarantee. Fine for a soft "some real people did this" signal, not fine as
  a business metric.
- **It counts page loads, not verified purchases.** Since the emotion pages
  are only reachable via the BMC redirect (see below), a load is *almost*
  always a real unlock — but anyone who gets hold of a direct URL and
  revisits it, or a bot that crawls a leaked link, would also increment it.
- **To make this durable**, swap the Abacus calls for a first-party
  serverless function backed by Vercel KV, Vercel Postgres, or Upstash
  Redis under your own account — I don't have the access to provision
  storage resources for you, so that step is a manual one-time setup in the
  Vercel dashboard if you want it later.

## Share feature

Each emotion page has a quiet "Share this feeling" button at the bottom
(below the piece, doesn't clutter the reading experience). Clicking it:

1. Draws a 1080×1080 quote card client-side (`<canvas>`) using that page's
   own gradient colors and a short pull-quote from the piece.
2. Tries the native share sheet (`navigator.share` with the image file) —
   works on most mobile browsers.
3. Falls back to downloading the PNG + copying a caption to the clipboard
   on desktop/unsupported browsers.

Deliberately **does not** share the emotion page's own URL — only a caption
+ link back to the landing page (`moodshop.lol`). Sharing the
direct page link would let anyone who receives it read the full piece for
free, defeating the point of the paywall. The quote card gives people
something to post without giving away the product itself.

## Content

The actual writing lives in each emotion page — that's the product. Feel
free to edit tone/length; each is currently 150–300 words in second-person
or letter format, per the spec.
