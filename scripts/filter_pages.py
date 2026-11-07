import json, re
from wikilib import search

US = """Alabama Alaska Arizona Arkansas California Colorado Connecticut Delaware Florida Georgia
Hawaii Idaho Illinois Indiana Iowa Kansas Kentucky Louisiana Maine Maryland Massachusetts Michigan
Minnesota Mississippi Missouri Montana Nebraska Nevada Ohio Oklahoma Oregon Pennsylvania
Tennessee Texas Utah Vermont Virginia Washington Wisconsin Wyoming""".split()
US += ["New Hampshire","New Jersey","New Mexico","New York","North Carolina","North Dakota",
       "Rhode Island","South Carolina","South Dakota","West Virginia","District of Columbia",
       "Puerto Rico","Guam","American Samoa","Northern Mariana Islands","United States Virgin Islands"]
USset=set(US)

cand=set(json.load(open("wiki_candidates.json")))

# extra discovery: district-level + special elections
for q in ['intitle:"2026" intitle:"congressional district"',
          'intitle:"2026" intitle:"special election" intitle:"congressional"',
          'intitle:"2025" intitle:"congressional district" intitle:"special"']:
    try: cand |= set(search(q)); print("search ok:", q)
    except Exception as e: print("FAIL", q, e)

keep=set()
for t in cand:
    # federal Senate
    if re.match(r'^2026 United States Senate (election|elections|special election)', t): keep.add(t); continue
    # federal House
    if re.match(r'^2026 United States House of Representatives (election|elections)', t): keep.add(t); continue
    # congressional district pages (incl. 2025/2026 specials)
    if re.search(r"congressional district (special )?election", t) and re.match(r'^(2025|2026)\b', t): keep.add(t); continue
    # governor: 2026 <US state> gubernatorial election
    m=re.match(r'^2026 ([A-Z][A-Za-z ]+?) gubernatorial election$', t)
    if m and m.group(1) in USset: keep.add(t); continue
    if t=="2026 United States gubernatorial elections": keep.add(t); continue
    if t=="Opinion polling for the 2026 United States legislative election": keep.add(t); continue

# drop state-legislature and ratings pages
keep={t for t in keep if 'ratings' not in t.lower()}
# explicit extras worth having
keep |= {"2026 United States Senate elections","2026 United States House of Representatives elections",
         "2026 United States gubernatorial elections","2026 United States elections"}

print("\nkept:", len(keep))
json.dump(sorted(keep), open("wiki_pages.json","w"), indent=1)
import collections
print("senate:", sum(1 for t in keep if 'Senate' in t))
print("house:",  sum(1 for t in keep if 'House of Representatives' in t))
print("district:",sum(1 for t in keep if 'congressional district' in t))
print("gov:",    sum(1 for t in keep if 'gubernatorial' in t))
