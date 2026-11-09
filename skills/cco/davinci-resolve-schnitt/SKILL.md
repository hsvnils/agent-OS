---
name: davinci-resolve-schnitt
version: 1.0.0
beschreibung: Waehlt fuer Reels, Shorts und YouTube die passende Schnitttechnik (Keyframes, Uebergaenge, Effekte, Ton, Export) und beschreibt die Umsetzung in DaVinci Resolve 21.
lizenz: intern
autor: Claude Code fuer den Head of Agents (CEO-Auftrag 2026-11-09)
governance: intern
modell: Richtwert (modell-agnostisch)
---

# Skill: Schnitt mit DaVinci Resolve (CCO)

## Wann anwenden
Bei Schnittplaenen und Schnittvorgaben, bei Fragen wie „welcher Effekt, welcher Uebergang, wie Keyframes“, beim Bewerten eines
Schnitts und bei Technikfragen zu DaVinci Resolve. Stand: Resolve 21.1.2. **(S)** = nur in der Studio-Version.

## Ehrlich bleiben
- Prozent-, Frame- und dB-Werte sind **Startwerte aus der Praxis**, keine Gesetze. Am Material pruefen. Plattformen veroeffentlichen
  weder Safe Zones noch Lautheitsziele fuer Reels und TikTok.
- Der automatische Video-Cutter arbeitet mit ffmpeg, nicht mit Resolve. Einen Effekt nur als Vorgabe oder Handarbeit im Programm
  nennen, nie behaupten, er sei schon umgesetzt.

## Rangfolge beim Schneiden
1. Emotion vor Geschichte vor Rhythmus vor Bildregeln. Der Schnitt gehoert ans Gedankenende, den Atemzug, die Bewegung.
2. Jeder Schnitt und jeder Effekt braucht einen Grund: neue Information, neue Perspektive oder Betonung. Tempo entsteht durch
   neue Information, nicht durch Effekte.
3. Der harte Schnitt ist der Standard. Hoechstens eine Hauptbewegung je Einstellung, Zoom, Shake und Overlay nie gleichzeitig.
4. Bewusst ruhig werden vor der Pointe und bei Emotion, Kundenstimme, Zeugenaussage. Ruhe macht den Payoff staerker.

## Programm-Landkarte
| Seite | Wofuer |
|---|---|
| Media | Sichten, Bins, Audio-Sync, Proxies, IntelliSearch |
| Cut | Schneller Rohschnitt, Sync Bin, Viewer-Guides 9:16, Quick Export |
| Edit | Feinschnitt, Trim, Inspector-Keyframes, Retime, Titel, Untertitel, Text Based Editing (S) |
| Fusion | Node-Grafik: Text+, Follower, Tracker, Masken, Parallax, eigene Templates |
| Color | Grade, Scopes, Qualifier, Magic Mask (S), Noise Reduction (S), Tracking, Resolve FX |
| Fairlight | Dialog-Kette, Ducker, Automation, Lautheit, Sound Library |
| Deliver | Presets, Render Queue, Lautheits-Normalisierung, Untertitel einbrennen |

9:16: Timeline 1080x1920 („Use vertical resolution“), Mismatched Resolution auf „Scale full frame with crop“.

## Keyframe-Handwerk
- Ort: Edit > Inspector > Transform (Zoom, Position, Rotation, Anchor), Raute je Parameter, Kurven im Keyframe-/Curve-Editor.
  Dynamic Zoom ist die schnelle Variante, Standard ist Pull-back, mit `Swap` wird es Push-in.
- **Nie linear**, ausser Ticker und Rolltitel. Weiche Fahrt: S-Kurve, Ease an beiden Enden. Resolve benennt Ease nach dem Key:
  Ease Out am Startkey, Ease In am Endkey.
- Kurzer Impuls unter 6 Frames: nur Ease Out, die S-Kurve sieht man dort nicht.
- Titel-Pop: Scale 0 -> 108 -> 100 % in 8-12 Frames. Nicht bei seriosen Bauchbinden.
- Anticipation vor grosser Geste: kurz 98 % (3 Frames), dann hoch. Sparsam.
- Auf Wort: erster Key 2-4 Frames vor dem betonten Wort, Maximum auf Wortbeginn. Auf Beat: Marker setzen, Spitze auf den Beat,
  Anlauf 2-6 Frames davor. Detect Music Beats (S). Nur Schluesselmomente, nicht jeden Beat.
- Frames: 0,1 s = 2,5 f bei 25 / 3 f bei 30 / 6 f bei 60. 0,3 s = 8 / 9 / 18. 0,5 s = 12 / 15 / 30.
- Fehler: linear, Ease nur an einem Ende, Bewegung stoppt kurz vor dem Schnitt, jeder Schnitt gezoomt, wechselnde Zoomtempi.
  Neu in 21: Ease-Modi loop/pingpong/relative, Keyframes ueber mehrere Clips, Inspector-Presets fuer wiederverwendbare Zooms.

## Statisches Bild beleben
| Situation | Technik | Umsetzung | Nicht wenn |
|---|---|---|---|
| Starre Einstellung | Langsamer Push-in | 100 -> 108-115 % in 6-10 s, S-Kurve. Short: 110-120 % in 2-4 s. Long: 5-8 % in 10 s und mehr | Bildrand oder Untertitel knapp; Bewegung darf nicht kurz vor dem Schnitt stoppen |
| Abschied, Reveal, Kontext | Pull-out | 115 -> 100 % in 4-8 s, Ease am Ende | Bei Wort-Pointen |
| Pointe | Punch-in | 100 -> 110-120 % in 4-8 Frames, Ease Out, Zoom bleibt bis zum Schnitt | Bei jedem Satz; Gesicht schon eng |
| Jump Cuts im Talking Head | Stufen 100/110/120 % | Jeder 2.-3. Schnitt andere Stufe, Ton-Crossfade 2-4 Frames | B-Roll waere besser |
| Foto | Ken Burns | Ganzes Bild -> 115-130 % aufs Motiv, 4-6 s (Short 1,5-3 s), Richtung abwechseln | Immer gleiche Bewegung = Diashow |
| Breites Foto | Pan | Vorher 120-140 % skalieren, 6-10 s, Ease an den Enden | Foto zu klein |
| Foto mit Tiefe | Parallax | Vordergrund per Magic Mask (S) oder Depth Map freistellen; Fusion: Image Plane 3D je Ebene, Merge 3D, Camera 3D, 3-6 s kleiner Weg | Haare, Glas, Stadionzaun an der Kante |
| Stativ wirkt tot | Mikrobewegung | Rotation 0,3-0,8 Grad in 6-10 s, Zoom 103-105 % gegen Raender | Horizont sichtbar |
| Impact, Tor | Kurzer Shake | Camera Shake, Motion Scale auf Marker, Abklingen in 6-12 Frames, gesamt 0,2-0,4 s | Dauer-Shake |
| Blick lenken | Weiche Vignette, Window | Circle Window, hohe Softness, aussen leicht dunkler | Rand sichtbar |
| Hinweis, Name | Overlay | Opacity 0-100 % in 6-8 Frames, 20-40 px Einflug, Ease Out, Standzeit ca. 0,2 s je Wort | Mehrere gleichzeitig |

Bewegungsrichtung folgt Blick oder Laufrichtung (Position 1-3 % versetzt).

**Zoom-Reserve:** UHD in 1080p-Timeline verlustfrei bis 200 %. 1080p in 1080p nur ca. 105-110 %. UHD quer in 9:16: Fuellen braucht fast
alle Pixel, nur ca. 12 % Reserve. 1080p quer in 9:16 ist sofort 178 % aufgeblasen und weich: nur als Hintergrund nutzen.

## Uebergaenge
Resolve-Standard ist 1 s, fuer Social fast immer zu lang.
| Situation | Technik | Dauer, Umsetzung | Nicht wenn |
|---|---|---|---|
| Normalfall | Harter Schnitt | Auf Atem, Blick, Bewegung; Ton-Crossfade 2-4 Frames | Unerklaerter Orts- oder Zeitsprung |
| Dialog, Reaktion | J-/L-Cut | Link loesen, Ton 6-12 Frames bis 0,5 s versetzen | Musikschnitt im Takt |
| Bewegung | Schnitt auf Aktion | Mitten in der Bewegung, gleiche Richtung | Richtungsbruch |
| Form, Bewegung verbinden | Match Cut | Zweiten Clip per Zoom/Position auf Deckung, Ton uebergreifen | Traegt die Story nicht |
| Etwas spaeter / Tage spaeter | Cross Dissolve | 8-12 Frames / 1-2 s | Im Talking Head; als Standard |
| Kapitelende | Dip to Black | 12-25 Frames je Seite, Ton mit ausblenden | Short |
| Drop, Schock | Dip to White, Flash | 2-4 Frames + Impact | Dauernd |
| Ortswechsel mit Energie | Whip Pan | Echten Schwenk in der Unschaerfe schneiden. Kuenstlich: Fusion Directional Blur mit Anim Curves (Mirror), 6-10 Frames, Whoosh | Ernstes Thema, falsche Richtung |
| Energie | Zoom-Transition | A: 100 -> 150-200 % in 6-10 Frames, B: 130 -> 100 %, plus Blur | Schwache Aufloesung |
| Warm, Erinnerung, Gastro | Light Leak | Overlay auf V2, Composite Screen oder Add, 12-24 Frames | Reportage, Interview |
| Durch Objekt | Masken-Uebergang | Clip A oben, Maske folgt Objekt, Magic Mask (S) | Objekt verdeckt Bild nicht |
| Kleiner Jump Cut | Smooth Cut | Nur 2-6 Frames, Kopf fast gleich | Kopfbewegung, Blick weg |
| Stil, Tech | Glitch | Chroma-Versatz + Jitter 5-20 px, 2-6 Frames | Dokumentarisch |

Billig wirkt: Stern-, Herz- und Blatt-Wipes, jeder Schnitt ein anderer Uebergang, Whoosh auf jedem Schnitt, Glitch bei ernstem Inhalt.
Sound: Whoosh nur auf sichtbare Bewegung, Spitze auf dem Schnitt. Riser laeuft auf den Moment zu. Impact auf den Aufprall.

## Effekte
**Reihenfolge der Color-Nodes:** Noise Reduction (S), Stabilisierung, Deflicker -> Farbbalance -> Sekundaer (Haut, Magic Mask) -> Look
(Halation, Glow) -> Grain -> Vignette, leichtes Sharpen. Jeder Resolve FX hat einen Blend-Regler. Secondaries nach der Balance.
Grundkorrektur: Belichtung, Kontrast, Balance, dann Hautton an die Skin-Tone-Linie im Vectorscope. Scopes statt Auge.

| Effekt | Wann, Dosis | Nicht |
|---|---|---|
| Speed Ramp | Betonung. 100 -> 25-40 -> 100 %, Rampe 0,3-0,5 s. Variable Speed stummt den Ton | Dauerlupe |
| Zeitlupe | Aus 60 fps auf 40-50 %. 24/25 fps nur mit Speed Warp (S) oder Optical Flow | Zaun, Netz, Haare, Rauch -> Frame Blend oder keine Lupe |
| Freeze Frame | Impact, Info, 0,5-2 s | Unscharfer Frame |
| Stabilisierung | Zuerst, vor Crop. Perspective, bei Randverzerrung Similarity oder Translation | Rolling-Shutter-Wabern, starke Unschaerfe |
| Noise Reduction (S) | Temporal vor Spatial, vor der Korrektur | Wachshaut, Geister |
| Halation, Grain, Film Look Creator | Analogwaerme, Grain kaschiert Banding, je eigener Node | Corporate, Sachlich |
| Glow | Nur Lichter, Threshold hoch, wenig Deckkraft | Action, Hautdetail |
| Lens Blur, CineFocus | Trennung, Rack Focus | Haare, Glas, Haende vor dem Gesicht |
| Text hinter Person | 3 Schichten: Original, Text, Kopie mit Magic Mask (S) | Bewegung ohne Nachfuehren |
| Split Screen, PiP | Vergleich, Reaktion, Crop plus Position | Kleiner Text |
| Farb-Akzent | Qualifier, Rest entsaettigt, sehr selten | Als Masche |
| Face Refinement (S), Blemish Removal | Dezent, Hauttextur erhalten | Plastikhaut |

## Rettung
Verwackelt: Stabilizer und leichter Zoom. Dunkel: Primaries, dann NR selektiv. Mischlicht: je Zone Qualifier oder Magic Mask, oder als
warm/kalt-Stil annehmen. 8-Bit-Handy: Korrekturen klein halten, Grain gegen Banding, Deband (S). Handy mit variabler Bildrate: vorher
pruefen. Nicht rettbar: ausgebrannte Lichter, stark verfehlter Fokus, Bewegungsunschaerfe, uebersteuerter Ton, Digitalzoom.

## Ton (Fairlight)
**Dialog-Kette:** Normalize Audio Levels -> Voice Isolation (S, Amount 50-80; sonst Noise Reduction) -> De-Hummer (50 Hz, nur bei
Brummen) -> Dialogue Leveler -> De-Esser 5-8 kHz -> Compressor 2,5-3:1, 3-6 dB Reduktion -> EQ High Pass 80-100 Hz -> Limiter auf dem Bus.
Nicht stapeln (Voice Isolation hoch plus Background Reduction plus Noise Reduction = Roboterstimme), Clip- oder Track-Ebene, nicht beides.

**Musik:** 12-18 dB unter Sprache. Ducker auf Musikspur mit Dialog-Bus als Quelle, Standard 2-5 dB, bei lauter Musik 6-9 dB, Recovery
600-1000 ms. **Stadion:** Atmo auf eigenem Bus, High Pass 60-100 Hz, Multiband gegen Jubelspitzen, unter Sprecher 3-6 dB ducken, Pegel
folgt der Aktion: Aufbau, Spitze beim Tor, Abfall.

**Lautheit:** um -14 LUFS, True Peak -1 dBTP (Project Settings > Fairlight > Target Loudness; Meter-Standard YouTube). -14 ist bei
YouTube ein Messwert der Community, keine offizielle Zahl; zu Laute werden abgesenkt. Immer am Handylautsprecher pruefen.

## Short-Form (Reels, TikTok, Shorts)
- **Hook 0-3 s** (Instagram misst dort die Skip Rate): Bild mit Bewegung oder Ergebnis, Text 2-5 Woerter, erster Laut ohne Atemluft. Kein Logo.
- Struktur: Hook, knapper Kontext, genau ein Payoff, danach kein Wort mehr. Loop-Ende: letzter Frame passt zum ersten, Ton laeuft durch.
- Talking Head: Jump Cuts alle 2-4 s, sichtbarer Wechsel alle 5-8 s, nie ueber 10-15 s starr. Kein fester Takt, sondern nach Inhalt.
- Laenge an Inhalt koppeln, meist 15-30 s. Gastro eher unter 30 s.
- Untertitel: 3-5 Woerter, hoechstens 2 Zeilen, fette serifenlose Schrift, Kontur, ein Akzentwort, Pop 3-6 Frames, kein Dauerwackeln.
  Wort-fuer-Wort ist Standard und kein Vorteil mehr. Namen und Zahlen pruefen.
- Universal Safe Zone bei 1080x1920: oben 250, unten 500, links 60, rechts 150 px frei. Konservativ, am echten Telefon pruefen.
- Reframe: je Einstellung von Hand, Auto-Reframe (S) nur als Vorschlag, versagt in Menschenmengen. Wenige Keyframes.
- Originalitaet: Instagram, Facebook und YouTube gehen 2026 gegen Wiederverwertung vor. Wasserzeichen, Tempoaenderung oder Voiceover machen
  Fremdmaterial nicht original. Immer aus dem Master exportieren, nie Downloads neu hochladen.

## YouTube Longform
- Erste 30 s loesen das Versprechen aus Titel und Thumbnail ein (YouTube zeigt den Anteil nach 30 s als „Intro“). Thema in ca. 15 s nennen.
- Bildwechsel nach Inhalt, Punch-ins selten, B-Roll bevorzugen, L-/J-Cuts als Standard. Struktur mit „aber/deshalb“ statt „und dann“ pruefen.
- Retention-Kurve lesen: Dips = Ursache suchen, Spikes = Interesse oder Unklarheit, Top Moments nach vorn holen. Eigene Kanalwerte statt fremder Benchmarks.
- Ablauf: Paper Edit, Rohschnitt, Feinschnitt, Ton, Farbe, Grafik, Export. Bei grossen Projekten Proxies.

## Nach Genre
- **Spieltag, Tor:** Aufbau 1-3 s Schnitte, ein klarer Moment je Reel, Schnitt auf den Schuss, kurze Ramp oder Freeze mit Impact, Jubel als Cutaway. Keine langen Lupen, keine Grafikflut.
- **Reaktion:** PiP oder Cutaway, L-Cut, Punch-in 110 % auf Mimik. Reaktion darf nicht den Inhalt verdecken.
- **Talking Head:** Stufen, B-Roll, Textkarten, Pausen raus (IntelliCut (S)), Schnitt auf Wortgrenze.
- **Food:** Textur, Dampf, Sizzle in 50 % aus 60 fps, lauter Ton, warm, Saettigung kontrolliert. Feuer- oder Sizzle-Shot als Opener.
- **Imagefilm:** ruhig, Push-ins 5-10 s, Match Cuts, Dissolves, saubere Titel. Kein Glitch, kein Whip.
- **Interview:** B-Roll 3-6 s mit Interviewton drunter, L-/J-Cuts, Smooth Cut nur bei kleinen Spruengen.
- **Vlog:** Handkamera bleibt, Whip bei Ortswechsel, Speed-up 200-800 % fuer Wege, Stabilizer sparsam.
- **Erklaerung:** ein Fokus je Bild, Grafik mit Ease Out, Beschriftung synchron zum Wort, kein Shake.

## Export
- 9:16: 1080x1920, 30 fps oder Quell-fps, MP4, H.264 High, AAC 48 kHz, 10-16 Mbit/s als Startwert, SDR Rec.709, kein HDR. Deliver-Preset TikTok mit „Use Vertical Resolution“ oder Custom.
- 16:9: Preset YouTube 1080p oder 2160p. MP4, H.264, BT.709, AAC 48 kHz. Ob der Upload in 4K bei 1080p-Material noch etwas bringt, ist unbelegt.
- Untertitel einbrennen: Render Settings > Subtitle Settings > Burn into video. Mehrere Formate: je Job in die Render Queue.

## Was sich automatisieren laesst
Externe Skriptsteuerung und der eingebaute MCP-Server sind (S). Die Skript-API kann Clips anlegen, trimmen, Stille entfernen, statische
Transforms, Effekte anlegen, Auto-Captions, Marker und Rendern. **Keyframes auf Edit-Clips kann sie nicht setzen**, Bewegung geht nur ueber
Umwege (Fusion-Comp je Clip, Fusion-Template, FCPXML), die noch nicht getestet sind. Automatisierungsideen gehen als Antrag an LUNA.

## Pruefliste vor Export
Hook sitzt, Text in der Safe Zone, keine tote Stelle, Payoff am Ende, Untertitel fehlerfrei, Sprache verstaendlich am Handy, Peak unter
-1 dBTP, Haut natuerlich, Bewegungen mit Ease, kein Effekt ohne Grund, Export aus dem Master.

## Grenzen und Freigaben
Veroeffentlichen bleibt CEO-Tor. Vor Nutzung pruefen: Musik- und SFX-Lizenzen, Einwilligung gezeigter Personen, Kundenfreigabe. Voice Convert,
Speech Generator, Face Reshaper und Face Age nie ohne ausdrueckliche CEO- und Personenfreigabe (Recht). Kein Fremdmaterial als eigenes ausgeben.

## Nachschlagen
Vollstaendiges Funktionsverzeichnis mit Handbuchseiten, Node- und Effektlisten, Rezepten und Quellen: Ordner `referenz/` neben dieser Datei
(01 Setup/Media/Cut, 02 Edit/Keyframes, 03 Fusion, 04 Color/Resolve FX, 05 Fairlight/Deliver, 06 Skript-API, 07 Social, 08 YouTube, 09 Techniken).
