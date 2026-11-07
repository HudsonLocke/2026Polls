import json, re
from wikilib import allpages, search, links

cand=set()
for p in ["2026 United States Senate election",
          "2026 United States Senate special election",
          "2026 United States House of Representatives election",
          "Opinion polling for the 2026",
          "2026 United States gubernatorial"]:
    try: cand |= set(allpages(p)); print("prefix ok:", p)
    except Exception as e: print("prefix FAIL", p, e)

for q in ['intitle:"2026" intitle:"gubernatorial election"',
          'intitle:"2026" intitle:"Senate election"',
          'intitle:"2026" intitle:"House of Representatives election"',
          'intitle:"2026" intitle:"Opinion polling"']:
    try: cand |= set(search(q)); print("search ok:", q)
    except Exception as e: print("search FAIL", q, e)

for hub in ["2026 United States gubernatorial elections",
            "2026 United States Senate elections",
            "2026 United States House of Representatives elections",
            "2026 United States elections"]:
    try:
        for t in links(hub):
            if re.search(r'\b2026\b', t) and re.search(r'(gubernatorial|Senate election|House of Representatives election|Opinion polling)', t):
                cand.add(t)
        print("hub ok:", hub)
    except Exception as e: print("hub FAIL", hub, e)

bad = re.compile(r'(Brazil|Goiás|Pernambuco|Israel|Victorian|South Australian|Japanese|Hungarian|Philippine|Colombian|Peruvian|Chilean|Mexican|Costa Rica|Bolivia|Ecuador|Honduras|Haiti|Indian|Tamil|Kerala|Bengal|Assam|Punjab|Scottish|Welsh|Senedd|Northern Ireland|Dutch|Swedish|Italian|Portuguese|Cypriot|Bosnian|Serbian|Moldovan|Armenian|Iraqi|Nepal|Bangladesh|Fijian|Vanuatu|Samoa|Papua|Jamaican|Trinidad|Guyana|Barbados|Bahamas|Belize|Suriname|Grenada|Dominica|Antigua|Ukrainian|Russian|Czech|Slovak|Polish|Austrian|Danish|Finnish|Norwegian|Irish general|Maltese|Latvian|Estonian|Lithuanian|Bulgarian|Romanian|Croatian|Slovenian|Albanian|Macedonian|Montenegr|Georgian parliament|Kazakh|Turkish|Lebanese|Jordan|Egypt|Tunisia|Morocco|Algeria|Nigeria|Kenya|Ghana|Uganda|Tanzania|Zambia|Zimbabwe|Malawi|Botswana|Namibia|South African|Ethiopia|Somalia|Sudan|Senegal|Ivor|Cameroon|Gabon|Congo|Angola|Mozambique|Madagascar|Mauritius|Seychelles|Thai|Vietnam|Cambodia|Laos|Myanmar|Malaysian|Singapore|Indonesian|Korean|Taiwan|Mongolia|Kyrgyz|Uzbek|Tajik|Turkmen|Azerbaijan|Belarus|Cuban|Venezuelan|Argentine|Uruguay|Paraguay|Panama|Nicaragua|Guatemala|El Salvador|Dominican Republic)', re.I)
cand = {t for t in cand if not bad.search(t)}
cand = {t for t in cand if re.search(r'\b(2025|2026)\b', t)}
cand = {t for t in cand if not t.startswith(("List of","Category:","Template:"))}

print("\ncandidate pages:", len(cand))
json.dump(sorted(cand), open("wiki_candidates.json","w"), indent=1)
