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
    # il dossier (note e voti dalla Gazzetta) viaggia dentro il listone, in
    # forma compatta: l'app lo mostra nella scheda Dossier e nel tetto.
    dossier = RADICE / "dati" / "dossier.json"
    if dossier.exists():
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import dossier as modulo_dossier
        blocco["dossier"] = modulo_dossier.esporta(modulo_dossier.carica(), modulo_dossier.carica_listone())
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
            raise SystemExit(f"GitHub non ha accettato il file: {err or out}")
        n = len(blocco["listone"])
        print(f"\n  listone inviato: {n} giocatori, {len(blocco.get('piani', {}))} piani, "
              f"{sum(1 for v in blocco['listone'] if v.get('gz'))} con segnale Gazzetta.")
        if blocco.get("lega"):
            print(f"  con la lega: {blocco['lega'].get('lega')} · asta {blocco['lega'].get('asta_testo')} · {len(blocco['lega'].get('avversari', []))} avversari")
        print("  L'app lo prende alla prossima apertura, su tutti i dispositivi collegati.\n")
    finally:
        if precedente and precedente != UTENTE:
            gh("auth", "switch", "--user", precedente)
