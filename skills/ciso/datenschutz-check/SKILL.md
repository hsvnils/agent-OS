---
name: datenschutz-check
version: 1.0.0
beschreibung: Prueft neue Datenfluesse, Werkzeuge und Dienste auf Datenschutz (DSGVO, BDSG, TDDDG) und haelt die KI-Nutzung im Rahmen der CEO-Entscheidungen.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A3/A5, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Datenschutz-Check (CISO, mit dem CLO)

## Wann anwenden
Bei jedem neuen oder geaenderten Datenfluss (`docs/datenfluesse.md`), neuen Diensten/Modellen, wenn personenbezogene
Daten Dritter (Kunden, Ansprechpartner, Fans, Freie) an ein externes Modell gehen koennten, bei Cookies/Tracking auf
Webseiten und bei Anfragen Betroffener (Auskunft, Loeschung).

## Grundlagen (Kurzfassung; Wortlaut der deutschen Normen in `quellen.md`)
- **DSGVO** (Verweis, EUR-Lex): Grundsaetze (Art. 5), Rechtsgrundlage (Art. 6, z. B. Vertrag oder berechtigtes
  Interesse), Informationspflichten (Art. 13/14), Betroffenenrechte (Art. 15-21), Auftragsverarbeitung (Art. 28,
  Vertrag mit dem Dienst), Verzeichnis (Art. 30), Sicherheit (Art. 32), Datenpanne 72 h (Art. 33), Drittland (Art. 44 ff.).
- **TDDDG § 25**: Speichern/Auslesen auf Endgeraeten (Cookies, Pixel) nur mit Einwilligung, ausser technisch noetig.
- **BDSG § 26**: Beschaeftigtendaten; **BDSG § 38**: Datenschutzbeauftragter erst ab 20 Personen mit staendiger
  automatisierter Verarbeitung.
- Hausregeln: `docs/datenschutz-ki-nutzung.md` (CEO-Entscheidungen 2026-09-29) -- Buchhaltung und Belege bleiben lokal,
  der Chat laeuft ueber Gemini, Training laut Bedingungen nein.

## Checkliste
1. Welche Daten, von wem (Personenbezug?), wohin (Dienst, Land), wie lange?
2. Rechtsgrundlage und Information der Betroffenen (Datenschutzerklaerung, Hinweis im Vertrag).
3. Auftragsverarbeitung/Bedingungen des Dienstes vorhanden? Drittland (USA) -> Grundlage pruefen.
4. Datensparsamkeit: geht es lokal (MACO470) oder ohne Personenbezug?
5. Eintrag in `docs/datenfluesse.md` und ggf. `docs/datenschutz-ki-nutzung.md` vorhanden?

## Ausgabe
Ampel je Datenfluss, Fundstelle, konkrete Massnahme, offene Fragen an Datenschutz-Fachleute. Kopfzeile „Entwurf --
keine Rechtsberatung“; Recht ist CEO-Tor.
