"""Rebuild an installable app page on this site from its Claude dashboard.
usage: python3 tools/build_app.py <app> <saved artifact index.html>
apps: europe, bdm, laura, farm, peptide, family, hockey. Writes <app>.html in the repo root.
Only the page is rebuilt; manifests, icons, claude-shim.js and the service workers stay as they are.
Used by the scheduled "Apps auto-update" task."""
import sys, re, os
APPS = {"europe": "Europe", "bdm": "BDM", "laura": "Laura's Desk", "farm": "Home Paddock", "peptide": "Peptides", "family": "Family"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def generic(s, app, short):
    s = s[s.index('<body>') + len('<body>'):]
    s = s.replace('<meta name="claude:viewport-fit-sides" content="cover">', '')
    s = re.sub(r'</body>\s*</html>\s*$', '', s.rstrip())
    s = re.sub(r'^\s*<!doctype html>\s*<html[^>]*>\s*<head>', '', s, flags=re.I)
    s = re.sub(r'</head>\s*<body[^>]*>', '', s, count=1, flags=re.I)
    s = re.sub(r'(?<=["\'(=\s])/_blob/', '_blob/', s)
    # Contacts only used by connector features (which need Claude) stay out of the public copy
    s = s.replace('jess@jessdensley.com', '')
    s = re.sub(r'FIN_SHARE=\[[^\]]*\]', 'FIN_SHARE=[]', s)
    s = re.sub(r'<link rel="(?:icon|apple-touch-icon)"[^>]*_blob/[^>]*>', '', s)
    head = ('''<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="{{SHORT}}">
<link rel="manifest" href="{{APP}}.webmanifest">
<link rel="icon" type="image/png" href="{{APP}}-icon-192.png">
<link rel="apple-touch-icon" href="{{APP}}-icon-180.png">
<style>:root{box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}html{scroll-padding-top:env(safe-area-inset-top,0px)}body{margin:0;padding:0}img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}</style>
<script>window.ANNETT_APP="{{APP}}";
/* A photo or document not yet copied to Drive hides itself instead of showing broken. */
addEventListener('error',function(e){var t=e.target;if(t&&t.tagName==='IMG'&&/_blob\\//.test(t.src)){var f=t.closest('figure,.shot');(f||t).style.display='none';}},true);</script>
<script src="claude-shim.js"></script>
</head>
<body>
''').replace('{{SHORT}}', short).replace('{{APP}}', app)
    return head + s + '\n</body>\n</html>\n'

HOCKEY_HEAD = r'''<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Tactics Board</title>
<meta name="theme-color" content="#0c1522">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Tactics">
<link rel="manifest" href="hockey.webmanifest">
<link rel="icon" type="image/png" href="hockey-icon-192.png">
<link rel="apple-touch-icon" href="hockey-icon-180.png">
<style>
html,body{margin:0;padding:0}
:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px);box-sizing:border-box}
#syncpill{font:600 .75rem system-ui,sans-serif;letter-spacing:.04em;border:1px solid #2b3e60;border-radius:999px;padding:6px 10px;min-height:32px;color:#93a4c2;background:#15223a}
#syncpill[data-s="ok"]{color:#4be3a0;border-color:#2a6b52}
#syncpill[data-s="err"]{color:#ff8a8a;border-color:#7a2f35}
#syncpill[data-s="busy"]{color:#ffd23f}
</style>
</head>
<body>
'''
HOCKEY_SYNC = r'''
<script>
/* ---------- Sync across devices (Google Drive via Apps Script) ---------- */
(function(){
  const APP='hockey', KEYS=['hb-boards','hb-names','hb-plays'], META='hb-sync';
  const meta=()=>{try{return JSON.parse(localStorage.getItem(META))||{}}catch(e){return{}}};
  const setMeta=m=>{try{localStorage.setItem(META,JSON.stringify(m))}catch(e){}};
  // One-tap setup link: hockey.html#sync=<url>&key=<key>
  if(location.hash.includes('sync=')){
    const p=new URLSearchParams(location.hash.slice(1)),m=meta();
    m.url=p.get('sync');m.key=p.get('key');m.updated=0;setMeta(m);
    history.replaceState(null,'',location.pathname);
  }
  const pill=document.createElement('button');pill.id='syncpill';
  document.getElementById('top').appendChild(pill);
  const show=(s,t)=>{pill.dataset.s=s;pill.textContent=t};
  const on=()=>{const m=meta();return m.url&&m.key};
  show(on()?'busy':'off',on()?'Syncing…':'Sync off');

  // Mark local changes so they get pushed
  let pushT=null, applying=false;
  const origSet=store.set;
  store.set=function(k,v){origSet(k,v);if(!applying&&KEYS.includes(k)){const m=meta();m.updated=Date.now();setMeta(m);schedule()}};
  function schedule(){if(!on())return;clearTimeout(pushT);show('busy','Saving…');pushT=setTimeout(push,1500)}
  const bundle=()=>{const d={};KEYS.forEach(k=>{d[k]=localStorage.getItem(k)});return d};

  function apply(r){
    applying=true;
    Object.entries(r.data||{}).forEach(([k,v])=>{try{v==null?localStorage.removeItem(k):localStorage.setItem(k,v)}catch(e){}});
    applying=false;
    const m=meta();m.updated=r.updated;setMeta(m);
    location.reload();
  }
  async function push(){
    const m=meta();if(!on())return;
    try{
      const res=await fetch(m.url,{method:'POST',headers:{'Content-Type':'text/plain'},body:JSON.stringify({k:m.key,app:APP,updated:m.updated||Date.now(),data:bundle()})});
      const r=await res.json();
      if(!r.ok)throw new Error(r.error);
      if(r.stale){apply(r);return}
      show('ok','Synced');
    }catch(e){show('err',navigator.onLine?'Sync error':'Offline')}
  }
  async function pull(){
    const m=meta();if(!on())return;
    try{
      const res=await fetch(m.url+(m.url.includes('?')?'&':'?')+'app='+APP+'&k='+encodeURIComponent(m.key));
      const r=await res.json();
      if(!r.ok)throw new Error(r.error);
      if(r.data&&r.updated>(m.updated||0)){apply(r);return}
      if((m.updated||0)>r.updated||!r.data){await push();return}
      show('ok','Synced');
    }catch(e){show('err',e.message==='bad key'?'Wrong key':navigator.onLine?'Sync error':'Offline')}
  }
  pull();
  document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')pull()});
  addEventListener('online',pull);
  setInterval(()=>{if(document.visibilityState==='visible'&&!document.querySelector('.sheet:not([hidden])'))pull()},60000);

  pill.onclick=()=>{
    const m=meta();
    openSheet(`<h2>Sync</h2><p class="empty" style="margin:0">Keeps your boards, squad and plays the same on every device. Paste the link and key from your setup once per device.</p>
      <input id="sy-url" placeholder="Sync link (https://script.google.com/…)" value="${esc(m.url||'')}">
      <input id="sy-key" placeholder="Key" value="${esc(m.key||'')}">
      <div class="row"><button class="ghost" id="x-no">Cancel</button><button class="primary" id="sy-ok">Save &amp; sync</button></div>`);
    document.getElementById('x-no').onclick=closeSheet;
    document.getElementById('sy-ok').onclick=()=>{const n=meta();n.url=document.getElementById('sy-url').value.trim();n.key=document.getElementById('sy-key').value.trim();setMeta(n);closeSheet();show('busy','Syncing…');pull()};
  };
})();

/* ---------- Offline support ---------- */
if('serviceWorker' in navigator)navigator.serviceWorker.register('hockey-sw.js',{scope:'./hockey'}).catch(()=>{});
</script>
'''

def hockey(src):
    body = src[src.index('<title>'):]
    body = re.sub(r'<title>[^<]*</title>\s*', '', body, count=1)
    body = body.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
    body = re.sub(r'</body>\s*</html>\s*$', '', body.rstrip())
    html = HOCKEY_HEAD + body.rstrip() + '\n' + HOCKEY_SYNC + '</body>\n</html>\n'
    return html.replace("`“${name}” is in Open on this device.`", "`“${name}” is saved in Open.`")

if __name__ == '__main__':
    app, src = sys.argv[1], sys.argv[2]
    s = open(src, encoding='utf8').read()
    html = hockey(s) if app == 'hockey' else generic(s, app, APPS[app])
    out = os.path.join(ROOT, app + '.html')
    open(out, 'w', encoding='utf8').write(html)
    print(out, len(html))
