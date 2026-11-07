import json, re, csv, collections, time
from mktlib import pm_search, pm_event

NAME={'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado',
 'CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois',
 'IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland',
 'MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana',
 'NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York',
 'NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania',
 'RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah',
 'VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming',
 'DC':'District of Columbia'}

rows=list(csv.DictReader(open('/Users/hudsonisonline/Desktop/Datasets/all_polls_2026.csv')))
need=collections.Counter()
for r in rows:
    if r['race_stage'] not in ('General','Special general'): continue
    need[(r['office'], r['state_po'], r['district'], r['cycle'])]+=1

def queries(off, st, dist):
    n=NAME.get(st, st)
    if off=='Senate':   return [f"{n} Senate Election Winner", f"{n} Senate 2026"]
    if off=='Governor': return [f"{n} Governor Election Winner", f"{n} Gubernatorial Election Winner"]
    if off=='House' and dist: return [f"{st}-{dist} House Election Winner", f"{n} {dist} congressional district 2026"]
    return []

def ok_event(e, off, st, dist, cycle):
    slug=str(e.get('slug') or '').lower(); title=str(e.get('title') or '').lower()
    blob=slug+' '+title
    if 'winner' not in blob: return False
    for bad in ['margin','turnout','primary','nominee','nomination','first-round','recount','runoff','combo']:
        if bad in blob: return False
    n=NAME.get(st,st).lower()
    if off=='Senate':
        if 'senate' not in blob or n not in blob: return False
    elif off=='Governor':
        if not re.search(r'governor|gubernatorial', blob) or n not in blob: return False
    elif off=='House':
        if not re.search(rf'\b{st.lower()}[- ]0?{dist}\b', blob) and not (n in blob and re.search(rf'\b0?{dist}(st|nd|rd|th)?\b', blob)):
            return False
    else: return False
    # markets must carry party-tagged candidate legs
    legs=[m for m in (e.get('markets') or []) if re.search(r'\((D|R)\)\s*$', str(m.get('groupItemTitle') or ''))]
    return len(legs)>=1

inv=[]; checked=0; hits=0; noevent=[]
targets=sorted(need, key=lambda k:-need[k])
for (off,st,dist,cyc) in targets:
    if off=='Generic ballot': continue
    if off=='House' and not dist: continue
    try: cycle=int(cyc)
    except Exception: continue
    found=None
    for q in queries(off,st,dist):
        for e in pm_search(q, limit=12):
            slug=e.get('slug')
            if not slug: continue
            full=pm_event(slug)
            if not full: continue
            if ok_event(full, off, st, dist, cycle):
                found=full; break
        if found: break
    checked+=1
    if found:
        hits+=1
        for m in (found.get('markets') or []):
            git=str(m.get('groupItemTitle') or '')
            pm=re.search(r'\((D|R)\)\s*$', git)
            if not pm: continue
            try: toks=json.loads(m.get('clobTokenIds') or '[]')
            except Exception: toks=[]
            if not toks: continue
            inv.append(dict(office=off, state_po=st, district=dist, cycle=cycle,
                            event_slug=found.get('slug'), event_title=found.get('title'),
                            market_id=m.get('id'), candidate=re.sub(r'\s*\((D|R)\)\s*$','',git),
                            party=pm.group(1), yes_token=toks[0],
                            outcome_price=(json.loads(m.get('outcomePrices') or '[]') or [None])[0],
                            n_poll_rows=need[(off,st,dist,cyc)]))
        print('  HIT  %-8s %-3s %-4s -> %s' % (off,st,dist,found.get('slug'))[:110], flush=True)
    else:
        noevent.append((off,st,dist,need[(off,st,dist,cyc)]))
    if checked%20==0: print('   ...%d/%d checked, %d hits' % (checked,len(targets),hits), flush=True)

# national chamber-control events, used for the generic ballot
for slug,label in [('which-party-will-win-the-house-in-2026','House control'),
                   ('which-party-will-win-the-senate-in-2026','Senate control')]:
    e=pm_event(slug)
    for m in (e.get('markets') or []):
        git=str(m.get('groupItemTitle') or '')
        p='D' if re.search(r'democrat', git, re.I) else ('R' if re.search(r'republican', git, re.I) else None)
        if not p: continue
        try: toks=json.loads(m.get('clobTokenIds') or '[]')
        except Exception: toks=[]
        if not toks: continue
        inv.append(dict(office='Generic ballot', state_po='US', district='', cycle=2026,
                        event_slug=slug, event_title=e.get('title'), market_id=m.get('id'),
                        candidate=git, party=p, yes_token=toks[0],
                        outcome_price=(json.loads(m.get('outcomePrices') or '[]') or [None])[0],
                        n_poll_rows=0, note=label))
    print('  NATIONAL %-44s legs now %d' % (slug, len(inv)), flush=True)

races={(x['office'],x['state_po'],x['district'],x['cycle']) for x in inv}
print()
print('Polymarket races matched: %d  (legs: %d)' % (len(races), len(inv)))
for o in ['Senate','Governor','House','Generic ballot']:
    print('   %-16s %d races' % (o, len({k for k in races if k[0]==o})))
print()
print('biggest races with NO Polymarket event:')
for off,st,dist,n in sorted(noevent, key=lambda x:-x[3])[:12]: print('   %-9s %-3s %-4s %d rows' % (off,st,dist,n))
json.dump(inv, open('raw/mkt/pm_inventory.json','w'), indent=1)
