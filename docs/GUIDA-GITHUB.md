# Mettere l'app online — passo passo

**Parti 1 e 2 già fatte il 5 settembre 2026**: l'app è su
<https://mxalfaxl.github.io/fc-cazzimma/> e il repository privato
`fc-cazzimma-dati` esiste. Restano la parte 3, il token, e la parte 4, i
dispositivi. Il resto della guida è qui per quando servirà rifare qualcosa.

Alla fine avrai l'icona sulla schermata Home di ogni dispositivo, e gli stessi
dati ovunque.

Due repository, perché fanno due mestieri diversi: uno **pubblico** con il
codice dell'app, uno **privato** con i tuoi dati. Chiunque abbia l'indirizzo
può aprire l'app, ma senza il tuo token non vede niente di tuo — vedrebbe
solo un'app vuota.

---

## Parte 1 — Il repository del codice

1. Se non ce l'hai, fatti un account su **github.com**. È gratis e basta
   una mail.

2. In alto a destra, **+ → New repository**.
   - Repository name: `fc-cazzimma`
   - Visibilità: **Public**
   - Non serve spuntare altro. **Create repository**.

3. Nella pagina che si apre, clicca **uploading an existing file**
   (oppure *Add file → Upload files*).
   Trascina dentro i **sei file** che trovi nello zip:

   ```
   index.html
   manifest.webmanifest
   sw.js
   icona-180.png
   icona-192.png
   icona-512.png
   ```

   Devono stare in radice, non dentro una cartella. Poi **Commit changes**.

4. Vai su **Settings** (in alto nel repository) → **Pages** nella colonna
   di sinistra.
   - Source: *Deploy from a branch*
   - Branch: **main**, cartella **/ (root)** → **Save**

   Dopo un paio di minuti in cima alla pagina compare il tuo indirizzo:

   ```
   https://mxalfaxl.github.io/fc-cazzimma/
   ```

   Se dà ancora errore, aspetta e ricarica: la prima pubblicazione è lenta.

---

## Parte 2 — Il repository dei dati

5. **+ → New repository**.
   - Repository name: `fc-cazzimma-dati`
   - Visibilità: **Private**
   - Spunta **Add a README file** — questo passaggio conta: un repository
     completamente vuoto non ha un ramo su cui scrivere, e l'app non
     riuscirebbe a salvare.
   - **Create repository**.

---

## Parte 3 — Il token

6. Clicca la tua foto profilo in alto a destra → **Settings**.
   Poi, in fondo alla colonna di sinistra, **Developer settings**.

7. **Personal access tokens → Fine-grained tokens → Generate new token**.
   - Token name: `cazzimma`
   - Expiration: scegli **una data oltre la fine della stagione**
   - Repository access: **Only select repositories** → seleziona
     `fc-cazzimma-dati`
   - **Repository permissions** → cerca **Contents** → mettilo su
     **Read and write**
   - In fondo, **Generate token**

8. **Copia subito il token.** GitHub te lo mostra una volta sola: se chiudi
   la pagina devi rigenerarlo. Inizia con `github_pat_`.

---

## Parte 4 — Collegare i dispositivi

9. Sul telefono apri **Safari** e vai su `https://mxalfaxl.github.io/fc-cazzimma/`.
   Prima di tutto: **Condividi → Aggiungi alla schermata Home**. L'icona sulla
   Home ha una memoria separata da Safari, quindi il collegamento va fatto
   dall'icona, non da Safari.

10. Apri l'app dall'icona. Compare la schermata **Primo accesso**.

11. Compila:
    - Utente GitHub: il tuo nome utente
    - Repository dei dati: `fc-cazzimma-dati`
    - Token: incollalo
    - Una password a tua scelta, ripetuta. Almeno 6 caratteri.
    - Lascia la spunta su **Resta collegato su questo dispositivo** se non
      vuoi riscrivere la password a ogni apertura.

    Premi **Configura e entra**. L'app controlla che il token apra davvero il
    repository, poi lo salva sul dispositivo **cifrato con la password**. Da
    qui in avanti il token non lo rivedi più: serve solo la password, e solo
    se togli la spunta o premi **Esci** nelle impostazioni.

12. Ripeti i punti 9-11 su iPad e Mac. Stesso token, stessa password o
    un'altra, come preferisci: la password è per dispositivo.

Chi apre il link senza token vede solo la schermata di accesso, e con un
token sbagliato l'app non entra. I dati stanno nel repository privato e nel
tuo dispositivo, cifrati.

**Se dimentichi la password**: nella schermata di accesso premi *Password
dimenticata? Ricomincia con il token* e rifai il primo accesso. La rosa non
si perde: è su GitHub.

## Se qualcosa non torna

**La pagina Pages dà 404.** Aspetta due minuti e ricarica. Controlla che
`index.html` sia in radice e non dentro una sottocartella.

**"Token non valido o scaduto".** Attenzione agli spazi davanti o dietro
quando incolli. Se non basta, rigenera il token.

**"Utente o password sbagliati".** L'utente è il nome GitHub, e la password
è quella scelta su quel dispositivo. Se non la ricordi, *Password
dimenticata? Ricomincia con il token*.

**"Il token non apre il repository dei dati".** Torna al token e verifica
due cose: che punti a `fc-cazzimma-dati` e che *Contents* sia su
**Read and write**, non su *Read-only*.

**"il repository è vuoto".** Non hai spuntato *Add a README file*. Aprilo,
*Add file → Create new file*, chiamalo `README.md`, scrivici qualsiasi cosa
e salva.

**Ho perso il token.** Nessun problema: revocalo su GitHub e generane un
altro. I dati stanno nel repository, non nel token.

---

## Due cose da sapere

**Il listone viaggia da solo.** Una volta collegata, l'app salva anche il
listone nel repository dei dati: lo incolli sul Mac e lo ritrovi sul
telefono senza rifare niente.

**Ogni salvataggio diventa una versione su GitHub.** Non devi fare backup:
se combini un guaio, la cronologia del repository `fc-cazzimma-dati` ti
riporta indietro di un giorno, di una settimana, di quello che serve.

---

## Scorciatoia dal Mac

Se preferisci, con Claude Code e `gh` installato le parti 1, 2 e 4 si fanno
in due comandi invece che a mano. Il token della parte 3 va comunque creato
dall'interfaccia web: GitHub non permette di generare token fine-grained da
riga di comando.
