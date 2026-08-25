const NAMESPACE = 'moodshop-digheakshaf';
const EMOTIONS = ['calm', 'nostalgia', 'happiness', 'hope', 'rage', 'hurt', 'sorrow', 'grief'];

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const { action, emotion } = req.query;

  if (action === 'hit') {
    if (!EMOTIONS.includes(emotion)) {
      res.status(400).json({ error: 'invalid emotion' });
      return;
    }
    try {
      const r = await fetch(`https://abacus.jasoncameron.dev/hit/${NAMESPACE}/${emotion}`);
      const text = await r.text();
      console.error('hit upstream status', r.status, 'body', text);
      if (!r.ok) {
        res.status(502).json({ error: 'upstream error', upstreamStatus: r.status, upstreamBody: text });
        return;
      }
      res.status(200).json(JSON.parse(text));
    } catch (err) {
      console.error('hit exception', err && err.message, err && err.stack);
      res.status(502).json({ error: 'upstream error', message: err && err.message });
    }
    return;
  }

  if (action === 'total') {
    try {
      const values = await Promise.all(EMOTIONS.map(async (e) => {
        const r = await fetch(`https://abacus.jasoncameron.dev/get/${NAMESPACE}/${e}`);
        const text = await r.text();
        if (r.status === 404) {
          // Abacus creates a key lazily on first hit — no hits yet just means 0.
          return 0;
        }
        if (!r.ok) {
          console.error('total upstream status', e, r.status, 'body', text);
          throw new Error(`bad response for ${e}: ${r.status} ${text}`);
        }
        const data = JSON.parse(text);
        return data.value || 0;
      }));
      const total = values.reduce((a, b) => a + b, 0);
      res.status(200).json({ ok: true, total });
    } catch (err) {
      console.error('total exception', err && err.message, err && err.stack);
      res.status(502).json({ ok: false, message: err && err.message });
    }
    return;
  }

  res.status(400).json({ error: 'invalid action' });
};
