/* Annett Apps runtime: stands in for Claude's in-page features outside Claude.
   - db: a Firestore-like document store kept on this device and synced to
     Google Drive through the Annett Apps sync script.
   - user, assets, downloads: simple local versions.
   - sample (ask Claude) and mcp (connectors) are not available outside Claude,
     so pages hide those features.
   Usage: <script>window.ANNETT_APP='europe'</script><script src="claude-shim.js"></script> */
(function () {
  const APP = window.ANNETT_APP || 'app';
  const LS = 'annett-' + APP + '-db', META = 'annett-sync';
  const now = () => Date.now();
  const read = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) || d; } catch (e) { return d; } };
  const write = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } };

  // ---------- sync settings (shared by all apps on this site) ----------
  if (location.hash.includes('sync=')) {
    const p = new URLSearchParams(location.hash.slice(1)), m = read(META, {});
    m.url = p.get('sync'); m.key = p.get('key'); write(META, m);
    history.replaceState(null, '', location.pathname + location.search);
  }
  const syncCfg = () => read(META, {});
  const shareCfg = () => { const c = syncCfg(); if (c.url && 'caches' in window) caches.open('annett-config').then(x => x.put('config', new Response(JSON.stringify({ url: c.url, key: c.key })))).catch(() => {}); };
  shareCfg();

  // ---------- store: { docs: { path: { d: data|null, t: time } }, updated } ----------
  let S = read(LS, { docs: {}, updated: 0 });
  const listeners = new Set();
  const save = () => { if (!write(LS, S)) console.warn('Storage full'); };
  const emit = () => { listeners.forEach(fn => { try { fn(); } catch (e) { console.error(e); } }); };
  const clone = o => o == null ? o : JSON.parse(JSON.stringify(o));
  const segs = p => String(p).split('/').filter(Boolean);
  const rid = () => Math.random().toString(36).slice(2, 10) + now().toString(36);

  function setDoc(path, data) {
    S.docs[path] = { d: data == null ? null : clone(data), t: now() };
    S.updated = now(); save(); emit(); schedulePush();
  }
  function merge(a, b) {
    const o = Object.assign({}, a);
    for (const k in b) {
      const v = b[k];
      if (v && typeof v === 'object' && !Array.isArray(v) && o[k] && typeof o[k] === 'object' && !Array.isArray(o[k])) o[k] = merge(o[k], v);
      else o[k] = v;
    }
    return o;
  }
  const snap = (path) => {
    const e = S.docs[path], ok = !!(e && e.d);
    return { id: segs(path).pop(), exists: ok, data: () => ok ? clone(e.d) : undefined, metadata: { fromCache: false, hasPendingWrites: false } };
  };
  function cmp(a, op, b) {
    switch (op) {
      case '==': return a === b; case '!=': return a !== b;
      case '<': return a < b; case '<=': return a <= b; case '>': return a > b; case '>=': return a >= b;
      case 'in': return (b || []).includes(a); case 'not-in': return !(b || []).includes(a);
      case 'array-contains': return Array.isArray(a) && a.includes(b);
    }
    return false;
  }
  function makeQuery(cpath, q) {
    q = q || { where: [], order: null, lim: 0 };
    const run = () => {
      const n = segs(cpath).length + 1, pre = cpath + '/';
      let docs = Object.keys(S.docs).filter(p => p.startsWith(pre) && segs(p).length === n && S.docs[p].d);
      docs = docs.filter(p => q.where.every(([f, op, v]) => cmp(S.docs[p].d[f], op, v)));
      if (q.order) {
        const [f, dir] = q.order, s = dir === 'desc' ? -1 : 1;
        docs.sort((a, b) => { const x = S.docs[a].d[f], y = S.docs[b].d[f];
          if (x === undefined) return 1; if (y === undefined) return -1; return x < y ? -s : x > y ? s : 0; });
      } else docs.sort();
      if (q.lim) docs = docs.slice(0, q.lim);
      const list = docs.map(snap);
      let prev = [];
      return { docs: list, size: list.length, empty: !list.length, metadata: { fromCache: false, hasPendingWrites: false },
        docChanges: () => list.map((d, i) => ({ type: 'added', doc: d, oldIndex: -1, newIndex: i })) };
    };
    const api = {
      path: cpath,
      where: (f, op, v) => makeQuery(cpath, Object.assign({}, q, { where: q.where.concat([[f, op, v]]) })),
      orderBy: (f, dir) => makeQuery(cpath, Object.assign({}, q, { order: [f, dir || 'asc'] })),
      limit: n => makeQuery(cpath, Object.assign({}, q, { lim: n })),
      get: async () => run(),
      onSnapshot(next) {
        let last = '';
        const fire = () => { const r = run(); const sig = JSON.stringify(r.docs.map(d => [d.id, S.docs[cpath + '/' + d.id].t]));
          if (sig !== last) { last = sig; next(r); } };
        listeners.add(fire); setTimeout(fire, 0);
        return () => listeners.delete(fire);
      },
      doc: id => docRef(cpath + '/' + (id || rid())),
      add: async data => { const r = docRef(cpath + '/' + rid()); await r.set(data); return r; },
    };
    return api;
  }
  function docRef(path) {
    return {
      id: segs(path).pop(), path,
      get: async () => snap(path),
      set: async data => setDoc(path, data),
      update: async data => { const e = S.docs[path]; if (!e || !e.d) throw { code: 'invalid_argument', message: 'Document does not exist' }; setDoc(path, merge(e.d, data)); },
      delete: async () => setDoc(path, null),
      acquire: async () => ({ acquired: true }),
      onSnapshot(next) {
        let last = -1;
        const fire = () => { const e = S.docs[path], t = e ? e.t : 0; if (t !== last) { last = t; next(snap(path)); } };
        listeners.add(fire); setTimeout(fire, 0);
        return () => listeners.delete(fire);
      },
      collection: sub => makeQuery(path + '/' + sub),
    };
  }
  const db = { doc: docRef, collection: p => makeQuery(p) };

  // ---------- one-time imports from the Claude version ----------
  // #seed=<base64url(gzip(json store))>   #assets=<base64url(gzip(json {id:{type,b64}}))>
  const unpack = async h => {
    const b = h.replace(/-/g, '+').replace(/_/g, '/');
    const bin = Uint8Array.from(atob(b), c => c.charCodeAt(0));
    return JSON.parse(await new Response(new Blob([bin]).stream().pipeThrough(new DecompressionStream('gzip'))).text());
  };
  window.annettImport = (async () => {
    const h = location.hash;
    if (!h.startsWith('#seed=') && !h.startsWith('#assets=')) return null;
    history.replaceState(null, '', location.pathname + location.search);
    try {
      if (h.startsWith('#seed=')) {
        const seed = await unpack(h.slice(6));
        let n = 0;
        for (const p in seed.docs) if (!S.docs[p]) { S.docs[p] = seed.docs[p]; n++; }
        S.updated = now(); save(); emit();
        await sync();
        return { seeded: n, total: Object.keys(seed.docs).length };
      }
      const list = await unpack(h.slice(8)), done = [];
      for (const id in list) {
        const a = list[id], bin = Uint8Array.from(atob(a.b64), c => c.charCodeAt(0));
        await putAsset(id, new Blob([bin], { type: a.type }));
        done.push(id);
      }
      return { assets: done.length };
    } catch (e) { console.error('Import failed', e); return { error: String(e) }; }
  })();

  // ---------- Google Drive sync (whole store, merged per document) ----------
  let pushT = null, busy = false, lastOk = 0;
  const status = s => { window.dispatchEvent(new CustomEvent('annett-sync', { detail: s })); };
  function schedulePush() { clearTimeout(pushT); pushT = setTimeout(sync, 1500); }
  function mergeRemote(remote) {
    let changed = false;
    for (const p in (remote && remote.docs) || {}) {
      const r = remote.docs[p], l = S.docs[p];
      if (!l || r.t > l.t) { S.docs[p] = r; changed = true; }
    }
    return changed;
  }
  // Every request gives up after a while, so a sync interrupted by the app being put
  // away (common on iPhone/iPad) can never leave syncing stuck.
  function fetchT(u, opts, ms) {
    const c = new AbortController(), t = setTimeout(() => c.abort(), ms);
    return fetch(u, Object.assign({ signal: c.signal, cache: 'no-store' }, opts || {})).finally(() => clearTimeout(t));
  }
  let busySince = 0, again = false;
  async function sync() {
    const c = syncCfg(); if (!c.url || !c.key) return;
    if (busy && now() - busySince < 150000) { again = true; return; }
    busy = true; busySince = now(); again = false; status('busy');
    try {
      for (let round = 0; round < 3; round++) {
        const g = await fetchT(c.url + '?app=' + APP + '&k=' + encodeURIComponent(c.key), null, 45000).then(r => r.json());
        if (!g.ok) throw new Error(g.error);
        const changed = mergeRemote(g.data);
        const needPush = !g.data || Object.keys(S.docs).some(p => !g.data.docs[p] || S.docs[p].t > g.data.docs[p].t);
        if (changed) { save(); emit(); }
        if (!needPush) break;
        const body = JSON.stringify({ k: c.key, app: APP, updated: Math.max(now(), (g.updated || 0) + 1), data: S });
        const r = await fetchT(c.url, { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body }, 120000).then(r => r.json());
        if (!r.ok) throw new Error(r.error);
        if (!r.stale) break;
        if (mergeRemote(r.data)) { save(); emit(); }
      }
      lastOk = now(); status('ok');
    } catch (e) { status(e.message === 'bad key' ? 'badkey' : navigator.onLine ? 'error' : 'offline'); }
    busy = false;
    if (again) setTimeout(sync, 500);
  }
  setTimeout(sync, 300);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') sync(); });
  addEventListener('online', sync);
  addEventListener('focus', sync);
  addEventListener('pageshow', sync);
  setInterval(() => { if (document.visibilityState === 'visible') sync(); }, 60000);

  // ---------- other capabilities ----------
  const user = {
    id: async () => 'tim', me: async () => ({ id: 'tim', name: '' }),
    isOwner: async () => true, canEdit: async () => true, can: async () => true,
    profiles: async ids => Object.fromEntries((ids || []).map(i => [i, { id: i, name: '' }])),
    search: async () => [],
  };
  // Photos/documents: kept in this device's cache and saved to Drive as their own small records.
  const hex = () => Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, '0')).join('');
  const assetPath = id => new URL('_blob/' + id, location.href).href;
  async function putAsset(id, blob) {
    try { await (await caches.open('annett-assets')).put(assetPath(id), new Response(blob, { headers: { 'Content-Type': blob.type || 'application/octet-stream' } })); } catch (e) {}
    const c = syncCfg(); if (!c.url) return;
    const b64 = await new Promise(r => { const fr = new FileReader(); fr.onload = () => r(String(fr.result).split(',')[1]); fr.readAsDataURL(blob); });
    try { const r = await fetch(c.url, { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: JSON.stringify({ k: c.key, app: 'a-' + id.slice(0, 24), updated: now(), data: { type: blob.type, b64 } }) }).then(r => r.json()); if (!r.ok) throw new Error(r.error); } catch (e) { console.error('Asset upload failed', id, e); throw e; }
  }
  const assets = {
    upload: async blob => { const id = hex(); await putAsset(id, blob); return { id, url: '_blob/' + id, sizeBytes: blob.size, contentType: blob.type }; },
    list: async () => ({ assets: [], usage: {} }),
    delete: async () => {},
  };
  const downloads = {
    save: async ({ filename, data }) => {
      const b = data instanceof Blob ? data : new Blob([data]);
      const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = filename || 'download';
      document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    },
  };
  const caps = { db, user, assets, downloads };
  window.claude = { use: async name => caps[name] || null };
  window.annettSync = { now: sync, config: syncCfg, lastOk: () => lastOk,
    set(url, key) { const m = read(META, {}); m.url = url; m.key = key; write(META, m); shareCfg(); sync(); } };

  // ---------- offline + install ----------
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});

  // ---------- small sync badge ----------
  addEventListener('DOMContentLoaded', () => {
    const b = document.createElement('button');
    b.id = 'annett-sync-badge';
    b.style.cssText = 'position:fixed;right:10px;bottom:calc(84px + env(safe-area-inset-bottom,0px));transition:opacity .4s;z-index:99999;font:600 11px system-ui,sans-serif;border-radius:999px;padding:6px 10px;border:1px solid rgba(0,0,0,.15);background:rgba(255,255,255,.92);color:#555;box-shadow:0 2px 8px rgba(0,0,0,.12);cursor:pointer';
    const set = s => { const m = { busy: ['Syncing…', '#8a6d00'], ok: ['Synced', '#16794a'], error: ['Sync error · tap to retry', '#b42318'], offline: ['Offline', '#666'], badkey: ['Wrong key', '#b42318'], off: ['Sync off', '#666'] }[s] || ['', '#666'];
      b.textContent = m[0]; b.style.color = m[1]; b.dataset.s = s;
      clearTimeout(b._t); b.style.opacity = 1; b.style.pointerEvents = 'auto';
      if (s === 'ok') b._t = setTimeout(() => { b.style.opacity = 0; b.style.pointerEvents = 'none'; }, 2500); };
    set(syncCfg().url ? 'busy' : 'off');
    addEventListener('annett-sync', e => set(e.detail));
    // Tap: sync now (or set up sync if it isn't yet). Press and hold: change the sync link or key.
    const ask = () => {
      const c = syncCfg();
      const url = prompt('Sync link (from your setup):', c.url || ''); if (url == null) return;
      const key = prompt('Sync key:', c.key || ''); if (key == null) return;
      window.annettSync.set(url.trim(), key.trim());
    };
    let held = false, holdT = null;
    b.addEventListener('pointerdown', () => { held = false; holdT = setTimeout(() => { held = true; ask(); }, 900); });
    ['pointerup', 'pointerleave', 'pointercancel'].forEach(ev => b.addEventListener(ev, () => clearTimeout(holdT)));
    b.onclick = () => {
      if (held) { held = false; return; }
      const c = syncCfg();
      if (c.url && c.key && b.dataset.s !== 'badkey') { set('busy'); sync(); } else ask();
    };
    document.body.appendChild(b);
  });
})();
