import json, datetime, collections
from mktlib import pm_history

inv=json.load(open('raw/mkt/pm_inventory.json'))
out={}; empty=[]
toks=sorted({x['yes_token'] for x in inv})
print('tokens to fetch:', len(toks), flush=True)
for i,tok in enumerate(toks,1):
    try: h=pm_history(tok)
    except Exception as e:
        print('  ERR', tok[:18], e, flush=True); h=[]
    # several intraday points can land on one day; keep the daily mean
    byday=collections.defaultdict(list)
    for pt in h:
        t=pt.get('t'); p=pt.get('p')
        if t is None or p is None: continue
        try: p=float(p)
        except Exception: continue
        if not (0.0 <= p <= 1.0): continue
        byday[datetime.datetime.fromtimestamp(t, datetime.UTC).date().isoformat()].append(p)
    series={d: round(sum(v)/len(v),4) for d,v in byday.items()}
    out[tok]=series
    if not series: empty.append(tok)
    if i%40==0: print('  %d/%d (empty so far %d)' % (i,len(toks),len(empty)), flush=True)

json.dump(out, open('raw/mkt/pm_history.json','w'))
ds=[len(v) for v in out.values()]
print()
print('tokens: %d | with data: %d | empty: %d' % (len(out), sum(1 for v in out.values() if v), len(empty)))
if ds: print('daily points per token: min %d med %d max %d' % (min(ds), sorted(ds)[len(ds)//2], max(ds)))
alld=sorted({d for v in out.values() for d in v})
if alld: print('date span:', alld[0], '->', alld[-1])
