---
name: zugriffs-pruefung
version: 1.0.0
beschreibung: Prueft Zugaenge, Rollen und Capabilities gegen die Zugriffs-Policy (Least-Privilege) und schlaegt Entzug oder Einschraenkung vor.
lizenz: intern
autor: Claude Code fuer den Head of Agents (AGENTEN_AUSBAU A3/A5, 2026-10-05)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Zugriffs- und Rollenpruefung (CISO)

## Wann anwenden
Bei jeder Anfrage nach einem neuen Zugang (Tool, Konto, Schluessel, Modul in LUNA-OS), bei neuen Team-Nutzern,
monatlich als Durchsicht und nach einem Sicherheitsvorfall.

## Grundlage
`governance/zugriffs-policy.md` (Policy-Tabelle Capability -> erlaubte Agenten), `AGENTS.md` 5.7 (CISO autorisiert,
CTO setzt um, kein Zugriff ohne CISO-konforme Freigabe). Neue externe Zugaenge und neue Kosten sind CEO-Tor.

## Checkliste
1. Wer/was bekommt Zugriff (Agent, Mensch, Maschine wie der Cutter-Worker)? Wofuer genau?
2. Ist die Capability schon in der Policy-Tabelle? Wenn nein: neuer Zugang -> CEO-Tor.
3. Least-Privilege: nur lesen, wo lesen reicht; ein Repo statt Konto (Deploy-Key statt Token); feste IP/Netz, wo moeglich.
4. Secret bleibt in `orchestrator/.env` bzw. ausserhalb des Repos; Agenten erhalten Werkzeuge, nie den Schluessel.
5. LUNA-OS-Nutzer: Rolle und Module passend (`luna_os_users`); Owner-Rechte nur der CEO.
6. Widerruf geklaert: Wie wird der Zugang entzogen, wer macht es?
7. Bestehende Zugaenge: noch genutzt? Ruhende Konten (Status „RUHT“) regelmaessig hinterfragen.

## Ausgabe
Je Zugang: Empfehlung **gewaehren / einschraenken / ablehnen / entziehen** mit Begruendung, noetige Policy-Zeile
(Entwurf) und wer umsetzt (CTO) bzw. freigibt (CEO). Keine Werte von Schluesseln nennen oder anfordern.
