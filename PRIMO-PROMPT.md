# Il primo prompt

> Nota del 5 settembre 2026: i punti 1-4 sono stati fatti. L'app è online
> su <https://mxalfaxl.github.io/fc-cazzimma/>. Il blocco qui sotto resta
> come promemoria; il prossimo lavoro è il punto 5.

Apri il Terminale, entra nella cartella del progetto e lancia Claude Code:

```bash
cd ~/Documents/"Fantacalcio Marco"
claude
```

Poi incolla tutto il blocco qui sotto, dal primo `Leggi` all'ultima riga.

---

```
Leggi CLAUDE.md prima di fare qualsiasi cosa: contiene le regole della lega,
l'architettura e le cose che non vanno toccate.

Sono MxalfaxL su GitHub. Ho già creato a mano due repository:
- fc-cazzimma, pubblico, vuoto
- fc-cazzimma-dati, privato, con un README

Ho anche già generato il token fine-grained per il secondo. Non ti serve e non
devo dartelo: vive solo dentro l'app sul telefono.

Fai questo, in ordine, e fermati a dirmelo se qualcosa non torna.

1. Verifica che gh sia installato e che io sia autenticato. Se manca,
   installalo con brew e lancia gh auth login guidandomi.

2. Inizializza il repository git in questa cartella, collegalo a
   github.com/MxalfaxL/fc-cazzimma, e fai il primo push su main.
   Controlla prima che .gitignore stia escludendo davvero i file Excel, i
   PDF, dati/rosa.json e la cartella report: sono dati miei e il repository
   è pubblico. Se il push includesse uno di quei file, fermati e dimmelo.

3. Attiva GitHub Pages su branch main, cartella root. Aspetta che pubblichi e
   verifica con una richiesta HTTP che rispondano la pagina principale,
   sw.js, manifest.webmanifest e le tre icone. Dimmi l'indirizzo finale.

4. Controlla che il motore Python funzioni:
   - python3 motore/ottimizzatore.py deve girare sulla rosa di prova e
     stampare modulo, undici con il costo dei dubbi, panchina e confronto
     fra i sette moduli
   - python3 motore/verifica_parita.py deve dire OK
   - python3 motore/listone.py dati/quotazioni-esempio.csv deve avvisare che
     il listone è incompleto invece di sputare numeri sbagliati
   Se manca pandas o openpyxl, installali.

5. Poi passiamo al punto 4 della lista in CLAUDE.md, la pipeline dati
   settimanale su GitHub Actions. Prima di scrivere codice spiegami cosa
   scaricherebbe, da dove, e come lo scriverebbe nel repository dei dati
   senza pestare i piedi all'app. Aspetta il mio ok.
```

---

## Dopo, quando serve

Claude Code legge `CLAUDE.md` da solo a ogni sessione, quindi da qui in poi
bastano richieste brevi:

> Ho messo in dati/ le statistiche della stagione scorsa. Sostituisci
> l'approssimazione sulla solidità difensiva con le medie voto vere e rifai la
> verifica sulle bande di prezzo.

> Rigenera il listone col file aggiornato che ho appena messo in dati/, e
> dimmi cosa è cambiato rispetto a prima.

> Ecco la lista dei rigoristi. Portala nel modello.

## Le due cose che deve sempre rifiutare

Se per qualsiasi motivo si mette a scrivere nel repository `fc-cazzimma-dati`,
o a salvare un token in un file, fermalo. Sono le due regole in `CLAUDE.md` che
non hanno eccezioni.
