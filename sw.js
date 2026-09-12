/* Cache dell'app, così si apre anche senza rete: la sera dell'asta la rete
   del locale va e viene, e l'app deve esserci lo stesso, font compresi.
   Le chiamate a GitHub non passano di qui: quelle vanno sempre in rete.

   Quando cambia qualcosa nell'app, alza VERSIONE: il vecchio guscio viene
   buttato e il nuovo scaricato alla prima apertura con rete. */
const VERSIONE = '2026.09.12g';
const CACHE = 'cazzimma-' + VERSIONE;
const FONT = 'cazzimma-font';
const GUSCIO = ['./', './index.html', './manifest.webmanifest',
                './icona-180.png', './icona-192.png', './icona-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(GUSCIO)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(chiavi => Promise.all(chiavi.filter(k => k !== CACHE && k !== FONT).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.hostname === 'api.github.com') return;

  // font: prima la copia salvata, la rete solo se manca. Cambiano mai.
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
    e.respondWith(caches.open(FONT).then(async c => {
      const salvata = await c.match(e.request);
      if (salvata) return salvata;
      try {
        const r = await fetch(e.request);
        if (r.ok) c.put(e.request, r.clone());
        return r;
      } catch (err) {
        return new Response('', {status: 503});
      }
    }));
    return;
  }

  // il resto dell'app: prima la rete (così gli aggiornamenti arrivano),
  // se manca la copia salvata. Solo le pagine ripiegano su index.html.
  e.respondWith(
    fetch(e.request)
      .then(r => {
        if (r.ok && url.origin === location.origin) {
          const copia = r.clone();
          caches.open(CACHE).then(c => c.put(e.request, copia));
        }
        return r;
      })
      .catch(() => caches.match(e.request).then(r => {
        if (r) return r;
        if (e.request.mode === 'navigate') return caches.match('./index.html');
        return new Response('', {status: 504});
      }))
  );
});
