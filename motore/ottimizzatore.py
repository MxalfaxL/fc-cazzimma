"""Sceglie la formazione migliore fra i sette moduli ammessi.

La parte che nessun consigliere generico fa: il modificatore difesa cambia
la convenienza dei moduli. Un difensore da voto puro alto ma senza bonus
puo' valere piu' di uno che segna, perche' alza la media del modificatore.
Per questo i difensori non si scelgono per fantavoto atteso, ma provando
tutte le combinazioni e tenendo quella che massimizza il totale.

La seconda cosa che i consiglieri non fanno: dire quanto costa sbagliare.
Un titolare in dubbio non vale zero se non gioca, vale quanto il primo
della sua panchina che scende in campo. Per ogni dubbio schierato il motore
calcola di quanto scende il punteggio se il ballottaggio va male,
modificatore compreso. "Se perde ti costa 0,4" si schiera tranquillo,
"ti costa 3,1" e' la scelta della giornata.

Questo file e la testa dello <script> in index.html sono lo stesso
algoritmo in due lingue: motore/verifica_parita.py controlla che diano
gli stessi numeri sugli stessi dati.

Uso:
    python3 motore/ottimizzatore.py            # gira sull'esempio incluso
    python3 motore/ottimizzatore.py dati/rosa.json
"""

import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regole import MODULI, modificatore_difesa, gol_da_punti, punti_per_gol_successivo

PROB_BALLOTTAGGIO = 0.5   # quando delle probabili sappiamo solo "in dubbio"
RUOLI = ("P", "D", "C", "A")


class Giocatore:
    """fv   = fantavoto atteso, bonus e malus compresi
       voto = voto puro atteso, quello che conta per il modificatore
       p    = probabilita' di scendere in campo (0-1)

    Accetta anche la forma dell'app: st in T/B/F piu' pb, la percentuale
    del ballottaggio quando la conosciamo."""

    def __init__(self, nome, ruolo, fv, voto=None, p=None, st=None, pb=None,
                 squadra="", nota="", **_ignora):
        self.nome, self.ruolo = nome, ruolo.upper()
        self.fv = float(fv)
        self.voto = float(voto if voto is not None else fv)
        self.squadra, self.nota = squadra, nota
        if p is None:
            p = probabilita_da_stato(st, pb)
        self.p = float(p)

    def __repr__(self):
        return f"{self.nome} ({self.ruolo}) fv {self.fv:.2f} voto {self.voto:.2f} p {self.p:.0%}"


def probabilita_da_stato(st, pb=None):
    if st == "F":
        return 0.0
    if st == "B":
        try:
            pb = float(pb)
        except (TypeError, ValueError):
            pb = None
        return pb if pb is not None and 0 < pb < 1 else PROB_BALLOTTAGGIO
    return 1.0


def ordina(giocatori):
    """Ordine di panchina dentro un ruolo: per fantavoto. Entra il primo che
    ha giocato, quindi mettere davanti il migliore non costa nulla anche se
    e' in dubbio: se non gioca, si passa al successivo."""
    return sorted(giocatori, key=lambda g: (-g.fv, -g.voto, g.nome))


def catena(panca, campo):
    """Resa attesa della panchina di un ruolo: se il primo non gioca entra il
    secondo, e cosi' via. Se nessuno gioca la casella resta vuota e vale zero."""
    resa = 0.0
    for g in reversed(panca):
        resa = g.p * getattr(g, campo) + (1 - g.p) * resa
    return resa


def esiti_reparto(scelti, panca, forza=None):
    """Tutti gli esiti di un reparto schierato: per ogni combinazione di dubbi
    che giocano o no, le sostituzioni fatte come le fa la lega (ruolo per
    ruolo, in ordine di panchina, entra il primo che ha giocato). Ogni esito
    porta la sua probabilita', chi occupa ogni casella (None = vuota, vale
    zero), la somma dei fantavoti e i voti puri di chi e' in campo.

    Fino al 10 ottobre 2026 ogni dubbio valeva p*fv + (1-p)*ricambio con lo
    stesso ricambio per tutti: con tre ballottaggi in attacco il primo della
    panchina "entrava" tre volte, e un titolare sicuro lasciato fuori sembrava
    gratis (Thuram in panchina dietro a Lontani, Dovbyk e Vitinha). Enumerare
    gli esiti costa 2^dubbi per reparto, al massimo 256: nulla.

    `forza` e' un dizionario id(giocatore) -> probabilita' che sostituisce
    quella del giocatore: serve al costo dell'errore (lui gioca di sicuro /
    non gioca di sicuro, tutto il resto uguale)."""
    forza = forza or {}
    prob_di = lambda g: forza.get(id(g), g.p)
    dubbi = [g for g in scelti + panca if 0 < prob_di(g) < 1]
    esiti = []
    for maschera in range(1 << len(dubbi)):
        prob = 1.0
        giocano = set()
        for i, g in enumerate(dubbi):
            if maschera >> i & 1:
                prob *= prob_di(g)
                giocano.add(id(g))
            else:
                prob *= 1 - prob_di(g)
        gioca = lambda g: prob_di(g) >= 1 or id(g) in giocano
        riserve = [g for g in panca if gioca(g)]
        caselle = []
        for g in scelti:
            if gioca(g):
                caselle.append(g)
            elif riserve:
                caselle.append(riserve.pop(0))
            else:
                caselle.append(None)
        esiti.append({"p": prob, "caselle": caselle,
                      "fv": sum(g.fv for g in caselle if g is not None),
                      "voti": [g.voto for g in caselle if g is not None]})
    return esiti


def modificatore_atteso(esiti_p, esiti_d):
    """Il modificatore mediato su tutti gli esiti di portiere e difesa: con
    i dubbi in campo non e' un numero intero ma una media pesata."""
    totale = 0.0
    for ep in esiti_p:
        por = ep["caselle"][0]
        if por is None:
            continue
        for ed in esiti_d:
            punti, _ = modificatore_difesa(por.voto, ed["voti"])
            totale += ep["p"] * ed["p"] * punti
    return totale


def valuta_reparto(disponibili, scelti, forza=None):
    """Un reparto schierato: chi resta fuori fa da panchina, in ordine di
    fantavoto, e il valore e' la media dei fantavoti su tutti gli esiti."""
    ids = {id(g) for g in scelti}
    panca = ordina([g for g in disponibili if id(g) not in ids])
    esiti = esiti_reparto(scelti, panca, forza)
    attesi = []
    for i, g in enumerate(scelti):
        attesi.append({
            "g": g, "p": g.p,
            "atteso": sum(e["p"] * e["caselle"][i].fv for e in esiti if e["caselle"][i] is not None),
            "voto_atteso": sum(e["p"] * e["caselle"][i].voto for e in esiti if e["caselle"][i] is not None),
        })
    ricambio = {"fv": catena(panca, "fv"), "voto": catena(panca, "voto")}
    return {"scelti": list(scelti), "attesi": attesi, "panca": panca, "esiti": esiti,
            "ricambio": ricambio, "somma": sum(e["p"] * e["fv"] for e in esiti)}


def migliore_reparto(disponibili, n):
    migliore = None
    for combo in combinations(disponibili, n):
        v = valuta_reparto(disponibili, list(combo))
        if migliore is None or v["somma"] > migliore["somma"]:
            migliore = v
    return migliore


def totale_formazione(reparti, forza=None):
    """Il totale atteso di una formazione gia' scelta: i quattro reparti
    piu' il modificatore atteso. Serve al costo dell'errore."""
    esiti = {}
    somma = 0.0
    for r in RUOLI:
        esiti[r] = esiti_reparto(reparti[r]["scelti"], reparti[r]["panca"], forza)
        somma += sum(e["p"] * e["fv"] for e in esiti[r])
    return somma + modificatore_atteso(esiti["P"], esiti["D"])


def valuta_modulo(disponibili, nome_modulo):
    nd, nc, na = MODULI[nome_modulo]
    per = lambda r: ordina([g for g in disponibili if g.ruolo == r])
    P, D, C, A = per("P"), per("D"), per("C"), per("A")
    if not P or len(D) < nd or len(C) < nc or len(A) < na:
        return None

    # centrocampo e attacco non toccano il modificatore: si scelgono da soli
    c, a = migliore_reparto(C, nc), migliore_reparto(A, na)

    # portiere e difesa interagiscono col modificatore: si provano tutti
    portieri = [valuta_reparto(P, [por]) for por in P]
    migliore = None
    for combo in combinations(D, nd):
        vd = valuta_reparto(D, list(combo))
        for vp in portieri:
            mod_atteso = modificatore_atteso(vp["esiti"], vd["esiti"])
            totale = vp["somma"] + vd["somma"] + c["somma"] + a["somma"] + mod_atteso
            if migliore is None or totale > migliore["totale"]:
                # sul misuratore l'app disegna il modificatore "se giocano tutti"
                mod, media = modificatore_difesa(vp["scelti"][0].voto, [g.voto for g in combo])
                migliore = {"modulo": nome_modulo, "totale": totale, "modificatore": mod,
                            "media_difesa": media, "mod_atteso": mod_atteso,
                            "reparti": {"P": vp, "D": vd, "C": c, "A": a}}
    return migliore


def costo_errore(val, ruolo, indice):
    """Quanto costa se un titolare in dubbio non gioca: il totale atteso con
    lui sicuro in campo meno quello con lui sicuro fuori, tutto il resto
    com'e' (gli altri dubbi restano dubbi, i ricambi entrano da soli,
    modificatore compreso)."""
    rep = val["reparti"][ruolo]
    g = rep["attesi"][indice]["g"]
    con_lui = totale_formazione(val["reparti"], {id(g): 1.0})
    senza = totale_formazione(val["reparti"], {id(g): 0.0})
    sostituto = rep["panca"][0].nome if rep["panca"] else None
    return con_lui - senza, sostituto


def consiglia(rosa, modulo=None):
    """La formazione migliore; con `modulo` la migliore in quel modulo
    (e' quello che fa l'app quando Marco tocca un modulo)."""
    disponibili = [g for g in rosa if g.p > 0]
    valutazioni = [v for v in (valuta_modulo(disponibili, m) for m in MODULI) if v]
    if not valutazioni:
        raise ValueError("Rosa incompleta: non basta per nessun modulo.")
    valutazioni.sort(key=lambda v: -v["totale"])
    s = valutazioni[0]
    if modulo:
        trovati = [v for v in valutazioni if v["modulo"] == modulo]
        if not trovati:
            raise ValueError(f"Con questa rosa il {modulo} non si puo' schierare.")
        s = trovati[0]
    return completa(s, [v for v in valutazioni if v is not s], rosa)


def valuta_scelta(rosa, modulo, nomi):
    """Una formazione scelta a mano: gli undici per nome, nel modulo dato.
    Stesso conto del consiglio (esiti dei dubbi, sostituzioni, modificatore
    atteso), cosi' Marco vede quanto vale la sua idea accanto a quella del
    motore. Torna None se gli undici non riempiono il modulo."""
    disponibili = [g for g in rosa if g.p > 0]
    nd, nc, na = MODULI[modulo]
    nomi = set(nomi)
    reparti = {}
    for r, n in zip(RUOLI, (1, nd, nc, na)):
        per_ruolo = ordina([g for g in disponibili if g.ruolo == r])
        scelti = [g for g in per_ruolo if g.nome in nomi]
        if len(scelti) != n:
            return None
        reparti[r] = valuta_reparto(per_ruolo, scelti)
    mod_atteso = modificatore_atteso(reparti["P"]["esiti"], reparti["D"]["esiti"])
    totale = reparti["P"]["somma"] + reparti["D"]["somma"] + reparti["C"]["somma"] + reparti["A"]["somma"] + mod_atteso
    mod, media = modificatore_difesa(reparti["P"]["scelti"][0].voto, [g.voto for g in reparti["D"]["scelti"]])
    s = {"modulo": modulo, "totale": totale, "modificatore": mod, "media_difesa": media,
         "mod_atteso": mod_atteso, "reparti": reparti, "scelta": True}
    # accanto alla scelta a mano restano, per confronto, i moduli in automatico
    valutazioni = sorted([v for v in (valuta_modulo(disponibili, m) for m in MODULI) if v],
                         key=lambda v: -v["totale"])
    return completa(s, valutazioni, rosa)


def completa(s, alternative, rosa):
    """Dalla valutazione di un modulo alla risposta intera: undici con i
    costi, panchina, altri moduli, gol, dubbi."""
    s["undici"] = []
    for r in RUOLI:
        for i, x in enumerate(s["reparti"][r]["attesi"]):
            costo, sostituto = costo_errore(s, r, i)
            s["undici"].append({"g": x["g"], "ruolo": r, "p": x["p"], "atteso": x["atteso"],
                                "voto_atteso": x["voto_atteso"], "costo": costo, "sostituto": sostituto})
    s["panchina"] = [g for r in RUOLI for g in s["reparti"][r]["panca"]]
    s["ricambi"] = {r: s["reparti"][r]["ricambio"] for r in RUOLI}
    s["fuori"] = [g for g in rosa if g.p <= 0]
    s["alternative"] = [{"modulo": v["modulo"], "totale": v["totale"], "modificatore": v["modificatore"],
                         "media_difesa": v["media_difesa"], "mod_atteso": v["mod_atteso"]}
                        for v in alternative]
    s["gol"] = gol_da_punti(s["totale"])
    s["al_gol_dopo"] = punti_per_gol_successivo(s["totale"])
    s["dubbi"] = sorted([x for x in s["undici"] if x["p"] < 1], key=lambda x: -x["costo"])
    return s


def come_json(s):
    """La stessa forma che produce l'app, per confrontare le due implementazioni."""
    return {
        "modulo": s["modulo"], "totale": s["totale"], "mod": s["modificatore"], "media": s["media_difesa"],
        "modAtteso": s["mod_atteso"], "scelta": bool(s.get("scelta")),
        "undici": [{"n": x["g"].nome, "r": x["ruolo"], "p": x["p"], "atteso": x["atteso"],
                    "votoAtteso": x["voto_atteso"], "costo": x["costo"], "sostituto": x["sostituto"]}
                   for x in s["undici"]],
        "panchina": [g.nome for g in s["panchina"]],
        "alternative": [{"modulo": a["modulo"], "totale": a["totale"], "mod": a["modificatore"],
                         "modAtteso": a["mod_atteso"]} for a in s["alternative"]],
        "gol": s["gol"], "alGolDopo": s["al_gol_dopo"],
    }


def stampa(s):
    ruoli = {"P": "Portiere", "D": "Difesa", "C": "Centrocampo", "A": "Attacco"}
    print(f"\n  {s['modulo']}   {s['totale']:.2f} punti attesi   {s['gol']} gol")
    if s["media_difesa"] is not None:
        print(f"  modificatore +{s['modificatore']} se giocano tutti (media difesa {s['media_difesa']:.3f}),"
              f" atteso +{s['mod_atteso']:.2f} contando i dubbi")
    else:
        print("  modificatore non attivo")
    print(f"  al gol successivo mancano {s['al_gol_dopo']} punti\n")

    ultimo = None
    for x in s["undici"]:
        g = x["g"]
        if x["ruolo"] != ultimo:
            print(f"  {ruoli[x['ruolo']]}")
            ultimo = x["ruolo"]
        avviso = f"   ← dubbio {x['p']:.0%}, se perde costa {x['costo']:.2f}" if x["p"] < 1 else ""
        print(f"    {g.nome:<18} {g.fv:>5.2f}   voto {g.voto:>4.2f}   atteso {x['atteso']:>5.2f}{avviso}")

    print("\n  Panchina, in quest'ordine (ruolo per ruolo, per fantavoto)")
    for i, g in enumerate(s["panchina"], 1):
        dubbio = f"   {g.p:.0%}" if g.p < 1 else ""
        print(f"    {i:>2}. {g.nome:<18} {g.ruolo}   {g.fv:>5.2f}{dubbio}")

    print("\n  Ricambio atteso per ruolo: " + "   ".join(
        f"{r} {s['ricambi'][r]['fv']:.2f}" for r in RUOLI if s["ricambi"][r]["fv"]))

    print("\n  Gli altri moduli")
    for alt in s["alternative"]:
        delta = alt["totale"] - s["totale"]
        mod = f"+{alt['mod_atteso']:.2f}" if alt["media_difesa"] is not None else "     "
        print(f"    {alt['modulo']}   {alt['totale']:>6.2f}   ({delta:+.2f})   mod {mod}")

    if s["dubbi"]:
        print("\n  I dubbi, dal piu' caro:")
        for x in s["dubbi"]:
            g = x["g"]
            entra = f"entra {x['sostituto']}" if x["sostituto"] else "nessun ricambio, casella vuota"
            print(f"    {g.nome:<18} {x['p']:.0%} titolare   se perde -{max(0, x['costo']):.2f}   ({entra})"
                  + (f"   {g.nota}" if g.nota else ""))
    print()


def carica(percorso):
    dati = json.loads(Path(percorso).read_text(encoding="utf-8"))
    voci = dati["giocatori"] if isinstance(dati, dict) and "giocatori" in dati else dati
    if isinstance(dati, dict) and "rosa" in dati:
        voci = dati["rosa"]
    out = []
    for v in voci:
        # accetta sia i nomi lunghi del Mac sia quelli corti dell'app
        out.append(Giocatore(
            nome=v.get("nome", v.get("n")), ruolo=v.get("ruolo", v.get("r")),
            fv=v.get("fv", 6.0), voto=v.get("voto"), p=v.get("p"), st=v.get("st"), pb=v.get("pb"),
            squadra=v.get("squadra", v.get("sq", "")), nota=v.get("nota", "")))
    return out


# --- rosa di esempio, serve per provare il motore prima dell'asta ---
ESEMPIO = [
    Giocatore("Portiere top", "P", 6.30, 6.30, 1.0),
    Giocatore("Portiere due", "P", 5.60, 5.60, 1.0),
    Giocatore("Portiere tre", "P", 5.40, 5.40, 1.0),
    Giocatore("Difensore muro", "D", 6.20, 6.20, 1.0),
    Giocatore("Terzino bonus", "D", 6.60, 6.00, 0.9),
    Giocatore("Centrale voto", "D", 6.45, 6.45, 1.0),
    Giocatore("Braccetto", "D", 6.15, 6.15, 0.95),
    Giocatore("Quinto rischio", "D", 6.00, 6.00, 0.5, nota="ballottaggio"),
    Giocatore("Riserva dif", "D", 5.80, 5.80, 1.0),
    Giocatore("Panchinaro dif", "D", 5.70, 5.70, 1.0),
    Giocatore("Ultimo dif", "D", 5.50, 5.50, 0.3),
    Giocatore("Mezzala gol", "C", 7.10, 6.10, 1.0),
    Giocatore("Regista", "C", 6.30, 6.30, 1.0),
    Giocatore("Trequartista", "C", 6.90, 6.20, 0.85),
    Giocatore("Esterno", "C", 6.40, 6.10, 0.9),
    Giocatore("Mediano", "C", 5.90, 6.00, 1.0),
    Giocatore("Jolly", "C", 6.10, 6.00, 0.6, nota="rientro da infortunio"),
    Giocatore("Riserva cen", "C", 5.70, 5.80, 1.0),
    Giocatore("Ultimo cen", "C", 5.60, 5.70, 0.5),
    Giocatore("Bomber", "A", 8.20, 6.40, 1.0),
    Giocatore("Punta due", "A", 7.10, 6.10, 0.95),
    Giocatore("Ala", "A", 6.70, 6.00, 0.8),
    Giocatore("Vice punta", "A", 6.20, 5.90, 0.45, nota="parte dietro nelle gerarchie"),
    Giocatore("Scommessa", "A", 5.90, 5.80, 1.0),
    Giocatore("Ultimo att", "A", 5.60, 5.70, 0.5),
]

if __name__ == "__main__":
    argomenti = [a for a in sys.argv[1:] if not a.startswith("--")]
    rosa = carica(argomenti[0]) if argomenti else ESEMPIO
    try:
        scelta = consiglia(rosa)
    except ValueError as e:
        print(f"\n  {e}")
        print("  Servono almeno 1 portiere, 3 difensori, 3 centrocampisti e 1 attaccante.")
        print("  Il file dati/rosa.json contiene solo quattro righe di esempio: riempilo dopo l'asta.\n")
        sys.exit(1)
    if "--json" in sys.argv:
        print(json.dumps(come_json(scelta), ensure_ascii=False, indent=1))
    else:
        stampa(scelta)
