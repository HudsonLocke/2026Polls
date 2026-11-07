import json, urllib.parse, urllib.request, urllib.error, re, time, os, hashlib, gzip

API="https://en.wikipedia.org/w/api.php"
UA="PollingDatasetCompiler/1.0 (personal research dataset; contact via local operator)"
CACHE="cache"
os.makedirs(CACHE, exist_ok=True)
_last=[0.0]
MIN_GAP=1.1

def _get(url, binary=False):
    key=hashlib.sha256(url.encode()).hexdigest()[:32]
    path=os.path.join(CACHE, key+".gz")
    if os.path.exists(path):
        with gzip.open(path,"rb") as f: return f.read()
    delay=2.0
    for attempt in range(7):
        gap=time.time()-_last[0]
        if gap < MIN_GAP: time.sleep(MIN_GAP-gap)
        _last[0]=time.time()
        req=urllib.request.Request(url, headers={"User-Agent":UA,"Accept-Encoding":"gzip"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw=r.read()
                if r.headers.get("Content-Encoding")=="gzip":
                    raw=gzip.decompress(raw)
            with gzip.open(path,"wb") as f: f.write(raw)
            return raw
        except urllib.error.HTTPError as e:
            if e.code in (429,503,502,504):
                time.sleep(delay); delay=min(delay*2, 60); continue
            if e.code==404: return b""
            raise
        except Exception:
            time.sleep(delay); delay=min(delay*2, 60); continue
    raise RuntimeError("failed: "+url)

def api(**params):
    params.setdefault("format","json")
    params.setdefault("formatversion","2")
    url=API+"?"+urllib.parse.urlencode(params)
    return json.loads(_get(url).decode())

def page_html(title):
    url="https://en.wikipedia.org/api/rest_v1/page/html/"+urllib.parse.quote(title.replace(" ","_"), safe="")
    b=_get(url)
    return b.decode("utf-8","replace") if b else ""

def allpages(prefix):
    out=[]; cont=None
    while True:
        p=dict(action="query", list="allpages", apprefix=prefix, aplimit="500", apnamespace=0)
        if cont: p["apcontinue"]=cont
        d=api(**p)
        out += [x["title"] for x in d["query"]["allpages"]]
        cont=d.get("continue",{}).get("apcontinue")
        if not cont: break
    return out

def search(q, cap=1000):
    out=[]; off=0
    while True:
        d=api(action="query", list="search", srsearch=q, srlimit="500", sroffset=off, srnamespace=0)
        out += [x["title"] for x in d["query"]["search"]]
        c=d.get("continue",{}).get("sroffset")
        if c is None or len(out)>=cap: break
        off=c
    return out

def links(title):
    out=[]; cont=None
    while True:
        p=dict(action="query", prop="links", titles=title, pllimit="500", plnamespace=0)
        if cont: p["plcontinue"]=cont
        d=api(**p)
        for pg in d["query"]["pages"]:
            out += [l["title"] for l in pg.get("links",[])]
        cont=d.get("continue",{}).get("plcontinue")
        if not cont: break
    return out
