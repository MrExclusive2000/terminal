import re, os, sys
from html.parser import HTMLParser
from collections import Counter

doc = open(sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),'argus-build-plan-v2.html')).read()
fails, warns = [], []

VOID = {'br','hr','img','input','link','meta','area','base','col','embed',
        'source','track','wbr','param'}

# ---------- 1. tag nesting ----------
class P(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True); s.stack=[]; s.err=[]; s.ids=[]; s.hrefs=[]
    def handle_starttag(s,t,a):
        d=dict(a)
        if d.get('id'): s.ids.append(d['id'])
        if d.get('href','').startswith('#'): s.hrefs.append((d['href'][1:], s.getpos()[0]))
        if t not in VOID: s.stack.append((t,s.getpos()[0]))
    def handle_endtag(s,t):
        if t in VOID: return
        if not s.stack: s.err.append(f"line {s.getpos()[0]}: </{t}> with empty stack"); return
        if s.stack[-1][0]!=t:
            s.err.append(f"line {s.getpos()[0]}: </{t}> but innermost open is <{s.stack[-1][0]}> from line {s.stack[-1][1]}")
            for i in range(len(s.stack)-1,-1,-1):
                if s.stack[i][0]==t: del s.stack[i:]; return
            return
        s.stack.pop()
p=P(); p.feed(doc)
for e in p.err: fails.append("NESTING "+e)
for t,l in p.stack: fails.append(f"NESTING unclosed <{t}> opened line {l}")

# ---------- 2. duplicate ids ----------
for i,c in Counter(p.ids).items():
    if c>1: fails.append(f"DUPLICATE id '{i}' x{c}")

# ---------- 3. dangling anchors ----------
ids=set(p.ids)
for h,l in p.hrefs:
    if h and h not in ids: fails.append(f"DANGLING anchor #{h} (line {l})")

# ---------- 4. rail matches sections, in order ----------
rail=re.findall(r'<a href="#([a-z]+)"><code>', doc)
secs=re.findall(r'<section id="([a-z]+)"', doc)
if rail!=secs: fails.append(f"RAIL/SECTION mismatch\n   rail={rail}\n   secs={secs}")

# ---------- 5. forbidden wrappers ----------
for bad in ('<!doctype','<html','<head>','<body'):
    if bad in doc.lower(): fails.append(f"FORBIDDEN wrapper {bad}")

# ---------- 6. css var integrity ----------
used={m for m in re.findall(r'var\((--[a-z0-9-]+)', doc)}
style=doc[doc.index('<style>'):doc.index('</style>')]
defined={m for m in re.findall(r'(--[a-z0-9-]+)\s*:\s*[^;{]', style)}
for v in sorted(used-defined): fails.append(f"CSS undefined var {v}")
# dark-theme parity for colour tokens
def block(pat):
    m=re.search(pat, style)
    if not m: return set()
    i=m.end(); depth=1; j=i
    while depth and j<len(style):
        if style[j]=='{': depth+=1
        elif style[j]=='}': depth-=1
        j+=1
    return set(re.findall(r'(--[a-z0-9-]+)\s*:\s*[^;{]', style[i:j]))
root  = block(r':root\s*\{')
dark_m= block(r'@media \(prefers-color-scheme: dark\)\s*\{\s*:root:not\(\[data-theme="light"\]\)\s*\{')
dark_a= block(r':root\[data-theme="dark"\]\s*\{')
if dark_m and dark_a and dark_m!=dark_a:
    d=dark_m^dark_a
    fails.append(f"THEME dark media block and [data-theme=dark] differ: {sorted(d)}")
if not dark_m: warns.append("THEME no prefers-color-scheme dark block found")
if not dark_a: warns.append("THEME no [data-theme=dark] block found")

# ---------- 7. table column consistency ----------
for ti,tbl in enumerate(re.findall(r'<table[^>]*>(.*?)</table>', doc, re.S)):
    ths=re.search(r'<thead>(.*?)</thead>', tbl, re.S)
    if not ths: continue
    n=len(re.findall(r'<th', ths.group(1)))
    body=re.search(r'<tbody>(.*?)</tbody>', tbl, re.S)
    if not body: continue
    for ri,row in enumerate(re.findall(r'<tr>(.*?)</tr>', body.group(1), re.S)):
        c=len(re.findall(r'<t[dh][ >]', row))
        spans=sum(int(x)-1 for x in re.findall(r'colspan="(\d+)"', row))
        if c+spans!=n:
            fails.append(f"TABLE {ti} row {ri}: {c+spans} cells vs {n} headers — {re.sub(r'<[^>]+>','',row)[:60]}")

# ---------- 8. stale figures / contradictions ----------
body_txt = doc[doc.index('</style>'):]
_c = body_txt.find('An earlier draft claimed')
corr_lo, corr_hi = (_c, body_txt.find('</table>', _c)) if _c!=-1 else (-1,-1)
checks = [
 (r'\b209\b',            "stale feature count 209"),
 (r'v1\.0',              "stale version string v1.0"),
 (r'Ctrl</kbd>\+<kbd>Alt', "Ctrl+Alt binding (rejected)"),
 (r'\b3\.6M\b',          "stale insider row count 3.6M"),
 (r'268',                "stale feature count 268"),
]
for pat,msg in checks:
    hits=[m.start() for m in re.finditer(pat, body_txt)]
    for h in hits:
        ctx=re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',body_txt[max(0,h-90):h+90]))
        # allow explicit corrections which name the old value as wrong
        row_start = body_txt.rfind('<tr>', 0, h); row_end = body_txt.find('</tr>', h)
        row = body_txt[row_start:row_end] if row_start!=-1 else ''
        in_corrections = corr_lo < h < corr_hi
        if in_corrections or re.search(r'must not be|Broken on UK', ctx, re.I):
            warns.append(f"OK-in-context [{msg}]: …{ctx}…"); continue
        fails.append(f"STALE [{msg}]: …{ctx}…")

# ---------- 9. feature/module counts ----------
feat_rows = len(re.findall(r'<td class="nm">', doc[doc.index('<section id="know"'):doc.index('<section id="build"')]))
claimed = set(re.findall(r'(\d+) features', body_txt))
print(f"  KNOW+BRAIN nm rows: {feat_rows}; claims of 'N features': {sorted(claimed)}")

# ---------- 10. misc hygiene ----------
if doc.count('<title>')!=1: fails.append("TITLE count != 1")
if 'favicon' in doc.lower(): warns.append("favicon markup in body (should be a param)")
prose = re.sub(r'<[^>]+>', ' ', doc[doc.index('</style>'):])
for m in re.finditer(r'&(?!amp;|lt;|gt;|quot;|#\d+;|nbsp;|hellip;|mdash;|ndash;|times;|minus;)', prose):
    fails.append(f"RAW ampersand in prose: {prose[max(0,m.start()-50):m.start()+30]!r}")

print("="*64)
print(f"FAILS: {len(fails)}")
for f in fails: print("  ✗", f)
print(f"WARN : {len(warns)}")
for w in warns: print("  ·", w[:150])
sys.exit(1 if fails else 0)
