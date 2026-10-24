"""La Conferma della formazione, dal Mac, quando Marco lo chiede.

Nell'app c'e' il tasto "Conferma: questa l'ho mandata": mette la formazione
della giornata in `stato.formazioni[N]` dentro stato.json, ed e' da li' che
`punteggio_giornata.py` fa i conti del lunedi'. Quando Marco non ha il
telefono in mano puo' chiedere di farlo da qui (regola sua del 24/10/2026):
SOLO su sua richiesta esplicita, mai di iniziativa.

E' l'unica scrittura su stato.json che parte dal Mac, quindi tocca il meno
possibile: la sola voce `formazioni[N]` e il contatore `v`, che sale di uno
cosi' l'app, alla prossima apertura, prende la versione del cloud. La scrittura
porta lo sha letto un attimo prima: se nel frattempo l'app ha scritto, GitHub
risponde 409/422 e qui ci si ferma senza toccare niente.

Il rischio che resta: un telefono con modifiche locali mai sincronizzate (e
quindi un `v` piu' alto) al primo collegamento rimanda la sua copia e la
conferma fatta da qui sparisce. Per questo, dopo, si dice a Marco di aprire
l'app e guardare Stagione -> Le mie giornate.

La formazione sta in `dati/formazioni/giornata-NN.json` (privato), nella forma
che usa l'app: {"formazioni": {"N": {"modulo", "totale", "mod", "undici":
[{"n", "r", "sq"}], "panchina": [{"n", "r"}]}}}.

Uso:
    python3 motore/conferma_formazione.py 8          # prova: dice cosa scriverebbe
    python3 motore/conferma_formazione.py 8 --vai    # scrive davvero
"""

import base64
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE / "motore"))
from punteggio_giornata import UTENTE, RIENTRO, REPO, gh  # noqa: E402



def leggi_formazione(giornata):
    percorso = RADICE / "dati" / "formazioni" / f"giornata-{giornata:02d}.json"
    if not percorso.exists():
        sys.exit(f"Non trovo {percorso.relative_to(RADICE)}: scrivi li' la formazione mandata.")
    dati = json.loads(percorso.read_text(encoding="utf-8"))
    voce = (dati.get("formazioni") or {}).get(str(giornata))
    if not voce:
        sys.exit(f"In {percorso.name} manca formazioni[\"{giornata}\"].")
    controlla(voce)
    return voce


def controlla(voce):
    """Undici da 11 col modulo giusto e nessuno due volte: una conferma storta
    rovina i conti del lunedi' senza che nessuno se ne accorga."""
    undici, panchina = voce.get("undici") or [], voce.get("panchina") or []
    if len(undici) != 11:
        sys.exit(f"L'undici ha {len(undici)} giocatori, non 11.")
    conta = {r: sum(1 for x in undici if x["r"] == r) for r in "PDCA"}
    atteso = [int(c) for c in voce["modulo"].split("-")]
    if conta["P"] != 1 or [conta["D"], conta["C"], conta["A"]] != atteso:
        sys.exit(f"L'undici non torna col {voce['modulo']}: {conta}.")
    nomi = [x["n"] for x in undici + panchina]
    doppi = {n for n in nomi if nomi.count(n) > 1}
    if doppi:
        sys.exit(f"Giocatori ripetuti: {', '.join(sorted(doppi))}.")


def leggi_remoto():
    esito = gh("api", f"repos/{UTENTE}/{REPO}/contents/stato.json")
    if esito.returncode != 0:
        sys.exit(f"Non riesco a leggere stato.json: {esito.stderr.strip() or esito.stdout.strip()}")
    pacco = json.loads(esito.stdout)
    return json.loads(base64.b64decode(pacco["content"])), pacco["sha"]


def scrivi_remoto(stato, sha, messaggio):
    corpo = {"message": messaggio, "sha": sha,
             "content": base64.b64encode(json.dumps(stato, ensure_ascii=False, indent=1).encode()).decode()}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(corpo, f)
    esito = gh("api", "-X", "PUT", f"repos/{UTENTE}/{REPO}/contents/stato.json", "--input", f.name)
    Path(f.name).unlink()
    if esito.returncode != 0:
        sys.exit("Scrittura rifiutata (se e' 409/422 l'app ha scritto nel frattempo: niente e' cambiato, "
                 f"rilancia): {esito.stderr.strip() or esito.stdout.strip()}")


def riassunto(voce):
    righe = [f"  {voce['modulo']} · {voce.get('totale')} attesi · mod {voce.get('mod')}"]
    for r in "PDCA":
        righe.append(f"  {r}: " + ", ".join(x["n"] for x in voce["undici"] if x["r"] == r))
    righe.append("  panchina: " + ", ".join(f"{i}. {x['n']}" for i, x in enumerate(voce.get("panchina") or [], 1)))
    return "\n".join(righe)


def main(argv):
    if not argv or not argv[0].isdigit():
        sys.exit("Uso: python3 motore/conferma_formazione.py N [--vai]")
    giornata, vai = int(argv[0]), "--vai" in argv
    voce = leggi_formazione(giornata)
    try:
        cambio = gh("auth", "switch", "--user", UTENTE)
        if cambio.returncode != 0:
            sys.exit(f"Non riesco a passare all'account {UTENTE}: {cambio.stderr.strip()}")
        stato, sha = leggi_remoto()
        gia = (stato.get("formazioni") or {}).get(str(giornata))
        print(f"stato.json v{stato.get('v')}, giornata dell'app {stato.get('giornata')}.")
        print(f"Giornata {giornata} nel cloud: " + ("gia' confermata:\n" + riassunto(gia) if gia else "non confermata."))
        print("Da confermare:\n" + riassunto(voce))
        if not vai:
            print("\nProva: non ho scritto niente. Con --vai scrivo (solo su richiesta di Marco).")
            return
        nuova = dict(voce, quando=int(time.time() * 1000))
        stato.setdefault("formazioni", {})[str(giornata)] = nuova
        stato["v"] = (stato.get("v") or 0) + 1
        scrivi_remoto(stato, sha, f"conferma giornata {giornata} dal Mac, su richiesta di Marco — v{stato['v']}")
        controllo, _ = leggi_remoto()
        if (controllo.get("formazioni") or {}).get(str(giornata)) != nuova:
            sys.exit("Scritto, ma rileggendo la voce non torna: guardare stato.json a mano.")
        print(f"\nConfermata la giornata {giornata}: stato.json ora e' v{controllo['v']}, riletto e uguale.")
        print("Marco: apri l'app e guarda Stagione -> Le mie giornate.")
    finally:
        gh("auth", "switch", "--user", RIENTRO)


if __name__ == "__main__":
    main(sys.argv[1:])
