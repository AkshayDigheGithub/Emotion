# Moodshop

A no-login static site. Each page is a short piece of writing built to make the
reader feel one specific emotion. Payment happens on Buy Me a Coffee (BMC);
BMC's post-payment redirect *is* the delivery mechanism — there is no backend,
no database, no email.

## Structure

```
index.html       landing page — hero, free preview picker, shelf, plans, FAQ
bundle.html      "Whole Shelf" delivery page — links to all 8, unlisted
gift.js          gifting: composes and reads gift links (no backend)
happiness.html   $2  (linked nowhere except the BMC redirect for this listing)
sorrow.html      $5
hurt.html        $4
calm.html        $1
nostalgia.html   $1
rage.html        $3
hope.html        $2
grief.html       $5
robots.txt       blocks crawlers from the emotion + bundle pages, allows the landing page
sitemap.xml      lists only index.html, on purpose
api/counter.js   Vercel serverless function — see "Unlock counter" below
```

The pricing table in the original spec also mentioned "Longing" at $3, but the
site structure only calls for these 8 pages. Add a `longing.html` the same way
as the others (copy `rage.html`'s structure, swap palette/copy) if you want a 9th.

## The landing page

`index.html` is the whole sales pitch. Top to bottom:

1. **Hero** — one promise ("Feel _______ in two minutes"), a rotating feeling
   word, four objection-killing chips (~2 min, nothing to install, no signup,
   from $1), and the honest unlock counter as social proof.
2. **Free preview picker** — the conversion engine. Eight mood chips plus a
   "Surprise me". Picking one themes the whole page in that emotion's palette
   and shows the *real* opening of that piece — 45-odd words lifted verbatim
   from the page you're selling — then fades the next line out under a mask
   and offers "Unlock the rest — $N". Nobody has to buy blind any more.
3. **How it works** — three steps, because "pay a stranger and get redirected
   somewhere" needs explaining before it feels safe.
4. **The shelf** — the eight cards, each now carrying its own opening line as
   a pull-quote and two actions: `Unlock` (straight to BMC) and `Preview`
   (scrolls back up and loads that piece into the picker).
5. **Plans** — see below.
6. **FAQ** — six questions, also emitted as `FAQPage` JSON-LD.

Everything is still one static file with no build step and no dependencies.
Motion is gated behind `prefers-reduced-motion`, and the scroll-reveal
animation is gated behind a `.js` class on `<html>` plus a 2.5s timer
fallback, so a JS failure can never leave the page blank.

### Keeping the previews honest

The excerpts in the picker are copy-pasted from the emotion pages, and the
word counts next to them are real. If you rewrite a piece, update its
`excerpt`/`tail`/`words` in the `PIECES` array in `index.html` or the preview
stops matching what buyers get.

## Plans

Three tiers on the landing page:

| Plan | Price | What it is | Status |
|---|---|---|---|
| One feeling | $1–$5 | Any single piece — the 8 existing BMC Extras | **Live** |
| The Whole Shelf | $9 | All eight in one payment (vs $23 separately) | **Needs one BMC step — see below** |
| Tip jar | Any | The plain BMC profile, no delivery promised | **Live** |

### The Whole Shelf is deliberately not buyable yet

The plan card is on the page, priced, with the $23-vs-$9 comparison — but its
button goes to `#shelf`, not to a checkout. That's on purpose, and it should
stay that way until the BMC Extra exists.

**Why:** there is no "Whole Shelf" Extra on Buy Me a Coffee, so a real
checkout would take $9 and deliver nothing automatically — you'd be emailing
the link by hand. A shop that takes money and goes quiet is worse than a shop
with one plan not open yet.

**Why keep the card at all:** it's a price anchor. $9 for eight makes a $1
piece read as trivial, which is exactly the decision we want a first-time
visitor to make. The card's button funnels to the shelf — "Start with one —
from $1" — so it sells singles instead of nothing.

**To open it** (three steps, then it's a real product):

1. Create a BMC Extra called **The Whole Shelf**, priced **$9**.
2. Set its success page to **Redirect to a URL** →
   `https://moodshop.lol/bundle.html` — already built, live, and unlisted.
3. In `index.html`, replace that card's `<a class="btn btn-ghost" href="#shelf">`
   with `<a class="btn btn-primary" href="<the /e/ URL>" rel="nofollow">Take
   the whole shelf — $9</a>`, swap the badge back to `Best value` (dropping
   `badge-soon`), and move the `featured` class from "One feeling" onto it.

Also restore the bundle to the `ItemList` JSON-LD when you do — it was removed
so structured data doesn't advertise an offer nobody can accept.

## Cross-sell on the emotion pages

Each emotion page now ends with a quiet line under the share button —
"You've got Grief. Seven other feelings are on the shelf, from $1 — or take
all eight for $9." — linking back to `#plans` and `#shelf`. It sits below the
piece and after the share button on purpose: the product gets read first, the
shop gets mentioned second.

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
