# FC Cazzimma

Sistema personale per il Fantacalcio Venezia 2026/27: preparazione e assistenza
all'asta, consigliere di formazione con il modificatore difesa, gestione della
stagione.

- `index.html` è l'app, una PWA senza dipendenze pubblicata su GitHub Pages.
- `motore/` è il codice Python che fa i conti lunghi sul Mac.
- `docs/` è la documentazione: si parte da `docs/AVVIO.md`.

Per provare il motore:

```bash
python3 motore/ottimizzatore.py
python3 motore/verifica_parita.py
```

Le istruzioni per lavorarci con Claude Code sono in `CLAUDE.md`.
