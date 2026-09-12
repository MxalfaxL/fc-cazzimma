"""Tira fuori da un PDF della Gazzetta le pagine che parlano di Serie A.

Marco butta i giornali nella cartella "Gazzetta dello sport/" in radice, con
il nome che hanno. Il PDF e' lungo e quasi tutto non ci riguarda: questo
script legge ogni pagina con pdftotext, conta quanti giocatori del nostro
listone e quante squadre di A vengono nominati, e salva solo le pagine dense
in dati/gazzetta/AAAA-MM-GG/ (la data la legge dalla prima pagina), con un indice che dice per ogni pagina di che tipo sembra (pagelle, listone,
probabili, articolo) e chi viene citato. Il lavoro di capire *cosa* dicono
dei giocatori lo fa poi chi legge quelle pagine e scrive nel dossier
(motore/dossier.py): un parser non capisce "rischia di saltare il derby".

Uso:
    python3 motore/leggi_gazzetta.py                       # tutti i PDF della cartella non ancora letti
    python3 motore/leggi_gazzetta.py "Gazzetta dello sport/x.pdf"   # uno solo, anche se gia' letto
    ... --tutte                                            # salva ogni pagina, anche quelle vuote

Tutto resta in dati/, che git ignora: e' un giornale comprato, uso personale.
"""

import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
LISTONE = RADICE / "report" / "listone.json"
CARTELLA_PDF = RADICE / "Gazzetta dello sport"
CARTELLA_TESTO = RADICE / "dati" / "gazzetta"

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]

# Sotto questa densita' la pagina non parla di Serie A (o ne parla di striscio).
SOGLIA_GIOCATORI = 4
# Cognomi cortissimi ("Rui", "Pau") trovano omonimi ovunque: contano solo se
# accompagnati da altri segnali, non da soli.
LUNGHEZZA_MINIMA = 4

TIPI = {
    "listone": ("ALLENATORI", "FANTACAMPIONATO", "IL LISTONE"),
    "pagelle": ("PAGELLE", "LE PAGELLE", "IL MIGLIORE", "IL PEGGIORE"),
    "probabili": ("PROBABILI", "IN DUBBIO", "SQUALIFICATI", "INDISPONIBILI", "BALLOTTAGG"),
    "fantacalcio": ("FANTACALCIO", "FANTA", "CONSIGLI", "CHI SCHIERARE"),
}


def norm(t):
    return re.sub(r"[^a-z]", "", unicodedata.normalize("NFD", str(t)).encode("ascii", "ignore").decode().lower())


def cognome(nome_listone):
    """'Martinez L.' -> 'martinez'; 'Nico Paz' -> 'nicopaz' e anche 'paz'."""
    parti = [p for p in str(nome_listone).replace("’", "'").split() if not p.endswith(".")]
    intero = norm(" ".join(parti))
    return intero, norm(parti[-1]) if parti else intero


def carica_listone():
    if not LISTONE.exists():
        sys.exit(f"Manca {LISTONE}: prima python3 motore/listone.py")
    dati = json.load(open(LISTONE, encoding="utf-8"))
    giocatori = dati["listone"]
    squadre = sorted({g["sq"] for g in giocatori})
    # chiave normalizzata -> nome del listone. Se due giocatori condividono il
    # cognome (Martinez L. / Martinez J.) la citazione vale per entrambi:
    # meglio un dubbio dichiarato che un'attribuzione sbagliata.
    per_chiave = {}
    for g in giocatori:
        intero, ultimo = cognome(g["n"])
        for chiave in {intero, ultimo}:
            if len(chiave) >= LUNGHEZZA_MINIMA:
                per_chiave.setdefault(chiave, set()).add(g["n"])
    return per_chiave, squadre


def pagine_del_pdf(pdf):
    """Numero di pagine e generatore (numero, testo) via pdftotext -raw.
    -raw e non -layout: il layout tronca i nomi nelle colonne strette."""
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    m = re.search(r"Pages:\s+(\d+)", info)
    if not m:
        sys.exit(f"pdfinfo non legge {pdf}: e' un PDF vero?")
    n = int(m.group(1))
    for p in range(1, n + 1):
        testo = subprocess.run(
            ["pdftotext", "-raw", "-f", str(p), "-l", str(p), str(pdf), "-"],
            capture_output=True, text=True,
        ).stdout
        yield p, testo


def analizza_pagina(testo, per_chiave, squadre):
    parole = re.findall(r"[A-Za-zÀ-ÿ'’]+", testo)
    trovati = Counter()
    # cognomi singoli e coppie di parole (per "Nico Paz", "De Roon")
    candidati = [norm(w) for w in parole]
    coppie = [norm(a + b) for a, b in zip(parole, parole[1:])]
    for chiave in candidati + coppie:
        if chiave in per_chiave:
            for nome in per_chiave[chiave]:
                trovati[nome] += 1
    squadre_citate = sorted(s for s in squadre if re.search(r"\b" + re.escape(s) + r"\b", testo, re.I))

    maiuscolo = testo.upper()
    tipo = "articolo"
    for nome_tipo, spie in TIPI.items():
        if any(s in maiuscolo for s in spie):
            tipo = nome_tipo
            break
    # le pagelle sono piene di voti come 6,5 / 5,5: se ce ne sono tanti e' quello
    voti = len(re.findall(r"\b[4-9],5\b|\b[4-9]\b(?=\s|$)", testo))
    if tipo == "articolo" and voti > 40 and len(trovati) >= 15:
        tipo = "pagelle"
    return trovati, squadre_citate, tipo


def data_del_giornale(pdf):
    """AAAA-MM-GG dal nome del file se c'e', altrimenti dalla testata della
    prima pagina ("MARTEDI' 15 SETTEMBRE 2026"); in mancanza, il nome del file."""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", pdf.name)
    if m:
        return m.group(0)
    prima = subprocess.run(["pdftotext", "-raw", "-f", "1", "-l", "1", str(pdf), "-"],
                           capture_output=True, text=True).stdout.lower()
    m = re.search(r"(\d{1,2})\s+(" + "|".join(MESI) + r")\s+(\d{4})", prima)
    if m:
        return f"{m.group(3)}-{MESI.index(m.group(2)) + 1:02d}-{int(m.group(1)):02d}"
    return norm(pdf.stem) or "senza-data"


def leggi_pdf(pdf, per_chiave, squadre, tutte=False):
    etichetta = data_del_giornale(pdf)
    uscita = CARTELLA_TESTO / etichetta
    uscita.mkdir(parents=True, exist_ok=True)
    indice, totale = [], Counter()
    for p, testo in pagine_del_pdf(pdf):
        trovati, squadre_citate, tipo = analizza_pagina(testo, per_chiave, squadre)
        densa = len(trovati) >= SOGLIA_GIOCATORI or (len(trovati) >= 2 and len(squadre_citate) >= 2)
        if densa or tutte:
            (uscita / f"p{p:03d}.txt").write_text(testo, encoding="utf-8")
        if densa:
            totale.update(trovati)
            indice.append((p, tipo, len(trovati), squadre_citate, trovati.most_common(12)))

    righe = [f"# Gazzetta {etichetta} — pagine che parlano di Serie A", ""]
    if not indice:
        righe.append("Nessuna pagina densa di Serie A. O il PDF e' un'altra cosa, o pdftotext non legge il testo (scansione?).")
    for p, tipo, n, sq, top in indice:
        righe.append(f"## p{p:03d} · {tipo} · {n} giocatori · {', '.join(sq) or 'nessuna squadra'}")
        righe.append("  " + ", ".join(f"{nome} ({k})" for nome, k in top))
        righe.append("")
    righe.append("## Piu' citati in tutto il giornale")
    righe.append("  " + ", ".join(f"{nome} ({k})" for nome, k in totale.most_common(40)))
    (uscita / "indice.md").write_text("\n".join(righe) + "\n", encoding="utf-8")

    print(f"{pdf.name} → {etichetta}: {len(indice)} pagine di Serie A in {uscita.relative_to(RADICE)}/")
    for p, tipo, n, sq, top in indice:
        print(f"  p{p:03d}  {tipo:<11} {n:>3} giocatori  {', '.join(sq)[:60]}")
    return etichetta


def main(argv):
    tutte = "--tutte" in argv
    espliciti = [Path(a) for a in argv[1:] if not a.startswith("--")]
    per_chiave, squadre = carica_listone()
    if espliciti:
        for pdf in espliciti:
            if not pdf.exists():
                sys.exit(f"Non trovo {pdf}")
            leggi_pdf(pdf, per_chiave, squadre, tutte)
        return
    CARTELLA_PDF.mkdir(exist_ok=True)
    pdfs = sorted(CARTELLA_PDF.glob("*.pdf")) + sorted(CARTELLA_PDF.glob("*.PDF"))
    if not pdfs:
        sys.exit(f'Nessun PDF in "{CARTELLA_PDF.name}/": Marco deve caricarli li\'.')
    fatti = 0
    for pdf in pdfs:
        etichetta = data_del_giornale(pdf)
        if (CARTELLA_TESTO / etichetta / "indice.md").exists():
            print(f"{pdf.name} → {etichetta}: gia' letta, salto")
            continue
        leggi_pdf(pdf, per_chiave, squadre, tutte)
        fatti += 1
    print(f"\n{fatti} giornali nuovi su {len(pdfs)}. Adesso: leggere gli indici e aggiornare il dossier (motore/dossier.py).")


if __name__ == "__main__":
    main(sys.argv)
