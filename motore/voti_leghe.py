"""I voti ufficiali della lega, dai tabellini di SOS Fanta.

Il regolamento della Lega Minuetto dice che il risultato si fa con i voti
pubblicati da Leghe (Fantacalcio.it). Quelli della Gazzetta, che il dossier ha
raccolto fin qui, sono un'altra scala: buoni per capire chi gioca bene, non
per stimare i fantapunti che faremo davvero.

SOS Fanta (gruppo Gazzetta) pubblica dopo ogni partita l'articolo "I voti di
X-Y al fanta" con il tabellino completo nella scala di Leghe, e quel feed lo
scarichiamo gia' (leggi_sosfanta.py). Qui dentro si legge quel tabellino: e'
un formato regolare, quindi un parser lo fa meglio e a costo zero rispetto a
un lettore ad agenti.

Un articolo puo' contenere piu' partite ("Gli altri voti:"). I nomi sono gia'
quelli di Fantacalcio.it, cioe' gli stessi del nostro listone: l'abbinamento
usa la squadra della partita per sciogliere gli omonimi (Thuram, Adams,
Rodriguez, Martinez...), che e' il motivo per cui sbagliamo poco.

Uso:
    python3 motore/voti_leghe.py                          # tutte le cartelle di dati/sosfanta
    python3 motore/voti_leghe.py dati/sosfanta/2026-09-13  # una sola
    python3 motore/voti_leghe.py --prova                   # non scrive niente, fa vedere cosa troverebbe

Scrive nella cartella del giorno un `voti-leghe.json` nel formato di
dossier.py (fonte "leghe"), pronto per `dossier.py importa`.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
LISTONE = RADICE / "report" / "listone.json"
CARTELLE = RADICE / "dati" / "sosfanta"

# Da quale giorno parte ogni giornata di campionato. L'intestazione degli
# articoli NON serve: e' un testo riusato che dice "seconda giornata" anche a
# settembre (verificato il 14/9 su quattro articoli di tre giornate diverse).
# La giornata si ricava dalla data dell'articolo, che esce subito dopo la
# partita. Una giornata va dal suo anticipo al giorno prima dell'anticipo
# successivo: con le soste delle nazionali o i turni infrasettimanali questa
# tabella va allungata a mano, e se una data non ci cade dentro il parser lo
# dice invece di indovinare.
INIZIO_GIORNATA = {
    1: "2026-08-20",
    2: "2026-08-27",
    3: "2026-09-03",
    4: "2026-09-10",
    5: "2026-09-17",
}

GIORNATE = ["prima", "seconda", "terza", "quarta", "quinta", "sesta", "settima", "ottava",
            "nona", "decima", "undicesima", "dodicesima", "tredicesima", "quattordicesima",
            "quindicesima", "sedicesima", "diciassettesima", "diciottesima", "diciannovesima",
            "ventesima", "ventunesima", "ventiduesima", "ventitreesima", "ventiquattresima",
            "venticinquesima", "ventiseiesima", "ventisettesima", "ventottesima",
            "ventinovesima", "trentesima", "trentunesima", "trentaduesima", "trentatreesima",
            "trentaquattresima", "trentacinquesima", "trentaseiesima", "trentasettesima",
            "trentottesima"]

# Le voci in coda al tabellino: dicono chi ha fatto cosa. "Gol" e "Assist" li
# usiamo come eventi del voto, non per ricalcolare il fantavoto: quando uno fa
# doppietta il tabellino non sempre lo scrive due volte, e un fantavoto
# sbagliato e' peggio di un fantavoto assente.
EVENTI = ("Gol", "Assist", "Ammoniti", "Espulsi", "Rigori sbagliati",
          "Rigori segnati", "Rigori parati", "Autogol")


def ripulisci(testo):
    """I tabellini arrivano con la punteggiatura tipografica del web e cambia
    da un giorno all'altro: il minuto dei subentrati a volte e' 89' e a volte
    89′ (prime), il trattino fra squadra e voti a volte e' un en dash. Senza
    questa normalizzazione il 6 settembre sparivano tutti i subentrati."""
    for vecchio, nuovo in (("\u2032", "'"), ("\u2019", "'"), ("\u2018", "'"), ("\u00b4", "'"),
                           ("\u2013", "-"), ("\u2014", "-"), ("\u00a0", " ")):
        testo = testo.replace(vecchio, nuovo)
    return testo


def norm(t):
    return re.sub(r"[^a-z]", "", unicodedata.normalize("NFD", str(t)).encode("ascii", "ignore").decode().lower())


def carica_listone():
    if not LISTONE.exists():
        sys.exit(f"Manca {LISTONE}: prima python3 motore/listone.py")
    giocatori = json.load(open(LISTONE, encoding="utf-8"))["listone"]
    per_squadra = {}
    for g in giocatori:
        per_squadra.setdefault(norm(g["sq"]), {})[norm(g["n"])] = g["n"]
    esatti = {norm(g["n"]): g["n"] for g in giocatori}
    squadre = sorted({g["sq"] for g in giocatori})
    return per_squadra, esatti, squadre


def trova_nome(grezzo, squadra, per_squadra, esatti):
    """Il nome come lo scrive il tabellino -> il nome del listone. Prima dentro
    la squadra che sta giocando (cosi' 'Thuram' e' quello giusto), poi ovunque,
    poi per cognome: 'Ederson D.S.' e 'Ederson' sono lo stesso giocatore."""
    chiave = norm(grezzo)
    if not chiave:
        return None
    rosa = per_squadra.get(norm(squadra), {})
    if chiave in rosa:
        return rosa[chiave]
    # il match per prefisso serve per "Ederson D.S." scritto "Ederson", ma in
    # una rosa puo' pescare due persone: la Roma ha Pellegrini Lo. e
    # Pellegrini Lu., e un voto dato al gemello sbagliato falsa due medie.
    # Se i candidati sono piu' di uno, meglio non abbinato che indovinato.
    candidati = {nome for k, nome in rosa.items() if k.startswith(chiave) or chiave.startswith(k)}
    if len(candidati) == 1:
        return candidati.pop()
    if candidati:
        return None
    if chiave in esatti:
        return esatti[chiave]
    return None


def pezzi_voto(testo):
    """Da 'Carnesecchi 6,5; Bellanova 5,5 (68' Bernasconi 6)' alle coppie
    (nome, voto). I subentrati stanno fra parentesi col minuto davanti."""
    fuori = []
    for minuto, nome, voto in re.findall(r"\((\d+)'\s*([^)\d]+?)\s+(\d{1,2}(?:[,.]\d)?|sv)\)", testo):
        fuori.append((nome.strip(), voto))
    senza_parentesi = re.sub(r"\([^)]*\)", " ", testo)
    # si separa sul punto e virgola e sulle virgole che dividono i giocatori,
    # MAI su quella dei mezzi voti: "Bijlow 6,5; Marcandalli 5,5" tagliato
    # anche sul decimale diventa "Bijlow 6" e perde mezzo voto a mezza rosa
    for pezzo in re.split(r";|,(?!\d)", senza_parentesi):
        m = re.match(r"^\s*([A-Za-zÀ-ÿ'’.\- ]+?)\s+(\d{1,2}(?:[,.]\d)?|sv)\s*\.?\s*$", pezzo)
        if m:
            fuori.append((m.group(1).strip(), m.group(2)))
    return fuori


def leggi_partita(blocco, squadre):
    """Un blocco '✅ CASA-OSPITE 1-2 CASA - ... OSPITE - ... Gol: ...' ->
    (squadre, voti grezzi per squadra, eventi per giocatore). Le squadre si
    riconoscono dal listone e non dal titolo, che abbrevia ("JUVE-MILAN" ma
    poi nel tabellino c'e' "JUVENTUS"): il 6 settembre la Juve spariva."""
    blocco = " ".join(ripulisci(blocco).split())
    intestazione = re.match(r"\s*([A-ZÀ-Ü' \.]+)-([A-ZÀ-Ü' \.]+?)\s+(\d+)-(\d+)\b", blocco)
    if not intestazione:
        return None
    casa, ospite = intestazione.group(1).strip(), intestazione.group(2).strip()
    corpo = blocco[intestazione.end():]
    # la coda con gol/assist/ammoniti sta dopo l'ultimo elenco di voti
    taglio = len(corpo)
    for e in EVENTI:
        p = corpo.find(f"{e}:")
        if p != -1:
            taglio = min(taglio, p)
    voti_testo, coda = corpo[:taglio], corpo[taglio:]
    alternanza = "|".join(sorted((re.escape(s) for s in squadre), key=len, reverse=True))
    parti = re.split(rf"\b({alternanza})\s*-\s+", voti_testo, flags=re.I)
    per_squadra = {}
    for i in range(1, len(parti) - 1, 2):
        per_squadra.setdefault(parti[i].strip(), "")
        per_squadra[parti[i].strip()] += " " + parti[i + 1]
    eventi = {}
    for e in EVENTI:
        m = re.search(rf"{e}:\s*(.*?)(?=\s+(?:{'|'.join(EVENTI)}):|$)", coda)
        if not m:
            continue
        for nome in m.group(1).split(","):
            nome = nome.strip(" .-")
            if nome and nome != "-":
                eventi.setdefault(norm(nome), []).append(e.lower())
    return (casa, ospite), per_squadra, eventi


def giornata_della_data(data):
    """La giornata a cui appartiene un articolo, dalla sua data (AAAA-MM-GG).
    None se cade fuori dal calendario noto: meglio fermarsi che sbagliare
    giornata, perche' un voto messo nella casella sbagliata falsa due medie."""
    scelta = None
    for numero, inizio in sorted(INIZIO_GIORNATA.items()):
        if data >= inizio:
            scelta = numero
    ultima = max(INIZIO_GIORNATA)
    if scelta == ultima and data >= INIZIO_GIORNATA[ultima]:
        # oltre l'ultima riga della tabella non sappiamo dove finisce
        fine = f"{INIZIO_GIORNATA[ultima][:8]}{int(INIZIO_GIORNATA[ultima][8:]) + 7:02d}"
        if data > fine:
            return None
    return scelta


def leggi_articolo(percorso, per_squadra_listone, esatti, data_cartella, squadre):
    testo = ripulisci(Path(percorso).read_text(encoding="utf-8"))
    m = re.search(r"^DATA:\s*(\d{4}-\d{2}-\d{2})", testo, re.M)
    giornata = giornata_della_data(m.group(1) if m else data_cartella)
    if not giornata:
        return None, []
    voti, mancati = [], []
    for blocco in testo.split("✅")[1:]:
        letto = leggi_partita(blocco, squadre)
        if not letto:
            continue
        _, per_squadra, eventi = letto
        for squadra, elenco in per_squadra.items():
            for grezzo, voto in pezzi_voto(elenco):
                if voto == "sv":
                    continue
                nome = trova_nome(grezzo, squadra, per_squadra_listone, esatti)
                if not nome:
                    mancati.append({"nome_articolo": grezzo, "squadra": squadra,
                                    "file": Path(percorso).name})
                    continue
                voce = {"nome": nome, "giornata": giornata,
                        "voto": float(voto.replace(",", ".")), "fantavoto": None}
                ev = eventi.get(norm(grezzo)) or eventi.get(norm(nome))
                if ev:
                    voce["eventi"] = ", ".join(sorted(set(ev)))
                voti.append(voce)
    return giornata, (voti, mancati)


def cartella(percorso, per_squadra, esatti, squadre, prova=False):
    percorso = Path(percorso)
    articoli = sorted(p for p in percorso.glob("*.txt") if "i-voti" in p.name)
    if not articoli:
        return 0, 0
    tutti, mancati = {}, []
    for a in articoli:
        giornata, esito = leggi_articolo(a, per_squadra, esatti, percorso.name, squadre)
        if not giornata:
            continue
        v, m = esito
        # lo stesso giocatore puo' comparire in due articoli dello stesso
        # giorno (il riassunto e il pezzo sulla singola partita): l'ultimo vince
        for voce in v:
            tutti[(voce["nome"], voce["giornata"])] = voce
        mancati += m
    if not tutti:
        return 0, 0
    dati = {"data": percorso.name, "fonte": "leghe", "note": [], "rigoristi": [],
            "voti": sorted(tutti.values(), key=lambda x: (x["giornata"], x["nome"])),
            "non_abbinati": mancati,
            "sintesi": f"Voti ufficiali di Leghe Fantacalcio dai tabellini di SOS Fanta del {percorso.name}."}
    if not prova:
        (percorso / "voti-leghe.json").write_text(
            json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(dati["voti"]), len(mancati)


def main():
    argomenti = [a for a in sys.argv[1:] if not a.startswith("--")]
    prova = "--prova" in sys.argv
    per_squadra, esatti, squadre = carica_listone()
    cartelle = [Path(a) for a in argomenti] or sorted(p for p in CARTELLE.iterdir() if p.is_dir())
    totale = 0
    for c in cartelle:
        voti, mancati = cartella(c, per_squadra, esatti, squadre, prova)
        if voti:
            totale += voti
            print(f"  {c.name}: {voti} voti" + (f", {mancati} non abbinati" if mancati else ""))
    print(f"{totale} voti di Leghe" + (" (prova, niente scritto)" if prova else
          "; ora: python3 motore/dossier.py importa <cartella>/voti-leghe.json"))


if __name__ == "__main__":
    main()
