const app = createApp();
app.get('/shadow', shadowHandler);

export default function handler(req, res) {
  return res.status(200).json({ ok: true });
}

function shadowHandler(req, res) {
  return res.status(200).end();
}
