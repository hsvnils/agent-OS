# Datenfluesse

- Status: lebend
- Stand: 2026-09-25 (Code-Stand `f3c093f`)
- Hinweis: Beschreibt, welche Daten wohin fliessen: externe Dienste, Supabase-Tabellen, lokale Speicher,
  Eingaenge, Zeitplaene und Wege zwischen den Geraeten. `AGENTS.md` bleibt uebergeordnet. Jede neue oder
  geaenderte Verbindung wird **im selben Commit** hier nachgetragen (`AGENTS.md` 6).

## Wie diese Datei aktuell bleibt

`scripts/doku_check.py` liest die Codebloecke ```` ```doku-check:...``` ```` unten und vergleicht sie mit dem
Code. Er laeuft mit der Testsuite (`orchestrator/tests/test_doku_check.py`) und schlaegt fehl, wenn

- im Code ein externer Host, eine Supabase-Tabelle oder ein lokaler Speicher auftaucht, der hier fehlt,
- hier etwas steht, das im Code nicht mehr vorkommt, oder
- ein Speicher nicht vom Deploy ausgenommen ist oder weder gesichert wird noch unter `ohne-backup` steht.

Nachtragen: `python3 scripts/doku_check.py --liste` zeigt die Ist-Mengen mit Fundstellen.

**Grenzen des Checks** (von Hand pflegen): Dienste, die nur ueber ein SDK ohne URL im Code angesprochen werden
(Anthropic, OpenAI, Cartesia, Google-Client-Bibliothek), dynamische Hosts aus der `.env` (`SUPABASE_URL`,
`LUNA_OS_URL`, `IG_ANALYSE_BASE_URL`, Meta-Upload-Host), Zeitplaene und alles ausserhalb des Repos (DSM-Aufgaben,
systemd-Units auf dem MACO470, Windows-Aufgaben).

## Ueberblick

```
                       Internet-Dienste (Abschnitt 1)
   Telegram · Meta/Facebook · Google · Anthropic/Gemini/OpenAI · Brave · GitHub · Boersen-APIs · Supabase
                ▲                                   ▲                                 ▲
                │                                   │                                 │
  ┌─────────────┴─────────────── NAS (Synology DS923+) ───────────────────────────────┴──┐
  │  luna-telegram (Bot, EINZIGER Telegram-Poller, alle Zeitplaene)                      │
  │  luna-os (Web :8765, extern https://os.hanserautisch.synology.me, Webhook Meta)      │
  │  beide teilen /volume1/docker/ki-unternehmen als /app  ->  lokale Stores (Abschn. 3) │
  │  DSM-Aufgabe 03:30: Nightly-Reel (docker exec luna-os ...)                           │
  └───────▲──────────────────────────▲──────────────────────────────▲────────────────────┘
          │ CIFS read-only            │ HTTPS: Queue/Report/Reel      │ ssh + tar
          │ (Clip-Archiv)             │ (luna_bridge)                 │ (Backup 03:20, Deploy)
  ┌───────┴──────────────────────────┴──────────────────────────────┴────────────────────┐
  │  MACO470 (Windows 11 + WSL2-Ubuntu, Benutzer luna) — Werkbank seit 2026-09-25        │
  │  cutter-worker (systemd) · luna-backup.timer · Repo + .env · Push per Deploy-Key     │
  └──────────────────────────────────────────────────────────────────────────────────────┘
   MacBook: nur noch Zweit-Backup (launchd 03:00) und Sprachkanal/Orb (Phase 17 -> Windows)
```

## 1. Externe Dienste

**Senden nach aussen** (= Oeffentlichkeit/Geld) passiert nur nach CEO-Freigabe: Facebook-Reel, Mail,
Kalendereinladung, Alpaca-Order (Paper), Git-Push eines Antrags-Branches.

| Dienst / Host | Aufrufer | Was geht raus / kommt zurueck | Env-Key | Art |
|---|---|---|---|---|
| `api.telegram.org` | `channels/telegram/bot.py`, `cutter/melden.py`, `deploy/backup-from-nas.sh`, `deploy/luna_waechter.py` (Waechter-Meldungen direkt vom MACO470, BETRIEB Etappe 3) | Chat, Push-Meldungen, Reels (bis 50 MB) / Updates, Sprachdateien | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_CHAT_ID` | senden, nur an den CEO-Chat |
| `graph.facebook.com` (+ Meta-Upload-Host) | `governance/instagram.py`, `instagram_token.py`, `core/social_kit.py`, `governance/facebook_reels.py` | DMs, Insights, Token-Tausch / **Reel-Video + Caption** | `INSTAGRAM_*` | lesen; **veroeffentlicht** nur nach `/api/reel/{id}/freigeben` |
| `www.googleapis.com`, `oauth2.googleapis.com` (**Konto: luna.hanserautisch@gmail.com** seit 2026-09-28, vorher hanserautisch@gmail.com) | `governance/google_workspace.py`, `core/crm_mail.py`; seit Etappe 3 auch die Web-App (`/api/crm/angebote/*`: Angebot **senden** aus LUNAs Konto nach CEO-Klick mit Vorschau (`POST /api/crm/angebote/<nr>/senden`, nur Modul finanzen), Kalender-Erinnerungen Nachfassen/Ablauf, beim Festschreiben einer Rechnung „💶 Payment-Check“-Termin am Faelligkeitstag (Etappe 18, auch Vorkasse-Rechnungen); erledigte Erinnerungen -- Angebot angenommen/abgelehnt, Rechnung bezahlt/storniert -- loescht die Web-App sofort und der Bot im 15-min-Poll nachholend, nur eigene protokollierte kommende Termine, `core/erinnerungen.py`, Ereignis `kalender_erinnerung_entfernt`); Bot prueft im 15-min-Poll die Mailverlaeufe gesendeter Angebote auf Kundenantworten (`core/angebote.antworten_pruefen`, Meldung an den CEO); Betriebs-Waechter (BETRIEB_ROADMAP Etappe 3): der Bot schreibt alle 15 min `orchestrator/state/bot_herzschlag.json` (NAS, nicht gesynct, nicht gesichert -- fluechtig); `GET /api/betrieb/status` liefert Herzschlag-Alter + haengende Meldungen aus `notifications/log.jsonl`; `deploy/luna_waechter.py` auf dem MACO470 (Timer `luna-waechter.timer`, alle 15 min) ruft das per HTTP-Basic ab, liest `systemctl show luna-backup.service` und meldet per Telegram-`sendMessage` (kein Polling); Zustand in `~/.local/state/luna-waechter.json` (MACO470); Abos (Etappe 15, keine externe Verbindung): Ereignisse `abo_angelegt/_geaendert/_beendet/_faelligkeit` in der Hash-Kette, `GET/POST /api/finanzen/abos*`, taeglicher Lauf im Bot (05:00) bucht nur angehakte Abos als Eigenbeleg und meldet per Telegram-Outbox; TKP (Etappe 16): Katalog-Felder `kontakte/tkp_min_cent/tkp_max_cent/produktion_cent/omr` in `buchhaltung/katalog.json` (Etappe 23: dazu `provision_art/provision_wert`; Positionen in Angebot/Auftrag/Rechnung mit `provision`; Etappe 21: `kosten`, `physisch/mindestbestand/lager_start`, `mindestmarge_prozent`; Ereignis `lager_bewegung`, `GET /api/finanzen/lager`, `POST /api/finanzen/lager/<id>/bewegung`), Angebots-Positionen mit `tkp_cent`, `GET /api/crm/katalog` liefert die OMR-Werte; Stammdaten (Etappe 14, keine externe Verbindung): Ereignisse `firma_nummer_ergaenzt`, `eingang_firma_verknuepft`, `eigenbeleg_firma_verknuepft` in der Hash-Kette; `POST /api/finanzen/stammdaten/zuordnen`, `GET /api/finanzen/journal?firma=`, `/api/crm/kunden/<nr>` mit Buchungen; Beleg-Mail-Abruf (15-min-Poll, `core/eingangsbelege.mail_eingang_pruefen`): Suche `from:/to:/deliveredto:` der eigenen Adressen inkl. Spam, ohne Gesendet; Mails ohne PDF -> Rechnung im Mailtext wird Beleg (PDF-Ansicht + unveraenderte `.eml` in `buchhaltung/belege/<jahr>/`), Quittungen als Zahlungsnachweis (`eingang_datei`), automatische Weiterleitungen nur mit DKIM/DMARC + eigener Adresse; Etappe 25: Zeiterfassung (nur intern) -- Ereignisse `zeit_start/_stopp/_eintrag/_fahrt/_storniert/_zugeordnet/_einstellung` in der Hash-Kette (Stundensatz nur als Satz, Monatsbrutto nur in `buchhaltung/zeiterfassung.json` auf der NAS), Endpunkte `/api/finanzen/zeit*` (Modul finanzen), Telegram „Bin auf dem Weg zu …“/„Bin wieder zuhause“/„42 km“ + Knoepfe `zst:`/`zkm:`, Fahrten nur kalkulatorisch (Ereignis `zeit_fahrt`, kein Beleg); PROJEKTZEITEN Z1: Ereignisse `zeit_details`/`zeit_korrigiert`, Endpunkte `/api/finanzen/zeit/<id>/details` und `/korrigieren`, Telegram-Knoepfe `ztt:`; PROJEKTZEITEN Z2: `GET/POST /api/finanzen/rechnungen/<entwurf>/projektzeiten`, Entwurf/Rechnung mit Feld `projektzeiten` (eingefrorene Auswahl), `auftrag_geaendert` mit `verkauf_satz_cent/verkauf_km_cent`; Z3: `GET /api/finanzen/zeit/auswertung?von=&bis=[&format=csv]`, `zeit_details` mit `position`, Stundenzettel-Anlage im Rechnungs-PDF (`core/projektabrechnung.py`); PROJEKTBERICHT P1: Postings je Auftragsposition (aus der festgeschriebenen Kopie im Auftrag, nie aus dem Katalog), Ereignisse `posting_veroeffentlicht/_kennzahlen/_bild/_erinnert`, Endpunkte `GET /api/crm/auftraege/<nr>/postings`, `POST /api/crm/postings/<id>/veroeffentlicht|kennzahlen`, `GET /api/crm/postings/<id>/bild/<i>`; PROJEKTBERICHT P2: Bot nimmt Fotos an (`getFile`, nur CEO-Chat), Knoepfe `pkz:/pkj:/pkk:`, Erinnerung 7 Tage nach Veroeffentlichung im 15-min-Poll (09-21 Uhr, Ereignis `posting_erinnert`), `POST /api/crm/postings/<id>/bild` (Upload + Auslesen); PROJEKTBERICHT P3: Ereignisse `auftrag_bericht`/`auftrag_bericht_versendet`/`auftrag_bericht_entfaellt`, Endpunkte `/api/crm/auftraege/<nr>/bericht` (+ `/pdf`, `/versandvorschau`, `/senden`, `/entfaellt`), Bericht **senden** aus LUNAs Konto nur nach CEO-Klick mit Vorschau (Gmail, PDF-Anhang), gesendetes PDF als Firmenakte-Dokument (Art `bericht`, Bezug = Auftrag); P4: `GET /api/crm/katalog` mit `ist_kontakte`, `/api/crm/kunden/<nr>/akte` mit `kampagnen`, Ereignisse `posting_kennzahlen` mit `messpunkt: 30`, `auftrag_folge_erledigt`, `auftrag_kundenstimme_entwurf`, `POST /api/crm/auftraege/<nr>/folge-erledigt`, `POST /api/crm/auftraege/<nr>/kundenstimme-entwurf` (Gmail-**Entwurf** in LUNAs Konto, kein Versand); KONZEPT-MAPPE: Ereignisse `konzept_briefing/_idee/_skript/_szene/_szene_erledigt/_szene_entfernt/_dreh/_bild/_freigabe`, Endpunkte `/api/crm/konzept/<beleg>` (+ `/<vorgang>/<teil>`), `/api/crm/konzept-bild/…`, `/api/crm/konzept-pdf/…`, `/api/crm/konzept-versand/…` (Konzept-PDF per Gmail nur nach CEO-Klick, Ablage Firmenakte Art `konzept`); VERTRAGSWERK: Ereignisse `vertrag_vorlage_version/_status`, Endpunkte `/api/crm/vertraege*` (aendern/pruefen nur Modul finanzen); DIGITALER BELEG: Detail-Endpunkte von Angebot/Auftrag/Rechnung liefern zusaetzlich `blatt` (Inhalte wie im PDF, aus `firmendaten.json` Absender/Steuernummer/Bank), neu `GET /api/finanzen/mahnungen/<nr>`; BELEGVERFOLGUNG: `GET /api/crm/belege/<nummer>/verfolgung` (liest nur, Rechnungsteile nur mit Modul finanzen), Feld `korrektur_zu` an Korrektur-Entwurf/-Rechnung; Etappe 31: `POST /api/crm/auftraege` legt einen Auftrag ohne Angebot an (Ereignis `auftrag_angelegt` mit leerem `angebot`); Etappe 29/30: `GET /api/finanzen/zeit` liefert `start_ms`; Ereignisse `lieferung_angelegt/_datei/_entfernt`, `auftrag_status` mit `datum` (Geliefert) bzw. `beauftragt` (wieder geoeffnet), Endpunkte `/api/crm/auftraege/<nr>/lieferungen`, `/api/crm/lieferungen/*`; Etappe 28: Ereignis `rechnung_mahnverfahren` (gerichtliches Mahnverfahren an der Rechnung), `POST /api/finanzen/rechnungen/<nr>/mahnverfahren`; Beleg-Mail-Abruf und Firmenakte pruefen Mail + Anhangtext auf eigene Forderung (`firmenakte.eigene_forderung`) -> Akte statt Beleg; Etappe 27: Plattform-Auszahlungen -- Posten mit Erzielt-Zeitraum aus dem gespeicherten Meta-PDF-Text oder von Hand (Ereignis `eingang_posten`, aendert keine Buchung), `GET /api/finanzen/plattform`, `POST /api/finanzen/belege/<nr>/posten`; Etappe 26: `/api/finanzen/uebersicht` liefert den Zusatz `kalkulatorisch`, `/api/finanzen/journal?format=csv&kalkulatorisch=1` haengt einen getrennten Block an, `/api/finanzen/abschluss/export?kalkulatorisch=1` legt `zusatz/kalkulatorisch.csv` ins ZIP (nie in EUeR/`index.xml`), Browser-Schalter `luna-fin-kalk` (localStorage); Firmenakte ordnet Mails mit Belegnummer im Betreff (AN/AB/RE/RG) der Firma des Belegs zu; Etappe 24: Bot legt im 15-min-Poll Mails mit LUNA in CC/BCC oder vom CEO weitergeleitete Nicht-Beleg-Mails in der Firmenakte ab (`core/firmenakte.mails_pruefen`, Ereignisse `akte_dokument`/`akte_mail_offen`/`akte_mail_zugeordnet`, Dateien als Geschaeftsbrief), Uploads ueber `/api/crm/kunden/<nr>/akte`; Bot legt im 15-min-Poll erledigte Beleg-Mails (Anhang sicher im Kassenbuch) nach `LUNA/Rechnungen|Gutschriften|Doppelt/<Jahr>` ab, entfernt Posteingang/Spam/ungelesen (`messages.modify`, Ordner per `labels.create`, nie loeschen; `core/eingangsbelege.mails_ablegen`, Ereignis `eingang_mail_abgelegt`, Recht `gmail.modify`); Bot kopiert im 15-min-Poll jeden Beleg nach LUNAs Drive `LUNA-Buchhaltung/Belege/<jahr>/` und taeglich ab 03:00 Kette/Katalog/Firmendaten nach `LUNA-Buchhaltung/Stand/<datum>/` (`core/beleg_sicherung.py`, Pruefsummen-Abgleich, nie loeschen) | Gmail, Kalender, Drive, Sheets; Angebots-PDF + Kundenname/-Mail im Entwurf | `GOOGLE_OAUTH_*`, `GOOGLE_CALENDAR_*` | lesen frei; senden/aendern nur mit `bestaetigt=True`; Angebote nur als Entwurf (Senden = CEO in Gmail) |
| All-Inkl-Mailserver (`ALLINKL_SMTP_HOST`/`ALLINKL_IMAP_HOST`, Postfach luna@hanserautisch.de; MAILVERSAND_ALLINKL M1) | `governance/allinkl_mail.py` ueber `channels/web/app.py` (`_versand_google`: alle Kunden-Versandwege, `GET /api/finanzen/kundenversand`, `POST /api/finanzen/kundenversand/testmail`) und `channels/telegram/bot.py` (Folgemahnung) | raus: Kundenmail mit PDF-Anhang (SMTP), dieselbe Mail per IMAP-APPEND in „Gesendet“; zurueck: Status/Ordnerliste und (M2, `core/mail_antworten.py`, 15-min-Poll im Bot) Mails des Posteingangs der letzten 30 Tage nur lesend -- zugeordnete Kundenantworten werden als .eml archiviert (Angebot: `angebot_antwort`/`angebot_mail_archiviert`; sonst Firmenakte `akte_dokument` mit Bezug), Ereignis `mail_antwort`, Telegram-Meldung. Die .eml gesendeter Mails landet wie bisher in der Firmenakte | `KUNDENVERSAND`, `ALLINKL_SMTP_HOST`, `ALLINKL_SMTP_PORT`, `ALLINKL_IMAP_HOST`, `ALLINKL_IMAP_PORT`, `ALLINKL_MAIL_USER`, `ALLINKL_MAIL_PASSWORT`, `ALLINKL_ABSENDER`, `ALLINKL_GESENDET_ORDNER` | senden nur nach CEO-Klick/✅; nur aktiv mit `KUNDENVERSAND=allinkl` |
| Anthropic (SDK) | `core/hoa_conversation.py`, `core/backends.py`, `core/execution_live.py`, `governance/web_research.py`, `core/ig_analyse.py` | Prompts, Kontext, DM-Inhalte / Antworten | `ANTHROPIC_API_KEY` | lesen; Execution schreibt Code in `.worktrees/` |
| `accounts.google.com` | `deploy/google_oauth_neu.py` (nur von Hand auf dem MACO470, BF-33) | Google-Anmeldelink fuer die CEO-Zustimmung; neuer Refresh-Token landet nur in `orchestrator/.env` (MACO470 + NAS) | `GOOGLE_OAUTH_CLIENT_ID`/`_SECRET` | Zustimmung durch den CEO im Browser |
| `generativelanguage.googleapis.com` | `core/model_router.py` (Fallback), `cutter/gemini_video.py`, `cutter/reel_tag.py`, `core/ig_analyse.py`, `core/kennzahlen_lesen.py` (Insights-Screenshots, P2), `core/clo_pruefung.py` (CLO-Pruef-Lauf der Vertragsvorlagen, nur Vertragstexte, einmalig per Skript 2026-10-05, Modell `gemini-pro-latest`), `scripts/routing_probelauf.py` (Routing-Probelauf: nur Testfragen, System-Prompt, Werkzeug-Beschreibungen; manuell), `core/videograf.py` (Videograf-Vorschlaege aus der Konzept-Mappe: Briefing ohne Freigabe-Personen/Notizen, Idee/Skript, Szenen, Drehort/-zeit -- ohne Kontaktdaten), `core/contentplan.vorschlag` (`POST /api/contentplan/vorschlag`, CONTENT_PLAN C3: Zeitraum, eigene Plan-Titel, Feiertage/Anlaesse; Kunden-Postings und Drehs nur als „Kunden-Posting“/„Kundendreh“ ohne Namen) | Prompts, Screenshots, **Videoclips** (nur mit `CUTTER_VIDEO_KI=1`) | `GEMINI_API_KEY` | lesen; Upload zu Google |
| `www.gesetze-im-internet.de` | `core/rechtsquellen.py` (CLO_AUSBAU C3: Bot-Nachtlauf 04:30, seit AGENTEN_AUSBAU A2 ueber alle `skills/*/*/quellen.md` (CLO, CFO, CISO, CHRO), ~33 Seitenabrufe; Erstabruf am 2026-10-05) | keine (nur Abruf oeffentlicher Gesetzestexte) | -- | nur lesen; meldet Aenderungen, aendert keine Skills |
| OpenAI (SDK) | Fallback in `core/model_router.py`, `core/ig_analyse.py` | Prompts | `OPENAI_API_KEY`, `IG_ANALYSE_*` | lesen |
| `api.deepgram.com` | `bot.py` (Sprachnachrichten), `cutter/transkription.py` (3. Fallback), Voice | Audio / Transkript | `DEEPGRAM_API_KEY` | lesen |
| `api.elevenlabs.io`, Cartesia (SDK) | `channels/web/app.py` (`/api/tts`), `channels/voice/pipeline.py` | Text / Audio | `ELEVENLABS_API_KEY`, `CARTESIA_API_KEY` | lesen |
| `api.search.brave.com` | `governance/web_research.py`; seit Etappe 22 auch `core/firmendaten.py` (Web-App auf Knopfdruck, Bot sonntags bis 8 Firmen) | Suchanfragen („<Firmenname> Impressum“) | `BRAVE_API_KEY` | lesen |
| Websites der Geschaeftspartner (Impressum) | `core/firmendaten.py` (KUNDEN_FINANZEN Etappe 22) | GET der Impressums-Seite (nur Firmen, nie Privatpersonen, nur dieselbe Website, max. 800 KB) / oeffentliche Pflichtangaben als Vorschlag (Ereignis `firma_recherche`) | – | lesen |
| `nominatim.openstreetmap.org` | `core/routen.py` (KUNDEN_FINANZEN Etappe 25; Web-App/Bot beim Buchen einer Fahrt) | Adresse des Drehs bzw. der Firma und die eigene Firmenadresse (Start) / Koordinaten, zwischengespeichert in `buchhaltung/geocache.json`; max. 1 Anfrage/s, eigener User-Agent | – (oeffentlich) | lesen |
| `router.project-osrm.org` | `core/routen.py` (Etappe 25) | nur Koordinaten Start/Ziel / Strassenstrecke in Metern (Auto) -> km Hin + Rueck | – (oeffentlich) | lesen |
| `data-api.ecb.europa.eu` | `core/wechselkurse.py` (KUNDEN_FINANZEN Etappe 20; Web-App nach Beleg-Upload, Bot im 15-min-Poll) | Waehrung + Zeitraum (keine Belegdaten) / EZB-Referenzkurse (CSV), zwischengespeichert in `buchhaltung/wechselkurse.json` | – (oeffentlich) | lesen |
| `api.github.com` | `governance/github_watch.py` (Watch-Loop) | Topic-Suche / Repos | `GITHUB_TOKEN` (optional) | lesen |
| github.com (git) | `core/execution_live.py`, `core/hoa_tools.py` (`antrag_pushen`); Werkbank per Deploy-Key | Branches | `GITHUB_TOKEN` / `~/.ssh/github` | **schreiben** (Push) |
| `api.osv.dev` | `core/security_agent.py` (nur Tool `sicherheits_audit`, nicht im 04:00-Lauf) | Paket + Version / Schwachstellen | – | lesen |
| `paper-api.alpaca.markets` | `investment/broker.py` | **Orders (Paper)** / Konto, Positionen | `ALPACA_API_KEY`, `ALPACA_API_SECRET` | schreiben (Paper) |
| `finnhub.io`, `www.alphavantage.co`, `financialmodelingprep.com`, `api.coingecko.com`, `data.sec.gov` | `investment/providers.py` | Symbole / Kurse, News, Insider, Filings | `FINNHUB_API_KEY`, `ALPHAVANTAGE_API_KEY`, `FMP_API_KEY`, `SEC_EDGAR_USER_AGENT` | lesen |
| Supabase (`SUPABASE_URL`, PostgREST) | `governance/supabase.py` — **nur auf der NAS** | Zeilen (Abschnitt 2) | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | lesen + schreiben |
| LUNA-OS (`LUNA_OS_URL`) | `cutter/luna_bridge.py` (MACO470 -> NAS) | Queue, Status, Reels (Abschnitt 5) | `LUNA_OS_URL`, `LUNA_OS_USER`, `LUNA_OS_PASSWORD` | lesen + schreiben |
| `esm.sh` | `channels/voice/static/app.js` (Browser) | – / JS-Module | – | lesen (Client) |
| **Ollama (lokal)** `http://192.168.178.184:11434/v1` (MACO470, nur LAN) | `core/lokal_llm.py` ueber `core/model_router.py` (Chat) und `core/backends.py` (Fachagenten/Jobs) | Prompts, Kontext, Werkzeugliste / Antworten — **bleibt im Haus** | `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`, `LOCAL_LLM_CHAT`, `LOCAL_LLM_FACHAGENTEN`, `LOCAL_LLM_TIMEOUT`, `LOCAL_LLM_MAX_TOKENS` | lesen; je Bereich `zuerst`/`zuletzt`/`aus` |

Nicht angebunden, obwohl erwaehnt: AgentOps (nur Key-Check/Dienste-Register). Ollama steht nicht im Doku-Check-Block, weil
der Code es nur ueber die `.env`-Adresse (IP) anspricht.

```doku-check:hosts
api.telegram.org
graph.facebook.com
www.googleapis.com
oauth2.googleapis.com
accounts.google.com
generativelanguage.googleapis.com
api.deepgram.com
api.elevenlabs.io
api.search.brave.com
data-api.ecb.europa.eu
nominatim.openstreetmap.org
router.project-osrm.org
api.github.com
api.osv.dev
paper-api.alpaca.markets
finnhub.io
www.alphavantage.co
financialmodelingprep.com
api.coingecko.com
data.sec.gov
os.hanserautisch.synology.me   # Standardwert/Doku fuer LUNA_OS_URL
esm.sh
```

Hosts, die im Code nur als Link, Schema, Mock oder Test vorkommen (kein Datenfluss):

```doku-check:hosts-ignoriert
github.com                     # Anzeige-Links in github_watch
www.sec.gov                    # Anzeige-Links
www.tradingview.com            # Anzeige-Links
www.coingecko.com              # Registrierungs-Link
site.financialmodelingprep.com # Registrierungs-Link
json.schemastore.org           # SARIF-Schema
omr.com                        # Quellen-Link im Angebots-/Preislisten-PDF (Etappe 16), keine Verbindung
canva.link                     # Canva-Praesentation als Link in Angebots-PDF/Mail (ANGEBOT_PRAESENTATION), keine Verbindung
sarifweb.azurewebsites.net     # SARIF-Schema
www.w3.org                     # SVG-Namespace
www.apple.com                  # plist-DTD
mock.*                         # Mock-Clients
*.test                         # Test-/Mock-Hosts
*.example
```

## 2. Supabase-Tabellen

Nur die NAS-Container haben den Supabase-Key; der MACO470 bewusst nicht (er geht ueber die LUNA-OS-API).

| Tabelle | Schreibt | Liest | Schema |
|---|---|---|---|
| `luna_os_users` | `core/team_auth.py` | Login (`team_auth.py`) | `docs/hcc_k4_luna_os_users.sql` |
| `luna_os_prefs` | `channels/web/app.py` (`/api/prefs`) | web | `docs/hcc_luna_os_prefs.sql` |
| `luna_cutter_jobs` | web (`/api/cutter/*`) | web; Bot nur ueber lokalen Cache | `docs/hcc_k5_cutter_jobs.sql` |
| `crm_companies`, `crm_messages`, `crm_todos` | `core/crm_projection.py` (Write-through aus CrmStore) | `core/crm_sync.py` (15-min-Takt) | `docs/crm_supabase_schema.sql` |
| `inv_features`, `inv_forecasts`, `inv_actuals`, `inv_deviations`, `inv_model_runs` | `investment/loop_store.py` (best effort) | lokal zuerst | `docs/hcc_inv_loop.sql` |
| `trend_signals`, `ideas`, `content_drafts` | Content-Feed 07:00 (`core/hoa_tools.py`), web | web | **keine SQL-Datei** (Bestand aus HCC) |
| `sources`, `ai_intel_items` | web (Status-Aenderungen) | web | **keine SQL-Datei** (Bestand aus HCC) |

Vorsicht Namensfalle: `investment/store.py` fuehrt ebenfalls `TABELLEN` — das sind Event-Typen im
JSONL-Log, keine Supabase-Tabellen.

```doku-check:tabellen
luna_os_users
luna_os_prefs
luna_cutter_jobs
crm_companies
crm_messages
crm_todos
inv_features
inv_forecasts
inv_actuals
inv_deviations
inv_model_runs
trend_signals
ideas
content_drafts
sources
ai_intel_items
```

## 3. Lokale Speicher (Live-Daten auf der NAS)

Pfade relativ zum Repo-Root; auf der NAS `/volume1/docker/ki-unternehmen`, in **beiden** Containern als
`/app` gemountet. „Deploy-Schutz" = von `deploy/sync-to-nas.sh` ausgenommen; „Backup" = in der Liste von
`deploy/backup-from-nas.sh`. Seit 2026-09-25 (BF-03/BF-04) ist jede Luecke ein Fehler im Doku-Check; bewusst
ungesicherte Speicher stehen im Block `ohne-backup` unten.

| Speicher | Schreibt | Liest | Deploy-Schutz | Backup |
|---|---|---|---|---|
| `antraege/log.jsonl` | Bot, Web, Voice | alle | ja | ja |
| `lieferungen/<Auftrag>/` (Videos, Bilder, PDF, ZIP) | Web (`PUT /api/crm/lieferungen/upload/<id>/<teil>`, `POST .../fertig`; Etappe 30) | Web (`/api/crm/lieferungen/<id>/datei/<i>`, Auftrag, Firmenakte) | ja (`./lieferungen` ausgenommen) | nein (CEO 2026-10-01; Liste in der Hash-Kette) |
| `lieferungen/<Auftrag>/kennzahlen/` (Insights-Screenshots je Posting) | Telegram-Foto / Web (PROJEKTBERICHT P2, `core/postings.bild_ablegen`) | Web (`/api/crm/postings/<id>/bild/<i>`), Bericht | ja (`./lieferungen` ausgenommen) | nein (wie Lieferungen; Pruefsumme in der Hash-Kette, Zahlen selbst als Ereignis `posting_kennzahlen`) |
| `lieferungen/<Vorgang>/konzept/` (Moodboard-Bilder der Konzept-Mappe) | Web (`POST /api/crm/konzept-bild/<vorgang>`, KONZEPT_MAPPE K1) | Web (`/api/crm/konzept-bild/<vorgang>/<i>`) | ja (`./lieferungen` ausgenommen) | nein (wie Lieferungen; Pruefsumme in der Hash-Kette) |
| `orchestrator/state/rechtsquellen.json` (letzter Abgleich der Rechtsquellen aller Agenten, bekannte Abweichungen) | Bot (`core/rechtsquellen.lauf`, 04:30) | Bot | nein (`orchestrator/state` ausgenommen) | nein (fluechtig) |
| `skills/clo/*/SKILL.md`, `quellen.md` (CLO-Skills + Normen im Wortlaut mit Stand) | Repo (Claude Code) | CLO-Agent (System-Prompt), Nachtlauf | ja (Code-Sync) | Git |
| `skills/{cfo,cco,cro,cdo,ciso,cto,res,chro,cko,cpo,cxo,cao}/*/SKILL.md`, `skills/{cfo,ciso,chro}/*/quellen.md` (AGENTEN_AUSBAU A2/A3/A5: Skills; Normen UStG/UStDV/EStG/AO, TDDDG/BDSG, SGB IV mit Stand) | Repo (Claude Code) | Fachagent (System-Prompt), Nachtlauf (Quellen), Agenten-Profil (`/api/agenten/{key}/profil`) | ja (Code-Sync) | Git |
| `docs/recht/clo-pruefung-vertragsentwuerfe.json` (CLO-Pruefbericht + Version-2-Texte) | Repo (Pruef-Lauf C4) | Web (`/api/crm/vertraege-pruefung*`, Version 2 per CEO-Klick) | ja (Code-Sync) | Git |
| `orchestrator/state/luna_os_sitzungen.json` | Web (Login, Passkey-Login, Abmelden) | Web (jede Anfrage mit Cookie) | ja (`orchestrator/state` ausgenommen) | nein (fluechtig) |
| `orchestrator/state/luna_os_passkeys.json` | Web (Passkey einrichten/entfernen, Zaehler bei Anmeldung) | Web (Passkey-Login) | ja | ja |
| `research/log.jsonl` | Bot, Web | dito | ja | ja |
| `notifications/log.jsonl` (Outbox) | Bot, Web | Bot stellt zu | ja | ja |
| `agenda/log.jsonl` (auch Merker „Briefing gesendet") | Bot, Web | dito | ja | ja |
| `aktivitaet/log.jsonl` (auch Chat-Fehler, Kategorie `fehler`, und Werkzeug-Nutzung, Kategorie `werkzeug`) | Bot, Web | dito | ja | ja |
| `watch/log.jsonl` (Notbremse, `last_run`) | Bot | Bot, Web | ja | ja |
| `brain/log.jsonl` | Bot, Web | dito | ja | ja |
| `finance/kosten-log.jsonl` | Bot (Kostenlauf 03:00) | Bot, Web | ja | ja |
| `investment/log.jsonl` | Bot, Web | dito | ja | ja |
| `investment/features.jsonl` | Bot | Web | ja | ja |
| `approvals/log.jsonl` | Bot | Bot; Web liest offene Entscheidungen fuer `GET /api/handlungsbedarf` (UI-Roadmap Etappe 3, nur lesend) | ja | ja |
| `trajektorien/log.jsonl`, `social/log.jsonl` | Bot | Bot | ja | ja |
| `entwicklung/roadmap.jsonl` | Bot, Web, Voice | Web | ja | ja |
| `ig_inbox/log.jsonl` | Bot (Radar), Web (Webhook) | dito | ja | ja |
| `reel_freigabe/log.jsonl` + `<id>.mp4` | Web (`/api/reel/einreichen`, `/api/reel/uebersprungen`), Bot-Tageslauf 05:00 (Verfall nach 30 Tagen, MP4 abgelehnter/verfallener Reels nach 14 Tagen geloescht, gepostete bleiben; REELS_ROADMAP) | Web (`/api/reel`, `/api/reel/bremse`), Betriebs-Wacht (`zuletzt_aktiv`), Nachtlauf `cutter/reel_daily.py` (Bremse ab 10 wartenden) | ja | Log ja, Videos bewusst nein (CEO) |
| `cutter_ops/jobs_cache.jsonl` | Web | Bot | ja | nein (Cache von Supabase) |
| `cutter_ops/worker_herzschlag.json` | Web bei jedem `GET /api/cutter/queue` | Betriebs-Wacht | ja | nein (fluechtig) |
| `crm/log.jsonl` | Bot, Web | dito | ja | ja |
| `content_ops/*_cache.jsonl` (5 Dateien) | Web, Content-Feed | dito | ja | nein (Cache von Supabase) |
| `nutzung/log.jsonl` | Web (`/api/nutzung`) | Leistungsbericht | ja | ja |
| `agenten_nutzung/log.jsonl` (Fachagenten-Anfragen: Zeit, Agent, Dauer, Erfolg, Zahl der Skills, Quelle `delegate`/`werkzeug` -- **keine Inhalte**; AGENTEN_AUSBAU A1, FACHAGENTEN_ROUTING R3) | Bot/Web-Chat (Werkzeug `delegate` und jedes Werkzeug mit Fachbereich, `core/zustaendigkeit.py`) | Web (`/api/agenten/{key}/profil`, `/api/agenten-uebersicht`), Leistungsbericht (Web + Bot montags) | ja | ja |
| `backoffice/log.jsonl` (Auftraege, append-only) | Web (`/api/backoffice/*`, Worker-Ergebnisse) | Web, Bot (Werkzeug `auftrag_details`, Morgen-Briefing) | ja | ja |
| `buchhaltung/log.jsonl` (Hash-Kette: Nummern, Kunden, Angebote, Auftraege, Rechnungen, Eingangsbelege, Zahlungen, Eigenbelege) + `buchhaltung/belege/<jahr>/` (Angebots-PDFs, Original-Mails `.eml` zu Angeboten) | Web (Kunden- und Angebots-App), Bot (Mail-Archiv/Antworten im 15-min-Poll) | Bot (Integritaetspruefung 05:00), Web | ja | ja (Log + Beleg-Ordner, Schrumpf-Check) + ausser Haus in LUNAs Drive |
| `buchhaltung/firmendaten.json` (eigene Firma: Briefkopf, Steuernummer, Bankverbindung; **nur NAS, nie im Git**) | CEO (Angabe), von Hand angelegt | Web: Angebots-/Rechnungs-/Mahnungs-PDF (Briefkopf, Fusszeile mit Bank); Bot: Folgemahnung nach ✅ per Telegram | ja | ja |
| Content-Plan in der Hash-Kette (`buchhaltung/log.jsonl`, CONTENT_PLAN C1-C3): Ereignisse `plan_eintrag`/`plan_entfernt`/`plan_anlass`/`plan_anlass_entfernt` und `posting_geplant` | Web (`POST /api/contentplan`, `/api/contentplan/<id>`, `/api/contentplan/anlass`, `/api/crm/postings/<id>/geplant`; Modul content_ops bzw. crm) | Web: `GET /api/contentplan?von=&bis=` (fuehrt Plan-Eintraege, Kunden-Postings, Drehtermine der Konzept-Mappe, Feiertage Hamburg -- lokal berechnet, kein Dienst -- und Anlaesse zusammen) | ja | ja (wie Buchhaltung) |
| `buchhaltung/textbausteine.json` (Mail-Vorlagen je Belegart + Signatur mit Telefonnummer; **nur NAS**, TEXTBAUSTEINE T1) | Web (`POST /api/crm/textbausteine`, nur Modul finanzen; Aenderung als `textbausteine_geaendert` in der Kette, ohne Texte) | Web: alle Versandvorschauen (`…/versandvorschau?vorlage=`), Bot: Folgemahnung per Telegram; Mail-Entwurf `POST /api/crm/mailentwurf/<art>/<nr>/eml` und PDF `GET /api/crm/mailentwurf/<art>/<nr>/pdf` fuer das eigene Mail-Programm (Download aufs Geraet, kein externer Dienst); „Als versendet markieren“ = `…/senden` mit `kanal: mail-programm` (kein Gmail) | ja | ja (NAS-Backup + Drive-Kopie `LUNA-Buchhaltung/Stand/`) |
| `buchhaltung/katalog.json` (Leistungskatalog: Formate, Pakete, Zuschlaege, Textbausteine; **nur NAS**) + `buchhaltung/logo.jpg` | Web (`POST /api/crm/katalog`, nur Modul finanzen; Aenderung zusaetzlich als `katalog_geaendert` in der Kette) | Web: Angebots-Editor, Angebots-PDF, Preisliste (`/api/crm/katalog/preisliste.pdf`); Chat-Werkzeug `geschaeftsregeln` (nur Formate/Preise/Zuschlaege/Saetze, FACHAGENTEN_ROUTING R2); Canva-Praesentationslinks DE/EN (`texte.praesentation_*`) -> Angebot (eingefroren), PDF/Beleg/Mail | ja | ja |
| `orchestrator/memory/log.jsonl` | Bot, Voice | dito | ja | ja |
| `orchestrator/state/instagram_token.json` (**Secret**) | `governance/instagram_token.py` | dito | ja | bewusst nein (CEO) |
| `projekt_changelog.md`, `finance/budget.md` | Bot, Web, Agenten | alle | ja | Git |

```doku-check:speicher
antraege/log.jsonl
research/log.jsonl
notifications/log.jsonl
agenda/log.jsonl
aktivitaet/log.jsonl
watch/log.jsonl
brain/log.jsonl
finance/kosten-log.jsonl
investment/log.jsonl
investment/features.jsonl
approvals/log.jsonl
trajektorien/log.jsonl
social/log.jsonl
entwicklung/roadmap.jsonl
ig_inbox/log.jsonl
reel_freigabe/log.jsonl
cutter_ops/jobs_cache.jsonl
cutter_ops/worker_herzschlag.json
crm/log.jsonl
content_ops/aiinbox_cache.jsonl
content_ops/drafts_cache.jsonl
content_ops/ideas_cache.jsonl
content_ops/sources_cache.jsonl
content_ops/trends_cache.jsonl
nutzung/log.jsonl
agenten_nutzung/log.jsonl
backoffice/log.jsonl
buchhaltung/log.jsonl
buchhaltung/firmendaten.json
```

Bewusst ohne Backup (Caches, die aus Supabase neu entstehen, und fluechtige Zustaende):

```doku-check:ohne-backup
content_ops/aiinbox_cache.jsonl
content_ops/drafts_cache.jsonl
content_ops/ideas_cache.jsonl
content_ops/sources_cache.jsonl
content_ops/trends_cache.jsonl
cutter_ops/jobs_cache.jsonl         # Cache von luna_cutter_jobs
cutter_ops/worker_herzschlag.json   # wird bei jedem Worker-Poll neu geschrieben
orchestrator/state/luna_os_sitzungen.json  # Login-Sitzungen (nur Token-Hashes); Verlust = einmal neu anmelden
```

**MACO470** (WSL, Benutzer `luna`): `~/CutterInbox`, `~/CutterOutbox`, `~/ReelOutbox/<datum>/`,
`~/ReelState/` (`clip_index.json`, `used*.jsonl`, `source_allowlist.txt`), `~/whisper-models`,
`~/LUNA-Backups/<stamp>/`, `~/env-backups/`, Clip-Archiv read-only unter `/mnt/nas-clips`.
**MacBook:** `~/LUNA-Backups/` (Zweit-Backup), `~/.luna_orb/` (Orb-IPC).

## 4. Eingaenge und Zeitplaene

**Eingaenge**

- **Telegram:** Long-Poll `getUpdates` im Container `luna-telegram` — genau ein Poller, nie zusaetzlich starten.
- **LUNA-OS** (Container `luna-os`, Port 8765, extern `https://os.hanserautisch.synology.me`): HTTP-Basic-Auth
  (CEO aus `.env` oder Team-Nutzer aus `luna_os_users`); ausgenommen nur `/api/webhook/*` (Meta, per
  Verify-Token/HMAC geprueft). Routen-Gruppen: Kern (`/api/state`, `/api/me`, `/api/events`, `/api/prefs`,
  `/api/settings`, …), Chat/Voice (`/api/chat`, `/api/tts`, `/api/sehen`, `/api/brain`), Antraege und
  Entwicklungs-Roadmap, Cutter (`/api/cutter/*`, Maschine-zu-Maschine), Backoffice (`/api/backoffice/*`, Modul
  administration, Maschine-zu-Maschine), Kunden-Stammdaten (`/api/crm/kunden*`, `/api/crm/ansprechpartner/*`,
  Modul crm, schreibt in die Buchhaltungs-Kette), Angebote (`/api/crm/angebote*`, Modul crm: PDF, Gmail-Entwurf,
  Kalender), Katalog/Preisliste (`/api/crm/katalog*`, Speichern nur Modul finanzen), Auftraege (`/api/crm/auftraege*`, `POST /api/crm/angebote/<nr>/auftrag`; Senden nur Modul finanzen), Rechnungen (`/api/finanzen/rechnungen*`, Modul finanzen: Entwurf, Festschreiben, Senden, Zahlung, Storno; Etappe 19: `POST /api/finanzen/rechnungen/alt` (Altrechnung mit Originalnummer + PDF, Ereignis `rechnung_festgeschrieben` mit `alt: true`) und `/<nr>/altmahnung` (Ereignisse `mahnung_erstellt` mit `alt: true` + `mahnung_versendet`); Etappe 18: `POST /api/finanzen/rechnungen/aus-auftrag/<AB>` mit `{"vorkasse": true}` = Vorkasse-Rechnung, Felder `zahlung`/`art`/`abzuege`/`vorkasse_faellig` in den Rechnungs-Ereignissen, `zahlung` in `angebot_angelegt`/`_geaendert`, `vorkasse_cent`/`vorkasse_faellig` in `auftrag_angelegt`; `GET /api/crm/auftraege/<AB>` liefert Rechnungen + Zahlungstext), Belege (`/api/finanzen/belege*`, Modul finanzen: Upload als Base64-JSON (seit 2026-09-30 auch gespeicherte Mails `.eml` und Postfaecher `.mbox` -> `eingangsbelege.datei_importieren`, gleiche Erkennung wie Mails an LUNA, `mail_id` = `eml:<Message-ID>`), Zweck/Begruendung (`POST /api/finanzen/belege/<nr>/zweck`, Ereignis `eingang_zweck`; aus dem CEO-Text ueber weitergeleiteten Mails `zweck_aus_mail`, Feld `zweck` in `eingang_angelegt`, Export-Spalte `Zweck` in `eingangsbelege.csv`), Auslesen lokal inkl. Positionen, Buchen (optional `aufteilung` je Position, auch „privat“), Zahlung/Teilzahlung, Zahlungs-Storno), To-dos der Hauptseite (`GET /api/todos`, je Modul gefiltert, leitet aus Hash-Kette, CRM-To-dos und Reels ab; `POST /api/crm/angebote/<nr>/nachgefasst` -> Ereignis `angebot_nachgefasst` + Nachfass-Termin loeschen, `POST /api/finanzen/hinweis-quittieren` -> Ereignis `finanz_hinweis_quittiert`, `core/todos.py`; Bot 05:00 CFO-Finanzcheck -> Notification-Outbox; Telegram-Nachricht mit Euro-Betrag -> Vorschau-Knoepfe `eur:<ER>:<cent>:<datum>:y|n` -> `euro_buchen` (Ereignisse `eingang_gebucht` + `eingang_bezahlt`) + Kalender-Erinnerung loeschen), Barter (`POST /api/finanzen/rechnungen/<nr>/ware-erhalten` mit Nachweis-Dateien als Base64 -> Belegablage, `/ware-stornieren`; Ereignisse `rechnung_ware_erhalten`/`_storniert`), Mahnungen (`/api/finanzen/rechnungen/<nr>/mahnung-vorschau` + `/mahnung`, `/api/finanzen/mahnungen/<ma>/pdf|versandvorschau|senden`; Ereignisse `mahnung_erstellt`/`_versendet`/`_ausgesetzt`, Versand aus LUNAs Gmail nach Klick; Bot fragt Folgemahnungen 08-20 Uhr per Telegram `mah:<RE>:<stufe>:y|n`, `core/mahnungen.py`), Verlustvortrag (`POST /api/finanzen/verlustvortrag`, Ereignis `verlustvortrag_erfasst`), Jahresabschluss (`/api/finanzen/abschluss`, `/abschluss/export` = ZIP-Download mit CSV/`index.xml`, Kassenbuch, Belegen, PDF; `/abschluss/euer.pdf`; nur Lesen, `core/jahresabschluss.py`), Finanzen (`/api/finanzen/uebersicht?zeitraum=`, `/posten` (Drill-down), `/ki-kosten` (liest `finance/kosten-log.jsonl` + `finance/budget.md`, nur Anzeige), `/journal` (auch CSV), `/euer`, `/anlagen`, `/eigenbelege*`, Modul finanzen: nur Lesen/Falten der Hash-Kette, `core/finanzen.py`; Eigenbelege `EB-JJJJ-NNNN` schreiben `eigenbeleg_angelegt`/`_storniert`, `core/eigenbelege.py`); Bot uebernimmt Anhaenge weitergeleiteter Mails (nur Absender aus `BELEG_ABSENDER`, Standard CEO-Adressen inkl. moin@hanserautisch.de; Suche inkl. Spam, nur mit bestandener DKIM/DMARC-Pruefung, danach Gmail-`modify` SPAM -> INBOX) aus LUNAs Postfach als Beleg (Ausgabe oder Gutschrift/Einnahme); bei Fremdwaehrung legt Bot/Web-App einen Termin „Euro-Betrag eintragen“ in LUNAs Kalender an (Ereignis `eingang_erinnerung`, geloescht nach Buchung) und fordert ueber `backoffice/log.jsonl` (Auftrag `roh`, zweck `beleg:<ER>`) einen KI-Vorschlag an, Reels (`/api/reel/*`,
  **`/freigeben` postet auf Facebook**), CRM/Instagram, Content, Investment (inkl. `…/paper-order`).
- **Voice-Server** (localhost:7860, WebRTC) und **Mac-Orb** (ruft `127.0.0.1:8765`) — nur am MacBook.

**Zeitplaene im Bot** (Europe/Berlin, Pruefung alle 5 min, Merker in `agenda`)

| Zeit | Job | Schalter |
|---|---|---|
| alle 6 h | Watch: GitHub + eine Abteilung (Brave) + IT-Selbstcheck | `WATCH_INTERVAL_HOURS` |
| 02:00 | Nacht-Krypto (Paper) | `INV_AUTO_TRADE` |
| 03:00 | CFO-Kostenlauf (ueber das Backoffice, Meldung ins Morgen-Briefing) | – |
| 04:00 | Security-Audit | `SECURITY_AUDIT_ENABLED` |
| 02:00 | Content-Feed (ueber das Backoffice, Meldungen ins Morgen-Briefing; bis 2026-09-27: 07:00) | `CONTENT_FEED_ENABLED` |
| 07:00 | Merkmals-Snapshot | `INV_FEATURE_LOOP` |
| 08:00 / 20:00 | Briefings | Einstellungen |
| 04:00 | Self-Dev (nur Vorschlaege; ueber das Backoffice, Meldung ins Morgen-Briefing; bis 2026-09-27: 09:00) | `SELF_DEV_ENABLED` |
| Mo 09:00 | Leistungsbericht, Prognosen | – |
| werktags 15:00 / 16:00 | Auto-Paper-Trade / Markt-Screen | `INV_AUTO_TRADE` / `INVESTMENT_AUTO_SCREEN` |
| ~10 min | Depot-/Exit-Monitor | `INV_MONITOR` |
| 15 min | Betriebs-Wacht; Poll: Mail/Kalender, CRM-Sync, CRM-Mail, IG-DMs, IG-Radar (1x taeglich) | `BETRIEBSWACHT_ENABLED`, `INSTAGRAM_DM_POLL`, `IG_RADAR_AUTO` |

**Zeitplaene ausserhalb des Repos** (nicht vom Doku-Check erfasst — bei Aenderung hier pflegen)

| Wo | Zeit | Was |
|---|---|---|
| NAS, DSM-Aufgabenplaner (root) | 03:30 | `docker exec luna-os python -m cutter.reel_daily --einreichen --schnell-index` |
| MACO470, systemd `cutter-worker` | Dauerlauf, Poll 20 s | Cutter-Queue ueber LUNA-OS |
| MACO470, systemd `luna-backup.timer` | 03:20 (`Persistent=true`) | `deploy/backup-from-nas.sh` |
| MACO470, systemd `backoffice-worker` (`deploy/backoffice-worker.service`) | Poll alle 60 s | Backoffice-Auftraege mit lokalem LLM; laedt das Modell nur bei genug RAM (Tag 13 GB, 01-06 Uhr 11 GB), entlaedt nach dem Stapel |
| MACO470, Windows-Aufgabe `LUNA-WSL-Keepalive` | Anmeldung + alle 5 min | haelt WSL am Leben (BF-07) |
| MacBook, launchd `com.hanserautisch.investment-backup` | 03:00 | Zweit-Backup |

## 5. Wege zwischen den Geraeten

| Weg | Wie | Beleg |
|---|---|---|
| Clip-Archiv NAS -> MACO470 | SMB `//192.168.178.129/SocialMediaTeam` per **CIFS** read-only unter `/mnt/nas-clips` (Konto `maco470`, DSM nur-lesen) | `findmnt /mnt/nas-clips`; `docs/maco470-roadmap.md` E6 |
| Cutter-Queue MACO470 <-> NAS | `cutter/luna_bridge.py`: `GET /api/cutter/queue` (zugleich Herzschlag), `POST /api/cutter/report`, `POST /api/reel/einreichen` (Reel als base64-JSON) | `cutter/luna_bridge.py` |
| Backoffice MACO470 <-> NAS | `backoffice/worker.py` ueber `cutter/luna_bridge.py`: `GET /api/backoffice/naechster` (Auftrag wird `in_arbeit`), `POST /api/backoffice/ergebnis`; Modell ueber die **native** Ollama-API (`/api/chat`, `num_ctx` 8192, ohne Werkzeuge) auf `192.168.178.184:11434`; RAM-Messung per `powershell.exe` (Windows); Gegenlesen von Bewertungen/Analysen ueber Gemini | `backoffice/worker.py` |
| Reel -> Facebook | Reel liegt in `reel_freigabe/` auf der NAS -> CEO gibt in LUNA-OS frei -> `governance/facebook_reels.py` | `channels/web/app.py` |
| Backup NAS -> MACO470 | `ssh luna-nas "tar czf - <Liste>" \| tar xzf -` nach `~/LUNA-Backups/<stamp>`, 30 Staende; bei leerem Lauf Exit 1 + Telegram | `deploy/backup-from-nas.sh` |
| Browser/WebApp -> LUNA-OS | Login-Seite `/login` (Formular, Schluesselbund) oder Passkey (`/api/passkey/*`, WebAuthn, nur HTTPS) -> Cookie `luna_sitzung` (HttpOnly, Secure, SameSite=Lax, 30 Tage gleitend); aendernde Anfragen per Cookie nur mit eigener Origin; Maschinen (Waechter, Cutter-Bruecke) weiter HTTP-Basic | `channels/web/app.py` `auth()`, `core/sitzungen.py`, `core/passkeys.py` |
| Deploy MACO470 -> NAS | `deploy/sync-to-nas.sh` (tar ueber ssh, Schutzliste), Neustart per `sudo` durch den CEO | `deploy/sync-to-nas.sh` |
| Code MACO470 -> GitHub | `git push` per Deploy-Key (nur dieses Repo); Fetch anonym per HTTPS; **Repo ist oeffentlich** | `git remote -v` |
| LUNA -> GitHub | Tool `antrag_pushen` pusht Branch `antrag/<id>` | `core/hoa_tools.py` |
| LUNA (NAS) -> lokales LLM (MACO470) | HTTP im LAN auf Port 11434 (Windows-Firewall: nur NAS + WSL, `LOKALES_LLM_ROADMAP.md` Etappe 0); Kontextfenster am Server >= 16384 (BF-17) | `core/lokal_llm.py` |
