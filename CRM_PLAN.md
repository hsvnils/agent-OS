# CRM_PLAN.md — Collab-CRM (unter dem CRO)

> Leichtgewichtiges CRM fuer eingehende Kooperations-/Sponsoring-Anfragen. **Nur lesen/tracken/vorschlagen —
> kein automatisches Senden** (Oeffentlichkeit = CEO-Tor). Kanalagnostisch angelegt (Instagram ist der erste
> Kanal); Fundament fuers geplante Partner-/Akten-System. Konsistent mit `AGENTS.md` (kanonisch), Charta-System,
> Capability-/Secret-Muster, Second Brain, Changelog-Pflicht, `.md`-Konvention (umlautfrei).

## Ziel
DMs von Unternehmen (Collab-Anfragen) automatisch auslesen, daraus Kontakt-Historie + Status je Firma bilden
und LUNA **smarte To-do-Vorschlaege** liefern. Der CEO antwortet selbst.

## Einordnung
- Neue Faehigkeit + Unter-Agent **Collab-CRM** unter dem **CRO** (`agents/04_cro.md`, per HoA/CEO-Freigabe
  ergaenzt). Autonomie-Prinzip: arbeitet selbst, eskaliert an LUNA nur bei Bedarf.

## Datenspeicher (File-Store, KEIN Supabase)
`orchestrator/core/crm.py` -> `CrmStore` (event-sourced JSONL `crm/log.jsonl`, gitignored + sync-excludet,
leck-geschuetzt). Event-Typen statt separater Tabellen:
- `nachricht` (firma, quelle=instagram|telegram|gmail|manuell, richtung=ein|aus, text, absender, extern_id)
- `status` (Pipeline: neu -> in_gespraech -> angebot -> vereinbart | abgelehnt)
- `todo` / `todo_erledigt` (Vorschlag, Faelligkeit, Begruendung)
Gefaltete Sichten: `firmen()`, `konversation(firma)`, `todos()`, `uebersicht()` (Pipeline-Zaehlung).
`extern_id` dedupliziert Webhook-Wiederholungen.

## Ersetzt-statt-neu-gebaut (Wiederverwendung)
- **Kein Supabase** -> `CrmStore` (Muster wie `core/antraege.py` / `investment/store.py`).
- **Kein Vercel** -> Webhook als FastAPI-Route in `channels/web/app.py`, oeffentlich ueber die bestehende
  HTTPS-URL `os.hanserautisch.synology.me` (Synology Reverse-Proxy).
- **Alerts/To-dos** -> bestehende Outbox `core/notifications.py` (`melde_an_ceo`).
- **Kontext/Aussagefaehigkeit** -> bestehendes **Second Brain** (`brain_merken`, `quelle="crm"`).
- **Klassifikation** (Kooperation vs. privat) -> bestehendes Backend/`delegate` (Fachagent), kein neuer LLM-Weg.
- **Capability/Secrets** -> `governance/`-Vorlage (`google_workspace.py`), `.env` + `leak_guard`.

## Phasen (GATES)
- **A-Phase 0 — Charta + Store (GATE A):** CRO-Charta ergaenzt, `CrmStore` + Tests, `CRM_PLAN.md`. ERLEDIGT.
- **A-Phase 1 — Instagram-Anbindung (GATE B):** Capability-Modul `governance/instagram.py` (Auth + Lesen +
  Mock) + Webhook `POST /api/webhook/instagram` (Meta-Signatur/Verify-Challenge). CEO richtet Meta-App +
  Genehmigung ein, Token in `.env` (CEO-Tor + CISO). Self-Checks gegen Mock-DMs.
- **A-Phase 2 — CRM-Logik:** Klassifikation, CRM-Eintrag, Second-Brain-Notiz, To-do-Vorschlaege (Outbox).
  HoA-Tools `crm_zeigen` / `crm_todo_*`.
- **A-Phase 3 — Anzeige:** LUNA-OS-App CRM (`/api/crm` + `app.js`): Pipeline-Uebersicht, Konversation je Firma,
  kuratierte To-dos.

## Governance
Kein Auto-Senden. Instagram-Token/Meta = CEO-Tor + CISO. Changelog-Pflicht je Phase. `.md` umlautfrei.
