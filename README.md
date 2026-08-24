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
```

The pricing table in the original spec also mentioned "Longing" at $3, but the
site structure only calls for these 8 pages. Add a `longing.html` the same way
as the others (copy `rage.html`'s structure, swap palette/copy) if you want a 9th.

## Live deployment

Deployed on Vercel: **https://moodshop-delta.vercel.app**

`index.html`, `robots.txt`, and `sitemap.xml` all point at this domain now
(canonical, Open Graph, JSON-LD). If you later attach a custom domain in
Vercel, find-and-replace `moodshop-delta.vercel.app` across the repo with
your new domain and redeploy.

## Before this goes fully live

1. **Create 8 BMC Extras** at [buymeacoffee.com/digheakshaf](https://buymeacoffee.com/digheakshaf),
   one per emotion, priced per the table above.

2. **Set each Extra's post-payment redirect URL** to that emotion's page,
   e.g. the Calm listing redirects to `https://moodshop-delta.vercel.app/calm.html`
   (or your custom domain once you have one). This is the entire delivery
   mechanism — get it right per listing.

3. **Fix the BMC slugs in `index.html`.** Every card currently points to
   `https://www.buymeacoffee.com/digheakshaf/e/<emotion>` (e.g. `.../e/calm`).
   BMC auto-generates its own slug per Extra when you create it — once each
   listing exists, swap that last path segment for the real slug BMC gives you.
   The username (`digheakshaf`) is already correct.

4. **Optional: add social share art.** The Open Graph/Twitter tags currently
   omit an image since none exists yet. To add one, drop `og-image.png`
   (1200×630 works well) in the repo root and add back
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

Any static host works — GitHub Pages, Netlify, Vercel. No build step, no
dependencies. Push this repo and point the host at the root.

## Unlock counter

The landing page shows an honest running total: "N pieces unlocked so far."
It's real, not decorative — no number moves unless someone actually loads
an emotion page.

How it works: each emotion page fires a silent `fetch()` to
[Abacus](https://abacus.jasoncameron.dev) (a free, keyless public counter
API) on load, incrementing that emotion's key under the `moodshop-digheakshaf`
namespace. `index.html` reads all 8 keys on load, sums them, and shows the
total — or "No one has unlocked a piece yet — be the first." at zero. If the
fetch fails for any reason, the stat line just stays hidden rather than
showing a stale or wrong number.

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

## Content

The actual writing lives in each emotion page — that's the product. Feel
free to edit tone/length; each is currently 150–300 words in second-person
or letter format, per the spec.
