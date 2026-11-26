# Zugriffs-Policy — Capabilities und erlaubte Agenten (Least-Privilege)

> **Lebendes Steuerungsdokument.** `AGENTS.md` bleibt uebergeordnet; bei Widerspruch gilt `AGENTS.md`.
> Owner ist spaeter der **CISO**. Bis dieser im Orchestrator aktiv ist, genehmigt der **HoA**
> Policy-Aenderungen; **neue externe Zugaenge = CEO-Tor**. Technische Umsetzung: der **CTO**.

## Prinzip

- **Secrets bleiben in `orchestrator/.env`** (per `.gitignore` ausgeschlossen, nie committen). Kein Tool und
  kein Agent gibt je einen rohen Key aus.
- **Capability-Muster:** Externe Integrationen sind **Tools**, die ihren Key intern aus der `.env` lesen.
  Agenten erhalten **Faehigkeiten (Tools)**, niemals den Key-Text.
- **Least-Privilege:** Ein Agent erhaelt nur die Capabilities, die er fuer sein Mandat braucht.

## Vergabe-Verfahren (CTO-Tool `grant_capability`)

- **Fall A — vorhandene, bereits bezahlte Capability, im Budget:** gewaehren (Agent in die Policy
  aufnehmen), **CEO informieren** + Changelog. Autonom durch die IT auf HoA-Anforderung.
- **Fall B — neue Kosten / neuer externer Zugang / neuer Account:** NICHT gewaehren; **CEO-Freigabe-Anfrage**
  erzeugen + Changelog. Budget-Pruefung gegen `finance/budget.md`. Erst nach Freigabe.

## Policy-Tabelle (Capability -> erlaubte Agenten)

> Bootstrap-Stand: noch **keine externen Capabilities** vergeben. Der Betrieb des Orchestrators selbst
> (HoA/Subagenten) laeuft ueber `ANTHROPIC_API_KEY` (GATE B) und ist keine vergebene Business-Capability.

| Capability | Beschreibung | Erlaubte Agenten | Status |
|------------|--------------|------------------|--------|
| `web_research` (ueber den Netz-Agenten) | Recherche-Auftraege an den Netz-Agenten (nur die reine Frage, keine internen Daten); zurueck kommt nur das gepruefte Formular (Antwort, Fakten mit Quellen, `unsicher`). | **res (Researcher)**; Watcher, Content-Feed, Firmen-/Impressum-Suche, Modell-Radar und Rechtsquellen als feste Auftraggeber ueber `core/netz_auftraege.py` | **LIVE** seit 2026-10-26 (NETZ_AGENT Q3); vorher Brave direkt aus LUNA (2026-06-25 bis 2026-10-26) |
| `web_research` (Anthropic-Web) | Agentische Mehrschritt-Recherche; frueher Eskalation. | -- | **AUS** seit 2026-10-26 (`ANTHROPIC_WEB_ERLAUBT=False`; freie Websuche nur ueber den Netz-Agenten, CLAUDE_AKTIV-Entscheidung 2026-10-23) |
| `google_workspace` (gmail, calendar, drive, sheets) | Zugriff auf LUNAs **eigenes** Google-Konto `luna.hanserautisch@gmail.com` (seit 2026-09-28; kein Zugriff mehr auf hanserautisch@gmail.com): Mails/Termine/Dateien/Sheets lesen; Senden/Aendern/Schreiben nur gated. | **hoa (LUNA)** | **LIVE** seit 2026-06-25 (OAuth-Credentials in `.env`, Mac + NAS; Mac+Container-Live-Test OK) |
| `allinkl_mail` (SMTP + IMAP, Postfach `luna@hanserautisch.de`) | Kundenmails (Angebot, Auftragsbestaetigung, Rechnung, Mahnung, Projektbericht, Konzept) **nur nach CEO-Klick** bzw. Telegram-✅ senden; Kopie per IMAP in „Gesendet“ ablegen; Anmelde-Pruefung ohne Versand. Seit M2: Posteingang **nur lesen** (readonly, Gelesen-Status bleibt, nichts verschieben/loeschen) und nur Antworten auf eigene gesendete Belege uebernehmen. Zugangsdaten nur in `orchestrator/.env` (NAS), nie im Git/Log. | **hoa (LUNA)** ueber die Web-App/den Bot | **LIVE** seit 2026-10-05 (MAILVERSAND_ALLINKL M1; Zugangsdaten vom CEO eingetragen, Testmails ok, `KUNDENVERSAND=allinkl` auf CEO-Anweisung) |
| `nils_mail` (SMTP + IMAP, Postfach `nils@hanserautisch.de`, KONTAKTE K5) | Freie Mails an Ansprechpartner mit Absender nils@ **nur nach CEO-Klick** in LUNA-OS (Modul finanzen); Kopie per IMAP-APPEND in „Gesendet“ von nils@. Posteingang **nur lesend** (`select readonly`, `BODY.PEEK`) und **nur Antworten auf von LUNA gesendete Mails**: Server-Suche nach `<luna-` in `In-Reply-To`/`References`, Kopfzeilen werden nachgeprueft, erst dann wird der Inhalt geladen -- alle anderen Mails werden nie heruntergeladen; nichts verschieben/loeschen/markieren. Zugangsdaten `NILS_MAIL_USER`/`NILS_MAIL_PASSWORT` nur in der NAS-`.env`, vom CEO selbst eingetragen, nie im Git/Log/Fehlertext. **CISO-Pruefung 2026-11-19:** Auflagen oben in `governance/allinkl_mail.py` `NilsMail` umgesetzt und per Test belegt (`test_kontakt_nils.py`, Gegenproben rot). **Restrisiko:** Das Passwort oeffnet technisch das ganze Postfach -- die Begrenzung ist Code; daher Widerruf jederzeit: Passwort im All-Inkl-KAS aendern oder die zwei Zeilen aus der `.env` entfernen + Neustart. | **hoa (LUNA)** ueber Web-App (Senden) und Bot-Poll (Antworten) | **FREIGEGEBEN (CISO, Auflagen)**, live sobald der CEO die Zugangsdaten eintraegt |
| `hsvinside_mail` (nur IMAP, Postfach `moin@hsvinside.de`, OFC_ROADMAP O0) | Fanclub HSVInside: Posteingang **nur lesend** (`select readonly`, `BODY.PEEK`) und **nur Mails von PayPal, Eventim und HSV** (Server-Suche `FROM` nach den Domains `paypal.de`, `paypal.com`, `eventim.de`, `eventim.com`, `hsv.de`, erweiterbar per `HSVINSIDE_ABSENDER`); der Absender-Kopf wird nachgeprueft, erst dann der Inhalt geladen -- alle anderen Mails werden nie heruntergeladen. **Kein Senden**, nichts verschieben/loeschen/markieren. Zugangsdaten `HSVINSIDE_IMAP_HOST`/`HSVINSIDE_MAIL_USER`/`HSVINSIDE_MAIL_PASSWORT` nur in der NAS-`.env`, vom CEO selbst eingetragen. Analyse-Endpunkte nur fuer den CEO (Rolle owner), Berichte ohne Namen/Betraege (maskiert). **CISO-Pruefung 2026-11-24:** Auflagen in `HsvInsideMail` umgesetzt, Tests `test_ofc.py` mit Gegenproben. **Restrisiko:** Passwort oeffnet technisch das ganze Postfach -- Begrenzung ist Code; Widerruf: Passwort im KAS aendern oder `.env`-Zeilen entfernen + Neustart. | **hoa (LUNA)** ueber LUNA-OS (nur CEO) | **FREIGEGEBEN (CISO, Auflagen)**, live sobald der CEO die Zugangsdaten eintraegt |
| `fanclub_nas` (Mount `HSVInside_Shared/Fanclub HSVInside` -> `/fanclub_nas` in `luna-os`, OFC_ROADMAP O0) | Nur dieser Unterordner der Freigabe. O0/O1 nur lesend (`:ro`); **ab O2 (CEO-Go 2026-11-24) schreibend**: LUNA benennt nur Ticket-Dateien um (`os.rename` nach Vorschau + Bestaetigung, nie ueberschreiben -- Kollision auch bei Gross/Klein abgelehnt), **loescht nie** (Gegenprobe-Test `test_ofc_namen.py`); jede Umbenennung als Ereignis `ofc_name` protokolliert, „Rueckgaengig“ moeglich. **Ab O3:** LUNA legt zusaetzlich neue Spielordner und fehlende Rechnungs-/Ticket-Dateien aus HSV-Mails an -- nur neu (`open(..., "xb")`), nie ueberschreiben, nie loeschen (Gegenprobe `test_ofc_post.py`). Nicht im Container `luna-telegram`. | **hoa (LUNA)** ueber LUNA-OS | **FREIGEGEBEN (CISO, E2)**, aktiv nach `docker compose up -d` durch den CEO |
| `google_workspace` -> Tabelle „Mitgliedschaftsanfrage“ (OFC_ROADMAP OM) | Kein neuer Zugangstyp: vorhandener Google-Zugang von LUNA; der CEO hat die Tabelle mit LUNAs Konto **als Betrachter** geteilt. Code nutzt nur `files.list` und `values.get` (Gegenprobe-Test `test_ofc_mitglieder.py`), speichert nichts, gibt nichts an ein KI-Modell. Anzeige nur fuer den CEO (Rolle owner). Widerruf: Freigabe der Tabelle in Google zuruecknehmen. | **hoa (LUNA)** ueber LUNA-OS (nur CEO) | **FREIGEGEBEN** (CEO E5, Freigabe als Betrachter; CISO: nur lesend) |
| `luna_os_api` (Konto `maco470-worker`) | Maschinen-Konto des Cutter-Workers auf dem MACO470: Queue lesen (`/api/cutter/queue`), Job-Status melden, fertige Reels zur CEO-Freigabe einreichen. Rolle `content`, Modul `content_ops` — **kein** CEO-Konto, jederzeit revozierbar. | **cutter-worker (MACO470)** | **RUHT** seit 2026-09-25 — der MACO470 ist jetzt die volle Werkbank; auf CEO-Entscheidung nutzt der Worker dort das **CEO-Konto**. Zugangsdaten des Maschinen-Kontos gesichert ausserhalb des Repos (`~/env-backups/`), Konto bleibt fuer einen Rueckweg bestehen. |
| `freigabe_link` (oeffentlicher Pfad `/teilen/<schluessel>`) | Kunden ohne LUNA-OS-Konto sehen und laden **genau einen** Kundenordner: 32-Byte-Zufallsschluessel (nur SHA-256 in der Kette), Ablauf 7/30/90 Tage (kein Link ohne Ablauf), optional Passwort (PBKDF2), jederzeit widerrufbar, Abruf-Protokoll (IP gekuerzt), Bremse 120 Abrufe/Minute je IP + Sperre nach 5 Fehlversuchen (unbekannter Schluessel, falsches Passwort), keine anderen Pfade ohne Anmeldung, Downloads nur als Anhang, strenge Sicherheits-Kopfzeilen (CSP, noindex, no-referrer). Anlegen/Widerrufen nur angemeldet in LUNA-OS. | **Kunden (extern), nur lesen**; Verwaltung: CEO in LUNA-OS | **gebaut** 2026-10-19 (KUNDENORDNER F2, Weg A), live mit dem Deploy F1-F3 |
| `netz_agent` (Container `luna-netz`) | Freie Websuche (Brave) und Abruf **nur der Treffer-Seiten**; eigener Container ohne LUNA-Dateien und ohne LUNA-`.env` (eigene `netz_agent/.env` nur mit `BRAVE_API_KEY`), lesendes Dateisystem, keine Rechte (`cap_drop: ALL`, `no-new-privileges`), kein Port nach aussen; private/lokale Ziele gesperrt; seit Q2 ein Modell (`claude-haiku-5-5`, Workspace „luna-netz“, Limit 20 USD) **ohne Werkzeuge** mit festem Ergebnis-Schema; Quellen nur aus den Suchtreffern; eigenes Docker-Netz, Heimnetz im Container-Netz gesperrt (Q4), ohne Sperre nimmt er keine Auftraege an; unsichtbarer Seitentext wird verworfen, fremde Links im Formular ersetzt (Q5). | **Netz-Agent (Arbeiter des Researchers, keine Charta)** | **live** seit 2026-10-23 (Q1-Q4 live 2026-10-26); **einziger** Weg fuer freie Websuche und freie Seitenabrufe (Regel `AGENTS.md` 5.7) |
| `app_kennzahlen` (Function `luna-kennzahlen` der Hanserautisch-App, `APP_KENNZAHLEN_ROADMAP.md`) | Nur **HTTPS-GET** an genau diese eine Adresse mit eigenem Token `HANSERAUTISCH_LUNA_API_TOKEN` (nur aus der Umgebung lesen, nie in Log/Fehlertext/Antwort/Datei/Repo); kein Datenbank-Zugang, kein Supabase-Schluessel, keine Aenderung am App-Projekt. Es kommen nur Tagessummen (keine Konten, Namen, Inhalte); Abo- und Umsatzzahlen gehen an **kein** KI-Modell, kein Chat-Werkzeug. Archiv nur auf der NAS. Widerruf: neues Token in der App, Zeile aus der `.env` entfernen + Neustart. | **hoa (LUNA)**: Abruf in `luna-telegram`, Anzeige in `luna-os` (nur CEO, E1) | **FREIGEGEBEN (CISO, Auflagen)** 2026-11-26 (CEO-Go AK0-AK3; Auflagen in `core/app_kennzahlen.py`, Tests `test_app_kennzahlen.py` mit Gegenproben, Wachtest `test_netz_wache.py`); Meldungen nie in den Chat-Verlauf/Chat-Werkzeuge; live nach Deploy + `docker compose up -d`; Token nur in der NAS-`.env` (vom CEO uebertragen, MACO470-Kopie entfernt); Schutzbedarf vertraulich, nicht personenbezogen; Sperren per neuem Token in Supabase (altes sofort 401) |
| `nas_smb_archiv` (DSM-Konto `maco470`) | **Nur-Lese**-Zugriff per SMB/CIFS auf die Freigabe `SocialMediaTeam` (Rohclip-Archiv), gemountet als `/mnt/nas-clips`. Nur SMB, kein DSM-Login, kein Schreibrecht. | **cutter-worker (MACO470)** | **LIVE** seit 2026-08-12 (Credentials in `/etc/cifs-nas.cred`, chmod 600) |
| `nas_ssh_deploy` (SSH-Schluessel `maco470-deploy-nas`) | Deploy-Weg MACO470 -> NAS (`deploy/sync-to-nas.sh`, tar-over-ssh als Benutzer `nilskrueger`). **Eingeschraenkt auf die feste IP 192.168.178.184** (`from=`-Option in `authorized_keys`) — von anderen Adressen wertlos. Container-Neustart bleibt beim CEO (sudo). | **Claude Code auf dem MACO470** | **LIVE** seit 2026-09-24 (privater Schluessel nur in `/home/luna/.ssh/luna-nas`, chmod 600) |
| `lokal_llm` (Ollama auf dem MACO470, Port 11434) | Lokales LLM ohne Anmeldung (Ollama kennt keine). Absicherung ueber die **Windows-Firewall**: Regel „Ollama API" nur fuer die NAS (`192.168.178.129`) und das WSL-Netz (`172.16.0.0/12`); keine Portfreigabe nach aussen. Nur Inferenz, keine Daten auf dem MACO470 gespeichert. | **hoa (LUNA) + Fachagenten** (NAS-Container), **Claude Code auf dem MACO470** | **eingerichtet** 2026-09-25 (Firewall + `OLLAMA_CONTEXT_LENGTH=16384`, `OLLAMA_KEEP_ALIVE=30m`); Nutzung durch LUNA erst mit den `.env`-Schaltern (`LOKALES_LLM_ROADMAP.md`) |
| `github_push` (Deploy-Key `maco470-deploy-github`) | Push-Recht auf das Repo `hsvnils/agent-OS` vom MACO470 aus. Bewusst **Deploy-Key statt Token**: nur dieses eine Repo, kein Zugriff auf andere Repos oder das GitHub-Konto, jederzeit einzeln loeschbar. Holen laeuft weiter anonym per HTTPS. | **Claude Code auf dem MACO470** | **LIVE** seit 2026-09-25 (Deploy-Key mit Schreibrecht, vom CEO bei GitHub eingetragen; privater Schluessel nur in `/home/luna/.ssh/github`) |

> **Google-Sicherheitsmodell (CEO 2026-06-25): Lesen frei, Schreiben/Senden/Aendern nur nach Bestaetigung.**
> Read-Tools (mail_suchen/lesen, kalender_agenda, drive_suchen/lesen, tabelle_lesen) laufen direkt.
> Write-Tools (mail_senden, termin_anlegen, tabelle_schreiben) liefern OHNE `bestaetigt=true` nur eine
> **Vorschau** und werden erst nach ausdruecklicher CEO-Bestaetigung ausgefuehrt (Mensch-Tor, AGENTS.md 4).
> **Ausnahme (CEO 2026-09-28):** LUNAs **eigene**, im Kassenbuch protokollierte Erinnerungen zu erledigten Angeboten/
> Rechnungen loescht sie ohne Rueckfrage (`core/erinnerungen.py`); fremde Termine bleiben gated.
> `mail_entwurf` ist sicher (legt nur einen Entwurf an, sendet nicht). Least-Privilege ueber OAuth-Scopes
> (CISO autorisiert); Credentials NUR in `orchestrator/.env` (separates Konto), Refresh-Token nie im Repo.
> **Go-Live:** OAuth-Setup laut `deploy/google-oauth-setup.md`; ohne Credentials -> Fall-B-Hinweis (CEO-Tor).

> **To-do-Termine (CEO 2026-10-27, TODOS_ROADMAP):** Kalendertermine zu eigenen To-dos des CEO legt LUNA ohne Rueckfrage an,
> verschiebt und loescht sie -- nur diese eigenen, protokollierten Termine (Termin-ID am To-do in `todos/log.jsonl`);
> fremde Termine bleiben gated.

> **Ab 2026-10-26 (NETZ_AGENT, Regel `AGENTS.md` 5.7):** Freie Websuche und freie Seitenabrufe nur noch ueber den
> Netz-Agenten; Brave ruft nur er auf (`BRAVE_API_KEY` nur in `netz_agent/.env`), Anthropic-Web ist aus. Die beiden
> folgenden Absaetze sind Historie.
>
> **Routing-Policy (CEO, 2026-06-25):** **Brave zuerst** -- immer. Anthropic-Web (billbar) wird NUR genutzt,
> wenn Brave nicht verfuegbar ist, ein Limit/Fehler liefert, keine Treffer bringt, ODER der CEO eine
> **Revision/weitere Recherche** beauftragt (`eskalation`). Schlaegt Anthropic-Web fehl (z. B. Guthaben),
> faellt der Researcher automatisch auf Brave zurueck. So bleiben die Kosten niedrig.
>
> **Least-Privilege (Phase 8.5):** Die Web-Capability haelt **ausschliesslich der Researcher (Agent 15)**.
> Andere Abteilungen erhalten Web-Infos **nur ueber ihn** (via LUNA): sie melden ihren Bedarf an den HoA, der
> den Researcher beauftragt (`recherche_beauftragen` -> Research-Ticket). So gibt es **einen** Ort fuer
> Kosten, Rate-Limit und Audit.
>
> **Offen:** Anthropic-`web_search` laeuft ueber die **raw API (Pay-as-you-go-Guthaben)**, nicht ueber das
> CLI-Abo. Es wird erst wirken, wenn das Anthropic-API-Guthaben aufgeladen ist (console.anthropic.com/Billing).

> **Go-Live `web_research` (Fall B, CEO-Tor):** Beide Provider sind externer Zugang/Kosten.
> - **Brave Search API** -- ✅ aktiv. `BRAVE_API_KEY` in `orchestrator/.env` (Gratis-Kontingent; vom CEO geliefert).
> - **Anthropic-Web** -- nutzt den vorhandenen `ANTHROPIC_API_KEY`, ist aber **billbar** (ca. 10 USD je 1000
>   Suchen + Token). Bleibt **aus**, bis der CEO die Kosten freigibt durch `WEB_RESEARCH_ANTHROPIC=1` in
>   `orchestrator/.env` (vorher CFO-Kostenvoranschlag). Bis dahin laufen auch komplexe Anfragen ueber Brave.
> Ohne Freigabe liefert der jeweilige Provider einen Fall-B-Hinweis statt Ergebnissen (kein Absturz).

## IT-Selbstheilung (CEO-Delegation 2026-06-25)

> **Eng begrenzte Autonomie.** Der CEO hat LUNA/IT erlaubt, **rein technische, kostenfreie** Fixes (nur
> Strom) **selbst** freizugeben, umzusetzen (Branch + Tests) und bei gruenen Tests nach main zu mergen --
> ohne CEO-Freigabe. Werkzeug: `technische_freigabe(antrag_id)`; nur fuer Antraege der Kategorie
> **`technisch-kostenfrei`**.
> **Hart ausgeschlossen (immer CEO-Tor):** Geld/Kosten/neue Abos, Recht/Vertraege, Oeffentlichkeit,
> Secrets/Keys, Charta/Mandat/Governance, Daten-Loeschung. Code-Schutz: Kategorie-Pflicht + Stichwort-Scan +
> Tests-gruen-Pflicht + Notbremse + CEO-Meldung mit Bericht + Git-Reversibilitaet. Diese Delegation beruehrt
> AGENTS.md 4 NICHT (kein Geld/Recht/Oeffentlichkeit).

## Aenderungshistorie

| Datum | Capability | Agent | Aktion | Genehmigt durch |
|-------|------------|-------|--------|-----------------|
| 2026-06-25 | `web_research` | berater, cto | vorbereitet (Code+Tests) | offen (CEO-Tor) |
| 2026-06-25 | `web_research` (Brave) | berater, cto | **live** (BRAVE_API_KEY hinterlegt) | CEO (Key geliefert) |
| 2026-06-25 | `web_research` | res (Researcher) | auf Researcher **verengt** (Least-Privilege, Agent 15 neu) | CEO (Charta-Freigabe) |
| 2026-06-25 | `google_workspace` | hoa (LUNA) | vorbereitet (Code+Tests), noch NICHT live | offen (CEO-Tor + CISO) |
| 2026-06-25 | `google_workspace` | hoa (LUNA) | **live** (OAuth fuer hanserautisch@gmail.com, Mac+NAS) | CEO (Konto + Zustimmung) |
| 2026-09-28 | `google_workspace` | hoa (LUNA) | **umgestellt** auf LUNAs eigenes Konto luna.hanserautisch@gmail.com (MACO470+NAS); alter Zugang auf hanserautisch@gmail.com vom CEO widerrufen und geprueft (`invalid_grant`) -- `LUNA_GOOGLE_KONTO_ROADMAP.md` | CEO (Konto, Zustimmung, Widerruf) |
| 2026-08-12 | `luna_os_api` | cutter-worker (MACO470) | **live** (Maschinen-Konto `maco470-worker` statt CEO-Zugang) | CEO (MACO470-Roadmap E3, 2026-07-14) |
| 2026-08-12 | `nas_smb_archiv` | cutter-worker (MACO470) | **live** (DSM-Konto `maco470`, nur Lesen, nur SMB) | CEO (Konto selbst angelegt) |
| 2026-08-17 | — | — | beide Zugaenge **nachdokumentiert** (bei der Anlage am 12.08. versaeumt, E3 verlangt sie) | HoA (Pflege) |
| 2026-09-24 | `nas_ssh_deploy` | Claude Code (MACO470) | **live** (ed25519, `from=`-Bindung an 192.168.178.184) | CEO (ausdruecklich am 2026-09-24) |
| 2026-09-24 | `github_push` | Claude Code (MACO470) | vorbereitet (Deploy-Key erzeugt, Push-Remote auf SSH); **Eintrag bei GitHub = CEO** | CEO (ausdruecklich am 2026-09-24) |
| 2026-09-25 | `github_push` | Claude Code (MACO470) | **live** (Deploy-Key bei GitHub eingetragen, erster Push vom MACO470 = dieser Commit) | CEO (Key eingetragen) |
| 2026-09-25 | `lokal_llm` | hoa + Fachagenten (NAS), Claude Code (MACO470) | Firewall von „alle im privaten Netz" auf NAS + WSL-Netz **eingeschraenkt**; vorher war Ollama fuer jedes LAN-Geraet offen | CEO (ausgefuehrt am Windows-Rechner, `LOKALES_LLM_ROADMAP.md` Etappe 0) |
| 2026-09-25 | `luna_os_api` | cutter-worker (MACO470) | Maschinen-Konto **ruht**; MACO470 bekommt die volle `.env` des MacBooks inkl. CEO-Konto (**revidiert E3 fuer den MACO470**) | CEO (ausdruecklich: „der darf auf dem MACO ruhig CEO-Konto sein") |
| 2026-10-19 | `freigabe_link` | Kunden (extern) | **neuer oeffentlicher Pfad** `/teilen/*` (CISO-Pruefung: nur dieser Ordner, Ablauf, Passwort optional, Widerruf, Protokoll, Bremse, Pfadschutz; Tests `test_ordner_freigabe.py` mit Gegenprobe) | CEO (Go Weg A, 2026-10-19) + CISO-Pruefung (HoA, Kriterien aus `KUNDENORDNER_FREIGABE_ROADMAP.md` F2) |
| 2026-10-23 | `netz_agent` | Netz-Agent | **neuer isolierter Container** fuer freie Websuche (nur Treffer-Seiten, keine LUNA-Dateien/-Secrets, keine privaten Ziele) | CEO (Go Q1, 2026-10-23) + CISO-Pruefung (HoA, Kriterien `NETZ_AGENT_ROADMAP.md` Q1) |
| 2026-10-26 | `web_research` | Researcher u. a. | Brave direkt aus LUNA **entzogen** (`BRAVE_API_KEY` aus `orchestrator/.env` entfernt), Anthropic-Web **aus**; nur noch Auftraege an den Netz-Agenten | CEO (Go Q3) |
| 2026-10-26 | `netz_agent` | Netz-Agent | Heimnetz gesperrt (Q4), Regel „nur der Netz-Agent geht frei ins Netz“ in `AGENTS.md` 5.7 (Q5) | CEO (Go Q4/Q5, Diff bestaetigt) + CISO-Pruefung (Angriffsreihe `test_netz_angriffe.py`) |
| 2026-11-19 | `nils_mail` | hoa (LUNA) | **neuer Zugang** Postfach nils@ (K5): Senden nur per CEO-Klick, Lesen nur Antworten auf LUNA-Mails (Server-Suche + Kopf-Pruefung, readonly) | CEO (Go K5) + CISO-Pruefung (Auflagen + Tests); Inbetriebnahme = CEO traegt Zugangsdaten ein |
| 2026-11-24 | `hsvinside_mail`, `fanclub_nas` | hoa (LUNA) | **neue Zugaenge** OFC O0: Postfach moin@ nur lesend, nur PayPal/Eventim/HSV; Fanclub-Ordner nur lesend eingehaengt | CEO (E1/E2, Go O0) + CISO-Pruefung (Auflagen + Tests); Inbetriebnahme = CEO traegt Zugangsdaten ein und erstellt `luna-os` neu |
| 2026-11-24 | `google_workspace` (Tabelle Mitgliedschaftsanfrage) | hoa (LUNA) | OFC OM: Mitgliederliste nur lesend aus der geteilten Google-Tabelle | CEO (E5, Go OM; Tabelle als Betrachter geteilt); kein neuer Zugang |
| 2026-11-24 | `fanclub_nas` | hoa (LUNA) | OFC O2: Mount schreibend (nur Umbenennen von Ticket-Dateien, nie loeschen/ueberschreiben) | CEO (E2, Go O2); Inbetriebnahme = CEO erstellt `luna-os` neu (`docker compose up -d luna-os`) |
| 2026-11-24 | `hsvinside_mail`, `fanclub_nas` | hoa (LUNA) | OFC O3: HSV-Mails (nur `hsv.de`, nur lesend) automatisch alle 15 Minuten in `luna-os`; Ordner/Dateien nur neu anlegen | CEO (Go O3); kein neuer Zugang |
| 2026-11-24 | `hsvinside_mail` | hoa (LUNA) | OFC O4: PayPal-Mails (nur `paypal.de`/`paypal.com`, nur lesend) fuer eigene Zahlungen an Eventim/HSV; nur Ergebnisfelder gespeichert | CEO (Go O4); kein neuer Zugang |
| 2026-11-24 | `hsvinside_mail` | hoa (LUNA) | OFC O5: Zahlungseingaenge der Mitglieder aus denselben PayPal-Mails (Name, Betrag, Mitteilung) im Fanclub-Speicher, nur CEO | CEO (Go O5); kein neuer Zugang |
| 2026-11-24 | `fanclub_nas` | hoa (LUNA) | OFC O6: Spielordner nach/aus `Abgeschlossen/` verschieben (nur per Klick mit Vorschau, nie loeschen/ueberschreiben) | CEO (E7, Go O6); kein neuer Zugang |
| 2026-11-26 | `app_kennzahlen` | hoa (LUNA) | **geplant**: neuer lesender Zugang auf die Kennzahlen-Function der App (`APP_KENNZAHLEN_ROADMAP.md`); Token vom CEO auf dem MACO470 eingetragen, einmaliger Lesetest ohne Werteausgabe (HTTP 200), danach per SSH auf die NAS uebertragen und vom MACO470 entfernt | offen (CEO-Go + CISO, AK0) |
| 2026-11-26 | `app_kennzahlen` | hoa (LUNA) | **freigegeben**: Abruf nur GET an die eine Function, Token nur aus der Umgebung, Archiv nur NAS, Anzeige nur CEO, Zahlen an kein KI-Modell | CEO (Go AK0-AK3) + CISO-Pruefung (HoA, Auflagen + Tests) |
