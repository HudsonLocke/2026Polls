"""Collapse the same poll question carried by more than one source into one record.

Within a dedupe_key (office|state|district|stage|normalised pollster|end_date), questions
from DIFFERENT sources are matched to each other on their candidate sets and merged.
Questions from the SAME source are never collapsed into each other -- when one source
lists two matchups for a poll, those are two real questions, not duplicates.
"""
import csv, os, re, collections, unicodedata, itertools

OUT="/Users/hudsonisonline/Desktop/Datasets"
DD=os.path.join(OUT,"deduped")
os.makedirs(DD, exist_ok=True)

# which source supplies the base pct values when a tie has to be broken
PRIORITY={'Wikipedia':0,'VoteHub':1,'Silver Bulletin':2}
PRIORITY_GB={'Silver Bulletin':0,'VoteHub':1,'Wikipedia':2}
META_FILL=['sample_size','population','margin_of_error','url','sponsors','undecided_pct','other_pct']

NOISE=re.compile(r'generic|someone else|^other$|undecided|neither|another|unsure|no ?one|write|^all others$|rcv round', re.I)

def lastname(n):
    n=unicodedata.normalize('NFKD', str(n or ''))
    n=re.sub(r'\([^)]*\)','',n)
    n=re.sub(r'[^A-Za-z \-\']','',n).strip()
    n=re.sub(r"\b(jr|sr|ii|iii|iv|dr|mr|mrs|ms)\b",'',n,flags=re.I).strip()
    parts=[p for p in n.split() if p]
    if not parts: return ''
    return parts[-1].lower().replace("'","").replace("-","")

def nameset(group):
    # The generic ballot has no candidates: Silver Bulletin writes 'Democratic candidate',
    # VoteHub writes 'Dem'. Match those on party instead of on a surname.
    if group[0]['office']=='Generic ballot':
        return frozenset(x['candidate_party'] for x in group if x['candidate_party'] in ('D','R'))
    return frozenset(lastname(x['candidate']) for x in group
                     if x['candidate'] and not NOISE.search(x['candidate']) and lastname(x['candidate']))

def pctmap(group):
    gb = group[0]['office']=='Generic ballot'
    m={}
    for x in group:
        k = x['candidate_party'] if gb else lastname(x['candidate'])
        if not k or (gb and k not in ('D','R')): continue
        try: m[k]=float(x['pct'])
        except Exception: pass
    return m

def jaccard(a,b):
    if not a or not b: return 0.0
    return len(a&b)/len(a|b)

rows=list(csv.DictReader(open(os.path.join(OUT,'all_polls_2026.csv'))))
FIELDS=list(rows[0].keys())
questions=collections.OrderedDict()
for r in rows: questions.setdefault(r['question_id'], []).append(r)

bykey=collections.defaultdict(list)
for qid,g in questions.items(): bykey[g[0]['dedupe_key']].append(qid)

merged_clusters=[]      # list of list-of-qid
stats=collections.Counter()

for key, qids in bykey.items():
    bysrc=collections.defaultdict(list)
    for qid in qids: bysrc[questions[qid][0]['source']].append(qid)

    if len(bysrc)==1:
        for qid in qids: merged_clusters.append([qid])
        stats['single_source_questions']+=len(qids)
        continue

    office=questions[qids[0]][0]['office']
    pri = PRIORITY_GB if office=='Generic ballot' else PRIORITY
    # base source: the one listing the most distinct matchups, then by priority
    order=sorted(bysrc, key=lambda s:(-len(bysrc[s]), pri.get(s,9)))
    base_src=order[0]
    clusters=[[qid] for qid in bysrc[base_src]]
    base_sets=[nameset(questions[qid]) for qid in bysrc[base_src]]
    base_pcts=[pctmap(questions[qid]) for qid in bysrc[base_src]]

    for src in order[1:]:
        for qid in bysrc[src]:
            ns=nameset(questions[qid]); pm=pctmap(questions[qid])
            best=None; best_score=None
            for i,(bs,bp) in enumerate(zip(base_sets,base_pcts)):
                if any(questions[c][0]['source']==src for c in clusters[i]):
                    continue                      # that base already took a record from this source
                shared=ns & bs
                if not shared: continue
                exact = 1 if ns==bs else 0
                j=jaccard(ns,bs)
                if not exact:
                    # A looser match is only allowed when one record's candidates are a
                    # strict subset of the other's (a source that omitted the minor
                    # candidates), at least two candidates are shared, and the overlap is
                    # better than half. Without all three, a first-past-the-post question
                    # merges with a two-way, or a 'vs Generic Opponent' merges with a real
                    # matchup -- both of which happened at a 0.5 threshold.
                    if not (ns <= bs or bs <= ns): continue
                    if len(shared) < 2: continue
                    if j <= 0.6: continue
                # closeness of the shared candidates' numbers, smaller is better
                d=sum(abs(pm[k]-bp[k]) for k in shared if k in pm and k in bp)/max(1,len(shared))
                score=(exact, j, -d)
                if best_score is None or score>best_score:
                    best_score=score; best=i
            if best is not None:
                clusters[best].append(qid)
                stats['exact_matches' if best_score[0]==1 else 'partial_matches']+=1
            else:
                clusters.append([qid]); base_sets.append(ns); base_pcts.append(pm)
                stats['unmatched_kept_as_own']+=1
    merged_clusters += clusters

out=[]
EXTRA=['sources','n_source_records','source_pct_max_delta','match_rule']
for cl in merged_clusters:
    recs=[questions[q] for q in cl]
    # base = most candidate rows, then source priority
    office=recs[0][0]['office']
    pri = PRIORITY_GB if office=='Generic ballot' else PRIORITY
    recs_sorted=sorted(recs, key=lambda g:(-len(g), pri.get(g[0]['source'],9)))
    base=recs_sorted[0]; others=recs_sorted[1:]
    srcs=sorted({g[0]['source'] for g in recs})

    # max disagreement on shared candidates
    delta=''
    if others:
        bp=pctmap(base); ds=[]
        for g in others:
            op=pctmap(g)
            for k in set(bp)&set(op): ds.append(abs(bp[k]-op[k]))
        if ds: delta=round(max(ds),1)

    exactish = all(nameset(g)==nameset(base) for g in others)
    rule = ('unique' if not others else ('exact' if exactish else 'partial'))

    for r in base:
        o=dict(r)
        for m in META_FILL:
            if not o.get(m):
                for g in others:
                    v=next((x[m] for x in g if x.get(m)), '')
                    if v: o[m]=v; break
        flags=[f for f in (o['data_quality_flag'].split('; ') if o['data_quality_flag'] else []) if f]
        if delta!='' and delta>1.0 and 'source_pct_disagreement' not in flags:
            flags.append('source_pct_disagreement')
        if others and rule=='partial':
            flags.append('merged_on_partial_candidate_match')
        o['data_quality_flag']='; '.join(flags)
        o['sources']='; '.join(srcs)
        o['n_source_records']=len(recs)
        o['source_pct_max_delta']=delta
        o['match_rule']=rule
        out.append(o)

FOUT=FIELDS+EXTRA
def key(r): return (r['end_date'] or '0000-00-00', r['state_po'], str(r['district']), r['question_id'], str(r['candidate']))
out.sort(key=key, reverse=True)

def write(path, data, fields):
    with open(os.path.join(DD,path),'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(data)
    return len(data)

write('all_polls_2026_deduped.csv', out, FOUT)
for off,fn in [('Senate','senate_polls_2026_deduped.csv'),('Governor','governor_polls_2026_deduped.csv'),
               ('House','house_polls_2026_deduped.csv'),('Generic ballot','generic_ballot_polls_2026_deduped.csv')]:
    sub=[r for r in out if r['office']==off]
    write(fn, sub, FOUT)
    print(f"{off}: rows={len(sub)} questions={len({r['question_id'] for r in sub})} firms={len({r['pollster'] for r in sub})}")

# question-level view
QF=['source','sources','office','cycle','state','state_po','district','race_label','race_stage','poll_id',
    'pollster','pollster_partisan_lean','sponsors','internal_poll','start_date','end_date','days_to_election',
    'sample_size','population','margin_of_error','undecided_pct','other_pct','dem_pct','rep_pct','margin_dem_minus_rep','top_candidates',
    'n_source_records','source_pct_max_delta','match_rule','data_quality_flag','url','wiki_page','wiki_section','dedupe_key']
bq=collections.OrderedDict()
for r in out: bq.setdefault(r['question_id'], []).append(r)
qrows=[]
for qid,g in bq.items():
    g0=dict(g[0])
    cands=sorted([(float(x['pct']),x['candidate'],x['candidate_party']) for x in g if x['pct']], reverse=True)
    g0['top_candidates']='; '.join((f"{c} ({p}) {v}%" if p else f"{c} {v}%") for v,c,p in cands[:6])
    qrows.append(g0)
write('poll_questions_2026_deduped.csv', qrows, QF)

# firm inventory on the deduped set
inv=collections.defaultdict(lambda: collections.defaultdict(set)); meta={}
for r in out:
    k=r['pollster']
    inv[k][r['office']].add(r['question_id'])
    m=meta.setdefault(k, {'q':set(),'srcs':set(),'lean':set(),'first':'9999','last':'0000'})
    m['q'].add(r['question_id']); m['srcs'].update(r['sources'].split('; '))
    if r['pollster_partisan_lean']: m['lean'].add(r['pollster_partisan_lean'])
    if r['end_date']:
        m['first']=min(m['first'],r['end_date']); m['last']=max(m['last'],r['end_date'])
pf=['pollster','questions','senate','governor','house','generic_ballot','sources','partisan_lean','first_poll','last_poll']
pol=[dict(pollster=k, questions=len(meta[k]['q']), senate=len(inv[k]['Senate']), governor=len(inv[k]['Governor']),
          house=len(inv[k]['House']), generic_ballot=len(inv[k]['Generic ballot']),
          sources='; '.join(sorted(meta[k]['srcs'])), partisan_lean='; '.join(sorted(meta[k]['lean'])),
          first_poll=(meta[k]['first'] if meta[k]['first']!='9999' else ''),
          last_poll=(meta[k]['last'] if meta[k]['last']!='0000' else ''))
     for k in sorted(inv, key=lambda x:-len(meta[x]['q']))]
write('pollsters_2026_deduped.csv', pol, pf)

print()
print("match stats:", dict(stats))
print(f"IN : {len(rows):,} rows / {len(questions):,} questions")
print(f"OUT: {len(out):,} rows / {len({r['question_id'] for r in out}):,} questions "
      f"/ {len({r['pollster'] for r in out}):,} firms")
print(f"removed: {len(questions)-len({r['question_id'] for r in out}):,} duplicate questions")
mr=collections.Counter(r['match_rule'] for r in qrows)
print("per-question match_rule:", dict(mr))
nm=collections.Counter(r['n_source_records'] for r in qrows)
print("questions by number of source records merged:", dict(sorted(nm.items())))
# metadata completeness gain
for m in META_FILL:
    a=sum(1 for g in bq.values() if any(x[m] for x in g))
    print(f"   {m:<18} populated on {a:,} of {len(bq):,} deduped questions ({100*a/len(bq):.0f}%)")
