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

## Before this goes live

1. **Replace the placeholder domain.** Every `https://moodshop.example` in
   `index.html`, `robots.txt`, and `sitemap.xml` needs to become your real
   domain once you have one. Find-and-replace `moodshop.example` across the repo.

2. **Create 8 BMC Extras**, one per emotion, priced per the table above.

3. **Set each Extra's post-payment redirect URL** to that emotion's page,
   e.g. the Calm listing redirects to `https://yourdomain.com/calm.html`.
   This is the entire delivery mechanism — get it right per listing.

4. **Replace the BMC links in `index.html`.** Right now every card points to
   `https://www.buymeacoffee.com/yourusername/e/<emotion>` — swap
   `yourusername` and the slug for your real BMC username and each Extra's
   actual slug. Also update the "Support Moodshop" link in the footer.

5. **Optional: add `og-image.png`.** `index.html` references
   `/og-image.png` for social share previews (1200×630 works well). Drop one
   in the repo root, or remove the two `og:image` / `twitter:image` tags if
   you don't want one yet.

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

## Content

The actual writing lives in each emotion page — that's the product. Feel
free to edit tone/length; each is currently 150–300 words in second-person
or letter format, per the spec.
