---
name: deploy-checkliste
version: 1.0.0
beschreibung: Fuehrt durch einen sicheren Deploy auf NAS und MACO470 (Gate, Sync, Neustart durch den CEO, Live-Pruefung).
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A3/A5, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Deploy-Checkliste (CTO)

## Wann anwenden
Vor jedem Deploy und wenn etwas nach einem Deploy nicht laeuft.

## Ablauf (Ist-Stand)
1. **Gate:** ganze Testsuite gruen (gegen die Baseline in `docs/bekannte-fehler.md`), `scripts/doku_check.py` ok,
   Changelog-Eintrag geschrieben, CEO-Go fuer Merge/Push/Deploy liegt vor.
2. **Merge und Push** auf `main` (nur nach gruener Suite).
3. **Sync Code:** `cd ~/ki-unternehmen && bash deploy/sync-to-nas.sh --no-restart` -- Live-Daten (Buchhaltung, CRM,
   Logs, `.env`, `orchestrator/state`) sind ausgenommen. Cutter/Worker: `deploy/sync-to-maco.sh`; Web-Endpunkte
   liegen trotzdem auf der NAS.
4. **Neustart** macht der CEO (sudo): `docker compose restart`; bei neuer Python-Abhaengigkeit `up -d --build`.
5. **Cache-Bust:** bei UI-Aenderung `app-v2.js?v=`/`style-v2.css?v=` erhoeht?
6. **Live-Pruefung:** Version der Oberflaeche, betroffene Endpunkte, Wirkung bis zum Empfaenger (z. B. Telegram
   wirklich zugestellt), Container-Log bei Fehlern.

## Typische Fallen
Neue Abhaengigkeit ohne Rebuild; neue Daten-Ordner nicht vom Sync ausgenommen (Live-Daten ueberschrieben!);
Telegram-Bot doppelt gestartet (nur ein Poller); Aenderung nur auf dem MACO470 deployt, Endpunkt aber auf der NAS.

## Ausgabe
Abgehakte Checkliste, fehlende Schritte, kopierbare Befehle (mit `cd ~/ki-unternehmen &&` vorneweg), Rollback-Weg
(vorheriger Commit). Keine Neustarts oder Werte aus `.env` ausfuehren/anzeigen.
