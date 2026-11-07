import json, re, sys, datetime
from bs4 import BeautifulSoup
from wikilib import page_html

MONTHS = {m.lower():i for i,m in enumerate(
 ["January","February","March","April","May","June","July","August","September","October","November","December"],1)}
MONTHS.update({m[:3].lower():i for m,i in list(MONTHS.items())})
MON_RE = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t)?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'

META_KEYS = [
 'poll source','pollster','poll','source','sponsor','date','dates administered','date(s) administered',
 'date administered','sample size','samplesize','margin of error','moe','error','undecided','other',
 'other/undecided','undecided/other','none','none of these','neither','lead','margin','spread','link',
 'notes','population','mode','someone else','would not vote','no opinion','refused','not sure',
 'don\'t know','dk','abstain','blank','write-in','all others','others','total','sampling error'
]

def clean(s):
    s = s.replace(' ',' ')
    s = re.sub(r'\[\s*[a-zA-Z0-9]{1,3}\s*\]','',s)   # footnote markers
    s = re.sub(r'\[\s*\d+\s*\]','',s)
    s = re.sub(r'\s+',' ',s).strip()
    return s

def cell_text(td):
    for tag in td.find_all(['sup','style','script']):
        tag.decompose()
    return clean(td.get_text(' ', strip=True))

def expand(table):
    """Return grid[r][c] = (text, tag_name) handling rowspan/colspan."""
    rows = table.find_all('tr', recursive=False)
    if not rows:
        body = table.find('tbody')
        rows = body.find_all('tr', recursive=False) if body else table.find_all('tr')
    grid = {}
    pend = {}   # col -> (remaining, value)
    maxc = 0
    for r, tr in enumerate(rows):
        c = 0
        # place pending rowspans
        for col in sorted(pend):
            pass
        cells = tr.find_all(['td','th'], recursive=False)
        ci = 0
        while True:
            while (r,c) in grid:
                c += 1
            if ci >= len(cells):
                break
            cell = cells[ci]; ci += 1
            txt = cell_text(cell)
            try: cs = int(cell.get('colspan',1) or 1)
            except Exception: cs = 1
            try: rs = int(cell.get('rowspan',1) or 1)
            except Exception: rs = 1
            cs = max(1,min(cs,40)); rs = max(1,min(rs,200))
            for dr in range(rs):
                for dc in range(cs):
                    grid[(r+dr, c+dc)] = (txt, cell.name, dc>0 or dr>0)
            c += cs
            maxc = max(maxc, c)
    nrows = max((k[0] for k in grid), default=-1)+1
    out=[]
    for r in range(nrows):
        out.append([grid.get((r,c), ('', 'td', False)) for c in range(maxc)])
    return out

def norm_key(h):
    h = clean(h).lower().rstrip(':')
    h = re.sub(r'\(.*?\)','',h).strip()
    h = re.sub(r'\s+',' ',h)
    return h

def is_meta(h):
    k = norm_key(h)
    if not k: return True
    if k in META_KEYS: return True
    for m in META_KEYS:
        if k == m or k.startswith(m) or m in k.split('/'):
            return True
    if re.search(r'sample|margin of error|date|pollster|poll source|undecided|other|lead|margin|spread|sponsor|^moe$|not sure|no opinion|someone else|would not|write-?in|none of', k):
        return True
    return False

DASHES = '\u2013\u2014\u2212\u2012\u2015\u2010\u2011\u2043\uff0d\u02d7'
def parse_dates(s, default_year=None):
    raw = clean(s)
    if not raw: return (None,None,raw)
    s = raw
    for d in DASHES: s = s.replace(d, '-')
    s = re.sub(r'\s+to\s+', ' - ', s, flags=re.I)
    s = re.sub(r'\s*-\s*', ' - ', s)
    yrs = re.findall(r'\b(20\d\d)\b', s)
    y2 = int(yrs[-1]) if yrs else default_year
    y1 = int(yrs[0]) if len(yrs)>1 else y2
    # Mon D - Mon D, YYYY
    m = re.search(rf'({MON_RE})\.?\s+(\d{{1,2}})(?:\s*,\s*(20\d\d))?\s*-\s*({MON_RE})\.?\s+(\d{{1,2}})', s, re.I)
    if m and y2:
        try:
            ya = int(m.group(3)) if m.group(3) else y1
            a=datetime.date(ya, MONTHS[m.group(1)[:3].lower()], int(m.group(2)))
            b=datetime.date(y2, MONTHS[m.group(4)[:3].lower()], int(m.group(5)))
            if b<a:
                # cross-year range written with one year, e.g. 'December 21 - January 6, 2026'
                a=datetime.date(y2-1, a.month, a.day)
            if b<a: return (b.isoformat(), b.isoformat(), raw)
            return (a.isoformat(), b.isoformat(), raw)
        except Exception: pass
    # Mon D-D, YYYY
    m = re.search(rf'({MON_RE})\.?\s+(\d{{1,2}})\s*-\s*(\d{{1,2}})(?!\d)', s, re.I)
    if m and y2:
        try:
            mo=MONTHS[m.group(1)[:3].lower()]
            a=datetime.date(y2, mo, int(m.group(2))); b=datetime.date(y2, mo, int(m.group(3)))
            return (a.isoformat(), b.isoformat(), raw)
        except Exception: pass
    # D-D Mon YYYY
    m = re.search(rf'(\d{{1,2}})\s*-\s*(\d{{1,2}})\s+({MON_RE})', s, re.I)
    if m and y2:
        try:
            mo=MONTHS[m.group(3)[:3].lower()]
            return (datetime.date(y2,mo,int(m.group(1))).isoformat(), datetime.date(y2,mo,int(m.group(2))).isoformat(), raw)
        except Exception: pass
    # single Mon D, YYYY
    m = re.search(rf'({MON_RE})\.?\s+(\d{{1,2}})', s, re.I)
    if m and y2:
        try:
            d=datetime.date(y2, MONTHS[m.group(1)[:3].lower()], int(m.group(2))).isoformat()
            return (d,d,raw)
        except Exception: pass
    # D Mon YYYY
    m = re.search(rf'(\d{{1,2}})\s+({MON_RE})', s, re.I)
    if m and y2:
        try:
            d=datetime.date(y2, MONTHS[m.group(2)[:3].lower()], int(m.group(1))).isoformat()
            return (d,d,raw)
        except Exception: pass
    # YYYY-MM-DD ranges and single dates
    m = re.search(r'(20\d\d)\s*-\s*(\d{2})\s*-\s*(\d{2})\s*-\s*(20\d\d)\s*-\s*(\d{2})\s*-\s*(\d{2})', s)
    if m:
        return (f"{m.group(1)}-{m.group(2)}-{m.group(3)}", f"{m.group(4)}-{m.group(5)}-{m.group(6)}", raw)
    m = re.search(r'(20\d\d)\s*-\s*(\d{2})\s*-\s*(\d{2})', s)
    if m:
        d=f"{m.group(1)}-{m.group(2)}-{m.group(3)}"; return (d,d,raw)
    return (None,None,raw)

NUM = re.compile(r'^\s*[~<>]?\s*(\d{1,3}(?:\.\d+)?)\s*%?\s*$')
def pct(s):
    s=clean(s).replace('–','-').replace('—','-')
    if not s or s in {'-','--','*','n/a','N/A','?'}: return None
    m=NUM.match(s)
    if m:
        v=float(m.group(1))
        return v if 0<=v<=100 else None
    m=re.match(r'^\s*(\d{1,3}(?:\.\d+)?)\s*%', s)
    if m:
        v=float(m.group(1)); return v if 0<=v<=100 else None
    return None

def sample(s):
    s=clean(s).replace(',','')
    m=re.search(r'(\d{2,7})', s)
    n=int(m.group(1)) if m else None
    pop=None
    low=clean(s).lower()
    if re.search(r'\blv\b|likely', low): pop='lv'
    elif re.search(r'\brv\b|registered', low): pop='rv'
    elif re.search(r'\ba\b$|adults?', low): pop='a'
    elif re.search(r'\bv\b$|voters', low): pop='v'
    return n, pop

def moe(s):
    s=clean(s)
    m=re.search(r'(\d{1,2}(?:\.\d+)?)\s*(?:%|pp|percentage)?', s)
    return float(m.group(1)) if m else None

SECTION_TAGS=('h1','h2','h3','h4','h5','h6')

def section_path(table):
    """Nearest preceding headings, outer->inner."""
    path={}
    node=table
    # walk up to a section container if parsoid sections are used
    while node is not None:
        prev=node.find_previous(SECTION_TAGS)
        break
    seen=[]
    h=table.find_previous(SECTION_TAGS)
    lastlvl=99
    while h is not None and len(seen)<6:
        lvl=int(h.name[1])
        if lvl<lastlvl:
            seen.append((lvl, clean(h.get_text(' ', strip=True))))
            lastlvl=lvl
        h=h.find_previous(SECTION_TAGS)
    seen.reverse()
    return [s for _,s in seen]

def parse_page(title, html, office_guess):
    soup=BeautifulSoup(html, 'lxml')
    out=[]
    tables=soup.find_all('table')
    for ti,tb in enumerate(tables):
        cls=' '.join(tb.get('class') or [])
        grid=expand(tb)
        if len(grid)<2: continue
        # find header row: a row where >=60% cells are th and it contains a pollster-ish and date-ish label
        hdr_idx=None; header=None
        for r in range(min(6,len(grid))):
            labels=[g[0] for g in grid[r]]
            nth=sum(1 for g in grid[r] if g[1]=='th')
            if nth < max(2, int(0.5*len(grid[r]))): continue
            low=' | '.join(labels).lower()
            if re.search(r'poll source|pollster|poll\b|source', low) and re.search(r'date', low):
                hdr_idx=r; header=labels; break
        if hdr_idx is None: continue
        # merge a second header row for candidate names if first row has blanks
        secs=section_path(tb)
        # column roles
        roles={}
        for c,h in enumerate(header):
            k=norm_key(h)
            if re.search(r'poll source|pollster|^poll$|^source$', k): roles.setdefault('pollster',c)
            elif re.search(r'date', k): roles.setdefault('date',c)
            elif re.search(r'sample', k): roles.setdefault('sample',c)
            elif re.search(r'margin of error|^moe$|^error$|sampling error', k): roles.setdefault('moe',c)
            elif re.search(r'^sponsor', k): roles.setdefault('sponsor',c)
            elif re.search(r'undecided', k): roles.setdefault('undecided',c)
            elif re.search(r'^other|someone else|all others', k): roles.setdefault('other',c)
            elif re.search(r'^lead$|^margin$|^spread$', k): roles.setdefault('lead',c)
        if 'pollster' not in roles or 'date' not in roles: continue
        cand_cols=[(c,clean(header[c])) for c in range(len(header))
                   if c not in roles.values() and not is_meta(header[c]) and clean(header[c])]
        if not cand_cols: continue
        default_year = 2026 if '2026' in title else (2025 if '2025' in title else None)
        for r in range(hdr_idx+1, len(grid)):
            row=grid[r]
            if all(g[1]=='th' for g in row if g[0]): continue
            texts=[g[0] for g in row]
            if len(set(t for t in texts if t))<=1: continue      # spanning note row
            pollster=clean(texts[roles['pollster']]) if roles['pollster']<len(texts) else ''
            if not pollster or is_meta(pollster): continue
            if re.search(r'^(20\d\d |)election|results?$|^average|^final results', pollster.lower()): 
                pass
            draw=texts[roles['date']] if roles['date']<len(texts) else ''
            sd,ed,draw_raw=parse_dates(draw, default_year)
            ss,pop = sample(texts[roles['sample']]) if 'sample' in roles and roles['sample']<len(texts) else (None,None)
            mo = moe(texts[roles['moe']]) if 'moe' in roles and roles['moe']<len(texts) else None
            und = pct(texts[roles['undecided']]) if 'undecided' in roles and roles['undecided']<len(texts) else None
            oth = pct(texts[roles['other']]) if 'other' in roles and roles['other']<len(texts) else None
            spon = clean(texts[roles['sponsor']]) if 'sponsor' in roles and roles['sponsor']<len(texts) else ''
            vals=[]
            for c,name in cand_cols:
                if c>=len(texts): continue
                v=pct(texts[c])
                if v is not None: vals.append((name,v))
            if not vals: continue
            poll_key=f"{title}|{ti}|{r}"
            for name,v in vals:
                out.append(dict(
                    office=office_guess, wiki_page=title, section=' > '.join(secs[-3:]),
                    table_index=ti, row_index=r, poll_id=poll_key,
                    pollster=pollster, sponsor=spon,
                    date_raw=draw_raw, start_date=sd, end_date=ed,
                    sample_size=ss, population=pop, margin_of_error=mo,
                    candidate=name, pct=v, undecided=und, other=oth))
    return out

def office_of(title):
    if 'gubernatorial' in title: return 'Governor'
    if 'Senate' in title: return 'Senate'
    if 'House of Representatives' in title or 'congressional district' in title: return 'House'
    if 'legislative election' in title: return 'Generic ballot'
    return 'Other'

if __name__=='__main__':
    titles=json.load(open('wiki_pages.json'))
    if len(sys.argv)>1 and sys.argv[1]=='test':
        titles=["2026 United States Senate election in Michigan",
                "2026 Georgia gubernatorial election",
                "2026 United States House of Representatives elections in Ohio"]
    rows=[]; stats=[]
    for i,t in enumerate(titles,1):
        try: html=page_html(t)
        except Exception as e:
            print(f"[{i}/{len(titles)}] FETCH FAIL {t}: {e}", flush=True); continue
        if not html:
            print(f"[{i}/{len(titles)}] no html {t}", flush=True); continue
        try: r=parse_page(t, html, office_of(t))
        except Exception as e:
            print(f"[{i}/{len(titles)}] PARSE FAIL {t}: {type(e).__name__} {e}", flush=True); continue
        rows+=r
        np={len(set(x['poll_id'] for x in r))}
        stats.append((t,len(set(x['poll_id'] for x in r)),len(r)))
        print(f"[{i}/{len(titles)}] {t}: polls={len(set(x['poll_id'] for x in r))} rows={len(r)}", flush=True)
    json.dump(rows, open('wiki_rows.json','w'))
    print("\nTOTAL rows:", len(rows), "polls:", len(set(x['poll_id'] for x in rows)),
          "pollsters:", len(set(x['pollster'] for x in rows)))
