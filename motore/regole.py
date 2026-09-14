"""Le regole della lega, in un posto solo.

Se lo staff cambia qualcosa nel regolamento, si tocca solo questo file
e tutto il resto del motore si adegua.
"""

# --- asta ---
BUDGET = 500
SLOT = {"P": 3, "D": 8, "C": 8, "A": 6}
SQUADRE_PER_LEGA = 10

# --- moduli schierabili: (difensori, centrocampisti, attaccanti) ---
MODULI = {
    "3-4-3": (3, 4, 3),
    "3-5-2": (3, 5, 2),
    "4-3-3": (4, 3, 3),
    "4-4-2": (4, 4, 2),
    "4-5-1": (4, 5, 1),
    "5-4-1": (5, 4, 1),
    "5-3-2": (5, 3, 2),
}

SOSTITUZIONI = 5
SOGLIA_PRIMO_GOL = 66
AMPIEZZA_FASCIA = 4

# --- bonus e malus ---
# Il regolamento della lega non li elenca: al punto 9 dice che "l'applicazione
# fa tutto automaticamente", quindi valgono quelli standard di Leghe
# Fantacalcio. Le chiavi sono le colonne del file dei voti ufficiali.
# Attenzione a Rf: nel file di Fantacalcio.it il rigore segnato NON e' dentro
# Gf, e' una colonna a parte (verificato sul rigore di Maldini alla 4ª, Gf 0 e
# Rf 1). Sommarli tutti e due e' giusto, considerarlo compreso nei gol
# toglierebbe 3 punti a ogni rigorista.
BONUS = {
    "Gf": 3.0,      # gol su azione
    "Rf": 3.0,      # rigore segnato
    "Ass": 1.0,     # assist
    "Rp": 3.0,      # rigore parato (portieri)
    "Rs": -3.0,     # rigore sbagliato
    "Au": -2.0,     # autogol
    "Amm": -0.5,    # ammonizione
    "Esp": -1.0,    # espulsione
    "Gs": -1.0,     # gol subito (conta solo per i portieri)
}


def fantavoto(voto, eventi, ruolo):
    """Voto piu' bonus e malus, come li conta la lega. `eventi` e' il
    dizionario delle colonne del file ufficiale (Gf, Gs, Rp, ...). I gol
    subiti pesano solo sul portiere: un difensore non perde punti perche' la
    sua squadra ha preso gol."""
    totale = float(voto)
    for chiave, peso in BONUS.items():
        if chiave == "Gs" and ruolo != "P":
            continue
        totale += peso * float(eventi.get(chiave) or 0)
    return round(totale, 2)

# --- modificatore difesa: (soglia superiore esclusa, punti) ---
FASCE_MODIFICATORE = [(6.00, 0), (6.25, 1), (6.50, 2), (6.75, 3), (7.00, 4)]
MODIFICATORE_MAX = 5
DIFENSORI_MINIMI_PER_MODIFICATORE = 4


def modificatore_difesa(voto_portiere, voti_difensori):
    """Punti extra dal modificatore.

    Si attiva con 4 o piu' difensori schierati. Fa la media fra il voto puro
    del portiere e quelli dei 3 migliori difensori schierati.
    Restituisce (punti, media). Con meno di 4 difensori: (0, None).
    """
    if len(voti_difensori) < DIFENSORI_MINIMI_PER_MODIFICATORE:
        return 0, None
    migliori = sorted(voti_difensori, reverse=True)[:3]
    media = (voto_portiere + sum(migliori)) / 4
    for soglia, punti in FASCE_MODIFICATORE:
        if media <= soglia:
            return punti, media
    return MODIFICATORE_MAX, media


def gol_da_punti(punti):
    """Fasce gol fisse ogni 4 punti a partire da 66."""
    if punti < SOGLIA_PRIMO_GOL:
        return 0
    return int((punti - SOGLIA_PRIMO_GOL) // AMPIEZZA_FASCIA) + 1


def punti_per_gol_successivo(punti):
    """Quanti punti mancano al gol successivo. Utile per capire se vale la pena
    rischiare un attaccante in piu' o blindare il modificatore."""
    if punti < SOGLIA_PRIMO_GOL:
        return round(SOGLIA_PRIMO_GOL - punti, 2)
    prossima = SOGLIA_PRIMO_GOL + (gol_da_punti(punti)) * AMPIEZZA_FASCIA
    return round(prossima - punti, 2)
