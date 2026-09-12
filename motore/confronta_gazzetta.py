"""Confronta il nostro listone con quello del Fantacampionato della Gazzetta.

La Gazzetta aggiorna le sue quotazioni ogni settimana, dopo le partite: e' un
secondo parere sulle gerarchie. Usa una scala sua (21 giocatori, altro gioco),
quindi i costi non si confrontano uno a uno: si confronta la posizione dentro
il ruolo. Chi la Gazzetta mette molto piu' in alto di noi e' salito nelle
gerarchie; chi mette molto piu' in basso va verificato prima di pagarlo.

Il file della Gazzetta e' un CSV con tre colonne, nome;squadra;costo, ricavato
dal PDF del giornale (pdftotext -raw sulla pagina del listone, righe
"NOME SQUADRA COSTO"). Gli allenatori vanno tolti.

Uso:
    python3 motore/confronta_gazzetta.py dati/gazzetta-2026-09-11-grezzo.csv
Scrive report/confronto-gazzetta.md (privato).
"""

import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from listone import leggi
from regole import SLOT, SQUADRE_PER_LEGA

COMPRATI = {r: SLOT[r] * SQUADRE_PER_LEGA for r in SLOT}
SOGLIA_SU, SOGLIA_GIU = 25, 20       # posizioni di differenza per segnalare
COSTO_MINIMO_CAMBIO = 8              # sotto, un cognome uguale in un'altra squadra e' un omonimo


def norm(t):
    return re.sub(r"[^a-z]", "", unicodedata.normalize("NFD", str(t)).encode("ascii", "ignore").decode().lower())


def parole(nome):
    return str(nome).replace("’", "'").split()


def cognome(nome):
    return norm(" ".join(p for p in parole(nome) if not p.endswith(".")))


def ultima(nome):
    return norm([p for p in parole(nome) if not p.endswith(".")][-1])


def iniziali(nome):
    return [norm(p)[:1] for p in parole(nome) if p.endswith(".")]


def abbina(gazzetta, ufficiale):
    """Per cognome e squadra; poi per ultima parola e squadra; poi, solo se il
    costo e' alto, per solo cognome (giocatore trasferito dopo il file)."""
    per_sq, per_cognome, per_ultima = {}, {}, {}
    for _, r in ufficiale.iterrows():
        per_sq.setdefault((cognome(r["nome"]), norm(r["squadra"])), []).append(r)
        per_cognome.setdefault(cognome(r["nome"]), []).append(r)
        per_ultima.setdefault((ultima(r["nome"]), norm(r["squadra"])), []).append(r)

    def scegli(c, nome):
        if len(c) <= 1:
            return c
        for lettere in (iniziali(nome), [norm(p)[:1] for p in parole(nome) if not p.endswith(".")][:-1]):
            if lettere:
                c2 = [x for x in c if any(i in iniziali(x["nome"]) for i in lettere)]
                if len(c2) == 1:
                    return c2
        return c

    righe, nuovi, cambi = [], [], []
    for nome, sq, costo in gazzetta:
        c = scegli(per_sq.get((cognome(nome), norm(sq)), []), nome)
        come = "ok"
        if not c:
            c = scegli(per_ultima.get((ultima(nome), norm(sq)), []), nome)
        if not c and costo >= COSTO_MINIMO_CAMBIO:
            c = scegli(per_cognome.get(cognome(nome), []) or per_cognome.get(ultima(nome), []), nome)
            come = "cambio"
        if len(c) == 1:
            r = c[0]
            if come == "cambio":
                cambi.append((r["nome"], r["ruolo"], r["squadra"], sq.title(), costo))
            righe.append({"nome": r["nome"], "ruolo": r["ruolo"], "squadra": sq.title(), "qt": int(r["qt"]), "gazzetta": costo})
        elif not c and costo >= COSTO_MINIMO_CAMBIO:
            nuovi.append((nome.title(), sq.title(), costo))
    return righe, nuovi, cambi


def confronta(righe, listone):
    prezzi = {(x["n"], x["r"]): x["pr"] for x in listone}
    for x in righe:
        x["mercato"] = prezzi.get((x["nome"], x["ruolo"]), 0.0)
    for ruolo in SLOT:
        blocco = [x for x in righe if x["ruolo"] == ruolo]
        for chiave, campo in (("mercato", "pos_nostra"), ("gazzetta", "pos_gazzetta")):
            for i, x in enumerate(sorted(blocco, key=lambda x: -x[chiave]), 1):
                x[campo] = i
        for x in blocco:
            x["scarto"] = x["pos_nostra"] - x["pos_gazzetta"]
    su = sorted([x for x in righe if x["pos_gazzetta"] <= COMPRATI[x["ruolo"]] and x["scarto"] >= SOGLIA_SU], key=lambda x: -x["scarto"])
    giu = sorted([x for x in righe if x["pos_nostra"] <= COMPRATI[x["ruolo"]] * 0.6 and x["scarto"] <= -SOGLIA_GIU], key=lambda x: x["scarto"])
    return su, giu


def tabella(lista):
    out = ["| ruolo | giocatore | squadra | nostra posizione | posizione Gazzetta | Gazzetta | nostro mercato |",
           "|---|---|---|---:|---:|---:|---:|"]
    out += [f"| {x['ruolo']} | {x['nome']} | {x['squadra']} | {x['pos_nostra']}° | {x['pos_gazzetta']}° | {x['gazzetta']} | {round(x['mercato'])} |" for x in lista]
    return "\n".join(out)


if __name__ == "__main__":
    argomenti = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not argomenti:
        raise SystemExit(__doc__)
    percorso = Path(argomenti[0])
    with open(percorso, encoding="utf-8") as f:
        gazzetta = [(r["nome"], r["squadra"], int(r["costo"])) for r in csv.DictReader(f, delimiter=";")]
    ufficiale = leggi(RADICE / "dati" / "Quotazioni_Fantacalcio_Stagione_2026_27.xlsx")
    listone = json.loads((RADICE / "report" / "listone.json").read_text(encoding="utf-8"))["listone"]

    righe, nuovi, cambi = abbina(gazzetta, ufficiale)
    su, giu = confronta(righe, listone)
    data = re.search(r"\d{4}-\d{2}-\d{2}", percorso.name)
    data = data.group(0) if data else "?"

    doc = [f"# Confronto con il listone Gazzetta del {data}\n",
           "File privato: git lo ignora. La Gazzetta usa una scala sua, quindi si confronta la **posizione dentro il ruolo**, non il costo.\n",
           f"Abbinati {len(righe)} giocatori su {len(gazzetta)}.\n",
           "## Non nel nostro file ufficiale\n",
           "Se la lista e' lunga, il file delle quotazioni va riscaricato da Fantacalcio.it.\n",
           "| giocatore | squadra | Gazzetta |", "|---|---|---:|",
           *[f"| {n} | {s} | {c} |" for n, s, c in sorted(nuovi, key=lambda x: -x[2])],
           "\n## Squadra diversa dal nostro file\n",
           "| giocatore | ruolo | nel nostro file | per la Gazzetta | Gazzetta |", "|---|---|---|---|---:|",
           *[f"| {n} | {r} | {a} | {b} | {c} |" for n, r, a, b, c in sorted(cambi, key=lambda x: -x[4])],
           f"\n## In ascesa\n", f"La Gazzetta li mette almeno {SOGLIA_SU} posizioni piu' in alto di noi, dentro la zona di chi viene comprato.\n", tabella(su),
           f"\n## In calo\n", f"Noi li abbiamo alti, la Gazzetta almeno {SOGLIA_GIU} posizioni piu' in basso. Da verificare prima di pagarli il tetto.\n", tabella(giu)]
    uscita = RADICE / "report" / "confronto-gazzetta.md"
    uscita.write_text("\n".join(doc) + "\n", encoding="utf-8")

    print(f"\n  abbinati {len(righe)} su {len(gazzetta)} · non nel file: {len(nuovi)} · squadra diversa: {len(cambi)}")
    print(f"  in ascesa: {len(su)} · in calo: {len(giu)}")
    for titolo, lista in (("IN ASCESA", su[:15]), ("IN CALO", giu[:15])):
        print(f"\n  {titolo}")
        for x in lista:
            print(f"    {x['ruolo']} {x['nome']:<18} {x['squadra']:<11} noi {x['pos_nostra']:>3}° · Gazzetta {x['pos_gazzetta']:>3}°")
    if nuovi:
        print("\n  non nel file ufficiale: " + ", ".join(f"{n} ({s})" for n, s, c in sorted(nuovi, key=lambda x: -x[2])[:12]))
    print(f"\n  → {uscita.relative_to(RADICE)}\n")
