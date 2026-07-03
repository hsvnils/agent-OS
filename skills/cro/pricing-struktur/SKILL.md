---
name: pricing-struktur
version: 1.0.0
beschreibung: Definiert Kooperations-Pakete und eine transparente Richtpreis-Logik als Basis fuer Angebote.
lizenz: intern
autor: Head of Agents
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Paket-/Pricing-Struktur (CRO)

Legt **wiederverwendbare Kooperations-Pakete** und eine **nachvollziehbare Preis-Logik** fest -- die Grundlage,
auf die der Skill `kooperation-bewerten` beim Kalkulieren zurueckgreift. Ziel: konsistente, faire Angebote
statt Bauchgefuehl.

## Wann anwenden
Wenn ein Angebot/Paket kalkuliert werden soll, oder wenn der CEO die Preisstruktur festlegen/aktualisieren will.

## Pakete (Bausteine)
Definiere je Leistung ein Paket; typische Bausteine:
- **Feed-Post** (1 Bild/Karussell), **Reel** (Produktion aufwendiger -> hoeher), **Story-Set** (mehrere Frames),
  **Kampagne** (Mehrteiler ueber Zeitraum), **Ambassador/laufend** (monatlich, Vorzugskonditionen).
- Add-ons: **Nutzungsrechte** (Partner darf den Content schalten/lizenzieren -> Zuschlag), **Exklusivitaet**
  (keine Wettbewerber im Zeitraum -> Zuschlag), **Express/Deadline** (Zuschlag), **Whitelisting/Spark Ads**.

## Preis-Logik (transparent, nicht erfunden)
- **Basiswert** je Format = Richtwert **pro 1.000 Follower**, gewichtet mit dem **Engagement-Faktor**
  (Engagement-Rate ueber Schnitt -> oberes Ende; darunter -> unteres Ende). Reichweite/Engagement kommen aus
  `social_media_analyzer`.
- **Aufschlaege** additiv: Reel- vs. Feed-Faktor, Nutzungsrechte, Exklusivitaet, Express.
- **Immer eine Spanne** (von--bis) mit offengelegten Annahmen; nie eine erfundene Fixzahl.
- **Richtwert je 1.000 Follower ist eine CEO-Vorgabe.** Ist sie in `finance/`/Charta hinterlegt -> diese nehmen.
  Sonst: eine **begruendete Annahme** klar als solche kennzeichnen und dem CEO zur Bestaetigung vorlegen.

## Marktbenchmark (2026, Referenz -- KEINE Vorgabe)
Nur zur Einordnung/Plausibilisierung; der verbindliche Preis ist eine CEO-Entscheidung.
- **Tier Micro (10k-100k Follower):** ~500-5.000 USD je Feed-Post -- grosse Spanne, stark abhaengig von
  Engagement/Nische. (Nano <10k deutlich weniger; Mid >100k deutlich mehr.)
- **Grobe Faustregel Startwert:** ~10 USD je 1.000 Follower fuer einen Feed-Post, dann mit Engagement-/
  Nischen-/Regions-Faktor anpassen (USD ~ EUR fuer die grobe Einordnung).
- **Format:** Reel 1,5-3x Feed-Post; Story deutlich guenstiger.
- **Engagement:** > ~5% Engagement-Rate -> 40-60% Aufschlag ueblich.
- **Publikum:** DACH/westlich -> +20-40% ggue. Schwellenmaerkten.
- Quellen: Influencer Marketing Hub / Later / Shopify (2026-Benchmarks).

## Output (an den Head of Agents)
Eine kompakte **Paket-/Preis-Tabelle**: Paket · Leistung · Richtpreis-Spanne · Aufschlag-Optionen · Annahmen.
Bei Bedarf zusaetzlich eine Empfehlung, welches Paket zur konkreten Anfrage passt.

## Grenzen (CEO-Tor)
Verbindliche Preise/Rabatte/Vertraege (Geld/Recht) entscheidet der CEO. Dieser Skill liefert die
**Struktur + Richtwerte als Entwurf** -- keine autonome Zusage.
