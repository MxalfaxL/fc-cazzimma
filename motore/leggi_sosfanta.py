"""Legge il feed RSS di SOS Fanta e salva gli articoli nuovi, pronti per il
lettore che scrive nel dossier.

SOS Fanta e' il sito fantacalcio della Gazzetta: infortuni, probabili,
formazioni ufficiali, ultime dai campi, piu' volte al giorno. Il feed RSS
(https://www.sosfanta.com/feed/) porta gli ultimi 25 articoli a testo
completo, con data, categorie e squadre: e' il canale pubblico pensato per i
lettori di notizie, e lo usiamo cosi', due o tre volte al giorno, per uso
personale. La loro API interna e' chiusa (robots.txt) e non si tocca.

Ogni articolo nuovo finisce in dati/sosfanta/AAAA-MM-GG/NNN-titolo.txt con
un'intestazione (titolo, data e ora, categorie, link) e il testo pulito.
I gia' visti stanno in dati/sosfanta/visti.json, cosi' si puo' lanciare
quante volte si vuole. Poi il lettore (model sonnet, prompt in
wiki/PROMPT-LETTORE.md, fonte "sosfanta") legge la cartella del giorno e
scrive note.json; dossier.py importa lo prende.

Uso:
    python3 motore/leggi_sosfanta.py                       # il feed: salva i nuovi, stampa l'elenco
    python3 motore/leggi_sosfanta.py --da 2026-09-05 --a 2026-09-10   # arretrato, una tantum, dall'archivio
                                                           # pubblico di WordPress (poche richieste, mai in automatico)
Nessuna dipendenza oltre la libreria standard.
"""

import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
FEED = "https://www.sosfanta.com/feed/"
CARTELLA = RADICE / "dati" / "sosfanta"
VISTI = CARTELLA / "visti.json"
NS = {"content": "http://purl.org/rss/1.0/modules/content/", "dc": "http://purl.org/dc/elements/1.1/"}
ROMA = timezone(timedelta(hours=2))   # ora legale; d'inverno sbaglia di un'ora, non importa


def scarica():
    richiesta = urllib.request.Request(FEED, headers={"User-Agent": "fc-cazzimma lettore personale (feed RSS)"})
    with urllib.request.urlopen(richiesta, timeout=30) as r:
        return r.read()


def pulisci(testo_html):
    """Da HTML a testo: paragrafi a capo, niente tag, entita' sciolte."""
    t = re.sub(r"<\s*(br|/p|/h\d|/li|/div)\s*/?>", "\n", testo_html or "", flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return t.strip()


def slug(titolo):
    return re.sub(r"[^a-z0-9]+", "-", titolo.lower().encode("ascii", "ignore").decode()).strip("-")[:60] or "articolo"


ARCHIVIO = "https://www.sosfanta.com/wp-json/wp/v2/posts"


def dal_feed():
    """Gli articoli del feed RSS: (guid, titolo, quando, categorie, corpo, link)."""
    radice = ET.fromstring(scarica())
    for item in radice.iter("item"):
        guid = (item.findtext("guid") or item.findtext("link") or "").strip()
        titolo = html.unescape((item.findtext("title") or "").strip())
        try:
            quando = parsedate_to_datetime(item.findtext("pubDate")).astimezone(ROMA)
        except Exception:
            quando = datetime.now(ROMA)
        categorie = [html.unescape(c.text or "") for c in item.findall("category")]
        corpo = pulisci(item.findtext("content:encoded", namespaces=NS) or item.findtext("description") or "")
        yield guid, titolo, quando, categorie, corpo, (item.findtext("link") or "").strip()


def dall_archivio(da, a):
    """L'arretrato fra due date dall'archivio pubblico di WordPress, 100 per
    pagina. Le categorie arrivano come numeri: le lasciamo perdere, il
    titolo basta. Solo a mano, solo per recuperare: il giro di ogni giorno
    usa il feed."""
    pagina = 1
    while True:
        url = (f"{ARCHIVIO}?per_page=100&page={pagina}&after={da}T00:00:00&before={a}T23:59:59"
               "&_fields=id,date,link,title,content")
        richiesta = urllib.request.Request(url, headers={"User-Agent": "fc-cazzimma lettore personale", "Accept": "application/json"})
        with urllib.request.urlopen(richiesta, timeout=60) as r:
            totale_pagine = int(r.headers.get("X-WP-TotalPages") or 1)
            posts = json.loads(r.read())
        for p in posts:
            quando = datetime.fromisoformat(p["date"]).replace(tzinfo=ROMA)
            yield p["link"], html.unescape(p["title"]["rendered"]), quando, [], pulisci(p["content"]["rendered"]), p["link"]
        if pagina >= totale_pagine:
            break
        pagina += 1


def main():
    CARTELLA.mkdir(parents=True, exist_ok=True)
    visti = json.loads(VISTI.read_text()) if VISTI.exists() else {}
    argomenti = sys.argv[1:]
    try:
        if "--da" in argomenti:
            da = argomenti[argomenti.index("--da") + 1]
            a = argomenti[argomenti.index("--a") + 1] if "--a" in argomenti else datetime.now(ROMA).strftime("%Y-%m-%d")
            articoli = list(dall_archivio(da, a))
        else:
            articoli = list(dal_feed())
    except Exception as e:
        sys.exit(f"Non riesco a leggere SOS Fanta: {e}")
    nuovi, per_giorno = [], {}
    for guid, titolo, quando, categorie, corpo, link in articoli:
        if not guid or guid in visti:
            continue
        giorno = quando.strftime("%Y-%m-%d")
        cartella = CARTELLA / giorno
        cartella.mkdir(exist_ok=True)
        n = len(list(cartella.glob("*.txt"))) + 1
        file = cartella / f"{n:03d}-{slug(titolo)}.txt"
        file.write_text(
            f"TITOLO: {titolo}\nDATA: {quando.strftime('%Y-%m-%d %H:%M')}\nCATEGORIE: {', '.join(categorie)}\n"
            f"LINK: {link}\nFONTE: sosfanta\n\n{corpo}\n", encoding="utf-8")
        visti[guid] = {"data": giorno, "titolo": titolo}
        nuovi.append((giorno, quando.strftime("%H:%M"), titolo, categorie))
        per_giorno.setdefault(giorno, []).append(file.name)
    VISTI.write_text(json.dumps(visti, ensure_ascii=False, indent=0), encoding="utf-8")
    # indice del giorno: si aggiorna a ogni giro
    for giorno in per_giorno:
        cartella = CARTELLA / giorno
        righe = [f"# SOS Fanta {giorno} — articoli salvati", ""]
        for f in sorted(cartella.glob("*.txt")):
            testa = f.read_text(encoding="utf-8").split("\n")
            righe.append(f"- {f.name} · {testa[1][6:]} · {testa[2][11:]}")
        (cartella / "indice.md").write_text("\n".join(righe) + "\n", encoding="utf-8")
    if not nuovi:
        print("Niente di nuovo su SOS Fanta.")
        return
    print(f"{len(nuovi)} articoli nuovi:")
    for giorno, ora, titolo, cat in sorted(nuovi):
        print(f"  {giorno} {ora}  {titolo[:70]:<70}  [{', '.join(c for c in cat if c != 'News')[:40]}]")
    print("Cartelle: " + ", ".join(f"dati/sosfanta/{g}/" for g in sorted(per_giorno)) + " → lettore sonnet → dossier.py importa")


if __name__ == "__main__":
    main()
