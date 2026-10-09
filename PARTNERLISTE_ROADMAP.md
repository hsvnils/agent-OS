# Roadmap: Liste potenzieller Partner und Kunden (Akquise-Ideen)

- Status: in Umsetzung
- Stand: 2026-10-09
- Arbeitsbranch: `ai/zeitgrund-partnerliste`
- Basiscommit: `a680e53`
- Naechster Schritt: Deploy (CEO), dann Abnahme durch den CEO (Telegram-Test) und Roadmap abschliessen.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-09)

„Potenzielle Partner- oder Kunden-Liste einfuehren, um Unternehmen zu sammeln, die wir bzgl. Zusammenarbeit ansprechen
koennten. Per Telegram Ideen fuer neue Unternehmen aufnehmen, um sie spaeter anzuschreiben, ob Interesse an einer
Partnerschaft besteht.“

## Analyse (read-only, 2026-10-09)

- Kundenstamm (`core/kunden.py`): Typen kunde/lieferant/partner/**interessent**; liegt in der Buchhaltungs-**Kette**
  (unveraenderbar, nichts loeschbar). Live: 24 Lieferanten, 9 Kunden, 1 Partner, 0 Interessenten.
- Vorstellungs-Mails (`SERIEN_UND_VORSTELLUNG_ROADMAP.md`, V1/V2 live): „✉️ Neue Mail“ legt eine Firma **erst beim Senden**
  als Interessent an, Reiter „✉️ Vorstellungen“ und „Interessenten“, Nachfassen nach 7 Tagen. Es fehlt die **Vorstufe**:
  ein Merkzettel fuer Firmen, die noch nicht angeschrieben sind.
- Collab-CRM (Instagram-Partner, Supabase `crm_*`) haengt am verworfenen Meta-Postfach (Register 2026-09-29) -> nicht
  wiederbeleben, sondern die neue Liste im Bereich Kunden bauen.
- Recht: Anschreiben bleibt an den bestehenden UWG-Hinweis der Vorstellungs-Mail gebunden; die Liste selbst ist nur intern.

## Etappe P1: Liste „💡 Ideen“ im Bereich Kunden

- Status: umgesetzt
- Ziel / Scope: Neuer Reiter **„💡 Ideen“** neben Vorstellungen/Interessenten: Firma, Art (**potenzieller Kunde** /
  **potenzieller Partner**), Branche, Ort, Website/Instagram, Mail/Ansprechpartner (optional), Warum (Notiz), Quelle
  (OS/Telegram), Datum, Status **Idee -> angeschrieben -> Interessent / kein Interesse**. Anlegen, bearbeiten, loeschen.
  Speicher **getrennt vom Kundenstamm** (`akquise/log.jsonl` auf der NAS, nicht in der Kette -> loeschbar, im Backup,
  vom Deploy ausgenommen). Dubletten-Hinweis gegen Ideen und Kundenstamm (Name/Domain).
- Nicht-Scope: automatisches Anschreiben (Oeffentlichkeit = CEO-Tor), Massenimport.
- Gate: Tests (Anlegen/Aendern/Loeschen, Dublette, nicht in der Kette, Gegenprobe); Browser Rechner/iPad/iPhone.
- Aufwand: mittel.

## Etappe P2: Ideen per Telegram

- Status: umgesetzt
- Ziel / Scope: Satz an LUNA, z. B. „Idee: Elbphilharmonie Gastro – passt fuer Food-Reels“ oder „Merk dir Kiez Burger als
  moeglichen Partner“ -> LUNA legt die Idee an und antwortet mit Zusammenfassung + Knopf „↩️ Rueckgaengig“. Erkennung
  regelbasiert (Woerter Idee/merk dir/potenzieller Partner/Kunde), zusaetzlich als LUNA-Werkzeug, damit auch freie Saetze im
  Chat funktionieren (Werkzeugauswahl, Token-Grenze beachten). Optional: „🔎 Daten suchen“ ergaenzt Website/Ort ueber die
  vorhandene Brave-Suche (kein neuer Dienst) -- nur auf Klick.
- Gate: Tests (Erkennung, Rueckgaengig, kein Eintrag bei normalem Chat, Gegenprobe); echter Telegram-Test durch den CEO.
- Aufwand: klein bis mittel.

## Etappe P3: Von der Idee zur Vorstellungs-Mail

- Status: umgesetzt
- Ziel / Scope: In jeder Idee Knopf **„✉️ Anschreiben …“** -> oeffnet die vorhandene Vorstellungs-Mail mit Firma, Mail und
  passender Vorlage (Kunde bzw. Partner; neue Textbaustein-Vorlage „Partnerschaft“). Nach dem Senden: Idee = „angeschrieben“,
  Firma wird wie heute Interessent; Antwort/Nachfassen laufen ueber V2. „Kein Interesse“ schliesst die Idee.
- Gate: Tests (Statuswechsel, Verknuepfung Idee -> Vorstellung -> Interessent); Browsertest; Senden nur per Klick.
- Aufwand: klein.

## Umsetzung (2026-10-09, Go CEO fuer P1-P3)

- P1: `core/akquise.py` (`IdeenStore`, `akquise/ideen.json`, wirklich loeschbar), Dubletten gegen Ideen und Kundenstamm
  (Name ohne Rechtsform, Website-/Mail-Domain ohne Freemail); Reiter Kunden -> „💡 Ideen“ mit Formular, Status, Verlauf;
  Deploy-Ausschluss, Backup, `.gitignore` (dabei `einwilligungen/` nachgezogen, BF-70).
- P2: Telegram „Partner-Idee: …“, „Kunden-Idee: …“, „Akquise: …“, „Merk dir … als moeglichen Partner/Kunden“ -> Idee mit
  „🔎 Daten suchen“ (Brave + Impressum, nur Vorschlag, „✅ Uebernehmen“) und „↩️ Rueckgaengig“; bei Dublette erst Rueckfrage.
  Ein blosses „Idee: …“ bleibt Chat (oft Content) -- dafuer LUNA-Werkzeug `akquise_idee_merken` (eigene kleine Gruppe,
  Token-Budget eingehalten).
- P3: „✉️ Anschreiben …“ oeffnet die Vorstellungs-Mail vorbelegt (Name, Mail, Ansprechpartner, Website); Partner-Ideen
  mit neuer Vorlage „Vorstellung – Partnerschaft“; nach dem Senden Idee „angeschrieben“ + Firma (Interessent), danach Stand
  aus Vorstellung/Kundenstamm (Antwort, kein Interesse, Kunde).
- Tests `test_akquise.py` (7, Gegenproben rot); Browser Rechner/iPad/iPhone.

## Nicht-Scope

Kein automatischer Versand, keine Kaltakquise-Serien, keine Wiederbelebung des Collab-Radars/Meta-Postfachs.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md` (neuer Speicher, Telegram),
`docs/entscheidungs-register.md`, `deploy/sync-to-nas.sh`/`deploy/backup-from-nas.sh` (P1).

## Definition of Done

Ideen fuer Partner und Kunden lassen sich in LUNA-OS und per Telegram sammeln, mit Status verfolgen und mit einem Klick
als Vorstellungs-Mail anschreiben.
