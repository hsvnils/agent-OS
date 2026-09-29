# Datenschutz-Check der KI-Nutzung (Entwurf)

> **Entwurf zur Entscheidung durch den CEO** (BETRIEB_ROADMAP Etappe 4, 2026-09-29). Keine Rechtsberatung: Rechtliche
> Fragen sind CEO-Tor (`AGENTS.md` 4) -- im Zweifel Datenschutz-Anwalt/-Generator. Belege: Code-Stellen und
> `docs/datenfluesse.md`; externe Quellen mit Datum.

## 1. Kurzfassung

- **Buchhaltung und Belege bleiben im Haus.** Belegtexte liest das lokale Modell auf dem MACO470 (`eingangsbelege.
  llm_beauftragen` -> Backoffice-Auftrag `art="roh"`, kein Gegenlesen durch Gemini). Rechnungen, Kunden und Finanzen
  haben keine Chat-Werkzeuge -- sie laufen ueber LUNA-OS, nicht ueber ein Cloud-Modell.
- **Der Chat laeuft ueber Gemini (Google).** Ueber seine Werkzeuge koennen dabei **personenbezogene Daten Dritter** zu
  Google gehen: Mails (`mail_lesen`, `posteingang`, `mail_suchen`), Instagram-DMs (`crm_konversation`, `crm_dm_abrufen`),
  Drive-/Tabellen-Inhalte, Bildschirmfotos (`bildschirm_sehen`). Dazu die DM-Analyse (`core/ig_analyse.py`, Standard
  `gemini-flash-latest`) und das Gegenlesen von Bewertungen/Analysen im Backoffice (`backoffice/worker.py`).
- **Training: nein.** Googles Gemini-API-Bedingungen (Stand 28.04.2026, ai.google.dev/gemini-api/terms): Fuer Nutzer im
  EWR/der Schweiz/UK gelten die Datenregeln der **Bezahl-Stufe auch fuer die Gratis-Stufe** -- „Google doesn't use your
  prompts ... or responses to improve our products“; Speicherung nur zur Missbrauchserkennung. Der Registereintrag vom
  2026-07-06 („Free-Tier nutzt Inhalte zum Training“) ist fuer den CEO (Deutschland) damit **ueberholt** (korrigiert).
- **EU AI Act:** fuer das heutige LUNA kaum Pflichten -- siehe 4.

## 2. Wohin gehen welche Daten? (Stand Code 2026-09-29)

| Weg | Dienst | Daten | Personenbezug Dritter | Beleg |
|---|---|---|---|---|
| Belege/Rechnungen auslesen | lokal (Ollama, MACO470) | Belegtext | ja (Lieferanten), bleibt im Haus | `core/eingangsbelege.py` `llm_beauftragen` |
| Chat (Telegram/LUNA-OS) | **Gemini** (Standard seit 2026-09-26), lokal als Ausweich | Nachricht + Werkzeug-Ergebnisse | **ja**, wenn Mail-/CRM-/Drive-Werkzeuge genutzt werden | Register „Gemini-Gratis-Tier als Standard fuer den Chat“; `core/model_router.py`, `core/hoa_tools.py` |
| Bildschirm sehen (Phase 17) | Gemini | Bildschirmfoto | moeglich (was gerade offen ist) | `docs/datenfluesse.md` (Screenshots) |
| DM-Analyse Collab-Radar | Gemini (Modell per `IG_ANALYSE_MODELL`) | Instagram-DMs von Marken/Personen | **ja** | `core/ig_analyse.py` |
| Backoffice-Gegenlesen | Gemini | Entwurf von Bewertungen/Analysen (Auftraege `bewertung`/`analyse`) | je nach Auftrag | `backoffice/worker.py` `GEGENLESEN` |
| Reel-Schnitt/Tagging | Gemini (nur mit `CUTTER_VIDEO_KI=1` bzw. Tagging) | Videoclips aus dem eigenen Archiv | Personen im Stadion (ohnehin oeffentlich gepostet) | `cutter/gemini_video.py`, `cutter/reel_tag.py` |
| Sprache rein | Deepgram | Sprachnachrichten des CEO | kaum (CEO selbst) | `docs/datenfluesse.md` |
| Sprache raus | ElevenLabs / Cartesia | LUNAs Antworttext | moeglich (wenn die Antwort Dritte nennt) | `channels/web/app.py` `/api/tts` |
| Web-Recherche | Brave | Suchanfragen | selten | `governance/web_research.py` |
| Anthropic | (Schluessel ungueltig, BF-18) | -- | -- | Register |

Schutz, der schon da ist: `leak_guard` (keine Schluessel an Modelle), `input_guard` (Prompt-Injection-Pruefung, PII-
Erkennung bei Mail/Web/DM), Mails an Kunden nur nach CEO-Klick mit festen Vorlagen, keine automatischen DMs.

## 3. DSGVO-Punkte (Einordnung, keine Rechtsberatung)

1. **Auftragsverarbeitung mit Google:** Wer personenbezogene Daten Dritter (Mails, DMs) an Gemini gibt, braucht nach
   Art. 28 DSGVO einen Auftragsverarbeitungsvertrag. Fuer die Bezahl-Stufe gilt Googles „Data Processing Addendum“; ob
   es fuer die Gratis-Stufe im EWR ebenfalls greift, geht aus den Bedingungen **nicht eindeutig** hervor. -> offen (5.1).
2. **Informationspflicht:** Marken, die per DM oder Mail anfragen, sollten in der Datenschutzerklaerung von
   hanserautisch.de erfahren, dass Anfragen mit KI-Diensten (Google) ausgewertet werden (Art. 13/14 DSGVO). -> offen (5.2).
3. **Datenminimierung:** Der Chat bekommt Mails/DMs im Volltext; noetig ist das nur, wenn der CEO danach fragt
   (Werkzeuge werden je Nachricht ausgewaehlt, `core/werkzeugauswahl.py`) -- das ist schon sparsam.
4. **Drittland:** Google, Deepgram, ElevenLabs sind US-Anbieter; Uebermittlung ueblicherweise ueber das EU-US Data
   Privacy Framework bzw. Standardvertragsklauseln des Anbieters -- im jeweiligen Konto pruefen. -> offen (5.1).

## 4. EU AI Act (Einordnung)

Quelle: Art. 50 und Art. 113 (artificialintelligenceact.eu, abgerufen 2026-09-29).

- **Art. 50 Transparenz gilt ab 2. August 2026.** Fuer LUNA heute:
  - *KI spricht direkt mit Personen:* nur der CEO und sein Team chatten mit LUNA; Dritte bekommen keine automatischen
    KI-Antworten -> keine Hinweispflicht. **Sollte LUNA kuenftig Marken/Fans selbst antworten, muss sie sich als KI zu
    erkennen geben.**
  - *Deepfakes:* Reels werden aus echtem Material geschnitten, nicht erzeugt -> nicht betroffen (anders bei kuenftiger
    KI-Videoproduktion).
  - *KI-Texte fuer die Oeffentlichkeit:* Ausnahme, wenn ein Mensch prueft und redaktionell verantwortet -- Captions und
    Posts gibt der CEO frei (Posten ist CEO-Tor) -> erfuellt.
- **Art. 4 KI-Kompetenz** (gilt schon): Betreiber sollen fuer ausreichende KI-Kompetenz der Beteiligten sorgen -- fuer
  ein Kleinstunternehmen: Team kurz einweisen, was LUNA darf und was nicht.
- Moegliche Verschiebungen durch das „Digital Omnibus“-Paket der EU sind hier **nicht** geprueft (Stand vor Umsetzung
  nachsehen).

## 5. Empfehlungen (CEO entscheidet)

1. **Google-Konto pruefen (CEO, 10 Minuten):** In Google AI Studio / Cloud-Konsole des Projekts „LUNA“ nachsehen, ob
   der EWR-Standort hinterlegt ist und das Data Processing Addendum akzeptiert werden kann. Falls nur mit Bezahl-Stufe:
   Kosten beim aktuellen Volumen gering -- Beschaffung ist CEO-Tor (Kostenvoranschlag CFO).
2. **Datenschutzerklaerung ergaenzen (CEO/Generator):** Satz zur KI-gestuetzten Bearbeitung von Anfragen (Google Gemini,
   ggf. Deepgram/ElevenLabs). LUNA kann einen Textvorschlag liefern.
3. **Optional technisch (eigene Etappe, nur bei Bedarf):** DM-Analyse auf das lokale Modell stellen
   (`IG_ANALYSE_MODELL` -> lokal) und/oder bei Chat-Werkzeugen mit Mails/DMs E-Mail-Adressen, Telefonnummern und IBANs
   vor dem Senden an Gemini maskieren (`input_guard.redigiere_pii` gibt es schon, heute nur fuer Protokolle).
4. **Regel fuer spaeter:** Neue Funktionen, die Dritten automatisch antworten oder Inhalte erzeugen, bekommen vorab einen
   KI-Hinweis (Art. 50) -- als Punkt in die Roadmap-Vorlage aufnehmen, sobald so etwas geplant wird.

## 6. Offen fuer den CEO

- 5.1 Google-Konto (EWR, Data Processing Addendum), 5.2 Datenschutzerklaerung, 5.3 ob die optionale Maskierung/Lokal-
  Umstellung gewuenscht ist.
