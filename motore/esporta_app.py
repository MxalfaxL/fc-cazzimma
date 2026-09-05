"""Prepara il blocco di dati che l'app si aspetta.

Il Mac fa il lavoro pesante (statistiche, avversario di giornata, probabili
formazioni) e lo riassume in tre numeri per giocatore. L'app li riceve
e da li' in poi lavora da sola, anche dal telefono.

Uso:
    python3 motore/esporta_app.py 7                 # stampa il blocco
    python3 motore/esporta_app.py 7 | pbcopy        # e te lo mette negli appunti
    python3 motore/esporta_app.py 7 --salva         # scrive anche report/settimana.json
"""

import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
ROSA = RADICE / "dati" / "rosa.json"
USCITA = RADICE / "report" / "settimana.json"


def stato_da_probabilita(p):
    """L'app ragiona per stati, non per decimali: e' piu' veloce da correggere
    con un dito la sera prima della partita."""
    if p >= 0.8:
        return "T"      # titolare
    if p > 0:
        return "B"      # ballottaggio
    return "F"          # fuori


def esporta(giornata):
    if not ROSA.exists():
        raise SystemExit(f"Manca {ROSA}. Compilalo dopo l'asta.")
    dati = json.loads(ROSA.read_text(encoding="utf-8"))
    voci = dati["giocatori"] if isinstance(dati, dict) else dati

    giocatori = []
    for v in voci:
        if str(v.get("nome", "")).startswith("Esempio"):
            continue
        giocatori.append({
            "nome": v["nome"],
            "fv": round(float(v.get("fv", 6.0)), 2),
            "voto": round(float(v.get("voto", 6.0)), 2),
            "st": stato_da_probabilita(float(v.get("p", 1.0))),
        })

    if not giocatori:
        raise SystemExit("Nessun giocatore vero in rosa.json: ci sono solo le righe di esempio.")

    return {"giornata": giornata, "giocatori": giocatori}


if __name__ == "__main__":
    argomenti = [a for a in sys.argv[1:] if not a.startswith("--")]
    giornata = int(argomenti[0]) if argomenti else 1
    blocco = esporta(giornata)
    testo = json.dumps(blocco, ensure_ascii=False, separators=(",", ":"))

    if "--salva" in sys.argv:
        USCITA.parent.mkdir(exist_ok=True)
        USCITA.write_text(testo, encoding="utf-8")
        print(f"Scritto in {USCITA}", file=sys.stderr)

    print(testo)
