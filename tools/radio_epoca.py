"""Scarica da Internet Archive (raccolta 78 giri) registrazioni d'epoca di dominio pubblico
per la Killa Radio. Solo canzoni con autori morti da oltre 70 anni e incisioni pubblicate
prima del 1940 (in Europa le incisioni pubblicate prima del 1963 sono di dominio pubblico)."""
import json, os, subprocess, sys, urllib.parse, urllib.request

CANZONI = [  # (titolo da cercare, interprete, titolo da mostrare)
    ("sole mio", "Caruso", "'O sole mio"),
    ("Santa Lucia", "Caruso", "Santa Lucia"),
    ("Mattinata", "Caruso", "Mattinata"),
    ("Core 'ngrato", "Caruso", "Core 'ngrato"),
    ("Addio a Napoli", "Caruso", "Addio a Napoli"),
    ("Vucchella", "Caruso", "'A vucchella"),
    ("Torna a Surriento", "Gigli", "Torna a Surriento"),
    ("Marechiare", "Schipa", "Marechiare"),
    ("Funiculi", "", "Funiculì funiculà"),
]
MONDO = [
    ("Maple Leaf Rag", "", "Maple Leaf Rag (Scott Joplin)"),
    ("Entertainer", "Joplin", "The Entertainer (Scott Joplin)"),
    ("Over There", "", "Over There"),
    ("After You've Gone", "", "After You've Gone"),
    ("Bill Bailey", "", "Bill Bailey, Won't You Please Come Home"),
    ("Cumparsita", "", "La Cumparsita"),
    ("Por una cabeza", "Gardel", "Por una cabeza"),
    ("Mi Buenos Aires querido", "Gardel", "Mi Buenos Aires querido"),
    ("Le temps des cerises", "", "Le temps des cerises"),
    ("Choclo", "", "El Choclo"),
    ("Dark Eyes", "", "Ochi chornye (Occhi neri)"),
    ("La Paloma", "", "La Paloma"),
]
UA = {"User-Agent": "KillaRadio/1.0 (killarecordsgames.com)"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def cerca(titolo, artista):
    q = f'collection:(78rpm) AND mediatype:audio AND title:("{titolo}")'
    if artista:
        q += f" AND (creator:({artista}) OR title:({artista}))"
    url = ("https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
        {"q": q, "fl[]": ["identifier", "title", "creator", "date", "year"], "rows": 8, "output": "json"}, doseq=True))
    return json.loads(get(url))["response"]["docs"]


def main(out, elenco="italia"):
    os.makedirs(out, exist_ok=True)
    risultati = []
    canzoni, prefisso = (MONDO, "mondo") if elenco == "mondo" else (CANZONI, "epoca")
    for n, (titolo, artista, mostra) in enumerate(canzoni, start=1):
        try:
            docs = cerca(titolo, artista)
        except Exception as exc:
            print("ERRORE ricerca", titolo, exc); continue
        scelto = None
        for d in docs:
            anno = str(d.get("year") or d.get("date") or "")[:4]
            if anno.isdigit() and int(anno) >= 1940:
                continue
            scelto = d; break
        if not scelto:
            print("NESSUN RISULTATO", titolo, [(d["identifier"], d.get("year")) for d in docs]); continue
        ident = scelto["identifier"]
        meta = json.loads(get(f"https://archive.org/metadata/{ident}"))
        mp3 = [f["name"] for f in meta.get("files", []) if f["name"].lower().endswith(".mp3")]
        # il file "restored" o il primo mp3 senza "_78_" di altre facciate
        mp3.sort(key=lambda s: (("restored" not in s.lower()), len(s)))
        if not mp3:
            print("NESSUN MP3", ident); continue
        src = os.path.join(out, f"raw{n:02d}.mp3")
        open(src, "wb").write(get(f"https://archive.org/download/{ident}/{urllib.parse.quote(mp3[0])}"))
        dst = os.path.join(out, f"{prefisso}{n:02d}.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", "loudnorm=I=-14:TP=-1:LRA=11",
                        "-ar", "44100", "-ac", "2", "-b:a", "128k", dst], check=True)
        os.remove(src)
        durata = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", dst],
                                      capture_output=True, text=True).stdout)
        creator = scelto.get("creator")
        creator = ", ".join(creator) if isinstance(creator, list) else (creator or "")
        r = {"titolo": mostra, "artista": creator, "file": "epoca/" + os.path.basename(dst), "durata": round(durata, 1),
             "anno": scelto.get("year") or scelto.get("date"), "fonte": f"https://archive.org/details/{ident}",
             "titolo_originale": scelto.get("title")}
        risultati.append(r)
        print("OK", json.dumps(r, ensure_ascii=False))
    json.dump(risultati, open(os.path.join(out, prefisso + ".json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "epoca", sys.argv[2] if len(sys.argv) > 2 else "italia")
