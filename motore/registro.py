"""Il registro delle estrazioni: quando abbiamo guardato ogni fonte, l'ultima
volta, e fin dove eravamo arrivati.

I siti si aggiornano di continuo: senza un segno del tempo non si sa da dove
riprendere e si rischia di rileggere tutto o, peggio, di saltare un pezzo.
Qui, in dati/estrazioni.json, per ogni fonte restano l'ora dell'ultimo
controllo, la data e ora dell'articolo piu' recente che abbiamo preso, quanti
ne sono arrivati e le ultime venti passate. Marco vede a colpo d'occhio se
una fonte e' ferma.

Uso da riga di comando:
    python3 motore/registro.py            # cosa abbiamo guardato e quando
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
FILE = RADICE / "dati" / "estrazioni.json"
ROMA = timezone(timedelta(hours=2))
STORIA_MAX = 20


def adesso():
    return datetime.now(ROMA).strftime("%Y-%m-%d %H:%M")


def carica():
    if FILE.exists():
        return json.loads(FILE.read_text(encoding="utf-8"))
    return {}


def ultimo(fonte):
    """L'articolo piu' recente gia' preso da questa fonte ('AAAA-MM-GG HH:MM'),
    o None se non l'abbiamo mai guardata. E' da qui che si riparte."""
    return carica().get(fonte, {}).get("ultimo_articolo")


def segna(fonte, nuovi=0, ultimo_articolo=None, nota=""):
    """Chiude un'estrazione: quando l'abbiamo fatta, quanto ha portato, fin
    dove siamo arrivati. `ultimo_articolo` non torna mai indietro."""
    registro = carica()
    voce = registro.setdefault(fonte, {"storia": []})
    voce["ultimo_controllo"] = adesso()
    if ultimo_articolo and ultimo_articolo > (voce.get("ultimo_articolo") or ""):
        voce["ultimo_articolo"] = ultimo_articolo
    voce["ultimi_nuovi"] = nuovi
    voce["storia"] = ([{"quando": voce["ultimo_controllo"], "nuovi": nuovi, **({"nota": nota} if nota else {})}]
                      + voce.get("storia", []))[:STORIA_MAX]
    FILE.parent.mkdir(exist_ok=True)
    FILE.write_text(json.dumps(registro, ensure_ascii=False, indent=1), encoding="utf-8")
    return voce


def quanto_fa(quando):
    try:
        d = datetime.strptime(quando, "%Y-%m-%d %H:%M").replace(tzinfo=ROMA)
    except (ValueError, TypeError):
        return "?"
    minuti = int((datetime.now(ROMA) - d).total_seconds() // 60)
    if minuti < 60:
        return f"{minuti} min fa"
    if minuti < 60 * 36:
        return f"{minuti // 60} ore fa"
    return f"{minuti // 1440} giorni fa"


def stampa():
    registro = carica()
    if not registro:
        print("Nessuna estrazione registrata.")
        return
    print(f"{'fonte':<20}  {'ultimo controllo':<18}{'quanto fa':<14}{'ultimo preso':<18}nuovi")
    for fonte, v in sorted(registro.items(), key=lambda kv: kv[1].get("ultimo_controllo", ""), reverse=True):
        print(f"{fonte:<20}  {v.get('ultimo_controllo','-'):<18}{quanto_fa(v.get('ultimo_controllo')):<14}"
              f"{v.get('ultimo_articolo') or '-':<18}{v.get('ultimi_nuovi', 0)}")


if __name__ == "__main__":
    stampa()
