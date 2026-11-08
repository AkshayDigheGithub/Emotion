// The nine translated trees (/de/, /es/, /fr/, /pt/, /hi/, /zh/, /ja/,
// /ru/, /ar/) were removed in November 2026. The site is English-only.
//
// 410 rather than 404, deliberately: "this existed and has been taken
// down" is what gets a URL dropped from an index promptly, where 404
// only says "not here just now" and keeps the URL on the retry list.
// Vercel serves static files before it reaches a function, so nothing
// that still exists can land here; vercel.json points the dead prefixes
// at this handler.
//
// The reply still names the English page the reader was probably after,
// because a person following an old link deserves somewhere to go.

const LANGS = ['de', 'es', 'fr', 'pt', 'hi', 'zh', 'ja', 'ru', 'ar'];
const SAFE = /^\/[A-Za-z0-9/_.-]*$/;

function englishPath(url) {
  const path = String(url || '/').split('?')[0].split('#')[0];
  const m = path.match(/^\/([a-z]{2})(?:\/(.*))?$/);
  if (!m || !LANGS.includes(m[1])) return '/';
  const rest = '/' + (m[2] || '');
  return SAFE.test(rest) && !rest.includes('..') ? rest : '/';
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

function body(target) {
  const href = escapeHtml(target);
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>This page has been removed | Moodshop</title>
<meta name="robots" content="noindex">
<link rel="stylesheet" href="/moodshop.css">
</head>
<body>
<main id="main" class="wrap" style="padding:clamp(3rem,12vw,6rem) 0;max-width:34rem;">
  <h1>This page has been removed.</h1>
  <p>Moodshop used to be published in ten languages. It is written in
     English now, and the translated pages are gone for good.</p>
  <p><a href="${href}">Read this page in English</a> &middot;
     <a href="/">Back to the shelf</a></p>
</main>
</body>
</html>
`;
}

module.exports = (req, res) => {
  const target = englishPath(req.url);
  res.statusCode = 410;
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 'public, max-age=0, must-revalidate');
  res.setHeader('X-Robots-Tag', 'noindex');
  res.end(body(target));
};

module.exports.englishPath = englishPath;
