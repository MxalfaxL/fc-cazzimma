"""I fantapunti veri di una giornata: la formazione confermata ai voti ufficiali.

Il giro, dal 10 ottobre 2026: Marco manda la formazione sulla piattaforma e
nell'app tocca "Conferma: questa l'ho mandata" (finisce in
`stato.formazioni[giornata]` dentro stato.json); il lunedi' arriva il file dei
voti e `voti_ufficiali.py` scrive `dati/voti-ufficiali/giornata-N.json`. Qui
si mettono insieme le due cose con le regole della lega (`regole.py`), e il
risultato va in `report/risultati.json`, che `invia_listone.py` porta all'app.

Niente avversario e niente calendario: la lega ha piu' competizioni tutte
contro tutti, la Stagione dell'app e' personale (decisione di Marco del
10/10/2026). Si contano i punti di FC Cazzimma e basta.

Come si fanno i conti (regolamento, punti 5, 7.1, 8.2 e 9):
- chi ha un voto prende il fantavoto: voto piu' bonus e malus del file
  ufficiale, con il ruolo con cui e' stato schierato (i gol subiti pesano solo
  sul portiere);
- chi non ha voto (non ha giocato, o s.v.) lascia il posto al primo della
  panchina DELLO STESSO RUOLO che ha un voto, nell'ordine della panchina;
  massimo 5 sostituzioni in tutto, portiere compreso. Si scorre l'undici da
  portiere ad attacco, come lo scrive l'app;
- il regolamento prevede anche il cambio modulo quando in panchina manca il
  ruolo: NON lo modelliamo. La casella resta vuota, vale 0, e lo diciamo forte
  (in quel caso il punteggio della piattaforma puo' essere piu' alto del nostro);
- modificatore difesa sui voti PURI del portiere e dei difensori davvero in
  campo (titolari con voto e difensori entrati), solo se sono almeno 4;
- gol dalle fasce: primo a 66, poi uno ogni 4.

`stato.json` del repository privato si LEGGE soltanto: ci scrive solo l'app.

Uso:
    python3 motore/punteggio_giornata.py 6
    python3 motore/punteggio_giornata.py 6 --stato copia-dello-stato.json

Scrive (o aggiorna, una giornata alla volta) `report/risultati.json`:
    {"giornate": {"6": {"giornata", "modulo", "totale", "gol", "mod", "media",
      "attesi", "undici": [{"n", "r", "sq", "voto", "fv", "eventi",
      "entrato_per", "vuoto"}], "sostituzioni": [{"fuori", "dentro"}],
      "senza_voto": [chi e' rimasto senza voto E senza ricambio], "calcolato"}}}
"""

import json
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE / "motore"))
from dossier import norm  # noqa: E402
from regole import (MODULI, SOSTITUZIONI, DIFENSORI_MINIMI_PER_MODIFICATORE,  # noqa: E402
                    fantavoto, gol_da_punti, modificatore_difesa, punti_per_gol_successivo)
from voti_ufficiali import USCITA as CARTELLA_VOTI, racconta  # noqa: E402

UTENTE = "MxalfaxL"          # l'account che vede il repository privato
RIENTRO = "MarcoRenais"      # l'account di lavoro, quello di default sul Mac
REPO = "fc-cazzimma-dati"
RISULTATI = RADICE / "report" / "risultati.json"
LISTONE = RADICE / "report" / "listone.json"
ORDINE = ["P", "D", "C", "A"]
NOME_RUOLO = {"P": "Portiere", "D": "Difesa", "C": "Centrocampo", "A": "Attacco"}


def gh(*argomenti):
    return subprocess.run(["gh", *argomenti], capture_output=True, text=True)


def leggi_stato_remoto():
    """stato.json dal repository privato, in sola lettura. Il cambio di account
    si rimette a posto anche se la lettura fallisce: l'account di lavoro deve
    restare quello attivo sul Mac."""
    try:
        cambio = gh("auth", "switch", "--user", UTENTE)
        if cambio.returncode != 0:
            sys.exit(f"Non riesco a passare all'account {UTENTE}: {cambio.stderr.strip()}")
        esito = gh("api", f"repos/{UTENTE}/{REPO}/contents/stato.json",
                   "-H", "Accept: application/vnd.github.raw")
        if esito.returncode != 0:
            sys.exit(f"Non riesco a leggere stato.json da {REPO}: {esito.stderr.strip() or esito.stdout.strip()}")
        try:
            return json.loads(esito.stdout)
        except json.JSONDecodeError:
            sys.exit("stato.json letto da GitHub non e' un JSON valido: guardalo prima di andare avanti.")
    finally:
        gh("auth", "switch", "--user", RIENTRO)


def leggi_stato(percorso):
    if percorso:
        p = Path(percorso)
        if not p.exists():
            sys.exit(f"Non trovo {p}")
        return json.loads(p.read_text(encoding="utf-8"))
    return leggi_stato_remoto()


def leggi_voti(giornata):
    percorso = CARTELLA_VOTI / f"giornata-{giornata}.json"
    if not percorso.exists():
        sys.exit(f"Mancano i voti della {giornata}ª ({percorso.relative_to(RADICE)}). Metti il file "
                 f"di Fantacalcio.it in 'Voti Fantacalcio/' e lancia: python3 motore/voti_ufficiali.py")
    return json.loads(percorso.read_text(encoding="utf-8"))["voti"]


def squadre_dal_listone():
    """Nome -> squadra, per i panchinari (la conferma salva la squadra solo
    degli undici) e per accorgersi dei nomi che nel listone non ci sono."""
    if not LISTONE.exists():
        return {}
    return {g["n"]: g.get("sq", "") for g in json.loads(LISTONE.read_text(encoding="utf-8"))["listone"]}


class Voti:
    """I voti della giornata, cercati per nome come fa `dossier.py importa`:
    il file dei voti usa i nomi del listone, e la rosa dell'app pure. Il file
    porta solo chi ha preso un voto: chi non c'e' non ha giocato (o e' s.v.).
    Solo per un nome che il listone non conosce (scritto a mano, accento
    diverso) si prova la stessa forma senza accenti e punteggiatura, se e' una
    sola: per un nome del listone che manca nei voti la risposta giusta e'
    "non ha giocato", non il primo che gli somiglia."""

    def __init__(self, voti, nomi_listone=()):
        self.esatti = {v["nome"]: v for v in voti}
        self.nomi_listone = set(nomi_listone)
        self.per_chiave = defaultdict(list)
        for v in voti:
            self.per_chiave[norm(v["nome"])].append(v)
        self.senza_colonne = 0

    def di(self, nome):
        if nome in self.esatti:
            return self.esatti[nome]
        if nome in self.nomi_listone:
            return None
        simili = self.per_chiave.get(norm(nome), [])
        return simili[0] if len(simili) == 1 else None

    def scheda(self, giocatore):
        """Voto, fantavoto ed eventi di un giocatore, o None se non ha voto."""
        v = self.di(giocatore["n"])
        if v is None:
            return None
        ruolo = giocatore["r"]
        if "colonne" in v:
            colonne = v["colonne"]
            fv = fantavoto(v["voto"], colonne, ruolo)
            eventi = racconta(colonne, ruolo)
            if v.get("ufficio"):
                eventi = (eventi + ", " if eventi else "") + "voto d'ufficio"
        else:
            # file scritto prima del 10/10/2026: il fantavoto e' gia' fatto con
            # le stesse regole ma con il ruolo del listone. Va quasi sempre bene,
            # ma e' meglio rigenerare il file e lo diciamo in fondo.
            self.senza_colonne += 1
            fv = v["fantavoto"]
            eventi = v.get("eventi", "")
        return {"voto": v["voto"], "fv": round(fv, 2), "eventi": eventi}


def calcola(giornata, formazione, voti, squadre):
    """La giornata come la conta la lega. Restituisce il risultato (quello che
    va nel file) e gli avvisi da stampare."""
    avvisi = []
    undici_conf = formazione.get("undici") or []
    panchina = list(formazione.get("panchina") or [])
    modulo = formazione.get("modulo", "")

    if len(undici_conf) != 11:
        avvisi.append(f"la formazione confermata ha {len(undici_conf)} titolari, non 11")
    if modulo in MODULI:
        attesi = dict(zip(["D", "C", "A"], MODULI[modulo]), P=1)
        contati = {r: sum(1 for g in undici_conf if g.get("r") == r) for r in ORDINE}
        if contati != attesi:
            avvisi.append(f"il modulo dice {modulo} ma i ruoli sono "
                          + " ".join(f"{r}{contati[r]}" for r in ORDINE))
    else:
        avvisi.append(f"modulo '{modulo}' sconosciuto")
    for g in undici_conf + panchina:
        if squadre and g.get("n") not in squadre:
            avvisi.append(f"{g.get('n')} non e' nel listone: se risulta senza voto puo' essere il nome, "
                          "non la partita saltata")

    in_campo, sostituzioni, senza_voto, usati = [], [], [], set()
    # da portiere ad attacco, nell'ordine dell'undici: e' l'ordine in cui la
    # piattaforma scorre i titolari quando cerca i ricambi
    titolari = sorted(undici_conf, key=lambda g: ORDINE.index(g["r"]) if g.get("r") in ORDINE else 9)
    for g in titolari:
        sq = g.get("sq") or squadre.get(g["n"], "")
        s = voti.scheda(g)
        if s is not None:
            in_campo.append({"n": g["n"], "r": g["r"], "sq": sq, **s, "entrato_per": None})
            continue
        ricambio = None
        if len(sostituzioni) < SOSTITUZIONI:
            for i, b in enumerate(panchina):
                if i in usati or b.get("r") != g["r"]:
                    continue
                sb = voti.scheda(b)
                if sb is not None:
                    ricambio = (i, b, sb)
                    break
        if ricambio:
            i, b, sb = ricambio
            usati.add(i)
            sostituzioni.append({"fuori": g["n"], "dentro": b["n"]})
            in_campo.append({"n": b["n"], "r": b["r"], "sq": squadre.get(b["n"], ""), **sb,
                             "entrato_per": g["n"]})
        else:
            perche = ("finite le 5 sostituzioni" if len(sostituzioni) >= SOSTITUZIONI
                      else "nessuno in panchina nel suo ruolo con un voto")
            senza_voto.append(g["n"])
            avvisi.append(f"{g['n']} ({g['r']}) senza voto e senza ricambio ({perche}): casella vuota, 0 punti. "
                          "La piattaforma qui cambierebbe modulo se puo': il nostro conto e' per difetto")
            in_campo.append({"n": g["n"], "r": g["r"], "sq": sq, "voto": None, "fv": 0,
                             "eventi": "senza voto, nessun ricambio", "entrato_per": None, "vuoto": True})

    # il modificatore: voti puri, solo chi e' davvero in campo
    portiere = next((x for x in in_campo if x["r"] == "P" and not x.get("vuoto")), None)
    voti_dif = [x["voto"] for x in in_campo if x["r"] == "D" and not x.get("vuoto")]
    mod, media = 0, None
    if portiere and len(voti_dif) >= DIFENSORI_MINIMI_PER_MODIFICATORE:
        mod, media = modificatore_difesa(portiere["voto"], voti_dif)
        media = round(media, 3)
    elif not portiere:
        avvisi.append("nessun portiere con un voto: modificatore non calcolato")

    somma = round(sum(x["fv"] for x in in_campo), 2)
    totale = round(somma + mod, 2)
    risultato = {
        "giornata": giornata, "modulo": modulo, "totale": totale, "gol": gol_da_punti(totale),
        "mod": mod, "media": media, "attesi": formazione.get("totale"),
        "undici": in_campo, "sostituzioni": sostituzioni, "senza_voto": senza_voto,
        "calcolato": int(time.time() * 1000),
    }
    return risultato, avvisi, somma, portiere, voti_dif


def numero(x):
    """6.0 -> '6', 6.5 -> '6.5': come si leggono i voti sul giornale."""
    if x is None:
        return "–"
    return f"{x:g}"


def stampa(r, avvisi, somma, portiere, voti_dif, formazione, voti):
    quando = formazione.get("quando")
    conferma = f" · confermata il {datetime.fromtimestamp(quando / 1000):%d/%m alle %H:%M}" if quando else ""
    print(f"\nGiornata {r['giornata']} · {r['modulo']}{conferma}\n")
    for ruolo in ORDINE:
        righe = [x for x in r["undici"] if x["r"] == ruolo]
        if not righe:
            continue
        print(f"  {NOME_RUOLO[ruolo]}")
        for x in righe:
            nota = f"  (entrato per {x['entrato_per']})" if x["entrato_per"] else ""
            if x.get("vuoto"):
                print(f"    {x['n']:<22} {x['sq']:<11} SENZA VOTO, nessun ricambio      fv  0")
                continue
            bonus = x["fv"] - (x["voto"] or 0)
            dettaglio = f"{x['eventi']}" if x["eventi"] else ""
            segno = f"{bonus:+g}" if bonus else ""
            print(f"    {x['n']:<22} {x['sq']:<11} voto {numero(x['voto']):<4} {segno:<5} {dettaglio:<20} fv {numero(x['fv'])}{nota}")
    print()
    if r["sostituzioni"]:
        print(f"  Sostituzioni ({len(r['sostituzioni'])} di {SOSTITUZIONI}): "
              + ", ".join(f"{s['fuori']} -> {s['dentro']}" for s in r["sostituzioni"]))
    else:
        print("  Nessuna sostituzione: hanno preso il voto tutti e undici.")
    if r["senza_voto"]:
        print(f"  RIMASTI SENZA VOTO E SENZA RICAMBIO: {', '.join(r['senza_voto'])}")
    if r["media"] is not None:
        migliori = sorted(voti_dif, reverse=True)[:3]
        print(f"  Modificatore: portiere {numero(portiere['voto'])} + difensori "
              f"{', '.join(numero(v) for v in migliori)} -> media {r['media']:.3f} -> +{r['mod']}")
    else:
        print(f"  Modificatore: niente ({len(voti_dif)} difensori in campo con un voto, ne servono "
              f"{DIFENSORI_MINIMI_PER_MODIFICATORE})")
    manca = punti_per_gol_successivo(r["totale"])
    print(f"\n  TOTALE {numero(r['totale'])}  (fantavoti {numero(somma)} + modificatore {r['mod']})"
          f"  ->  {r['gol']} gol, al prossimo mancavano {numero(manca)}")
    if r.get("attesi") is not None:
        print(f"  Attesi alla conferma: {numero(r['attesi'])}  (scarto {r['totale'] - r['attesi']:+.2f})")
    if voti.senza_colonne:
        print(f"\n  Nota: per {voti.senza_colonne} giocatori il file dei voti non ha le colonne degli eventi "
              "(e' di prima del 10/10): uso il fantavoto gia' calcolato. Rilancia voti_ufficiali.py.")
    for a in avvisi:
        print(f"  ATTENZIONE: {a}")


def main():
    argomenti = sys.argv[1:]
    percorso_stato = None
    if "--stato" in argomenti:
        i = argomenti.index("--stato")
        if i + 1 >= len(argomenti):
            sys.exit("--stato vuole il percorso di una copia di stato.json")
        percorso_stato = argomenti[i + 1]
        del argomenti[i:i + 2]
    if len(argomenti) != 1 or not argomenti[0].isdigit():
        sys.exit("Uso: python3 motore/punteggio_giornata.py N [--stato copia.json]")
    giornata = int(argomenti[0])

    # prima i voti, che sono sul Mac: senza quelli e' inutile scomodare GitHub
    squadre = squadre_dal_listone()
    voti = Voti(leggi_voti(giornata), squadre)
    stato = leggi_stato(percorso_stato)
    formazioni = stato.get("formazioni") or {}
    formazione = formazioni.get(str(giornata)) or formazioni.get(giornata)
    if not formazione:
        confermate = sorted(int(k) for k, v in formazioni.items() if v and str(k).isdigit())
        sys.exit(f"Per la {giornata}ª non c'e' una formazione confermata nell'app"
                 + (f" (confermate: {', '.join(map(str, confermate))})" if confermate else " (nessuna confermata finora)")
                 + ". Si conferma dalla scheda Formazione: 'Conferma: questa l'ho mandata'.")

    if not squadre:
        print("  (manca report/listone.json: niente squadre per i panchinari e niente controllo dei nomi)")
    risultato, avvisi, somma, portiere, voti_dif = calcola(giornata, formazione, voti, squadre)
    stampa(risultato, avvisi, somma, portiere, voti_dif, formazione, voti)

    archivio = {"giornate": {}}
    if RISULTATI.exists():
        archivio = json.loads(RISULTATI.read_text(encoding="utf-8"))
        archivio.setdefault("giornate", {})
    archivio["giornate"][str(giornata)] = risultato
    archivio["giornate"] = dict(sorted(archivio["giornate"].items(), key=lambda kv: int(kv[0])))
    RISULTATI.parent.mkdir(exist_ok=True)
    RISULTATI.write_text(json.dumps(archivio, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  Scritto {RISULTATI.relative_to(RADICE)} (giornate: {', '.join(archivio['giornate'])}). "
          "Ora: python3 motore/invia_listone.py\n")


if __name__ == "__main__":
    main()
