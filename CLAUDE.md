# FC Cazzimma

Progetto personale di Marco per il Fantacalcio Venezia, seconda edizione,
stagione 2026/27.

**Questo non è lavoro.** Marco fa il consulente CRM e Salesforce in RMT, e su
quel fronte lavora con una metodologia strutturata, skill aziendali, documenti
brandizzati per i clienti e task su ClickUp. Qui niente di tutto quello serve, e
tirarlo dentro fa solo danno:

- Non usare le skill RMT — discovery, quote, kickoff, SAL, change request,
  documenti brandizzati, persona dei clienti. Non c'entrano niente e non vanno
  attivate, nemmeno se un termine sembra assomigliare a qualcosa di lavorativo
  ("asta", "listone", "piano", "stima" qui vogliono dire altro).
- Nessun deliverable formale, nessuna copertina, nessun logo cliente, nessuna
  specifica funzionale. La documentazione è quella in `docs/` e basta.
- Niente task su ClickUp, niente riferimenti a progetti o clienti RMT, niente
  account o repository aziendali.
- Il tono è quello di due amici che costruiscono una cosa per divertimento.
  Diretto, senza cerimonie.

**Data dell'asta: 6 ottobre 2026.** Tutto quello che serve per l'asta ha
priorità su tutto il resto.

## La cartella di lavoro

Tutto il progetto vive in una cartella sul Mac di Marco, quella in cui stai
girando adesso. È la tua area di lavoro: leggi e scrivi lì dentro liberamente,
crea sottocartelle se servono, e tieni tutto in quel perimetro. Non ti serve
uscire da qui: gli input grezzi vanno in `dati/`, quello che produci in
`report/`, la documentazione in `docs/`.

Le uniche due cose fuori da questa cartella sono i due repository su GitHub,
e le regole su quelli stanno più sotto.

Se Marco ti chiede una cosa che richiederebbe di toccare file altrove sul Mac,
chiedi conferma prima.

---

Rispondi sempre in italiano. Anche i nomi di funzioni, variabili e file sono in
italiano: è una scelta voluta, mantienila.

---

## Cos'è

Un sistema che fa tre cose, in ordine di valore:

1. **Prepara e assiste l'asta.** È la sera che decide la stagione: una buona
   asta vale una quarantina di punti, la formazione ottimale ne vale qualcuno a
   settimana.
2. **Consiglia la formazione ogni giornata**, tenendo conto del modificatore
   difesa che nella lega di Marco cambia la convenienza dei moduli.
3. **Tiene la stagione**: storico, classifica, rose degli avversari.

---

## Le regole della lega che contano

Stanno tutte in `motore/regole.py`, e il codice deve leggerle da lì. Non
duplicarle altrove.

- Budget 500 crediti, rosa di 25: **3 portieri, 8 difensori, 8 centrocampisti,
  6 attaccanti**. 10 squadre per divisione.
- **L'asta procede a ruoli chiusi**, nell'ordine P → D → C → A, a chiamata e a
  rotazione. Chiuso un reparto non si torna indietro: è per questo che il budget
  va pianificato per fase e non globalmente.
- Se sfori il budget sull'ultimo attaccante **perdi il diritto d'asta** su quel
  giocatore. L'app deve rendere questo errore impossibile.
- Dopo la fase centrocampisti i crediti residui di tutti diventano pubblici.
- **Modificatore difesa**: con 4 o più difensori schierati si fa la media fra il
  voto puro del portiere e quelli dei 3 migliori difensori. Fasce: ≤6 → 0,
  ≤6.25 → 1, ≤6.50 → 2, ≤6.75 → 3, ≤7 → 4, >7 → 5. È la regola più importante
  di tutto il progetto: vale fino a 5 punti a giornata, più di un gol intero.
- **Fasce gol**: primo gol a 66 punti, poi uno ogni 4.
- Sette moduli: 3-4-3, 3-5-2, 4-3-3, 4-4-2, 4-5-1, 5-4-1, 5-3-2.
- Panchina libera nell'ordine, **5 sostituzioni** ruolo per ruolo.
- Formazione entro **15 minuti dalla prima partita** della giornata. Chi si
  dimentica si ritrova schierata quella della giornata precedente.
- Svincolo a metà prezzo per chi resta in Serie A, prezzo pieno per chi va
  all'estero o si ritira. L'arrotondamento va confermato con lo staff.

---

## Architettura, e perché è così

```
   iPhone / iPad (PWA su GitHub Pages)      Mac (questo progetto)
   ┌──────────────────────────────┐      ┌─────────────────────────┐
   │ asta · listone · formazione  │      │ listone.py: prezzi      │
   │ stagione · avversari         │      │ pipeline dati settimana │
   │ motore di scelta in JS       │      │ ottimizzatore in Python │
   │ copia locale (localStorage)  │      └───────────┬─────────────┘
   └──────────────┬───────────────┘                  │
                  └────► repo privato fc-cazzimma-dati ◄──┘
                         stato.json, versionato
```

**Il motore di scelta della formazione sta nel telefono, non sul Mac.** Le
probabili definitive escono un'ora prima delle partite e la deadline è 15 minuti
dopo il primo fischio: un report generato al Mac il giovedì è già vecchio. Il
problema è piccolo — 3 portieri per un massimo di 56 combinazioni di difensori —
e gira in un millisecondo in JavaScript.

**Il Mac fa solo i conti lunghi**: listone, statistiche storiche, pipeline
settimanale. Non deve mai essere un anello necessario per decidere.

**Conseguenza da non dimenticare**: la logica del modificatore, delle fasce gol
e dell'ottimizzatore esiste in due lingue, `motore/regole.py` e
`motore/ottimizzatore.py` da un lato, la testa dello `<script>` in `index.html`
dall'altro. **Se cambi una regola, cambiala in entrambi i posti** e verifica che
diano lo stesso risultato sugli stessi dati.

---

## Com'è fatto il repository

```
index.html                 la PWA, autoconsistente, tutto dentro
manifest.webmanifest       nome, icone, standalone
sw.js                      cache dell'app e dei font, funziona offline
icona-*.png                generate dallo stemma
motore/regole.py           le regole della lega, unica fonte
motore/ottimizzatore.py    modulo, undici, costo dei ballottaggi, versione Python
motore/verifica_parita.py  controlla che Python e JavaScript diano gli stessi numeri
motore/listone.py          prezzi d'asta e piani dal listone ufficiale
motore/esporta_app.py      blocco settimanale da incollare nell'app
motore/confronta_gazzetta.py  secondo parere: posizioni nel ruolo contro il listone della Gazzetta
motore/invia_listone.py    manda report/listone.json all'app, via repository dei dati
dati/                      input grezzi (gitignored tranne gli esempi e le prove)
dati/piani.json            i piani di spesa di Marco (gitignored)
dati/piani-esempio.json    ripartizione neutra del mercato, per far girare il codice
dati/NOTE-TARATURA.md      bande di prezzo di riferimento (gitignored)
dati/rosa-prova.json       rosa finta per la verifica di parità
dati/probabili-esempio.txt testo di probabili per provare il lettore
report/                    uscite del motore (gitignored)
docs/                      documentazione di progetto
docs/MANUALE.md            il manuale per Marco, schermata per schermata
```

Nello `<script>` di `index.html` il motore sta fra i segnaposto
`/* ==== motore: inizio ==== */` e `/* ==== motore: fine ==== */`: è codice
puro, senza DOM, ed è quello che `verifica_parita.py` estrae e fa girare in
node. Tutto ciò che tocca lo schermo sta dopo il secondo segnaposto.

`index.html` sta in radice perché GitHub Pages pubblica da lì. Il resto è
pubblico ma innocuo: non ci sono segreti nel codice.

---

## Cose da non fare

- **Non toccare mai `stato.json` nel repository `fc-cazzimma-dati`.** Ci
  scrive solo l'app attraverso l'API di GitHub: se ci mettessimo le mani da
  qui, le versioni si pesterebbero i piedi. L'unica eccezione, dal 12
  settembre 2026, è `listone.json`: lo scrive `motore/invia_listone.py` dal
  Mac e l'app lo prende se è più recente del suo. Niente altro.
- **Nessun token, nessuna credenziale in un file.** Il token dell'app vive solo
  sul dispositivo, cifrato con la password che Marco sceglie nella schermata
  di accesso (PBKDF2 + AES-GCM, tutto nel browser). Se ti serve autenticarti
  su GitHub, usa `gh auth login`. Se Marco incolla un token in chat, non
  usarlo e digli di rigenerarlo.
- **Niente scraping di Fantacalcio.it.** Il loro regolamento lo vieta, e uno
  scraper si accorge di essersi rotto sempre il sabato alle tre del pomeriggio.
  I voti e le probabili si importano da un incolla dell'utente.
- **Niente inserimento automatico delle formazioni.** Marco le scrive a mano
  sulla piattaforma. Il sistema consiglia e prepara il testo da copiare.
- **Niente `localStorage` rimosso o sostituito** senza pensarci: l'app deve
  funzionare offline durante l'asta, dove la rete balla.
- Non aggiungere dipendenze oltre `pandas` e `openpyxl`. L'app non ha
  dipendenze: nessun framework, nessun bundler, nessuna build.

---

## Come si scrive qui

- Codice leggibile prima che breve. I commenti spiegano **perché**, non cosa.
- Ogni modulo si può lanciare da solo e stampa qualcosa di sensato:
  `python3 motore/ottimizzatore.py` gira su una rosa finta.
- Quando cambi `index.html`, alza `VERSIONE` in `sw.js` e `VERSIONE_APP` in
  `index.html`: altrimenti i telefoni tengono la copia vecchia in cache.
- Se un dato manca o è incompleto, **dillo forte invece di restituire numeri
  belli e sbagliati**. Vedi `controlla()` in `listone.py`.
- Ogni scelta di modello deve essere spiegabile a parole. Se Marco non capisce
  perché l'app gli dice di schierare il 4-4-2, non si fida e fa di testa sua, e
  allora il progetto è inutile.
- Prima di dichiarare fatto qualcosa, provalo. Per l'app: `node --check` sullo
  script estratto, `python3 motore/verifica_parita.py` se hai toccato il
  motore, e un giro nel browser con `.claude/launch.json` (server statico
  in node sulla porta 8765) guardandola a larghezza iPhone.

---

## Note di taratura, da conoscere prima di toccare `listone.py`

Il listone ufficiale dà due numeri: **Qt.A**, la quotazione, e **FVM**, la stima
di mercato. Fanno lavori diversi.

- **L'FVM decide come si divide il budget fra reparti.** Sommato per ruolo sui
  250 giocatori che verranno comprati dice quanto il mercato spende su
  portieri, difensori, centrocampisti e attaccanti. Nessuna quotazione
  contiene questa informazione.
- **La quotazione decide i prezzi dentro il reparto**, corretta per il valore sul
  sostituto. L'FVM qui non va usato: è troppo ripido in cima. `MISCELA_FVM = 0.0`
  è il risultato di una taratura su cinque giocatori di riferimento,
  confrontata con i prezzi che fanno davvero all'asta. **Se cambi quel
  parametro, rifai il controllo sulle bande** prima di considerarlo un
  miglioramento.
- **Approssimazione dichiarata**: la solidità difensiva di una squadra è oggi
  stimata dalla quotazione del suo portiere più caro, perché il portiere non fa
  bonus e la sua quotazione è quasi tutta aspettativa di porta inviolata. Va
  sostituita con le medie voto vere appena arrivano le statistiche.
- **I piani di spesa sono di Marco e non stanno nel codice.** Vivono in
  `dati/piani.json`, che git ignora; in pubblico c'è solo
  `dati/piani-esempio.json` con la ripartizione neutra del mercato. Spostano
  crediti su portiere e difesa rispetto al mercato: non è un gusto, è il
  modificatore, che nessuno degli altri nove partecipanti sta prezzando.
- I numeri concreti (ripartizione del mercato, bande dei cinque giocatori di
  riferimento) stanno in `dati/NOTE-TARATURA.md`, privato. **Nel repository
  pubblico non vanno mai tetti, piani o prezzi stimati**: sono le carte da
  giocare all'asta.

## Dove siamo

Fatto e funzionante:

- PWA completa: asta con tetto dinamico, listone con ricerca e spiegazione
  del tetto, cambio piano con un tocco, annulla ultimo movimento, rose e
  crediti degli avversari che si costruiscono segnando i loro acquisti
  (tendina "Comprato da" nel modulo, di default su me),
  consigliere di formazione, stagione, sincronizzazione con il repository
  privato (stato e listone), tema chiaro e scuro, schermo acceso in asta.
- `listone.py` tarato sul file ufficiale del 12 settembre 2026, un solo
  `report/listone.json` con tutti i giocatori (chi è fuori dai 250 vale 1),
  i piani dentro e i segnali della Gazzetta (`gz`/`gzn`), più
  `report/LISTONE.md` con le tabelle. Entrambi privati. La sequenza è
  `listone.py` → `confronta_gazzetta.py` → `invia_listone.py`.
- **Costo dell'errore sui ballottaggi** (punto 1, fatto): il ricambio è il vero
  primo di panchina del ruolo, con la catena "se non gioca lui entra il
  successivo", e per ogni dubbio schierato l'app dice quanto costa se perde,
  modificatore compreso. Metodo in `docs/BALLOTTAGGI.md`; Python e JS
  verificati uguali con `verifica_parita.py`.
- **Marcatore formazioni ufficiali** (punto 2, fatto): si segnano le squadre
  che hanno già dato la formazione e i loro giocatori hanno la spunta verde
  in campetto, undici e panchina.
- **Lettore delle probabili** (punto 3, fatto): si incolla il testo della
  pagina delle probabili, riconosce i cognomi della rosa, assegna T/B/F con
  la percentuale del ballottaggio, e dice chi non ha trovato o su chi non è
  sicuro. Nessuno scraper.

- **Schermata di accesso** (5 settembre 2026): chi apre il link vede solo
  utente e password. Primo accesso per dispositivo con il token, verificato
  contro GitHub prima di accettarlo; poi il token sta in `localStorage`
  cifrato con la chiave derivata dalla password. "Resta collegato" salva la
  chiave sul dispositivo. Il codice è pubblico: è una porta chiusa, non una
  cassaforte, e i dati erano già protetti dal token.
- **Pubblicata** il 5 settembre 2026 su
  <https://mxalfaxl.github.io/fc-cazzimma/> da GitHub Pages, ramo `main`,
  cartella radice. `gh` è installato e autenticato come MxalfaxL; `git push`
  su `main` aggiorna l'app in meno di un minuto. Il repository privato
  `fc-cazzimma-dati` esiste, con il solo README: ci scrive l'app.

Da fare, in quest'ordine:

1. **Pipeline dati settimanale** che gira come lavoro programmato su GitHub
   Actions: scarica quello che è lecito scaricare, calcola i valori attesi,
   scrive nel repository dei dati. Costo zero, niente Mac acceso.
2. **Misurazione delle fonti.** Salvare ogni settimana cosa prevedevano le
   probabili e cosa è successo, per pesare le fonti su quanto ci prendono
   davvero invece che su quanto sono famose. L'app oggi salva le percentuali
   lette (`pb`): è il punto di partenza.
3. **Mercato di riparazione**: le rose degli avversari ci sono già; mancano
   i valori di svincolo aggiornati e il suggerimento degli scambi.

## Cosa serve ancora da Marco

- Le statistiche della stagione scorsa: media voto, fantamedia, presenze, gol,
  assist, ammonizioni. Sostituiscono l'approssimazione sulla solidità difensiva.
- La lista dei rigoristi delle venti squadre. È l'informazione che sposta più
  punti e non sta in nessun listone.
- La conferma dello staff su data dell'asta e arrotondamento dello svincolo.
- **Il file delle quotazioni va riscaricato da Fantacalcio.it la settimana
  dell'asta**: quello di agosto aveva 30 giocatori in meno e 6 squadre
  sbagliate. Ogni giovedì la Gazzetta pubblica il suo listone: la pagina
  del PDF, passata per `pdftotext -raw`, diventa il CSV per
  `confronta_gazzetta.py`.
