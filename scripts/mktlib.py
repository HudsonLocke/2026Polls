import json, urllib.request, urllib.error, urllib.parse, os, time, hashlib, gzip

CACHE="cache_mkt"; os.makedirs(CACHE, exist_ok=True)
UA="PollingDatasetCompiler/1.0 (personal research; prediction-market history join)"
_last=[0.0]; MIN_GAP=0.6

def get(url, gap=None, cache=True):
    key=hashlib.sha256(url.encode()).hexdigest()[:32]
    path=os.path.join(CACHE,key+".gz")
    if cache and os.path.exists(path):
        with gzip.open(path,"rb") as f: return f.read()
    delay=1.5
    for attempt in range(8):
        g=time.time()-_last[0]; mg=gap or MIN_GAP
        if g<mg: time.sleep(mg-g)
        _last[0]=time.time()
        req=urllib.request.Request(url, headers={"User-Agent":UA,"Accept":"application/json","Accept-Encoding":"gzip"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw=r.read()
                if r.headers.get("Content-Encoding")=="gzip": raw=gzip.decompress(raw)
            if cache:
                with gzip.open(path,"wb") as f: f.write(raw)
            return raw
        except urllib.error.HTTPError as e:
            body=b''
            try: body=e.read()[:200]
            except Exception: pass
            if e.code in (429,500,502,503,504):
                time.sleep(delay); delay=min(delay*2,45); continue
            return b'{"__http_error__":%d,"__body__":%s}' % (e.code, json.dumps(body.decode('utf-8','replace')).encode())
        except Exception:
            time.sleep(delay); delay=min(delay*2,45); continue
    return b'{"__failed__":true}'

def getj(url, **kw):
    try: return json.loads(get(url, **kw).decode())
    except Exception: return {}

KAL="https://api.elections.kalshi.com/trade-api/v2"
GAMMA="https://gamma-api.polymarket.com"
CLOB="https://clob.polymarket.com"

class FetchError(Exception): pass

def kalshi_markets(series):
    out=[]; cursor=None
    while True:
        u=f"{KAL}/markets?series_ticker={series}&limit=200"
        if cursor: u+=f"&cursor={urllib.parse.quote(cursor)}"
        d=getj(u)
        if d.get('__failed__') or d.get('__http_error__'):
            raise FetchError(f"{series}: {d.get('__http_error__') or 'failed'}")
        if 'markets' not in d:
            raise FetchError(f"{series}: no markets key")
        out += d.get('markets') or []
        cursor=d.get('cursor')
        if not cursor or len(out)>1000: break
    return out

def kalshi_candles(series, ticker, start_ts, end_ts, period=1440):
    """Kalshi caps the span per request, so walk it in chunks."""
    pts=[]; step=60*60*24*180
    t=start_ts
    while t < end_ts:
        e=min(t+step, end_ts)
        d=getj(f"{KAL}/series/{series}/markets/{ticker}/candlesticks"
               f"?start_ts={t}&end_ts={e}&period_interval={period}")
        cs=d.get('candlesticks') or []
        pts += cs
        t=e
    return pts

def pm_search(q, limit=12):
    d=getj(f"{GAMMA}/public-search?q={urllib.parse.quote(q)}&limit_per_type={limit}")
    return (d.get('events') or []) if isinstance(d,dict) else []

def pm_event(slug):
    d=getj(f"{GAMMA}/events?slug={urllib.parse.quote(slug)}")
    if isinstance(d,list) and d: return d[0]
    return d if isinstance(d,dict) and d.get('markets') else {}

def pm_history(token, fidelity=1440):
    d=getj(f"{CLOB}/prices-history?market={token}&interval=max&fidelity={fidelity}")
    return d.get('history') or []
