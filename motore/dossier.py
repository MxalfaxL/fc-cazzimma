"""Il dossier: cosa sappiamo di ogni giocatore oltre al listone.

Il listone dice prezzi e aspettative di agosto. Da settembre in poi la
Gazzetta di ogni giorno dice cose che il listone non sa: chi gioca davvero,
chi e' rotto, chi tira i rigori, chi e' salito o sceso nelle gerarchie, che
voti sta prendendo. Ogni cosa che riguarda un giocatore diventa una nota
datata qui dentro, in dati/dossier.json (privato). Le note le scrive chi legge
le pagine estratte da leggi_gazzetta.py; questo modulo le tiene in ordine e
le ricapitola per ruolo, ed e' la base della classifica per l'asta.

Uso:
    python3 motore/dossier.py aggiungi "Malen" 2026-09-15 infortunio "Lesione al flessore, rientro a fine ottobre"
    python3 motore/dossier.py voto "Malen" 3 6.5 9.5          # giornata, voto, fantavoto (fantavoto facoltativo)
    python3 motore/dossier.py rigorista "Malen" si            # si / no / dubbio
    python3 motore/dossier.py mostra                          # tutto, per ruolo
    python3 motore/dossier.py mostra A                        # un ruolo
    python3 motore/dossier.py mostra "Malen"                  # un giocatore
    python3 motore/dossier.py cerca lauta                     # come si chiama nel listone?

Tipi di nota: infortunio, rientro, squalifica, titolare, panchina, forma,
rigorista, mercato, altro. Il nome e' quello del listone, esatto: se non
c'e', il comando lo dice e propone i somiglianti invece di inventare.
"""

import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
LISTONE = RADICE / "report" / "listone.json"
DOSSIER = RADICE / "dati" / "dossier.json"

TIPI = ("infortunio", "rientro", "squalifica", "titolare", "panchina", "forma", "rigorista", "mercato", "altro")
RUOLI = {"P": "Portieri", "D": "Difensori", "C": "Centrocampisti", "A": "Attaccanti"}
# Con una di queste note l'ultima parola sullo stato del giocatore cambia.
STATO_DA_TIPO = {"infortunio": "infortunato", "squalifica": "squalificato", "rientro": "ok", "titolare": "ok"}


def norm(t):
    return re.sub(r"[^a-z]", "", unicodedata.normalize("NFD", str(t)).encode("ascii", "ignore").decode().lower())


def carica_listone():
    if not LISTONE.exists():
        sys.exit(f"Manca {LISTONE}: prima python3 motore/listone.py")
    return {g["n"]: g for g in json.load(open(LISTONE, encoding="utf-8"))["listone"]}


def carica():
    if DOSSIER.exists():
        return json.load(open(DOSSIER, encoding="utf-8"))
    return {"aggiornato": None, "giocatori": {}}


def salva(dossier):
    dossier["aggiornato"] = date.today().isoformat()
    DOSSIER.parent.mkdir(exist_ok=True)
    json.dump(dossier, open(DOSSIER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def trova(nome, listone):
    """Il nome esatto del listone, o esce elencando i somiglianti."""
    if nome in listone:
        return nome
    chiave = norm(nome)
    simili = [n for n in listone if chiave and (chiave in norm(n) or norm(n) in chiave)]
    if len(simili) == 1:
        return simili[0]
    if simili:
        sys.exit(f"'{nome}' e' ambiguo nel listone: " + ", ".join(f"{n} ({listone[n]['sq']}, {listone[n]['r']})" for n in simili))
    sys.exit(f"'{nome}' non e' nel listone. Prova: python3 motore/dossier.py cerca {nome[:4]}")


def voce(dossier, nome):
    return dossier["giocatori"].setdefault(nome, {"stato": "ok", "rigorista": None, "voti": [], "note": []})


def aggiungi(dossier, listone, nome, data, tipo, testo, fonte="gazzetta"):
    nome = trova(nome, listone)
    if tipo not in TIPI:
        sys.exit(f"Tipo '{tipo}' sconosciuto. Uno fra: {', '.join(TIPI)}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data):
        sys.exit(f"Data '{data}' non valida: serve AAAA-MM-GG")
    v = voce(dossier, nome)
    if any(n["data"] == data and n["testo"] == testo for n in v["note"]):
        print(f"{nome}: nota gia' presente, non la ripeto")
        return
    v["note"].append({"data": data, "fonte": fonte, "tipo": tipo, "testo": testo})
    v["note"].sort(key=lambda n: n["data"])
    if tipo in STATO_DA_TIPO:
        v["stato"] = STATO_DA_TIPO[tipo]
    if tipo == "rigorista" and v["rigorista"] is None:
        v["rigorista"] = "si"
    print(f"{nome} ({listone[nome]['sq']}, {listone[nome]['r']}) · {data} · {tipo}: {testo}")


def voto(dossier, listone, nome, giornata, v, fv=None):
    nome = trova(nome, listone)
    voci = voce(dossier, nome)["voti"]
    voci[:] = [x for x in voci if x["g"] != int(giornata)]
    voci.append({"g": int(giornata), "v": float(v), "fv": float(fv) if fv is not None else None})
    voci.sort(key=lambda x: x["g"])
    print(f"{nome}: giornata {giornata} voto {v}" + (f", fantavoto {fv}" if fv is not None else ""))


def rigorista(dossier, listone, nome, valore):
    nome = trova(nome, listone)
    if valore not in ("si", "no", "dubbio"):
        sys.exit("rigorista vuole si, no o dubbio")
    voce(dossier, nome)["rigorista"] = valore
    print(f"{nome}: rigorista = {valore}")


def media(voci, chiave):
    valori = [x[chiave] for x in voci if x.get(chiave) is not None]
    return sum(valori) / len(valori) if valori else None


def riga(nome, v, g):
    mv, fm = media(v["voti"], "v"), media(v["voti"], "fv")
    pezzi = [f"{nome:<18} {g['sq']:<11} {g['r']}  qt {g['qt']:>3}  pr {g['pr']:>6.1f}"]
    pezzi.append(f"pres {len(v['voti'])}")
    pezzi.append(f"mv {mv:.2f}" if mv is not None else "mv  -  ")
    pezzi.append(f"fm {fm:.2f}" if fm is not None else "fm  -  ")
    if v["stato"] != "ok":
        pezzi.append(v["stato"].upper())
    if v["rigorista"] in ("si", "dubbio"):
        pezzi.append("RIG" if v["rigorista"] == "si" else "rig?")
    return "  ".join(pezzi)


def mostra(dossier, listone, filtro=None):
    if filtro and filtro not in RUOLI:
        nome = trova(filtro, listone)
        v = dossier["giocatori"].get(nome)
        if not v:
            print(f"{nome}: niente nel dossier, solo listone → {listone[nome]}")
            return
        print(riga(nome, v, listone[nome]))
        for n in v["note"]:
            print(f"   {n['data']}  [{n['tipo']}] {n['testo']}  ({n['fonte']})")
        if v["voti"]:
            print("   voti: " + "  ".join(f"g{x['g']} {x['v']}" + (f"/{x['fv']}" if x['fv'] is not None else "") for x in v["voti"]))
        return
    for r in ([filtro] if filtro else RUOLI):
        nomi = [n for n in dossier["giocatori"] if listone.get(n, {}).get("r") == r]
        if not nomi:
            continue
        print(f"\n== {RUOLI[r]} ({len(nomi)} nel dossier)")
        for nome in sorted(nomi, key=lambda n: -listone[n]["pr"]):
            v = dossier["giocatori"][nome]
            ultima = v["note"][-1] if v["note"] else None
            print(riga(nome, v, listone[nome]) + (f"\n      ultima: {ultima['data']} [{ultima['tipo']}] {ultima['testo']}" if ultima else ""))
    print(f"\n{len(dossier['giocatori'])} giocatori con qualcosa nel dossier, aggiornato il {dossier['aggiornato']}")


def cerca(listone, pezzo):
    chiave = norm(pezzo)
    for n, g in sorted(listone.items(), key=lambda kv: -kv[1]["pr"]):
        if chiave in norm(n):
            print(f"{n:<18} {g['sq']:<11} {g['r']}  qt {g['qt']:>3}  pr {g['pr']:>6.1f}")


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    comando, resto = argv[1], argv[2:]
    listone = carica_listone()
    dossier = carica()
    if comando == "aggiungi" and len(resto) >= 4:
        aggiungi(dossier, listone, resto[0], resto[1], resto[2], " ".join(resto[3:]))
    elif comando == "voto" and len(resto) in (3, 4):
        voto(dossier, listone, *resto)
    elif comando == "rigorista" and len(resto) == 2:
        rigorista(dossier, listone, *resto)
    elif comando == "mostra":
        mostra(dossier, listone, resto[0] if resto else None)
        return
    elif comando == "cerca" and resto:
        cerca(listone, resto[0])
        return
    else:
        sys.exit(__doc__)
    salva(dossier)


if __name__ == "__main__":
    main(sys.argv)
