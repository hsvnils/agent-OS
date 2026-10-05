---
name: secret-hygiene
version: 1.0.0
beschreibung: Prueft den Umgang mit Schluesseln und Passwoertern (Ablage, Weitergabe, Rotation) und plant Rotationen nach der Checkliste.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A3/A5, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Secret-Hygiene (CISO)

## Wann anwenden
Wenn ein Schluessel im Chat, in einem Screenshot, Log oder Commit aufgetaucht sein koennte, bei der Auswertung des
naechtlichen Security-Audits (04:00), vor Weitergabe von Dateien und als halbjaehrliche Rotation.

## Regeln im System
- Secrets nur in `orchestrator/.env` (Werkbank und NAS), gitignored und vom NAS-Sync ausgeschlossen.
- Der Leck-Schutz redigiert echte Secrets in Ausgaben; Logs und Antworten nennen nie Werte.
- Rotation nach `docs/secrets-rotation-checkliste.md`: neuen Wert erzeugen -> an beiden Stellen eintragen ->
  Container neu starten (CEO) -> Funktion testen -> erst dann alten Wert widerrufen.

## Checkliste bei Verdacht
1. Welcher Schluessel, wo sichtbar gewesen (Chat, Repo, Screenshot, Log), seit wann, fuer wen sichtbar?
2. Reichweite: was kann man damit tun (lesen, senden, zahlen, deployen)?
3. Dringlichkeit: Geld/Konto-Uebernahme -> sofort rotieren; nur lesend und intern -> geplant rotieren.
4. Git-Historie: bei Commit reicht Loeschen nicht -- Schluessel gilt als verbrannt, rotieren.
5. Nachpruefung: Funktion nach Rotation getestet, alter Wert widerrufen, Changelog ohne Werte.

## Ausgabe
Befund (Ampel), betroffene Schluessel nur mit **Namen**, Rotationsplan in der Reihenfolge der Checkliste, offene
Schritte fuer den CEO (Portale, Passwoerter macht der CEO selbst). Niemals Werte ausgeben oder anfordern.
