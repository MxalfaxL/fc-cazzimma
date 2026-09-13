"""Le chiavi stanno nel portachiavi del Mac, non nei file e non in chat.

Regola del progetto: nessuna credenziale in un file, nemmeno in uno ignorato
da git. Il portachiavi di macOS e' il posto giusto: Marco ce la mette una
volta, gli script la leggono al momento di usarla e non la stampano mai.

Marco, per metterci la chiave di API-Football (te la chiede e non la mostra,
e cosi' non finisce nemmeno nella cronologia del terminale):

    security add-generic-password -U -a "$USER" -s fc-cazzimma-apifootball -w

Per cambiarla, lo stesso comando. Per toglierla:

    security delete-generic-password -s fc-cazzimma-apifootball

Su GitHub Actions la stessa chiave vive come segreto del repository
(API_FOOTBALL_KEY) e arriva agli script come variabile d'ambiente: per questo
qui si guarda prima l'ambiente e poi il portachiavi.
"""

import os
import subprocess
import sys

SERVIZIO = "fc-cazzimma-apifootball"
VARIABILE = "API_FOOTBALL_KEY"


def chiave(obbligatoria=True):
    """La chiave di API-Football: prima la variabile d'ambiente (Actions),
    poi il portachiavi del Mac. Non viene mai stampata."""
    dall_ambiente = os.environ.get(VARIABILE, "").strip()
    if dall_ambiente:
        return dall_ambiente
    esito = subprocess.run(["security", "find-generic-password", "-s", SERVIZIO, "-w"],
                           capture_output=True, text=True)
    valore = esito.stdout.strip()
    if valore:
        return valore
    if obbligatoria:
        sys.exit(
            "Manca la chiave di API-Football.\n"
            "Marco la mette nel portachiavi cosi' (la chiede e non la mostra):\n"
            f'  security add-generic-password -U -a "$USER" -s {SERVIZIO} -w\n'
            f"In GitHub Actions invece serve il segreto {VARIABILE}."
        )
    return None


def c_e():
    return bool(chiave(obbligatoria=False))


if __name__ == "__main__":
    k = chiave(obbligatoria=False)
    print(f"Chiave di API-Football: {'presente (' + str(len(k)) + ' caratteri)' if k else 'non impostata'}")
