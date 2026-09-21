// Server usa e getta: riceve i PNG dal canvas del browser e li scrive su disco.
const http = require('http'), fs = require('fs'), path = require('path');
const DEST = '/Users/marco/Documents/Fantacalcio Marco/logo';
http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', '*');
  if (req.method === 'OPTIONS') { res.end(); return; }
  let corpo = '';
  req.on('data', c => corpo += c);
  req.on('end', () => {
    try {
      const { nome, dati } = JSON.parse(corpo);
      const file = path.join(DEST, path.basename(nome));
      fs.writeFileSync(file, Buffer.from(dati.split(',')[1], 'base64'));
      console.log('scritto', file, fs.statSync(file).size, 'byte');
      res.end('ok');
    } catch (e) { console.log('errore', e.message); res.statusCode = 500; res.end('ko'); }
  });
}).listen(8766, () => console.log('in ascolto su 8766'));
