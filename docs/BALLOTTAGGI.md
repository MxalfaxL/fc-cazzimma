# I ballottaggi: quanto costa sbagliare

Il consigliere di formazione non dice solo chi schierare. Per ogni titolare
in dubbio dice **di quanto scende il punteggio se il ballottaggio va male**.
È il numero che decide la giornata: "se perde ti costa 0,3" si schiera
tranquillo, "ti costa 1,8" merita di aspettare le formazioni ufficiali.

Questo documento spiega come si arriva a quel numero. Lo stesso calcolo vive
in due posti, `motore/ottimizzatore.py` e la testa dello `<script>` in
`index.html`, e `motore/verifica_parita.py` controlla che coincidano.

## 1. La probabilità di giocare

Ogni giocatore ha uno stato, e lo stato dà la probabilità di scendere in
campo:

| stato | probabilità |
|---|---|
| **T** titolare | 1 |
| **B** ballottaggio | la percentuale delle probabili, se la conosciamo; altrimenti 0,5 |
| **F** fuori | 0 |

La percentuale arriva dal lettore delle probabili ("Kean 70% - Piccoli 30%")
oppure la scrivi a mano toccando una seconda volta il bottone **B**.

## 2. Chi entra se non gioca

Nella vostra lega le sostituzioni sono ruolo per ruolo e la panchina è
libera nell'ordine. Se un difensore non gioca entra il primo difensore in
panchina **che ha giocato**; se nemmeno lui ha giocato, il secondo; e così
via. Se nessuno del ruolo ha giocato la casella resta vuota e vale zero.

**L'ordine di panchina dentro un ruolo è per fantavoto**, non per
certezza. Sembra strano mettere davanti un giocatore in dubbio, ma se non
gioca viene semplicemente saltato: entra il successivo, senza costo. Quindi
il primo della panchina deve essere il più forte, punto.

## 3. Tutti gli esiti, uno per uno

Un reparto schierato ha dei dubbi, in campo e in panchina. Il motore
**enumera tutte le combinazioni** di dubbi che giocano o non giocano (con
quattro dubbi sono sedici esiti, con otto 256: nulla, anche sul telefono) e
per ciascuna:

1. calcola la probabilità, prodotto delle `p` di chi gioca e delle `1 − p` di
   chi non gioca;
2. fa le sostituzioni **come le fa la lega**: per ogni titolare che non gioca
   entra il primo panchinaro di quel ruolo che ha giocato, e viene consumato;
   se la panchina è finita la casella resta vuota e vale zero;
3. somma i fantavoti di chi è davvero in campo e tiene da parte i voti puri
   dei difensori e del portiere per il modificatore.

Il valore del reparto è la **media pesata** di quelle somme. Il
modificatore è la media pesata, su tutti gli esiti di portiere e difesa
insieme, del modificatore calcolato su chi è in campo in quell'esito: con i
dubbi non è un intero ma, per esempio, +1,32.

Perché non basta il conto più semplice (`p·fv + (1 − p)·ricambio` per ogni
dubbio, con lo stesso ricambio per tutti)? Perché con due o tre dubbi nello
stesso reparto il primo della panchina viene contato due o tre volte. Il 10
ottobre 2026 il motore metteva Thuram in panchina dietro a tre attaccanti in
ballottaggio: sulla carta 21,4 punti d'attacco, in realtà 19,7, meno dei
19,9 di Thuram titolare. Con l'enumerazione il trucco sparisce da solo.

Per ogni titolare l'app mostra l'**atteso**: la media di quello che renderà
la sua casella, lui o chi entra al suo posto.

## 4. La scelta dell'undici

Per ogni modulo:

- **centrocampo e attacco** non toccano il modificatore, quindi si prova
  ogni combinazione di titolari del reparto e si tiene quella col valore più
  alto. Con 8 centrocampisti e 5 slot sono 56 combinazioni, niente.
- **portiere e difesa** interagiscono col modificatore: si prova ogni
  portiere con ogni combinazione di difensori e si tiene il totale migliore,
  modificatore atteso compreso.

Il modulo migliore è quello col totale più alto. Gli altri sei vengono
mostrati con la distanza, perché quando il margine è mezzo punto decidi tu.
Sul misuratore l'app disegna il modificatore **se giocano tutti** (la media
dei voti attesi di portiere e titolari) e accanto scrive quello atteso
contando i dubbi.

## 5. Il costo dell'errore

Per ogni titolare in dubbio si confrontano due scenari, tenendo tutto il
resto com'è (gli altri dubbi restano dubbi, le sostituzioni si fanno da
sole):

- **gioca di sicuro**: la sua probabilità diventa 1;
- **non gioca di sicuro**: la sua probabilità diventa 0, e nella sua casella
  entra chi tocca.

Il costo è la differenza fra i due totali attesi, **modificatore
ricalcolato in entrambi**. Per un attaccante è circa `fv − primo della
panchina`. Per un difensore può essere molto di più: se il suo voto tiene la
media sopra una soglia e il ricambio la fa scendere, il costo include la
fascia di modificatore persa, cioè un punto intero.

Esempio dalla rosa di prova (`dati/rosa-prova.json`):

| dubbio | probabilità | se perde costa | entra |
|---|---:|---:|---|
| Kean | 70% | 0,80 | Dovbyk |
| Orsolini | 55% | 0,30 | Barella |
| Bremer | 60% | 0,20 | Gila |

Kean è il più caro perché il primo attaccante in panchina rende meno di
quanto rendono i primi centrocampisti in panchina. Bremer costa poco perché
Gila ha un voto vicino al suo e la media del modificatore non scende di
fascia.

Nell'app i costi hanno tre colori: verde sotto 0,6, oro fino a 1,5, rosso
sopra. Il rosso è la scelta della giornata.

## 6. Approssimazioni dichiarate

- Le **5 sostituzioni** massime non sono modellate: servirebbe che sei
  titolari saltassero nella stessa giornata.
- Il **cambio modulo** quando un ruolo è scoperto non è modellato: la
  casella vuota vale zero, che è la cosa più prudente.
- I ballottaggi sono trattati come **indipendenti** fra loro. Se due tuoi
  giocatori sono in ballottaggio l'uno con l'altro (i due portieri del
  Napoli), il modello non lo sa: pensa che possano saltare entrambi.
- Il modificatore è calcolato sui **voti attesi**, come se ogni voto fosse
  certo. In realtà i voti ballano, e con 5 difensori contano i 3 migliori:
  il "meglio di 5" vale un po' più del "meglio di 4" di quanto dica il
  motore. Fra un modulo a 5 e uno a 4 appaiati, il 5 è leggermente
  sottostimato.
- La **percentuale delle probabili** è presa come probabilità vera. È la
  migliore informazione che abbiamo, ma la misurazione delle fonti (punto 5
  della lista) dirà quanto ci prendono davvero.

## 7. Come si verifica

```bash
python3 motore/ottimizzatore.py                 # rosa di esempio, a schermo
python3 motore/ottimizzatore.py dati/rosa-prova.json
python3 motore/verifica_parita.py               # Python contro JavaScript
```

Se `verifica_parita.py` dice OK, i due motori danno gli stessi numeri fino
alla nona cifra decimale. Se dice DIFFERENZE, qualcuno ha cambiato una regola
in un posto solo.
