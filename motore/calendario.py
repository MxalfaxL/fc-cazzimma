"""Chi incontra ogni squadra nelle prime giornate dopo l'asta.

L'asta e' il 7 ottobre, la 6ª giornata il 10-12: i primi turni di una rosa si
giocano contro avversari che conosciamo gia'. Qui non si da' un voto al
calendario, si mettono in fila i numeri che servono per darlo a ottobre:
per ogni partita, casa o trasferta e quanti gol a partita segna e subisce
l'avversario, in questa stagione (5 giornate) e nella scorsa (38).

Per le tre salite dalla B i numeri della scorsa stagione sono di Serie B e
lo scriviamo accanto: non sono confrontabili a occhio con quelli di A.

Uso:
    python3 motore/calendario.py            # giornate 6-10
    python3 motore/calendario.py 6 15       # un altro intervallo
Scrive report/CALENDARIO.md (privato).
"""

import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
CALENDARIO = RADICE / "dati" / "calendario-2026-27.json"
STAGIONE_SCORSA = RADICE / "dati" / "stagione-2025-26.json"
QUESTA = RADICE / "dati" / "squadre-2026-27.json"
USCITA = RADICE / "report" / "CALENDARIO.md"


def per_partita(gf, gs, partite):
    return (round(gf / partite, 2), round(gs / partite, 2)) if partite else (None, None)


def main():
    da, a = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) == 3 else (6, 10)
    for f in (CALENDARIO, STAGIONE_SCORSA, QUESTA):
        if not f.exists():
            sys.exit(f"Manca {f.relative_to(RADICE)}")
    cal = json.load(open(CALENDARIO, encoding="utf-8"))["giornate"]
    scorsa = json.load(open(STAGIONE_SCORSA, encoding="utf-8"))
    questa = json.load(open(QUESTA, encoding="utf-8"))["squadre"]

    numeri = {}
    for r in scorsa["classifica"]:
        numeri[r["squadra"]] = {"prima": per_partita(r["gf"], r["gs"], r["v"] + r["n"] + r["p"]), "serie": "A"}
    for r in scorsa.get("serie_b_neopromosse", []):
        numeri[r["squadra"]] = {"prima": per_partita(r["gf"], r["gs"], 38), "serie": "B"}
    for sq, s in questa.items():
        # i gol fatti del file ufficiale non contano gli autogol degli avversari:
        # e' una differenza di un gol ogni tanto, dichiarata
        numeri.setdefault(sq, {"prima": (None, None), "serie": "?"})["ora"] = \
            per_partita(s["gol_fatti_senza_autogol_avversari"], s["gol_subiti"], s["giocate"])

    squadre = sorted(questa)
    righe = [f"# Calendario delle giornate {da}-{a}, con i numeri degli avversari", "",
             "Per ogni partita: avversario (C casa, T trasferta), gol fatti e subiti a partita",
             "dall'avversario in questa stagione (5 giornate) / nella scorsa (38; per le",
             "neopromosse e' la Serie B, marcata B). Nessun giudizio: i numeri per decidere a ottobre.", ""]
    intestazione = "| Squadra | " + " | ".join(f"{g}ª" for g in range(da, a + 1)) + " |"
    righe += [intestazione, "|---" * (a - da + 2) + "|"]
    for sq in squadre:
        celle = []
        for g in range(da, a + 1):
            giornata = next((x for x in cal if x["giornata"] == g), None)
            partita = next((p for p in giornata["partite"] if sq in (p["casa"], p["trasferta"])), None) if giornata else None
            if not partita:
                celle.append("?")
                continue
            casa = partita["casa"] == sq
            avv = partita["trasferta"] if casa else partita["casa"]
            n = numeri.get(avv, {})
            ora, prima = n.get("ora", (None, None)), n.get("prima", (None, None))
            b = " B" if n.get("serie") == "B" else ""
            celle.append(f"{avv} ({'C' if casa else 'T'}) {ora[0]}-{ora[1]} / {prima[0]}-{prima[1]}{b}")
        righe.append(f"| **{sq}** | " + " | ".join(celle) + " |")
    righe += ["", "Lettura: \"Genoa (C) 1.2-2.0 / 1.1-1.5\" = in casa col Genoa, che quest'anno segna 1.2",
              "e subisce 2.0 a partita, e l'anno scorso 1.1 e 1.5."]
    USCITA.write_text("\n".join(righe) + "\n", encoding="utf-8")
    print(f"Giornate {da}-{a} per {len(squadre)} squadre → {USCITA.relative_to(RADICE)}")


if __name__ == "__main__":
    main()
