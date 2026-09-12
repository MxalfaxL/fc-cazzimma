// OCR di pagine scansionate con Vision di macOS. Lo compila leggi_gazzetta.py al bisogno.
// Uso diretto: xcrun swiftc -O motore/ocr_pagina.swift -o dati/gazzetta/.ocr && dati/gazzetta/.ocr pagina.png
import Foundation
import Vision
import AppKit

for percorso in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: percorso),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        FileHandle.standardError.write("non leggo \(percorso)\n".data(using: .utf8)!); continue
    }
    let richiesta = VNRecognizeTextRequest()
    richiesta.recognitionLevel = .accurate
    richiesta.recognitionLanguages = ["it-IT"]
    richiesta.usesLanguageCorrection = true
    let gestore = VNImageRequestHandler(cgImage: cg, options: [:])
    do { try gestore.perform([richiesta]) } catch {
        FileHandle.standardError.write("errore su \(percorso): \(error)\n".data(using: .utf8)!); continue
    }
    // ordina per colonna (x) grossolana e poi per y: il giornale e' a colonne
    let oss = richiesta.results ?? []
    let righe = oss.map { (o) -> (Double, Double, String) in
        (Double(o.boundingBox.minX), Double(1 - o.boundingBox.maxY), o.topCandidates(1).first?.string ?? "")
    }.sorted { a, b in
        let ca = Int(a.0 * 6), cb = Int(b.0 * 6)   // sei colonne
        return ca != cb ? ca < cb : a.1 < b.1
    }
    print("===== \(percorso)")
    for r in righe { print(r.2) }
}
