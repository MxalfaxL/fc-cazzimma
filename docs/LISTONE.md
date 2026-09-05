# Il listone: come nascono i prezzi

Un prezzo consigliato non è "quanto è forte", è **quanto vale rispetto a chi
lo sostituirebbe**. Le tabelle con i numeri veri, prezzi di mercato e tetti
per ogni piano, le produce `motore/listone.py` in `report/LISTONE.md` e
`report/listone.json`: stanno sul Mac e non vengono pubblicate, perché sono
le carte da giocare all'asta.

## Tre passaggi, tutti verificabili nel codice

**Valore sul sostituto.** In una lega da 10 squadre si comprano 30 portieri,
80 difensori, 80 centrocampisti e 60 attaccanti. Un giocatore vale quanto
rende in più del primo che resterebbe libero. È il motivo per cui un
attaccante da 25 costa molto più del doppio di uno da 12: sotto una certa
soglia gli attaccanti si equivalgono, sopra no.

**Premio del modificatore.** Una quota del monte crediti della lega viene
girata su portieri e difensori, pesata sulla solidità difensiva della loro
squadra. È il pezzo che i listoni in circolazione non hanno, perché il
modificatore è una regola vostra.

**Il tuo tetto.** I prezzi di mercato dicono quanto si spenderà in media per
reparto. Il tuo piano dice quanto vuoi spenderci tu. Il rapporto fra i due è
il fattore che alza o abbassa i tetti in quel reparto. I piani stanno in
`dati/piani.json`, fuori dal repository.

## I due numeri del listone ufficiale

Il file ufficiale dà **Qt.A**, la quotazione, e **FVM**, la stima di mercato.
Fanno lavori diversi: l'FVM sommato per ruolo dice come il mercato divide il
budget fra i reparti, la quotazione decide i prezzi dentro il reparto. L'FVM
dentro il reparto non va usato: è troppo ripido in cima e darebbe prezzi
fuori scala ai primi tre di ogni ruolo.

## Un'approssimazione dichiarata

La solidità difensiva di una squadra è oggi stimata dalla quotazione del suo
portiere più caro, perché il portiere non fa bonus e la sua quotazione è quasi
tutta aspettativa di porta inviolata. Va sostituita con le medie voto vere
appena arrivano le statistiche della scorsa stagione.

## Come si usa

```bash
python3 motore/listone.py dati/Quotazioni_Fantacalcio_Stagione_2026_27.xlsx --tutti
```

Ne escono il riepilogo a schermo, `report/listone.json` da incollare nell'app
e `report/LISTONE.md` con le tabelle. Con un listone incompleto lo script si
rifiuta di scrivere: i prezzi sarebbero sbagliati.
