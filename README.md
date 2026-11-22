# KILLA NEWS 1.3.0

**Killa Records** · *L'informazione, senza barriere.*

KILLA NEWS è un'edicola digitale per Windows 10 e 11 pensata per persone non vedenti, ipovedenti e per chi usa un lettore di schermo. Riunisce in un solo programma giornali italiani, internazionali e locali. Ogni funzione si usa da tastiera, senza mouse. La versione 1.0.0 è gratuita.

---

## 1. Avvio rapido

### Modo A: installatore o versione portatile (consigliato per gli utenti)

1. Eseguire `KillaNews_1.0.0_Installazione.exe` e seguire la procedura guidata. È possibile scegliere la cartella, aggiungere un collegamento sul desktop e un collegamento nel menu Start. Il programma si disinstalla da Impostazioni di Windows > App.
2. In alternativa, estrarre `KillaNews_1.0.0_Portatile.zip` e avviare `KillaNews_Portatile.exe`. Non serve installarlo.

Il paragrafo 3 spiega come si creano questi due file.

### Modo B: dal codice sorgente

1. Installare **Python 3.11, 3.12 o 3.13 a 64 bit** da python.org. Durante l'installazione spuntare «Add python.exe to PATH».
2. Fare doppio clic su `AVVIA_KILLA_NEWS.bat`. Al primo avvio installa da solo le dipendenze (wxPython, feedparser, requests, lxml, trafilatura, pywin32), poi apre il programma.

In alternativa, da riga di comando:

```
py -m pip install -r requirements.txt
py main.py
```

---

## 2. Come si usa

La finestra ha due riquadri:

- **a sinistra, il menu delle sezioni**: Prima pagina, Tutti i giornali, Italia, Giornali internazionali, Cronaca, Economia e finanza, Sport, Tecnologia, Cultura e spettacolo, Salute e benessere, Giornali locali, Articoli salvati, Cronologia, Cerca, Impostazioni;
- **a destra, l'elenco delle notizie**. Ogni riga riporta titolo, testata, data, categoria, stato e descrizione.

Ci si sposta tra i riquadri con **F6** (oppure Tab).

L'ultima sezione del menu, **Killa Records**, è presente anche nella barra dei menu in alto. Contiene: Segnala un problema (apre il programma di posta con la segnalazione già scritta per info@killarecordsgames.com, con la possibilità di allegare le informazioni tecniche), Chi ha creato KILLA NEWS, i collegamenti al sito, a YouTube, al gruppo Facebook e al canale WhatsApp, la donazione PayPal, le Impostazioni e la Guida.

Nel menu delle sezioni:
- le **frecce su e giù** scelgono una sezione;
- la **freccia destra** apre le sottosezioni (per esempio Sport > Serie A);
- in **Giornali locali** si sceglie prima cosa leggere: «Tutti gli articoli locali», «Scegli per città», «Scegli per regione e provincia» oppure «Scegli per testata». Ogni città, regione e provincia offre a sua volta «Tutti gli articoli» di quel luogo oppure le singole testate. Le scelte compaiono anche nell'elenco a destra e si aprono con Invio;
- in **Giornali internazionali** si sceglie allo stesso modo: «Tutti gli articoli internazionali», «Scegli per continente», «Scegli per nazione» oppure «Scegli per testata». Scelto un continente compaiono le sue nazioni; scelta una nazione compaiono prima le sue testate e poi «Tutti gli articoli» di quella nazione, con le testate mescolate. Anche ogni continente ha i suoi «Tutti gli articoli». La voce «Notizie dal mondo per area» raccoglie le notizie estere di tutti i giornali, anche italiani, divise per Europa, Africa, America, Asia e Medio Oriente;
- la **freccia sinistra** le richiude;
- **Invio** porta all'elenco delle notizie.

Nell'elenco delle notizie:
- **Invio** apre l'articolo nel lettore;
- il **tasto Applicazioni** (o Maiusc+F10) apre il menu contestuale;
- **Canc** rimuove l'articolo dalla sezione Articoli salvati, Cronologia o Disponibili offline in cui ci si trova.

Nel **lettore**, il testo si legge con le frecce come un documento. Si può usare anche la lettura continua di NVDA (NVDA+Freccia giù). La lettura vocale di KILLA NEWS:
- parte dal paragrafo in cui si trova il cursore e legge un paragrafo alla volta;
- si mette in pausa e riprende;
- **si interrompe subito con Ctrl+K o con Esc**, anche negli articoli molto lunghi.

Se il feed fornisce solo un estratto, il lettore lo scrive chiaramente e offre il pulsante **Apri articolo originale**.

**Voce di NVDA.** In Impostazioni > Voce, oltre alle voci di Windows, c'è «Voce di NVDA»: la lettura vocale usa la sintesi, la voce e la velocità scelte in NVDA. Con NVDA 2024.1 o successivo il programma sa quando NVDA ha finito un paragrafo e passa subito al successivo; con versioni più vecchie stima la durata. La pausa ferma la voce e la ripresa rilegge il paragrafo dall'inizio. Se NVDA è spento si usa la voce di Windows.

**Traduzione.** Gli articoli scritti in altre lingue si traducono in italiano con il pulsante **Traduci in italiano** o con **Ctrl+T**; premendo di nuovo Ctrl+T si torna alla lingua originale. Sotto il titolo il lettore dice da quale lingua è stato tradotto. Nelle Impostazioni si può scegliere di tradurre tutto da solo. La traduzione usa il servizio gratuito di Google Traduttore (se non risponde, MyMemory): serve Internet, è automatica e può contenere errori. Ogni articolo viene tradotto una sola volta e poi resta salvato.

**Ricerca per nazione e continente.** Nel pannello Cerca si può filtrare per continente o per nazione, oltre che per testo, categoria, testata e periodo.

### Scorciatoie predefinite (modificabili in Impostazioni > Scorciatoie)

| Tasti | Azione |
|---|---|
| Ctrl+1 | Prima pagina |
| Ctrl+2 | Tutti i giornali |
| Ctrl+F | Ricerca |
| Ctrl+S | Salva o rimuovi dai preferiti |
| Ctrl+P | Avvia la lettura vocale |
| Ctrl+Maiusc+P | Pausa / riprendi (nel lettore) |
| Ctrl+K | Interrompi la lettura vocale |
| Ctrl+H | Cronologia |
| Ctrl+D | Preferiti (articoli salvati) |
| Ctrl+R | Aggiorna le notizie da Internet |
| F5 | Aggiorna l'elenco visualizzato |
| F6 / Maiusc+F6 | Riquadro successivo / precedente |
| Ctrl+Maiusc+S | Scarica per la lettura offline |
| Ctrl+O | Apri l'articolo originale nel browser |
| Ctrl+Maiusc+T | Stampa l'articolo (finestra di stampa di Windows) |
| Ctrl+T | Traduci in italiano / torna alla lingua originale (nel lettore) |
| Alt+Freccia giù / su | Paragrafo successivo / precedente (lettore) |
| Alt+Inizio | Leggi dall'inizio (lettore) |
| Ctrl+Pagina giù / su | Articolo successivo / precedente (lettore) |
| Ctrl+E | Esporta l'articolo in un file di testo (lettore) |
| Ctrl+Maiusc+F | Gestione delle fonti |
| Ctrl+Maiusc+I | Impostazioni |
| F1 | Guida |
| Esc | Indietro, interrompe la voce o chiude la finestra secondaria |

**Conflitti evitati.** Nessuna scorciatoia usa i tasti Insert, Bloc Maiusc o Windows, che sono riservati a NVDA e a Windows. Non sono assegnabili nemmeno Ctrl+Alt+N (avvio di NVDA), Alt+F4, Alt+Tab, Ctrl+Esc e F10. La finestra delle scorciatoie rifiuta queste combinazioni e quelle già in uso, e ne spiega il motivo.

### Aggiornamento delle notizie

- Le fonti si aggiornano **in background ogni 15 minuti**. La frequenza si regola nelle impostazioni.
- L'elenco che si sta leggendo **non viene mai ricaricato da solo**, perché il focus non deve saltare. Quando arrivano nuove notizie compare un annuncio, e l'elenco si aggiorna con **F5**.
- Ctrl+R avvia un aggiornamento manuale.
- In fondo alla finestra, la barra di stato mostra l'ora dell'ultimo aggiornamento.
- Le fonti non raggiungibili sono elencate in **Fonti > Fonti non raggiungibili**.
- Se manca Internet, il programma lo segnala e continua a mostrare gli articoli già scaricati.

---

## 3. Creare l'eseguibile e l'installatore

PyInstaller non può creare eseguibili Windows partendo da un altro sistema operativo, quindi questi passaggi vanno fatti **su Windows**.

### Sul proprio PC Windows
1. Installare Python (vedi il paragrafo 1).
2. **Versione portatile**: doppio clic su `CREA_PORTATILE.bat`. Il risultato è `dist\KillaNews_1.0.0_Portatile.zip`.
3. **Installatore**: installare gratuitamente Inno Setup 6 da <https://jrsoftware.org/isdl.php>, poi fare doppio clic su `CREA_INSTALLER.bat`. Il risultato è `dist\KillaNews_1.0.0_Installazione.exe`.

Entrambi gli script eseguono prima i test automatici.

### Con GitHub, senza installare nulla
Il file `.github/workflows/build.yml` compila tutto su un computer Windows di GitHub.
1. Caricare il progetto in un repository GitHub.
2. Aprire la scheda **Actions**, scegliere «Compila KILLA NEWS per Windows», poi **Run workflow**.
3. Al termine, scaricare l'artefatto `KillaNews-1.0.0-Windows`. Contiene lo zip portatile e l'installatore.

### Messaggi di NVDA (facoltativo)
Copiando `nvdaControllerClient.dll` (64 bit) nella cartella `lib`, NVDA pronuncia i messaggi di stato senza spostare il focus, per esempio «Aggiornamento completato: 12 nuove notizie». Le istruzioni sono in `lib/LEGGIMI.txt`. Senza la libreria, i messaggi compaiono nella barra di stato, che NVDA legge con NVDA+Fine.

---

## 4. Scelte tecniche

- **wxPython invece di Tkinter.** Su Windows, wxPython usa i controlli nativi del sistema: albero SysTreeView32, elenchi SysListView32, campi di testo RichEdit, menu, pulsanti e finestre di dialogo standard. NVDA li riconosce e li legge in modo completo. I widget di Tkinter (in particolare Treeview e Text) sono disegnati da Tk e NVDA li espone solo in parte: il nome dei controlli, gli elementi degli elenchi e la posizione del cursore spesso non vengono letti. Per un programma il cui requisito obbligatorio è l'accessibilità, Tkinter non era adatto.
- **SAPI5 diretto via COM invece di pyttsx3.** pyttsx3 ha un ciclo di eventi bloccante e un comando di arresto poco affidabile durante i testi lunghi. KILLA NEWS invece:
  - usa l'oggetto `SAPI.SpVoice` in modalità asincrona;
  - legge un paragrafo alla volta;
  - si ferma con `SVSFPurgeBeforeSpeak`, che svuota subito la coda;
  - usa le voci SAPI5 installate e, se il sistema lo consente, anche le voci italiane «OneCore» di Windows 10/11.

  All'avvio sceglie automaticamente una voce italiana.
- **SQLite in modalità WAL.** L'aggiornamento in background scrive con una propria connessione mentre l'interfaccia legge, quindi nulla si blocca. La ricerca usa FTS5, indipendente da maiuscole e accenti; se FTS5 non è disponibile ripiega su LIKE.
- **Feed RSS/Atom con feedparser.** Il programma usa ETag e Last-Modified per non riscaricare i feed che non sono cambiati. I duplicati vengono controllati per testata in tre modi: GUID, collegamento normalizzato (senza parametri di tracciamento) e titolo.
- **Testo integrale.** Viene recuperato solo dalle pagine pubbliche delle testate segnate come prive di abbonamento (`testo_completo: true`), senza credenziali né cookie. Se la pagina dichiara `isAccessibleForFree: false`, il programma non estrae il testo. **Nessun paywall viene aggirato.**

### Struttura del progetto

```
KILLA_NEWS/
  main.py                  avvio, istanza unica, gestione degli errori
  killanews/
    config.py              identità, percorsi (AppData), impostazioni predefinite
    database.py            schema SQLite, migrazioni, backup e ripristino
    models.py              modello Articolo, date in italiano
    catalog.py             categorie, fonti, giornali locali, classificazione per parole chiave
    feed_manager.py        download dei feed, analisi, duplicati, ricerca del feed sul sito
    article_reader.py      testo integrale autorizzato, controllo paywall, paragrafi per la voce
    news_manager.py        sezioni, prima pagina, ricerca universale con filtri
    speech_manager.py      sintesi vocale SAPI5 (pausa, ripresa, arresto immediato)
    favorites_manager.py   preferiti, cartelle, "da leggere"
    history_manager.py     cronologia
    download_manager.py    archivio offline, spazio occupato, esportazione in .txt
    updater.py             aggiornamento automatico in background
    keyboard_manager.py    scorciatoie personalizzabili e controllo dei conflitti
    settings_manager.py    impostazioni persistenti
    accessibility.py       annunci a NVDA (nvdaControllerClient) o barra di stato
    core.py                collega tutti i moduli
    ui/                    main_window, sidebar, article_list, article_view,
                           search_view, settings_view, dialogs, common
  data/sources.json        catalogo delle testate (modificabile)
  data/categories.json     categorie, sottocategorie, parole chiave
  tests/test_core.py       test automatici (server di prova locale, senza Internet)
  installer/               specifica PyInstaller, script Inno Setup, dati di versione
  assets/                  icona Killa Records
```

---

## 5. Catalogo delle fonti

Il catalogo iniziale comprende 57 testate e 72 feed (25 testate con feed verificati, 32 consultabili tramite il sito finché non viene trovato il loro feed):
- quotidiani nazionali;
- agenzie (ANSA, AGI, Adnkronos);
- Rai News;
- sport (Corriere dello Sport, Tuttosport, Sky Sport, Eurosport);
- internazionali (BBC, The Guardian, Le Monde, El País, New York Times, Al Jazeera, Reuters, Associated Press);
- tecnologia;
- testate locali del Veneto (L'Arena, VeronaSera, Il Giornale di Vicenza, Il Mattino di Padova, Corriere del Veneto, Il Gazzettino) e le edizioni regionali di ANSA;
- le 11 edizioni locali de La Stampa: Torino, Alessandria, Asti, Biella, Cuneo, Novara, Vercelli, Verbano Cusio Ossola (Piemonte), Aosta (Valle d'Aosta), Savona, Imperia e Sanremo (Liguria).

**Verifica dei feed.** Nessun indirizzo è stato inventato. Ogni feed del catalogo è stato controllato il 20/11/2026 su directory pubbliche che verificano i feed: Feeder.co, che li riportava come attivi, ed elenchi Feedspot. Il campo `verifica` di ogni feed indica quale directory è stata usata.

**Testate senza feed confermato.** Per queste testate il campo `feed` è vuoto e il programma apre il sito originale: Corriere della Sera, la Repubblica, Il Messaggero, Avvenire, Il Fatto Quotidiano, il manifesto, Il Tempo, Il Post, La Gazzetta dello Sport, Sky Sport, Eurosport, HDblog, Wired Italia e gran parte dei giornali locali. Reuters e Associated Press non pubblicano feed RSS pubblici. Con **Fonti > Gestione delle fonti > Cerca feed sul sito**, il programma legge la pagina della testata, trova i feed che il sito stesso dichiara, li verifica scaricandoli e propone di aggiungerli. **Lo fa anche da solo** durante l'aggiornamento: per ogni testata senza feed riprova al massimo una volta alla settimana e aggiunge solo i feed che il sito dichiara e che funzionano davvero.

### Aggiungere testate, regioni, province e città senza toccare il codice
- dal programma: **Fonti > Gestione delle fonti > Aggiungi testata**;
- oppure aggiungendo voci a `data/sources.json`, nel formato qui sotto:

```json
{"id": "mia_testata", "nome": "La mia testata", "paese": "Italia", "regione": "Lombardia",
 "provincia": "Brescia", "citta": "Brescia", "gruppo": "Locali", "sito": "https://...",
 "testo_completo": false,
 "feed": [{"url": "https://.../rss.xml", "categoria": "italia/cronaca_locale", "principale": true}]}
```

Aumentando `versione_catalogo`, al prossimo avvio le novità vengono caricate. Le modifiche fatte dall'utente vengono mantenute. In alternativa si può usare **Importa catalogo**. L'albero dei giornali locali (regione > provincia > città) si crea da solo a partire dai campi della testata.

---

## 6. Dati personali e backup

Preferiti, cartelle, cronologia, archivio offline e impostazioni si trovano in `%APPDATA%\KillaNews\killanews.db`. La versione portatile li salva invece nella sottocartella `dati`, perché accanto all'eseguibile c'è il file `portable.flag`.

- Ogni giorno, all'avvio, il programma crea un backup automatico in `backup\` e conserva gli ultimi 5.
- Da **Impostazioni > Dati personali** si può creare un backup, ripristinarne uno (il ripristino avviene al riavvio) e gestire lo spazio dell'archivio offline.
- La disinstallazione non cancella i dati personali.
- Il file di registro `killanews.log`, nella stessa cartella, aiuta a diagnosticare i problemi.

Il programma non contiene chiavi, password o credenziali.

## 7. Test

```
py -m unittest discover -s tests -v
```

Sono 12 test e non richiedono Internet. Coprono:
- database, catalogo, aggiunta e rimozione di fonti, backup;
- download dei feed RSS e Atom, ETag, duplicati;
- errori HTTP e di rete, situazione di Internet assente;
- ricerca con filtri e ricerca di ripiego senza FTS5;
- preferiti, cartelle, cronologia;
- archivio offline e persistenza dopo la riapertura;
- paywall;
- aggiornamento in background;
- sintesi vocale (pausa, ripresa, arresto immediato, navigazione) con una voce simulata;
- scorciatoie e conflitti.

Una prova automatica dell'interfaccia apre tutte le finestre e simula l'uso (sezioni, ricerca, lettore, voce, finestre di dialogo, temi): `py tests\smoke_ui.py`.

Per le prove con NVDA si usa `CHECKLIST_NVDA.md`. Le funzionalità completate e le limitazioni sono elencate in `FUNZIONALITA_E_LIMITI.md`.

## 8. Diritto d'autore

Gli articoli appartengono alle rispettive testate. KILLA NEWS mostra soltanto ciò che i feed pubblicano o che è liberamente accessibile sulle pagine pubbliche, e rimanda sempre alla fonte originale. Gli articoli salvati e scaricati restano nel computer dell'utente per uso personale.

---
© Killa Records – KILLA NEWS 1.0.0 – *L'informazione, senza barriere.*
