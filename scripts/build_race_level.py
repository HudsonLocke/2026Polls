"""One row per 2026 general-election race: final polling average, each platform's
eve-of-election probability, and the realised winner from market settlement."""
import csv, json, os, statistics, collections, datetime

OUT="/Users/hudsonisonline/Desktop/Datasets"
os.makedirs(os.path.join(OUT,'analysis'), exist_ok=True)
ELECTION=datetime.date(2026,11,3)
EVE=datetime.date(2026,11,2)          # "the day before Election Day"
FINAL_WINDOW=14                       # days of polling that make up the final average

k_inv=json.load(open('raw/mkt/kalshi_inventory.json'))
k_hist=json.load(open('raw/mkt/kalshi_history.json'))
p_inv=json.load(open('raw/mkt/pm_inventory.json'))
p_hist=json.load(open('raw/mkt/pm_history.json'))

def rk(off,st,dist): return (off, st, str(dist or ''))

# ---- outcomes from settlement, independently from each platform ----
k_win={}; p_win={}
for leg in k_inv:
    if leg.get('cycle')!=2026: continue
    if leg.get('result')=='yes': k_win[rk(leg['office'],leg['state_po'],leg['district'])]=leg['party']
for leg in p_inv:
    if leg.get('cycle')!=2026 or leg['office']=='Generic ballot': continue
    try: op=float(leg.get('outcome_price') or 'nan')
    except Exception: continue
    if op==1.0: p_win[rk(leg['office'],leg['state_po'],leg['district'])]=leg['party']

# ---- eve-of-election probabilities ----
def eve_prob(inv, hist, tokkey, want_party):
    tbl=collections.defaultdict(list)
    for leg in inv:
        if leg.get('cycle')!=2026: continue
        if leg['party']!=want_party: continue
        s=hist.get(leg[tokkey]) or {}
        if s: tbl[rk(leg['office'],leg['state_po'],leg['district'])].append(s)
    out={}
    for race,serieses in tbl.items():
        vals=[]
        for s in serieses:
            v=None
            for back in range(0,8):           # last price on or before the eve
                d=(EVE-datetime.timedelta(days=back)).isoformat()
                if d in s: v=s[d]; break
            if v is None: vals=[]; break
            vals.append(v)
        if vals: out[race]=round(sum(vals),4)
    return out
KD=eve_prob(k_inv,k_hist,'ticker','D'); KR=eve_prob(k_inv,k_hist,'ticker','R')
PD=eve_prob(p_inv,p_hist,'yes_token','D'); PR=eve_prob(p_inv,p_hist,'yes_token','R')

# ---- final polling average, from the deduplicated question-level file ----
polls=collections.defaultdict(list)
src=os.path.join(OUT,'deduped','poll_questions_2026_deduped.csv')
for r in csv.DictReader(open(src)):
    if r['cycle']!='2026' or r['race_stage'] not in ('General','Special general'): continue
    if r['office']=='Generic ballot': continue
    if not (r['dem_pct'] and r['rep_pct'] and r['end_date']): continue
    if 'pollster_admitted_fabrication' in r['data_quality_flag']: continue   # Wedgewood
    try:
        ed=datetime.date.fromisoformat(r['end_date']); d=float(r['dem_pct']); rp=float(r['rep_pct'])
    except Exception: continue
    if ed > EVE: continue
    polls[rk(r['office'],r['state_po'],r['district'])].append((ed,d,rp,r['pollster']))

races=sorted(set(list(polls)+list(KD)+list(PD)+list(k_win)+list(p_win)))
rows=[]
for race in races:
    off,st,dist=race
    ps=sorted(polls.get(race,[]), reverse=True)
    recent=[p for p in ps if (ELECTION-p[0]).days <= FINAL_WINDOW]
    pool = recent if recent else ps[:1]
    rec=dict(office=off, state_po=st, district=dist,
             race_label=(f"{st}-{dist}" if off=='House' and dist else f"{st} {off}"))
    if pool:
        dm=[p[1] for p in pool]; rm=[p[2] for p in pool]
        rec['poll_avg_dem']=round(statistics.mean(dm),2)
        rec['poll_avg_rep']=round(statistics.mean(rm),2)
        rec['poll_avg_margin']=round(statistics.mean(dm)-statistics.mean(rm),2)
        rec['poll_margin_abs']=abs(rec['poll_avg_margin'])
        rec['n_polls_in_average']=len(pool)
        rec['n_pollsters_in_average']=len({p[3] for p in pool})
        rec['last_poll_end_date']=pool[0][0].isoformat()
        rec['days_last_poll_to_election']=(ELECTION-pool[0][0]).days
        rec['poll_average_window']=('final_14_days' if recent else 'single_most_recent_poll')
        rec['poll_leader']=('D' if rec['poll_avg_margin']>0 else ('R' if rec['poll_avg_margin']<0 else 'tie'))
    for tag,D,R in (('kalshi',KD,KR), ('polymarket',PD,PR)):
        d=D.get(race); r_=R.get(race)
        if d is not None: rec[f'{tag}_dem_prob_eve']=d
        if r_ is not None: rec[f'{tag}_rep_prob_eve']=r_
        if d is not None and r_ is not None and (d+r_)>0:
            rec[f'{tag}_dem_prob_eve_norm']=round(d/(d+r_),4)
            rec[f'{tag}_favorite']=('D' if d>r_ else ('R' if r_>d else 'tie'))
    kw=k_win.get(race); pw=p_win.get(race)
    rec['winner_party_kalshi_settlement']=kw or ''
    rec['winner_party_polymarket_settlement']=pw or ''
    if kw and pw and kw!=pw: rec['winner_party']=''; rec['winner_source']='DISAGREE'
    elif kw: rec['winner_party']=kw; rec['winner_source']='kalshi_settlement'+('+polymarket' if pw else '')
    elif pw: rec['winner_party']=pw; rec['winner_source']='polymarket_settlement'
    else: rec['winner_party']=''; rec['winner_source']=''
    w=rec['winner_party']
    for who,key in (('poll_leader','poll_leader_correct'),
                    ('kalshi_favorite','kalshi_favorite_correct'),
                    ('polymarket_favorite','polymarket_favorite_correct')):
        pred=rec.get(who)
        rec[key]=('' if (not w or not pred or pred=='tie') else (1 if pred==w else 0))
    rec['close_race_7pt']=('' if rec.get('poll_margin_abs') is None else (1 if rec['poll_margin_abs']<7 else 0))
    rows.append(rec)

FIELDS=['office','state_po','district','race_label',
        'poll_avg_dem','poll_avg_rep','poll_avg_margin','poll_margin_abs','poll_leader',
        'n_polls_in_average','n_pollsters_in_average','last_poll_end_date',
        'days_last_poll_to_election','poll_average_window',
        'kalshi_dem_prob_eve','kalshi_rep_prob_eve','kalshi_dem_prob_eve_norm','kalshi_favorite',
        'polymarket_dem_prob_eve','polymarket_rep_prob_eve','polymarket_dem_prob_eve_norm',
        'polymarket_favorite','winner_party','winner_source',
        'winner_party_kalshi_settlement','winner_party_polymarket_settlement',
        'poll_leader_correct','kalshi_favorite_correct','polymarket_favorite_correct','close_race_7pt']
path=os.path.join(OUT,'analysis','race_level_2026.csv')
with open(path,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore'); w.writeheader()
    for r in sorted(rows, key=lambda x:(x['office'],x['state_po'],x['district'])): w.writerow(r)

print('races:', len(rows))
for o in ['Senate','Governor','House']:
    print('   %-10s %d' % (o, sum(1 for r in rows if r['office']==o)))
print()
print('outcome known           :', sum(1 for r in rows if r['winner_party']))
print('  from both platforms   :', sum(1 for r in rows if r['winner_party_kalshi_settlement'] and r['winner_party_polymarket_settlement']))
print('  platforms DISAGREE    :', sum(1 for r in rows if r['winner_source']=='DISAGREE'))
print('has polling average     :', sum(1 for r in rows if r.get('poll_leader')))
print('has kalshi eve prob     :', sum(1 for r in rows if r.get('kalshi_favorite')))
print('has polymarket eve prob :', sum(1 for r in rows if r.get('polymarket_favorite')))
print('COMPLETE (poll+both mkts+outcome):',
      sum(1 for r in rows if r.get('poll_leader') and r.get('kalshi_favorite') and r.get('polymarket_favorite') and r['winner_party']))
print('usable (poll+>=1 mkt+outcome)   :',
      sum(1 for r in rows if r.get('poll_leader') and (r.get('kalshi_favorite') or r.get('polymarket_favorite')) and r['winner_party']))
