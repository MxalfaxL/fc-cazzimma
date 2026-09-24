"""Chi parte titolare, giornata per giornata, dalle formazioni ufficiali.

Il dossier sa chi ha preso un voto, non chi e' partito dal primo minuto: un
attaccante con voto in 5 giornate su 5 puo' essere titolare fisso o entrare
sempre a mezz'ora dalla fine, e al fantacalcio sono due giocatori diversi (il
subentrato prende spesso 6 d'ufficio e segna meno). Le fonti le abbiamo gia'
nel feed di SOS Fanta (`dati/sosfanta/`):

- il **tabellino** di fine partita negli articoli "I voti di ...": undici
  titolari e cambi con il minuto ("Marcandalli 4,5 (82' Meichtry sv)"), da
  cui escono anche i MINUTI giocati di ognuno. E' la fonte principale;
- le **formazioni ufficiali** di un'ora prima del fischio: fanno da riserva
  dove il tabellino manca, e dove ci sono entrambi si controlla che dicano la
  stessa cosa.

I minuti sono un conto semplice: il titolare gioca fino al cambio o a 90, il
subentrato dal suo ingresso al cambio successivo o a 90. Recuperi ed
espulsioni non entrano: e' un ordine di grandezza, non un cronometro.

Come si abbina un nome della formazione ("A. Adams", "Hojlund", "Alisson")
a un giocatore senza tirare a indovinare: si cerca SOLO fra chi ha preso un
voto con quella squadra in quella giornata, nel file ufficiale. Sono 13-16
candidati per squadra, con il codice giocatore, quindi il cognome basta quasi
sempre; l'iniziale scioglie i pochi casi doppi. Quel che non si abbina lo
diciamo, non lo forziamo.

Uso:
    python3 motore/titolari.py        # scrive dati/titolari-2026-27.json e report/TITOLARI.md
"""

import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE / "motore"))
from squadre import leggi_giornata  # noqa: E402
from voti_leghe import giornata_della_data, leggi_partita, ripulisci  # noqa: E402
from voti_ufficiali import CARTELLA_FILE, giornata_dal_nome  # noqa: E402

FEED = RADICE / "dati" / "sosfanta"
LISTONE = RADICE / "report" / "listone.json"
USCITA_JSON = RADICE / "dati" / "titolari-2026-27.json"
USCITA_MD = RADICE / "report" / "TITOLARI.md"

SQUADRE = ["Atalanta", "Bologna", "Cagliari", "Como", "Fiorentina", "Frosinone", "Genoa", "Inter",
           "Juventus", "Lazio", "Lecce", "Milan", "Monza", "Napoli", "Parma", "Roma", "Sassuolo",
           "Torino", "Udinese", "Venezia"]
# come le scrivono in maiuscolo davanti alla formazione
SCRITTE = {s.upper(): s for s in SQUADRE} | {"JUVE": "Juventus"}

# Soprannomi e nomi di battesimo che nessuna regola sul cognome puo' sciogliere.
# Si aggiunge qui quando il resoconto li mette fra i "non riconosciuti".
SOPRANNOMI = {
    "lautaro": "martinez l", "pio": "esposito fp", "pio esposito": "esposito fp",
    "alisson": "santos a", "alisson santos": "santos a", "nico paz": "paz n",
}


def pulisci(t):
    t = t.replace("ø", "o").replace("Ø", "O").replace("æ", "ae").replace("ß", "ss").replace("ł", "l")
    t = unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z\- ]", " ", t).split()


def chiave_listone(nome):
    """'Adams A.' → ('adams', 'a'); 'Esposito F.P.' → ('esposito', 'fp');
    'Zambo Anguissa' → ('zambo anguissa', '')."""
    m = re.match(r"^(.*?)\s+((?:[A-Z][a-z]{0,2}\.)+)$", nome.strip())
    cognome, iniziali = (m.group(1), m.group(2)) if m else (nome, "")
    return " ".join(pulisci(cognome)), "".join(pulisci(iniziali))


def abbina(token, candidati, portiere=False):
    """Il candidato (riga del file ufficiale) che corrisponde al nome letto
    nella formazione, o None. Nessuna somiglianza vaga: cognome uguale, o
    cognome contenuto per intero (Anguissa in Zambo Anguissa).

    Il primo nome di una formazione e' sempre il portiere: cercarlo solo fra i
    portieri (e gli altri solo fra i non portieri) scioglie casi come
    "Martinez" dell'Inter, che e' Josep e non Lautaro."""
    parole = pulisci(token)
    if not parole:
        return None
    frase = " ".join(parole)
    frase = SOPRANNOMI.get(frase, frase)
    parole = frase.split()
    candidati = [c for c in candidati if (c["Ruolo"] == "P") == portiere]
    # iniziale davanti ("A. Adams") o dietro ("Adams A."): una parola di una lettera
    iniziali = "".join(p for p in parole if len(p) <= 2)
    resto = [p for p in parole if len(p) > 2]
    if not resto:
        return None

    def cerca(parole_cercate):
        compatte = "".join(parole_cercate).replace("-", "")
        trovati = []
        for c in candidati:
            cognome, ini = chiave_listone(c["Nome"])
            pezzi = cognome.split()
            if (" ".join(parole_cercate) == cognome or " ".join(parole_cercate[:len(pezzi)]) == cognome
                    or compatte == cognome.replace(" ", "").replace("-", "")      # Ndicka = N'Dicka
                    or (len(parole_cercate) == 1 and parole_cercate[0] in pezzi)):
                trovati.append((c, ini))
        if len(trovati) > 1 and iniziali:
            trovati = [(c, ini) for c, ini in trovati if ini.startswith(iniziali[0])] or trovati
        return trovati[0][0] if len(trovati) == 1 else None

    trovato = cerca(resto)
    if trovato or len(resto) == 1:
        return trovato
    # nome e cognome ("Nico Gonzalez", "Kike Perez"): una parola alla volta,
    # e vale solo se una sola parola porta a un solo giocatore
    singoli = {id(c): c for c in (cerca([p]) for p in resto) if c}
    return next(iter(singoli.values())) if len(singoli) == 1 else None


def segmenti(testo):
    """Le coppie (squadra, testo della formazione) di un articolo."""
    marcatori = list(re.finditer(r"\b(" + "|".join(SCRITTE) + r")\s*[-–:]\s*", testo))
    for i, m in enumerate(marcatori):
        fine = marcatori[i + 1].start() if i + 1 < len(marcatori) else m.end() + 500
        pezzo = testo[m.end():fine]
        # una formazione vera ha almeno un punto e virgola nei primi caratteri
        if ";" not in pezzo[:60]:
            continue
        yield SCRITTE[m.group(1)], pezzo


def undici(pezzo):
    nomi = [n.strip() for n in re.split(r"[;,]", pezzo)]
    nomi = [n for n in nomi if n][:11]
    if nomi:
        # l'ultimo si porta dietro il resto della frase: si taglia al primo punto
        # che non chiude un'iniziale
        nomi[-1] = re.split(r"(?<![A-Z])\.\s", nomi[-1] + " ")[0].strip()
    return nomi


def pezzi_di_primo_livello(testo):
    """Separa i giocatori sul punto e virgola e sulle virgole fra giocatori,
    ma mai dentro le parentesi dei cambi e mai sul decimale ("5,5")."""
    pezzi, livello, corrente = [], 0, ""
    for i, ch in enumerate(testo):
        if ch == "(":
            livello += 1
        elif ch == ")":
            livello -= 1
        if livello == 0 and (ch == ";" or (ch == "," and not testo[i + 1:i + 2].isdigit())):
            pezzi.append(corrente)
            corrente = ""
        else:
            corrente += ch
    pezzi.append(corrente)
    return [p.strip() for p in pezzi if p.strip()]


NOME_VOTO = re.compile(r"^\s*(.+?)\s+(\d{1,2}(?:[,.]\d)?|sv)\s*\.?\s*$")


def catena(pezzo):
    """'Bellanova 5,5 (75' Cambiaso sv (86' Koopmeiners 7))' →
    [('Bellanova', None), ('Cambiaso', 75), ('Koopmeiners', 86)]: il titolare
    e chi gli e' subentrato dopo, in ordine, col minuto d'ingresso."""
    titolare = pezzo.split("(")[0]
    m = NOME_VOTO.match(titolare)
    if not m:
        return []
    uscita = [(m.group(1).strip(), None)]
    for minuto, nome_voto in re.findall(r"\((\d+)'\s*([^()]+)", pezzo):
        mm = NOME_VOTO.match(nome_voto.strip().rstrip(";"))
        if mm:
            uscita.append((mm.group(1).strip(), int(minuto)))
    return uscita


def leggi_tabellini(in_campo, giornate):
    """(giornata, squadra) → {titolari: [codici], minuti: {codice: minuti}},
    dai tabellini degli articoli dei voti. Piu' i nomi non abbinati."""
    partite, non_riconosciuti = {}, []
    articoli = sorted(p for p in FEED.glob("*/*.txt") if "i-voti" in p.name)
    for p in articoli:
        testo = ripulisci(p.read_text(encoding="utf-8"))
        m = re.search(r"^DATA:\s*(\d{4}-\d{2}-\d{2})", testo, re.M)
        g = giornata_della_data(m.group(1) if m else p.parent.name)
        if g not in giornate:
            continue
        for blocco in testo.split("✅")[1:]:
            letto = leggi_partita(blocco, SQUADRE + ["Juve"])
            if not letto:
                continue
            _, per_squadra, _ = letto
            for scritta, elenco in per_squadra.items():
                squadra = SCRITTE.get(scritta.strip().upper())
                candidati = in_campo.get((g, squadra), [])
                if not squadra or not candidati or (g, squadra) in partite:
                    continue
                titolari, minuti, mancano = [], {}, []
                for i, pezzo in enumerate(pezzi_di_primo_livello(elenco)):
                    giro = catena(pezzo)
                    for j, (nome, entrato) in enumerate(giro):
                        uscito = giro[j + 1][1] if j + 1 < len(giro) else None
                        c = abbina(nome, candidati, portiere=(i == 0 and j == 0)) \
                            or (j and abbina(nome, candidati, portiere=True))
                        if not c:
                            mancano.append(nome)
                            non_riconosciuti.append({"giornata": g, "squadra": squadra, "nome": nome,
                                                     "file": p.name, "fonte": "tabellino"})
                            continue
                        if j == 0:
                            titolari.append(c["Cod."])
                        minuti[c["Cod."]] = max(0, min(90, (uscito or 90) - (entrato or 0)))
                if len(titolari) + sum(1 for n in mancano) >= 11:
                    partite[(g, squadra)] = {"titolari": titolari, "minuti": minuti,
                                             "non_riconosciuti": mancano, "file": p.name, "fonte": "tabellino"}
    return partite, non_riconosciuti


def partita_del_titolo(testo):
    """Le due squadre di campionato dal titolo ("Juve-Parma, formazioni
    ufficiali..."), o None. Serve a scartare Champions, Europa e Conference
    League e Coppa Italia, che cadono nelle stesse settimane delle giornate: la
    formazione di Juventus-Nec presa per quella di campionato falserebbe la 5ª."""
    m = re.search(r"^TITOLO:\s*([^,:\n]+?)\s*-\s*([^,:\n]+?)\s*[,:]", testo, re.M)
    if not m:
        return None
    casa, fuori = (SCRITTE.get(x.strip().upper()) for x in m.groups())
    return (casa, fuori) if casa and fuori else None


def leggi_formazioni(in_campo, giornate):
    """(giornata, squadra) → undici dalle formazioni ufficiali pre-partita."""
    formazioni, non_riconosciuti = {}, []
    articoli = [p for p in sorted(FEED.glob("*/*.txt"))
                if re.search(r"^TITOLO:.*formazion[ei] ufficial", p.read_text(encoding="utf-8")[:400], re.I | re.M)]
    for p in articoli:
        testo = p.read_text(encoding="utf-8")
        m = re.search(r"^DATA:\s*(\d{4}-\d{2}-\d{2})", testo, re.M)
        g = giornata_della_data(m.group(1)) if m else None
        partita = partita_del_titolo(testo)
        if g not in giornate or not partita:
            continue                      # coppe e amichevoli: non sono campionato
        corpo = " ".join(testo.split("\n")[5:])
        for squadra, pezzo in segmenti(corpo):
            candidati = in_campo.get((g, squadra), [])
            if squadra not in partita or (g, squadra) in formazioni or not candidati:
                continue
            nomi = undici(pezzo)
            if len(nomi) < 11:
                continue
            titolari, mancano = [], []
            for i, n in enumerate(nomi):
                c = abbina(n, candidati, portiere=(i == 0))
                if c:
                    titolari.append(c["Cod."])
                else:
                    mancano.append(n)
                    non_riconosciuti.append({"giornata": g, "squadra": squadra, "nome": n,
                                             "file": p.name, "fonte": "formazione"})
            formazioni[(g, squadra)] = {"titolari": titolari, "non_riconosciuti": mancano,
                                        "file": p.name, "fonte": "formazione"}
    return formazioni, non_riconosciuti


def main():
    per_giornata = {}
    for f in sorted(CARTELLA_FILE.glob("*.xlsx")):
        g = giornata_dal_nome(f)
        if g:
            per_giornata[g] = leggi_giornata(f)
    in_campo = defaultdict(list)          # (giornata, squadra) → righe del file ufficiale
    for g, righe in per_giornata.items():
        for r in righe:
            in_campo[(g, r["squadra"])].append(r)

    tabellini, nr_tab = leggi_tabellini(in_campo, per_giornata)
    formazioni, nr_form = leggi_formazioni(in_campo, per_giornata)
    # dove ci sono entrambe le fonti, dicono gli stessi undici?
    diversi = []
    for chiave, tab in tabellini.items():
        form = formazioni.get(chiave)
        if form and not tab["non_riconosciuti"] and not form["non_riconosciuti"] \
                and set(tab["titolari"]) != set(form["titolari"]):
            diversi.append({"giornata": chiave[0], "squadra": chiave[1],
                            "solo_tabellino": sorted(set(tab["titolari"]) - set(form["titolari"])),
                            "solo_formazione": sorted(set(form["titolari"]) - set(tab["titolari"]))})
    partite = {**formazioni, **tabellini}          # il tabellino, se c'e', vince
    non_riconosciuti = [x for x in nr_tab] + [x for x in nr_form if (x["giornata"], x["squadra"]) not in tabellini]

    nomi_listone = {}
    if LISTONE.exists():
        nomi_listone = {x["id"]: x for x in json.load(open(LISTONE, encoding="utf-8"))["listone"] if "id" in x}
    giocatori = {}
    for (g, squadra), righe in in_campo.items():
        f = partite.get((g, squadra))
        for r in righe:
            v = giocatori.setdefault(r["Cod."], {"codice": r["Cod."], "nome": r["Nome"], "ruolo": r["Ruolo"],
                                                "squadra": squadra, "titolare": [], "entrato": [], "ignoto": [],
                                                "minuti": {}})
            v["squadra"] = squadra
            if f is None:
                v["ignoto"].append(g)
            elif r["Cod."] in f["titolari"]:
                v["titolare"].append(g)
            elif f["non_riconosciuti"]:
                v["ignoto"].append(g)     # potrebbe essere lui il nome non abbinato
            else:
                v["entrato"].append(g)
            if f and "minuti" in f and r["Cod."] in f["minuti"]:
                v["minuti"][g] = f["minuti"][r["Cod."]]
    for v in giocatori.values():
        v["minuti_totali"] = sum(v["minuti"].values())

    mancanti = sorted((g, s) for g in per_giornata for s in SQUADRE if (g, s) not in partite)
    senza_minuti = sorted((g, s) for g in per_giornata for s in SQUADRE if (g, s) not in tabellini)
    USCITA_JSON.write_text(json.dumps({
        "giornate": sorted(per_giornata),
        "partite": {f"{g}|{s}": v for (g, s), v in sorted(partite.items())},
        "mancanti": [{"giornata": g, "squadra": s} for g, s in mancanti],
        "senza_minuti": [{"giornata": g, "squadra": s} for g, s in senza_minuti],
        "tabellino_e_formazione_diversi": diversi,
        "non_riconosciuti": non_riconosciuti,
        "giocatori": sorted(giocatori.values(), key=lambda v: (v["squadra"], v["ruolo"], v["nome"])),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    G = len(per_giornata)
    righe = ["# Titolari, subentrati e minuti — tabellini e formazioni ufficiali (SOS Fanta) + voti ufficiali", "",
             f"Partite coperte: **{len(partite)}** su {G * 20} (squadra per giornata): {len(tabellini)} dal "
             f"tabellino, con i minuti, {len(partite) - len(tabellini)} dalla sola formazione ufficiale.",
             f"Dove ci sono entrambe le fonti, undici diversi in {len(diversi)} casi. Nomi non riconosciuti: "
             f"{len(non_riconosciuti)}.", "",
             "T = titolare, E = entrato, ? = ignoto. Minuti: il titolare fino al cambio o a 90, il subentrato",
             "dall'ingresso; recuperi ed espulsioni non contati.", ""]
    if mancanti:
        righe += ["**Partite mancanti**: " + ", ".join(f"{s} ({g}ª)" for g, s in mancanti), ""]
    if senza_minuti:
        righe += ["**Senza minuti** (manca il tabellino): " + ", ".join(f"{s} ({g}ª)" for g, s in senza_minuti), ""]
    if non_riconosciuti:
        righe += ["**Nomi non riconosciuti**: " +
                  ", ".join(f"{x['nome']} ({x['squadra']}, {x['giornata']}ª, {x['fonte']})" for x in non_riconosciuti), ""]
    for ruolo, titolo in (("P", "Portieri"), ("D", "Difensori"), ("C", "Centrocampisti"), ("A", "Attaccanti")):
        righe += [f"## {titolo} del listone da piu' di 10 crediti", "",
                  f"| Giocatore | Squadra | Prezzo | Titolare | Entrato | Minuti su {G * 90} | Giornate |",
                  "|---|---|---|---|---|---|---|"]
        scelti = [v for v in giocatori.values() if v["ruolo"] == ruolo and v["codice"] in nomi_listone
                  and nomi_listone[v["codice"]].get("pr", 0) > 10]
        for v in sorted(scelti, key=lambda v: -nomi_listone[v["codice"]]["pr"]):
            prezzo = round(nomi_listone[v["codice"]]["pr"])
            dettaglio = " ".join(
                f"{g}{'T' if g in v['titolare'] else 'E' if g in v['entrato'] else '?'}"
                + (f"{v['minuti'][g]}'" if g in v["minuti"] else "")
                for g in sorted(v["titolare"] + v["entrato"] + v["ignoto"]))
            righe.append(f"| {nomi_listone[v['codice']]['n']} | {v['squadra']} | {prezzo} | {len(v['titolare'])} | "
                         f"{len(v['entrato'])} | {v['minuti_totali']} | {dettaglio} |")
        righe.append("")
    USCITA_MD.write_text("\n".join(righe) + "\n", encoding="utf-8")

    print(f"{len(partite)} partite su {G * 20} ({len(tabellini)} con i minuti dal tabellino), "
          f"{len(diversi)} undici diversi fra le due fonti, {len(non_riconosciuti)} nomi non riconosciuti "
          f"→ {USCITA_JSON.relative_to(RADICE)}, {USCITA_MD.relative_to(RADICE)}")
    if mancanti:
        print("  mancano: " + ", ".join(f"{s} {g}ª" for g, s in mancanti))
    if senza_minuti:
        print("  senza minuti: " + ", ".join(f"{s} {g}ª" for g, s in senza_minuti))
    for d in diversi[:10]:
        print(f"  diversi {d['squadra']} {d['giornata']}ª: solo tabellino {d['solo_tabellino']}, "
              f"solo formazione {d['solo_formazione']}")
    for x in non_riconosciuti[:30]:
        print(f"  non riconosciuto: {x['nome']!r} ({x['squadra']}, {x['giornata']}ª, {x['fonte']})")


if __name__ == "__main__":
    main()
