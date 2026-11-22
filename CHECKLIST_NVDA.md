# KILLA NEWS 1.0.0 – Checklist per le prove reali con NVDA

Da eseguire su Windows 10 e su Windows 11, con l'ultima versione di NVDA e con la sintesi vocale predefinita. Per ogni punto annotare: **OK**, **NON OK** (con cosa è stato letto o cosa è successo) oppure **NON PROVATO**.

> Queste prove **non sono state ancora eseguite**: il programma è stato sviluppato e collaudato in un ambiente Linux senza Windows né NVDA. Questa checklist serve proprio a fare la verifica reale.

Prima di iniziare:
- NVDA attivo, modalità di navigazione (browse mode) automatica.
- Per provare gli annunci di NVDA, copiare `nvdaControllerClient.dll` in `lib` (vedi `lib/LEGGIMI.txt`). Ripetere le prove anche senza la libreria.
- Ripetere le prove anche con il contrasto elevato di Windows attivo e con il tema scuro del programma.

## 1. Avvio
- [ ] All'avvio NVDA legge il titolo della finestra «KILLA NEWS - L'informazione, senza barriere.»
- [ ] Il focus è sul menu delle sezioni, su «Prima pagina», e NVDA lo annuncia come albero/elemento dell'albero.
- [ ] Al primo avvio viene annunciato (o compare nella barra di stato) il messaggio di benvenuto e di scaricamento.
- [ ] Un secondo avvio del programma mostra il messaggio «KILLA NEWS è già aperto», leggibile.
- [ ] NVDA+Fine legge la barra di stato (messaggio e ultimo aggiornamento).

## 2. Menu laterale (albero)
- [ ] Le frecce su e giù leggono il nome di ogni sezione e il suo livello.
- [ ] La freccia destra apre le sottosezioni e NVDA dice «espanso»; la freccia sinistra le chiude e NVDA dice «compresso».
- [ ] Giornali locali > Veneto > Provincia di Verona > Verona > L'Arena: tutti i livelli sono raggiungibili.
- [ ] Le testate senza feed sono lette con «(solo sito, nessun feed)».
- [ ] Scorrendo velocemente con le frecce l'elenco a destra non ruba il focus.
- [ ] Invio su una sezione porta il focus all'elenco delle notizie.
- [ ] Invio su «Cerca» porta al campo di ricerca; Invio su «Impostazioni» apre le impostazioni.

## 3. Elenco delle notizie
- [ ] NVDA annuncia il nome dell'elenco (per esempio «Prima pagina - Notizie principali: 120 articoli»).
- [ ] Ogni riga viene letta con titolo, testata, data, categoria, stato e descrizione.
- [ ] Le colonne si leggono anche con i comandi tabella di NVDA (Ctrl+Alt+frecce).
- [ ] Lo stato «salvato», «da leggere» e «disponibile offline» viene letto come testo.
- [ ] Invio apre il lettore; il tasto Applicazioni e Maiusc+F10 aprono il menu contestuale, leggibile.
- [ ] Canc in Articoli salvati chiede conferma, rimuove l'articolo e il focus resta sulla riga successiva.
- [ ] Una sezione vuota mostra un messaggio leggibile (Tab o NVDA+Tab).
- [ ] Testata «solo sito»: la riga spiega che manca il feed; Invio apre il sito nel browser.

## 4. Aggiornamenti senza salti del focus
- [ ] Durante un aggiornamento automatico, mentre si scorre l'elenco, il focus **non** si sposta e l'elenco **non** si ricarica.
- [ ] Al termine viene annunciato «Aggiornamento completato: N nuove notizie... Premi F5».
- [ ] F5 ricarica l'elenco mantenendo selezionato lo stesso articolo.
- [ ] Ctrl+R annuncia «Aggiornamento delle notizie in corso...» e poi il risultato.
- [ ] Con la rete scollegata viene annunciata l'assenza di connessione e gli articoli già scaricati restano leggibili.
- [ ] Durante la lettura vocale di un articolo, l'aggiornamento in background non la interrompe.

## 5. Lettore degli articoli
- [ ] All'apertura NVDA legge il titolo della finestra (titolo dell'articolo) e il focus è sul testo.
- [ ] Con le frecce si leggono titolo, testata, data, autore, categoria, stato del testo e paragrafi.
- [ ] La lettura continua di NVDA (NVDA+Freccia giù) funziona sul testo.
- [ ] Con un articolo parziale il testo dice chiaramente che è un estratto e indica il collegamento all'originale.
- [ ] Tab raggiunge il campo «Stato della lettura vocale» e tutti i pulsanti, ognuno con un nome.
- [ ] Esc chiude il lettore e il focus torna sulla stessa riga dell'elenco.

## 6. Lettura vocale (punto critico)
- [ ] Ctrl+P avvia la lettura dal paragrafo in cui si trova il cursore.
- [ ] Ctrl+Maiusc+P mette in pausa; premuto di nuovo riprende dallo stesso punto.
- [ ] **Ctrl+K interrompe immediatamente la voce**, anche a metà di un paragrafo lungo.
- [ ] **Esc interrompe immediatamente la voce**; un secondo Esc chiude il lettore.
- [ ] L'interruzione funziona anche durante la pausa.
- [ ] Con un articolo lunghissimo (più di 10 paragrafi) l'interruzione è sempre immediata.
- [ ] Alt+Freccia giù/su passa al paragrafo successivo/precedente; Alt+Inizio ricomincia dall'inizio.
- [ ] Ctrl+Pagina giù/su passano all'articolo successivo/precedente e fermano la voce del precedente.
- [ ] Chiudendo il lettore la voce si ferma.
- [ ] La voce predefinita è italiana (per esempio Microsoft Elsa).
- [ ] In Impostazioni > Voce: voce, velocità e volume si cambiano e «Prova la voce» li applica.
- [ ] Le voci «(voce di sistema)» (OneCore) funzionano oppure, se non funzionano, non bloccano il programma.
- [ ] La voce di KILLA NEWS e quella di NVDA non si bloccano a vicenda: premendo Ctrl, NVDA tace mentre la voce del programma continua.

## 7. Ricerca
- [ ] Ctrl+F porta al campo «Testo da cercare» e NVDA ne legge l'etichetta.
- [ ] Tutti i filtri (Categoria, Testata, Paese, Periodo, Dal, Al) vengono letti con la loro etichetta.
- [ ] «Dal» e «Al» sono attivi solo scegliendo «Intervallo di date» (NVDA dice «non disponibile» altrimenti).
- [ ] Invio esegue la ricerca, annuncia il numero di risultati e porta il focus ai risultati.
- [ ] Senza risultati viene annunciato un messaggio e il focus resta nel campo.
- [ ] Una data sbagliata (per esempio 31/02/2026) mostra un errore leggibile.
- [ ] Esc dal pannello di ricerca riporta al menu delle sezioni.

## 8. Preferiti, cartelle, cronologia, offline
- [ ] Ctrl+S salva l'articolo e annuncia «Articolo salvato nei preferiti»; premuto di nuovo lo rimuove.
- [ ] «Sposta in cartella» e «Nuova cartella...» sono leggibili; la cartella compare nel menu laterale.
- [ ] Ctrl+D apre Articoli salvati; Ctrl+H apre la Cronologia, che indica gli articoli letti.
- [ ] Ctrl+Maiusc+S scarica l'articolo; la finestra di attesa viene letta e il pulsante Annulla funziona.
- [ ] Gli articoli scaricati si aprono anche con Internet scollegato.
- [ ] Chiudendo e riaprendo il programma, preferiti, cartelle e cronologia ci sono ancora.

## 9. Fonti
- [ ] Gestione delle fonti (Ctrl+Maiusc+F): la tabella è leggibile, con lo stato di ogni testata scritto come testo.
- [ ] Aggiungi testata: tutti i campi hanno un'etichetta; il controllo dei feed viene letto.
- [ ] «Verifica il feed», «Cerca feed sul sito» e «Dettagli degli errori» mostrano risultati leggibili.
- [ ] Una nuova regione o città aggiunta compare nell'albero dei giornali locali.

## 10. Impostazioni
- [ ] Ctrl+Tab cambia scheda (Generale, Aspetto, Voce, Scorciatoie, Dati personali) e NVDA legge il nome.
- [ ] Tutte le caselle, i campi numerici e le scelte hanno un'etichetta.
- [ ] Scorciatoie: Invio su una riga apre la modifica; una combinazione riservata (per esempio Ctrl+Alt+N) o già usata viene rifiutata con un messaggio leggibile.
- [ ] La nuova scorciatoia funziona subito, senza riavviare.
- [ ] Dimensione e tipo di carattere, tema scuro e contrasto elevato vengono applicati.
- [ ] Backup e ripristino funzionano e i messaggi sono leggibili.

## 11. Conflitti con NVDA e Windows
- [ ] Nessuna scorciatoia del programma interferisce con i comandi NVDA+... (Insert o Bloc Maiusc).
- [ ] In modalità di navigazione NVDA non intercetta le lettere: KILLA NEWS usa solo controlli nativi, quindi NVDA deve restare in modalità focus.
- [ ] Alt apre la barra dei menu; tutti i menu e le voci sono leggibili e raggiungibili con le lettere sottolineate.
- [ ] Alt+F4 chiude il programma.

## 12. Installatore e versione portatile
- [ ] L'installatore è leggibile in ogni pagina: scelta della cartella, collegamento sul desktop facoltativo, menu Start.
- [ ] La disinstallazione da Impostazioni > App funziona.
- [ ] La versione portatile si avvia da una chiavetta USB e salva i dati nella sottocartella «dati».

Data della prova: ________  Versione di Windows: ________  Versione di NVDA: ________  Sintesi di NVDA: ________
