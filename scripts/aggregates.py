import csv, re, os
from bs4 import BeautifulSoup
from wikilib import page_html
from parse_wiki import expand, clean

OUT="/Users/hudsonisonline/Desktop/Datasets"
PAGES=["2026 United States House of Representatives elections",
       "2026 United States Senate elections",
       "2026 United States gubernatorial elections",
       "2026 United States elections"]
rows=[]
for p in PAGES:
    h=page_html(p)
    if not h: continue
    s=BeautifulSoup(h,'lxml')
    for ti,t in enumerate(s.find_all('table')):
        g=expand(t)
        if len(g)<2: continue
        hdr=[c[0] for c in g[0]]
        low=' | '.join(hdr).lower()
        if not re.search(r'aggregat|average', low): continue
        sec=t.find_previous(['h2','h3','h4'])
        sect=clean(sec.get_text(' ',strip=True)) if sec else ''
        for r in range(1,len(g)):
            vals=[c[0] for c in g[r]]
            if not any(vals): continue
            rec={'wiki_page':p,'section':sect,'table_index':ti}
            for c,hn in enumerate(hdr):
                hn=clean(hn) or f'col{c}'
                rec[hn]=clean(vals[c]) if c<len(vals) else ''
            rows.append(rec)
# dedupe: the same aggregate table is transcluded onto several hub pages
seen=set(); ded=[]
for r in rows:
    k=tuple(sorted((kk,vv) for kk,vv in r.items() if kk not in ('wiki_page','table_index')))
    if k in seen: continue
    seen.add(k); ded.append(r)
rows=ded
keys=['wiki_page','section','table_index']
for r in rows:
    for k in r:
        if k not in keys: keys.append(k)
with open(os.path.join(OUT,'polling_aggregates_final_2026.csv'),'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=keys, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
print('aggregate rows:', len(rows))
for r in rows[:14]: print('  ', {k:v for k,v in r.items() if v and k!='wiki_page'})
