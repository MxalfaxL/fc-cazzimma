"""Costruisce il listone d'asta per FC Cazzimma.

Il file ufficiale dà due numeri per giocatore: la quotazione (Qt.A), che è un
listino, e l'FVM, che è la stima di mercato. Fanno due lavori diversi e qui
vengono usati per due cose diverse.

L'FVM decide **come si divide il budget fra i reparti**: sommato per ruolo dice
che in una lega da 10 squadre si spendono in media 32 crediti di portieri, 96
di difensori, 179 di centrocampisti e 194 di attaccanti. È l'informazione buona
dell'FVM, e nessuna quotazione la contiene.

La quotazione decide **i prezzi dentro il reparto**, corretta per il valore sul
sostituto: si comprano 30 portieri, 80 difensori, 80 centrocampisti e 60
attaccanti, quindi un giocatore vale quanto rende in più del primo che
resterebbe libero. L'FVM qui non serve perché è troppo ripido in cima: dà
Dimarco a 130 crediti, che non è un prezzo, è un abbaglio.

Sopra ci va il premio del modificatore difesa, che è la regola vostra e che
nessun listone in circolazione considera.

Il risultato e' un solo file, report/listone.json, con dentro i prezzi di
mercato e il tetto di tutti e quattro i piani per ogni giocatore: l'app lo
legge una volta e in asta si cambia piano con un tocco.

Uso:
    python3 motore/listone.py dati/Quotazioni_Fantacalcio_Stagione_2026_27.xlsx
    python3 motore/listone.py dati/listone.xlsx --piano difesa     # stampa solo quel piano
    python3 motore/listone.py dati/listone.xlsx --tutti            # stampa tutti i piani

I piani di spesa stanno in dati/piani.json, fuori dal codice pubblico.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from regole import BUDGET, SLOT, SQUADRE_PER_LEGA

DRAFTATI = {r: SLOT[r] * SQUADRE_PER_LEGA for r in SLOT}

# quanto dell'FVM entra nei prezzi dentro il reparto.
# 0 = solo quotazione. Calibrato a 0 perche' con l'FVM i prezzi in cima
# escono fuori scala rispetto a quello che si paga davvero all'asta.
MISCELA_FVM = 0.0

# il modificatore vale fino a 5 punti a giornata: questa quota del valore del
# reparto viene spostata verso chi lo alimenta
QUOTA_MODIFICATORE = 0.14
PESO_MOD = {"P": 1.0, "D": 0.55}   # il portiere entra sempre, dei difensori contano i 3 migliori

# I piani di spesa sono una scelta personale e non stanno nel codice, che e'
# pubblico: si leggono da dati/piani.json (che git ignora). Senza quel file
# si usa l'esempio neutro, e lo si dice forte.
def carica_piani():
    for nome in ("piani.json", "piani-esempio.json"):
        percorso = RADICE / "dati" / nome
        if percorso.exists():
            dati = json.loads(percorso.read_text(encoding="utf-8"))
            piani = dati.get("piani", dati)
            for nome_piano, ob in piani.items():
                if set(ob) != set(SLOT) or sum(ob.values()) != BUDGET:
                    raise SystemExit(f"Piano '{nome_piano}' in {percorso.name}: deve avere P, D, C, A e sommare a {BUDGET}.")
            if nome != "piani.json":
                print("  ATTENZIONE: manca dati/piani.json, uso i piani di esempio (solo il mercato).")
            return piani
    raise SystemExit("Manca dati/piani.json e anche dati/piani-esempio.json.")


PIANI = carica_piani()

ALIAS = {
    "nome": ["nome", "giocatore", "calciatore", "player"],
    "squadra": ["squadra", "team", "club"],
    "ruolo": ["r", "ruolo", "ruolo classic"],
    "qt": ["qta", "qt", "quotazione", "qti", "quotazione attuale"],
    "fvm": ["fvm", "fantavalore"],
}


# --------------------------------------------------------------- lettura file
def _pulisci(t):
    return re.sub(r"[^a-z ]", "", str(t).strip().lower()).strip()


def _riconosci(colonne):
    """Associa le colonne del file a quelle che ci servono senza dare per
    scontata la posizione: il formato cambia ogni anno."""
    mappa = {}
    for chiave, possibili in ALIAS.items():
        for c in colonne:
            if _pulisci(c) in possibili and chiave not in mappa:
                mappa[chiave] = c
    return mappa


def leggi(percorso):
    percorso = Path(percorso)
    if percorso.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        fogli = pd.read_excel(percorso, sheet_name=None, header=None)
        candidati = []
        for nome, foglio in fogli.items():
            if "cedut" in nome.lower():
                continue          # chi ha lasciato la Serie A non si compra
            for riga in range(min(6, len(foglio))):
                prova = foglio.iloc[riga + 1:].copy()
                prova.columns = [str(x) for x in foglio.iloc[riga]]
                mappa = _riconosci(prova.columns)
                candidati.append((len(mappa), len(prova), prova, mappa))
        candidati.sort(key=lambda x: (x[0], x[1]), reverse=True)
        if not candidati or candidati[0][0] < 3:
            raise SystemExit("Non ho riconosciuto le colonne. Servono almeno "
                             "nome, ruolo e quotazione.")
        _, _, df, mappa = candidati[0]
    else:
        df = pd.read_csv(percorso, sep=None, engine="python")
        mappa = _riconosci(df.columns)

    mancanti = {"nome", "ruolo", "qt"} - set(mappa)
    if mancanti:
        raise SystemExit(f"Nel file mancano: {', '.join(sorted(mancanti))}. "
                         f"Colonne viste: {list(df.columns)[:14]}")

    out = pd.DataFrame({
        "nome": df[mappa["nome"]].astype(str).str.strip(),
        "squadra": (df[mappa["squadra"]].astype(str).str.strip()
                    if "squadra" in mappa else ""),
        "ruolo": df[mappa["ruolo"]].astype(str).str.strip().str.upper().str[0],
        "qt": pd.to_numeric(df[mappa["qt"]], errors="coerce"),
    })
    out["fvm"] = (pd.to_numeric(df[mappa["fvm"]], errors="coerce")
                  if "fvm" in mappa else out["qt"])
    out = out[out["ruolo"].isin(list(SLOT))]
    out = out[out["qt"].notna()]
    out = out[~out["nome"].isin(["", "nan", "None"])]
    out["fvm"] = out["fvm"].fillna(out["qt"])
    return out.drop_duplicates(subset=["nome", "ruolo"]).reset_index(drop=True)


def controlla(df):
    """Il modello ha senso solo su un listone completo: se mancano i giocatori
    sotto la soglia di acquisto, il sostituto non esiste e i prezzi schizzano."""
    return [f"{r}: {int((df['ruolo'] == r).sum())} nel file, "
            f"ne servirebbero almeno {int(DRAFTATI[r] * 1.3)}"
            for r in SLOT
            if int((df["ruolo"] == r).sum()) < int(DRAFTATI[r] * 1.3)]


# ------------------------------------------------------------------- modello
def solidita_difensiva(df):
    """Quanto ci si aspetta che una squadra tenga la porta inviolata.

    Il portiere non fa bonus: la sua quotazione e' quasi tutta aspettativa di
    porta inviolata, quindi il portiere piu' caro di una squadra dice quanto il
    mercato si fida della sua difesa. Approssimazione dichiarata, da sostituire
    con le medie voto vere appena avremo le statistiche.
    """
    portieri = df[df["ruolo"] == "P"]
    if portieri.empty or (portieri["squadra"].astype(str) == "").all():
        return {}
    massimi = portieri.groupby("squadra")["qt"].max()
    lo, hi = massimi.min(), massimi.max()
    if hi <= lo:
        return {s: 0.5 for s in massimi.index}
    return {s: (v - lo) / (hi - lo) for s, v in massimi.items()}


def calcola(df, piano="equilibrio", miscela=MISCELA_FVM):
    df = df.copy()
    obiettivi = PIANI[piano]

    # 1. valore base dentro il reparto
    df["base"] = (df["qt"] ** (1 - miscela)) * (df["fvm"] ** miscela)

    # 2. chi verra' comprato, e quanto vale il primo che resterebbe libero
    df["comprato"] = False
    df["sostituto"] = 0.0
    for r in SLOT:
        blocco = df[df["ruolo"] == r].sort_values("base", ascending=False)
        n = min(DRAFTATI[r], max(len(blocco) - 1, 0))
        df.loc[df["ruolo"] == r, "sostituto"] = float(blocco["base"].iloc[n])
        df.loc[blocco.index[:DRAFTATI[r]], "comprato"] = True
    df["surplus"] = (df["base"] - df["sostituto"]).clip(lower=0)

    # 3. premio del modificatore: sposta crediti verso chi lo alimenta
    solidita = solidita_difensiva(df)
    df["premio"] = 0.0
    if solidita:
        for r in PESO_MOD:
            m = df["comprato"] & (df["ruolo"] == r)
            if not m.any():
                continue
            forza = df.loc[m, "squadra"].map(lambda s: 0.3 + 0.7 * solidita.get(s, 0.5))
            peso = forza * PESO_MOD[r]
            if peso.sum() > 0:
                df.loc[m, "premio"] = (QUOTA_MODIFICATORE * df.loc[m, "surplus"].sum()
                                       * peso / peso.sum())
    df["valore"] = df["surplus"] + df["premio"]

    # 4. ripartizione fra reparti dedotta dall'FVM, e la tua sopra
    comprati = df["comprato"]
    fvm_reparto = {r: df.loc[comprati & (df["ruolo"] == r), "fvm"].sum() for r in SLOT}
    totale_fvm = sum(fvm_reparto.values()) or 1
    mercato = {r: BUDGET * fvm_reparto[r] / totale_fvm for r in SLOT}

    df["prezzo"] = 1.0
    df["tetto"] = 1.0
    df["mercato_reparto"] = 0.0
    for r in SLOT:
        m = comprati & (df["ruolo"] == r)
        somma = df.loc[m, "valore"].sum()
        n = int(m.sum())
        df.loc[df["ruolo"] == r, "mercato_reparto"] = round(mercato[r])
        if somma <= 0 or n == 0:
            continue
        quota = df.loc[m, "valore"] / somma
        df.loc[m, "prezzo"] = 1 + (mercato[r] * SQUADRE_PER_LEGA - n) * quota
        df.loc[m, "tetto"] = 1 + (obiettivi[r] * SQUADRE_PER_LEGA - n) * quota

    df["prezzo"] = df["prezzo"].round(1)
    df["tetto"] = df["tetto"].round(0).clip(lower=1).astype(int)
    df["premio"] = df["premio"].round(2)
    return df.sort_values(["ruolo", "tetto"], ascending=[True, False])


# ------------------------------------------------------------------- uscite
def esporta_app(per_piano, percorso):
    """Un solo file per l'app: prezzi di mercato uguali per tutti, un tetto
    per ogni piano. Cosi' in asta si passa dal piano A al piano B senza
    ricaricare niente."""
    base = next(iter(per_piano.values()))
    voci = []
    for _, r in base[base["comprato"]].iterrows():
        tetti = {}
        for nome, df in per_piano.items():
            riga = df[(df["nome"] == r["nome"]) & (df["ruolo"] == r["ruolo"])]
            tetti[nome] = int(riga["tetto"].iloc[0]) if not riga.empty else 1
        voci.append({"n": r["nome"], "sq": r["squadra"], "r": r["ruolo"],
                     "qt": int(r["qt"]), "pr": float(r["prezzo"]), "tt": tetti})
    voci.sort(key=lambda v: (v["r"], -max(v["tt"].values()), -v["pr"]))
    blocco = {
        "stagione": "2026/27",
        "generato": date.today().isoformat(),
        "piani": {nome: dict(PIANI[nome]) for nome in per_piano},
        "listone": voci,
    }
    percorso.parent.mkdir(exist_ok=True)
    percorso.write_text(json.dumps(blocco, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(voci)


def esporta_tabelle(per_piano, percorso, quanti=18):
    """Le tabelle con i tetti, per leggerle con calma prima dell'asta.
    Vanno in report/, che git ignora: sono le tue carte."""
    nomi = {"P": "Portieri", "D": "Difensori", "C": "Centrocampisti", "A": "Attaccanti"}
    base = next(iter(per_piano.values()))
    righe = ["# Listone FC Cazzimma — tetti per piano\n",
             f"Generato da `motore/listone.py` il {date.today().isoformat()}. File privato: git lo ignora.\n",
             "## I piani\n", "| piano | P | D | C | A |", "|---|---|---|---|---|"]
    righe += [f"| {n} | {ob['P']} | {ob['D']} | {ob['C']} | {ob['A']} |" for n, ob in PIANI.items()]
    for r in SLOT:
        blocco = base[(base["ruolo"] == r) & base["comprato"]].head(quanti)
        righe += [f"\n### {nomi[r]}\n", "| giocatore | squadra | qt | mercato | " + " | ".join(per_piano) + " |",
                  "|---|---|---:|---:|" + "---:|" * len(per_piano)]
        for _, g in blocco.iterrows():
            tetti = []
            for df in per_piano.values():
                riga = df[(df["nome"] == g["nome"]) & (df["ruolo"] == r)]
                tetti.append(str(int(riga["tetto"].iloc[0])) if not riga.empty else "-")
            righe.append(f"| {g['nome']} | {g['squadra']} | {int(g['qt'])} | {round(g['prezzo'])} | " + " | ".join(tetti) + " |")
    percorso.write_text("\n".join(righe) + "\n", encoding="utf-8")


def stampa(df, piano, quanti=14):
    ob = PIANI[piano]
    print(f"\n  PIANO {piano.upper()} — " + "   ".join(f"{r} {ob[r]}" for r in SLOT))
    print(f"  {len(df)} giocatori nel file, {int(df['comprato'].sum())} verranno comprati\n")
    for r in ("P", "D", "C", "A"):
        blocco = df[(df["ruolo"] == r) & df["comprato"]]
        if blocco.empty:
            continue
        mercato = int(blocco["mercato_reparto"].iloc[0])
        print(f"  {r}   il mercato ci spende {mercato}, tu ne metti {ob[r]}")
        for _, g in blocco.head(quanti).iterrows():
            print(f"    {str(g['nome'])[:19]:<19} {str(g['squadra'])[:11]:<12} "
                  f"qt {int(g['qt']):>3}   mercato {g['prezzo']:>5.1f}   TETTO {g['tetto']:>3}")
        print(f"    ... gli ultimi comprati stanno intorno a {blocco['tetto'].iloc[-1]}\n")


if __name__ == "__main__":
    argomenti = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not argomenti:
        raise SystemExit(__doc__)

    grezzo = leggi(argomenti[0])
    problemi = controlla(grezzo)
    for problema in problemi:
        print("  ATTENZIONE, listone incompleto — " + problema)

    da_stampare = list(PIANI) if "--tutti" in sys.argv else [next(iter(PIANI))]
    if "--piano" in sys.argv:
        da_stampare = [sys.argv[sys.argv.index("--piano") + 1]]
    for p in da_stampare:
        if p not in PIANI:
            raise SystemExit(f"Piani: {', '.join(PIANI)}")

    # i piani si calcolano sempre tutti: l'app li vuole insieme
    per_piano = {p: calcola(grezzo, p) for p in PIANI}
    for p in da_stampare:
        stampa(per_piano[p], p)

    # con un listone incompleto i prezzi sono sbagliati: non si sovrascrive
    # il file buono per l'app, si dice forte e basta
    if problemi:
        print("  Listone incompleto: report/listone.json NON aggiornato, i prezzi sarebbero sbagliati.\n")
        raise SystemExit(1)
    uscita = RADICE / "report" / "listone.json"
    n = esporta_app(per_piano, uscita)
    esporta_tabelle(per_piano, RADICE / "report" / "LISTONE.md")
    print(f"  → report/listone.json, {n} giocatori e {len(per_piano)} piani, pronto per l'app")
    print(f"  → report/LISTONE.md, le tabelle con i tetti da leggere prima dell'asta\n")
