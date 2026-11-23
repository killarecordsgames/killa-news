import requests, urllib.parse
fr = "Le gouvernement français a annoncé mardi une série de mesures pour soutenir l'économie."
UAS = {"killa": "KillaNews/1.5 (+https://www.killarecordsgames.com)", "browser": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"}
def t(nome, fn):
    try:
        r = fn(); print(nome, r.status_code, r.text[:160].replace("\n", " "))
    except Exception as e: print(nome, "ERRORE", e)
for k, ua in UAS.items():
    h = {"User-Agent": ua}
    t(f"gtx-{k}", lambda: requests.get("https://translate.googleapis.com/translate_a/single", params={"client": "gtx", "sl": "auto", "tl": "it", "dt": "t", "q": fr}, headers=h, timeout=15))
    t(f"dict-chrome-ex-{k}", lambda: requests.post("https://clients5.google.com/translate_a/t", params={"client": "dict-chrome-ex", "sl": "auto", "tl": "it"}, data={"q": fr}, headers=h, timeout=15))
    t(f"google-m-{k}", lambda: requests.get("https://translate.google.com/m", params={"sl": "auto", "tl": "it", "q": fr}, headers=h, timeout=15))
for inst in ["https://lingva.ml", "https://lingva.lunar.icu", "https://translate.plausibility.cloud", "https://lingva.garudalinux.org"]:
    t("lingva " + inst, lambda: requests.get(inst + "/api/v1/auto/it/" + urllib.parse.quote(fr, safe=""), timeout=15))
t("mymemory-autodetect", lambda: requests.get("https://api.mymemory.translated.net/get", params={"q": fr, "langpair": "autodetect|it", "de": "info@killarecordsgames.com"}, timeout=15))
t("mymemory-fr-de", lambda: requests.get("https://api.mymemory.translated.net/get", params={"q": fr, "langpair": "fr|it", "de": "info@killarecordsgames.com"}, timeout=15))
