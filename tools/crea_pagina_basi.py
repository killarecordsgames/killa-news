"""Genera sito/basi-main.html e promo/basi/beatstars.md da promo/basi/basi.json."""
import json, html, pathlib
R = pathlib.Path(__file__).resolve().parent.parent
basi = json.loads((R / "promo/basi/basi.json").read_text(encoding="utf-8"))
CDN = "https://cdn.jsdelivr.net/gh/killarecordsgames/killa-news@main/promo/basi/"
e = html.escape
schede = []
for b in [x for x in basi if x.get("payhip")]:
    t = e(b["titolo"])
    schede.append(f'''      <li class="base-scheda">
        <article aria-labelledby="base-{b["id"]}">
          <img class="base-copertina" src="{CDN}{b["id"]}.jpg" width="900" height="900" loading="lazy" alt="Copertina di {t}: {e(b["alt"])}.">
          <div>
            <h3 id="base-{b["id"]}">{t}</h3>
            <p class="base-info">{e(b["genere"])} · {b["bpm"]} BPM · {e(b["tonalita"])} · {e(b["mood"])}</p>
            <p>{e(b["descr"])}</p>
            <audio controls preload="none" src="{CDN}anteprime/{b["id"]}.mp3" aria-label="Anteprima di {t}, con il tag vocale Killa on the beat"></audio>
            <ul class="brano-link">
              <li><a class="button button-primary" href="{b["payhip"]}" target="_blank" rel="noopener noreferrer">Acquista {t}<span class="sr-only">: licenza MP3 o WAV su Payhip, si apre in una nuova scheda</span></a></li>
              <li><a class="button" href="mailto:info@killarecordsgames.com?subject={e("Licenza base " + b["titolo"])}">Chiedi l'esclusiva<span class="sr-only"> di {t} via email</span></a></li>
            </ul>
          </div>
        </article>
      </li>''')
pagina = f'''  <main id="contenuto" class="container brano">
    <p class="eyebrow">MUSIC · BASI</p>
    <h1>Basi Killa On The Beat</h1>
    <p class="brano-sottotitolo">Basi trap, drill, afro e rap melodico da usare per le tue canzoni.</p>
    <p>Ascolta le anteprime, scegli la base e la licenza che ti serve: MP3 da 19,99 €, WAV da 39,99 € oppure l'esclusiva da 299 €. Paghi con PayPal o con la carta e ricevi i file subito dopo l'acquisto. Puoi vedere tutte le basi anche sul <a href="https://payhip.com/KillaOnTheBeat">negozio Payhip di Killa On The Beat</a>. In tutte le licenze basta scrivere «Prod. Killa On The Beat» nei crediti. <a href="/licenze-basi">Leggi cosa comprende ogni licenza</a>.</p>
    <p class="brano-nota">Le anteprime contengono il tag vocale «Killa on the beat», che non c'è nei file acquistati. Le basi sono create con l'aiuto dell'intelligenza artificiale e scelte e sistemate a mano dal produttore.</p>

    <section aria-labelledby="basi-elenco" class="brano-blocco">
      <h2 id="basi-elenco">Le basi disponibili ({len([x for x in basi if x.get("payhip")])})</h2>
      <ul class="basi-lista">
{chr(10).join(schede)}
      </ul>
    </section>

    <section aria-labelledby="basi-domande" class="brano-blocco brano-testo">
      <h2 id="basi-domande">Domande frequenti</h2>
      <h3>Posso pubblicare la canzone su Spotify?</h3>
      <p>Sì, con tutte le licenze. Con la licenza MP3 fino a 10.000 ascolti, con la WAV fino a 100.000, con l'esclusiva senza limiti.</p>
      <h3>Cosa succede se supero il limite?</h3>
      <p>Passi alla licenza superiore pagando solo la differenza.</p>
      <h3>Posso avere una base su misura?</h3>
      <p>Sì, scrivi a <a href="mailto:info@killarecordsgames.com">info@killarecordsgames.com</a> con genere, BPM e atmosfera che cerchi.</p>
    </section>
    <script>
      // Una sola anteprima alla volta: quando ne parte una, le altre si fermano.
      document.addEventListener("play", function (e) {{
        document.querySelectorAll("audio").forEach(function (a) {{ if (a !== e.target) a.pause(); }});
      }}, true);
    </script>
  </main>
'''
(R / "sito/basi-main.html").write_text(pagina, encoding="utf-8")

md = ["# Schede per BeatStars\n", "Prezzi: MP3 lease 19,99 € · WAV lease 39,99 € · Exclusive 299 €. Crediti: Prod. Killa On The Beat. Dichiarare l'aiuto dell'IA dove BeatStars lo chiede.\n"]
for b in basi:
    md.append(f'''## {b["titolo"]}
- File copertina: copertine/{b["id"]}.jpg (3000x3000)
- Genere: {b["genere"]} · BPM: {b["bpm"]} · Tonalità: {b["key_en"]}
- Tag: {", ".join(b["tag"])}
- Descrizione (IT): {b["descr"]} Prod. Killa On The Beat.
''')
(R / "promo/basi/beatstars.md").write_text("\n".join(md), encoding="utf-8")
print("ok")
