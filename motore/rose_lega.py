"""Le rose di tutta la lega dopo l'asta, controllate prima di fidarsene.

In asta alcuni 'via' non sono stati segnati, altri senza compratore o senza
prezzo: la fonte vera sono gli screenshot dell'app Fantacalcio che Marco manda
squadra per squadra, ricopiati in dati/rose-lega-2026-27.json. Ricopiare a mano
25 righe per 9 squadre sbaglia, quindi qui si controlla tutto quello che si
puo' controllare da soli:

- 3/8/8/6 per ruolo;
- i crediti: la lega e' a 500, ma la piattaforma parte da 9999, quindi
  9999 meno i crediti mostrati e' quanto ha speso la squadra e deve fare la
  somma dei prezzi. Se non torna, c'e' un prezzo letto male. Restano 500 meno
  la spesa;
- ogni nome esiste nel listone con quel ruolo e quella squadra;
- nessun giocatore sta in due rose (FC Cazzimma compresa).

Con --confronta si mette accanto lo stato dell'app (una copia di stato.json):
chi l'app non aveva, chi aveva senza compratore o con un prezzo diverso.

Uso:
    python3 motore/rose_lega.py
    python3 motore/rose_lega.py --confronta dati/asta-backup-2026-10-08_0000-finale.json
Scrive report/ROSE-LEGA.md (privato).
"""

import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regole import BUDGET, SLOT  # noqa: E402

RADICE = Path(__file__).resolve().parent.parent
ROSE = RADICE / "dati" / "rose-lega-2026-27.json"
MIA = RADICE / "dati" / "rosa-2026-27.json"
LISTONE = RADICE / "report" / "listone.json"
LEGA = RADICE / "dati" / "lega.json"
USCITA = RADICE / "report" / "ROSE-LEGA.md"
ORDINE = ["P", "D", "C", "A"]


def norm(nome):
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return " ".join(s.lower().replace("'", "").replace(".", "").split())


def carica(f):
    return json.load(open(f, encoding="utf-8"))


def controlla_squadra(sq, budget_piattaforma, listone):
    """Restituisce (crediti veri, lista di problemi) per una squadra."""
    problemi = []
    rosa = sq["rosa"]
    conti = Counter(g["r"] for g in rosa)
    for r in ORDINE:
        if conti[r] != SLOT[r]:
            problemi.append(f"{r}: {conti[r]} invece di {SLOT[r]}")
    spesi = sum(g["pagato"] for g in rosa)
    spesi_app = budget_piattaforma - sq["crediti_app"]
    veri = BUDGET - spesi_app
    if spesi_app != spesi:
        problemi.append(f"crediti: per la piattaforma ha speso {spesi_app}, i prezzi sommano {spesi}: "
                        f"c'e' un prezzo letto male")
    for g in rosa:
        voce = listone.get(norm(g["n"]))
        if voce is None:
            problemi.append(f"{g['n']} non e' nel listone")
            continue
        if voce["r"] != g["r"]:
            problemi.append(f"{g['n']}: ruolo {g['r']}, il listone dice {voce['r']}")
        if voce["sq"] != g["sq"]:
            problemi.append(f"{g['n']}: squadra {g['sq']}, il listone dice {voce['sq']}")
    return veri, spesi, problemi


def confronta_app(squadre, stato, cognomi_app):
    """Cosa cambia nell'app se le rose degli screenshot diventano la verita'."""
    avv = [a["n"] for a in stato.get("avversari", [])]
    venduti = {norm(v["n"]): v for v in stato.get("venduti", [])}
    righe = []
    for sq in squadre:
        mancanti, senza_chi, altro_chi, prezzo = [], [], [], []
        for g in sq["rosa"]:
            v = venduti.get(norm(g["n"]))
            if v is None:
                mancanti.append(f"{g['n']} {g['pagato']}")
                continue
            a = v.get("a")
            chi = avv[a] if isinstance(a, int) and 0 <= a < len(avv) else None
            if chi is None:
                senza_chi.append(g["n"])
            elif sq.get("cognome") and chi != sq["cognome"]:
                altro_chi.append(f"{g['n']} (l'app: {chi})")
            if v.get("p") not in (None, g["pagato"]):
                prezzo.append(f"{g['n']} {v['p']} → {g['pagato']}")
            elif v.get("p") is None:
                pass  # il prezzo mancante e' il caso normale, non lo elenchiamo uno per uno
        segnati_con_prezzo = sum(1 for g in sq["rosa"] if (venduti.get(norm(g["n"])) or {}).get("p") is not None)
        righe.append((sq, mancanti, senza_chi, altro_chi, prezzo, segnati_con_prezzo))
    presi = {norm(g["n"]) for sq in squadre for g in sq["rosa"]}
    orfani = [v for k, v in venduti.items() if k not in presi]
    return righe, orfani


def main():
    args = sys.argv[1:]
    file_stato = None
    if args[:1] == ["--confronta"] and len(args) == 2:
        file_stato = Path(args[1])
    for f in (ROSE, MIA, LISTONE):
        if not f.exists():
            sys.exit(f"Manca {f.relative_to(RADICE)}")
    dati = carica(ROSE)
    squadre = dati["squadre"]
    mia = carica(MIA)
    listone = {norm(v["n"]): v for v in carica(LISTONE)["listone"]}
    cognomi = carica(LEGA)["avversari"] if LEGA.exists() else []

    out = ["# Le rose della lega dopo l'asta", "",
           f"Da `dati/rose-lega-2026-27.json`: {len(squadre)} avversari su 9 ricopiati dagli screenshot.", ""]
    tutti_ok = True
    print(f"{len(squadre)} avversari su 9\n")
    for sq in squadre:
        veri, spesi, problemi = controlla_squadra(sq, dati["budget_piattaforma"], listone)
        # nome e cognome della persona, quando li sappiamo: Marco non li ricorda tutti
        persona = sq.get("persona") or sq["allenatore"]
        chi = persona if sq.get("cognome") else f"{persona} (cognome da confermare)"
        stato_riga = "OK" if not problemi else "DA RIVEDERE"
        tutti_ok &= not problemi
        print(f"{sq['nome']} · {chi} · spesi {spesi}, restano {veri} · {stato_riga}")
        for p in problemi:
            print(f"   ! {p}")
        out += [f"## {sq['nome']} — {chi}", "",
                f"Spesi {spesi}, restano {veri}. Controllo: {stato_riga}.", ""]
        out += [f"- {p}" for p in problemi]
        out += ["| Ruolo | Giocatori (pagato) | Totale |", "|---|---|---|"]
        for r in ORDINE:
            gs = sorted((g for g in sq["rosa"] if g["r"] == r), key=lambda g: -g["pagato"])
            out.append(f"| {r} | " + ", ".join(f"{g['n']} ({g['sq']}) {g['pagato']}" for g in gs)
                       + f" | {sum(g['pagato'] for g in gs)} |")
        out.append("")

    # un giocatore in due rose vuol dire che uno screenshot e' stato ricopiato male
    dove = {}
    for nome_sq, rosa in [(s["nome"], s["rosa"]) for s in squadre] + [(mia["squadra"], mia["rosa"])]:
        for g in rosa:
            # rosa-2026-27.json scrive "nome", le rose degli screenshot "n"
            dove.setdefault(norm(g.get("n") or g["nome"]), []).append(nome_sq)
    doppi = {k: v for k, v in dove.items() if len(v) > 1}
    for k, v in doppi.items():
        tutti_ok = False
        print(f"! {k} sta in due rose: {', '.join(v)}")
        out.append(f"- **{k} sta in due rose**: {', '.join(v)}")

    senza = [c for c in cognomi if c not in {s.get("cognome") for s in squadre}]
    if senza:
        print(f"\nMancano ancora: {', '.join(senza)} (o il loro nome sulla piattaforma)")

    if file_stato:
        stato = carica(file_stato)
        righe, orfani = confronta_app(squadre, stato, cognomi)
        print(f"\nConfronto con l'app ({file_stato.name}, v{stato.get('v')}):")
        out += ["", f"## Confronto con l'app ({file_stato.name}, v{stato.get('v')})", ""]
        for sq, mancanti, senza_chi, altro_chi, prezzo, con_prezzo in righe:
            riga = (f"{sq['nome']}: {len(mancanti)} non segnati, {len(senza_chi)} senza compratore, "
                    f"{len(altro_chi)} a un altro, {con_prezzo} col prezzo")
            print("  " + riga)
            out.append(f"- **{riga}**")
            for titolo, lista in (("non segnati", mancanti), ("a un altro", altro_chi), ("prezzo diverso", prezzo)):
                if lista:
                    print(f"     {titolo}: {', '.join(lista)}")
                    out.append(f"  - {titolo}: {', '.join(lista)}")
        if len(squadre) == 9 and orfani:
            print(f"  'via' nell'app che non sono in nessuna rosa: {', '.join(v['n'] for v in orfani)}")
            out.append(f"- 'via' nell'app che non sono in nessuna rosa: {', '.join(v['n'] for v in orfani)}")

    USCITA.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\n{'Tutto torna.' if tutti_ok else 'CI SONO PROBLEMI, vedi sopra.'} Scritto {USCITA.relative_to(RADICE)}")


if __name__ == "__main__":
    main()
