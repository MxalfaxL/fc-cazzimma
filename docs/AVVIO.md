# FC Cazzimma — impianto e avvio

Niente server, niente abbonamenti, niente account nuovi. Due pezzi che si
parlano: un'app che apri dal telefono, dall'iPad e dal Mac, e questa cartella
sul Mac dove stanno i dati e si fanno i conti lunghi.

## Chi fa cosa

**L'app fa tutto quello che serve al volo.** Asta, rosa, formazione
consigliata, stagione. Salva sul tuo repository privato: quello che tocchi dal
Mac lo ritrovi sull'iPhone e viceversa. La formazione la calcola l'app, non il
Mac, quindi puoi ricalcolarla il sabato alle 14:50 quando escono le probabili
definitive e scopri che il tuo centrale è in panchina. Incolli le probabili,
lei rifà undici e modulo e ti dice quanto costa ogni dubbio, tu copi e incolli
sulla piattaforma. Il Mac può essere spento.

**Il Mac fa i conti lunghi.** Il listone per l'asta, le statistiche storiche,
i valori attesi della settimana. Ne escono pochi numeri per giocatore, che
passi all'app con un incolla.

**Il repository privato è l'archivio.** Ogni salvataggio dell'app è una
versione: se combini un guaio torni indietro di un giorno o di una settimana.

**L'app è chiusa a chiave.** Chi apre il link vede una schermata di accesso e
basta. Su ogni dispositivo si entra una volta con il token e una password a
scelta; il token resta lì cifrato con la password. Il codice dell'app è
pubblico, i dati no.

## La cartella

Tutto vive qui, in `~/Documents/Fantacalcio Marco`:

```
index.html · sw.js · manifest · icone     l'app, pubblicata su GitHub Pages
motore/                                    il codice Python
dati/                                      input grezzi: listone ufficiale, rosa
report/                                    quello che il motore produce
docs/                                      questi documenti
```

## Provalo subito

Basta il Python che il Mac ha già, più `pandas` e `openpyxl` per il listone.

```bash
cd ~/Documents/"Fantacalcio Marco"
python3 motore/ottimizzatore.py
```

Gira su una rosa finta e stampa formazione, panchina, il costo di ogni
ballottaggio e il confronto fra i sette moduli. È lo stesso ragionamento che
c'è dentro l'app, e questo lo controlla:

```bash
python3 motore/verifica_parita.py
```

Se dice OK, il Python e il JavaScript dell'app danno gli stessi numeri.

## Il listone

Prima dell'asta, una volta sola:

1. Scarica il listone ufficiale di Fantacalcio.it, modalità **Classic**, e
   mettilo in `dati/`.
2. Genera i prezzi:

   ```bash
   python3 motore/listone.py dati/Quotazioni_Fantacalcio_Stagione_2026_27.xlsx --tutti
   ```

   Ne escono il riepilogo a schermo, **un solo file** per l'app,
   `report/listone.json`, con dentro i prezzi di mercato e il tuo tetto per
   ogni piano, e `report/LISTONE.md` con le tabelle. I piani li scrivi in
   `dati/piani.json`: niente di tutto questo finisce su GitHub.

3. Mandalo all'app:

   ```bash
   python3 motore/invia_listone.py
   ```

   Lo scrive nel repository dei dati e l'app lo prende alla prossima
   apertura, su tutti i dispositivi. Incollarlo a mano in **Asta → Listone**
   resta possibile, ma non serve più.

Se hai anche la pagina del listone della Gazzetta, fra il passo 2 e il 3
lancia `python3 motore/confronta_gazzetta.py dati/gazzetta-DATA-grezzo.csv`:
accanto ai nomi compare ▲ *sale* o ▼ *cala*, con la spiegazione quando li
tocchi. È un secondo parere sulle gerarchie, non un prezzo.

In asta: cerchi il nome, vedi il tuo tetto, tocchi il nome se vuoi sapere da
dove viene, premi **preso** e il modulo è compilato. Chi va a un avversario lo
segni con **via**; se vuoi tenere il conto anche degli altri, nella tendina
**Comprato da** scegli l'avversario e scrivi il prezzo: crediti e rose degli
altri si aggiornano da soli. Se hai sbagliato, **annulla** sull'ultimo
movimento.

Il **piano di spesa** si cambia con un tocco fra equilibrio, difesa,
centrocampo e attacco. Stessi prezzi di mercato, tetti diversi. Se all'asta
qualcuno impazzisce sui difensori e il piano A salta, il piano B è lì.

Il tetto non è fisso: si adatta mentre compri. Se prendi un difensore a 5
quando ne avevi previsti 12, quei crediti risparmiati alzano il tetto sugli
altri difensori. Se ne paghi uno 60, il tetto sugli altri crolla da solo.
Come nascono i prezzi è spiegato in `LISTONE.md`; le tabelle con i tuoi tetti
le trovi in `report/LISTONE.md`, che resta sul Mac.

## La routine della settimana

Il sabato, dal telefono, quando escono le probabili definitive:

1. **Formazione → Leggi le probabili formazioni.** Copi il testo della pagina
   delle probabili e lo incolli. L'app riconosce i tuoi giocatori fra
   titolari, ballottaggi con la percentuale, indisponibili e squalificati, e
   ti dice chi ha cambiato stato e chi non ha trovato. Quello che non trova
   lo lascia com'era: correggi con i tre bottoni **T B F**.
2. **Formazioni ufficiali già uscite.** Alla deadline, 15 minuti dopo il primo
   fischio, sono certe solo le squadre che hanno già dato la formazione.
   Tocchi quelle squadre e sui loro giocatori compare la spunta verde: su
   quelli non puoi più essere tradito, sugli altri sì.
3. **I dubbi di questa giornata.** Per ogni titolare in ballottaggio l'app
   dice quanto ti costa se non gioca e chi entrerebbe. Verde sotto 0,6, oro
   fino a 1,5, rosso sopra: il rosso è la scelta della giornata. Il metodo è
   in `BALLOTTAGGI.md`.
4. **Copia la formazione** e incollala sulla piattaforma, a mano. Entro 15
   minuti dalla prima partita.

Il giovedì o il venerdì, se vuoi, cinque minuti al Mac per aggiornare i
valori attesi: aggiorni `dati/rosa.json`, lanci
`python3 motore/esporta_app.py 7 | pbcopy` e incolli in **Dati della
settimana dal Mac**. Se salti questo passaggio non succede niente di grave:
l'app usa gli ultimi valori che ha.

A giornata finita, in **Stagione**, registri i tuoi punti e quelli
dell'avversario.

## Perché l'app sceglie moduli strani

Il modificatore difesa cambia la convenienza dei moduli, e quasi nessun
consigliere ne tiene conto. Con 4 o più difensori entrano fino a 5 punti
extra, che sulle vostre fasce valgono più di un gol. Per questo i difensori
non vengono scelti per fantavoto: l'app prova tutte le combinazioni di
portiere e difensori e tiene quella che massimizza il totale, modificatore
compreso. Un centrale da voto 6,5 costante può valere più di un terzino che
ogni tanto segna, e in quel caso il 4-4-2 batte il 3-4-3 anche se sulla carta
hai l'attacco migliore.

Nel riquadro nero in alto c'è il misuratore del modificatore: sei tacche, una
per fascia, e il cursore sulla media della tua difesa. Ti dice quanto manca
alla fascia sopra e quanto margine hai su quella sotto. Sotto c'è il campetto
con l'undici: il cerchietto oro con la percentuale segna un ballottaggio, la
spunta verde un giocatore confermato dalle formazioni ufficiali.

Chi è in ballottaggio non pesa metà a caso: pesa la sua parte più la parte
del vero primo di panchina del suo ruolo, e lo stesso vale per il voto che
entra nel modificatore. È il motivo per cui la panchina è ordinata per
fantavoto e non per certezza: entra il primo che ha giocato, quindi il più
forte va davanti anche se è in dubbio.

## Cosa manca ancora

Il pezzo grosso che manca è quello che **calcola** i fantavoto attesi
partendo dai dati veri invece che a mano, e il lavoro programmato in cloud che
li aggiorna da solo. Prima di quello vengono le statistiche della stagione
scorsa e la lista dei rigoristi, che sono roba tua da procurare.
