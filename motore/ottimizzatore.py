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


def valuta_reparto(disponibili, scelti):
    """Un reparto schierato: chi resta fuori fa da ricambio, e ogni titolare
    in dubbio vale la sua parte piu' la parte del ricambio."""
    ids = {id(g) for g in scelti}
    panca = ordina([g for g in disponibili if id(g) not in ids])
    ricambio = {"fv": catena(panca, "fv"), "voto": catena(panca, "voto")}
    attesi = [{
        "g": g, "p": g.p,
        "atteso": g.p * g.fv + (1 - g.p) * ricambio["fv"],
        "voto_atteso": g.p * g.voto + (1 - g.p) * ricambio["voto"],
    } for g in scelti]
    return {"attesi": attesi, "panca": panca, "ricambio": ricambio,
            "somma": sum(x["atteso"] for x in attesi)}


def migliore_reparto(disponibili, n):
    migliore = None
    for combo in combinations(disponibili, n):
        v = valuta_reparto(disponibili, list(combo))
        if migliore is None or v["somma"] > migliore["somma"]:
            migliore = v
    return migliore


def valuta_modulo(disponibili, nome_modulo):
    nd, nc, na = MODULI[nome_modulo]
    per = lambda r: ordina([g for g in disponibili if g.ruolo == r])
    P, D, C, A = per("P"), per("D"), per("C"), per("A")
    if not P or len(D) < nd or len(C) < nc or len(A) < na:
        return None

    # centrocampo e attacco non toccano il modificatore: si scelgono da soli
    c, a = migliore_reparto(C, nc), migliore_reparto(A, na)

    # portiere e difesa interagiscono col modificatore: si provano tutti
    migliore = None
    for por in P:
        vp = valuta_reparto(P, [por])
        for combo in combinations(D, nd):
            vd = valuta_reparto(D, list(combo))
            mod, media = modificatore_difesa(vp["attesi"][0]["voto_atteso"],
                                             [x["voto_atteso"] for x in vd["attesi"]])
            totale = vp["somma"] + vd["somma"] + c["somma"] + a["somma"] + mod
            if migliore is None or totale > migliore["totale"]:
                migliore = {"modulo": nome_modulo, "totale": totale, "modificatore": mod,
                            "media_difesa": media, "reparti": {"P": vp, "D": vd, "C": c, "A": a}}
    return migliore


def costo_errore(val, ruolo, indice):
    """Quanto costa se un titolare in dubbio non gioca: la differenza fra il
    punteggio con lui in campo e quello con il suo ricambio al suo posto,
    modificatore compreso."""
    rep = val["reparti"][ruolo]
    x = rep["attesi"][indice]

    def scenario(fv_suo, voto_suo):
        voti_d = [voto_suo if (ruolo == "D" and i == indice) else d["voto_atteso"]
                  for i, d in enumerate(val["reparti"]["D"]["attesi"])]
        voto_p = voto_suo if ruolo == "P" else val["reparti"]["P"]["attesi"][0]["voto_atteso"]
        mod, _ = modificatore_difesa(voto_p, voti_d)
        return val["totale"] - x["atteso"] + fv_suo - val["modificatore"] + mod

    con_lui = scenario(x["g"].fv, x["g"].voto)
    senza = scenario(rep["ricambio"]["fv"], rep["ricambio"]["voto"])
    sostituto = rep["panca"][0].nome if rep["panca"] else None
    return con_lui - senza, sostituto


def consiglia(rosa):
    disponibili = [g for g in rosa if g.p > 0]
    valutazioni = [v for v in (valuta_modulo(disponibili, m) for m in MODULI) if v]
    if not valutazioni:
        raise ValueError("Rosa incompleta: non basta per nessun modulo.")
    valutazioni.sort(key=lambda v: -v["totale"])
    s = valutazioni[0]

    s["undici"] = []
    for r in RUOLI:
        for i, x in enumerate(s["reparti"][r]["attesi"]):
            costo, sostituto = costo_errore(s, r, i)
            s["undici"].append({"g": x["g"], "ruolo": r, "p": x["p"], "atteso": x["atteso"],
                                "voto_atteso": x["voto_atteso"], "costo": costo, "sostituto": sostituto})
    s["panchina"] = [g for r in RUOLI for g in s["reparti"][r]["panca"]]
    s["ricambi"] = {r: s["reparti"][r]["ricambio"] for r in RUOLI}
    s["fuori"] = [g for g in rosa if g.p <= 0]
    s["alternative"] = [{"modulo": v["modulo"], "totale": v["totale"],
                         "modificatore": v["modificatore"], "media_difesa": v["media_difesa"]}
                        for v in valutazioni[1:]]
    s["gol"] = gol_da_punti(s["totale"])
    s["al_gol_dopo"] = punti_per_gol_successivo(s["totale"])
    s["dubbi"] = sorted([x for x in s["undici"] if x["p"] < 1], key=lambda x: -x["costo"])
    return s


def come_json(s):
    """La stessa forma che produce l'app, per confrontare le due implementazioni."""
    return {
        "modulo": s["modulo"], "totale": s["totale"], "mod": s["modificatore"], "media": s["media_difesa"],
        "undici": [{"n": x["g"].nome, "r": x["ruolo"], "p": x["p"], "atteso": x["atteso"],
                    "votoAtteso": x["voto_atteso"], "costo": x["costo"], "sostituto": x["sostituto"]}
                   for x in s["undici"]],
        "panchina": [g.nome for g in s["panchina"]],
        "alternative": [{"modulo": a["modulo"], "totale": a["totale"], "mod": a["modificatore"]} for a in s["alternative"]],
        "gol": s["gol"], "alGolDopo": s["al_gol_dopo"],
    }


def stampa(s):
    ruoli = {"P": "Portiere", "D": "Difesa", "C": "Centrocampo", "A": "Attacco"}
    print(f"\n  {s['modulo']}   {s['totale']:.2f} punti attesi   {s['gol']} gol")
    if s["modificatore"]:
        print(f"  modificatore +{s['modificatore']} (media difesa {s['media_difesa']:.3f})")
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
        mod = f"+{alt['modificatore']}" if alt["modificatore"] else "  "
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
