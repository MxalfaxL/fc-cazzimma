"""Manda report/listone.json all'app, scrivendolo nel repository privato dei dati.

E' l'unica scrittura consentita dal Mac verso fc-cazzimma-dati, e riguarda solo
il file listone.json: l'app lo legge e lo prende se e' piu' recente del suo.
stato.json, che contiene la rosa e tutto il resto, non si tocca mai da qui:
ci scrive solo l'app.

Serve gh autenticato con l'account personale. Se il default e' un altro
account, lo script passa a quello giusto e poi torna indietro.

Uso:
    python3 motore/invia_listone.py
"""

import base64
import json
import subprocess
import sys
import time
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
LISTONE = RADICE / "report" / "listone.json"
UTENTE = "MxalfaxL"
REPO = "fc-cazzimma-dati"
FILE_REMOTO = "listone.json"


def gh(*argomenti, corpo=None):
    comando = ["gh", *argomenti]
    esito = subprocess.run(comando, input=corpo, capture_output=True, text=True)
    return esito.returncode, esito.stdout.strip(), esito.stderr.strip()


def invia_con_git(contenuto, messaggio):
    """Strada di riserva: blob, albero, commit e ramo con l'API git. Il 7/10/2026
    l'API dei contenuti rispondeva 500 (vuoto) su listone.json per ore, con
    GitHub 'tutto operativo'. Cambia solo listone.json: l'albero parte da
    quello attuale, quindi stato.json resta come l'ha scritto l'app."""
    base = f"repos/{UTENTE}/{REPO}"

    def chiama(metodo, percorso, dati=None):
        argomenti = ["api", "-X", metodo, f"{base}/{percorso}"] + (["--input", "-"] if dati is not None else [])
        codice, out, err = gh(*argomenti, corpo=json.dumps(dati) if dati is not None else None)
        if codice != 0:
            raise SystemExit(f"GitHub non ha accettato il file nemmeno con l'API git ({metodo} {percorso}): {err or out}")
        return json.loads(out)

    _, ramo, _ = gh("api", base, "--jq", ".default_branch")
    blob = chiama("POST", "git/blobs", {"content": contenuto, "encoding": "base64"})["sha"]
    testa = chiama("GET", f"git/ref/heads/{ramo}")["object"]["sha"]
    albero_base = chiama("GET", f"git/commits/{testa}")["tree"]["sha"]
    albero = chiama("POST", "git/trees", {"base_tree": albero_base, "tree": [
        {"path": FILE_REMOTO, "mode": "100644", "type": "blob", "sha": blob}]})["sha"]
    commit = chiama("POST", "git/commits", {"message": messaggio, "tree": albero, "parents": [testa]})["sha"]
    # senza force: se l'app ha appena scritto stato.json fallisce, e si rilancia
    chiama("PATCH", f"git/refs/heads/{ramo}", {"sha": commit})


def account_attivo():
    _, out, _ = gh("api", "user", "--jq", ".login")
    return out


if __name__ == "__main__":
    if not LISTONE.exists():
        raise SystemExit("Manca report/listone.json: prima lancia motore/listone.py.")
    blocco = json.loads(LISTONE.read_text(encoding="utf-8"))
    if not blocco.get("listone"):
        raise SystemExit("Il listone e' vuoto.")
    # la lega (nome, data dell'asta, cognomi degli avversari) sta in un file
    # privato e viaggia dentro il listone: l'app rinomina gli avversari che
    # hanno ancora il nome di default. Cosi' i cognomi non finiscono nel codice.
    lega = RADICE / "dati" / "lega.json"
    if lega.exists():
        blocco["lega"] = json.loads(lega.read_text(encoding="utf-8"))
        blocco["lega"].pop("_cosa_e", None)
    # il dossier (note e voti dai giornali) viaggia dentro il listone, in
    # forma compatta e con il consiglio della classifica: l'app lo mostra
    # nella scheda Analisi e nel tetto d'asta.
    dossier = RADICE / "dati" / "dossier.json"
    if dossier.exists():
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import classifica_asta
        _, _, blocco["dossier"] = classifica_asta.genera()
    # le righe di strategia per reparto (dipendono dal piano scelto e citano
    # prezzi: per questo stanno in un file privato e non nel codice)
    consigli = RADICE / "dati" / "consigli-asta.json"
    if consigli.exists():
        blocco["consigli"] = json.loads(consigli.read_text(encoding="utf-8"))
        blocco["consigli"].pop("_cosa_e", None)
    # la fascia della guida SOS Fanta: e' dove gli altri nove fanno l'ancora
    guida = RADICE / "dati" / "guida-asta-sosfanta.json"
    if guida.exists():
        fasce = {v["nome"]: v["fascia"] for v in json.loads(guida.read_text(encoding="utf-8"))["giocatori"] if v.get("fascia")}
        for g in blocco["listone"]:
            if g["n"] in fasce:
                g["sos"] = fasce[g["n"]]
    # i dati della settimana (fantavoto, voto, stato di ogni giocatore della
    # rosa per la giornata in corso) non si incollano piu' a mano: viaggiano
    # qui dentro e l'app li applica da sola quando sono piu' recenti
    # (decisione di Marco del 10/10/2026: "lo fai tu e li salvi tu")
    settimana = RADICE / "report" / "settimana.json"
    if settimana.exists():
        blocco["settimana"] = json.loads(settimana.read_text(encoding="utf-8"))
    # il marcatore di tempo e' quello che l'app confronta: piu' recente vince
    blocco["caricato"] = int(time.time() * 1000)
    contenuto = base64.b64encode(json.dumps(blocco, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).decode("ascii")

    precedente = account_attivo()
    if precedente != UTENTE:
        codice, _, err = gh("auth", "switch", "--user", UTENTE)
        if codice != 0:
            raise SystemExit(f"Non riesco a passare all'account {UTENTE}: {err}")
    try:
        # sha del file esistente, se c'e': GitHub lo vuole per sovrascrivere
        codice, out, _ = gh("api", f"repos/{UTENTE}/{REPO}/contents/{FILE_REMOTO}", "--jq", ".sha")
        sha = out if codice == 0 else None
        corpo = {"message": f"listone dal Mac — {time.strftime('%Y-%m-%d %H:%M')}", "content": contenuto}
        if sha:
            corpo["sha"] = sha
        codice, out, err = gh("api", "-X", "PUT", f"repos/{UTENTE}/{REPO}/contents/{FILE_REMOTO}", "--input", "-",
                              corpo=json.dumps(corpo))
        if codice != 0:
            print(f"  l'API dei contenuti ha rifiutato il file ({err or out}): riprovo con l'API git")
            invia_con_git(contenuto, corpo["message"])
        n = len(blocco["listone"])
        print(f"\n  listone inviato: {n} giocatori, {len(blocco.get('piani', {}))} piani, "
              f"{sum(1 for v in blocco['listone'] if v.get('gz'))} con segnale Gazzetta.")
        if blocco.get("lega"):
            print(f"  con la lega: {blocco['lega'].get('lega')} · asta {blocco['lega'].get('asta_testo')} · {len(blocco['lega'].get('avversari', []))} avversari")
        if blocco.get("settimana"):
            print(f"  con i dati della giornata {blocco['settimana'].get('giornata')}: {len(blocco['settimana'].get('giocatori', []))} giocatori")
        print("  L'app lo prende alla prossima apertura, su tutti i dispositivi collegati.\n")
    finally:
        if precedente and precedente != UTENTE:
            gh("auth", "switch", "--user", precedente)
