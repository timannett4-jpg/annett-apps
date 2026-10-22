// Annett Apps offline cache (farm, bdm, laura, europe).
// Pages: network first so updates arrive, cache when offline.
// Photos and documents (_blob/<id>): served from this device's cache, fetched from your Google Drive sync when missing.
const CACHE = 'annett-apps-v1', ASSETS = 'annett-assets', CONFIG = 'annett-config';
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

async function asset(req, id) {
  const c = await caches.open(ASSETS);
  const hit = await c.match(req, { ignoreSearch: true });
  if (hit) return hit;
  const cfgRes = await (await caches.open(CONFIG)).match('config');
  if (!cfgRes) return new Response('Not synced yet', { status: 404 });
  const cfg = await cfgRes.json();
  const r = await fetch(cfg.url + '?app=a-' + id.slice(0, 24) + '&k=' + encodeURIComponent(cfg.key)).then(r => r.json());
  if (!r.ok || !r.data) return new Response('Not found', { status: 404 });
  const bin = Uint8Array.from(atob(r.data.b64), ch => ch.charCodeAt(0));
  const res = new Response(bin, { headers: { 'Content-Type': r.data.type || 'application/octet-stream' } });
  await c.put(req, res.clone());
  return res;
}

self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.hostname.endsWith('google.com') || u.hostname.endsWith('googleusercontent.com')) return;
  const m = u.pathname.match(/\/_blob\/([0-9a-f]{32})/);
  if (m) { e.respondWith(asset(new Request(u.origin + u.pathname), m[1]).catch(() => new Response('Offline', { status: 503 }))); return; }
  e.respondWith(fetch(e.request).then(r => {
    if (r.ok || r.type === 'opaque') { const c = r.clone(); caches.open(CACHE).then(x => x.put(e.request, c)); }
    return r;
  }).catch(() => caches.match(e.request, { ignoreSearch: true })));
});
