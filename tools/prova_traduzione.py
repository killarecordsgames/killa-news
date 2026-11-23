import sys, requests, json
sys.path.insert(0, '.')
from killanews import translator, config
fr = ("Le gouvernement français a annoncé mardi une série de mesures pour soutenir l'économie, après une année marquée par une inflation élevée et une croissance plus faible que prévu. " * 14)
print("lunghezza testo", len(fr), "blocchi", [len(c) for c in translator._chunks(fr)])
s = requests.Session(); s.headers["User-Agent"] = config.USER_AGENT
for q in (fr[:300], fr[:1800]):
    try:
        r = s.get("https://translate.googleapis.com/translate_a/single", params={"client": "gtx", "sl": "auto", "tl": "it", "dt": "t", "q": q}, timeout=20)
        print("GET gtx", len(q), r.status_code, r.text[:150].replace("\n", " "))
    except Exception as e: print("GET gtx errore", e)
    try:
        r = s.post("https://translate.googleapis.com/translate_a/single", params={"client": "gtx", "sl": "auto", "tl": "it", "dt": "t"}, data={"q": q}, timeout=20)
        print("POST gtx", len(q), r.status_code, r.text[:150].replace("\n", " "))
    except Exception as e: print("POST gtx errore", e)
try:
    r = s.get("https://api.mymemory.translated.net/get", params={"q": fr[:480], "langpair": "fr|it"}, timeout=20)
    print("mymemory", r.status_code, r.text[:200])
except Exception as e: print("mymemory errore", e)
try:
    t, l = translator.translate_text(fr, "fr")
    print("translate_text OK", l, t[:120])
except Exception as e:
    print("translate_text ERRORE", repr(e), repr(e.__cause__))
