"""Le fasce della guida all'asta di SOS Fanta, accanto ai nostri prezzi.

All'asta non conta solo quanto vale un giocatore, conta quanto sono disposti
a pagarlo gli altri nove. Molti arrivano al tavolo con una guida in mano, e la
piu' letta del gruppo Gazzetta e' quella di SOS Fanta, "fascia per fascia",
aggiornata dopo ogni giornata. Sapere in che fascia mette un giocatore dice
dove gli altri faranno l'ancora: un giocatore che la guida mette "SUPER TOP"
lo pagheranno caro anche se noi lo stimiamo meno, uno "LOW COST" che per
noi vale di piu' e' un'occasione.

La guida ha una forma fissa, un paragrafo per fascia: "TOP – Martinez Jo.,
Carnesecchi, Maignan", con i nomi gia' scritti come nel listone. Qui si legge
quella forma e nient'altro; i nomi si riconoscono solo se sono nel listone
(chi non c'e' viene elencato, non indovinato). Le frasi dove la guida cita
dei crediti ("si puo' arrivare a pagarlo N crediti su 500 in una lega a 8")
si tengono intere, accanto al giocatore di cui parla il paragrafo: sono per
leghe diverse dalla nostra, vanno lette, non sommate.

Uso:
    python3 motore/guida_asta.py                      # l'ultima guida in dati/fonti/asta-sosfanta/
    python3 motore/guida_asta.py --scarica            # prima riscarica la guida (una richiesta)
    python3 motore/guida_asta.py <file della guida>
Scrive dati/guida-asta-sosfanta.json e report/GUIDA-ASTA.md (privati: ci sono i nostri prezzi).
"""

import html
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
CARTELLA = RADICE / "dati" / "fonti" / "asta-sosfanta"
LISTONE = RADICE / "report" / "listone.json"
USCITA_JSON = RADICE / "dati" / "guida-asta-sosfanta.json"
USCITA_MD = RADICE / "report" / "GUIDA-ASTA.md"

# Dalla fascia piu' cara alla meno cara, come le usa la guida. Le ultime tre
# non sono un prezzo ma un avviso: stanno in fondo e si leggono a parte.
ORDINE = ["SUPER TOP", "TUTTI I RIGORISTI SUPER TOP", "TOP", "SEMITOP", "SOTTO AI SEMITOP", "FASCIA ALTA",
          "JOLLY 1ª FASCIA", "POSSIBILI SORPRESE", "FASCIA MEDIA", "SCOMMESSE", "SOPRA AI LOW COST",
          "JOLLY 2ª FASCIA", "LOW COST 1ª FASCIA", "LOW COST 2ª FASCIA", "LEGHE NUMEROSE",
          "JOLLY 3ª FASCIA", "JOLLY 4ª FASCIA", "INFORTUNATI", "A RISCHIO", "DA EVITARE"]
AVVISI = {"INFORTUNATI", "A RISCHIO", "DA EVITARE"}
RIGA_FASCIA = re.compile(r"^(?:.*?\b)?(" + "|".join(re.escape(f) for f in sorted(ORDINE, key=len, reverse=True))
                         + r")\s*[–-]\s*(.+)$")
# la guida ha sempre lo stesso indirizzo e viene riscritta dopo ogni giornata
SLUG = "guida-asta-fantacalcio-2026-2027-tutti-consigli-fasce-chi-prendere"
ARCHIVIO = "https://www.sosfanta.com/wp-json/wp/v2/posts"
CREDITI = re.compile(r"[^.]*\b\d+(?:\s*/\s*\d+)?\s*crediti[^.]*\.", re.I)


def norm(t):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower())


def nomi_della_riga(resto, per_norma):
    """'Mandas, Okoye' → ['Mandas', 'Okoye']; l'ultimo pezzo puo' portarsi
    dietro l'inizio della descrizione, e si tiene solo il nome del listone
    piu' lungo con cui comincia."""
    trovati, ignoti = [], []
    pezzi = [p.strip() for p in resto.split(",") if p.strip()]
    for i, p in enumerate(pezzi):
        chiave = norm(p)
        if chiave in per_norma:
            trovati.append(per_norma[chiave])
            continue
        if i == len(pezzi) - 1:
            parole = p.split()
            for n in range(len(parole), 0, -1):
                k = norm(" ".join(parole[:n]))
                if k in per_norma:
                    trovati.append(per_norma[k])
                    break
            else:
                ignoti.append(p[:40])
        else:
            ignoti.append(p)
    return trovati, ignoti


def scarica():
    """La guida dall'archivio WordPress: una richiesta, un paragrafo per riga
    (il feed la taglia: nel numero del 16/9 mancavano le prime fasce dei portieri)."""
    richiesta = urllib.request.Request(f"{ARCHIVIO}?slug={SLUG}&_fields=date,modified,title,content,link",
                                       headers={"User-Agent": "fc-cazzimma lettore personale", "Accept": "application/json"})
    with urllib.request.urlopen(richiesta, timeout=60) as r:
        post = json.loads(r.read())[0]
    corpo = re.sub(r"</(p|h[1-6]|li)>", "\n", post["content"]["rendered"])
    corpo = html.unescape(re.sub(r"<[^>]+>", " ", corpo))
    corpo = "\n".join(" ".join(r.split()) for r in corpo.split("\n") if r.strip())
    giorno = post["modified"][:10]
    uscita = CARTELLA / f"guida-{giorno}.txt"
    CARTELLA.mkdir(parents=True, exist_ok=True)
    uscita.write_text(f"TITOLO: {html.unescape(post['title']['rendered'])}\nDATA: {post['date'][:16].replace('T', ' ')}\n"
                      f"AGGIORNATA: {post['modified'][:16].replace('T', ' ')}\nLINK: {post['link']}\nFONTE: sosfanta\n\n"
                      + corpo, encoding="utf-8")
    print(f"Guida aggiornata il {post['modified'][:16].replace('T', ' ')} → {uscita.relative_to(RADICE)}")
    return uscita


def main():
    if "--scarica" in sys.argv:
        scarica()
        sys.argv.remove("--scarica")
    if len(sys.argv) > 1:
        guida = Path(sys.argv[1])
    else:
        guide = sorted(CARTELLA.glob("guida-*.txt"))
        if not guide:
            sys.exit(f"Nessuna guida in {CARTELLA.relative_to(RADICE)}")
        guida = guide[-1]
    righe = guida.read_text(encoding="utf-8").split("\n")
    aggiornata = next((r.split(":", 1)[1].strip() for r in righe if r.startswith("AGGIORNATA:")), "?")
    listone = json.load(open(LISTONE, encoding="utf-8"))["listone"]
    per_nome = {g["n"]: g for g in listone}
    per_norma = {norm(g["n"]): g["n"] for g in listone}

    giocatori, ignoti, corrente = {}, [], []
    for riga in righe:
        m = RIGA_FASCIA.match(riga)
        if m:
            fascia = m.group(1).replace("TUTTI I RIGORISTI ", "")
            nomi, non_trovati = nomi_della_riga(m.group(2), per_norma)
            ignoti += [{"fascia": fascia, "nome": n} for n in non_trovati]
            corrente = nomi
            for n in nomi:
                # un nome puo' stare in due fasce (es. tra gli infortunati e in una
                # fascia di prezzo): vale la prima, l'avviso si aggiunge
                v = giocatori.setdefault(n, {"nome": n, "ruolo": per_nome[n]["r"], "squadra": per_nome[n]["sq"],
                                             "fascia": None, "avvisi": [], "crediti": []})
                if fascia in AVVISI:
                    v["avvisi"].append(fascia)
                elif v["fascia"] is None:
                    v["fascia"] = fascia
            continue
        # un paragrafo di descrizione: le frasi coi crediti vanno al giocatore
        # della fascia corrente che il paragrafo nomina per primo
        frasi = CREDITI.findall(riga)
        if frasi and corrente:
            citati = [n for n in corrente if re.search(r"\b" + re.escape(re.sub(r"\s+\S+\.$", "", n)), riga)]
            destinatario = citati[0] if citati else corrente[0]
            giocatori[destinatario]["crediti"] += [f.strip() for f in frasi]

    for v in giocatori.values():
        v["ordine_fascia"] = ORDINE.index(v["fascia"]) if v["fascia"] else None
        g = per_nome[v["nome"]]
        v["nostro_prezzo"] = round(g.get("pr", 0))
    USCITA_JSON.write_text(json.dumps({"guida": guida.name, "aggiornata": aggiornata,
                                       "giocatori": sorted(giocatori.values(), key=lambda v: (v["ruolo"], v["ordine_fascia"] or 99)),
                                       "non_riconosciuti": ignoti}, ensure_ascii=False, indent=1), encoding="utf-8")

    md = [f"# La guida all'asta di SOS Fanta, fascia per fascia (aggiornata {aggiornata})", "",
          "Accanto a ogni nome il **nostro prezzo stimato** dal listone (piano di equilibrio del mercato).",
          "Le frasi coi crediti sono della guida, spesso per leghe da 8: vanno lette, non sommate.",
          f"Nomi della guida non trovati nel listone: {len(ignoti)}"
          + (" — " + ", ".join(i["nome"] for i in ignoti) if ignoti else ""), ""]
    for ruolo, titolo in (("P", "Portieri"), ("D", "Difensori"), ("C", "Centrocampisti"), ("A", "Attaccanti")):
        md += [f"## {titolo}", ""]
        for fascia in ORDINE:
            chi = [v for v in giocatori.values() if v["ruolo"] == ruolo and
                   (v["fascia"] == fascia or (fascia in AVVISI and fascia in v["avvisi"]))]
            if not chi:
                continue
            chi.sort(key=lambda v: -v["nostro_prezzo"])
            md.append(f"**{fascia}**: " + ", ".join(f"{v['nome']} ({v['nostro_prezzo']})" for v in chi))
            for v in chi:
                for f in v["crediti"]:
                    md.append(f"  - {v['nome']}: «{f}»")
        md.append("")
    senza = [g["n"] for g in listone if g["n"] not in giocatori and g.get("pr", 0) >= 10]
    md += ["## Del listone da 10 crediti in su, ma non nella guida", "", ", ".join(senza) or "nessuno", ""]
    USCITA_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{guida.name} (aggiornata {aggiornata}): {len(giocatori)} giocatori in fascia, "
          f"{sum(len(v['crediti']) for v in giocatori.values())} frasi coi crediti, {len(ignoti)} nomi non riconosciuti "
          f"→ {USCITA_JSON.relative_to(RADICE)}, {USCITA_MD.relative_to(RADICE)}")
    for i in ignoti[:20]:
        print(f"  non riconosciuto: {i['nome']!r} ({i['fascia']})")


if __name__ == "__main__":
    main()
