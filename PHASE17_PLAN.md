# PHASE 17 — Teilplan: „LUNA am Mac" (Live-Co-Working am Rechner)

> Untergeordnet `AGENTS.md` (kanonisch) und `governance/autonomie-stufen.md` (L1->L2->L3).
> Voller Vision-Text + Bausteine: `ROADMAP.md` -> „Phase 17". Dieses Dokument ist der **vereinbarte
> MVP-Zuschnitt** (CEO-Entscheidungen 2026-06-28) und der GATE fuer den ersten Schritt.

---

## 1. CEO-Vision (verbindlich, praezisiert 2026-06-28)

Nicht ein fest verdrahtetes Einzel-Skript, sondern **generelle On-Screen-Awareness + echte Mac-Steuerung**:
LUNA **weiss, welche App vorne ist**, welche Programme **installiert** sind, **was jedes Programm kann** und
**welches sie fuer welche Aufgabe** nutzt. Verpackt in einen **kleinen Menueleisten-Orb** (oben neben Akku/
Claude), der **nur laeuft, wenn der Mac an ist**, und der **Zugang ins bestehende LUNA-System** hat (Agenten,
Wissen, Dateien auf der NAS ablegen). Co-Working: CEO sieht die App, spricht/weist an, LUNA setzt **live** um,
CEO justiert per Sprache, LUNA schlaegt selbst vor.

**Harte Randbedingung:** die **bestehende LUNA** (NAS-Container `luna-telegram`, `luna-os`) wird **nicht
angefasst/kaputtgemacht**. Der Mac-Teil ist **additiv** und ein **separater Prozess**.

## 2. Entscheidungen (CEO 2026-06-28)

- **App-Technik:** **native Swift `.app`** (Menueleisten-Orb), nicht Python/rumps.
- **Erster Zuschnitt:** **L1 + L2 mit EINER App** — erster Build bringt schon **eine** benigne, gegatete
  Steuer-Aktion mit, damit Co-Working sofort **live** erlebbar ist.
- **Ort/Kanal:** Steuerung laeuft **lokal am Mac** (wo Schirm + Apps sind); kein NAS->Mac-Befehlskanal im MVP.
  Die Bruecke ins LUNA-System (Wissen/Agenten) laeuft lokal (Orchestrator-Code liegt am Mac) + NAS-Ablage per
  bestehendem `ssh luna-nas`.

## 3. Architektur (zwei Haelften, lokal am Mac)

```
[ Swift Menueleisten-Orb (.app) ]            [ Lokale LUNA (Python) ]
  Augen + Haende + UI                          Verstand + Wissen + Tor
  - NSStatusItem-Orb (idle/listen/speak)  <->  - orchestrator/channels/web (LUNA-OS), lokal
  - Screen Recording (Screenshot)              - HoaConversation + Tools (Gemini/Anthropic)
  - Accessibility (AX-Baum lesen + handeln)    - runner/  (NEU): awareness, capabilities, gate, audit
  - Mikrofon / Voice                           - Bruecke: brain/memory/delegate + NAS-Ablage (ssh)
  - native Bestaetigungs-Sheet (CEO-Tor)
  - Not-Aus-Knopf
        |  localhost HTTP/WS (nur 127.0.0.1)            |
        +----------------------------------------------+
```

- **Native Seite (Swift) besitzt** Capture + Aktuator-Primitive (Permissions haengen sauber am `.app`-Bundle),
  Mikrofon/Voice, den Orb, das **native Bestaetigungs-Sheet** und den **Not-Aus**.
- **Python-Seite besitzt** das Gespraech, die Tool-Entscheidung, **Allowlist/Tor/Audit** und die **Bruecke**
  ins LUNA-System. **Das Tor wird serverseitig (Python) erzwungen** und nativ (Sheet) sichtbar bestaetigt.

## 3a. Klarstellungen CEO (2026-06-28, 2. Runde) — verbindlich

- **„Eine LUNA, zwei Gesichter" (Pflicht):** Mac-Orb und NAS-LUNA sind **dieselbe** LUNA — gleicher Code,
  gleiche Regeln (`AGENTS.md`), gleiche Agenten-Charten (`agents/*`). **Aber** lebender Zustand (Gedaechtnis/
  `brain`, offene Antraege, Meldungen, Verlauf) liegt **live auf der NAS** (sync-ausgenommen). Damit nichts
  **auseinanderdriftet**, liest/schreibt der Mac-Orb diesen Zustand ueber die **NAS-Bruecke** (gemeinsame
  Quelle der Wahrheit), statt eine eigene lokale Insel zu fuehren. Architektur-Invariante, nicht optional.
- **App-Wissen als fortgeschriebene `.md`-Registry:** `runner/capabilities.py` **scannt installierte
  Programme** und schreibt eine **automatisch aktualisierte** `.md` (App -> wofuer gut -> wie steuerbar).
  Bei neu installierten Programmen wird die Registry beim naechsten Scan **aktualisiert**. LUNA leitet daraus
  ab, **welche App ideal fuer eine Aufgabe** ist.
- **Cursor-Steuerung ausdruecklich gewollt/erlaubt:** Maus bewegen/klicken (AX/cliclick) ist Teil des
  Aktuators — unter demselben Tor (Allowlist/Vorschau+Bestaetigung/Not-Aus/Audit).
- **Live-Gespraech ist der KERN (M4):** Duplex-Sprachschleife am Orb wie hinter dem LUNA-OS-Orb — LUNA hoert
  zu, antwortet in der Sprache des CEO, **Barge-in** (Unterbrechen erlaubt), **kombiniert CEO-Kontext +
  On-Screen-Awareness** und bedient dann den Rechner. Nativer Weg: `SFSpeechRecognizer` (DE) + `AVAudioEngine`
  (Echo-Cancellation) = echtes Barge-in ohne Pipecat. **Diese Gespraechsart ist Lunas Kern, nicht ein Add-on.**

## 4. Neue Bausteine

| Modul | Inhalt |
|-------|--------|
| `mac/LunaOrb/` (Swift) | Menueleisten-Orb (NSStatusItem, `.accessory`-Policy), Capture (Screenshot/AX), Aktuator-Ausfuehrung, Voice, Bestaetigungs-Sheet, Not-Aus. Spricht nur mit `127.0.0.1`. |
| `runner/awareness.py` | Vorderste App, Fenstertitel, AX-Zusammenfassung, Screenshot-Abruf -> strukturierter „Was sehe ich"-Kontext. |
| `runner/capabilities.py` | Installierte Apps scannen (`/Applications`, `mdfind`) + **kuratierte Faehigkeits-Karte** (App -> wofuer -> wie ansteuerbar). Waechst. |
| `runner/actuator.py` | Aktuator-Tor: **Allowlist** (Least-Privilege), **Vorschau->Bestaetigung**, **Not-Aus** (respektiert `autonomie_pausieren`), **Audit** in `aktivitaet/log.jsonl`. Geld/Recht/Oeffentlichkeit/Loeschen = CEO-Tor. |
| `orchestrator/channels/web` (+) | Neue lokale Endpunkte fuer Co-Working (observe/act) + neue LUNA-Tools (`bildschirm_sehen`, `apps_kennen`, `rechner_aktion`). Mac-only, import-guarded; NAS-Deploy unberuehrt. |

## 5. Governance (HART)

- **Nur auf ausdrueckliche Anweisung, nie autonom.**
- **Vier Schutzschichten** vor jeder Aktion: Allowlist · Vorschau+Bestaetigung (natives Sheet) · Not-Aus ·
  Audit. **Geld/Recht/Oeffentlichkeit/Loeschen = CEO-Tor.** (Beispiel: Mail **senden** gesperrt, nur Entwurf.)
- **Least-Privilege:** Allowlist startet mit **einer** App + **einem** benignen, umkehrbaren Verb.
- **Autonomie-Treppe:** L1 (sehen/vorschlagen) + L2 (gegatete, umkehrbare Aktion). **Kein L3** im MVP.
- **Maker/Checker:** LUNA (Maker) schlaegt Aktion vor; **CEO-Bestaetigung im Sheet** ist der Checker.

## 6. Erste L2-App (Demo): Klartext schreiben in **TextEdit**

Benigne, voll umkehrbar, sofort sichtbar, keine personenbezogenen Daten, keine Sende-/Loesch-Verben.
Allowlist-Eintrag #1: `TextEdit` -> Verb `text_schreiben` (neues Dokument anlegen + Text einfuegen). Swappbar.

## 7. GATE des MVP

1. Menueleisten-Orb **installiert + startet** (Swift `.app` baut, Orb sichtbar in der Menueleiste).
2. **Awareness** liefert: welche App ist vorne · welche Apps installiert · was kann die App · Screenshot/AX-Read.
3. **Bruecke** steht: LUNA greift auf Wissen (brain/memory) + Agenten zu; NAS-Ablage moeglich.
4. **L2-Demo**: in TextEdit auf Anweisung Text schreiben — **mit Vorschau, Bestaetigung, Audit, Not-Aus**.
5. **Bestehende LUNA unberuehrt** (separater Prozess; NAS-Container nicht veraendert).
6. Self-Checks gruen · Changelog · Commit.

## 8. Milestones (Reihenfolge)

- **M0** — dieser Plan + Changelog + Commit. *(erledigt mit diesem Eintrag)*
- **M1** — Swift-Menueleisten-Orb baut + erscheint + spricht mit lokaler LUNA (`/api/chat`). Drei Orb-Zustaende.
- **M2** — `runner/awareness.py` + `runner/capabilities.py` + Endpunkt; LUNA beantwortet „was siehst du / welche
  App / was kann sie / welche Apps habe ich".
- **M3** — `runner/actuator.py` (Tor: Allowlist/Vorschau/Not-Aus/Audit) + natives Bestaetigungs-Sheet + die
  EINE TextEdit-Aktion. End-to-end Co-Working-Demo.
- **M4** — Voice-Schleife am Orb (Mikrofon -> /api/chat -> TTS) im nativen App-Kontext; GATE-Abnahme.
- **M5** — Tiefes App-Verstaendnis (Inhalte sehen + bearbeiten). **Teil #2 erledigt** (XMind ueber `.xmind`-
  Datei: `runner/xmind.py` + Tools `xmind_lesen`/`xmind_bearbeiten`, gegated). **Teil #3 = Computer-Use**
  (siehe 8a).

## 8a. M5/#3 — Generisches „sehen + bedienen" (Gemini-Loop + deterministisch)

> **Korrektur (CEO-Frage 2026-06-29): Anthropic ist NICHT zwingend.** „Computer Use" = zwei Haelften:
> **Haende** (klicken/tippen) sind gratis + lokal; **Augen+Kopf** (Screenshot deuten -> Aktion entscheiden)
> brauchen EIN multimodales Modell — das kann **Gemini (Gratis-Tier)**, Anthropic (am zuverlaessigsten,
> billbar, ab ~01.07.) oder spaeter ein **lokales** Modell sein. CEO-Wahl: **beides** — Gemini-Loop generisch
> UND deterministische App-Recipes praezise.

**Zwei macOS-Berechtigungen sind der Schluessel** (Befund 2026-06-29): echtes Steuern braucht
- **Bedienungshilfen/Accessibility** — fuer Tastatur/Maus (`keystroke`/Klick); Fehler 1002 ohne.
- **Bildschirmaufnahme/Screen Recording** — fuer Screenshots; serverseitiges `screencapture` schlaegt sonst
  fehl („could not create image from display").
Beide haengen am ausfuehrenden Prozess. **Folge:** Capture + Aktuator gehoeren in den **Orb (.app)** (dort
erteilt der CEO die Rechte einmal sauber), nicht in den terminal-gestarteten Server. Datei-/`open`-Aktionen
(XMind, app_oeffnen) brauchen das NICHT und laufen schon.

**Stand:**
- ✅ **Deterministische Haende (gratis):** Aktuator-Verben `app_oeffnen`, `text_schreiben`, **`tastatur_text`**
  (Text in vorderste App), **`taste`** (Kuerzel wie `cmd+s`/`return`). Logik gebaut + unit-getestet; Ausfuehrung
  braucht Accessibility (s. o.).
- ✅ **Augen + Loop (Gemini), server-seitig gebaut + unit-getestet (2026-07-08):** `runner/computer_use.py` —
  der generische `sehen -> entscheiden -> handeln`-Loop `fuehre_ziel_aus()`. Aus EINEM gesprochenen Ziel macht
  LUNA eine Kette atomarer Schritte (klick/tippe/taste/oeffne_app/fertig/frage). Strikte JSON-Validierung,
  normierte Koordinaten (0..1) -> Bildschirmpunkte (`map_klick`, retina-fest), **Gefahr-Heuristik**
  (`ist_gefaehrlich`: senden/loeschen/kaufen/posten... + `cmd+delete` -> immer anhalten), Konfidenz-Schwelle,
  Not-Aus-Check je Schritt, `max_schritte`-Deckel, Audit je Schritt. **Verhalten „Ansagen & handeln"**
  (CEO-Wahl 2026-07-08): benigne Schritte laufen direkt + werden angesagt; gefaehrlich/unsicher -> **anhalten
  + zurueckfragen, NICHT ausfuehren**. LUNA-Tool **`rechner_ziel`** verdrahtet Orb-Screenshot + Gemini
  (`vision.bild_lesen`) + Aktuator. **Dependency-injected -> 24 Tests gruen ohne Mac/Gemini.**
- **Jede Aktion durch DASSELBE Tor:** `actuator.execute()` (Not-Aus, Allowlist, Audit); gefaehrlich/CEO-Tor
  wird vom Loop **vorher** abgefangen und nie automatisch ausgefuehrt.

**Einziger offener Geraete-Teil (Swift, nur am Mac baubar/testbar):** der Orb muss einen **Screenshot auf
Anfrage** liefern. Der Server schickt `orb_bridge.sende("screenshot")` und erwartet als Antwort-JSON
`{ok, bild_base64, breite, hoehe}` (Breite/Hoehe in **Punkten**, damit `map_klick` stimmt). Heute PUSHt der
Orb Screenshots nur menuegetrieben an `/api/sehen`; fuer den Loop muss `OrbActuator`/`ScreenReader` den
Queue-Befehl `typ:"screenshot"` behandeln (ScreenCaptureKit -> PNG -> base64 + `NSScreen.main` Punkt-Groesse).
Danach laeuft die Kette end-to-end. `cliclick`/CGEvent-Haende + Vision stehen schon.
Anthropic-Computer-Use bleibt optionales Qualitaets-Upgrade.

## 9. Modell-Hinweis

Fluessiges „beliebige App per Hingucken bedienen" wird mit **Claude Computer-Use** am staerksten (selbes
Anthropic-Tor wie Execution, frei ab 2026-07-01). **L1-Awareness + skriptbasierte L2-Aktionen laufen schon
mit Gemini** — der MVP ist model-agnostisch, ab 1. Juli mit Opus schaerfer.
