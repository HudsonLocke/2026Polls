import json, datetime, collections
from mktlib import kalshi_candles

START=int(datetime.datetime(2024,1,1).timestamp())
END  =int(datetime.datetime(2026,11,10).timestamp())

inv=json.load(open('raw/mkt/kalshi_inventory.json'))
out={}; empty=[]
for i,leg in enumerate(inv,1):
    tk=leg['ticker']
    try:
        cs=kalshi_candles(leg['series'], tk, START, END, 1440)
    except Exception as e:
        print('  ERR', tk, e, flush=True); cs=[]
    series={}
    for c in cs:
        ts=c.get('end_period_ts')
        if not ts: continue
        day=datetime.datetime.fromtimestamp(ts, datetime.UTC).date()
        pr=c.get('price') or {}
        v=pr.get('mean_dollars') or pr.get('close_dollars') or pr.get('previous_dollars')
        if v in (None,''): continue
        try: v=float(v)
        except Exception: continue
        if not (0.0 <= v <= 1.0): continue
        # candle period ends at 00:00 of the next day, so attribute it to the prior day
        series[(day - datetime.timedelta(days=1)).isoformat()]=round(v,4)
    out[tk]=series
    if not series: empty.append(tk)
    if i%20==0: print('  %d/%d legs (empty so far: %d)' % (i,len(inv),len(empty)), flush=True)

json.dump(out, open('raw/mkt/kalshi_history.json','w'))
days=[len(v) for v in out.values()]
print()
print('legs: %d | with data: %d | empty: %d' % (len(out), sum(1 for v in out.values() if v), len(empty)))
if days: print('daily points per leg: min %d med %d max %d' % (min(days), sorted(days)[len(days)//2], max(days)))
alld=sorted({d for v in out.values() for d in v})
if alld: print('date span:', alld[0], '->', alld[-1])
if empty: print('empty legs:', empty[:20])
