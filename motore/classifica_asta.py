"""La classifica per l'asta: quanto vale ogni giocatore, per ruolo, alla luce
del dossier.

Il listone dice cosa il mercato si aspetta ad agosto. Il dossier dice cosa e'
successo da allora: chi gioca, chi e' rotto, che voti prende, chi tira i
rigori. Qui i due si incontrano in un numero solo, i **fantapunti attesi a
giornata**, costruito in tre pezzi che si possono spiegare a voce:

1. **Voto atteso**: parte dall'aspettativa del listone (chi costa di piu' nel
   suo ruolo e' atteso piu' in alto) e si sposta verso la media Gazzetta man
   mano che i voti si accumulano. Con 3 voti la Gazzetta pesa gia' il 60%.
2. **Bonus attesi**: gol e assist visti nelle pagelle, piu' un'aspettativa di
   ruolo e prezzo per chi non ha ancora segnato; il rigorista prende un extra.
3. **Disponibilita'**: quante volte e' finito in pagella rispetto alle giornate
   giocate (in pagella ci vai se giochi), corretta se l'ultima notizia lo da'
   infortunato: stop lungo (mesi) quasi zero, medio (settimane) meta',
   altrimenti tre quarti.

atteso = disponibilita' x (voto atteso + bonus attesi)

Il **verdetto** confronta la posizione per atteso con la posizione per prezzo
dentro il ruolo: chi sta molto piu' in alto per atteso che per prezzo e' un
affare (▲), chi sta molto piu' in basso e' da lasciare ad altri (▼).

I voti sono quelli della Gazzetta, non quelli della lega: un termometro,
non la verita'. Ogni numero e' accompagnato dal suo perche' in parole.

Uso:
    python3 motore/classifica_asta.py          # scrive report/CLASSIFICA.md e aggiorna report/dossier-app.json
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from regole import SLOT, SQUADRE_PER_LEGA
import dossier as modulo_dossier

USCITA_MD = RADICE / "report" / "CLASSIFICA.md"
USCITA_APP = RADICE / "report" / "dossier-app.json"

NOME_RUOLO = {"P": "Portieri", "D": "Difensori", "C": "Centrocampisti", "A": "Attaccanti"}
# quanti ne compra il mercato: dentro questi il listone ha un prezzo vero
COMPRATI = {r: SLOT[r] * SQUADRE_PER_LEGA for r in SLOT}

# Voto atteso a priori: dal peggiore al migliore del ruolo (per prezzo).
VOTO_PRIORI = {"P": (5.7, 6.4), "D": (5.8, 6.4), "C": (5.8, 6.5), "A": (5.7, 6.5)}
# Bonus a priori per giornata, dal peggiore al migliore del ruolo. I portieri
# hanno il malus dei gol subiti, che qui vale come bonus negativo medio.
BONUS_PRIORI = {"P": (-1.4, -0.8), "D": (0.0, 0.5), "C": (0.1, 1.0), "A": (0.3, 1.7)}
# Disponibilita' a priori: chi costa e' titolare, chi vale 1 e' una scommessa.
DISP_PRIORI = (0.35, 0.9)
# Il rigorista designato vale circa un rigore ogni 4 giornate: +3 x 0.25
EXTRA_RIGORISTA = 0.6
# Quanto pesa la Gazzetta contro il listone: n / (n + PESO_PRIORI). I bonus
# sono piu' rumorosi dei voti (un gol in tre partite non fa una stagione),
# quindi il loro prior pesa di piu'.
PESO_PRIORI = 2.0
PESO_PRIORI_BONUS = 4.0
# Soglie del verdetto: quante posizioni di differenza, in frazione del ruolo
SOGLIA_VERDETTO = 0.12

STOP_LUNGO = re.compile(r"(\d+\s*mesi|due mesi|tre mesi|quattro mesi|fine novembre|dicembre|gennaio|2027|crociato|operat|frattur|stagione finita)", re.I)
STOP_MEDIO = re.compile(r"(un mese|mese|\d+\s*settimane|40 giorni|30 giorni|50 giorni|lesione)", re.I)


def percentile_per_prezzo(voci):
    """0 per il piu' economico del ruolo, 1 per il piu' caro, fra i comprati.
    Chi e' fuori dai comprati (vale 1) sta a zero."""
    out = {}
    for r in SLOT:
        gruppo = sorted([g for g in voci if g["r"] == r], key=lambda g: -g["pr"])
        n = min(len(gruppo), COMPRATI[r])
        for i, g in enumerate(gruppo):
            out[g["n"]] = max(0.0, 1 - i / max(1, n - 1)) if i < n else 0.0
    return out


def interpola(coppia, p):
    return coppia[0] + (coppia[1] - coppia[0]) * p


# Quanti voti servono, per una squadra in una giornata, per dire che di quella
# giornata sappiamo chi ha giocato. In una pagella ci sono 11-14 nomi: sotto
# questa soglia abbiamo solo briciole e non possiamo dedurre le assenze.
COPERTURA_MINIMA = 8


def giornate_per_squadra(dossier, listone_per_nome):
    """Per ogni squadra due insiemi di giornate:

    - **giocate**: tutte quelle che ha davvero disputato. Il campionato non
      salta giornate, quindi se un suo giocatore ha un voto alla 3ª allora la
      1ª e la 2ª le ha giocate per forza, anche se in archivio non abbiamo
      quelle pagelle. E' il denominatore del "3/4" che si legge nell'app.
    - **coperte**: quelle di cui abbiamo abbastanza voti da sapere chi era in
      campo. Solo su queste si puo' stimare la disponibilita': dove le pagelle
      mancano, un giocatore non risulta assente, risulta ignoto.

    Prima contavo solo le giornate con voti: della 1ª giornata abbiamo le
    pagelle di una partita sola, e quindici squadre su venti risultavano ferme
    a due giornate invece di tre."""
    conteggio = {}
    for nome, v in dossier["giocatori"].items():
        squadra = listone_per_nome.get(nome, {}).get("sq")
        if not squadra:
            continue
        for x in v["voti"]:
            conteggio[(squadra, x["g"])] = conteggio.get((squadra, x["g"]), 0) + 1
    per_squadra = {}
    for (squadra, g), quanti in conteggio.items():
        voce = per_squadra.setdefault(squadra, {"massima": 0, "coperte": set()})
        voce["massima"] = max(voce["massima"], g)
        if quanti >= COPERTURA_MINIMA:
            voce["coperte"].add(g)
    for squadra, voce in per_squadra.items():
        voce["giocate"] = set(range(1, voce["massima"] + 1))
    return per_squadra


def giornate_giocate(dossier, listone_per_nome=None):
    """Le giornate della squadra piu' avanti: serve per il titolo del
    rapporto. Il conto che vale e' quello per squadra."""
    if listone_per_nome:
        per_squadra = giornate_per_squadra(dossier, listone_per_nome)
        return max((v["massima"] for v in per_squadra.values()), default=0)
    return max((x["g"] for v in dossier["giocatori"].values() for x in v["voti"]), default=0)


def bonus_da_eventi(voti, ruolo):
    """Gol, assist, ammonizioni, espulsioni, rigori e gol subiti letti dagli
    eventi delle pagelle: un conteggio prudente, quello che il testo dice
    chiaro. Per i portieri i gol sono quelli subiti, mai quelli fatti."""
    tot = 0.0
    for x in voti:
        ev = (x.get("ev") or "").lower()
        if not ev:
            continue
        # prima i gol subiti, cosi' "3 gol subiti" non diventa una tripletta
        m = re.search(r"(\d+)\s*gol subit", ev)
        subiti = int(m.group(1)) if m else 0
        # via anche i gol degli altri ("assist per il gol di Malen") e quelli non validi
        ev_pulito = re.sub(r"\d+\s*gol subit\w*|gol subit\w*|gol annullat\w*|gol sbagliat\w*|gol mangiat\w*|gol divorat\w*|(per|sul|del|il)\s+gol\s+d\w*\s+\S+|gol\s+d[ie]\s+[A-Z]\S*", " ", ev, flags=re.I)
        if ruolo == "P":
            tot -= subiti
            if "rigore parato" in ev or "para un rigore" in ev or "para il rigore" in ev: tot += 3
        else:
            m = re.search(r"(\d+)\s*gol", ev_pulito)
            gol = int(m.group(1)) if m else (1 if re.search(r"\bgol\b|\brete\b|doppietta|tripletta", ev_pulito) else 0)
            if "doppietta" in ev_pulito: gol = max(gol, 2)
            if "tripletta" in ev_pulito: gol = max(gol, 3)
            if "autogol" in ev or "autorete" in ev: gol = max(0, gol - 1); tot -= 2
            m = re.search(r"(\d+)\s*assist", ev)
            assist = int(m.group(1)) if m else (1 if "assist" in ev else 0)
            tot += 3 * gol + assist
            if "rigore sbagliato" in ev or "rigore fallito" in ev or ("sbaglia" in ev and "rigor" in ev): tot -= 3
        if "ammonit" in ev or "giallo" in ev: tot -= 0.5
        if "espuls" in ev or "rosso" in ev: tot -= 1
    return tot


def stop_infortunio(voce):
    """Quanto dura lo stop, letto dall'ultima nota di infortunio: lungo, medio
    o breve. Restituisce (fattore, parola)."""
    note = [n for n in voce["note"] if n["tipo"] == "infortunio"]
    if not note:
        return 0.75, "stop non quantificato"
    # tutte le note di infortunio recenti, perche' l'ultima e' spesso generica
    # ("indisponibile") e la diagnosi sta in quella prima
    recenti = sorted(note, key=lambda n: n["data"], reverse=True)[:3]
    testo = " ".join(n["testo"] for n in recenti)
    if STOP_LUNGO.search(testo):
        return 0.1, "stop lungo"
    if STOP_MEDIO.search(testo):
        return 0.5, "stop di settimane"
    return 0.75, "stop breve o da valutare"


def valuta(g, voce, pct, squadra):
    """Il numero e il suo perche', per un giocatore."""
    r = g["r"]
    perche = []
    voti = voce["voti"] if voce else []
    n = len(voti)
    voto_priori = interpola(VOTO_PRIORI[r], pct)
    bonus_priori = interpola(BONUS_PRIORI[r], pct)
    disp_priori = interpola(DISP_PRIORI, pct)

    if n:
        media = sum(x["v"] for x in voti) / n
        peso = n / (n + PESO_PRIORI)
        voto = voto_priori * (1 - peso) + media * peso
        bonus_visti = bonus_da_eventi(voti, r) / n
        peso_b = n / (n + PESO_PRIORI_BONUS)
        bonus = bonus_priori * (1 - peso_b) + bonus_visti * peso_b
        perche.append(f"{n} vot{'o' if n == 1 else 'i'} Gazzetta, media {media:.2f}")
        if abs(bonus_visti) > 0.4:
            perche.append(f"bonus visti {bonus_visti:+.1f} a partita")
    else:
        voto, bonus = voto_priori, bonus_priori
        perche.append("mai in pagella finora" if squadra else "nessun voto ancora")

    # Due conti diversi, e la differenza conta:
    # - giocate: le giornate che la sua squadra ha disputato (il "3/4" da mostrare)
    # - coperte: quelle di cui abbiamo le pagelle, le uniche su cui si puo'
    #   stimare quanto gioca. Dove le pagelle mancano non e' assente: e' ignoto.
    giocate = squadra.get("giocate", set()) if squadra else set()
    coperte = squadra.get("coperte", set()) if squadra else set()
    G = len(giocate)
    pres = len({x["g"] for x in voti if x["g"] in giocate}) if G else 0
    pres_note = len({x["g"] for x in voti if x["g"] in coperte})
    C = len(coperte)
    if C:
        disp_viste = pres_note / C
        peso_d = C / (C + 2)
        disp = disp_priori * (1 - peso_d) + disp_viste * peso_d
        if pres == G:
            perche.append(f"sempre in campo ({pres}/{G})")
        elif pres_note == 0:
            perche.append(f"mai in campo ({pres}/{G})")
        else:
            perche.append(f"in campo {pres}/{G}")
        if C < G:
            mancanti = sorted(giocate - coperte)
            perche.append("di " + ("una giornata" if len(mancanti) == 1 else f"{len(mancanti)} giornate")
                          + f" (la {', la '.join(str(x) for x in mancanti)}ª) non abbiamo le pagelle")
    else:
        disp = disp_priori

    if voce:
        if voce["rigorista"] == "si":
            bonus += EXTRA_RIGORISTA
            perche.append("rigorista")
        elif voce["rigorista"] == "dubbio":
            bonus += EXTRA_RIGORISTA / 2
            perche.append("rigorista in dubbio")
        if voce["stato"] == "infortunato":
            fattore, parola = stop_infortunio(voce)
            disp *= fattore
            perche.append(f"INFORTUNATO, {parola}")
        elif voce["stato"] == "squalificato":
            disp *= 0.85
            perche.append("squalificato")
        # l'ultima parola sulle gerarchie, se e' fresca
        gerarchie = [x for x in voce["note"] if x["tipo"] in ("titolare", "panchina")]
        if gerarchie:
            u = max(gerarchie, key=lambda x: x["data"])
            if u["tipo"] == "panchina":
                disp *= 0.85
                perche.append(f"panchina secondo il {u['data'][8:]}/{u['data'][5:7]}")
            else:
                disp = min(1.0, disp * 1.05)

    atteso = disp * (voto + bonus)
    return {
        "atteso": round(atteso, 2), "voto": round(voto, 2), "bonus": round(bonus, 2),
        "disp": round(disp, 2), "perche": perche,
        # presenze su giornate giocate dalla squadra: il "3/4" che Marco vuole vedere
        "pres": pres, "gs": G, "cop": C,
    }


def classifica(listone, dossier):
    voci = listone["listone"]
    pct = percentile_per_prezzo(voci)
    per_nome = {g["n"]: g for g in voci}
    per_squadra = giornate_per_squadra(dossier, per_nome)
    G = giornate_giocate(dossier, per_nome)
    righe = []
    for g in voci:
        voce = dossier["giocatori"].get(g["n"])
        v = valuta(g, voce, pct[g["n"]], per_squadra.get(g["sq"]))
        v.update({"n": g["n"], "sq": g["sq"], "r": g["r"], "pr": g["pr"], "qt": g["qt"],
                  "tt": g["tt"].get("equilibrio", next(iter(g["tt"].values()))) if isinstance(g["tt"], dict) else g["tt"]})
        righe.append(v)
    # verdetto: posizione per atteso contro posizione per prezzo, nel ruolo
    for r in SLOT:
        gruppo = [x for x in righe if x["r"] == r]
        per_prezzo = {x["n"]: i for i, x in enumerate(sorted(gruppo, key=lambda x: -x["pr"]))}
        per_atteso = {x["n"]: i for i, x in enumerate(sorted(gruppo, key=lambda x: -x["atteso"]))}
        soglia = max(3, int(len(gruppo) * SOGLIA_VERDETTO))
        for x in gruppo:
            x["pos_prezzo"] = per_prezzo[x["n"]] + 1
            x["pos_atteso"] = per_atteso[x["n"]] + 1
            delta = per_prezzo[x["n"]] - per_atteso[x["n"]]
            # fuori dai comprati il prezzo e' 1 per tutti: il confronto non dice niente
            if x["pos_prezzo"] > COMPRATI[r] and x["pos_atteso"] > COMPRATI[r]:
                x["verdetto"] = ""
            elif delta >= soglia:
                x["verdetto"] = "su"
            elif delta <= -soglia:
                x["verdetto"] = "giu"
            else:
                x["verdetto"] = ""
    return righe, G


def scrivi_md(righe, G, quanti=45):
    out = [f"# Classifica per l'asta — {date.today().strftime('%d/%m/%Y')}", "",
           f"Fantapunti attesi a giornata, con fino a {G} giornate di voti Gazzetta nel dossier "
           "(la disponibilita' di ognuno e' contata sulle giornate che la SUA squadra ha giocato). "
           "atteso = disponibilità × (voto atteso + bonus attesi). ▲ vale più di quanto costa, ▼ meno. "
           "Tetto: piano equilibrio. Privato: non va su GitHub.", ""]
    for r in SLOT:
        gruppo = sorted([x for x in righe if x["r"] == r], key=lambda x: -x["atteso"])[:quanti]
        out += [f"## {NOME_RUOLO[r]}", "", "| # | | giocatore | squadra | mercato | tetto | atteso | pres | voto | bonus | disp | perché |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for i, x in enumerate(gruppo, 1):
            v = {"su": "▲", "giu": "▼"}.get(x["verdetto"], "")
            out.append(f"| {i} | {v} | **{x['n']}** | {x['sq']} | {x['pr']:.0f} | {x['tt']} | **{x['atteso']:.2f}** | {x['pres']}/{x['gs']} | {x['voto']:.2f} | {x['bonus']:+.2f} | {x['disp']:.2f} | {'; '.join(x['perche'])} |")
        out.append("")
        affari = [x for x in sorted([x for x in righe if x["r"] == r], key=lambda x: -x["atteso"]) if x["verdetto"] == "su"][:8]
        trappole = [x for x in sorted([x for x in righe if x["r"] == r], key=lambda x: -x["pr"]) if x["verdetto"] == "giu"][:8]
        if affari:
            out.append("**Affari** (valgono più di quanto costano): " + ", ".join(f"{x['n']} ({x['pr']:.0f} → atteso {x['atteso']:.2f})" for x in affari))
        if trappole:
            out.append("**Da lasciare agli altri** (costano più di quanto valgono ora): " + ", ".join(f"{x['n']} ({x['pr']:.0f}, {x['perche'][-1] if x['perche'] else ''})" for x in trappole))
        out.append("")
    USCITA_MD.write_text("\n".join(out), encoding="utf-8")


def aggiorna_app(righe, dossier, listone_per_nome):
    """Aggiunge a report/dossier-app.json il consiglio per ogni giocatore
    comprabile: atteso, verdetto e perche'. Chi non ha note ne' voti entra con
    il solo consiglio."""
    blocco = modulo_dossier.esporta(dossier, listone_per_nome)
    giocatori = blocco["giocatori"]
    for x in righe:
        if x["pos_prezzo"] > COMPRATI[x["r"]] and x["n"] not in giocatori:
            continue
        voce = giocatori.setdefault(x["n"], {"st": "ok", "v": [], "n": []})
        voce["c"] = {"at": x["atteso"], "ve": x["verdetto"], "mo": "; ".join(x["perche"]),
                     "pr": x["pres"], "gs": x["gs"], "co": x["cop"]}
    blocco["giornate"] = giornate_giocate(dossier, listone_per_nome)
    USCITA_APP.write_text(json.dumps(blocco, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return blocco


def genera():
    """Classifica, file privato e blocco per l'app in un colpo: e' quello che
    chiama anche invia_listone.py, cosi' il consiglio parte sempre aggiornato."""
    listone = json.loads((RADICE / "report" / "listone.json").read_text(encoding="utf-8"))
    dossier = modulo_dossier.carica()
    if not dossier["giocatori"]:
        sys.exit("Il dossier e' vuoto: prima leggi qualche giornale (leggi_gazzetta.py, dossier.py importa).")
    righe, G = classifica(listone, dossier)
    scrivi_md(righe, G)
    blocco = aggiorna_app(righe, dossier, {g["n"]: g for g in listone["listone"]})
    return righe, G, blocco


def main():
    righe, G, blocco = genera()
    print(f"{len(righe)} giocatori valutati con {G} giornate di voti → {USCITA_MD.relative_to(RADICE)}, consiglio per {sum(1 for v in blocco['giocatori'].values() if 'c' in v)} nell'app")
    for r in SLOT:
        top = sorted([x for x in righe if x["r"] == r], key=lambda x: -x["atteso"])[:8]
        print(f"  {r}: " + ", ".join(f"{x['n']} {x['atteso']:.2f}{'▲' if x['verdetto']=='su' else '▼' if x['verdetto']=='giu' else ''}" for x in top))


if __name__ == "__main__":
    main()
