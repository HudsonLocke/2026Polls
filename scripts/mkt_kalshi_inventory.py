import json, re, csv, collections, time
from mktlib import kalshi_markets, FetchError

PO={'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
    'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
    'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC'}
# a market belongs to an election if it closes just after that election day
WINDOWS={2026:('2026-11-03','2026-12-31'), 2025:('2025-11-04','2025-12-31')}

rows=list(csv.DictReader(open('/Users/hudsonisonline/Desktop/Datasets/all_polls_2026.csv')))
need=collections.Counter()
for r in rows:
    if r['race_stage'] not in ('General','Special general'): continue
    need[(r['office'], r['state_po'], r['district'], r['cycle'])]+=1

series=sorted({s['ticker'] for s in json.load(open('raw/mkt/kalshi_series.json'))['series']})
cands=collections.defaultdict(set)
for t in series:
    # Senate, incl. special-election series (trailing S)
    m=re.match(r'^(KX)?SENATE(PARTY)?([A-Z]{2})(S?)$', t)
    if m and m.group(3) in PO: cands[('Senate', m.group(3), '')].add(t); continue
    m=re.match(r'^(KX)?GOV(PARTY)?([A-Z]{2})(S?)$', t)
    if m and m.group(3) in PO: cands[('Governor', m.group(3), '')].add(t); continue
    m=re.match(r'^(KX)?HOUSE([A-Z]{2})(\d{2}|AL)$', t)
    if m and m.group(2) in PO:
        d='AL' if m.group(3)=='AL' else str(int(m.group(3)))
        cands[('House', m.group(2), d)].add(t); continue

wanted=set()
for (off,st,dist,cyc) in need:
    for k in ([(off,st,dist)] + ([(off,st,'AL'),(off,st,'1')] if off=='House' else [])):
        wanted |= cands.get(k,set())
print('series to fetch:', len(wanted), flush=True)

fetched={}; failed=[]
for i,s in enumerate(sorted(wanted),1):
    for attempt in range(3):
        try: fetched[s]=kalshi_markets(s); break
        except FetchError as e:
            if attempt==2: failed.append((s,str(e)))
            else: time.sleep(3*(attempt+1))
    if i%40==0: print('   %d/%d (failures %d)' % (i,len(wanted),len(failed)), flush=True)
print('fetched:', len(fetched), '| FAILED:', len(failed), flush=True)
for s,e in failed: print('   FAIL', s, e)

inv=[]
for (off,st,dist,cyc) in need:
    try: cycle=int(cyc)
    except Exception: continue
    if cycle not in WINDOWS: continue
    lo,hi=WINDOWS[cycle]
    if off=='House' and not dist: continue   # statewide House polling is not a district race
    ss=set()
    for k in ([(off,st,dist)] + ([(off,st,'AL')] if off=='House' and dist in ('1','AL') else [])):
        ss |= cands.get(k,set())
    for s in sorted(ss):
        for m in fetched.get(s) or []:
            tk=m.get('ticker','')
            mm=re.match(r'^(.+)-(\w+)-(D|R)$', tk)
            if not mm: continue
            ct=str(m.get('close_time'))[:10]
            # Two independent signals, because neither alone is sound. Some markets are
            # tickered by the TERM year, not the election year (GOVPARTYNH-28 closed
            # 2026-11-04), and some 2026 markets have a close_time a year out
            # (SENATEAK-26 closes 2027-11-03). Accept on either, but never accept a
            # market tickered for a later cycle.
            cyc_tag=mm.group(2)
            tag_ok = cyc_tag == str(cycle)[-2:]
            win_ok = lo <= ct <= hi
            later  = re.fullmatch(r'\d{2}', cyc_tag or '') and int(cyc_tag) > int(str(cycle)[-2:])
            if later or not (tag_ok or win_ok): continue
            inv.append(dict(office=off, state_po=st, district=dist, cycle=cycle, series=s, ticker=tk,
                            party=mm.group(3), subtitle=(m.get('yes_sub_title') or ''),
                            result=m.get('result') or '', close_time=ct, n_poll_rows=need[(off,st,dist,cyc)]))

# drop duplicate legs (a race matched by two series) keeping the resolved one
best={}
for x in inv:
    k=(x['office'],x['state_po'],x['district'],x['cycle'],x['party'])
    cur=best.get(k)
    if cur is None or (not cur['result'] and x['result']): best[k]=x
inv=list(best.values())

races={(x['office'],x['state_po'],x['district'],x['cycle']) for x in inv}
legs=collections.Counter((x['office'],x['state_po'],x['district'],x['cycle']) for x in inv)
print()
print('races with a Kalshi market: %d of %d  (legs: %d)' % (len(races), len(need), len(inv)))
print('races with both D and R legs:', sum(1 for v in legs.values() if v>=2))
for o in ['Senate','Governor','House']:
    print('   %-10s %d races' % (o, len({k for k in races if k[0]==o})))
print('resolved legs:', sum(1 for x in inv if x['result']))
json.dump(sorted(inv, key=lambda x:(x['office'],x['state_po'],x['district'],x['party'])),
          open('raw/mkt/kalshi_inventory.json','w'), indent=1)
