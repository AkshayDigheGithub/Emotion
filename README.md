# Moodshop

A no-login static site. Each page is a short piece of writing built to make the
reader feel one specific emotion. Payment happens on Buy Me a Coffee (BMC);
BMC's post-payment redirect *is* the delivery mechanism — there is no backend,
no database, no email.

## Structure

```
content/moods.json    THE SOURCE OF TRUTH — every mood, price, teaser, palette,
                      collection and mood-finder answer lives here
tools/build.py        generates every public page from it. Run after any edit.
templates/*.html      hand-written body copy for the bespoke pages (home, about,
                      send, for, payment help, 404) — build.py wraps them

--- generated, do not hand-edit ---
index.html            homepage
moods/index.html      every feeling
mood/<slug>/index.html  one sales + SEO page per feeling  (/mood/grief/)
collections/          themed collections, all "coming soon"
about/  send/  for/  help/payment/  404.html
moods-data.js         the same data, for the client
sitemap.xml  robots.txt
img/og/<slug>.jpg     per-mood Open Graph card, 1200x630

--- shared, hand-written ---
moodshop.css          one stylesheet for every public page
moodshop.js           finder, today's mood, share, send/receive, counter
analytics.js          msTrack() over Vercel Analytics + Datafast
gift.js               gifting from a paid page (unchanged)

--- the paid product: NEVER generated, never restyled by the shop ---
calm.html nostalgia.html happiness.html hope.html
rage.html hurt.html sorrow.html grief.html
bundle.html           the pack's delivery page
api/counter.js        Vercel serverless function — see "Unlock counter"
```

### The rule that matters

**The reader pages are what people paid for.** They are self-contained: their
own `<style>`, their own fonts, no dependency on `moodshop.css` or
`moodshop.js`. A change to the shop can therefore never break a page someone
already bought. `tools/build.py` does not write to them. Keep it that way.

### Adding a ninth mood

1. Add an entry to `content/moods.json` (copy an existing one).
2. Write `<slug>.html` — the paid piece — by copying an existing reader page.
3. Create the Buy Me a Coffee Extra, set its success page to redirect to
   `https://moodshop.lol/<slug>.html`, and paste the `/e/` URL into
   `checkoutUrl`.
4. Add the slug to `EMOTIONS` in `api/counter.js`.
5. `python3 tools/build.py` — the homepage grid, `/mood/<slug>/`, `/moods/`,
   the finder, the sitemap, robots.txt, the JSON-LD and the OG image all
   update themselves.

Nothing in that list involves touching a component, which is the whole point:
the shop scales to 50 moods without a rewrite.

## The landing page

`index.html` answers one question — *how do you want to feel?* — and then
gets out of the way. Top to bottom:

1. **Hero** — "How do you want to feel?" with a rotating tail word,
   "Tiny pieces of writing for very specific feelings", two CTAs (*Find my
   mood* / *Explore all moods*), four objection-killing chips, and the honest
   unlock counter.
2. **Maybe you're feeling…** — the eight mood cards. Each is a whole-card
   link to `/mood/<slug>/`, carrying its name, its one-line tagline and its
   price. A ninth dashed card marks *Love* as being written; it is not
   clickable and not buyable.
3. **Find your mood** — one question, eight answers, a recommendation. Pure
   client-side, no login, no storage. Answers map to moods in
   `content/moods.json` under `finder`.
4. **Today's mood** — one feeling a day, picked from the UTC date so everyone
   sees the same one and it changes at midnight. No database, no cron.
5. **Before any of this is a shop** — the free piece of writing the site opens
   with. It used to be the first thing on the page; it now sits after the
   product so the page says what it is before it gives something away.
6. **The Complete Mood Pack** — see below.
7. **Send a feeling** — entry point to `/send/`.
8. **How it works**, then the trust line, then the FAQ (`FAQPage` JSON-LD),
   then the signed author note.

Motion is gated behind `prefers-reduced-motion`, and scroll-reveal is gated
behind a `.js` class on `<html>` plus a 2.5s timer fallback, so a JS failure
can never leave the page blank.

### Keeping the teasers honest

Every teaser is the *real* opening of the piece it sells — 24–35% of the
words, cut mid-thought with a CSS mask. If you rewrite a piece, update its
`teaser` / `teaserTail` / `words` in `content/moods.json` and rebuild, or the
preview stops matching what buyers get.

## Plans

| Plan | Price | What it is | Status |
|---|---|---|---|
| One feeling | $1–$5 | Any single piece — the 8 existing BMC Extras | **Live** |
| The Complete Mood Pack | $9 | All eight in one payment (vs $23 separately) | **Needs one BMC step — see below** |
| Tip jar | Any | The plain BMC profile, no delivery promised | **Live** |

### Why prices are $1–$5 and not a flat $1

The per-piece prices here are the prices of the **live Buy Me a Coffee
Extras**. They are set on BMC, not in this repo, and the site displays
whatever `price` says in `content/moods.json`. Those two must agree: showing
"Enter this feeling — $1" on a button that opens a $5 checkout is a broken
purchase and a false price claim, so the data mirrors reality.

If you want the flat $1-per-piece / $5-pack model:

1. Re-price all eight Extras to $1 on Buy Me a Coffee.
2. Set every `"price": 1` in `content/moods.json`, and the bundle to `5`.
3. `python3 tools/build.py`.

Every price on the site — cards, buttons, JSON-LD offers, OG images, the
"$23 → save $14" anchor — is computed from that one file, so it is a
three-minute change once BMC agrees.

### The Complete Mood Pack is deliberately not buyable yet

`bundle.html` (the delivery page) is built and live. What does not exist is a
BMC Extra to sell it, so `content/moods.json` has `bundle.checkoutUrl: null`
and **every** pack block on the site renders as a price anchor pointing at
`/moods/`, never as a checkout. That is enforced in one place —
`bundle_block()` in `tools/build.py` — so it cannot be half-done.

**Why:** a real checkout would take $9 and deliver nothing automatically.

**Why keep the card at all:** it is a price anchor. $9 for eight makes a $1
piece read as trivial, which is exactly the decision a first-time visitor
should make.

**To open it:**

1. Create a BMC Extra called **The Complete Mood Pack**, priced **$9**.
2. Set its success page to **Redirect to a URL** →
   `https://moodshop.lol/bundle.html`.
3. Put the `/e/` URL in `content/moods.json` as `bundle.checkoutUrl`.
4. `python3 tools/build.py`.

Step 4 flips every pack block on every page to a live "Get the complete
collection — $9" button with a *Best value* badge. Nothing else to edit.

## Cross-sell on the emotion pages

Each reader page ends with a quiet line under the share button — "You've got
Grief. Seven other feelings are on the shelf, from $1." — now linking to
`/moods/` rather than the old `#shelf` anchor, which no longer exists. It sits
below the piece and after the share button on purpose: the product gets read
first, the shop gets mentioned second.

Those pages also load `analytics.js` and fire `purchase_completed` on load —
they are reachable only through the BMC redirect, so a load *is* a purchase.
A load carrying a gift fragment is excluded: there, the sender paid.

## Gifting (no backend, no database)

Every emotion page has a **Send this to someone** button under the piece. The
buyer types a recipient name, a short note and their own name; `gift.js`
encodes that into the link's `#fragment` and hands it back:

```
https://moodshop.lol/hope.html#g=eyJ0IjoiU2FtIiwiZiI6...
```

They send that link themselves, in whatever app they already talk to that
person in. The recipient opens it, sees the note in a card above the piece,
and the footer line switches from "You've got Hope" to "Someone paid to send
you this."

Why a fragment and not a query string or a database:

- **A fragment is never transmitted to the server.** It doesn't reach Vercel,
  doesn't appear in any access log, and isn't stored anywhere — the note
  exists only in the two people's browsers. That's a stronger version of the
  promise the rest of the site already makes.
- **No backend to run, nothing to expire.** The link keeps working as long as
  the page exists.

Trade-offs worth knowing:

- The recipient reads that piece for free. That *is* the gift — and they land
  on a real piece with a link back to the shop, which is the best advertising
  the site has.
- **You can't tell whether a gift was opened.** No database, no analytics on
  the note. If you ever want redemption stats, that's the thing you'd need a
  backend for.
- Notes are capped at 240 characters and names at 40, which keeps links around
  160–450 characters — short enough for any messenger.
- Everything is rendered with `textContent`, so a note can't inject markup,
  and a malformed payload is ignored rather than breaking the page.

Gifting is currently **free with any purchase** rather than its own product.
That's deliberate: it costs nothing to run, raises the value of every piece
sold, and puts your writing in front of people who didn't know the shop
existed. If you'd rather sell it, make a "Gift a feeling" BMC Extra the same
way as the bundle and point it at the piece.

The emotion pages also carry Open Graph tags now, so a gift link shows a
card ("Someone sent you a feeling") instead of a bare URL when it's pasted
into a messenger. They stay `noindex`.

## The author note

A short signed note sits between the FAQ and the footer, answering the
question every reader now asks by default: did a person make this, or did a
model?

It says, in Akshay's voice, that Moodshop is one person; that the pieces were
written with AI in the loop; and that what he did was choose the eight
feelings and decide what stays. That disclosure is deliberate. The pieces
were drafted by an AI assistant (see the first commit, `ab72e1b`), so a note
claiming they were hand-written would be false in exactly the way a suspicious
reader suspects — and it would be doing that work on a page asking for money.
Saying it plainly is both true and, in a market where everyone else stays
quiet, the more persuasive move.

Keep it accurate if the shop changes. If pieces get rewritten by hand later,
the note should say so; if an email list ever appears, the last line stops
being true.

## Free pieces (the SEO asset)

`free/` holds three short pieces that are **free and indexable**, plus a hub
page at `/free/`. They exist because the shop could not rank: the product is
deliberately `noindex`, which left exactly one indexable page with 831 words
and nothing for Google to match a query against.

| URL | The search it is written for |
|---|---|
| `/free/cant-sleep.html` | "something to read when you can't sleep", 3am racing thoughts |
| `/free/waiting-for-news.html` | waiting on a result, a diagnosis, a decision |
| `/free/the-strong-one.html` | "tired of being the strong one", everyone leans on me |

Deliberately **different feelings from the paid eight**, so nothing on the
shelf is cannibalised. Each is self-canonical, carries `Article` schema,
ends with a link into `/#taste`, and is listed in `sitemap.xml`. The landing
page links to `/free/` under the shelf, giving crawlers a path in.

This took the site from 1 indexable page / 831 words to **5 pages / 1,914
words** with real internal linking. It will not rank for anything
competitive — it is aimed at long-tail phrasings where the intent match is
exact and the competition is weak.

Add more over time; that is the whole mechanism. One new free piece a week
is worth more than any amount of meta-tag work.

## Canonical domain

`moodshop.lol` 308-redirects to `www.moodshop.lol`, so **every URL in this
repo points at `www`** — canonical tags, `og:url`, sitemap, `robots.txt`,
and the share captions in `gift.js` and the emotion pages. Previously they
pointed at the bare apex, which meant the canonical named a URL that
immediately redirected.

If you would rather the bare domain be primary, flip it in Vercel
(Project → Settings → Domains) and reverse this repo with:

```
grep -rl 'https://www\.moodshop\.lol' --include='*.html' --include='*.js' \
  --include='*.txt' --include='*.xml' . \
  | xargs sed -i 's#https://www\.moodshop\.lol#https://moodshop.lol#g'
```

The rule is only that the repo and Vercel must agree.

## The overture

The site used to open with ~250 words of free writing before any product was
visible. That writing is still on the homepage — under *"Before any of this is
a shop"* — but it now sits **after** the mood grid, the finder and today's
mood.

The reason for the move: a visitor arriving cold could not tell what Moodshop
*was* until they had scrolled past an essay. The page now answers "how do you
want to feel?" in the first viewport and gives the free thing once the offer
is understood. Nothing was deleted.

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

## Social share image

`og-image.jpg` (600×315) lives in the repo root and is wired into
`index.html`'s `og:image`/`twitter:image` tags. It's a brand card — dark
gradient, "Moodshop" wordmark, the 8 emotion-color swatches, `moodshop.lol`
— generated by rendering `og-image.html`-style markup through headless
Chromium and screenshotting it (no design tool involved). To regenerate it
with different copy/colors, edit the HTML, re-screenshot at 1200×630 (crop
to exact size if the renderer pads it — Chrome's `--screenshot` CLI can add
a few dozen px of blank space depending on version), and replace the file.

## Why the emotion pages aren't linked anywhere

This is the "unlisted, not locked" approach: the only way to reach
`sorrow.html` etc. is the BMC redirect after payment. To keep it that way:

- Nothing on the shop links to a reader page — the public page for a feeling
  is `/mood/<slug>/`, which sells it and shows only its opening.
- Each reader page ships `<meta name="robots" content="noindex, nofollow">`.
- `robots.txt` disallows them, and `tools/build.py` regenerates that list from
  `readerPage` in `content/moods.json`, so a new mood can't be forgotten.
- `sitemap.xml` lists only public pages.

It's a soft gate, not real security — anyone with the direct URL can still
open the page. That's the intended tradeoff (no backend, no auth).

**Do not confuse the two URL shapes:**

| URL | What it is | Indexed? |
|---|---|---|
| `/mood/grief/` | the shop page — tagline, teaser, price, buy button | yes |
| `/grief.html` | the piece itself, what a payment opens | no |

## SEO notes

Every feeling has its own indexable page at `/mood/<slug>/` with a unique
title, description, canonical, Open Graph + Twitter card, its own 1200x630
OG image, and `Product` + `BreadcrumbList` JSON-LD. Titles are written around
the intent someone actually types — "something to read when you're grieving
someone", "something to read when everything feels too loud" — rather than
stuffed with keywords.

Page inventory and their markup:

| Route | JSON-LD |
|---|---|
| `/` | `WebSite` + `ItemList` of 8 `Product`/`Offer` + `FAQPage` |
| `/moods/` | `ItemList` |
| `/mood/<slug>/` | `Product` + `Offer` + `BreadcrumbList` |
| `/free/` | `CollectionPage` (pre-existing) |
| `/collections/`, `/about/`, `/send/` | none needed |
| `/for/`, `/help/payment/` | `noindex` — not search destinations |

`sitemap.xml` and `robots.txt` are both generated by `tools/build.py`. Adding
a mood adds its sitemap entry and its reader-page `Disallow` automatically.

### The Product markup, and what Search Console wants from it

Search Console first reported all eight shelf items as **invalid**: one
critical issue each, because a `Product` with no `image` can't produce a rich
result. The `ItemList` now gives every piece the full set:

| Property | Value |
|---|---|
| `image` | `https://www.moodshop.lol/img/og/<slug>.jpg` — 1200×630, the piece's own gradient |
| `url` | `https://www.moodshop.lol/mood/<slug>/` — that feeling's own page |
| `sku` | `moodshop-<key>` |
| `brand` | Moodshop |
| `offers.url` | the BMC Extra that actually sells it |
| `offers` | `price`, `priceCurrency`, `availability`, `itemCondition`, `priceValidUntil`, `seller` |

Two things to keep in mind when editing:

- **The prices in the JSON-LD and on the page can no longer disagree** — both
  come from `price` in `content/moods.json`. This used to be a manual-action
  risk; now it is one number in one file. Same for the word counts.
- **`priceValidUntil` is 2027-12-31.** Once it's in the past Google treats the
  offer as expired and the item drops out of rich results. Push it forward.

`review` and `aggregateRating` are still reported as missing. That's a
non-critical warning and it stays: there are no real reviews, and inventing
them is exactly the kind of thing that earns a structured-data penalty. If
real ratings ever exist, add them then. `shippingDetails` and
`hasMerchantReturnPolicy` are likewise absent — nothing ships, and there's no
written refund policy to encode yet (the FAQ says a wrong piece gets swapped,
not refunded). Encode it only once it's a real policy.

Regenerate the OG images after a palette change:

```
pip install Pillow
python3 tools/build.py
```

`tools/make-product-images.py` is the older 1200x1200 square generator; its
output in `img/*.jpg` is no longer referenced by any markup, and its palette
table is a hand-kept copy. `tools/build.py` reads the palettes straight from
`content/moods.json`, so there is nothing to keep in sync.
- Reader pages stay `noindex` — they're the paid product, not content you
  want ranking or showing up in search results out of context. `/mood/<slug>/`
  is the page that ranks for a feeling.
- Consider adding a few backlinks / a short blog post around "Moodshop"
  once the domain is live — the JSON-LD alone won't rank an empty domain.

## Deploying

Deployed on Vercel specifically because it now needs one small serverless
function (see below) — a pure static host (GitHub Pages, Netlify's static
tier) would no longer be enough. Any host with lightweight function support
would still work.

The Vercel project is **connected to this GitHub repo**, so every push to the
production branch deploys itself. Nothing to run by hand.

- **Production branch: `claude/moodshop-static-site-cue6zs`.** This repo has
  no `main` — that branch is the default, and it is what Vercel builds and
  aliases to `moodshop.lol`. Merge feature branches into it to ship.
- Pushes to any other branch produce a preview deployment on a `.vercel.app`
  URL, which is behind the SSO wall described above.

Worth knowing, because it cost an afternoon once: the project spent its early
life **unlinked**, deployed by direct file upload from a laptop. If a push
ever stops showing up on the live site, check Settings → Git first — an
unlinked project accepts pushes silently and deploys none of them, and a
project linked to the *wrong* repo will happily publish that repo's site to
`moodshop.lol`.

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

- **A missing key counts as zero.** Abacus does not create a key until a
  page is first loaded, so before this was handled, one never-unlocked
  emotion made `?action=total` return 502 and the landing page silently hid
  the stat line — it had never rendered for a single visitor. A 404 from
  upstream is now read as the zero it is; a real outage still fails loudly.
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

Two different share surfaces, on purpose.

**On the shop (`/mood/<slug>/`)** — a row of five: *Send this feeling*
(native share sheet), *Copy link*, *Post on X*, *WhatsApp*, *Save the card*.
The last one draws a 1080x1080 quote card client-side on a `<canvas>` in that
feeling's own gradient, then offers it to the native share sheet or downloads
it. Everything shared points at `/mood/<slug>/` — the page with the teaser,
not the piece — so a shared link converts instead of leaking.

**On a reader page** — the pre-existing quiet "Share this feeling" button,
unchanged. It shares a caption and the card, never the reader page's own URL,
because that link would give the full piece away.

## Send a feeling (`/send/` and `/for/`)

A pre-purchase gifting loop that needs no backend, no account and no database.

1. On `/send/`, someone picks a feeling, a recipient name and a short note.
2. `moodshop.js` encodes `{m, t, f, n}` as url-safe base64 into the
   **fragment** of `https://www.moodshop.lol/for/#<payload>`.
3. They send that link themselves, in whatever app they already use.
4. `/for/` decodes the fragment, shows "For Sam." over their note in that
   feeling's colours, and offers *Open the feeling →* into `/mood/<slug>/`.

**A fragment is never transmitted to the server.** The note reaches Vercel,
this repo and every analytics provider exactly never — it exists only in the
two people's browsers. There is nothing to store and nothing to leak.

The recipient gets the free teaser, like everyone else. This is deliberately
*not* a way to give away paid writing: that is what `gift.js` on a reader page
is for, and it requires having paid first.

`/for/` is `noindex` and degrades gracefully — a missing, truncated or
mangled payload shows a written empty state, and `<noscript>` explains why the
note needs JS and links on to the shelf.

## Analytics

`analytics.js` defines `window.msTrack(name, props)` over the two providers
already on the site — Vercel Web Analytics (`window.va`) and Datafast
(`window.datafast`). Either may be blocked by a content blocker; every call is
wrapped, so a missing provider is a no-op and never an exception. Calls made
before the deferred provider scripts run are queued and flushed.

Events, and where they fire:

| Event | Fired by |
|---|---|
| `homepage_view` | the providers' own pageview — not duplicated here |
| `mood_selected` | any mood card, today's mood, a finder result, a gift open |
| `mood_finder_started` | first answer tapped, or the nav/hero *Find my mood* |
| `mood_finder_completed` | a recommendation is shown |
| `mood_page_view` | the providers' own pageview on `/mood/<slug>/` |
| `teaser_view` | the teaser scrolls 40% into view |
| `checkout_started` | any click on any `buymeacoffee.com` link, anywhere |
| `purchase_completed` | a reader page or `bundle.html` loads without a gift fragment |
| `bundle_clicked` | any pack CTA |
| `share_clicked` / `share_completed` | the share row |
| `send_feeling_clicked` | the *Send a feeling* entry points and `/send/` submit |

Declarative usage: `data-track="…"` plus optional `data-track-mood` /
`data-track-from` on any element. No personal data is collected — event names
and a mood slug, nothing else. Custom events need a Vercel Web Analytics plan
that supports them; the calls are harmless either way.

## Error and empty states

| State | Page |
|---|---|
| 404 | `404.html` — "Looks like this feeling got lost." + all eight moods. Vercel serves it automatically for unmatched paths on a static deployment. |
| Payment cancelled / declined / paid-but-nothing-opened / link lost | `/help/payment/`, linked from every mood page under the buy button |
| A gift link that carried nothing | the empty state on `/for/` |
| JS off on `/for/` | `<noscript>` explains and links to `/moods/` |

## Social proof

There are no testimonials, so none are shown. The structure is in
`templates/home.html` as a commented-out section, and `content/moods.json`
has an empty `testimonials` array. Real quotes go in there. **Nothing
invented goes there** — fake reviews are the fastest way to lose both trust
and a rich result.

## Content

The actual writing lives in each emotion page — that's the product. Feel
free to edit tone/length; each is currently 150–300 words in second-person
or letter format, per the spec.
