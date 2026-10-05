---
name: abschluss-check-euer
version: 1.0.0
beschreibung: Monats- und Jahresabschluss-Check fuer die Einnahmen-Ueberschuss-Rechnung (EStG § 4 Abs. 3) eines Kleinunternehmers.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A2, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Monats- und Jahresabschluss-Check EUeR (CFO)

## Wann anwenden
Zum Monatsende (Abgleich, offene Punkte), zum Jahresende (Vorbereitung EUeR fuer den Steuerberater) oder wenn der CEO
fragt „Wie steht das Jahr?“.

## Grundlagen (Kurzfassung, Wortlaut in `quellen.md`)
- **EStG § 4 Abs. 3**: Gewinn = Betriebseinnahmen minus Betriebsausgaben (Zufluss/Abfluss). **EStG § 11**: Zufluss-/
  Abflussprinzip; regelmaessig wiederkehrende Zahlungen rund um den Jahreswechsel (10-Tage-Regel) dem Jahr der
  wirtschaftlichen Zugehoerigkeit zuordnen.
- **EStG § 4 Abs. 5**: nicht abziehbare Betriebsausgaben (z. B. Geschenke ueber 50 € je Empfaenger und Jahr, Bewirtung
  nur 70 %, Wege Wohnung-Betrieb).
- **EStG § 6 Abs. 2/2a**: geringwertige Wirtschaftsgueter bis 800 € netto sofort absetzbar; Sammelposten 250-1.000 €.
- **AO § 141**: Buchfuehrungspflicht erst ab 800.000 € Umsatz oder 80.000 € Gewinn -- bis dahin genuegt die EUeR.
- **UStG § 19** (siehe CLO-Skill `kleinunternehmer-hinweise`): Grenzen 25.000 € (Vorjahr) / 100.000 € (laufendes Jahr).

## Checkliste Monat
1. Alle Zahlungseingaenge einer Rechnung zugeordnet; offene Posten und Mahnstufen aktuell.
2. Alle Ausgaben mit Beleg; fehlende Belege benennen.
3. Abos/wiederkehrende Kosten vollstaendig (Abo-Liste in LUNA-OS).
4. Umsatz kumuliert gegen die § 19-Grenzen.
5. Auffaelligkeiten (doppelte Buchung, ungewoehnliche Betraege, Privatanteile).

## Checkliste Jahr (zusaetzlich)
6. 10-Tage-Regel fuer Zahlungen um den Jahreswechsel.
7. Anlagegueter: GWG/Sammelposten/AfA richtig zugeordnet.
8. Nicht abziehbare Anteile (Geschenke, Bewirtung) getrennt.
9. Gutschriften, Stornos, Korrekturen nachvollziehbar.
10. Unterlagenpaket fuer den Steuerberater (EUeR-Uebersicht, Belegliste, offene Fragen).

## Ausgabe
Kurzbericht: Einnahmen, Ausgaben, Ergebnis, offene Posten, **Liste offener Punkte mit Fundstelle**, Fragen an den
Steuerberater. Zahlen nur aus den von LUNA gelieferten Daten -- fehlende Zahlen als Luecke benennen, nie schaetzen ohne
Kennzeichnung. Kopfzeile „Entwurf -- der Steuerberater zeichnet“.
