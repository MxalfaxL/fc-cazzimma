"""La stagione 2025/26 giocatore per giocatore, dai tabellini di SOS Fanta.

Da settembre il progetto aspetta "le statistiche della stagione scorsa" (media
voto, presenze, gol, assist, ammonizioni): servono a non giudicare un
giocatore su cinque giornate. SOS Fanta ha pubblicato, per ogni partita del
2025/26, l'articolo "I voti di ..." con il tabellino di Leghe Fantacalcio:
undici titolari, cambi col minuto, voto di ognuno, gol, assist, cartellini,
rigori. Sono gli stessi voti della lega (verificato il 14/9 sulla stagione in
corso: 1056 su 1058 identici ai file ufficiali).

Si scarica UNA volta la sola categoria "Voti" dall'archivio WordPress del
sito (poche richieste, distanziate; stessa strada dell'arretrato gia' decisa
il 12 settembre), si salva sul Mac e da li' in poi si lavora in locale.

Limiti dichiarati: i gol si contano dalla riga "Gol:" del tabellino, che per
una doppietta di solito ripete il nome ma non e' garantito, e che comprende i
rigori segnati (una riga "Rigori segnati" non esiste: chi ha segnato dal
dischetto lo dice la tabella rigori di `dati/stagione-2025-26.json`, dal web);
i minuti non contano recuperi ed espulsioni. Le prime 4 giornate del 2025/26
hanno i voti in immagine, non in testo: mancano, e ogni squadra ha 34 partite
lette su 38. I rapporti (presenze, titolarita') vanno fatti su quelle 34.

Uso:
    python3 motore/stagione_scorsa.py              # scarica se serve, poi scrive i conti
    python3 motore/stagione_scorsa.py --riscarica  # rifa' lo scaricamento

Scrive dati/stagione-2025-26-giocatori.json e report/STAGIONE-SCORSA.md (privati).
"""

import html
import json
import re
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE / "motore"))
from leggi_sosfanta import pulisci  # noqa: E402
from titolari import catena, pezzi_di_primo_livello  # noqa: E402
from voti_leghe import carica_listone, leggi_partita, norm, ripulisci, trova_nome  # noqa: E402

ARCHIVIO = "https://www.sosfanta.com/wp-json/wp/v2/posts"
CATEGORIA_VOTI = 32
DAL, AL = "2025-08-01", "2026-06-15"
CARTELLA = RADICE / "dati" / "sosfanta-2025-26"
GREZZO = CARTELLA / "archivio-voti.json"
USCITA_JSON = RADICE / "dati" / "stagione-2025-26-giocatori.json"
USCITA_MD = RADICE / "report" / "STAGIONE-SCORSA.md"
LISTONE = RADICE / "report" / "listone.json"

# Le venti del 2025/26: quelle di quest'anno senza le tre salite dalla B, con
# le tre scese. Servono a spezzare il tabellino squadra per squadra.
SQUADRE_2025_26 = ["Atalanta", "Bologna", "Cagliari", "Como", "Cremonese", "Fiorentina", "Genoa",
                   "Inter", "Juventus", "Lazio", "Lecce", "Milan", "Napoli", "Parma", "Pisa", "Roma",
                   "Sassuolo", "Torino", "Udinese", "Verona"]
ALIAS = {"JUVE": "Juventus", "HELLAS VERONA": "Verona", "HELLAS": "Verona"}
PAUSA = 5          # secondi fra una pagina e l'altra: e' un sito, non un servizio


def scarica(filtro):
    """Tutte le pagine di una ricerca nell'archivio, fra DAL e AL."""
    articoli, pagina = [], 1
    while True:
        url = (f"{ARCHIVIO}?{filtro}&per_page=100&page={pagina}"
               f"&after={DAL}T00:00:00&before={AL}T23:59:59&_fields=id,date,link,title,content")
        richiesta = urllib.request.Request(url, headers={"User-Agent": "fc-cazzimma lettore personale",
                                                         "Accept": "application/json"})
        with urllib.request.urlopen(richiesta, timeout=90) as r:
            pagine = int(r.headers.get("X-WP-TotalPages") or 1)
            posts = json.loads(r.read())
        for p in posts:
            articoli.append({"id": p["id"], "data": p["date"], "link": p["link"],
                             "titolo": html.unescape(p["title"]["rendered"]),
                             "testo": pulisci(p["content"]["rendered"])})
        print(f"  {filtro[:30]}: pagina {pagina}/{pagine}, {len(posts)} articoli")
        if pagina >= pagine:
            return articoli
        pagina += 1
        time.sleep(PAUSA)


def archivio(riscarica=False):
    """La categoria Voti, piu' i pochi articoli di voti che la redazione ha
    messo in altre categorie (Sassuolo-Como, Juve-Lazio, un riepilogo di
    maggio): senza, mancavano una decina di partite."""
    CARTELLA.mkdir(parents=True, exist_ok=True)
    dati = json.load(open(GREZZO, encoding="utf-8")) if GREZZO.exists() and not riscarica else {}
    if isinstance(dati, list):                    # primo formato: solo la categoria
        dati = {"categoria": dati}
    cambiato = False
    if "categoria" not in dati:
        print(f"Scarico la categoria Voti di SOS Fanta dal {DAL} al {AL}...")
        dati["categoria"] = scarica(f"categories={CATEGORIA_VOTI}")
        cambiato = True
    if "fuori_categoria" not in dati:
        print("Cerco gli articoli di voti fuori dalla categoria...")
        time.sleep(PAUSA)
        trovati = scarica(f"search=voti&categories_exclude={CATEGORIA_VOTI}")
        dati["fuori_categoria"] = [a for a in trovati if "i voti" in a["titolo"].lower()]
        cambiato = True
    if cambiato:
        GREZZO.write_text(json.dumps(dati, ensure_ascii=False, indent=0), encoding="utf-8")
    return dati["categoria"] + dati["fuori_categoria"]


def canonico(scritta):
    s = scritta.strip().upper()
    if s in ALIAS:
        return ALIAS[s]
    for q in SQUADRE_2025_26:
        if q.upper() == s:
            return q
    return None


def leggi_partite(articoli):
    """(casa, ospite) → {squadra: [(nome, voto, titolare, minuti)], eventi}.
    Ogni accoppiamento si gioca una volta sola in casa: e' la chiave che
    toglie i doppioni fra l'articolo della partita e il riepilogo di giornata."""
    partite = {}
    for a in sorted(articoli, key=lambda a: a["data"]):
        # la coda del tabellino scrive a volte "Rigore sbagliato:" al singolare,
        # e il lettore conosce solo il plurale: senza questo se ne perdeva una parte
        testo = ripulisci(a["testo"]).replace("Rigore sbagliato:", "Rigori sbagliati:") \
            .replace("Rigore parato:", "Rigori parati:")
        for blocco in testo.split("✅")[1:]:
            # qualche tabellino ha l'intestazione senza risultato ("INTER-ATALANTA
            # INTER - Sommer 6"): un 0-0 finto la fa leggere, il risultato non si usa
            blocco = re.sub(r"^\s*([A-ZÀ-Ü' .]+?-[A-ZÀ-Ü' .]+?)\s+(?=[A-ZÀ-Ü' .]+\s*-\s)", r"\1 0-0 ", blocco, count=1)
            letto = leggi_partita(blocco, SQUADRE_2025_26 + list(ALIAS))
            if not letto:
                continue
            (casa, ospite), per_squadra, eventi = letto
            chiave = (canonico(casa), canonico(ospite))
            if None in chiave:
                continue
            squadre = {}
            for scritta, elenco in per_squadra.items():
                sq = canonico(scritta)
                if sq not in chiave:
                    continue
                giocatori = []
                for pezzo in pezzi_di_primo_livello(elenco):
                    giro = catena(pezzo.replace("*", ""))
                    for j, (nome, entrato) in enumerate(giro):
                        uscito = giro[j + 1][1] if j + 1 < len(giro) else None
                        voto = re.search(rf"{re.escape(nome)}\s+(\d{{1,2}}(?:[,.]\d)?|sv)", pezzo.replace("*", ""))
                        v = voto.group(1) if voto else "sv"
                        giocatori.append({"nome": nome, "voto": None if v == "sv" else float(v.replace(",", ".")),
                                          "titolare": j == 0,
                                          "minuti": max(0, min(90, (uscito or 90) - (entrato or 0)))})
                squadre[sq] = giocatori
            if len(squadre) == 2 and all(len([g for g in gg if g["titolare"]]) >= 10 for gg in squadre.values()):
                # a parita' di partita vince il tabellino piu' completo
                vecchio = partite.get(chiave)
                if not vecchio or sum(map(len, squadre.values())) >= sum(map(len, vecchio["squadre"].values())):
                    partite[chiave] = {"squadre": squadre, "eventi": eventi, "data": a["data"][:10], "link": a["link"]}
    return partite


def conta(partite):
    per_squadra_listone, esatti, _ = carica_listone()
    listone = {g["n"]: g for g in json.load(open(LISTONE, encoding="utf-8"))["listone"]}
    giocatori = {}
    partite_per_squadra = defaultdict(int)
    for (casa, ospite), p in partite.items():
        for sq, elenco in p["squadre"].items():
            partite_per_squadra[sq] += 1
            for g in elenco:
                # prima dentro la squadra di quest'anno se e' la stessa, poi per nome esatto:
                # chi ha cambiato squadra si ritrova se il nome e' unico nel listone
                nome_listone = trova_nome(g["nome"], sq, per_squadra_listone, esatti)
                chiave = nome_listone or f"{g['nome']}|{sq}"
                v = giocatori.setdefault(chiave, {
                    "nome_tabellino": g["nome"], "nome_listone": nome_listone, "squadre_2025_26": [],
                    "ruolo": listone[nome_listone]["r"] if nome_listone else None,
                    "squadra_2026_27": listone[nome_listone]["sq"] if nome_listone else None,
                    "in_distinta": 0, "presenze_con_voto": 0, "titolare": 0, "minuti": 0, "voti": [],
                    "gol": 0, "assist": 0, "ammonizioni": 0, "espulsioni": 0, "autogol": 0,
                    "rigori_sbagliati": 0, "rigori_parati": 0})
                if sq not in v["squadre_2025_26"]:
                    v["squadre_2025_26"].append(sq)
                v["in_distinta"] += 1
                v["titolare"] += g["titolare"]
                v["minuti"] += g["minuti"]
                if g["voto"] is not None:
                    v["presenze_con_voto"] += 1
                    v["voti"].append(g["voto"])
                for e in p["eventi"].get(norm(g["nome"]), []):
                    campo = {"gol": "gol", "assist": "assist", "ammoniti": "ammonizioni", "espulsi": "espulsioni",
                             "autogol": "autogol", "rigori sbagliati": "rigori_sbagliati",
                             "rigori parati": "rigori_parati"}.get(e)
                    if campo:
                        v[campo] += 1
    for v in giocatori.values():
        v["media_voto"] = round(sum(v["voti"]) / len(v["voti"]), 2) if v["voti"] else None
        del v["voti"]
    return giocatori, dict(partite_per_squadra)


def scrivi_md(giocatori, partite_per_squadra, n_partite):
    abbinati = [v for v in giocatori.values() if v["nome_listone"]]
    righe = ["# La stagione 2025/26 dei giocatori del listone — tabellini SOS Fanta (voti Leghe)", "",
             f"Partite lette: **{n_partite}** su 380. Giocatori abbinati al listone: {len(abbinati)}.",
             "Presenze = con voto (sv escluso). Minuti senza recuperi. Gol dalla riga 'Gol:' del tabellino.", "",
             "Partite per squadra: " + ", ".join(f"{s} {n}" for s, n in sorted(partite_per_squadra.items())), ""]
    for ruolo, titolo, minimo in (("P", "Portieri", 10), ("D", "Difensori", 15), ("C", "Centrocampisti", 15),
                                  ("A", "Attaccanti", 12)):
        righe += [f"## {titolo} (almeno {minimo} presenze con voto)", "",
                  "| Giocatore | Squadra oggi | 2025/26 | Pres. | Tit. | Minuti | Media | Gol | Ass | Amm | Rig. sbagl. |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        scelti = [v for v in abbinati if v["ruolo"] == ruolo and v["presenze_con_voto"] >= minimo]
        for v in sorted(scelti, key=lambda v: -(v["media_voto"] or 0)):
            righe.append(f"| {v['nome_listone']} | {v['squadra_2026_27']} | {'/'.join(v['squadre_2025_26'])} | "
                         f"{v['presenze_con_voto']} | {v['titolare']} | {v['minuti']} | {v['media_voto']} | "
                         f"{v['gol']} | {v['assist']} | {v['ammonizioni']} | {v['rigori_sbagliati']} |")
        righe.append("")
    # i rigori: chi li ha calciati lo dice la tabella del web (Sky, squadra per
    # squadra); dai tabellini si controllano solo quelli sbagliati
    web = RADICE / "dati" / "stagione-2025-26.json"
    righe += ["## Rigori calciati nel 2025/26", ""]
    if web.exists():
        rigori = json.load(open(web, encoding="utf-8")).get("rigori", [])
        sbagliati_tab = {v["nome_listone"]: v["rigori_sbagliati"] for v in giocatori.values() if v["nome_listone"]}
        righe += ["Dalla tabella del web (`dati/stagione-2025-26.json`); fra parentesi i rigori sbagliati "
                  "contati dai tabellini, per controllo.", ""]
        for r in sorted(rigori, key=lambda r: (r["squadra"], -(r.get("calciati") or 0))):
            nome = r.get("nome_listone") or f"{r['nome_fonte']} (fuori listone)"
            oggi = ""
            if r.get("nome_listone"):
                sq = next((v["squadra_2026_27"] for v in giocatori.values() if v["nome_listone"] == r["nome_listone"]), None)
                oggi = f", oggi {sq}" if sq and sq != r["squadra"] else ""
                oggi += f" (tabellini: {sbagliati_tab.get(r['nome_listone'], 0)} sbagliati)"
            righe.append(f"- {r['squadra']}: **{nome}** {r.get('calciati')} calciati, {r.get('segnati')} segnati, "
                         f"{r.get('sbagliati')} sbagliati{oggi}")
    else:
        righe.append("Manca `dati/stagione-2025-26.json`: dai soli tabellini si vedono i rigori sbagliati, non i segnati.")
    USCITA_MD.write_text("\n".join(righe) + "\n", encoding="utf-8")


def main():
    articoli = archivio(riscarica="--riscarica" in sys.argv)
    partite = leggi_partite(articoli)
    giocatori, per_squadra = conta(partite)
    USCITA_JSON.write_text(json.dumps({
        "partite": len(partite), "partite_per_squadra": per_squadra,
        "giocatori": sorted(giocatori.values(), key=lambda v: (v["squadra_2026_27"] or "~", v["nome_tabellino"])),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    scrivi_md(giocatori, per_squadra, len(partite))
    abbinati = sum(1 for v in giocatori.values() if v["nome_listone"])
    print(f"{len(articoli)} articoli, {len(partite)} partite su 380, {len(giocatori)} giocatori "
          f"({abbinati} nel listone) → {USCITA_JSON.relative_to(RADICE)}, {USCITA_MD.relative_to(RADICE)}")
    corte = {s: n for s, n in per_squadra.items() if n < 38}
    if corte:
        print(f"  squadre con meno di 38 partite lette: {corte}")


if __name__ == "__main__":
    main()
