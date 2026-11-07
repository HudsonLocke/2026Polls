import json, csv, re, os, datetime, collections, unicodedata

OUT="/Users/hudsonisonline/Desktop/Datasets"
ELECTION_DAY=datetime.date(2026,11,3)

STATES={
 'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO',
 'Connecticut':'CT','Delaware':'DE','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID',
 'Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA',
 'Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN',
 'Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV',
 'New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC',
 'North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA',
 'Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX',
 'Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA','West Virginia':'WV',
 'Wisconsin':'WI','Wyoming':'WY','District of Columbia':'DC','Puerto Rico':'PR','Guam':'GU',
 'American Samoa':'AS','Northern Mariana Islands':'MP','United States Virgin Islands':'VI',
 'U.S. Virgin Islands':'VI','Virgin Islands':'VI','United States':'US',
}
PO2NAME={v:k for k,v in STATES.items()}
PO2NAME['US']='United States'

def state_norm(s):
    if not s: return ('','')
    s=s.strip()
    if s in STATES: return (s, STATES[s])
    if s.upper() in PO2NAME: return (PO2NAME[s.upper()], s.upper())
    for name in STATES:
        if name.lower()==s.lower(): return (name, STATES[name])
    return (s,'')

PARTY_RE=re.compile(r'\((D|R|I|L|G|DFL|NPL|D-NPL|IND|Dem|Rep|GOP|Lib|Grn|Ind|NP|NPA|NPP|NON|UNA|U|WF|WFP|C|CON|SAM|UNITE|FWD|AIP|PSL|SWP|AE)\)\s*$', re.I)
def split_party(name):
    name=(name or '').strip()
    m=PARTY_RE.search(name)
    party=''
    if m:
        party=m.group(1).upper()
        name=PARTY_RE.sub('',name).strip()
        party={'DEM':'D','REP':'R','GOP':'R','IND':'I','LIB':'L','GRN':'G',
               'DFL':'D','NPL':'D','D-NPL':'D','WFP':'WF','CON':'C',
               'NON':'NP','UNA':'NP','U':'NP','NPP':'NP'}.get(party,party)
    low=name.lower()
    if not party:
        if low in ('dem','democrat','democratic','democrats','generic democrat','democratic candidate'): party='D'
        elif low in ('rep','republican','republicans','gop','generic republican','republican candidate'): party='R'
    return name, party

def lean_from_pollster(p):
    m=re.findall(r'\((D|R)\)', p or '')
    if not m: return ''
    s=set(m)
    if s=={'D'}: return 'D'
    if s=={'R'}: return 'R'
    return 'D/R'

def norm_pollster(p):
    p=unicodedata.normalize('NFKD', p or '')
    p=re.sub(r'\((?:D|R|D/R|R/D)\)','',p)
    p=p.lower()
    p=re.sub(r'\bthe\b','',p)          # 'The New York Times/Siena' == 'New York Times / Siena'
    p=re.sub(r'\b(inc|llc|co|corp)\b\.?','',p)
    p=re.sub(r'[^a-z0-9]+','', p)
    return p

def dte(end):
    if not end: return ''
    try:
        d=datetime.date.fromisoformat(end)
    except Exception: return ''
    return (ELECTION_DAY-d).days

FIELDS=['source','office','cycle','state','state_po','district','race_label','race_stage',
        'poll_id','question_id','pollster','pollster_partisan_lean','sponsors','internal_poll',
        'start_date','end_date','field_dates_raw','days_to_election','sample_size','population',
        'margin_of_error','candidate','candidate_party','pct','undecided_pct','other_pct',
        'dem_pct','rep_pct','margin_dem_minus_rep','data_quality_flag','url','wiki_page',
        'wiki_section','dedupe_key']

def mk(**kw):
    r={k:'' for k in FIELDS}
    r.update({k:('' if v is None else v) for k,v in kw.items()})
    return r

rows=[]

# ---------------- VoteHub ----------------
vh=json.load(open('raw/votehub_polls.json'))
OFFICE={'us-senator':'Senate','governor':'Governor','us-representative':'House','generic-ballot':'Generic ballot'}
for p in vh:
    pt=p.get('poll_type')
    if pt not in OFFICE: continue
    subject=(p.get('subject') or '').strip()
    m=re.match(r'^(20\d\d)\s*(.*)$', subject)
    cycle=int(m.group(1)) if m else ''
    rest=(m.group(2).strip() if m else subject)
    stage='General'; district=''
    if pt=='us-representative':
        mm=re.match(r'^([A-Za-z]{2})-(\d{1,3})$', rest)
        if mm: stname,stpo=state_norm(mm.group(1).upper()); district=str(int(mm.group(2)))
        else: stname,stpo=state_norm(rest)
    elif pt=='generic-ballot':
        stname,stpo=('United States','US')
    else:
        mm=re.match(r'^(.*?)\s+(Democratic|Republican)$', rest)
        if mm:
            stname,stpo=state_norm(mm.group(1).strip())
            stage=mm.group(2)+' primary'
        else:
            stname,stpo=state_norm(rest)
    office=OFFICE[pt]
    if office=='House' and district: race_label=f"{stpo or stname}-{district}"
    elif office=='Generic ballot': race_label='National generic ballot'
    else: race_label=f"{stname} {office}"
    answers=p.get('answers') or []
    dem=rep=None
    for a in answers:
        _,pty=split_party(a.get('choice'))
        if pty=='D' and dem is None: dem=a.get('pct')
        if pty=='R' and rep is None: rep=a.get('pct')
    margin=(round(dem-rep,2) if (dem is not None and rep is not None) else '')
    dk=f"{office}|{stpo}|{district}|{stage}|{norm_pollster(p.get('pollster'))}|{p.get('end_date') or ''}"
    for i,a in enumerate(answers):
        cname,cparty=split_party(a.get('choice'))
        rows.append(mk(source='VoteHub', office=office, cycle=cycle, state=stname, state_po=stpo,
            district=district, race_label=race_label, race_stage=stage,
            poll_id='VH-'+str(p.get('id')), question_id='VH-'+str(p.get('id')),
            pollster=p.get('pollster'), pollster_partisan_lean=(p.get('partisan') or ''),
            sponsors='; '.join(p.get('sponsors') or []),
            internal_poll=('TRUE' if p.get('internal') else 'FALSE'),
            start_date=p.get('start_date'), end_date=p.get('end_date'),
            field_dates_raw=f"{p.get('start_date')} to {p.get('end_date')}",
            days_to_election=dte(p.get('end_date')), sample_size=p.get('sample_size'),
            population=p.get('population'), candidate=cname, candidate_party=cparty,
            pct=a.get('pct'), dem_pct=dem, rep_pct=rep, margin_dem_minus_rep=margin,
            url=p.get('url'), dedupe_key=dk))

# ---------------- Wikipedia ----------------
wk=json.load(open('wiki_rows.json'))
def wiki_race(page, section, office):
    # state / district from page title
    stname=stpo=''; district=''
    m=re.search(r'Senate (?:election|elections|special election) in (?:the )?(.+)$', page)
    if m: stname,stpo=state_norm(m.group(1))
    m=re.search(r'House of Representatives (?:election|elections) in (?:the )?(.+)$', page)
    if m:
        base=re.sub(r'\s*\(districts.*\)$','',m.group(1)).strip()
        stname,stpo=state_norm(base)
    m=re.match(r'^2026 (.+?) gubernatorial election$', page)
    if m: stname,stpo=state_norm(m.group(1))
    m=re.match(r"^(?:20\d\d(?:[\u2013\-]\d\d)?) (.+?)['\u2019]s (\d{1,2})(?:st|nd|rd|th) congressional district", page)
    if m:
        stname,stpo=state_norm(m.group(1)); district=m.group(2)
    if not district:
        m=re.search(r'District (\d{1,2})\b', section or '')
        if m: district=m.group(1)
        m=re.search(r"(\d{1,2})(?:st|nd|rd|th) (?:congressional )?district", section or '', re.I)
        if m: district=m.group(1)
    if not stname and 'legislative election' in page:
        stname,stpo=('United States','US')
    sec=(section or '').lower()
    if 'democratic primary' in sec: stage='Democratic primary'
    elif 'republican primary' in sec: stage='Republican primary'
    elif 'runoff' in sec: stage='Runoff'
    elif 'primary' in sec: stage='Primary'
    elif 'special' in sec: stage='Special general'
    else: stage='General'
    if 'runoff' in sec and 'democratic' in sec: stage='Democratic primary runoff'
    if 'runoff' in sec and 'republican' in sec: stage='Republican primary runoff'
    if office=='House' and district: label=f"{stpo or stname}-{district}"
    elif office=='Generic ballot' or stpo=='US': label='National generic ballot'
    else: label=f"{stname} {office}"
    return stname, stpo, district, stage, label

byq=collections.defaultdict(list)
for r in wk: byq[r['poll_id']].append(r)

for qid, group in byq.items():
    g0=group[0]
    office=g0['office']
    if office not in ('Senate','Governor','House','Generic ballot'): continue
    stname,stpo,district,stage,label=wiki_race(g0['wiki_page'], g0['section'], office)
    if office=='Generic ballot' or (stpo=='US'): office='Generic ballot'
    dem=rep=None
    for r in group:
        _,pty=split_party(r['candidate'])
        if pty=='D' and dem is None: dem=r['pct']
        if pty=='R' and rep is None: rep=r['pct']
    margin=(round(dem-rep,2) if (dem is not None and rep is not None) else '')
    cyc=2026 if '2026' in g0['wiki_page'] else (2025 if '2025' in g0['wiki_page'] else '')
    lean=lean_from_pollster(g0['pollster'])
    dk=f"{office}|{stpo}|{district}|{stage}|{norm_pollster(g0['pollster'])}|{g0['end_date'] or ''}"
    for r in group:
        cname,cparty=split_party(r['candidate'])
        rows.append(mk(source='Wikipedia', office=office, cycle=cyc, state=stname, state_po=stpo,
            district=district, race_label=label, race_stage=stage,
            poll_id='WP-'+str(abs(hash(qid))%10**12), question_id='WP-'+str(abs(hash(qid))%10**12),
            pollster=re.sub(r'\s*\((?:D|R|D/R)\)\s*$','',r['pollster']).strip() or r['pollster'],
            pollster_partisan_lean=lean, sponsors=r.get('sponsor') or '',
            internal_poll=('TRUE' if lean else 'FALSE'),
            start_date=r['start_date'], end_date=r['end_date'], field_dates_raw=r['date_raw'],
            days_to_election=dte(r['end_date']), sample_size=r['sample_size'],
            population=r['population'], margin_of_error=r['margin_of_error'],
            candidate=cname, candidate_party=cparty, pct=r['pct'],
            undecided_pct=r['undecided'], other_pct=r['other'],
            dem_pct=dem, rep_pct=rep, margin_dem_minus_rep=margin,
            wiki_page=r['wiki_page'], wiki_section=r['section'], dedupe_key=dk))

# ---------------- Silver Bulletin generic ballot ----------------
sb=list(csv.DictReader(open('raw/silverbulletin_generic_ballot.csv')))
def mdy(s):
    s=(s or '').strip()
    if not s: return ''
    for f in ('%m/%d/%Y','%m/%d/%y','%Y-%m-%d'):
        try: return datetime.datetime.strptime(s,f).date().isoformat()
        except Exception: pass
    return ''
sb_extra=[]
for p in sb:
    sd=mdy(p.get('startdate')); ed=mdy(p.get('enddate'))
    pid='SB-'+str(p.get('poll_id') or '')+'-'+str(p.get('question_id') or '')
    pop=(p.get('population') or '').strip().lower()
    dem=p.get('dem'); rep=p.get('rep')
    try: demf=float(dem)
    except Exception: demf=None
    try: repf=float(rep)
    except Exception: repf=None
    margin=(round(demf-repf,2) if demf is not None and repf is not None else '')
    dk=f"Generic ballot|US||General|{norm_pollster(p.get('pollster'))}|{ed}"
    base=dict(source='Silver Bulletin', office='Generic ballot', cycle=2026,
        state='United States', state_po='US', district='', race_label='National generic ballot',
        race_stage='General', poll_id=pid, question_id=pid, pollster=p.get('pollster'),
        pollster_partisan_lean=(p.get('partisan') or ''), sponsors=p.get('sponsors') or '',
        internal_poll=('TRUE' if (p.get('partisan') or '').strip() else 'FALSE'),
        start_date=sd, end_date=ed, field_dates_raw=f"{p.get('startdate')} to {p.get('enddate')}",
        days_to_election=dte(ed), sample_size=p.get('samplesize'), population=pop,
        dem_pct=demf, rep_pct=repf, margin_dem_minus_rep=margin, url=p.get('url'), dedupe_key=dk)
    for cand,party,val in (('Democratic candidate','D',demf),('Republican candidate','R',repf)):
        if val is None: continue
        rows.append(mk(candidate=cand, candidate_party=party, pct=val, **base))
    sb_extra.append(dict(poll_id=pid, pollster=p.get('pollster'), sponsors=p.get('sponsors'),
        start_date=sd, end_date=ed, sample_size=p.get('samplesize'), population=pop,
        subgroup=p.get('subgroup'), dem=p.get('dem'), rep=p.get('rep'), net=p.get('net'),
        adjusted_dem=p.get('adjusted_dem'), adjusted_rep=p.get('adjusted_rep'),
        adjusted_net=p.get('adjusted_net'), weight=p.get('weight'), influence=p.get('influence'),
        url=p.get('url')))

# ---------------- post-pass: clean, backfill party, recompute margins ----------------
JUNK=re.compile(r'^[\d.,%$()\s]+$|^\d[\d,.]*\s*\((?:RV|LV|A|V)\)$', re.I)
before=len(rows)
NOT_A_CANDIDATE=re.compile(r'^(rcv round|round \d*|round|total|turnout|n/a|sample|margin|net)$', re.I)
rows=[r for r in rows
      if r['pollster'] and not JUNK.match(str(r['pollster']))
      and not NOT_A_CANDIDATE.match(str(r['candidate']).strip())]
dropped_junk=before-len(rows)

# Minnesota DFL and North Dakota Democratic-NPL are the state Democratic parties
dfl=0
for r in rows:
    if str(r['candidate_party']).upper() in ('DFL','NPL','D-NPL'):
        r['candidate_party']='D'
        r['data_quality_flag']='state_affiliate_mapped_to_D'
        dfl+=1

def cname_key(n):
    n=unicodedata.normalize('NFKD', str(n or '')).lower()
    n=re.sub(r'\b(jr|sr|ii|iii|iv)\b','',n)
    n=re.sub(r'[^a-z ]','',n)
    return ' '.join(n.split())

# party map learned from rows that already carry a party letter
scoped=collections.defaultdict(collections.Counter)
glob=collections.defaultdict(collections.Counter)
for r in rows:
    if r['candidate_party'] in ('D','R','I','L','G'):
        k=cname_key(r['candidate'])
        if len(k.split())>=2:
            scoped[(r['state_po'], r['office'], k)][r['candidate_party']]+=1
            glob[k][r['candidate_party']]+=1

STAGE_PARTY={'Democratic primary':'D','Democratic primary runoff':'D',
             'Republican primary':'R','Republican primary runoff':'R'}
backfilled=0
for r in rows:
    if r['candidate_party']: continue
    k=cname_key(r['candidate'])
    if re.search(r'generic|someone else|other|undecided|another|unsure|no ?one|neither', k):
        continue
    cnt=scoped.get((r['state_po'], r['office'], k))
    if not cnt and len(k.split())>=2: cnt=glob.get(k)
    if cnt and len(cnt)==1:
        r['candidate_party']=next(iter(cnt)); r['data_quality_flag']='party_inferred_from_name'
        backfilled+=1
    elif r['race_stage'] in STAGE_PARTY:
        r['candidate_party']=STAGE_PARTY[r['race_stage']]
        r['data_quality_flag']='party_inferred_from_primary'
        backfilled+=1

# Candidates who never appear with ANY party label anywhere in the dataset, standing as
# the only other named candidate against a known D or R in a general election, are
# inferred to be the opposite major party. Flagged, because an unlabelled independent or
# nonpartisan candidate would be wrongly assigned by this rule.
labelled_anywhere={cname_key(r['candidate']) for r in rows if r['candidate_party']}
NOISE=re.compile(r'generic|someone else|^other|undecided|neither|another|unsure|no ?one|write', re.I)
_bq=collections.defaultdict(list)
for r in rows: _bq[r['question_id']].append(r)
opp_inferred=0
for qid,g in _bq.items():
    if g[0]['race_stage'] not in ('General','Special general'): continue
    named=[r for r in g if not NOISE.search(str(r['candidate']))]
    known=[r for r in named if r['candidate_party'] in ('D','R')]
    unknown=[r for r in named if not r['candidate_party']]
    if len(named)==2 and len(known)==1 and len(unknown)==1:
        if cname_key(unknown[0]['candidate']) in labelled_anywhere: continue
        unknown[0]['candidate_party']='R' if known[0]['candidate_party']=='D' else 'D'
        f=unknown[0]['data_quality_flag']
        unknown[0]['data_quality_flag']=(f+'; ' if f else '')+'party_inferred_as_sole_opponent'
        opp_inferred+=1
print(f"post-pass: mapped {dfl} DFL/NPL rows to D, inferred {opp_inferred} sole-opponent parties")

# recompute dem/rep/margin per question now that parties are filled in
bq=collections.defaultdict(list)
for r in rows: bq[r['question_id']].append(r)
for qid,g in bq.items():
    if g[0]['race_stage'] not in ('General','Special general'):
        dem=rep=None
    else:
        dem=rep=None
        for r in g:
            v=r['pct']
            try: v=float(v)
            except Exception: continue
            if r['candidate_party']=='D' and dem is None: dem=v
            if r['candidate_party']=='R' and rep is None: rep=v
    margin=(round(dem-rep,2) if (dem is not None and rep is not None) else '')
    for r in g:
        r['dem_pct']=('' if dem is None else dem)
        r['rep_pct']=('' if rep is None else rep)
        r['margin_dem_minus_rep']=margin

# Firms that publicly admitted fabricating 2026 polling. Kept in the data, flagged,
# never silently deleted.
FABRICATED=re.compile(r'^(wedgewood\s*polls?|median\s*strategies)\b', re.I)
fab=0
for r in rows:
    if FABRICATED.match(str(r['pollster']).strip()):
        f=r['data_quality_flag']
        r['data_quality_flag']=(f+'; ' if f else '')+'pollster_admitted_fabrication'
        fab+=1
print(f"post-pass: flagged {fab} rows from firms that admitted fabricating polls")

# flag source-side date problems rather than silently editing them
bad_dates=0
for r in rows:
    sd,ed=r['start_date'],r['end_date']
    if sd and ed and str(sd)>str(ed):
        f=r['data_quality_flag']
        r['data_quality_flag']=(f+'; ' if f else '')+'start_after_end_in_source'
        bad_dates+=1
    if not ed:
        f=r['data_quality_flag']
        r['data_quality_flag']=(f+'; ' if f else '')+'no_parsable_date'

print(f"post-pass: dropped {dropped_junk} malformed rows, inferred party on {backfilled} rows, "
      f"flagged {bad_dates} rows whose source dates run backwards")

# ---------------- write ----------------
os.makedirs(OUT, exist_ok=True)
def key(r):
    return (r['end_date'] or '0000-00-00', r['state_po'], str(r['district']), r['poll_id'], str(r['candidate']))
rows.sort(key=key, reverse=True)

def write(path, data, fields=FIELDS):
    with open(os.path.join(OUT,path),'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(data)
    return len(data)

n_all=write('all_polls_2026.csv', rows)
for off,fn in [('Senate','senate_polls_2026.csv'),('Governor','governor_polls_2026.csv'),
               ('House','house_polls_2026.csv'),('Generic ballot','generic_ballot_polls_2026.csv')]:
    sub=[r for r in rows if r['office']==off]
    print(f"{off}: rows={len(sub)} questions={len({r['question_id'] for r in sub})} firms={len({r['pollster'] for r in sub})}")
    write(fn, sub)

# one row per poll question (wide-ish margin view)
seen=set(); margins=[]
MF=['source','office','cycle','state','state_po','district','race_label','race_stage','poll_id',
    'pollster','pollster_partisan_lean','sponsors','internal_poll','start_date','end_date',
    'days_to_election','sample_size','population','margin_of_error','dem_pct','rep_pct',
    'margin_dem_minus_rep','top_candidates','data_quality_flag','url','wiki_page',
    'wiki_section','dedupe_key']
bq=collections.defaultdict(list)
for r in rows: bq[r['question_id']].append(r)
for qid,g in bq.items():
    g0=dict(g[0])
    cands=sorted([(x['pct'],x['candidate'],x['candidate_party']) for x in g if isinstance(x['pct'],(int,float))], reverse=True)
    g0['top_candidates']='; '.join(f"{c} ({p}) {v}%" if p else f"{c} {v}%" for v,c,p in cands[:6])
    margins.append(g0)
margins.sort(key=lambda r:(r['end_date'] or '', r['state_po']), reverse=True)
write('poll_questions_2026.csv', margins, MF)

# pollster inventory
inv=collections.defaultdict(lambda: collections.defaultdict(set))
meta={}
for r in rows:
    k=r['pollster']
    inv[k][r['office']].add(r['question_id'])
    m=meta.setdefault(k, {'sources':set(),'first':'9999','last':'0000','lean':set(),'q':set()})
    m['sources'].add(r['source']); m['q'].add(r['question_id'])
    if r['pollster_partisan_lean']: m['lean'].add(str(r['pollster_partisan_lean']))
    if r['end_date']:
        m['first']=min(m['first'], r['end_date']); m['last']=max(m['last'], r['end_date'])
pf=['pollster','questions','senate','governor','house','generic_ballot','sources','partisan_lean','first_poll','last_poll']
pol=[]
for k in sorted(inv, key=lambda x: -len(meta[x]['q'])):
    m=meta[k]
    pol.append(dict(pollster=k, questions=len(m['q']),
        senate=len(inv[k]['Senate']), governor=len(inv[k]['Governor']),
        house=len(inv[k]['House']), generic_ballot=len(inv[k]['Generic ballot']),
        sources='; '.join(sorted(m['sources'])), partisan_lean='; '.join(sorted(m['lean'])),
        first_poll=(m['first'] if m['first']!='9999' else ''), last_poll=(m['last'] if m['last']!='0000' else '')))
write('pollsters_2026.csv', pol, pf)

# per-source raw/long copies
os.makedirs(os.path.join(OUT,'source_data'), exist_ok=True)
for src,fn in [('VoteHub','source_data/votehub_polls_long.csv'),
               ('Wikipedia','source_data/wikipedia_polls_long.csv'),
               ('Silver Bulletin','source_data/silver_bulletin_generic_ballot_long.csv')]:
    write(fn, [r for r in rows if r['source']==src])
write('source_data/silver_bulletin_generic_ballot_with_adjusted.csv', sb_extra,
      ['poll_id','pollster','sponsors','start_date','end_date','sample_size','population','subgroup',
       'dem','rep','net','adjusted_dem','adjusted_rep','adjusted_net','weight','influence','url'])

print()
print("TOTAL candidate-level rows:", n_all)
print("TOTAL poll questions:", len({r['question_id'] for r in rows}))
print("TOTAL distinct polling firms/consortia:", len({r['pollster'] for r in rows if r['pollster']}))
print("date span:", min((r['end_date'] for r in rows if r['end_date']), default=''), "->",
      max((r['end_date'] for r in rows if r['end_date']), default=''))
print("by source:", collections.Counter(r['source'] for r in rows))
print("stages:", collections.Counter(r['race_stage'] for r in rows))
print("races covered:", len({(r['office'],r['state_po'],r['district']) for r in rows}))
gen=[r for r in rows if r['race_stage'] in ('General','Special general')]
gq={r['question_id'] for r in gen}
withm={r['question_id'] for r in gen if r['margin_dem_minus_rep']!=''}
print(f"general-election questions with a usable D-R margin: {len(withm):,} of {len(gq):,}")
print("rows missing candidate_party:", sum(1 for r in rows if not r['candidate_party']))
print("rows with a quality flag:", sum(1 for r in rows if r['data_quality_flag']))
json.dump({'n_rows':n_all}, open('norm_stats.json','w'))
