# FC Cazzimma — la tua lista

Solo le cose che devi fare tu. Il resto lo faccio io e te lo consegno pronto.
Le voci con ⛔ bloccano il lavoro successivo: sono quelle da fare per prime.

---

## 1. Al PC, una volta sola — circa 30 minuti

**Fatti il 5 settembre 2026**: 1.1, 1.2 e 1.3. L'app è su
<https://mxalfaxl.github.io/fc-cazzimma/>. Restano il token (1.4) e i
dispositivi (1.5).

⛔ **1.1 Account GitHub personale.**
Con una mail tua, non quella di lavoro. Se sei già loggato con l'account
aziendale, quando crei i repository controlla il menu **Owner** in alto a
sinistra: deve esserci il tuo nome, non RMT.

⛔ **1.2 Repository del codice.**
Nuovo repository `fc-cazzimma`, **pubblico**, vuoto. Il push lo facciamo
insieme da Claude Code con `gh` (vedi `PRIMO-PROMPT.md`), poi Settings →
Pages → branch `main`, cartella `/ (root)`.

⛔ **1.3 Repository dei dati.**
Nuovo repository `fc-cazzimma-dati`, **privato**, spuntando **Add a README
file**. Senza il README non c'è un ramo su cui scrivere e l'app non salva.

⛔ **1.4 Token.**
Profilo → Settings → Developer settings → Personal access tokens →
Fine-grained → Generate new token. Scadenza oltre fine stagione, accesso al
solo `fc-cazzimma-dati`, permesso **Contents: Read and write**. Copialo
subito, te lo mostra una volta sola.

**1.5 Collegare i dispositivi.**
Apri l'indirizzo su **Safari**, subito Condividi → Aggiungi alla schermata
Home, poi apri l'app **dall'icona**. Nella schermata di primo accesso metti
utente, token e una password a tua scelta. Da lì in poi serve solo la
password, o niente se lasci "resta collegato". Ripeti su iPad e Mac.

I passaggi dettagliati sono in GUIDA-GITHUB.md.

---

## 2. I file da passarmi — 10 minuti

⛔ **2.1 Il listone ufficiale.**
Fantacalcio.it, pagina delle quotazioni, download Excel della modalità
**Classic** (non Mantra). Senza questo non esistono i prezzi.

**2.2 Le statistiche della stagione scorsa.**
Media voto, fantamedia, presenze, gol, assist, ammonizioni per giocatore.
Non blocca niente, ma è la differenza fra un modificatore stimato e uno
calcolato. Vale parecchio.

**2.3 Le statistiche di squadra, se le trovi.**
Gol subiti e porte inviolate per squadra. È il cuore del modificatore.

---

## 3. Le domande allo staff — un messaggio in chat

**3.1 La data dell'asta**, e se sarà in presenza o da remoto. Cambia come ti
prepari, non cosa costruiamo.

**3.2 Quale listone usa la lega.** I listoni in giro sono tre e le quotazioni
non coincidono. Se la lega non usa quello di Fantacalcio.it, i prezzi vanno
ricalcolati sull'altro.

**3.3 Come si arrotonda lo svincolo a metà prezzo.** Un giocatore pagato 15
si svincola a 7 o a 8? Sembra un dettaglio, a gennaio non lo è.

---

## 4. Prima dell'asta — il lavoro che vale di più

**4.1 I rigoristi.**
Segnati chi tira i rigori nelle venti squadre. È l'informazione che sposta
più punti in assoluto e non sta in nessun listone: un rigorista fisso vale
diversi gol a stagione, e all'asta spesso costa uguale a chi non tira.
Passamela come lista e la porto dentro il modello.

**4.2 I titolari delle squadre piccole.**
Otto difensori e otto centrocampisti sono tanti, e la lega media li riempie
con gente da 1 credito che non gioca mai. Chi ci mette titolari veri di
squadre piccole trasforma ogni ballottaggio da rischio a non-problema. È qui
che si vince la stagione, non la domenica.

**4.3 Prova a secco.**
Mezz'ora con l'app e uno scenario d'asta finto che ti preparo io. Serve a
scoprire i difetti ora e non la sera vera.

---

## 5. La sera dell'asta

- Telefono carico, e portati il powerbank.
- App aperta e listone caricato **prima** che si inizi.
- Ogni tuo acquisto va inserito subito, e ogni giocatore che va a un
  avversario si segna con *via*. Trenta secondi in tutto, e in cambio sai
  sempre chi resta e quanto puoi spingere.
- Il tetto si adatta da solo mentre compri: fidati del numero, è tarato sul
  tuo piano.

---

## 6. Ogni settimana — cinque minuti

1. Copi il testo delle probabili formazioni e lo incolli in **Formazione →
   Leggi le probabili**. L'app assegna titolari, ballottaggi con percentuale
   e fuori, e ti dice chi non ha trovato.
2. Segni le squadre che hanno già dato la formazione ufficiale: sui loro
   giocatori compare la spunta verde.
3. Controlli **I dubbi di questa giornata**: per ognuno vedi quanto ti costa
   se non gioca. Il rosso è la scelta della giornata.
4. Copi la formazione e la schieri entro **15 minuti dalla prima partita**.
5. A giornata finita registri i tuoi punti e quelli dell'avversario.

---

## 7. A gennaio

Il mercato di riparazione. Ci arrivi con i valori di svincolo già calcolati
e con le rose dei nove avversari sotto gli occhi, per capire chi ha bisogno
di cosa prima di proporre uno scambio.

---

## Quello che faccio io

Fatto: il listone con i prezzi e i quattro piani di spesa, il costo
dell'errore su ogni ballottaggio, il marcatore delle formazioni ufficiali, il
lettore delle probabili, le rose e i crediti degli avversari che si
costruiscono in asta.

Da fare: il lavoro programmato che aggiorna i dati da solo in cloud, e la
misurazione delle fonti, per pesarle su quanto ci prendono davvero invece che
su quanto sono famose.

---

## L'ordine di importanza, se dovessi tagliare

**L'asta vale più di tutto il resto messo insieme.** Una buona asta ti dà
quaranta punti in una sera. La formazione ottimale te ne dà qualcuno a
settimana, e serve a non buttare quello che hai costruito.

Se avessi tempo per una cosa sola, sarebbe il punto 4.1: i rigoristi.
Se ne avessi per due, il 4.2: la panchina.
