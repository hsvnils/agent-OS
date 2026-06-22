# Orchestrierung — wie der Head of Agents das Agenten-Unternehmen steuert

> **Zweck.** Dieses Dokument beschreibt **verbindlich, wie Auftraege durch das Agenten-Unternehmen fliessen**.
> Es **ergaenzt** `AGENTS.md`, ersetzt es aber **nicht**. **Bei Widerspruch gilt `AGENTS.md`.**
> Visuelle Fassung derselben Logik: [`orchestrierung.xmind`](orchestrierung.xmind).
>
> Status: **nur Dokumentation** — noch keine Orchestrierungs-Implementierung / kein Laufzeit-Code. Die
> Umsetzung folgt nach der Framework-Entscheidung.

---

## 1 Grundprinzip

- Der **CEO spricht nur mit dem Head of Agents (HoA)**. **Abteilungs-Agenten sprechen nur mit dem HoA.**
- **Autonomie zuerst:** Jeder Agent loest so viel wie moeglich selbst; **Eskalation ist die Ausnahme**.
- **Architektur: Supervisor-Pattern** — der **HoA ist der Supervisor**, die **Abteilungen sind Sub-Agenten**.
- **Jede Aktion** wird in `projekt_changelog.md` **protokolliert**.

## 2 Auftrags-Lebenszyklus (Hauptschleife)

1. **CEO-Anweisung empfangen.**
2. **Klaeren — nur wenn noetig** (eine gebuendelte Rueckfrage statt vieler).
3. **In Teilaufgaben zerlegen.**
4. **Zustaendige Agenten waehlen.**
5. **Abhaengigkeiten & Reihenfolge pruefen.**
6. **Delegieren** (Auftragsformat siehe Abschnitt 3).
7. **Agenten arbeiten** (Autonomie zuerst).
8. **Ergebnisse zurueck** (Ergebnisformat siehe Abschnitt 4).
9. **HoA buendelt** und prueft **Qualitaet / Konsistenz / Konflikte**.
10. **Bei Mangel:** mit **konkreter Nachbesserungsanweisung** zurueck an die Abteilung.
11. **Konsolidierte, entscheidungsreife Vorlage an den CEO.**

## 3 Delegations-Auftrag (HoA → Agent)

Enthaelt **stets**:

- **Ziel** — was erreicht werden soll.
- **Kontext** — relevanter Hintergrund.
- **Erwarteter Output** — Form/Format des Ergebnisses.
- **Frist** — bis wann.
- **Constraints** — Grenzen, Vorgaben, Markenregeln etc.
- **Abhaengigkeiten** — wovon/von wem die Aufgabe abhaengt.

## 4 Ergebnis-Rueckmeldung (Agent → HoA)

Enthaelt **stets**:

- **Ergebnis** — das Lieferobjekt.
- **Status** — `fertig` / `blockiert` / `Input nötig`.
- **Offene Punkte** — was noch fehlt oder zu klaeren ist.
- **Annahmen & Quellen** — worauf das Ergebnis beruht.
- **Kosten** — falls relevant (siehe Abschnitt 6).

## 5 Eskalation & Request-Protokoll

> Massgeblich: `AGENTS.md`, Abschnitt 5 (Request-/Freigabe-Protokoll). Hier nur die Orchestrierungssicht.

- **Agent kommt nicht weiter** → an den **HoA**.
- **Technischer Bedarf** → zuerst an den **CTO/IT**; die IT **loest selbst, wenn im Mandat**, und eskaliert
  an den HoA **nur, wenn nicht loesbar**.
- **Blockade** → der **CTO sucht einen Workaround**, bevor der CEO behelligt wird.
- **Zugriffe/Berechtigungen** → der **CISO autorisiert**, der **CTO setzt um**.
- **CEO-Tor-Kategorie** → der **HoA holt die Freigabe beim CEO** ein.

## 6 Kosten & Budget

> Massgeblich: `AGENTS.md`, Abschnitt 5.9 (Kosten & Budget).

- Der **CFO ueberwacht alle Kosten**, zeigt sie an und fuehrt eine **Monats-Kostenstatistik mit Verlauf**
  (`finance/kosten-statistik.md`).
- **Neues Modell/Dienst/Abo** → **CFO-Kostenvoranschlag** → **HoA**.
- Der **HoA verwaltet das Monatsbudget** (Quelle: `finance/budget.md`); **innerhalb des Budgets steuert er
  eigenstaendig**.
- **Passt es ins Budget und ist es wichtig** → **CEO-Freigabe**.

## 7 CEO-Tor-Kategorien (immer Freigabe)

Geld/Kosten · Recht/Vertraege · Oeffentlichkeit/Veroeffentlichung · neue kostenpflichtige Tools/Modelle/Abos ·
Mandats-/Charta-Aenderungen · Loeschen von Daten.

## 8 Inter-Agenten-Zusammenarbeit

- **Keine eigenmaechtigen Alleingaenge** zwischen Agenten.
- Braucht ein Agent den **Output eines anderen**, meldet er die **Abhaengigkeit dem HoA**; der **HoA
  sequenziert**.
- Fuer **wiederkehrende Ablaeufe** darf der HoA **vordefinierte Workflows** festlegen, z. B. Content:
  **CCO → CBO-Review → CCO final → CXO-Check**.

## 9 Konfliktloesung

- Widersprechen sich Agenten (z. B. **CBO Marke vs. CRO Umsatz**), **mediiert der HoA**.
- **Ungeloest oder strategisch** → **Entscheidung beim CEO**.

## 10 Status & Gedaechtnis

- **Task- und Statusverfolgung** in einem Aufgabenspeicher (**Supabase**).
- **Entscheidungen** → `projekt_changelog.md`.
- **Langfristiges Wissen** → **CKO** (Supabase **pgvector**).

## 11 Erste aktive Welle

- **Aktiv:** HoA + **CTO, CCO, CFO, CBO**. **Uebrige: Entwurf.**
- Eskaliert eine Aufgabe an einen **noch nicht aktiven Agenten**, **uebernimmt der HoA interim** oder die
  Aufgabe **wartet, bis der Agent aktiviert ist**.
