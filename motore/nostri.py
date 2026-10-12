"""I nostri 25, squadra per squadra: chi gioca la prossima giornata e perche'.

Dal 12 ottobre 2026 (regola di Marco) il giro delle fonti guarda soprattutto
le squadre in cui FC Cazzimma ha giocatori: e' li' che si decide la
formazione. I lettori scrivono nel loro note.json, oltre alle note del
dossier, due campi in piu':
  "nostri":  [{nome, squadra, stato, testo, file|pagina|fonte}]
             cosa dice la fonte di un nostro giocatore per la prossima
             partita, o come ha giocato se e' una cronaca;
  "squadre": {squadra: "modulo, parole del tecnico, ballottaggi"}.
Questo modulo li raccoglie da tutte le cartelle lette negli ultimi giorni
(giornale, feed, pagine web), ci affianca gli ultimi voti e le note del
dossier, e mette tutto in fila nell'ordine in cui le nostre squadre giocano
la prossima giornata. E' il foglio da cui partono le stime di dati/rosa.json
(PROCEDURE 2quinquies): prima si legge questo, poi si decide.

Uso:
    python3 motore/nostri.py               # prossima giornata, fonti degli ultimi 7 giorni
    python3 motore/nostri.py 7 --giorni 4  # una giornata precisa, finestra piu' stretta

Scrive report/NOSTRI.md (privato: dentro ci sono rosa e prezzi pagati).
"""

import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
ROSA = RADICE / "dati" / "rosa-2026-27.json"
CALENDARIO = RADICE / "dati" / "calendario-2026-27.json"
DOSSIER = RADICE / "dati" / "dossier.json"
CARTELLE = [RADICE / "dati" / "gazzetta", RADICE / "dati" / "sosfanta", RADICE / "dati" / "fonti"]
USCITA = RADICE / "report" / "NOSTRI.md"

GIORNI_SETTIMANA = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
ORDINE_RUOLI = {"P": 0, "D": 1, "C": 2, "A": 3}
# Quante righe per giocatore: oltre, il foglio non si legge piu' in cinque minuti.
MAX_NOSTRI = 6
MAX_DOSSIER = 4
MAX_SQUADRA = 4
TIPI_DOSSIER = ("infortunio", "rientro", "squalifica", "titolare", "panchina", "rigorista", "mercato")


def prossima_giornata(calendario, oggi):
    """La prima giornata che non e' ancora cominciata, o che comincia oggi:
    la formazione si chiude 15' prima del primo fischio, quindi il giorno
    dell'anticipo e' ancora tempo di decidere."""
    for g in calendario["giornate"]:
        if min(g["date"]) >= oggi.isoformat():
            return g
    sys.exit("Nel calendario non ci sono giornate future: va allungato dati/calendario-2026-27.json")


def ora_del_file(cartella, nome_file):
    """L'ora di un articolo del feed, dall'intestazione DATA: serve a mettere in
    fila due notizie dello stesso giorno (la probabile del mattino e
    l'ufficiale del pomeriggio dicono cose diverse)."""
    p = cartella / nome_file
    if p.exists():
        for riga in p.read_text(encoding="utf-8").split("\n")[:4]:
            m = re.match(r"DATA:\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", riga)
            if m:
                return m.group(1)
    return None


def riferimento(voce, fonte):
    if voce.get("pagina"):
        return f"{fonte} p.{voce['pagina']}"
    if voce.get("file"):
        return f"{fonte} {voce['file'][:3]}"
    return voce.get("fonte") or fonte


def raccogli(dal):
    """Le voci "nostri" e "squadre" di tutte le cartelle lette dal giorno `dal`."""
    nostri, squadre, lette = defaultdict(list), defaultdict(list), []
    for radice in CARTELLE:
        if not radice.exists():
            continue
        for cartella in sorted(radice.iterdir()):
            if not (cartella.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", cartella.name)):
                continue
            if cartella.name < dal:
                continue
            for f in sorted(cartella.glob("note*.json")):
                try:
                    dati = json.load(open(f, encoding="utf-8"))
                except json.JSONDecodeError:
                    print(f"ATTENZIONE: {f} non e' JSON valido, saltato")
                    continue
                fonte = dati.get("fonte", radice.name)
                giorno = dati.get("data", cartella.name)
                quando_file = (dati.get("letto_alle") or f"{giorno} 06:00")[:16]
                if "nostri" in dati or "squadre" in dati:
                    lette.append(f"{cartella.name} {fonte} {f.stem}")
                for v in dati.get("nostri", []):
                    # una pagina web letta oggi puo' riportare una tabella di due giorni fa:
                    # conta la data della notizia ("data" della voce), non quella della lettura
                    quando = (v.get("data") or (ora_del_file(cartella, v["file"]) if v.get("file") else None)
                              or quando_file)
                    if len(quando) == 10:
                        quando += " 12:00"
                    nostri[v.get("nome", "")].append({
                        "quando": quando, "stato": v.get("stato", ""), "testo": v.get("testo", ""),
                        "rif": riferimento(v, fonte)})
                for sq, testo in (dati.get("squadre") or {}).items():
                    squadre[sq].append({"quando": quando_file, "testo": testo, "rif": fonte})
    return nostri, squadre, lette


def giorno_breve(iso):
    d = date.fromisoformat(iso[:10])
    return f"{GIORNI_SETTIMANA[d.weekday()]} {d.day}/{d.month}"


def voti_brevi(scheda):
    """Gli ultimi tre voti nella scala della lega (Leghe), il piu' recente primo."""
    voti = [v for v in scheda.get("voti", []) if v.get("f") == "leghe"][-3:]
    return ", ".join(f"{v['g']}ª {str(v['v']).replace('.', ',')}" for v in reversed(voti)) or "nessun voto"


def main():
    argomenti = sys.argv[1:]
    giorni = 7
    if "--giorni" in argomenti:
        i = argomenti.index("--giorni")
        giorni = int(argomenti[i + 1])
        del argomenti[i:i + 2]
    oggi = date.today()
    calendario = json.load(open(CALENDARIO, encoding="utf-8"))
    if argomenti:
        numero = int(argomenti[0])
        giornata = next((g for g in calendario["giornate"] if g["giornata"] == numero), None)
        if not giornata:
            sys.exit(f"La {numero}ª non e' nel calendario")
    else:
        giornata = prossima_giornata(calendario, oggi)
    rosa = json.load(open(ROSA, encoding="utf-8"))["rosa"]
    dossier = json.load(open(DOSSIER, encoding="utf-8"))["giocatori"] if DOSSIER.exists() else {}
    dal = (oggi - timedelta(days=giorni)).isoformat()
    nostri, squadre, lette = raccogli(dal)

    partita_di = {}
    for p in giornata["partite"]:
        partita_di[p["casa"]] = (p["data"], f"{p['casa']}-{p['trasferta']}", "casa")
        partita_di[p["trasferta"]] = (p["data"], f"{p['casa']}-{p['trasferta']}", "fuori")
    per_squadra = defaultdict(list)
    for g in rosa:
        per_squadra[g["squadra"]].append(g)
    senza_partita = [sq for sq in per_squadra if sq not in partita_di]
    nomi_rosa = {g["nome"] for g in rosa}
    estranei = sorted(n for n in nostri if n not in nomi_rosa)

    righe = [f"# I nostri verso la {giornata['giornata']}ª giornata "
             f"({giorno_breve(min(giornata['date']))} - {giorno_breve(max(giornata['date']))})", "",
             f"_Generato il {datetime.now():%d/%m/%Y alle %H:%M} da `motore/nostri.py`. "
             f"Fonti dal {giorno_breve(dal)}: {len(lette)} letture con il campo \"nostri\". "
             "Ultima voce in alto; lo stato e' quello scritto dalla fonte, non una stima._", ""]
    if senza_partita:
        righe += [f"**ATTENZIONE**: squadre senza partita nel calendario: {', '.join(senza_partita)}.", ""]
    if estranei:
        righe += [f"**ATTENZIONE**: voci \"nostri\" con un nome che non e' in rosa (lettore da correggere): "
                  f"{', '.join(estranei)}.", ""]

    # il colpo d'occhio: un giocatore per riga, l'ultima parola della fonte
    righe += ["| Gioca | Partita | Giocatore | Ultimi voti | Ultima parola |", "|---|---|---|---|---|"]
    # le due squadre della stessa partita stanno vicine, anche se in ordine alfabetico sono lontane
    ordine = sorted(per_squadra, key=lambda sq: (*partita_di.get(sq, ("9999", "?"))[:2], sq))
    for sq in ordine:
        quando, partita, _ = partita_di.get(sq, ("", "?", ""))
        for g in sorted(per_squadra[sq], key=lambda g: ORDINE_RUOLI[g["ruolo"]]):
            voci = sorted(nostri.get(g["nome"], []), key=lambda v: v["quando"], reverse=True)
            ultima = f"{voci[0]['stato']} ({giorno_breve(voci[0]['quando'])})" if voci else "—"
            righe.append(f"| {giorno_breve(quando) if quando else '?'} | {partita} | {g['nome']} ({g['ruolo']}) "
                         f"| {voti_brevi(dossier.get(g['nome'], {}))} | {ultima} |")
    righe.append("")

    for sq in ordine:
        quando, partita, campo = partita_di.get(sq, ("", "?", ""))
        righe += [f"## {sq} — {partita}, {giorno_breve(quando) if quando else '?'} ({campo})", ""]
        for v in sorted(squadre.get(sq, []), key=lambda v: v["quando"], reverse=True)[:MAX_SQUADRA]:
            righe.append(f"- _{giorno_breve(v['quando'])} · {v['rif']}_ — {v['testo']}")
        if squadre.get(sq):
            righe.append("")
        for g in sorted(per_squadra[sq], key=lambda g: ORDINE_RUOLI[g["ruolo"]]):
            scheda = dossier.get(g["nome"], {})
            stato = scheda.get("stato", "ok")
            righe.append(f"**{g['nome']}** ({g['ruolo']}, pagato {g['pagato']}) · voti: {voti_brevi(scheda)}"
                         + (f" · **dossier: {stato}**" if stato != "ok" else ""))
            for v in sorted(nostri.get(g["nome"], []), key=lambda v: v["quando"], reverse=True)[:MAX_NOSTRI]:
                quando = date.fromisoformat(v["quando"][:10])
                righe.append(f"- {quando.day}/{quando.month} {v['quando'][11:16]} · {v['rif']} · **{v['stato']}** — {v['testo']}")
            # dal dossier solo le note che cambiano lo stato o la gerarchia: le altre
            # ripetono quasi sempre le voci "nostri" appena sopra
            recenti = [n for n in scheda.get("note", []) if n["data"] >= dal and n["tipo"] in TIPI_DOSSIER]
            for n in sorted(recenti, key=lambda n: n["data"], reverse=True)[:MAX_DOSSIER]:
                righe.append(f"- _dossier {giorno_breve(n['data'])} · {n['tipo']}_ — {n['testo']}")
            righe.append("")

    USCITA.parent.mkdir(exist_ok=True)
    USCITA.write_text("\n".join(righe), encoding="utf-8")
    con_voci = sum(1 for g in rosa if nostri.get(g["nome"]))
    print(f"{giornata['giornata']}ª giornata: {con_voci}/{len(rosa)} dei nostri hanno voci delle fonti "
          f"dal {dal} ({len(lette)} letture). Scritto {USCITA.relative_to(RADICE)}")
    for nome in estranei:
        print(f"  nome non in rosa nelle voci 'nostri': {nome}")


if __name__ == "__main__":
    main()
