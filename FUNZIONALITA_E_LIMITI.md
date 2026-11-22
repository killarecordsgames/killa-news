# KILLA NEWS 1.0.0 – Funzionalità completate e limitazioni

## Cosa è stato verificato davvero (e cosa no)

| Verifica | Esito | Come |
|---|---|---|
| Sintassi di tutti i file Python | ✅ superata | `py_compile` e analisi statica `pyflakes` senza errori |
| Nucleo: database, fonti, feed, duplicati, ricerca, preferiti, cronologia, offline, errori di rete, paywall, aggiornamento in background, voce (simulata), scorciatoie | ✅ 12 test automatici superati | `tests/test_core.py` con un server di prova locale (Linux, Python 3.13) |
| Interfaccia grafica: creazione delle finestre, sezioni, ricerca, lettore, finestre di dialogo, temi | ✅ 6 scenari superati | `tests/smoke_ui.py` su Linux con wxPython 4.2.3 (GTK) e schermo virtuale: su Windows i controlli sono quelli nativi e vanno riprovati |
| Avvio reale con il catalogo completo, senza Internet | ✅ superato | Il programma si apre, crea il database e il backup, prova ad aggiornare e annuncia correttamente l'assenza di connessione |
| Funzionamento su **Windows 10/11** | ❌ **non verificato** | L'ambiente di sviluppo era Linux, senza Windows |
| Compatibilità con **NVDA** | ❌ **non verificata** | NVDA non era disponibile: usare `CHECKLIST_NVDA.md` |
| Voce **SAPI5** reale (pausa, ripresa, arresto) | ❌ **non verificata su Windows** | La logica è collaudata con una voce simulata; le chiamate SAPI sono quelle documentate da Microsoft |
| Eseguibile portatile e installatore | ❌ **non compilati qui** | PyInstaller non crea .exe da Linux: usare `CREA_PORTATILE.bat`, `CREA_INSTALLER.bat` oppure la compilazione automatica su GitHub (`.github/workflows/build.yml`) |
| Indirizzi dei feed | ⚠️ verificati indirettamente | Il computer di sviluppo non poteva collegarsi ai siti dei giornali: ogni feed è stato confermato il 20/11/2026 su directory pubbliche che ne controllano il funzionamento (Feeder.co, Feedspot). Il primo avvio su Windows farà la verifica diretta e il menu Fonti segnala quelli non funzionanti |

## Funzionalità completate

**Interfaccia e accessibilità**
- Finestra classica di Windows con controlli nativi: barra dei menu, albero, elenco a colonne, campi di testo, schede e finestre standard.
- Menu laterale con le 15 sezioni richieste e le sottosezioni (Italia 7, Notizie dal mondo 8, Economia 8, Sport 15, Tecnologia 6, Cultura 7, Salute 5). I giornali locali sono organizzati per regione, provincia e città; la prima pagina ha 5 viste.
- Navigazione completa da tastiera: frecce, Tab, Invio, F6, Esc, menu contestuale da tastiera, Canc.
- Ogni controllo è preceduto da un'etichetta e nessun pulsante è senza nome. Lo stato degli articoli è scritto come testo, non affidato a colori o icone.
- Il focus non salta durante gli aggiornamenti: l'elenco si ricarica solo con F5 o su richiesta. Questo comportamento si può cambiare nelle impostazioni.
- Messaggi di stato pronunciati da NVDA tramite `nvdaControllerClient.dll`, se presente, e sempre mostrati nella barra di stato.
- Finestre di attesa annullabili per tutte le operazioni lente: download, verifica e ricerca dei feed.
- Temi: colori di sistema (rispetta il contrasto elevato di Windows), chiaro, scuro, contrasto elevato giallo su nero. Dimensione e tipo di carattere regolabili.
- Guida (F1) generata con le scorciatoie attuali.

**Notizie**
- Catalogo di 57 testate (incluse le 11 edizioni locali de La Stampa) e 72 feed verificati. Le testate senza feed restano consultabili sul sito originale finché il programma non trova da solo il loro feed ufficiale.
- Funzione «Cerca feed sul sito»: trova i feed che il sito stesso dichiara e li verifica prima di aggiungerli.
- Aggiornamento automatico in background (15 minuti, regolabile) e manuale (Ctrl+R), con download parallelo dei feed, ETag/Last-Modified e controllo dei duplicati.
- Ora dell'ultimo aggiornamento, segnalazione delle fonti non raggiungibili, rilevamento dell'assenza di Internet.
- Classificazione automatica nelle sottocategorie tramite parole chiave modificabili in `categories.json`.
- Pulizia automatica degli articoli vecchi; quelli salvati e scaricati non vengono mai cancellati.
- Gestione completa delle fonti: aggiungere, modificare, eliminare, attivare e disattivare; verificare i feed; importare ed esportare il catalogo; ripristinare l'originale. Nuove regioni, province e città si aggiungono senza toccare il codice.

**Lettore e voce**
- Il lettore mostra titolo, sottotitolo, testata, data e ora, autore, categoria, stato del testo, testo e collegamento alla fonte.
- Il testo integrale viene recuperato solo dalle pagine pubbliche autorizzate; i paywall non vengono aggirati. Quando il testo è parziale, il lettore lo dichiara.
- La lettura vocale SAPI5 va un paragrafo alla volta e parte dal punto in cui si trova il cursore. Comandi disponibili: avvio, pausa, ripresa, **arresto immediato** (Ctrl+K o Esc), dall'inizio, paragrafo precedente e successivo, articolo precedente e successivo.
- Scelta della voce, con preferenza automatica per l'italiano; regolazione di velocità e volume; pulsante di prova.

**Dati personali**
- Preferiti con cartelle personalizzate, articoli «da leggere», cronologia con data dell'ultima consultazione e numero di letture.
- Archivio offline con indicazione dello spazio occupato, eliminazione degli articoli e indicazione «disponibile offline» nell'elenco.
- Esportazione degli articoli in file di testo nella cartella dei download.
- Stampa degli articoli (Ctrl+Maiusc+T) tramite la finestra di stampa standard di Windows, con caratteri della dimensione scelta nelle impostazioni e numeri di pagina.
- Database SQLite in AppData (oppure nella cartella «dati» per la versione portatile), backup automatico giornaliero, backup e ripristino manuali, migrazioni pronte per le versioni future.
- Ricerca universale in titoli, testi, autori e testate, con filtri per categoria, testata, paese, periodo e intervallo di date. Non distingue maiuscole e accenti.
- Scorciatoie personalizzabili, con blocco delle combinazioni riservate a NVDA e a Windows e controllo dei conflitti.

## Limitazioni ancora presenti

1. **Nessuna prova reale su Windows e con NVDA.** I controlli scelti sono quelli meglio supportati da NVDA, ma il comportamento effettivo va confermato con `CHECKLIST_NVDA.md` prima della distribuzione.
2. **Eseguibile e installatore da compilare su Windows** con gli script forniti o con GitHub Actions.
3. **32 testate senza feed confermato**, comprese le 11 edizioni locali de La Stampa (l'indirizzo delle pagine locali è ricavato dalla struttura del sito e va confermato al primo uso),: tra queste Corriere della Sera, la Repubblica, La Gazzetta dello Sport, Il Messaggero, Il Fatto Quotidiano, Sky Sport e la maggior parte dei giornali locali del Veneto. Si aprono sul sito originale. «Cerca feed sul sito» può aggiungere i loro feed se il sito li dichiara. Reuters e Associated Press non offrono feed pubblici.
4. **Sottocategorie basate su parole chiave.** Le sottocategorie senza un feed dedicato, per esempio Serie C, Pallavolo e Oceania, si riempiono solo se le parole chiave compaiono nel titolo o nel sommario. Possono restare vuote o contenere qualche articolo fuori tema.
5. **«In evidenza» e «Approfondimenti» sono definite da regole.** «In evidenza» raccoglie l'ultima ora delle agenzie; «Approfondimenti» raccoglie gli articoli con testo lungo. I feed RSS non indicano cosa la redazione mette in evidenza.
6. **Testo integrale non sempre disponibile.** Dipende dalla struttura della pagina. Per le testate con abbonamento è disattivato e viene mostrata solo l'anteprima del feed.
7. **Voci «OneCore»** di Windows 10/11: sono elencate quando SAPI5 le espone. Su alcuni sistemi potrebbero non funzionare; in quel caso vanno usate le voci SAPI5, come Microsoft Elsa Desktop.
8. **Annunci di NVDA senza spostare il focus**: richiedono di aggiungere `nvdaControllerClient.dll` nella cartella `lib`, perché la libreria non è inclusa nel pacchetto. Senza la libreria i messaggi vanno solo nella barra di stato.
9. **Tema scuro parziale**: barra dei menu, pulsanti e schede seguono i colori di Windows. Per il massimo contrasto è consigliato il contrasto elevato di Windows con il tema «Colori di sistema».
10. **Le scorciatoie nei menu** sono scritte tra parentesi nel nome della voce, quindi NVDA le legge come parte del nome e non come «tasto di scelta rapida».
11. **Esc** e **Invio** hanno funzioni fisse e non sono personalizzabili.
