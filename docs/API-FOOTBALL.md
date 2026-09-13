# API-Football (api-sports.io) — scheda operativa

## VERIFICATO SUL CAMPO, 13 settembre 2026: il piano gratuito non serve

Provato con la chiave vera di Marco, chiamate reali. L'account è **Free**,
100 richieste al giorno. Per la stagione in corso ogni endpoint utile
risponde con un errore di piano:

```
{"errors": {"plan": "Free plans do not have access to this season,
             try from 2022 to 2024."}}
```

| Chiamata | Esito |
|---|---|
| `/status` | OK (non consuma quota) |
| `/leagues?name=Serie A&country=Italy` | OK: Serie A = **id 135**, stagione in corso = **2026** |
| `/injuries?league=135&season=2026` | **negato dal piano** |
| `/fixtures?league=135&season=2026&round=Regular Season - 4` | **negato dal piano** |
| `/players?league=135&season=2026&page=1` | **negato dal piano** |
| `/players?league=135&season=2024&page=1` | OK (20 risultati) |

**Trappola da ricordare**: in `/leagues` la stagione 2026 dichiara
`coverage.injuries = true`, `coverage.fixtures.lineups = true` eccetera. Quel
`coverage` dice che il dato **esiste**, non che il tuo piano lo **può
leggere**. L'unico modo di saperlo è chiamare e guardare `errors.plan`.

**Conseguenza**: col piano gratuito non si costruisce la pipeline della
stagione in corso. Le fonti restano Gazzetta (PDF), SOS Fanta (feed RSS) e le
pagine web. Se un giorno si passa a un piano a pagamento, il resto di questa
scheda è già pronto: host, header, endpoint e campi.

**La chiave** non sta in nessun file: portachiavi del Mac, vedi
`motore/chiave.py`. In GitHub Actions sarebbe il segreto `API_FOOTBALL_KEY`.

---

Nota sulla fonte: il sito ufficiale (`api-football.com/documentation-v3`) ha
risposto 403 a ogni lettura automatica in questa sessione (probabilmente
blocca i fetch senza browser vero). Quanto segue è ricostruito da fonti
secondarie affidabili: pagine "how to" ufficiali di API-FOOTBALL trovate via
ricerca, il corso Educative "Getting Soccer Data with Api-Football in
JavaScript" (che riproduce pagina per pagina la documentazione ufficiale), e
pacchetti open source che ne rispecchiano i modelli. **Prima di scrivere il
modulo Python, fai almeno una chiamata vera con la tua chiave e conferma i
nomi dei campi**, specialmente per `/injuries`, `/fixtures/events` (valori di
`type`/`detail`) e `/sidelined`, segnati sotto come da verificare.

---

## 1. Autenticazione e host

Ci sono due modi di avere una chiave, e cambiano host e header:

| Come hai l'account | Host da chiamare | Header con la chiave |
|---|---|---|
| Diretto su **api-sports.io** (dashboard.api-football.com) | `https://v3.football.api-sports.io` | `x-apisports-key: <CHIAVE>` |
| Tramite **RapidAPI** | `https://api-football-v1.p.rapidapi.com` | `x-rapidapi-key: <CHIAVE>` e `x-rapidapi-host: api-football-v1.p.rapidapi.com` |

Per un account diretto (quello che ti serve, presumo) l'header **unico e
sufficiente** è `x-apisports-key`. Non serve nessun `Authorization: Bearer`.

Esempio minimo in libreria standard:

```python
import json
import urllib.request

HOST = "https://v3.football.api-sports.io"
CHIAVE = "<CHIAVE>"

def chiamata(percorso, parametri=None):
    query = ""
    if parametri:
        query = "?" + urllib.parse.urlencode(parametri)
    richiesta = urllib.request.Request(
        HOST + percorso + query,
        headers={"x-apisports-key": CHIAVE},
    )
    with urllib.request.urlopen(richiesta) as risposta:
        corpo = json.loads(risposta.read())
        # gli header di rate limit sono su risposta.headers, vedi sezione 2
        return corpo
```

---

## 2. Limiti (piano gratuito) e header del rate limit

- **100 richieste al giorno** (piano free), reset giornaliero.
- **10 richieste al minuto** (piano free) — indipendente dal limite giornaliero.
- Il piano free ha accesso a tutti gli endpoint, ma le stagioni storiche
  disponibili sono limitate (verifica quali stagioni ti restituisce
  `/leagues` per la Serie A prima di fare affidamento su dati vecchi).

Ogni risposta porta **quattro header** utili per non sforare:

```
x-ratelimit-requests-limit: 100        # richieste/giorno assegnate dal piano
x-ratelimit-requests-remaining: 87      # richieste/giorno rimaste oggi
X-RateLimit-Limit: 10                   # richieste/minuto assegnate dal piano
X-RateLimit-Remaining: 7                # richieste/minuto rimaste in questo minuto
```

Leggili sempre e fermati (o rallenta) quando `remaining` si avvicina a 0,
invece di aspettare l'errore 429. In `urllib` sono su
`risposta.headers.get("x-ratelimit-requests-remaining")` (case-insensitive).

Errore tipico quando sfori: corpo JSON con `errors.rateLimit` o
`errors.requests` invece dei dati attesi — controlla sempre se `response` è
vuoto e `errors` non lo è.

---

## 3. Paginazione

Ogni risposta ha un blocco:

```json
"paging": { "current": 1, "total": 3 }
```

Se `total > current`, ci sono altre pagine: ripeti la chiamata aggiungendo
`page=2`, `page=3`, ecc. ai parametri. La dimensione della pagina **varia per
endpoint** (esempio noto: `/players` pagina a 20 risultati); non dare per
scontato un numero fisso, e verificalo empiricamente per gli endpoint che usi
(in particolare `/players` per le statistiche stagione, che con la Serie A
intera richiede più pagine).

---

## 4. Identificare un giocatore

Il giocatore porta sempre:

```json
"player": {
  "id": 909,
  "firstname": "Lautaro",
  "lastname": "Martínez",
  "name": "L. Martinez"
}
```

- `id` è l'unico identificatore stabile: usalo come chiave, mai il nome.
- `name` è il nome "corto" mostrato ovunque (iniziale del nome + cognome):
  per un sudamericano tipicamente **"L. Martinez"**, non "Lautaro Martinez".
  Per un italiano è uguale: es. "N. Barella" non "Nicolò Barella".
- `firstname`/`lastname` sono i nomi completi, utili per il fuzzy-match sui
  cognomi che incolli dal listone o dalle probabili (che di solito riportano
  solo il cognome, es. "Barella").
- **Per abbinare ai tuoi nomi**: usa `lastname` (o l'ultima parola di `name`
  dopo il punto) come chiave di match sul cognome, e tieni `id` come chiave
  primaria una volta risolto l'abbinamento — non ri-matchare per nome ogni
  volta.

---

## 5. Endpoint, uno per uno

### `/leagues` — trovare l'id Serie A e la stagione corrente

```
GET https://v3.football.api-sports.io/leagues?name=Serie A&country=Italy
```

Parametri utili: `id`, `name`, `country`, `code`, `season`, `current` (bool,
filtra solo la stagione in corso), `type` (`league` o `cup`), `search`,
`team`, `last`.

Campi principali risposta:

```json
{
  "league": { "id": 135, "name": "Serie A", "type": "League", "logo": "..." },
  "country": { "name": "Italy", "code": "IT", "flag": "..." },
  "seasons": [
    { "year": 2026, "start": "2026-08-...", "end": "2027-05-...",
      "current": true,
      "coverage": {
        "fixtures": { "events": true, "lineups": true, "statistics_fixtures": true, "statistics_players": true },
        "standings": true,
        "players": true,
        "top_scorers": true,
        "injuries": true,
        "predictions": true,
        "odds": true
      }
    }
  ]
}
```

**Trappola**: controlla sempre `seasons[].coverage.injuries` (e gli altri
flag di `coverage`) prima di fidarti di un endpoint per la Serie A —
se `false`, quell'endpoint non è alimentato per quella lega/stagione, e non
otterrai un errore ma solo un risultato vuoto che sembra "nessun dato".

L'id della **Serie A è 135** (valore noto e stabile su api-sports; confermalo
comunque con la chiamata sopra). La stagione 2026/27 si esprime come
**`season=2026`** (anno di inizio, singolo, non "2026-27" — vedi trappole).

### `/teams` — le 20 squadre di Serie A

```
GET https://v3.football.api-sports.io/teams?league=135&season=2026
```

Parametri: `id`, `name`, `league`+`season` (insieme), `country`, `code`,
`search` (min. 3 caratteri).

Campi principali:

```json
{
  "team": {
    "id": 505, "name": "Inter", "code": "INT", "country": "Italy",
    "founded": 1908, "national": false, "logo": "..."
  },
  "venue": {
    "id": 907, "name": "Giuseppe Meazza", "address": "...", "city": "Milano",
    "capacity": 75923, "surface": "grass", "image": "..."
  }
}
```

### `/fixtures` — partite di una giornata

```
GET https://v3.football.api-sports.io/fixtures?league=135&season=2026&round=Regular Season - 5
GET https://v3.football.api-sports.io/fixtures?league=135&season=2026&date=2026-10-04
```

Parametri principali: `id`, `ids`, `live` (`all` o lista id lega separata da
`-`), `date` (YYYY-MM-DD), `league`+`season`, `team`, `last` (ultime N,
due cifre), `next` (prossime N), `from`/`to` (intervallo date), `round`,
`status` (es. `NS`, `FT`, `LIVE`), `timezone`.

**Il `round` per la Serie A si scrive per esteso**, come restituito da
`/fixtures/rounds?league=135&season=2026`, nella forma:

```
Regular Season - 1
Regular Season - 2
...
Regular Season - 38
```

(spazi e trattino inclusi, case sensitive). Recupera sempre la lista vera con
`/fixtures/rounds` invece di costruirla a mano: le coppe cambiano formato
("Group Stage - 1", ecc.), il campionato no, ma è comunque più sicuro leggerla.

Campi principali risposta:

```json
{
  "fixture": {
    "id": 1234567, "referee": "...", "timezone": "UTC",
    "date": "2026-10-04T13:00:00+00:00", "timestamp": 1759582800,
    "periods": { "first": 1759582800, "second": null },
    "venue": { "id": 907, "name": "Giuseppe Meazza", "city": "Milano" },
    "status": { "long": "Not Started", "short": "NS", "elapsed": null }
  },
  "league": { "id": 135, "name": "Serie A", "country": "Italy", "season": 2026, "round": "Regular Season - 5" },
  "teams": {
    "home": { "id": 505, "name": "Inter", "logo": "...", "winner": null },
    "away": { "id": 500, "name": "Bologna", "logo": "...", "winner": null }
  },
  "goals": { "home": null, "away": null },
  "score": {
    "halftime": { "home": null, "away": null },
    "fulltime": { "home": null, "away": null },
    "extratime": { "home": null, "away": null },
    "penalty": { "home": null, "away": null }
  }
}
```

### `/fixtures/lineups` — formazioni ufficiali

```
GET https://v3.football.api-sports.io/fixtures/lineups?fixture=1234567
```

Parametri: `fixture` (obbligatorio), `team`, `player`, `type`
(`Formation`/`Coach`/`startXI`/`Substitutes`).

```json
{
  "team": { "id": 505, "name": "Inter", "logo": "..." },
  "coach": { "id": 123, "name": "Cristian Chivu", "photo": "..." },
  "formation": "3-5-2",
  "startXI": [
    { "player": { "id": 909, "name": "L. Martinez", "number": 10, "pos": "F", "grid": "1:1" } }
  ],
  "substitutes": [
    { "player": { "id": 999, "name": "M. Thuram", "number": 9, "pos": "F", "grid": null } }
  ]
}
```

**Trappola nota**: per il piano gratuito le formazioni ufficiali diventano
disponibili di solito **20-40 minuti prima del fischio d'inizio**, non
prima. Non affidarti a `/fixtures/lineups` per pianificare con largo anticipo:
resta il lettore delle probabili (già in `index.html`) lo strumento giusto per
il preavviso lungo.

### `/injuries` — infortunati (verifica consigliata prima dell'uso)

```
GET https://v3.football.api-sports.io/injuries?league=135&season=2026&team=505
GET https://v3.football.api-sports.io/injuries?fixture=1234567
GET https://v3.football.api-sports.io/injuries?league=135&season=2026&date=2026-10-04
```

Parametri: `league`+`season`, `team`, `player`, `fixture`, `date`, `timezone`.
Aggiornamento dichiarato ogni ~4 ore.

Struttura (nomi confermati da più fonti secondarie, **verifica il campo
esatto di gravità con una chiamata vera** — potrebbe chiamarsi `reason` o
essere annidato sotto `player.reason`):

```json
{
  "player": { "id": 909, "name": "L. Martinez", "photo": "..." },
  "team": { "id": 505, "name": "Inter", "logo": "..." },
  "fixture": { "id": 1234567, "timezone": "UTC", "date": "...", "timestamp": 0 },
  "league": { "id": 135, "season": 2026, "name": "Serie A", "country": "Italy" },
  "type": "Missing Fixture",
  "reason": "Hamstring Injury"
}
```

`type` distingue tipicamente infortunio vero da assenza per squalifica
(valori osservati altrove: `"Injury"` / `"Missing Fixture"`); `reason`
porta il dettaglio testuale libero ("Knee Injury", "Hamstring Injury",
"Suspended"). **Controlla `league.coverage.injuries` da `/leagues` prima**:
se `false` per la Serie A/stagione che usi, l'endpoint torna vuoto.

### `/players` — statistiche stagionali di un giocatore

```
GET https://v3.football.api-sports.io/players?id=909&season=2026
GET https://v3.football.api-sports.io/players?league=135&season=2026&team=505&page=1
```

Parametri: `id`, `league`+`season`, `team`, `search` (min. 3 caratteri),
`page`. **Paginazione a 20 risultati/pagina** su questo endpoint: per
scaricare tutta la Serie A (~25 giocatori × 20 squadre) servono più pagine,
controlla sempre `paging.total`.

Campi principali (`statistics` è una lista, un elemento per squadra/lega in
cui il giocatore ha giocato quella stagione):

```json
{
  "player": {
    "id": 909, "name": "Lautaro Martínez", "firstname": "Lautaro",
    "lastname": "Martínez", "age": 28,
    "birth": { "date": "1997-08-22", "place": "Bahía Blanca", "country": "Argentina" },
    "nationality": "Argentina", "height": "174 cm", "weight": "72 kg",
    "injured": false, "photo": "..."
  },
  "statistics": [
    {
      "team": { "id": 505, "name": "Inter", "logo": "..." },
      "league": { "id": 135, "name": "Serie A", "country": "Italy", "season": 2026 },
      "games": {
        "appearences": 5, "lineups": 5, "minutes": 450, "number": 10,
        "position": "Attacker", "rating": "7.200000", "captain": true
      },
      "substitutes": { "in": 0, "out": 1, "bench": 0 },
      "shots": { "total": 12, "on": 7 },
      "goals": { "total": 4, "conceded": 0, "assists": 1, "saves": null },
      "passes": { "total": 100, "key": 5, "accuracy": 82 },
      "tackles": { "total": 3, "blocks": 0, "interceptions": 1 },
      "duels": { "total": 40, "won": 22 },
      "dribbles": { "attempts": 10, "success": 6, "past": null },
      "fouls": { "drawn": 8, "committed": 3 },
      "cards": { "yellow": 1, "yellowred": 0, "red": 0 },
      "penalty": { "won": 1, "commited": 0, "scored": 1, "missed": 0, "saved": null }
    }
  ]
}
```

Campi che ti servono per il fantacalcio, nomi esatti:

- media voto: `statistics[].games.rating` — **è una stringa**, es.
  `"7.200000"`, convertila con `float(...)`.
- presenze: `statistics[].games.appearences` (occhio, è scritto con la "e"
  in più, tipico refuso storico dell'API, non "appearances").
- minuti: `statistics[].games.minutes`
- gol: `statistics[].goals.total`
- assist: `statistics[].goals.assists`
- cartellini: `statistics[].cards.yellow`, `.yellowred`, `.red`
- rigori segnati/sbagliati: `statistics[].penalty.scored`,
  `statistics[].penalty.missed` (anche `.won`, `.commited` — sì, con una
  sola "m", altro refuso noto — e `.saved` per i portieri)

### `/players/squads` — rose delle squadre

```
GET https://v3.football.api-sports.io/players/squads?team=505
GET https://v3.football.api-sports.io/players/squads?player=909
```

Parametri: `team` **oppure** `player` (uno dei due, non entrambi).

```json
{
  "team": { "id": 505, "name": "Inter", "logo": "..." },
  "players": [
    { "id": 909, "name": "Lautaro Martínez", "age": 28, "number": 10,
      "position": "Attacker", "photo": "..." }
  ]
}
```

Nota: qui **non c'è `rating`** né statistiche — solo l'anagrafica di rosa.
Per le statistiche usa `/players`.

### `/fixtures/players` — statistiche giocatore per singola partita

```
GET https://v3.football.api-sports.io/fixtures/players?fixture=1234567
```

Parametri: `fixture` (obbligatorio), `team`.

```json
{
  "team": { "id": 505, "name": "Inter", "logo": "..." },
  "players": [
    {
      "player": { "id": 909, "name": "L. Martinez", "photo": "..." },
      "statistics": [
        {
          "games": {
            "minutes": 90, "number": 10, "position": "F",
            "rating": "7.8", "captain": true, "substitute": false
          },
          "offsides": 1,
          "shots": { "total": 4, "on": 3 },
          "goals": { "total": 2, "conceded": 0, "assists": 0, "saves": null },
          "passes": { "total": 30, "key": 2, "accuracy": "90" },
          "tackles": { "total": 1, "blocks": 0, "interceptions": 0 },
          "duels": { "total": 8, "won": 5 },
          "dribbles": { "attempts": 3, "success": 2, "past": null },
          "fouls": { "drawn": 2, "committed": 1 },
          "cards": { "yellow": 0, "red": 0 },
          "penalty": { "won": 0, "commited": 0, "scored": 1, "missed": 0, "saved": null }
        }
      ]
    }
  ]
}
```

Stessa forma di `/players`, ma un solo elemento in `statistics` (quella
partita) e senza il livello `league`/`team` fuori da `player` (qui il `team`
sta un livello più su, condiviso da tutti i `players` di quella squadra).
`rating` qui è il voto vero e proprio della singola gara — quello che vuoi
per calcolare medie tue in stile Fantacalcio, alternativo al `rating`
stagionale già mediato di `/players`.

### `/fixtures/events` — gol, cartellini, sostituzioni

```
GET https://v3.football.api-sports.io/fixtures/events?fixture=1234567
```

Parametri: `fixture` (obbligatorio), `team`, `player`, `type`.

```json
{
  "time": { "elapsed": 63, "extra": null },
  "team": { "id": 505, "name": "Inter", "logo": "..." },
  "player": { "id": 909, "name": "L. Martinez" },
  "assist": { "id": null, "name": null },
  "type": "Goal",
  "detail": "Normal Goal",
  "comments": null
}
```

Valori noti di `type`/`detail` (**da confermare con una chiamata vera**, qui
riportati da fonti secondarie coerenti fra loro):

| `type` | `detail` | Significato |
|---|---|---|
| `Goal` | `Normal Goal` | gol normale |
| `Goal` | `Own Goal` | autogol |
| `Goal` | `Penalty` | rigore **segnato** |
| `Goal` | `Missed Penalty` | rigore **sbagliato** — attenzione: sotto `type: Goal` anche se non è un gol |
| `Card` | `Yellow Card` | ammonizione |
| `Card` | `Red Card` | espulsione diretta |
| `Card` | `Second Yellow card` | doppia ammonizione |
| `subst` | `Substitution 1` (numerato) | cambio |

Per contare rigori sbagliati filtra `type == "Goal" and detail == "Missed Penalty"`,
non per `type` diverso da `Goal` — è la trappola più facile da prendere qui.

### `/sidelined` — indisponibilità storiche (esiste, da verificare a fondo)

```
GET https://v3.football.api-sports.io/sidelined?player=909
GET https://v3.football.api-sports.io/sidelined?players=909-910-911
GET https://v3.football.api-sports.io/sidelined?coach=123
```

Parametri: `player` **o** `players` (fino a più id separati da `-`), oppure
`coach`/`coachs`. Dà lo storico completo di infortuni/squalifiche di quel
giocatore/allenatore, ciascuno con tipo e periodo:

```json
{
  "type": "Injury",
  "start": "2026-02-01",
  "end": "2026-02-20"
}
```

`end` può essere assente/`null` per un'indisponibilità ancora in corso.
Diverso da `/injuries`: questo è lo storico, non l'elenco degli indisponibili
alla prossima giornata. **Verifica con una chiamata vera se il tuo piano lo
include** — non è fra gli endpoint più citati nelle guide introduttive.

---

## 6. Trappole da tenere a mente

- **`season` è sempre un anno singolo**, es. `2026`, non `"2026-27"` né
  `"2026/2027"`. Rappresenta la stagione che *inizia* in quell'anno.
- **Copertura non garantita**: controlla sempre `seasons[].coverage` in
  `/leagues` per la combinazione lega+stagione che ti interessa, endpoint per
  endpoint (`injuries`, `predictions`, `odds`, `statistics_players`, ecc.),
  prima di considerare "vuoto" un dato che magari non è mai stato coperto.
- **Piano gratuito e stagione corrente**: alcuni endpoint sul piano free
  restituiscono con ritardo o non hanno ancora la stagione più recente subito
  a inizio campionato — se `season=2026` per la Serie A torna vuoto a inizio
  stagione, prova a controllare `current` su `/leagues` per vedere se la
  stagione è già "aperta" lato loro.
- **Refusi storici nei nomi campo**: `appearences` (non `appearances`),
  `commited` (una sola "m", non `committed`) — sono così anche nella API vera,
  non correggerli quando fai il parsing o non troverai il campo.
- **`rating` è una stringa**, non un numero — sempre da convertire.
- **Rate limit doppio**: il limite al minuto (10/min free) può bloccarti
  anche con richieste/giorno abbondanti residue: se fai un ciclo su tante
  squadre/giocatori, metti una pausa fra le chiamate, non fidarti solo del
  contatore giornaliero.
- **Lineups tardive**: non pianificare la formazione consigliata basandoti su
  `/fixtures/lineups`, arriva troppo tardi rispetto ai 15 minuti di deadline
  del regolamento della lega — resta il lettore delle probabili incollate a
  mano lo strumento giusto per l'anticipo.
- **Rigore sbagliato sotto `type: Goal`**: vedi tabella sopra, è la trappola
  più insidiosa di `/fixtures/events`.
