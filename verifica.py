import json, time, concurrent.futures as cf, feedparser, requests
from candidati import C
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KILLA-NEWS/1.2 (+https://www.killarecordsgames.com/killa-news)"}
def check(url):
    try:
        r = requests.get(url, headers=UA, timeout=25)
        f = feedparser.parse(r.content)
        n = len(f.entries)
        newest = ""
        for e in f.entries:
            t = e.get("published_parsed") or e.get("updated_parsed")
            if t:
                s = time.strftime("%Y-%m-%d", t)
                newest = max(newest, s)
        return {"url": url, "http": r.status_code, "voci": n, "ultima": newest, "titolo": (f.feed.get("title") or "")[:60]}
    except Exception as ex:
        return {"url": url, "errore": str(ex)[:120]}
urls = [u for c in C for u in c[5]]
with cf.ThreadPoolExecutor(16) as ex:
    res = list(ex.map(check, urls))
print("RISULTATI_JSON_INIZIO")
print(json.dumps(res, ensure_ascii=False))
print("RISULTATI_JSON_FINE")
