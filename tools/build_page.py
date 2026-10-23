"""Turn a Claude artifact page (saved HTML) into the installable app page on this site.
usage: python3 tools/build_page.py <saved artifact html> <app id> "<short name>" <out.html>
Used by the scheduled "Europe app auto-update" task. Only the page is rebuilt;
the manifest, icons, claude-shim.js and sw.js stay as they are."""
import sys, re
src, app, short, out = sys.argv[1:5]
s = open(src, encoding='utf8').read()
s = s[s.index('<body>') + len('<body>'):]
s = s.replace('<meta name="claude:viewport-fit-sides" content="cover">', '')
s = re.sub(r'</body>\s*</html>\s*$', '', s.rstrip())
s = re.sub(r'^\s*<!doctype html>\s*<html[^>]*>\s*<head>', '', s, flags=re.I)
s = re.sub(r'</head>\s*<body[^>]*>', '', s, count=1, flags=re.I)
s = re.sub(r'(?<=["\'(=\s])/_blob/', '_blob/', s)
s = re.sub(r'<link rel="(?:icon|apple-touch-icon)"[^>]*_blob/[^>]*>', '', s)
head = f'''<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="{short}">
<link rel="manifest" href="{app}.webmanifest">
<link rel="icon" type="image/png" href="{app}-icon-192.png">
<link rel="apple-touch-icon" href="{app}-icon-180.png">
<style>:root{{box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}html{{scroll-padding-top:env(safe-area-inset-top,0px)}}body{{margin:0;padding:0}}img{{max-width:100%}}[hidden]:not([hidden=until-found i]){{display:none!important}}</style>
<script>window.ANNETT_APP={app!r};
/* A photo not yet copied to Drive hides itself instead of showing a broken image. */
addEventListener('error',function(e){{var t=e.target;if(t&&t.tagName==='IMG'&&/_blob\\//.test(t.src)){{var f=t.closest('figure,.shot');(f||t).style.display='none';}}}},true);</script>
<script src="claude-shim.js"></script>
</head>
<body>
'''
html = head + s + '\n</body>\n</html>\n'
open(out, 'w', encoding='utf8').write(html)
print(out, len(html))
