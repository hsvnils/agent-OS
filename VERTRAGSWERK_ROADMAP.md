# Roadmap: Vertragswerk (Vorlagen-Bibliothek, Vertrag je Auftrag, AGB am Angebot)
- Status: in Umsetzung
- Stand: 2026-10-05
- Arbeitsbranch: `ai/plan-konzept-vertrag` (Plan); Umsetzung auf eigenem Branch
- Basiscommit: `6636d02`
- Naechster Schritt: V1+V2 gebaut (2026-10-05); CEO laedt die ersten Entwuerfe, liest sie; CLO-Ausbau (C1-C4) erzeugt Pruefbericht + Version 2; dann anwaltliche Pruefung (CEO-Tor); danach Go fuer V3/V4.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-05)

„Wir sollten auch was wie unser ‚Vertragswerk‘ im System einbauen.“ -- Vorlagen-Bibliothek, ein Vertrag je Auftrag und
AGB am Angebot (CEO-Entscheidung 2026-10-05).

## Analyse (read-only, 2026-10-05)

- Heute keine Vertragstexte im System: Firmenakte kennt nur die Dokumentart „Vertrag“ (Upload). Rechtlich relevante
  Bausteine stehen verstreut: Katalog-Zuschlaege **Nutzungsrechte Social 6 Monate, Whitelisting/Paid Ads, Nutzung
  ausserhalb Social, Branchenexklusivitaet 3 Monate, Vorgegebenes Skript**; Fusstext „Kennzeichnung als Werbung“;
  Zahlungsbedingungen inkl. Vorkasse (Etappe 18); Kleinunternehmer-Hinweis (§ 19 UStG).
- Der **CLO-Agent** (`agents/13_clo.md`) liefert nur Entwuerfe „Entwurf -- anwaltliche Pruefung erforderlich“; ein
  Anwalt zeichnet; jede rechtliche Verbindlichkeit ist CEO-Tor (`AGENTS.md` 4, 5.4).
- Vorhandene Texte: keine (CEO 2026-10-05) -- CLO entwirft.

## Grundsaetze

- **Nur gepruefte Vorlagen gehen raus:** jede Vorlage hat Versionen mit Status *Entwurf* / *anwaltlich geprueft am …
  von …* / *ausser Kraft*. An Kunden (Vertrag, AGB-Anhang) darf nur eine gepruefte Version; bis dahin ist alles klar
  als „Entwurf“ markiert und nur intern nutzbar.
- **Was galt, bleibt fest:** Am Angebot/Auftrag wird die verwendete Vorlagen-Version festgeschrieben (wie die
  Konditionen) -- spaetere Aenderungen der Vorlage aendern bestehende Vertraege nie.
- Keine digitale Signatur-Plattform in dieser Roadmap (waere ein neuer, ggf. kostenpflichtiger Dienst = CEO-Tor);
  unterschriebene Vertraege werden als PDF zurueck in die Firmenakte gelegt.

## Etappe V1: Vorlagen-Bibliothek

- Status: umgesetzt (2026-10-05) -- `core/vertraege.py` (Versionen, Status Entwurf/geprueft/ausser Kraft mit
  Pruefvermerk, „in Kraft“ = juengste gepruefte Version, Vergleich), Seite „📜 Vertragswerk“ (Geschaeft), aendern und
  pruefen nur CEO. Tests `test_vertraege.py` mit Gegenprobe; Browsertest 1300/820/402 px.
- Ziel / Scope: `core/vertraege.py`; Vorlagenarten **AGB, Kooperationsvertrag (Influencer-/Content-Kooperation),
  Nutzungsrechte-Vereinbarung, NDA**; Text in Paragraphen mit Platzhaltern (`{Kunde}`, `{Leistungen}`, `{Verguetung}`,
  `{Nutzungsrechte}`, `{Freigabe}` …); Versionen mit Status und Pruefvermerk (wer, wann, Dokument der Pruefung in der
  Akte); Bereich „📜 Vertragswerk“ in LUNA-OS (lesen, Version vergleichen, Status setzen nur CEO).
- Gate: Tests (Version festschreiben, nur gepruefte Version „freigegeben“, Vergleich); Browsertest 1300/820/402 px.
- Aufwand: mittel.

## Etappe V2: Erste Entwuerfe durch den CLO

- Status: Entwuerfe liegen vor (2026-10-05) -- **geschrieben von Claude Code, nicht vom CLO-Agenten** (Korrektur
  2026-10-05; CLO-Ausbau siehe `CLO_AUSBAU_ROADMAP.md`) -- `core/vertrag_entwuerfe.py` (AGB 14 §§, Kooperationsvertrag 11 §§,
  Nutzungsrechte 6 §§, NDA 6 §§, mit Platzhaltern); per Knopf „Erste Entwuerfe laden“ als Version 1 (Entwurf, Quelle „Entwurf Claude Code (ungeprueft)“).
  **Offen (CEO-Tor):** Lesen durch den CEO, anwaltliche Pruefung, dann Status „geprueft“.
- Ziel / Scope: CLO-Entwuerfe fuer AGB, Kooperationsvertrag, Nutzungsrechte-Vereinbarung, NDA -- passend zum Geschaeft
  (Kleinunternehmer, Social-Media-Kooperationen, Kennzeichnungspflicht, Nutzungsrechte/Whitelisting/Exklusivitaet wie
  die Katalog-Zuschlaege, Freigabeprozess aus der Konzept-Mappe, Zahlungsbedingungen/Vorkasse, Haftung, Kuendigung).
  Jeder Text traegt „Entwurf -- anwaltliche Pruefung erforderlich“. **CEO-Tor:** Auswahl und Beauftragung der
  Anwaeltin (Kosten) durch den CEO; erst nach Pruefung Status „geprueft“.
- Gate: Entwuerfe liegen vor; Pruefung extern (CEO).
- Aufwand: mittel (Text), Pruefung extern.

## Etappe V3: Vertrag je Auftrag

- Status: geplant
- Ziel / Scope: aus der geprueften Vorlage automatisch befuellt -- Parteien (Firmendaten/Kunde), Leistungen
  (Positionen/Postings), Verguetung + Zahlungsbedingungen, Nutzungsrechte/Whitelisting/Exklusivitaet aus den
  gewaehlten Zuschlaegen, Kennzeichnung, Freigabeprozess, Leistungszeitraum; Vorschau, PDF, Senden nach CEO-Klick
  (einzeln oder mit der Auftragsbestaetigung), Status *gesendet* / *unterschrieben zurueck* (Upload -> Firmenakte);
  Knoten „Vertrag“ in der Belegverfolgung; Handlungsbedarf „Vertrag noch nicht unterschrieben“.
- Gate: Tests (Platzhalter vollstaendig, festgeschriebene Version, ohne gepruefte Vorlage kein Versand);
  PDF-Pruefung; Browsertest.
- Aufwand: mittel.

## Etappe V4: AGB am Angebot und an der Auftragsbestaetigung

- Status: geplant
- Ziel / Scope: Verweis „Es gelten unsere AGB (Stand …)“ im Fusstext und die AGB als PDF-Anhang beim Senden von
  Angebot/AB -- nur mit gepruefter Version; die AGB-Version wird am Beleg festgeschrieben und im Belegblatt angezeigt.
- Gate: Tests (Version am Beleg, ohne gepruefte AGB kein Anhang/Verweis); Browsertest.
- Aufwand: klein.

## Nicht-Scope

Keine verbindliche Rechtsberatung, keine autonomen Vertragsabschluesse, keine E-Signatur-Plattform, keine Aenderung an
bestehenden Belegen.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md`, `docs/entscheidungs-register.md`.

## CEO-Entscheidungen (2026-10-05)

1. Umfang: **Vorlagen-Bibliothek + Vertrag je Auftrag + AGB am Angebot**.
2. Vorhandene Texte: **keine -- der CLO entwirft**, anwaltliche Pruefung vor dem ersten Einsatz.

## Definition of Done

V1, V3, V4 verifiziert (Rechner, iPad, iPhone 17 Pro); V2-Entwuerfe vom CEO gelesen und anwaltlich geprueft (Status
„geprueft“); erster echter Vertrag zu einem Auftrag gesendet und unterschrieben zurueck in der Akte.
