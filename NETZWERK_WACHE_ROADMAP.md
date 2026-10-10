# Roadmap: Netzwerk-Wache (Fritz!Box, NAS, Aussensicht)

- Status: in Umsetzung
- Stand: 2026-10-10
- Arbeitsbranch: `ai/netzwerk-wache`
- Basiscommit: `6f20343`
- Naechster Schritt: Deploy; CEO legt die Konten in Fritz!Box und DSM an, traegt sie mit NETZWERK_WACHE=1 in die NAS-.env ein und startet die Container neu -- dann erster echter Lauf und Abnahme.
- Hinweis: Diese Roadmap ist ein geplanter Ablauf und wird nur durch einen ausdruecklichen CEO-Auftrag zur
  aktuellen Arbeit. Sie aktiviert keine Umsetzung automatisch.

## Ziel (CEO, 2026-10-10)

„Koennte LUNA auch mein Netzwerk, die Netzwerk-Sicherheit usw. ueberwachen?“ -- Antwort: ja, als **Wache, die nur liest
und meldet**. Kein Mitlesen des Datenverkehrs, keine Aenderungen am Netzwerk.

## Analyse (read-only, 2026-10-10)

- Register (`docs/entscheidungs-register.md`): zu Netzwerk-Ueberwachung noch kein Eintrag.
- Vorhanden: Sicherheits-Agent (CISO, `core/security_agent.py`, taeglich 04:00) prueft nur LUNAs **eigenen Code**
  (Geheimnisse, Haertung, Abhaengigkeiten, Code-Muster, OSV) -- nicht das Netzwerk. Selbstwartung (`systemcheck`) prueft
  LUNAs Prozesse, nicht Router oder NAS-System.
- Netz: Heimnetz 192.168.178.0/24 (NAS .129, MACO470 .184) -- die Fritz!Box als Router ist naheliegend, Adresse und Modell
  sind **nicht nachgewiesen** (in N1 pruefen). Von aussen offen: Port 443 fuer LUNA-OS (Reverse-Proxy auf der NAS,
  Let's-Encrypt, DDNS `hanserautisch.synology.me`).
- Schutz vorhanden: Abrufe ins Heimnetz sind fuer die Impressum-Suche gesperrt (BF-60, `firmendaten.oeffentlich`). Die
  Wache braucht dafuer eine **eigene, eng begrenzte Ausnahme** (nur die zwei festen Adressen aus der `.env`).
- Offene Fragen (in der jeweiligen Etappe klaeren, nicht behauptet):
  - Fritz!Box-Schnittstelle TR-064: Welche Benutzerrechte sind fuer die Lese-Abfragen mindestens noetig? Die Fritz!Box kennt
    kein reines Lese-Konto -- daher erlaubt LUNAs Code **nur eine feste Liste von Lese-Aktionen** (Test prueft das).
  - NAS: Geht der Sicherheitsberater ohne Admin-Konto? Sonst Ausweichweg SNMP v3 (nur lesen) fuer System/Platten und
    Sicherheitsberater nur als Hinweis „bitte in DSM ansehen“.

## Etappe N1: Fritz!Box

- Status: umgesetzt
- Ziel / Scope (nur lesen, alle 15 Minuten im Bot-Takt, regelbasiert, kein LLM):
  - **Neue Geraete:** Liste der Geraete im Netz (Name, MAC, IP, WLAN/LAN, Gastnetz). Unbekanntes Geraet -> Telegram
    „🆕 Neues Geraet im Netz: …“ mit Knoepfen **„✅ Kenne ich“** (Name vergeben) / **„❓ Kenne ich nicht“** (bleibt markiert,
    Hinweis was zu tun ist -- Sperren macht der CEO in der Fritz!Box).
  - **Portfreigaben:** Ist-Liste gegen die Soll-Liste (heute: 443 -> NAS). Jede zusaetzliche Freigabe = Meldung.
  - **Firmware:** Update verfuegbar -> Meldung (einmal, nicht taeglich).
  - **Internet:** Ausfaelle/Neuverbindungen und neue oeffentliche IP (nur Protokoll; Meldung bei Ausfall > 10 min).
  - **Gastzugang/WLAN:** an/aus als Zustand in der Uebersicht.
- Technik: eigener schlanker TR-064-Client ohne neue Bibliothek (nur Standardbibliothek, Digest-Anmeldung), feste
  Allowlist der Lese-Aktionen; Zugangsdaten `FRITZBOX_URL`/`FRITZBOX_USER`/`FRITZBOX_PASSWORD` nur in der NAS-`.env`.
  Geraeteliste in `netzwerk/geraete.json` (nur NAS, nicht in der Kette, loeschbar, im Backup).
- Nicht-Scope: Geraete sperren, Ports schliessen, Einstellungen aendern (bleibt beim CEO).
- Gate: Tests (Allowlist -- jede schreibende Aktion wird abgelehnt, neue/bekannte Geraete, Soll-Ist-Ports, keine
  Doppelmeldung, Gegenprobe rot); echte Abfrage gegen die Fritz!Box nach CEO-Freigabe des Kontos.
- Aufwand: mittel.

## Etappe N2: NAS (Synology)

- Status: umgesetzt
- Ziel / Scope (nur lesen, taeglich 06:00 + bei Befund sofort):
  - **Anmeldungen:** fehlgeschlagene Anmeldungen und automatisch gesperrte IP-Adressen (Auto-Block) -> Meldung bei
    Haeufung oder neuer gesperrter Adresse.
  - **Sicherheitsberater:** Ergebnis/Stand des letzten Scans (wenn mit dem Konto lesbar, sonst Hinweis).
  - **Updates:** DSM- und Paket-Updates verfuegbar.
  - **Platten und Speicher:** Zustand (SMART), Volume-Status, freier Platz (Warnung unter 15 %).
- Technik: DSM-Web-API mit eigenem Konto (`DSM_USER`/`DSM_PASSWORD`, nur NAS-`.env`); falls fuer einzelne Werte Admin noetig
  waere: SNMP v3 nur lesen als Ausweichweg -- **kein Admin-Konto fuer LUNA** ohne gesonderte CEO-Entscheidung.
- Nicht-Scope: Updates installieren, Sperrlisten aendern, Dienste neu starten.
- Gate: Tests mit aufgezeichneten Antworten (kein Netz), Gegenprobe rot; echte Abfrage nach CEO-Freigabe.
- Aufwand: mittel.

## Etappe N3: Aussensicht und Uebersicht

- Status: umgesetzt
- Ziel / Scope:
  - **Zertifikat** von `os.hanserautisch.synology.me`: Ablauf in weniger als 21 Tagen -> Meldung.
  - **DDNS:** zeigt der Name auf die aktuelle oeffentliche IP der Fritz!Box (aus N1)?
  - **Uebersicht:** Kachel „🛡 Netzwerk“ unter LUNA & System (Ampel je Bereich: Geraete, Ports, Firmware, NAS, Zertifikat),
    Geraeteliste mit „bekannt/unbekannt“ und Umbenennen.
  - **Einbindung:** Befunde laufen zusaetzlich in den naechtlichen CISO-Bericht (Stufe L1 = melden, keine Aenderung);
    Telegram nur bei Befund, nie taeglich „alles ok“.
- Nicht-Scope: Port-Scan von aussen ueber fremde Dienste (wuerde die eigene IP an Dritte geben) -- die offenen Ports kommen
  aus der Fritz!Box selbst (N1).
- Gate: Tests; Browser Rechner/iPad/iPhone.
- Aufwand: klein bis mittel.

## Umsetzung (2026-10-10, Go CEO fuer N1-N3, Meldeschwelle: jedes neue Geraet sofort)

- Nachweis vorab (read-only, ohne Anmeldung): Router = **FRITZ!Box 7530 AX, FRITZ!OS 8.25** unter 192.168.178.1:49000
  (`/tr64desc.xml`); DSM-API-Verzeichnis (`query.cgi`) bietet alle benoetigten Schnittstellen.
- `core/netzwerk.py`: `FritzBox` (eigener TR-064-Client, Digest, Allowlist `FRITZ_LESEN` -- 18 Lese-Aktionen, alles andere
  `NurLesen`, nie gesendet), `Dsm` (Allowlist `DSM_LESEN`, Passwort im POST-Body, Fehler 105 = „ohne Rechte“), Zertifikat/DNS,
  Regeln `befunde_*`, Zustand `Wache` (`netzwerk/`), Laeufe `lauf_fritz` / `lauf_taeglich`.
- Bot: `_start_netzwerk_loop` (nur mit `NETZWERK_WACHE=1`, Notbremse), alle 15 min Fritz!Box, taeglich ab 06:00 NAS +
  Aussensicht; erster Lauf = Bestand (eine Sammelmeldung statt Flut); neue Geraete mit „✅ Kenne ich“ / „❓ Kenne ich nicht“;
  jeder Befund einmal (wieder, wenn er verschwand und zurueckkommt); Internet-Ausfall ab 10 min nach der Rueckkehr.
- LUNA-OS: LUNA & System -> „🛡 Netzwerk“ (nur administration): Einrichtungs-Haken, Ampel je Bereich, Befunde, Details,
  Geraeteliste (zu pruefen/alle/Gastnetz, bekannt/unbekannt, umbenennen, entfernen).
- CISO-Audit 04:00 nimmt offene Netzwerk-Befunde (warn/alarm) als Kategorie „netzwerk“ auf.
- Tests `test_netzwerk.py` (6, Gegenproben rot: Allowlist, Bestand, einmal melden, Admin-Recht); Browser Rechner/iPad/iPhone.
- Noch nicht live geprueft: echte Antworten mit Konto (Geraeteliste, Portfreigaben, DSM-Felder) -- erst nach der Einrichtung.

## Nicht-Scope (gesamt)

- Kein Mitlesen des Datenverkehrs, keine Einbruchserkennung auf Paketebene (braeuchte eigene Hardware, wenig Nutzen daheim).
- Keine Aenderung an Fritz!Box, NAS, Geraeten oder Diensten durch LUNA -- nur melden und vorschlagen.
- Keine KI auf Netzwerkdaten (alles regelbasiert, Daten verlassen das Heimnetz nur als kurze Telegram-Meldung).

## Entscheidungen fuer den CEO (vor N1/N2)

1. **Zugaenge (CEO-Tor, CISO-Freigabe):** je ein eigenes Konto „luna“ in Fritz!Box und DSM mit den geringsten noetigen
   Rechten; Passwoerter traegt der CEO selbst in die NAS-`.env` ein.
2. **Meldeschwelle:** jedes neue Geraet sofort melden (Empfehlung) oder nur Geraete ausserhalb des Gastnetzes.

## Doku je Etappe

`projekt_changelog.md`, Status hier und in `ROADMAP.md`, `docs/datenfluesse.md` (neue Verbindungen Fritz!Box/DSM, Speicher
`netzwerk/`), `docs/entscheidungs-register.md`, `deploy/sync-to-nas.sh` und `deploy/backup-from-nas.sh` (Ordner `netzwerk/`),
`.gitignore`.

## Definition of Done

LUNA meldet neue Geraete, unerwartete Portfreigaben, faellige Updates, Auffaelligkeiten bei Anmeldungen und Platten sowie
ein bald ablaufendes Zertifikat -- nur lesend, ohne etwas zu veraendern, mit einer Uebersicht in LUNA-OS.
