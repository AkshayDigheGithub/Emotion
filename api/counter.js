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
      const data = await r.json();
      res.status(200).json(data);
    } catch (err) {
      res.status(502).json({ error: 'upstream error' });
    }
    return;
  }

  if (action === 'total') {
    try {
      const values = await Promise.all(EMOTIONS.map(async (e) => {
        const r = await fetch(`https://abacus.jasoncameron.dev/get/${NAMESPACE}/${e}`);
        if (!r.ok) throw new Error('bad response');
        const data = await r.json();
        return data.value || 0;
      }));
      const total = values.reduce((a, b) => a + b, 0);
      res.status(200).json({ ok: true, total });
    } catch (err) {
      res.status(502).json({ ok: false });
    }
    return;
  }

  res.status(400).json({ error: 'invalid action' });
};
