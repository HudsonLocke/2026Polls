"""Attach Kalshi and Polymarket win probabilities to every poll, averaged over the
days the poll was in the field."""
import json, csv, os, datetime, collections

OUT="/Users/hudsonisonline/Desktop/Datasets"
k_inv=json.load(open('raw/mkt/kalshi_inventory.json'))
k_hist=json.load(open('raw/mkt/kalshi_history.json'))
p_inv=json.load(open('raw/mkt/pm_inventory.json'))
p_hist=json.load(open('raw/mkt/pm_history.json'))

def race_key(off, st, dist, cycle):
    return (off, st, str(dist or ''), str(cycle or ''))

# race -> party -> [(label, dailyseries)]
K=collections.defaultdict(lambda: collections.defaultdict(list))
for leg in k_inv:
    s=k_hist.get(leg['ticker']) or {}
    if s: K[race_key(leg['office'],leg['state_po'],leg['district'],leg['cycle'])][leg['party']].append((leg['ticker'], s))
GB_EVENT='which-party-will-win-the-house-in-2026'   # the generic ballot is a House vote
P=collections.defaultdict(lambda: collections.defaultdict(list))
for leg in p_inv:
    if leg['office']=='Generic ballot' and leg['event_slug']!=GB_EVENT:
        continue          # otherwise House-control and Senate-control legs get summed together
    s=p_hist.get(leg['yes_token']) or {}
    if s: P[race_key(leg['office'],leg['state_po'],leg['district'],leg['cycle'])][leg['party']].append((leg['event_slug'], s))

def days(a,b):
    try:
        d0=datetime.date.fromisoformat(a); d1=datetime.date.fromisoformat(b)
    except Exception: return []
    if d1<d0: d0,d1=d1,d0
    if (d1-d0).days>120: d0=d1-datetime.timedelta(days=120)
    return [(d0+datetime.timedelta(days=i)).isoformat() for i in range((d1-d0).days+1)]

def party_prob(legs, window):
    """Sum same-party legs per day (they are mutually exclusive outcomes), then average
    across the days of the window that have data."""
    if not legs: return None, 0, '', 0
    per_day={}
    for d in window:
        vals=[s[d] for _,s in legs if d in s]
        if len(vals)==len(legs): per_day[d]=sum(vals)
    if not per_day: return None, 0, '; '.join(sorted({l for l,_ in legs})), len(legs)
    return (round(sum(per_day.values())/len(per_day),4), len(per_day),
            '; '.join(sorted({l for l,_ in legs})), len(legs))

NEW=['kalshi_dem_prob','kalshi_rep_prob','kalshi_dem_minus_rep_pp','kalshi_dem_prob_norm',
     'kalshi_days_in_window','kalshi_market',
     'polymarket_dem_prob','polymarket_rep_prob','polymarket_dem_minus_rep_pp',
     'polymarket_dem_prob_norm','polymarket_days_in_window','polymarket_market','market_note']

def enrich(r):
    o={k:'' for k in NEW}
    off=r['office']; st=r['state_po']; dist=r['district']; cyc=r['cycle']
    if off=='Generic ballot':
        rk=race_key('Generic ballot','US','',2026)
    else:
        rk=race_key(off,st,dist,cyc)
    ed=r['end_date']; sd=r['start_date'] or ed
    if not ed:
        o['market_note']='no_poll_end_date'; return o
    if r['race_stage'] not in ('General','Special general'):
        o['market_note']='not_a_general_election_question'; return o
    window=days(sd,ed)
    notes=[]
    for tag, table in (('kalshi',K), ('polymarket',P)):
        legs=table.get(rk)
        if not legs:
            notes.append(f'no_{tag}_market_for_race'); continue
        d,dn,dl,dc=party_prob(legs.get('D'), window)
        rr,rn,rl,rc=party_prob(legs.get('R'), window)
        o[f'{tag}_market']='; '.join(sorted(set(filter(None,[dl,rl]))))
        o[f'{tag}_days_in_window']=max(dn,rn)
        if d is None and rr is None:
            notes.append(f'{tag}_market_had_no_prices_in_window'); continue
        if d is not None: o[f'{tag}_dem_prob']=d
        if rr is not None: o[f'{tag}_rep_prob']=rr
        if d is not None and rr is not None:
            o[f'{tag}_dem_minus_rep_pp']=round((d-rr)*100,2)
            if d+rr>0: o[f'{tag}_dem_prob_norm']=round(d/(d+rr),4)
            # Two separate binaries on one race can disagree when the market is thin:
            # Kalshi's FL-13 legs priced D 0.78 and R 0.74 at once. Flag it; use the
            # _norm column if you need something that sums to 1.
            if abs(d+rr-1.0) > 0.10: notes.append(f'{tag}_legs_sum_{round(d+rr,2)}')
        if max(dc,rc) > 1: notes.append(f'{tag}_party_prob_is_sum_of_{max(dc,rc)}_candidates')
    if off=='Generic ballot': notes.append('generic_ballot_uses_house_control_market')
    o['market_note']='; '.join(notes) if notes else 'ok'
    return o

FILES=['all_polls_2026.csv','senate_polls_2026.csv','governor_polls_2026.csv',
       'house_polls_2026.csv','generic_ballot_polls_2026.csv','poll_questions_2026.csv',
       'deduped/all_polls_2026_deduped.csv','deduped/senate_polls_2026_deduped.csv',
       'deduped/governor_polls_2026_deduped.csv','deduped/house_polls_2026_deduped.csv',
       'deduped/generic_ballot_polls_2026_deduped.csv','deduped/poll_questions_2026_deduped.csv']

stats=collections.Counter(); cov=collections.defaultdict(set)
for fn in FILES:
    path=os.path.join(OUT,fn)
    if not os.path.exists(path): print('MISSING', fn); continue
    rows=list(csv.DictReader(open(path)))
    if not rows: continue
    fields=[f for f in rows[0].keys() if f not in NEW]+NEW
    for r in rows:
        e=enrich(r)
        r.update(e)
        if fn=='all_polls_2026.csv':
            stats[e['market_note']]+=1
            if e['kalshi_dem_prob']!='': cov['kalshi'].add(r['question_id'])
            if e['polymarket_dem_prob']!='': cov['polymarket'].add(r['question_id'])
            if e['kalshi_dem_prob']!='' or e['polymarket_dem_prob']!='': cov['either'].add(r['question_id'])
            if r['race_stage'] in ('General','Special general'): cov['general_q'].add(r['question_id'])
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    print('  wrote %-52s %d rows, %d cols' % (fn, len(rows), len(fields)))

print()
print('market_note counts on all_polls_2026.csv:')
for k,v in stats.most_common(): print('   %-54s %d' % (k,v))
print()
g=len(cov['general_q'])
print('general-election questions: %d' % g)
print('   with Kalshi odds     : %d (%.0f%%)' % (len(cov['kalshi']), 100*len(cov['kalshi'])/g))
print('   with Polymarket odds : %d (%.0f%%)' % (len(cov['polymarket']), 100*len(cov['polymarket'])/g))
print('   with at least one    : %d (%.0f%%)' % (len(cov['either']), 100*len(cov['either'])/g))
