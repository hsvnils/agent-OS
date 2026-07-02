# Autonomie-Stufen — Entwurfsraster fuer autonome Schleifen (Loop Engineering)

> **Lebendes Steuerungsdokument.** `AGENTS.md` bleibt kanonisch und uebergeordnet — bei Widerspruch gilt
> `AGENTS.md`. Dieses Dokument legt **verbindlich** fest, wie JEDE neue **autonome Schleife** im LUNA-System
> entworfen, eingefuehrt und gegated wird. Inspiriert von **„Loop Engineering"** (cobusgreyling, MIT):
> uebernommen werden die **Konzepte** als Entwurfsregeln — **kein** Code-/CLI-Import (die dortigen npm-CLIs
> zielen auf Coding-Agenten/GitHub-Actions; LUNA bringt die Bausteine bereits selbst mit).

---

## 1 Warum

LUNA betreibt zunehmend **autonome Schleifen** (Watcher, Briefings, Self-Development, kuenftig Investment-
Screening). Damit Autonomie **sicher und kostenbewusst** waechst, durchlaeuft jede Schleife dieselbe Treppe
und dieselben Schutzmechanismen. Das ist die operative Auspraegung des Autonomie-Prinzips und der
CEO-Tor-Logik aus `AGENTS.md` (4/5).

## 2 Die Autonomie-Treppe L1 → L2 → L3 (Pflicht)

Jede autonome Schleife startet auf **L1** und steigt nur nach belegtem Track-Record und CEO-Freigabe.

- **L1 — Report (Beobachten/Melden):** Die Schleife sammelt nur Daten und **meldet** (Notifier/Telegram/
  LUNA-OS). Keine Aktion mit Wirkung. Default fuer alles Neue.
- **L2 — Assisted (Vorschlagen/Bestaetigen):** Die Schleife erzeugt **entscheidungsreife Vorschlaege/Antraege**
  (Phase 6); Ausfuehrung **erst nach Bestaetigung** (CEO bzw. bei rein technisch-kostenfreien Faellen die
  definierte Selbstheilungs-Freigabe). Simulierte/umkehrbare Ausfuehrung erlaubt (z. B. Branch+Tests, Paper).
- **L3 — Unattended (Selbststaendig im Mandat):** Die Schleife handelt **innerhalb harter Grenzen** selbst
  (Limits, Kill-Switch, Audit). **Nur** nach gutem L2-Track-Record und ausdruecklicher CEO-Freigabe; jede
  Wirkungskategorie (Geld/Recht/Oeffentlichkeit/Loeschen) bleibt CEO-Tor.

**Stufenwechsel = CEO-Tor** und wird im `projekt_changelog.md` protokolliert.

**Beispiel-Abbildungen:**
- Investment: **advisory = L1/L2**, **paper = L2** (simuliert), **live = L3** (siehe `INVESTMENT_ROADMAP.md`).
- Self-Development: Vorschlag = L2; Ausfuehrung nur ueber freigegebene Antraege (Branch+Tests).
- Watcher/Briefings: L1 (nur Meldungen, token-frugal).

## 3 Maker/Checker (Pflicht ab L2)

Kein Vorschlag/keine wirksame Aktion ohne **Gegenpruefung**: Ein erzeugender Agent (Maker) und ein
**pruefender** Agent (Checker) sind getrennt.

- Investment: Portfolio/Synthese-Agent (Maker) ↔ **Risk-Agent** (Checker) vor jedem Vorschlag.
- Code/Execution: ausfuehrender Agent (Maker) ↔ **Tests + CEO-Merge** (Checker).
- Beschaffung/Kosten: anfragender Agent (Maker) ↔ **CFO-Kostenvoranschlag + HoA-Budgetcheck** (Checker).

## 4 Kosten je Schleife (Pflicht)

Jede Schleife ist **token-/kostenbewusst**:
- **Bulk statt Einzel-Polling**; guenstiges Modell fuer Routine, starkes Modell nur fuer Synthese.
- Der **CFO** fuehrt Kosten **je Schleife/Dienst** in der Kostenstatistik; drohende Budget-Ueberschreitung wird
  fruehzeitig gemeldet (`finance/budget.md`).
- Neue kostenpflichtige Dienste/Modelle bleiben **CEO-Tor** (Kostenvoranschlag + Budgetcheck zuerst).

## 5 Weitere Bausteine (bereits im System vorhanden)

Loop Engineering nennt fuenf Bausteine; LUNA deckt sie ab:
- **Scheduling/Automations** → `core/scheduler.py` (WatchScheduler), Briefing-/Self-Dev-Loops.
- **Skills/persistentes Wissen** → **Second Brain** (`core/brain.py`) + Gedaechtnis.
- **Plugins/Connectors (MCP)** → Google Workspace, Web-Research, kuenftig Finanz-MCPs.
- **Sub-Agenten (Maker/Checker)** → `delegate` + Fachagenten + Risk/Tests.
- **Worktrees/Isolation** → Git-Branch-Sandbox der Execution-Engine.

## 5b Loop-Anatomie (jeden Loop so entwerfen)

Loop Engineering (breiter gefasst, popularisiert Juni 2026 von **Addy Osmani**, aufbauend auf Peter Steinberger
+ Anthropics Boris Cherny): Grundidee -- **nicht den einzelnen Prompt schreiben, sondern den Loop entwerfen,
der den Agenten fuer einen ansteuert.** Menschliches Urteil steckt im **System-Design** (Akzeptanzkriterien,
Verzweigungen, Retry/Stop), nicht in Handarbeit je Modellaufruf. Jede LUNA-Schleife wird entlang dieser fuenf
Teile spezifiziert:

1. **Ziel (messbar):** Woran ist „gut/fertig" erkennbar? (z. B. „N neue, relevante Trend-Kandidaten").
2. **Trigger:** Zeitplan (`core/scheduler.py`/WatchScheduler) oder Event (Webhook/neue Mail/DM).
3. **Lauf:** welche Agenten/Tools, welche Modelle (Routine guenstig, Synthese stark), **Bulk statt Einzel**.
4. **Verifikation/Eval:** Akzeptanzkriterien + **Maker/Checker** (§3) + ggf. **Team-Review** (L1/L2).
5. **Stop-Bedingung:** Limits (max. Kandidaten/Lauf, Token-/Kostenbudget, Zeit) + **Kill-Switch/Notbremse**.

Autonomiegrad (L1→L2→L3, §2) und Kostenrahmen (§4) sind Teil jeder Loop-Spezifikation. Wirkungskategorien
(Geld/Recht/Oeffentlichkeit/Loeschen) bleiben CEO-Tor.

## 6 Checkliste fuer eine neue autonome Schleife

1. **Start auf L1** (nur melden). Zweck + Datenquelle + Meldeweg festlegen.
2. **Kostenrahmen** definieren (Bulk, Modellwahl, CFO-Erfassung).
3. **Maker/Checker** benennen (spaetestens fuer L2).
4. **Aufstieg L1→L2→L3** nur mit Track-Record + **CEO-Freigabe**; Wirkungskategorien bleiben CEO-Tor.
5. **Kill-Switch/Limits/Audit** vor L3. Jede Stufe: Self-Checks gruen, Changelog, Commit.

> Referenziert aus `governance/orchestrierung.md` und `INVESTMENT_ROADMAP.md`. Gilt fuer alle autonomen
> Schleifen, nicht nur Investment.
