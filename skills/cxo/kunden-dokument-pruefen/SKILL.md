---
name: kunden-dokument-pruefen
version: 1.0.0
beschreibung: Prueft Dokumente an Kunden (Angebote, Konzepte, Projektberichte, Mails) auf Verstaendlichkeit, Ton, Vollstaendigkeit und Erscheinungsbild.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A5, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Kunden-Dokument pruefen (CXO)

## Wann anwenden
Bevor ein Angebot, eine Konzept-PDF, ein Projektbericht, eine Mahnung oder eine Mail an einen Kunden geht.

## Checkliste
1. **Verstaendlich:** Was bekommt der Kunde, was kostet es, was muss er tun, bis wann? In den ersten Zeilen.
2. **Ton:** freundlich, klar, Hanserautisch-Stimme (CBO-Skill `markenstimme`); bei Mahnungen sachlich.
3. **Richtig:** Kundenname exakt (z. B. KIEZALM), Ansprechpartner, Nummern, Daten, Betraege, Anlagen.
4. **Vollstaendig:** Pflichthinweise (§ 19 UStG auf Rechnung/Angebot), Werbekennzeichnung im Konzept, Kontakt.
5. **Erscheinungsbild:** Briefkopf/Logo, keine leeren Platzhalter, Seitenumbrueche sauber, am Handy lesbar (PDF).

## Ausgabe
Liste der Befunde mit Stelle und Vorschlag (Formulierung), Gesamturteil versandbereit ja/nein. Versand = CEO-Tor.
