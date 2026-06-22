# Orchestrierung — wie der Head of Agents das Agenten-Unternehmen steuert

> **Zweck.** Dieses Dokument beschreibt **verbindlich, wie Aufträge durch das Agenten-Unternehmen fließen**.
> Es **ergänzt** `AGENTS.md`, ersetzt es aber **nicht**. **Bei Widerspruch gilt `AGENTS.md`.**
> Visuelle Fassung derselben Logik: [`orchestrierung.xmind`](orchestrierung.xmind).
>
> Status: **nur Dokumentation** — noch keine Orchestrierungs-Implementierung / kein Laufzeit-Code. Die
> Umsetzung folgt nach der Framework-Entscheidung.

---

## 1 Grundprinzip

- Der **CEO spricht nur mit dem Head of Agents (HoA)**. **Abteilungs-Agenten sprechen nur mit dem HoA.**
- **Autonomie zuerst:** Jeder Agent löst so viel wie möglich selbst; **Eskalation ist die Ausnahme**.
- **Architektur: Supervisor-Pattern** — der **HoA ist der Supervisor**, die **Abteilungen sind Sub-Agenten**.
- **Jede Aktion** wird in `projekt_changelog.md` **protokolliert**.

## 2 Auftrags-Lebenszyklus (Hauptschleife)

1. **CEO-Anweisung empfangen.**
2. **Klären — nur wenn nötig** (eine gebündelte Rückfrage statt vieler).
3. **In Teilaufgaben zerlegen.**
4. **Zuständige Agenten wählen.**
5. **Abhängigkeiten & Reihenfolge prüfen.**
6. **Delegieren** (Auftragsformat siehe Abschnitt 3).
7. **Agenten arbeiten** (Autonomie zuerst).
8. **Ergebnisse zurück** (Ergebnisformat siehe Abschnitt 4).
9. **HoA bündelt** und prüft **Qualität / Konsistenz / Konflikte**.
10. **Bei Mangel:** mit **konkreter Nachbesserungsanweisung** zurück an die Abteilung.
11. **Konsolidierte, entscheidungsreife Vorlage an den CEO.**

## 3 Delegations-Auftrag (HoA → Agent)

Enthält **stets**:

- **Ziel** — was erreicht werden soll.
- **Kontext** — relevanter Hintergrund.
- **Erwarteter Output** — Form/Format des Ergebnisses.
- **Frist** — bis wann.
- **Constraints** — Grenzen, Vorgaben, Markenregeln etc.
- **Abhängigkeiten** — wovon/von wem die Aufgabe abhängt.

## 4 Ergebnis-Rückmeldung (Agent → HoA)

Enthält **stets**:

- **Ergebnis** — das Lieferobjekt.
- **Status** — `fertig` / `blockiert` / `Input nötig`.
- **Offene Punkte** — was noch fehlt oder zu klären ist.
- **Annahmen & Quellen** — worauf das Ergebnis beruht.
- **Kosten** — falls relevant (siehe Abschnitt 6).

## 5 Eskalation & Request-Protokoll

> Maßgeblich: `AGENTS.md`, Abschnitt 5 (Request-/Freigabe-Protokoll). Hier nur die Orchestrierungssicht.

- **Agent kommt nicht weiter** → an den **HoA**.
- **Technischer Bedarf** → zuerst an den **CTO/IT**; die IT **löst selbst, wenn im Mandat**, und eskaliert
  an den HoA **nur, wenn nicht lösbar**.
- **Blockade** → der **CTO sucht einen Workaround**, bevor der CEO behelligt wird.
- **Zugriffe/Berechtigungen** → der **CISO autorisiert**, der **CTO setzt um**.
- **CEO-Tor-Kategorie** → der **HoA holt die Freigabe beim CEO** ein.

## 6 Kosten & Budget

> Maßgeblich: `AGENTS.md`, Abschnitt 5.9 (Kosten & Budget).

- Der **CFO überwacht alle Kosten**, zeigt sie an und führt eine **Monats-Kostenstatistik mit Verlauf**
  (`finance/kosten-statistik.md`).
- **Neues Modell/Dienst/Abo** → **CFO-Kostenvoranschlag** → **HoA**.
- Der **HoA verwaltet das Monatsbudget** (Quelle: `finance/budget.md`); **innerhalb des Budgets steuert er
  eigenständig**.
- **Passt es ins Budget und ist es wichtig** → **CEO-Freigabe**.

## 7 CEO-Tor-Kategorien (immer Freigabe)

Geld/Kosten · Recht/Verträge · Öffentlichkeit/Veröffentlichung · neue kostenpflichtige Tools/Modelle/Abos ·
Mandats-/Charta-Änderungen · Löschen von Daten.

## 8 Inter-Agenten-Zusammenarbeit

- **Keine eigenmächtigen Alleingänge** zwischen Agenten.
- Braucht ein Agent den **Output eines anderen**, meldet er die **Abhängigkeit dem HoA**; der **HoA
  sequenziert**.
- Für **wiederkehrende Abläufe** darf der HoA **vordefinierte Workflows** festlegen, z. B. Content:
  **CCO → CBO-Review → CCO final → CXO-Check**.

## 9 Konfliktlösung

- Widersprechen sich Agenten (z. B. **CBO Marke vs. CRO Umsatz**), **mediiert der HoA**.
- **Ungelöst oder strategisch** → **Entscheidung beim CEO**.

## 10 Status & Gedächtnis

- **Task- und Statusverfolgung** in einem Aufgabenspeicher (**Supabase**).
- **Entscheidungen** → `projekt_changelog.md`.
- **Langfristiges Wissen** → **CKO** (Supabase **pgvector**).

## 11 Erste aktive Welle

- **Aktiv:** HoA + **CTO, CCO, CFO, CBO**. **Übrige: Entwurf.**
- Eskaliert eine Aufgabe an einen **noch nicht aktiven Agenten**, **übernimmt der HoA interim** oder die
  Aufgabe **wartet, bis der Agent aktiviert ist**.
