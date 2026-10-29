# Roadmap: LUNA bedient den Rechner (Jarvis Paket D = Phase 17, Windows)

- Status: geplant
- Stand: 2026-10-29
- Arbeitsbranch: `ai/rechner-steuerung-plan`
- Basiscommit: `969acf3`
- Naechster Schritt: CEO prueft Ziel, Endbild und Etappen, ergaenzt/aendert und beantwortet die Fragen in D0; danach Go fuer D1.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO-Vision 2026-06-28, Umbau auf Windows 2026-09-25)

LUNA bedient auf **ausdrueckliche Anweisung** den Rechner: Apps oeffnen und steuern, tippen, klicken, Dateien
ordnen -- zuerst als Auftrag („raeum den Download-Ordner auf“), am Ende als **Live-Co-Working**: Der CEO sieht die
offene App, spricht, LUNA setzt es sofort um, der CEO justiert per Sprache, LUNA schlaegt selbst vor.
**Nie autonom, nie Geld/Recht/Oeffentlichkeit/Loeschen ohne Bestaetigung.**

## Endbild -- was am Ende moeglich ist

| Stufe | Beispiel | Wie |
|---|---|---|
| Auftrag per Telegram/Chat | „Oeffne den Ordner Kiez Alm und zeig mir, was drin ist“ | LUNA (NAS) -> Auftrag -> Windows-Runner -> Bildschirmfoto + Ergebnis zurueck |
| Dateien ordnen | „Sortier die Downloads: PDFs nach Belege, Bilder nach Fotos“ | Vorschau der Verschiebungen -> ✅ -> ausgefuehrt; Loeschen nie ohne eigenes ✅ |
| Apps fuellen | „Leg in XMind eine Mindmap fuer die Herbstkampagne an“, „schreib den Text in Word“ | App-Steuerung ueber die Windows-Bedienschnittstelle (UI Automation), XMind ueber das Dateiformat |
| Mail-Entwurf | „Schreib Outlook-Entwurf an Kiez Alm mit dem Angebot“ | Entwurf ja, **Senden bleibt beim CEO** |
| Mehrschritt-Ziel | „Exportier die Praesentation als PDF und leg sie in den Kundenordner“ | Schleife sehen -> entscheiden -> handeln (vorhanden: `runner/computer_use.py`), haelt an bei Gefahr/Unsicherheit |
| Live-Co-Working | CEO spricht am Rechner, LUNA arbeitet sichtbar mit, „nein, den Knoten nach links“ | Sprachkanal + schneller Bild-/Entscheidungskreis (Modellfrage, siehe D0) |
| Jederzeit | „Stopp“ | Not-Aus per Telegram, Tastenkuerzel und Datei; Protokoll jeder Aktion |

**Bewusst nicht im Endbild (ohne eigene CEO-Entscheidung):** Browser frei im Internet bedienen (AGENTS.md 5.7:
freies Internet nur ueber den Netz-Agenten), Zahlungen/Bestellungen, Posten, Senden von Mails, Loeschen ohne
Einzel-✅, Systemeinstellungen/Installationen, Zugriff auf `.env`/Schluessel/Passwoerter.

## Bestand (Analyse, read-only, 2026-10-29)

| Baustein | Stand | Nachweis |
|---|---|---|
| Steuer-Schleife sehen->entscheiden->handeln | vorhanden, plattformneutral, getestet; Halt bei Gefahr/niedriger Konfidenz/Rueckfrage, Schritt-Deckel | `runner/computer_use.py` |
| Tor-Logik (Allowlist, Vorschau->Bestaetigung, Not-Aus, Audit) | vorhanden, aber **macOS-only** (AppleScript, `~/.luna_orb_killswitch`) | `runner/actuator.py` |
| XMind ueber Dateiformat | vorhanden | `runner/xmind.py` |
| Sandbox-Policy (Datei/Netz default-deny, Prozess-Sperrliste) | Blaupause fertig, **noch nirgends scharf** | `core/sandbox_policy.py`, `governance/sandbox-policy.json` (Phase 25) |
| Mac-MVP | ueber 8 Test-Aktionen (3 fehlgeschlagen) nie hinaus, seit 08.07. ungenutzt | `ROADMAP.md` Phase 17 |
| Windows-Seite MACO470 | Python 3.12 unter Windows installiert; Sitzung „nils“ an der Konsole aktiv seit 15.10.; **kein Auto-Login** (`AutoAdminLogon` nicht gesetzt); 30 GB RAM, Radeon 890M | `powershell.exe` 2026-10-29 |
| Bruecke NAS -> MACO470 | Muster vorhanden: Sprach-Arbeiter und Cutter holen Auftraege per LUNA-OS-API (Pull, Maschine-zu-Maschine) | `sprachdienst/`, `cutter/luna_bridge.py`, `/api/sprache/*` |
| Lokales Bildmodell | `gemma3:27b` im Ollama: liest Dateinamen auf einem Test-Bildschirm richtig, **Klick-Position grob falsch** (geschaetzt 850/550 statt 1180/680), ca. **13 s** je kurzer Antwort | Probe 2026-10-29 mit kuenstlichem Testbild |
| Cloud-Modelle | Claude wieder aktiv (Sonnet 5.5, `CLAUDE_AKTIV_ROADMAP.md`); Gemini als Ausweich | `docs/datenschutz-ki-nutzung.md` |

**Folgerung aus der Probe:** Klicken nach Pixel-Schaetzung ist mit dem lokalen Modell zu ungenau. Gezielt handeln
ueber die **Windows-Bedienschnittstelle (UI Automation)** -- Fenster, Knoepfe und Felder haben dort Namen, LUNA
waehlt „Knopf Neuer Ordner“ statt „Punkt 850/550“. Das Bild dient dem Verstehen und der Kontrolle.

## D0 -- Entscheidungen des CEO (vor D1)

1. **Welcher Rechner?** Sitzt du im Alltag am MACO470 (Windows) -- oder am MacBook? Der Plan geht vom MACO470 aus.
   (MacBook waere ein zweiter, eigener Runner -- spaeter moeglich, Mac-Code ist Referenz.)
2. **Welche Apps zuerst?** Vorschlag Start-Allowlist: Explorer (Dateien), Editor, XMind, Word/Excel, Outlook (nur
   Entwurf). Was fehlt, was soll nie?
3. **Welche Ordner?** Vorschlag: Downloads, Desktop, Dokumente\Hanserautisch, Kundenordner-Spiegel. Nie: Windows,
   Programme, `.env`-/SSH-Ordner, WSL.
4. **Modell fuer Sehen und Entscheiden** (Bildschirmfotos zeigen Kundendaten):
   - (a) **lokal** (`gemma3:27b`, kostenlos, bleibt im Haus, ca. 13-30 s je Schritt) -- fuer Auftraege, nicht live;
   - (b) **Claude** (Anthropic, Bildschirmfotos gehen an Anthropic, kostet je Schritt; Kostenvoranschlag CFO vor
     Freigabe) -- schnell genug fuer Live-Co-Working;
   - Vorschlag: (a) als Standard ab D3, (b) erst in D6 nach eigener Kosten-/Datenschutz-Freigabe.
5. **Auto-Login am MACO470?** Der Runner braucht die angemeldete Sitzung. Heute laeuft sie seit 15.10. durch; nach
   einem Neustart ohne Anmeldung kann LUNA nichts bedienen (sie sagt es dann). Auto-Login einschalten = deine
   Entscheidung (Sicherheit: wer am Geraet sitzt, ist angemeldet).
6. **Sprache fuer D6:** Mikrofon/Lautsprecher am MACO470 vorhanden? Oder Sprache weiter ueber iPhone/Telegram?

## Etappen

### D1: Windows-Runner mit Not-Aus, Protokoll und Sandbox (W1 + W7)

- Ziel / Scope: eigener kleiner Dienst unter **Windows** (nicht WSL) in der angemeldeten Sitzung, gestartet ueber
  die Aufgabenplanung „bei Anmeldung“; eigene Python-Umgebung; Code aus dem Repo (Weg ueber `\\wsl$` oder Kopie --
  in D1 entscheiden). Kann noch **nichts** bedienen ausser „lebe ich?“. Not-Aus drei Wege: Telegram „Stopp
  Rechner“, Tastenkuerzel, Sperrdatei. Sandbox-Policy (Phase 25) prueft **jede** spaetere Aktion; Protokoll jeder
  Anfrage in LUNAs Aktivitaetsprotokoll.
- Gate: Runner meldet sich nach Anmeldung von selbst; Not-Aus sperrt binnen 1 s (Test); eine Aktion ausserhalb
  der Policy wird abgewiesen (Test, Gegenprobe rot); `orchestrator/tests` + Doku-Check gruen.
- Risiko / Rueckweg: Aufgabe in der Aufgabenplanung deaktivieren = aus. Kein Eingriff in `cutter-worker`/Keepalive.
- CEO-Schritt: Aufgabe in der Windows-Aufgabenplanung anlegen (fertiger Befehl kommt von mir).

### D2: Bruecke LUNA (NAS) -> Runner (W6)

- Ziel / Scope: Auftragswarteschlange wie beim Sprach-Arbeiter (`/api/rechner/*`, Pull vom MACO470, eigenes
  Maschinenkonto); Werkzeug `rechner_auftrag` fuer LUNA; Ergebnis + Status zurueck in den Chat.
- Gate: „Rechner, lebst du?“ in Telegram -> Antwort vom Runner binnen 10 s (Empfang in Telegram geprueft);
  MACO470 aus -> klare Meldung statt Haenger.
- Risiko: neues Maschinenkonto/Zugriff = **CISO-Freigabe** (AGENTS.md 5.7) -- ich lege die Policy-Zeile vor.

### D3: Sehen (W2 + W4)

- Ziel / Scope: offene Fenster, vordere App, Liste der Bedienelemente (UI Automation); Bildschirmfoto auf
  Anfrage -> Telegram („zeig mir den Bildschirm“) und lokale Beschreibung (`gemma3:27b`). Fotos bleiben lokal bzw.
  gehen nur an dich; sie werden nach 24 h geloescht.
- Gate: 5 Probe-Fragen („welche Apps sind offen?“, „was steht im Explorer?“ …) korrekt; Foto kommt in Telegram an.

### D4: Einfache Handgriffe mit Vorschau (W3)

- Ziel / Scope: App aus der Allowlist oeffnen, Text tippen, Tasten, Datei verschieben/kopieren/umbenennen in
  freigegebenen Ordnern. Jeder Handgriff erst als **Vorschau** („Ich verschiebe 12 Dateien: …“) -> ✅; harmlose
  Handgriffe (App oeffnen, Fenster zeigen) nach deiner Wahl auch direkt. **Loeschen nur in den Papierkorb und nur
  mit eigenem ✅.**
- Gate: „Sortier die Downloads“ -> Vorschau stimmt -> nach ✅ genau so ausgefuehrt; ohne ✅ nichts; Pfad ausserhalb
  der Ordnerliste abgewiesen (Gegenprobe).

### D5: Mehrschritt-Ziele (Schleife)

- Ziel / Scope: `runner/computer_use.py` auf Windows: aus einem Ziel eine Kette von Handgriffen, je Schritt sehen ->
  entscheiden -> handeln, mit lokalem Modell; Halt bei Gefahr, Unsicherheit oder Rueckfrage; hoechstens N Schritte.
  App-tief: XMind ueber das Dateiformat, Office ueber UI Automation, Outlook nur Entwurf.
- Gate: 5 Probe-Aufgaben (z. B. Mindmap aus Stichpunkten, PDF-Export in den Kundenordner, Ordner anlegen und
  befuellen) -- Erfolgsquote dokumentiert; kein gefaehrlicher Schritt ohne Rueckfrage (Test).

### D6: Live-Co-Working per Sprache

- Ziel / Scope: du sprichst am Rechner (LUNA-OS im Browser oder Sprachkanal), LUNA arbeitet sichtbar mit und
  schlaegt vor. Braucht kurze Reaktionszeit -> Modell nach D0 Nr. 4 (b) und Live-Stimme (aus Paket A offen).
- Gate: 10-Minuten-Sitzung XMind oder Word ohne Abbruch; Reaktionszeit je Schritt gemessen.
- CEO-Tor: Kosten (Kostenvoranschlag CFO) und Datenschutz (Bildschirmfotos an den Anbieter) vor dem Bau.

## Reihenfolge und Aufwand

| Etappe | Aufwand | Kosten | Abhaengigkeit |
|---|---|---|---|
| D1 Runner + Not-Aus + Sandbox | mittel | keine | D0 Nr. 1, 5 |
| D2 Bruecke | mittel | keine | D1, CISO-Freigabe |
| D3 Sehen | mittel | keine (lokal) | D2 |
| D4 Handgriffe | mittel | keine | D3, D0 Nr. 2-3 |
| D5 Mehrschritt | gross | keine (lokal) | D4 |
| D6 Live-Co-Working | gross | laufend (Modell) | D5, D0 Nr. 4/6, CEO-Tor |

Nach D4 ist LUNA im Alltag schon nuetzlich (Auftraege mit Vorschau); D5/D6 sind der Ausbau.

## Nicht-Scope

Freie Websuche/Browser im Internet (Netz-Agent-Regel), Zahlungen, Posten, Mails senden, Installationen und
Systemeinstellungen, `.env`/Schluessel/Passwort-Manager, der Telegram-Bot (laeuft weiter nur auf der NAS),
`cutter-worker`/Backup/Keepalive auf dem MACO470, der MacBook-Runner (spaeter eigene Etappe), Charta-Aenderungen.

## Dokumentationspflicht bei Umsetzung

`projekt_changelog.md`, Etappen-Status hier, `ROADMAP.md` (Phase 17 + Verzeichnis), `JARVIS_ALLTAG_ROADMAP.md`
Paket D, `docs/entscheidungs-register.md` (D0-Entscheidungen), `docs/datenfluesse.md` (Bruecke, Bildschirmfotos,
Modell), `docs/datenschutz-ki-nutzung.md` (Bildschirmfotos), `docs/bekannte-fehler.md`, `governance/sandbox-policy.*`,
`AGENTS.md` Abschnitt 7 (neuer Ordner fuer den Windows-Runner).

## Definition of Done

D1-D5 verifiziert und vom CEO im Alltag abgenommen; D6 nach eigener Freigabe. Der CEO setzt den Status auf
abgeschlossen.
