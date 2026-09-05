# FC Cazzimma — progetto

Documento di impianto. Cosa costruiamo, perché così e in che ordine.
Da leggere una volta prima di iniziare a sviluppare, e poi da rileggere
quando qualcosa non torna.

---

## 1. Cosa deve fare

Tre momenti, tre bisogni diversi.

**All'asta**, una sera sola, ad alta pressione: sapere quanto puoi offrire
senza sforare, quanto vale davvero il giocatore che stanno chiamando, e
cosa resta per i reparti ancora da comprare. Deve funzionare in un
locale con la rete che va e viene.

**Ogni settimana**, in cinque minuti: sapere quale formazione schierare
fra i sette moduli, tenendo conto del modificatore difesa. Il momento
della verità non è giovedì al Mac, è sabato pomeriggio col telefono in
mano quando escono le probabili definitive.

**Durante la stagione**, quando serve: capire come stai andando, cosa
hanno gli altri, se conviene uno scambio, come arrivare al mercato di
riparazione con le idee chiare.

### Vincoli

- Accesso completo da iPhone, senza dipendere dal Mac acceso.
- Un solo utente, i dati non escono dai tuoi dispositivi.
- Zero costi ricorrenti, zero server da mantenere.
- Le formazioni si inseriscono a mano su Fantagazzetta: il sistema
  consiglia e prepara il testo da copiare, non automatizza l'inserimento.

---

## 2. Le decisioni, e le alternative scartate

**Il motore di calcolo sta sul telefono, non sul server.**
La scelta della formazione è un problema piccolo: 3 portieri per un
massimo di 56 combinazioni di difensori, poche centinaia di casi. Gira
in un millisecondo in JavaScript. Metterlo sul telefono significa poter
ricalcolare quando serve davvero, cioè all'ultimo minuto. Scartato: un
motore centrale che produce un report, perché un report invecchia e le
probabili formazioni cambiano fino a un'ora dal fischio d'inizio.

**Il Mac serve per i conti lunghi, non per le decisioni.**
Statistiche di più stagioni, quotazioni, calendario, calcolo del listone:
roba che richiede pandas e qualche secondo. Il risultato è compatto —
due numeri per giocatore — e viaggia bene. Il Mac è un laboratorio, non
un pezzo della catena operativa.

**L'app diventa una PWA installata sulla schermata Home.**
Icona vera, apertura in un secondo, funziona offline. Scartate: una app
nativa, perché servirebbe un account sviluppatore a pagamento e non
aggiungerebbe niente; e restare per sempre dentro un artifact, che va
benissimo per costruire ma dipende dall'aprire un'altra app e non si
installa.

**I dati stanno in un repository GitHub privato.**
È gratis, è privato, tiene la cronologia di ogni modifica, e si legge e
scrive da qualsiasi dispositivo con una chiamata HTTP. Il codice della
PWA sta in un repository pubblico separato — non contiene nulla di tuo.
Il token di accesso ai dati lo inserisci una volta per dispositivo e
resta lì. Scartate: iCloud Drive come database vero, perché una pagina
web su iPhone non può leggere file da iCloud; un database in cloud, che
vuol dire account e costi; CloudKit, che richiede l'abbonamento
sviluppatore Apple.

**Il telefono tiene sempre una copia locale.**
Tutto scrive prima in locale, poi prova a sincronizzare. Se la rete non
c'è, l'app funziona lo stesso e allinea dopo. All'asta questo non è un
dettaglio: è la differenza fra avere lo strumento e non averlo.

**Un solo scrittore, nessun conflitto vero.**
Sei solo tu su due dispositivi. Contatore di versione, l'ultimo che
scrive vince, e se il telefono trova una versione più recente ti avvisa
invece di sovrascrivere.

---

## 3. Architettura

```
   iPhone (PWA, schermata Home)          Mac (Claude Code)
   ┌──────────────────────────┐      ┌────────────────────────┐
   │ asta · rosa · formazione │      │ scarico dati grezzi    │
   │ stagione · avversari     │      │ modello previsionale   │
   │ motore di scelta         │      │ listone d'asta         │
   │ copia locale (storage)   │      │ cartella sul Mac       │
   └───────────┬──────────────┘      └───────────┬────────────┘
               │                                 │
               └────────► repo GitHub privato ◄──┘
                          stato.json, versionato
```

Il repository privato contiene pochi file di testo: la rosa, i valori
attesi della settimana, lo storico delle giornate, le rose degli
avversari. Ogni salvataggio è un commit, quindi hai il backup e la
cronologia senza fare niente.

---

## 4. I moduli

### M1 — Plancia d'asta
Fatta. Budget, offerta massima, tacche di fase, listone con ricerca e
tetto accanto a ogni giocatore, ricalcolo del tetto mentre l'asta va
avanti, cambio di piano con un tocco, annulla dell'ultimo movimento. Chi
va a un avversario si segna con il prezzo, e crediti e rose degli altri
si costruiscono da soli.

### M2 — Listone
Prezzi consigliati per ogni giocatore di Serie A, tarati su 500 crediti,
25 slot, 10 squadre e sul modificatore difesa. Dettagli in §6.

### M3 — Consigliere di formazione
Sceglie modulo, undici e ordine della panchina, e per ogni dubbio
schierato dice quanto costa se il ballottaggio va male, modificatore
compreso (`BALLOTTAGGI.md`). Legge le probabili incollate e segna chi è
confermato dalle formazioni ufficiali. Da aggiungere: il confronto col
punteggio atteso dell'avversario di giornata.

### M4 — Motore previsionale
Calcola i valori attesi che alimentano M2 e M3. Dettagli in §5.

### M5 — Stagione e avversari
Storico giornate, classifica, andamento. Le rose dei nove avversari,
per sapere chi ha cosa, chi è coperto male in un ruolo, e su chi ha
senso proporre uno scambio prima del mercato di riparazione.

---

## 5. Il motore previsionale

L'obiettivo sono due numeri per giocatore e giornata:
il **fantavoto atteso** e il **voto puro atteso**. Il secondo esiste
perché il modificatore difesa lavora sui voti senza bonus, e nella
vostra lega vale fino a 5 punti, più di un gol intero sulle fasce.

```
fantavoto_atteso = p_gioca × (voto_atteso + bonus_attesi − malus_attesi)
                 + (1 − p_gioca) × resa_del_ricambio
```

**voto_atteso** parte dalla media voto storica, pesata fra stagione in
corso e precedente, e — questo è importante — tirata verso il 6 quando
le presenze sono poche. Chi ha giocato due partite a 7,5 non è un
giocatore da 7,5: è un giocatore su cui non sappiamo ancora niente.
Sopra ci va la forma recente, smorzata, e la difficoltà dell'avversario.

**bonus_attesi** sono gol e assist attesi sui minuti attesi, ricavati
dalla frequenza storica per novanta minuti. Chi tira i rigori vale
molto di più, e va marcato a mano perché è un'informazione che cambia
in corsa.

**malus_attesi** sono cartellini attesi, e per il portiere i gol
subiti attesi in base alla forza dell'attacco avversario.

**Per portiere e difensori** il voto atteso ha un pezzo in più: la
probabilità di porta inviolata. È lì che si vince il modificatore. Una
difesa che non prende gol porta voti alti a tutto il reparto, e nella
vostra lega quel valore va comprato all'asta, non sperato la domenica.

**p_gioca** viene dalle probabili formazioni. Sul telefono lo semplifichi
in tre stati — titolare, ballottaggio, fuori — perché con un dito la
sera prima devi poter correggere in due secondi.

Nessuna magia: ogni numero deve essere spiegabile. Se l'app dice di
schierare il 4-4-2 devi poter vedere perché, altrimenti non ti fidi e
fai di testa tua, e allora tanto valeva non costruirla.

---

## 6. Il listone d'asta

Un prezzo consigliato non è "quanto è forte", è **quanto vale rispetto
a chi lo sostituirebbe**. In una lega da 10 squadre vengono comprati 30
portieri, 80 difensori, 80 centrocampisti e 60 attaccanti: il valore di
un giocatore è quanto rende in più rispetto all'ultimo del suo ruolo che
verrà comprato. Un attaccante da 6,5 è prezioso perché il sessantesimo
attaccante fa 5,9. Un portiere da 6,3 lo è molto meno, perché il
trentesimo portiere non è lontano.

Il totale dei crediti in gioco è 5000, cioè 500 per dieci squadre. Si
distribuiscono in proporzione al valore così calcolato, e il risultato è
un prezzo di mercato realistico invece di una classifica di bravura.

Sopra questo va la correzione del modificatore: per portiere e difensori
si stima quanti punti di modificatore portano in una stagione e li si
converte in crediti con lo stesso cambio. È la ragione per cui il tuo
listone sarà diverso da quelli che girano in chat, ed è il tuo vantaggio
nella lega.

Infine, siccome l'asta procede a ruoli chiusi e non si torna indietro,
il listone non dà solo prezzi: dà un piano di spesa per fase, con quanto
devi arrivare ad avere in tasca alla fine di ogni reparto, e tre varianti
— difesa forte, centrocampo forte, attacco forte — così se all'asta salta
il piano A ne hai già due pronti in tasca.

---

## 7. Come ci arriviamo

**Fase 0 — fatta.** L'app funziona già: asta, rosa, formazione,
stagione. Se da qui in poi non facessimo più niente, all'asta ci
arriveresti comunque attrezzato. Tutto quello che viene dopo è
miglioramento, non fondamenta.

**Fase 1 — prima dell'asta.** Dati e listone. Scarichiamo quotazioni e
statistiche, costruiamo il motore previsionale nella versione stagionale
e generiamo il listone con i piani di spesa. È la fase che ti fa
guadagnare più punti in assoluto, perché una rosa storta non la
raddrizzi con la formazione della domenica.

**Fase 2 — settimana dell'asta.** Il listone entra nella plancia:
ricerca per nome, prezzo massimo accanto a ogni chiamata, ricalcolo del
tetto mentre l'asta avanza. Prova a secco con un'asta finta, per non
scoprire un difetto la sera vera.

**Fase 3 — subito dopo l'asta.** La PWA vera con l'icona sulla home e la
sincronizzazione. Le rose dei nove avversari, che a quel punto sono
pubbliche. Il motore previsionale passa alla versione settimanale.

**Fase 4 — durante la stagione.** Rifinitura: confronto col punteggio
atteso dell'avversario, simulazione dei ballottaggi, preparazione del
mercato di riparazione con i valori di svincolo già calcolati. E il
promemoria della deadline formazioni sul calendario, che è la cosa più
banale e quella che fa perdere più punti a tutti.

---

## 8. Cosa può andare storto

**Le fonti dati cambiano forma.** Succederà. Per questo l'importatore
riconosce le colonne invece di dare per scontate le posizioni, e ogni
scarico viene salvato grezzo: se il formato cambia si riparte da lì
senza aver perso niente.

**Il modello sbaglia.** Sicuramente, ogni tanto. Per questo ogni
consiglio mostra i numeri che lo hanno prodotto e la distanza dal
secondo modulo: quando il margine è mezzo punto, decidi tu.

**L'asta va storta.** Piano B e piano C sono nel listone dalla partenza.

**Il telefono resta senza rete la sera dell'asta.** L'app funziona
offline per intero e allinea dopo.

**Perdi i dati.** Ogni salvataggio è un commit: si torna indietro di un
giorno, di una settimana, di quello che serve.

---

## 9. Cosa non facciamo

Niente inserimento automatico delle formazioni su Fantagazzetta: è
contro le regole del sito ed è il tipo di automazione che si rompe da
sola. Niente multiutente. Niente server. Niente modello che non sappiamo
spiegare a parole.
