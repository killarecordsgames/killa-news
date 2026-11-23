"""Il giornale parlato di KILLA NEWS: ogni mattina i titoli principali del giorno letti da una voce chiara.

Gira su GitHub Actions. Legge i feed RSS delle testate italiane del catalogo di KILLA NEWS
(solo i titoli, con il nome del giornale), crea l'audio con Piper e aggiorna il feed del podcast.
Uso: python podcast/giornale_parlato.py CARTELLA_PUBBLICA"""
import calendar
import datetime as dt
import email.utils
import html
import json
import os
import re
import subprocess
import sys
import time
import wave
from xml.sax.saxutils import escape

import feedparser
import numpy as np

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(QUI)
SITO = "https://killarecordsgames.github.io/killa-news/podcast"
ROMA = dt.timezone(dt.timedelta(hours=1))  # orario invernale; per la data basta
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
        "ottobre", "novembre", "dicembre"]
GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]

SEZIONI = [  # (titolo letto, prefissi di categoria, quante notizie)
    ("Prima pagina", ("evidenza",), 6),
    ("Italia", ("italia", "cronaca"), 5),
    ("Dal mondo", ("esteri",), 5),
    ("Economia", ("economia",), 4),
    ("Sport", ("sport",), 5),
    ("Tecnologia", ("tecnologia",), 3),
]
PREFERITE = ["ansa", "agi", "rainews", "adnkronos", "ilpost", "corriere", "repubblica", "sole24ore", "lastampa"]
TACI = re.compile(r"\b(VIDEO|FOTO|LIVE|DIRETTA|PODCAST|GALLERY|INTERVISTA)\b\s*[:|\-–]?\s*", re.I)
PAROLE_VUOTE = set("il lo la i gli le un una di a da in con su per tra fra e o ma che non è ai al alla alle agli del della dei delle degli nel nella nei nelle sul sulla dopo come piu più".split())


def pulisci(titolo: str, testata: str) -> str:
    t = html.unescape(re.sub(r"<[^>]+>", " ", titolo or ""))
    t = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", t)
    t = TACI.sub("", t)
    t = re.sub(r"\s*[-|–]\s*(%s).*$" % re.escape(testata), "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -–|:")
    if t and t[-1] not in ".?!»\"":
        t += "."
    return t


def parole(t):
    return {w for w in re.findall(r"[a-zàèéìòù0-9]{4,}", t.lower()) if w not in PAROLE_VUOTE}


def raccogli():
    cat = json.load(open(os.path.join(RADICE, "data", "sources.json"), encoding="utf-8"))["fonti"]
    limite = time.time() - 26 * 3600
    notizie = []
    for f in cat:
        if f.get("lingua", "it") != "it" or f.get("gruppo") == "Locali":
            continue
        for feed in f.get("feed", []):
            categoria = "evidenza" if feed.get("evidenza") else (feed.get("categoria") or "generale")
            try:
                d = feedparser.parse(feed["url"], agent="KillaNews-Podcast/1.0 (+https://www.killarecordsgames.com)")
            except Exception as exc:
                print("feed non letto", feed["url"], exc)
                continue
            for i, e in enumerate(d.entries[:25]):
                pub = e.get("published_parsed") or e.get("updated_parsed")
                quando = calendar.timegm(pub) if pub else time.time()
                if quando < limite:
                    continue
                titolo = pulisci(e.get("title", ""), f["nome"])
                if len(titolo) < 25 or len(titolo) > 220:
                    continue
                notizie.append({"titolo": titolo, "testata": f["nome"], "id": f["id"], "cat": categoria,
                                "pos": i, "quando": quando, "parole": parole(titolo)})
    print("titoli raccolti:", len(notizie))
    return notizie


def scegli(notizie):
    # quante testate parlano della stessa notizia: più ne parlano, più è importante
    for n in notizie:
        n["peso"] = sum(1 for m in notizie if m is not n and m["id"] != n["id"]
                        and len(n["parole"] & m["parole"]) >= 3)
    usati, scaletta = [], []
    for nome, prefissi, quante in SEZIONI:
        candidati = [n for n in notizie if n["cat"].startswith(prefissi)]
        if nome == "Prima pagina":
            candidati += [n for n in notizie if n["cat"] == "generale"]
        candidati.sort(key=lambda n: (-n["peso"], n["pos"],
                                      PREFERITE.index(n["id"]) if n["id"] in PREFERITE else 99, -n["quando"]))
        scelte = []
        for n in candidati:
            if any(len(n["parole"] & u["parole"]) >= 3 or n["titolo"] == u["titolo"] for u in usati):
                continue
            scelte.append(n)
            usati.append(n)
            if len(scelte) >= quante:
                break
        if scelte:
            scaletta.append((nome, scelte))
    return scaletta


def testo_puntata(oggi, scaletta):
    data = f"{GIORNI[oggi.weekday()]} {oggi.day} {MESI[oggi.month - 1]} {oggi.year}"
    blocchi = [("voce", f"Buongiorno! È {data}. Questo è il giornale parlato di Killa News, "
                        "i titoli principali del giorno, a cura di Killa Records.")]
    for nome, notizie in scaletta:
        blocchi.append(("stacco", ""))
        blocchi.append(("voce", nome + "."))
        for n in notizie:
            blocchi.append(("voce", f"{n['testata']}. {n['titolo']}"))
    blocchi.append(("stacco", ""))
    blocchi.append(("voce", "Per leggere gli articoli completi, scarica gratis Killa News, l'edicola digitale "
                            "accessibile, da killarecordsgames punto com. Oppure chiedi le notizie al nostro bot "
                            "su Telegram. Il giornale parlato torna domani mattina. Buona giornata!"))
    return data, blocchi


SR = 22050


def tono(freq, durata, vol=0.25):
    t = np.arange(int(SR * durata)) / SR
    s = np.sin(2 * np.pi * freq * t + 1.5 * np.sin(2 * np.pi * freq * 3 * t) * np.exp(-t * 6))
    return s * np.exp(-t * 4) * vol


def jingle(lungo=True):
    note = [72, 76, 79, 84] if lungo else [79, 84]
    out = np.zeros(int(SR * (1.6 if lungo else 0.7)))
    for i, m in enumerate(note):
        f = 440 * 2 ** ((m - 69) / 12)
        s = tono(f, 0.9)
        k = int(i * 0.14 * SR)
        out[k:k + len(s)] += s[: len(out) - k]
    return out


def silenzio(sec):
    return np.zeros(int(SR * sec))


def voce(testo, modello, cartella, n):
    wav = os.path.join(cartella, f"riga_{n}.wav")
    subprocess.run(["piper", "-m", modello, "--length_scale", "1.05", "--sentence_silence", "0.35",
                    "--output_file", wav], input=testo.replace("Killa News", "Killa News").encode("utf-8"),
                   check=True, capture_output=True)
    with wave.open(wav) as w:
        sr = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    if sr != SR:
        a = np.interp(np.arange(0, len(a), sr / SR), np.arange(len(a)), a)
    return a


def crea_audio(blocchi, modello, cartella, mp3):
    pezzi = [jingle(True), silenzio(0.3)]
    for i, (tipo, testo) in enumerate(blocchi):
        if tipo == "stacco":
            pezzi += [silenzio(0.25), jingle(False), silenzio(0.15)]
        else:
            pezzi += [voce(testo, modello, cartella, i), silenzio(0.55)]
    pezzi += [jingle(True), silenzio(0.5)]
    a = np.concatenate(pezzi)
    a = a / (np.max(np.abs(a)) + 1e-9) * 0.9
    wav = os.path.join(cartella, "puntata.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((a * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af",
                    "highpass=f=70,acompressor=threshold=-18dB:ratio=3:makeup=3,loudnorm=I=-16:TP=-1.5",
                    "-ar", "44100", "-ac", "1", "-b:a", "96k", mp3], check=True)
    return len(a) / SR


def aggiorna_feed(pubblica, episodi):
    voci = []
    for e in episodi:
        voci.append(f"""    <item>
      <title>{escape(e['titolo'])}</title>
      <description>{escape(e['descrizione'])}</description>
      <itunes:summary>{escape(e['descrizione'])}</itunes:summary>
      <enclosure url="{SITO}/{e['file']}" length="{e['byte']}" type="audio/mpeg"/>
      <guid isPermaLink="false">killanews-giornale-{e['data']}</guid>
      <pubDate>{e['pubdate']}</pubDate>
      <itunes:duration>{int(e['durata'])}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
      <itunes:episodeType>full</itunes:episodeType>
    </item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Il giornale parlato di KILLA NEWS</title>
    <link>https://www.killarecordsgames.com/giornale-parlato</link>
    <atom:link href="{SITO}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>it</language>
    <copyright>Killa Records</copyright>
    <itunes:author>Killa Records</itunes:author>
    <itunes:owner><itunes:name>Killa Records</itunes:name><itunes:email>info@killarecordsgames.com</itunes:email></itunes:owner>
    <description>Ogni mattina, in pochi minuti, i titoli principali del giorno dai giornali italiani, letti da una voce chiara. Un servizio gratuito di KILLA NEWS, l'edicola digitale accessibile di Killa Records, pensata anche per le persone non vedenti.</description>
    <itunes:summary>Ogni mattina i titoli principali del giorno dai giornali italiani, letti da una voce chiara. Un servizio gratuito di KILLA NEWS, l'edicola digitale accessibile di Killa Records.</itunes:summary>
    <itunes:image href="{SITO}/copertina.png"/>
    <image><url>{SITO}/copertina.png</url><title>Il giornale parlato di KILLA NEWS</title><link>https://www.killarecordsgames.com/giornale-parlato</link></image>
    <itunes:category text="News"><itunes:category text="Daily News"/></itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
{chr(10).join(voci)}
  </channel>
</rss>
"""
    open(os.path.join(pubblica, "feed.xml"), "w", encoding="utf-8").write(feed)


def main():
    pubblica = sys.argv[1]
    modello = os.environ.get("PIPER_MODELLO", "paola.onnx")
    os.makedirs(pubblica, exist_ok=True)
    tmp = os.path.join(QUI, "tmp")
    os.makedirs(tmp, exist_ok=True)
    oggi = dt.datetime.now(ROMA).date()
    scaletta = scegli(raccogli())
    if sum(len(n) for _, n in scaletta) < 10:
        print("Troppe poche notizie, puntata non creata")
        sys.exit(1)
    data_letta, blocchi = testo_puntata(oggi, scaletta)
    nome = f"giornale-{oggi.isoformat()}.mp3"
    durata = crea_audio(blocchi, modello, tmp, os.path.join(pubblica, nome))
    indice_p = os.path.join(pubblica, "episodi.json")
    episodi = json.load(open(indice_p, encoding="utf-8")) if os.path.exists(indice_p) else []
    episodi = [e for e in episodi if e["data"] != oggi.isoformat()]
    descr = "I titoli di oggi: " + " ".join(f"{nome_s}: " + "; ".join(n["titolo"].rstrip(".") for n in ns[:2]) + "."
                                            for nome_s, ns in scaletta[:3])
    episodi.insert(0, {"data": oggi.isoformat(), "titolo": f"Il giornale parlato di {data_letta}",
                       "descrizione": descr[:900], "file": nome,
                       "byte": os.path.getsize(os.path.join(pubblica, nome)), "durata": durata,
                       "pubdate": email.utils.formatdate(time.time(), usegmt=True),
                       "scaletta": [[s, [f"{n['testata']}: {n['titolo']}" for n in ns]] for s, ns in scaletta]})
    tenuti = episodi[:30]
    for e in episodi[30:]:
        try:
            os.remove(os.path.join(pubblica, e["file"]))
        except OSError:
            pass
    json.dump(tenuti, open(indice_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    aggiorna_feed(pubblica, tenuti)
    json.dump(tenuti[0], open(os.path.join(pubblica, "ultima.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("Puntata creata:", nome, round(durata), "secondi")
    for s, ns in scaletta:
        print("##", s)
        for n in ns:
            print("  -", n["testata"], "|", n["titolo"])


if __name__ == "__main__":
    main()
