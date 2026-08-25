import re, os, sys
doc=open(sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),'argus-build-plan-v2.html')).read()
txt=re.sub(r'<[^>]+>',' ',doc[doc.index('</style>'):])
txt=re.sub(r'\s+',' ',txt)
bad=[]

def sec(name):
    i=doc.index(f'<section id="{name}"'); 
    nxt=[doc.index(f'<section id="{s}"') for s in SECS if doc.index(f'<section id="{s}"')>i]
    return doc[i:min(nxt)] if nxt else doc[i:]
SECS=re.findall(r'<section id="([a-z]+)"',doc)

# --- feature reconciliation ---
_k=sec('know')
_map=re.search(r'<table class="d map">.*?</table>', _k, re.S)
map_html=_map.group(0) if _map else ''
know=len(re.findall(r'<td class="nm">', _k.replace(map_html,'')))
brain_all=re.findall(r'<td class="nm">', sec('brain'))
# module-17 table is the last table in BRAIN ("The features this becomes")
b=sec('brain'); k=b.index('The features this becomes')
brain_feat=len(re.findall(r'<td class="nm">', b[k:]))
total=know+brain_feat
print(f"  KNOW features       : {know}")
print(f"  BRAIN module-17     : {brain_feat}")
print(f"  TOTAL               : {total}")
if total!=182: bad.append(f"feature total {total} != claimed 182")

# --- every claim of a headline number agrees with itself ---
pairs={
 '182':  r'182 features|182 feature',
 '24 modules': r'24 modules',
 '96':   r'96 engineer-weeks|96 wks|\b96\b',
 '1,020':r'\$1,020',
}
for label,pat in pairs.items():
    n=len(re.findall(pat,txt))
    print(f"  mentions of {label:<10}: {n}")
    if n==0: bad.append(f"no mention of {label}")

# --- phase weeks arithmetic ---
cost=sec('cost')
rows=re.findall(r'<tr><td class="nm">(\d) · [^<]+</td>.*?<td class="n mono">(\d+)\+?</td><td class="n mono">(\d+)\+?</td>', cost, re.S)
run=0
for ph,w,cum in rows:
    run+=int(w)
    flag='' if run==int(cum) else f'  <-- MISMATCH (running {run})'
    print(f"  phase {ph}: +{w:>2}wk  cum stated {cum:>3}{flag}")
    if run!=int(cum): bad.append(f"phase {ph} cumulative {cum} != running {run}")
if len(rows)!=8: bad.append(f"expected 8 phase rows, parsed {len(rows)}")

# --- v1 = 96 must equal phase 0..6 cumulative ---
if rows:
    v1=sum(int(w) for ph,w,_ in rows if int(ph)<=6)
    print(f"  phases 0-6 sum      : {v1} (doc claims 96 to v1)")
    if v1!=96: bad.append(f"phases 0-6 sum {v1} != 96")

# --- multiplier arithmetic: 96 * 1.6 .. 2.5 = 154..240 ---
lo,hi=round(96*1.6),round(96*2.5)
print(f"  96 x 1.6-2.5        : {lo}-{hi} (doc claims 154-240)")
if (lo,hi)!=(154,240): bad.append(f"multiplier range {lo}-{hi} != 154-240")
# 154/0.65 .. 240/0.65 in years
y1,y2=154/0.65/52, 240/0.65/52
print(f"  at 0.65 wk/wk       : {y1:.1f}-{y2:.1f} years (doc claims 4.5-7)")
if not (4.3<=y1<=4.7 and 6.8<=y2<=7.2): bad.append(f"year range {y1:.1f}-{y2:.1f} != 4.5-7")

# --- min slice: phase 0 + 1 = 26 ---
if rows:
    m=int(rows[0][1])+int(rows[1][1])
    print(f"  phase 0+1           : {m} (doc claims 26)")
    if m!=26: bad.append(f"phase0+1 {m} != 26")

# --- licence total ~1020 ---
print(f"  899 + 120           : {899+120} (doc claims ~$1,020)")

# --- every module 1..24 accounted for ---
mods=set()
for cell in re.findall(r'<td>(.*?)</td>', map_html, re.S):
    for m in re.findall(r'(\d+)(?:–(\d+))?\s*·', cell):
        a=int(m[0]); b2=int(m[1]) if m[1] else a
        mods.update(range(a,b2+1))
# map feature column must sum to 182
_fe=[int(x) for x in re.findall(r'<td class="n mono">(\d+)</td>', map_html)]
print(f"  map feature column  : {len(_fe)} rows summing {sum(_fe)}")
if sum(_fe)!=182: bad.append(f"module map features sum {sum(_fe)} != 182")
if len(_fe)!=14: bad.append(f"module map has {len(_fe)} rows, expected 14")
missing=sorted(set(range(1,25))-mods)
print(f"  modules referenced  : {len(mods)}  missing: {missing if missing else 'none'}")

print("="*64)
print(f"CROSSCHECK FAILS: {len(bad)}")
for b3 in bad: print("  ✗",b3)
sys.exit(1 if bad else 0)
