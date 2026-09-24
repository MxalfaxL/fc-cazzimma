"""Le difese e i rigori veri, dai file dei voti ufficiali.

Il listone stima la solidita' di una difesa dalla quotazione del portiere piu'
caro: un'approssimazione dichiarata, in attesa dei numeri veri. I numeri veri
li abbiamo gia': i file di Fantacalcio.it che Marco scarica ogni giornata non
portano solo il voto, ma per ogni giocatore gol fatti e subiti, rigori
segnati, sbagliati e parati, assist, cartellini, autogol. Qui li contiamo per
squadra e per giocatore.

Perche' conta per l'asta: il modificatore difesa vive del voto PURO del
portiere e dei tre migliori difensori. Una difesa che prende pochi gol ma
che ha voti puri bassi non da' modificatore; una che ha voti alti si'. Per
questo, oltre ai gol subiti, contiamo il voto puro medio di portiere e
difensori squadra per squadra, e quanto varrebbe il modificatore se in campo
ci fossero portiere e tre migliori difensori di quella squadra (il "modificatore
di squadra": un tetto, non una previsione, perche' la rosa di Marco
mescolera' difensori di squadre diverse).

I rigori calciati davvero servono a controllare i rigoristi del dossier: e'
il livello di prova piu' alto che abbiamo (LEZIONI 16 set).

Uso:
    python3 motore/squadre.py         # scrive dati/squadre-2026-27.json e report/SQUADRE.md

Tutto resta privato: i file dei voti sono a uso personale degli iscritti.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import openpyxl

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE / "motore"))
from regole import modificatore_difesa  # noqa: E402
from voti_ufficiali import CARTELLA_FILE, COLONNE, FOGLIO, giornata_dal_nome  # noqa: E402

USCITA_JSON = RADICE / "dati" / "squadre-2026-27.json"
USCITA_MD = RADICE / "report" / "SQUADRE.md"
LISTONE = RADICE / "report" / "listone.json"


def leggi_giornata(percorso):
    """Tutte le righe con un voto, anche di chi non e' nel listone: per i
    conti di squadra servono tutti (un portiere ceduto ha comunque preso gol)."""
    foglio = openpyxl.load_workbook(percorso, read_only=True, data_only=True)[FOGLIO]
    righe, squadra = [], None
    for riga in foglio.iter_rows(values_only=True):
        prima = riga[0]
        if isinstance(prima, str) and riga[1] is None and len(prima) < 30:
            squadra = prima.strip()
            continue
        if not isinstance(prima, int) or riga[3] in (None, ""):
            continue
        d = dict(zip(COLONNE, riga))
        grezzo = str(d["Voto"]).strip()
        d["ufficio"] = grezzo.endswith("*")
        d["Voto"] = float(grezzo.rstrip("*").replace(",", "."))
        for k in ("Gf", "Gs", "Rp", "Rs", "Rf", "Au", "Amm", "Esp", "Ass"):
            d[k] = int(d.get(k) or 0)
        d["squadra"] = squadra
        righe.append(d)
    return righe


def media(valori):
    return round(sum(valori) / len(valori), 2) if valori else None


def conta(per_giornata, nomi_listone):
    squadre = defaultdict(lambda: {"giornate": {}})
    giocatori = {}
    for g, righe in sorted(per_giornata.items()):
        per_squadra = defaultdict(list)
        for r in righe:
            per_squadra[r["squadra"]].append(r)
        # gli autogol vanno all'avversario: senza calendario non sappiamo chi
        # sia, quindi il totale di squadra li conta a parte
        for sq, rr in per_squadra.items():
            portieri = [r for r in rr if r["Ruolo"] == "P"]
            difensori = [r for r in rr if r["Ruolo"] == "D"]
            gs = sum(r["Gs"] for r in portieri)
            # il portiere del modificatore e' quello che ha giocato di piu':
            # chi ha voto d'ufficio e' entrato a pochi minuti dalla fine
            veri = [r for r in portieri if not r["ufficio"]] or portieri
            portiere = veri[0] if veri else None
            voti_d = [r["Voto"] for r in difensori if not r["ufficio"]]
            punti, med = (0, None)
            if portiere and len(voti_d) >= 3:
                # anche con 3 difensori in campo calcoliamo il tetto: la
                # squadra reale puo' giocare a tre, la rosa di Marco a quattro.
                # Lo zero di riempimento non entra mai fra i tre migliori.
                punti, med = modificatore_difesa(portiere["Voto"], voti_d + [0] * max(0, 4 - len(voti_d)))
                med = round(med, 3)
            squadre[sq]["giornate"][g] = {
                "gs": gs,
                "gf": sum(r["Gf"] + r["Rf"] for r in rr),
                "autogol_fatti": sum(r["Au"] for r in rr),
                "porta_inviolata": gs == 0,
                "portiere": portiere["Nome"] if portiere else None,
                "voto_portiere": portiere["Voto"] if portiere else None,
                "voti_difensori": sorted(voti_d, reverse=True),
                "mod_media": med,
                "mod_punti": punti,
            }
        for r in righe:
            chiave = r["Cod."]
            v = giocatori.setdefault(chiave, {
                "codice": chiave, "nome": nomi_listone.get(chiave, r["Nome"]),
                "nel_listone": chiave in nomi_listone, "squadra": r["squadra"], "ruolo": r["Ruolo"],
                "presenze": 0, "voti_ufficio": 0, "voti": [], "gol": 0, "rigori_segnati": 0,
                "rigori_sbagliati": 0, "rigori_parati": 0, "assist": 0, "ammonizioni": 0,
                "espulsioni": 0, "autogol": 0, "gol_subiti": 0, "porte_inviolate": 0, "giornate": []})
            v["squadra"] = r["squadra"]       # l'ultima squadra vista, per chi cambia a settembre
            v["presenze"] += 1
            v["giornate"].append(g)
            if r["ufficio"]:
                v["voti_ufficio"] += 1
            else:
                v["voti"].append(r["Voto"])
            v["gol"] += r["Gf"] + r["Rf"]
            v["rigori_segnati"] += r["Rf"]
            v["rigori_sbagliati"] += r["Rs"]
            v["rigori_parati"] += r["Rp"]
            v["assist"] += r["Ass"]
            v["ammonizioni"] += r["Amm"]
            v["espulsioni"] += r["Esp"]
            v["autogol"] += r["Au"]
            if r["Ruolo"] == "P":
                v["gol_subiti"] += r["Gs"]
                if r["Gs"] == 0 and not r["ufficio"]:
                    v["porte_inviolate"] += 1
    for v in giocatori.values():
        v["media_voto_puro"] = media(v["voti"])
    riepilogo = {}
    for sq, s in squadre.items():
        gg = s["giornate"].values()
        mod = [x["mod_media"] for x in gg if x["mod_media"] is not None]
        riepilogo[sq] = {
            "giocate": len(s["giornate"]),
            "gol_subiti": sum(x["gs"] for x in gg),
            "gol_fatti_senza_autogol_avversari": sum(x["gf"] for x in gg),
            "porte_inviolate": sum(1 for x in gg if x["porta_inviolata"]),
            "voto_portiere_medio": media([x["voto_portiere"] for x in gg if x["voto_portiere"] is not None]),
            "voto_difesa_medio": media([v for x in gg for v in x["voti_difensori"]]),
            "mod_media": media(mod),
            "mod_punti_medi": media([x["mod_punti"] for x in gg if x["mod_media"] is not None]),
            "giornate": s["giornate"],
        }
    return riepilogo, giocatori


def scrivi_md(riepilogo, giocatori, giornate):
    righe = [f"# Difese e rigori veri — voti ufficiali, giornate {min(giornate)}-{max(giornate)}", "",
             "Dal file di Fantacalcio.it di ogni giornata. **Modificatore di squadra** = media fra il voto",
             "puro del portiere e dei 3 migliori difensori di quella squadra in quella giornata, e i punti",
             "che darebbe: e' un tetto (portiere e difesa tutti della stessa squadra), non una previsione.",
             "Voti d'ufficio (6*) fuori dalle medie.", "",
             "## Difese, dalla migliore per modificatore", "",
             "| Squadra | G | Gol subiti | Inviolate | Voto portiere | Voto difensori | Media mod. | Punti mod. a giornata |",
             "|---|---|---|---|---|---|---|---|"]
    for sq, s in sorted(riepilogo.items(), key=lambda kv: -(kv[1]["mod_media"] or 0)):
        righe.append(f"| {sq} | {s['giocate']} | {s['gol_subiti']} | {s['porte_inviolate']} | "
                     f"{s['voto_portiere_medio']} | {s['voto_difesa_medio']} | {s['mod_media']} | {s['mod_punti_medi']} |")
    righe += ["", "## Portieri (almeno 2 voti veri)", "",
              "| Portiere | Squadra | Voti | Media voto puro | Gol subiti | Inviolate | Rigori parati |",
              "|---|---|---|---|---|---|---|"]
    portieri = [v for v in giocatori.values() if v["ruolo"] == "P" and len(v["voti"]) >= 2]
    for v in sorted(portieri, key=lambda v: -v["media_voto_puro"]):
        fuori = "" if v["nel_listone"] else " (fuori listone)"
        righe.append(f"| {v['nome']}{fuori} | {v['squadra']} | {len(v['voti'])} | {v['media_voto_puro']} | "
                     f"{v['gol_subiti']} | {v['porte_inviolate']} | {v['rigori_parati']} |")
    righe += ["", "## Difensori per voto puro medio (almeno 3 voti veri)", "",
              "| Difensore | Squadra | Voti | Media voto puro | Gol | Assist | Ammonizioni |", "|---|---|---|---|---|---|---|"]
    difensori = [v for v in giocatori.values() if v["ruolo"] == "D" and len(v["voti"]) >= 3]
    for v in sorted(difensori, key=lambda v: -v["media_voto_puro"])[:40]:
        righe.append(f"| {v['nome']} | {v['squadra']} | {len(v['voti'])} | {v['media_voto_puro']} | "
                     f"{v['gol']} | {v['assist']} | {v['ammonizioni']} |")
    righe += ["", "## Rigori calciati davvero in campionato", ""]
    tiratori = [v for v in giocatori.values() if v["rigori_segnati"] or v["rigori_sbagliati"]]
    for v in sorted(tiratori, key=lambda v: (v["squadra"], v["nome"])):
        righe.append(f"- **{v['nome']}** ({v['squadra']}): {v['rigori_segnati']} segnati, {v['rigori_sbagliati']} sbagliati")
    parati = [v for v in giocatori.values() if v["rigori_parati"]]
    for v in parati:
        righe.append(f"- parato da **{v['nome']}** ({v['squadra']}): {v['rigori_parati']}")
    totale = sum(v["rigori_segnati"] + v["rigori_sbagliati"] for v in tiratori)
    partite = len(giornate) * 10
    righe += ["", f"{totale} rigori in {partite} partite: {totale / partite:.2f} a partita, "
              f"{totale / partite / 2:.2f} a squadra per partita."]
    USCITA_MD.write_text("\n".join(righe) + "\n", encoding="utf-8")


def main():
    file = sorted(CARTELLA_FILE.glob("*.xlsx"))
    if not file:
        sys.exit(f"Nessun file in {CARTELLA_FILE}")
    per_giornata = {}
    for f in file:
        g = giornata_dal_nome(f)
        if g:
            per_giornata[g] = leggi_giornata(f)
    nomi = {}
    if LISTONE.exists():
        nomi = {g["id"]: g["n"] for g in json.load(open(LISTONE, encoding="utf-8"))["listone"] if "id" in g}
    riepilogo, giocatori = conta(per_giornata, nomi)
    squadre_per_giornata = {g: len({r["squadra"] for r in rr}) for g, rr in per_giornata.items()}
    incomplete = {g: n for g, n in squadre_per_giornata.items() if n != 20}
    USCITA_JSON.write_text(json.dumps({
        "giornate": sorted(per_giornata), "squadre_per_giornata": squadre_per_giornata,
        "squadre": riepilogo, "giocatori": sorted(giocatori.values(), key=lambda v: (v["squadra"], v["ruolo"], v["nome"])),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    scrivi_md(riepilogo, giocatori, sorted(per_giornata))
    print(f"{len(per_giornata)} giornate, {len(riepilogo)} squadre, {len(giocatori)} giocatori "
          f"→ {USCITA_JSON.relative_to(RADICE)}, {USCITA_MD.relative_to(RADICE)}")
    if incomplete:
        print(f"ATTENZIONE: giornate con meno di 20 squadre: {incomplete}")
    for sq, s in sorted(riepilogo.items(), key=lambda kv: -(kv[1]["mod_media"] or 0))[:5]:
        print(f"  {sq:<11} gol subiti {s['gol_subiti']:>2}  inviolate {s['porte_inviolate']}  "
              f"modificatore di squadra {s['mod_media']} ({s['mod_punti_medi']} punti a giornata)")


if __name__ == "__main__":
    main()
