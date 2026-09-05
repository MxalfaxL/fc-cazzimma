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

Da qui la **resa attesa della panchina** di un ruolo, che chiamiamo
*ricambio*:

```
ricambio = p1·fv1 + (1 − p1) · [ p2·fv2 + (1 − p2) · [ p3·fv3 + … ] ]
```

dove `p` e `fv` sono probabilità e fantavoto atteso dei panchinari di quel
ruolo, in ordine di panchina. Lo stesso conto si fa sul voto puro, perché
serve al modificatore.

**L'ordine di panchina dentro un ruolo è per fantavoto**, non per
certezza. Sembra strano mettere davanti un giocatore in dubbio, ma se non
gioca viene semplicemente saltato: entra il successivo, senza costo. Quindi
il primo della panchina deve essere il più forte, punto.

Prima di questa versione il ricambio era un numero fisso, 5,6 per tutti.
Ora è il vero primo di panchina di quel ruolo, e cambia da giornata a
giornata con gli stati che imposti.

## 3. Il valore atteso di un titolare

Un titolare in dubbio vale la sua parte più la parte del ricambio:

```
atteso      = p · fv   + (1 − p) · ricambio_fv
voto_atteso = p · voto + (1 − p) · ricambio_voto
```

Il modificatore difesa si calcola sui **voti attesi** di portiere e
difensori, non sui voti pieni. Nella versione precedente il modificatore era
leggermente ottimista quando schieravi un dubbio in difesa: ora no.

## 4. La scelta dell'undici

Per ogni modulo:

- **centrocampo e attacco** non toccano il modificatore, quindi si prova
  ogni combinazione di titolari del reparto e si tiene quella con la somma
  degli attesi più alta. Con 8 centrocampisti e 5 slot sono 56 combinazioni,
  niente.
- **portiere e difesa** interagiscono col modificatore: si prova ogni
  portiere con ogni combinazione di difensori e si tiene il totale migliore,
  modificatore compreso.

Il modulo migliore è quello col totale più alto. Gli altri sei vengono
mostrati con la distanza, perché quando il margine è mezzo punto decidi tu.

## 5. Il costo dell'errore

Per ogni titolare in dubbio si confrontano due scenari, tenendo tutto il
resto com'è:

- **gioca**: al suo posto contano il suo fantavoto e il suo voto pieni;
- **non gioca**: al suo posto contano il ricambio del suo ruolo, fantavoto e
  voto.

Il costo è la differenza fra i due totali, **modificatore ricalcolato in
entrambi**. Per un attaccante è semplicemente `fv − ricambio`. Per un
difensore può essere molto di più: se il suo voto tiene la media sopra una
soglia e il ricambio la fa scendere, il costo include la fascia di
modificatore persa, cioè un punto intero.

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
  difensori sono in ballottaggio l'uno con l'altro, il modello non lo sa.
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
