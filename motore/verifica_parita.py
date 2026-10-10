"""Controlla che il motore Python e quello JavaScript dentro index.html diano
gli stessi numeri sugli stessi dati.

Il motore esiste in due lingue perche' la formazione si decide sul telefono
e i conti lunghi si fanno sul Mac. Se cambi una regola in un posto solo,
questo script se ne accorge. Lancialo prima di dichiarare fatto qualcosa.

Oltre al consiglio confronta le due strade della formazione scelta da Marco
(10/10/2026): il meglio in un modulo dato (consiglia con il modulo) e una
formazione fatta a mano (valuta_scelta / valutaScelta), sia con gli undici
del consiglio sia con un cambio dalla panchina.

Uso:
    python3 motore/verifica_parita.py                  # usa dati/rosa-prova.json
    python3 motore/verifica_parita.py dati/rosa.json   # sulla rosa vera
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ottimizzatore import carica, consiglia, valuta_scelta, come_json

TOLLERANZA = 1e-9
MODULO_PROVA = "4-4-2"   # il modulo scelto "a mano" nelle prove della scelta

# il motore JS legge la rosa nel formato dell'app; il collaudo aggiunge gli id
# e stampa lo stesso oggetto che produce il Python
CODA_JS = r"""
const rosa = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const voci = (Array.isArray(rosa) ? rosa : (rosa.rosa || rosa.giocatori)).map((v, i) => ({
  id: 'g' + i, n: v.n || v.nome, r: v.r || v.ruolo, fv: +(v.fv ?? 6), voto: +(v.voto ?? v.fv ?? 6),
  st: v.st || (v.p === undefined ? 'T' : (v.p <= 0 ? 'F' : (v.p >= 1 ? 'T' : 'B'))),
  pb: v.pb ?? (v.p !== undefined && v.p > 0 && v.p < 1 ? v.p : undefined),
}));
// le scelte a mano arrivano dal Python per nome: qui gli id sono 'g' + indice
const scelte = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8'));
const idDi = Object.fromEntries(voci.map(g => [g.n, g.id]));
const forma = s => s ? {
  modulo: s.modulo, totale: s.totale, mod: s.mod, media: s.media, modAtteso: s.modAtteso, scelta: !!s.scelta,
  undici: s.undici.map(x => ({n: x.g.n, r: x.r, p: x.p, atteso: x.atteso, votoAtteso: x.votoAtteso, costo: x.costo, sostituto: x.sostituto})),
  panchina: s.panchina.map(g => g.n),
  alternative: s.alternative.map(a => ({modulo: a.modulo, totale: a.totale, mod: a.mod, modAtteso: a.modAtteso})),
  gol: s.gol, alGolDopo: s.alGolDopo,
} : null;
const out = {consiglio: forma(consiglia(voci))};
if (scelte.modulo) {
  out.modulo = forma(consiglia(voci, scelte.modulo));
  out.scelta = forma(valutaScelta(voci, scelte.modulo, scelte.nomi.map(n => idDi[n])));
  out.cambio = scelte.cambio ? forma(valutaScelta(voci, scelte.modulo, scelte.cambio.map(n => idDi[n]))) : null;
}
console.log(JSON.stringify(out));
"""


def motore_js():
    """Il pezzo puro dello script dell'app, fra i due segnaposto."""
    html = (RADICE / "index.html").read_text(encoding="utf-8")
    m = re.search(r"/\* ==== motore: inizio ====.*?\*/(.*?)/\* ==== motore: fine ==== \*/", html, re.S)
    if not m:
        raise SystemExit("Non trovo i segnaposto del motore in index.html.")
    return m.group(1)


def esegui_js(percorso_rosa, scelte):
    node = shutil.which("node")
    if not node:
        raise SystemExit("Serve node per far girare il motore JavaScript: brew install node")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(motore_js() + CODA_JS)
        script = f.name
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(scelte, f, ensure_ascii=False)
        file_scelte = f.name
    esito = subprocess.run([node, script, str(percorso_rosa), file_scelte], capture_output=True, text=True)
    Path(script).unlink(missing_ok=True)
    Path(file_scelte).unlink(missing_ok=True)
    if esito.returncode != 0:
        raise SystemExit("Il motore JavaScript si e' fermato:\n" + esito.stderr)
    return json.loads(esito.stdout)


def confronta(py, js):
    differenze = []

    def num(chiave, a, b, tol=TOLLERANZA):
        if a is None and b is None:
            return
        if a is None or b is None or abs(a - b) > tol:
            differenze.append(f"{chiave}: python {a} · js {b}")

    if js is None:
        return ["il JavaScript non da' nessuna formazione, il Python si'"]
    if py["modulo"] != js["modulo"]:
        differenze.append(f"modulo: python {py['modulo']} · js {js['modulo']}")
    if py.get("scelta", False) != js.get("scelta", False):
        differenze.append(f"scelta a mano: python {py.get('scelta')} · js {js.get('scelta')}")
    num("totale", py["totale"], js["totale"])
    num("modificatore", py["mod"], js["mod"])
    num("modificatore atteso", py["modAtteso"], js["modAtteso"])
    num("media difesa", py["media"], js["media"])
    num("gol", py["gol"], js["gol"])
    num("al gol dopo", py["alGolDopo"], js["alGolDopo"], tol=0.006)

    if [x["n"] for x in py["undici"]] != [x["n"] for x in js["undici"]]:
        differenze.append(f"undici: python {[x['n'] for x in py['undici']]} · js {[x['n'] for x in js['undici']]}")
    else:
        for a, b in zip(py["undici"], js["undici"]):
            num(f"{a['n']} atteso", a["atteso"], b["atteso"])
            num(f"{a['n']} voto atteso", a["votoAtteso"], b["votoAtteso"])
            num(f"{a['n']} costo", a["costo"], b["costo"])
            if a["sostituto"] != b["sostituto"]:
                differenze.append(f"{a['n']} sostituto: python {a['sostituto']} · js {b['sostituto']}")
    if py["panchina"] != js["panchina"]:
        differenze.append(f"panchina: python {py['panchina']} · js {js['panchina']}")
    if [a["modulo"] for a in py["alternative"]] != [a["modulo"] for a in js["alternative"]]:
        differenze.append("ordine degli altri moduli diverso")
    else:
        for a, b in zip(py["alternative"], js["alternative"]):
            num(f"{a['modulo']} totale", a["totale"], b["totale"])
            num(f"{a['modulo']} modificatore atteso", a["modAtteso"], b["modAtteso"])
    return differenze


if __name__ == "__main__":
    argomenti = [a for a in sys.argv[1:] if not a.startswith("--")]
    percorso = Path(argomenti[0]) if argomenti else RADICE / "dati" / "rosa-prova.json"
    if not percorso.exists():
        raise SystemExit(f"Non trovo {percorso}")

    rosa = carica(percorso)
    s = consiglia(rosa)
    py = come_json(s)

    # la scelta di Marco: il meglio nel MODULO_PROVA, poi gli stessi undici
    # valutati come formazione a mano, poi un cambio (il primo centrocampista
    # in panchina al posto dell'ultimo titolare)
    prove_py, scelte = {}, {}
    try:
        s_mod = consiglia(rosa, MODULO_PROVA)
    except ValueError:
        s_mod = None
        print(f"\n  con questa rosa il {MODULO_PROVA} non si schiera: salto le prove della scelta")
    if s_mod:
        nomi = [x["g"].nome for x in s_mod["undici"]]
        scelte = {"modulo": MODULO_PROVA, "nomi": nomi, "cambio": None}
        prove_py["modulo"] = come_json(s_mod)
        prove_py["scelta"] = come_json(valuta_scelta(rosa, MODULO_PROVA, nomi))
        titolari_c = [x["g"].nome for x in s_mod["undici"] if x["ruolo"] == "C"]
        panca_c = [g.nome for g in s_mod["panchina"] if g.ruolo == "C"]
        if titolari_c and panca_c:
            cambio = [panca_c[0] if n == titolari_c[-1] else n for n in nomi]
            scelte["cambio"] = cambio
            prove_py["cambio"] = come_json(valuta_scelta(rosa, MODULO_PROVA, cambio))

    tutto_js = esegui_js(percorso, scelte)
    js = tutto_js["consiglio"]

    print(f"\n  rosa: {percorso.name}")
    print(f"  python      {py['modulo']}  {py['totale']:.6f}  mod +{py['mod']}")
    print(f"  javascript  {js['modulo']}  {js['totale']:.6f}  mod +{js['mod']}")
    dubbi = [x for x in py["undici"] if x["p"] < 1]
    if dubbi:
        print("  dubbi in campo:")
        for x in sorted(dubbi, key=lambda x: -x["costo"]):
            print(f"    {x['n']:<14} {x['p']:.0%}   se perde -{x['costo']:.3f}   entra {x['sostituto']}")

    differenze = confronta(py, js)
    titoli = {"modulo": f"consiglio nel {MODULO_PROVA}", "scelta": f"{MODULO_PROVA} a mano, undici del consiglio",
              "cambio": f"{MODULO_PROVA} a mano, con un cambio a centrocampo"}
    for chiave, py_prova in prove_py.items():
        js_prova = tutto_js.get(chiave)
        diff = confronta(py_prova, js_prova)
        print(f"  {titoli[chiave]:<42} python {py_prova['totale']:.6f} · js "
              + (f"{js_prova['totale']:.6f}" if js_prova else "nessuna") + ("" if diff else "  ok"))
        differenze += [f"[{titoli[chiave]}] {d}" for d in diff]
    if differenze:
        print("\n  DIFFERENZE fra i due motori:")
        for d in differenze:
            print("   -", d)
        print()
        sys.exit(1)
    print("\n  OK: i due motori danno gli stessi numeri.\n")
