"""Controlla che il motore Python e quello JavaScript dentro index.html diano
gli stessi numeri sugli stessi dati.

Il motore esiste in due lingue perche' la formazione si decide sul telefono
e i conti lunghi si fanno sul Mac. Se cambi una regola in un posto solo,
questo script se ne accorge. Lancialo prima di dichiarare fatto qualcosa.

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
from ottimizzatore import carica, consiglia, come_json

TOLLERANZA = 1e-9

# il motore JS legge la rosa nel formato dell'app; il collaudo aggiunge gli id
# e stampa lo stesso oggetto che produce il Python
CODA_JS = r"""
const rosa = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const voci = (Array.isArray(rosa) ? rosa : (rosa.rosa || rosa.giocatori)).map((v, i) => ({
  id: 'g' + i, n: v.n || v.nome, r: v.r || v.ruolo, fv: +(v.fv ?? 6), voto: +(v.voto ?? v.fv ?? 6),
  st: v.st || (v.p === undefined ? 'T' : (v.p <= 0 ? 'F' : (v.p >= 1 ? 'T' : 'B'))),
  pb: v.pb ?? (v.p !== undefined && v.p > 0 && v.p < 1 ? v.p : undefined),
}));
const s = consiglia(voci);
if (!s) { console.log('null'); process.exit(0); }
console.log(JSON.stringify({
  modulo: s.modulo, totale: s.totale, mod: s.mod, media: s.media,
  undici: s.undici.map(x => ({n: x.g.n, r: x.r, p: x.p, atteso: x.atteso, votoAtteso: x.votoAtteso, costo: x.costo, sostituto: x.sostituto})),
  panchina: s.panchina.map(g => g.n),
  alternative: s.alternative.map(a => ({modulo: a.modulo, totale: a.totale, mod: a.mod})),
  gol: s.gol, alGolDopo: s.alGolDopo,
}));
"""


def motore_js():
    """Il pezzo puro dello script dell'app, fra i due segnaposto."""
    html = (RADICE / "index.html").read_text(encoding="utf-8")
    m = re.search(r"/\* ==== motore: inizio ====.*?\*/(.*?)/\* ==== motore: fine ==== \*/", html, re.S)
    if not m:
        raise SystemExit("Non trovo i segnaposto del motore in index.html.")
    return m.group(1)


def esegui_js(percorso_rosa):
    node = shutil.which("node")
    if not node:
        raise SystemExit("Serve node per far girare il motore JavaScript: brew install node")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(motore_js() + CODA_JS)
        script = f.name
    esito = subprocess.run([node, script, str(percorso_rosa)], capture_output=True, text=True)
    Path(script).unlink(missing_ok=True)
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

    if py["modulo"] != js["modulo"]:
        differenze.append(f"modulo: python {py['modulo']} · js {js['modulo']}")
    num("totale", py["totale"], js["totale"])
    num("modificatore", py["mod"], js["mod"])
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
    return differenze


if __name__ == "__main__":
    argomenti = [a for a in sys.argv[1:] if not a.startswith("--")]
    percorso = Path(argomenti[0]) if argomenti else RADICE / "dati" / "rosa-prova.json"
    if not percorso.exists():
        raise SystemExit(f"Non trovo {percorso}")

    py = come_json(consiglia(carica(percorso)))
    js = esegui_js(percorso)

    print(f"\n  rosa: {percorso.name}")
    print(f"  python      {py['modulo']}  {py['totale']:.6f}  mod +{py['mod']}")
    print(f"  javascript  {js['modulo']}  {js['totale']:.6f}  mod +{js['mod']}")
    dubbi = [x for x in py["undici"] if x["p"] < 1]
    if dubbi:
        print("  dubbi in campo:")
        for x in sorted(dubbi, key=lambda x: -x["costo"]):
            print(f"    {x['n']:<14} {x['p']:.0%}   se perde -{x['costo']:.3f}   entra {x['sostituto']}")

    differenze = confronta(py, js)
    if differenze:
        print("\n  DIFFERENZE fra i due motori:")
        for d in differenze:
            print("   -", d)
        print()
        sys.exit(1)
    print("\n  OK: i due motori danno gli stessi numeri.\n")
