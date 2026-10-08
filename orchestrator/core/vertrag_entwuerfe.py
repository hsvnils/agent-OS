"""Erste Vertragsentwuerfe fuer das Vertragswerk (VERTRAGSWERK_ROADMAP V2, CEO 2026-10-05: „keine Texte vorhanden“).

HERKUNFT (Korrektur 2026-10-05, CEO): Diese Texte hat **Claude Code** beim Bau von V2 aus allgemeinem Wissen geschrieben --
**nicht** der CLO-Agent (der lief dabei nicht; er hat noch keine Skills und keine Wissensbasis, siehe
CLO_AUSBAU_ROADMAP.md). Sie werden als „Entwurf Claude Code (ungeprueft)“ gespeichert.

ENTWURF -- ANWALTLICHE PRUEFUNG ERFORDERLICH. Keine Rechtsberatung. Die Texte sind auf das Geschaeft zugeschnitten
(Kleinunternehmer nach § 19 UStG, Social-Media-Kooperationen, Kennzeichnung als Werbung, Nutzungsrechte/Whitelisting/
Exklusivitaet wie die Katalog-Zuschlaege, Freigabeprozess der Konzept-Mappe, Vorkasse) und muessen vor dem ersten
Einsatz bei Kunden von einer Anwaeltin/einem Anwalt geprueft werden (CEO-Tor Recht). Platzhalter in geschweiften
Klammern fuellt LUNA beim Vertrag je Auftrag (V3) aus den Auftragsdaten.
"""

ENTWUERFE = {
    "agb": {"titel": "Allgemeine Geschäftsbedingungen für Content- und Werbeleistungen", "paragraphen": [
        {"titel": "§ 1 Geltungsbereich",
         "text": "Diese Allgemeinen Geschäftsbedingungen gelten für alle Verträge zwischen {Auftragnehmer} (nachfolgend "
                 "„Auftragnehmer“) und seinen Kundinnen und Kunden (nachfolgend „Kunde“) über die Konzeption, Produktion und "
                 "Veröffentlichung von Inhalten auf Social-Media-Kanälen sowie damit verbundene Werbeleistungen. Abweichende "
                 "Bedingungen des Kunden gelten nur, wenn der Auftragnehmer ihnen ausdrücklich schriftlich zustimmt."},
        {"titel": "§ 2 Angebot und Vertragsschluss",
         "text": "Angebote des Auftragnehmers sind bis zum angegebenen Gültigkeitsdatum freibleibend. Ein Vertrag kommt mit der "
                 "Annahme des Angebots durch den Kunden (in Textform genügt) und der Auftragsbestätigung des Auftragnehmers "
                 "zustande. Maßgeblich für den Leistungsumfang sind Angebot, Auftragsbestätigung und – soweit vereinbart – das "
                 "freigegebene Konzept."},
        {"titel": "§ 3 Leistungen und redaktionelle Freiheit",
         "text": "Der Auftragnehmer erbringt die vereinbarten Formate (z. B. Reels, Stories, Feed-Beiträge) in eigener "
                 "redaktioneller Verantwortung und Gestaltung. Ein bestimmter Wortlaut oder ein vorgegebenes Skript ist nur "
                 "geschuldet, wenn dies ausdrücklich vereinbart ist. Der Auftragnehmer darf zur Leistungserbringung Dritte "
                 "(z. B. Kamera, Schnitt) einsetzen."},
        {"titel": "§ 4 Reichweite und Plattformen",
         "text": "Angaben zu Reichweiten, Aufrufen, Impressionen und Kontakten beruhen auf Erfahrungswerten (z. B. Median der "
                 "letzten 90 Tage) und sind Planungsgrößen, keine zugesicherten Eigenschaften. Die Ausspielung hängt von den "
                 "Algorithmen der Plattformen ab, auf die der Auftragnehmer keinen Einfluss hat. Eine Mindestreichweite ist "
                 "nur geschuldet, wenn sie ausdrücklich als garantiert vereinbart ist."},
        {"titel": "§ 5 Mitwirkung des Kunden",
         "text": "Der Kunde stellt rechtzeitig alle für die Leistung erforderlichen Informationen, Materialien, Zugänge und "
                 "Ansprechpartner bereit (Briefing, Logos, Produktangaben, Rabattcodes, Drehorte). Er versichert, dass er über "
                 "die Rechte an den bereitgestellten Materialien verfügt und dass Produkt- und Werbeaussagen, die er vorgibt, "
                 "zutreffend und zulässig sind."},
        {"titel": "§ 6 Konzept und Freigabe",
         "text": "Ist eine Konzeptabstimmung vereinbart, legt der Auftragnehmer das Konzept vor der Produktion zur Freigabe vor. "
                 "Der Kunde gibt innerhalb von fünf Werktagen frei oder teilt Änderungswünsche mit; eine Korrekturschleife ist "
                 "im Preis enthalten. Weitere Änderungen nach Freigabe werden gesondert vereinbart. Äußert sich der Kunde "
                 "nicht fristgerecht, darf der Auftragnehmer mit der Umsetzung des vorgelegten Konzepts beginnen."},
        {"titel": "§ 7 Kennzeichnung",
         "text": "Alle bezahlten oder sonst vergüteten Inhalte werden nach den gesetzlichen Vorgaben und den Regeln der "
                 "jeweiligen Plattform als Werbung gekennzeichnet. Wünsche des Kunden, die einer ordnungsgemäßen Kennzeichnung "
                 "entgegenstehen, muss der Auftragnehmer nicht umsetzen."},
        {"titel": "§ 8 Nutzungsrechte",
         "text": "Die Inhalte bleiben urheberrechtlich beim Auftragnehmer. Der Kunde erhält nur die ausdrücklich vereinbarten "
                 "Nutzungsrechte (z. B. Repost auf eigenen Kanälen, Schaltung als Anzeige, Nutzung außerhalb von Social Media) "
                 "in dem vereinbarten zeitlichen und räumlichen Umfang; ohne Vereinbarung ist eine Nutzung durch den Kunden nur "
                 "durch Teilen der Original-Beiträge über die Funktionen der Plattform erlaubt. Rechte an Musik, Marken Dritter "
                 "und abgebildeten Personen werden nur insoweit eingeräumt, wie der Auftragnehmer selbst über sie verfügt."},
        {"titel": "§ 9 Vergütung und Zahlung",
         "text": "Es gelten die Preise des Angebots. Gemäß § 19 UStG wird keine Umsatzsteuer berechnet "
                 "(Kleinunternehmerregelung). Ist Vorkasse vereinbart, beginnt die Produktion nach Eingang der Vorkasse. "
                 "Rechnungen sind innerhalb der angegebenen Frist ohne Abzug zu zahlen. Bei Zahlungsverzug gelten die "
                 "gesetzlichen Regelungen (§§ 286, 288 BGB)."},
        {"titel": "§ 10 Verschiebung und Rücktritt durch den Kunden",
         "text": "Verschiebt der Kunde einen fest vereinbarten Dreh- oder Veröffentlichungstermin weniger als sieben Tage vorher "
                 "oder tritt er vom Auftrag zurück, kann der Auftragnehmer den bis dahin entstandenen Aufwand und bereits "
                 "erbrachte Leistungen berechnen; weitergehende gesetzliche Ansprüche bleiben unberührt."},
        {"titel": "§ 11 Haftung",
         "text": "Der Auftragnehmer haftet unbeschränkt bei Vorsatz und grober Fahrlässigkeit sowie bei Verletzung von Leben, "
                 "Körper und Gesundheit. Bei leichter Fahrlässigkeit haftet er nur bei Verletzung wesentlicher Vertragspflichten "
                 "und begrenzt auf den vertragstypischen, vorhersehbaren Schaden. Für Inhalte und Aussagen, die der Kunde "
                 "vorgibt oder freigibt, stellt der Kunde den Auftragnehmer von Ansprüchen Dritter frei."},
        {"titel": "§ 12 Referenzen",
         "text": "Der Auftragnehmer darf die Zusammenarbeit (Name/Logo des Kunden und veröffentlichte Inhalte) als Referenz "
                 "nennen, sofern der Kunde dem nicht widerspricht."},
        {"titel": "§ 13 Datenschutz",
         "text": "Der Auftragnehmer verarbeitet personenbezogene Daten des Kunden und seiner Ansprechpartner nur zur "
                 "Durchführung des Vertrags und nach den geltenden Datenschutzvorschriften."},
        {"titel": "§ 14 Schlussbestimmungen",
         "text": "Es gilt das Recht der Bundesrepublik Deutschland. Ist der Kunde Kaufmann, juristische Person des öffentlichen "
                 "Rechts oder öffentlich-rechtliches Sondervermögen, ist Gerichtsstand {Gerichtsstand}. Sollte eine "
                 "Bestimmung unwirksam sein, bleibt der Vertrag im Übrigen wirksam."},
    ]},
    "kooperation": {"titel": "Kooperationsvertrag (Content-/Influencer-Kooperation)", "paragraphen": [
        {"titel": "§ 1 Vertragspartner",
         "text": "Zwischen {Auftragnehmer}, {Auftragnehmer_Anschrift} (nachfolgend „Auftragnehmer“) und {Kunde}, "
                 "{Kunde_Anschrift} (nachfolgend „Kunde“) wird zum Auftrag {Auftrag} folgender Vertrag geschlossen."},
        {"titel": "§ 2 Gegenstand und Leistungen",
         "text": "Der Auftragnehmer erstellt und veröffentlicht für den Kunden folgende Inhalte: {Leistungen}. "
                 "Leistungszeitraum: {Leistungszeitraum}. Grundlage sind Angebot und Auftragsbestätigung sowie das "
                 "freigegebene Konzept."},
        {"titel": "§ 3 Konzept und Freigabe",
         "text": "{Freigabe}"},
        {"titel": "§ 4 Kennzeichnung und Pflichtangaben",
         "text": "Alle Inhalte werden als Werbung gekennzeichnet. Der Kunde teilt Pflichtangaben (z. B. Markierung, Link, "
                 "Rabattcode) mit dem Briefing mit; der Auftragnehmer setzt sie um, soweit sie rechtlich zulässig sind."},
        {"titel": "§ 5 Vergütung und Zahlung",
         "text": "Die Vergütung beträgt {Verguetung}. {Zahlungsbedingungen} Gemäß § 19 UStG wird keine Umsatzsteuer berechnet."},
        {"titel": "§ 6 Nutzungsrechte",
         "text": "{Nutzungsrechte} Darüber hinausgehende Nutzungen bedürfen einer gesonderten Vereinbarung."},
        {"titel": "§ 7 Exklusivität",
         "text": "{Exklusivitaet}"},
        {"titel": "§ 8 Reichweite",
         "text": "Genannte Reichweiten sind Planungsgrößen auf Basis von Erfahrungswerten und keine Garantie. Nach Abschluss "
                 "erhält der Kunde einen Projektbericht mit den tatsächlich erreichten Zahlen."},
        {"titel": "§ 9 Haftung und Freistellung",
         "text": "Es gelten die Haftungsregeln der AGB des Auftragnehmers. Für vom Kunden vorgegebene Aussagen, Materialien und "
                 "Freigaben stellt der Kunde den Auftragnehmer von Ansprüchen Dritter frei."},
        {"titel": "§ 10 Laufzeit und Kündigung",
         "text": "Der Vertrag endet mit Erbringung der Leistungen und Ablauf der eingeräumten Nutzungsrechte. Das Recht zur "
                 "Kündigung aus wichtigem Grund bleibt unberührt; Kündigungen bedürfen der Textform."},
        {"titel": "§ 11 Schlussbestimmungen",
         "text": "Ergänzend gelten die AGB des Auftragnehmers in der bei Vertragsschluss gültigen Fassung. Änderungen bedürfen "
                 "der Textform. {Ort}, {Datum}"},
    ]},
    "nutzungsrechte": {"titel": "Vereinbarung über Nutzungsrechte", "paragraphen": [
        {"titel": "§ 1 Gegenstand",
         "text": "{Auftragnehmer} räumt {Kunde} an den im Auftrag {Auftrag} erstellten Inhalten ({Leistungen}) die folgenden "
                 "Nutzungsrechte ein."},
        {"titel": "§ 2 Umfang",
         "text": "{Nutzungsrechte} Die Rechte sind einfach (nicht exklusiv), nicht übertragbar und nur für die eigene Werbung "
                 "des Kunden nutzbar, soweit nicht anders vereinbart."},
        {"titel": "§ 3 Bearbeitung",
         "text": "Kürzen, Untertiteln und Formatanpassungen sind erlaubt; inhaltliche Veränderungen, die den Aussagegehalt "
                 "oder die Darstellung von Personen verändern, bedürfen der Zustimmung des Auftragnehmers."},
        {"titel": "§ 4 Rechte Dritter",
         "text": "Rechte an Musik, Marken Dritter und abgebildeten Personen werden nur eingeräumt, soweit der Auftragnehmer "
                 "darüber verfügt. Für die Schaltung als Anzeige verwendet der Kunde nur lizenzierte Musik."},
        {"titel": "§ 5 Vergütung",
         "text": "Die Einräumung ist mit der vereinbarten Vergütung ({Verguetung}) abgegolten. Eine Verlängerung oder "
                 "Erweiterung wird gesondert vereinbart."},
        {"titel": "§ 6 Ende der Nutzung",
         "text": "Nach Ablauf des Nutzungszeitraums stellt der Kunde neue Nutzungen ein; bereits veröffentlichte organische "
                 "Beiträge auf eigenen Kanälen dürfen bestehen bleiben, bezahlte Schaltungen sind zu beenden."},
    ]},
    "nda": {"titel": "Vertraulichkeitsvereinbarung", "paragraphen": [
        {"titel": "§ 1 Vertrauliche Informationen",
         "text": "Vertraulich sind alle nicht öffentlichen Informationen, die {Kunde} und {Auftragnehmer} einander im "
                 "Zusammenhang mit der geplanten Zusammenarbeit mitteilen, insbesondere Produktneuheiten, Kampagnentermine, "
                 "Konditionen und unveröffentlichte Inhalte."},
        {"titel": "§ 2 Pflichten",
         "text": "Die Parteien behandeln vertrauliche Informationen vertraulich, nutzen sie nur für die Zusammenarbeit und "
                 "geben sie nur an Personen weiter, die sie dafür benötigen und ebenso verpflichtet sind."},
        {"titel": "§ 3 Ausnahmen",
         "text": "Die Pflichten gelten nicht für Informationen, die öffentlich bekannt sind oder werden, die rechtmäßig von "
                 "Dritten erlangt wurden oder deren Offenlegung gesetzlich oder behördlich verlangt wird."},
        {"titel": "§ 4 Sperrfrist für Inhalte",
         "text": "Inhalte zu noch nicht veröffentlichten Produkten oder Kampagnen werden nicht vor dem vereinbarten "
                 "Veröffentlichungstermin gezeigt."},
        {"titel": "§ 5 Dauer",
         "text": "Die Vereinbarung gilt ab Unterzeichnung und bis zwei Jahre nach Ende der Zusammenarbeit."},
        {"titel": "§ 6 Schlussbestimmungen",
         "text": "Es gilt deutsches Recht. Änderungen bedürfen der Textform. {Ort}, {Datum}"},
    ]},
    # EINWILLIGUNG_AUFNAHMEN E1 (CEO 2026-10-08): Grundlage Web-Recherche (KUG, DSGVO Art. 6/7, Minderjaehrige, Tablet-
    # Unterschrift als Nachweis) -- Entwurf Claude Code, anwaltliche Pruefung vor dem ersten Einsatz. Die Zwecke kreuzt die
    # Person im Formular an (`core/einwilligungen.ZWECKE`); Platzhalter fuellt LUNA aus Auftrag und Firmendaten.
    "einwilligung": {"titel": "Einwilligung in Bild-, Video- und Tonaufnahmen", "paragraphen": [
        {"titel": "§ 1 Gegenstand",
         "text": "Ich willige ein, dass {Auftragnehmer} im Rahmen des Projekts „{Projekt}“ für {Kunde} am {Datum} in {Ort} "
                 "Video-, Bild- und Tonaufnahmen von mir anfertigt."},
        {"titel": "§ 2 Zwecke und Veröffentlichung",
         "text": "Die Aufnahmen dürfen – bearbeitet und geschnitten – für die unten angekreuzten Zwecke verwendet und "
                 "veröffentlicht werden. Für andere Zwecke werde ich vorher erneut gefragt. Mir ist bekannt, dass Inhalte im "
                 "Internet weltweit abrufbar sind und von Dritten gespeichert oder geteilt werden können."},
        {"titel": "§ 3 Umfang und Bearbeitung",
         "text": "Die Einwilligung umfasst mein Bild und meine Stimme. Mein Name oder Profil wird nur genannt, wenn das unten "
                 "angekreuzt ist. Übliche Bearbeitungen (Schnitt, Kürzung, Farbe, Musik, Untertitel, Text-Einblendungen) sind "
                 "erlaubt. Aufnahmen werden nicht in herabwürdigendem Zusammenhang verwendet; mein Gesicht oder meine Stimme "
                 "werden nicht ohne gesonderte Zustimmung mit KI verändert oder nachgebildet."},
        {"titel": "§ 4 Dauer und Widerruf",
         "text": "Die Einwilligung gilt zeitlich unbefristet. Ich kann sie jederzeit ohne Angabe von Gründen mit Wirkung für "
                 "die Zukunft widerrufen, formlos an {Kontakt}. Danach werden keine neuen Inhalte mit mir veröffentlicht und "
                 "eigene Beiträge mit mir in angemessener Frist entfernt, soweit das möglich ist. Inhalte, die Dritte (z. B. der "
                 "Auftraggeber oder Nutzer der Plattformen) bereits gespeichert oder geteilt haben, lassen sich nicht immer "
                 "vollständig zurückholen. Die bis zum Widerruf erfolgte Nutzung bleibt rechtmäßig."},
        {"titel": "§ 5 Vergütung",
         "text": "Die Einwilligung erfolgt unentgeltlich, sofern unten keine Vergütung eingetragen ist."},
        {"titel": "§ 6 Freiwilligkeit",
         "text": "Die Einwilligung ist freiwillig. Wenn ich sie nicht erteile oder widerrufe, entstehen mir keine Nachteile – "
                 "bei Beschäftigten des Auftraggebers insbesondere keine im Arbeitsverhältnis."},
        {"titel": "§ 7 Minderjährige",
         "text": "Für Personen unter 16 Jahren unterschreiben die Erziehungsberechtigten; ab 14 Jahren unterschreibt die "
                 "minderjährige Person zusätzlich selbst. Bei gemeinsamem Sorgerecht bestätigt der unterschreibende Elternteil, "
                 "im Einverständnis des anderen zu handeln."},
        {"titel": "§ 8 Datenschutzhinweise",
         "text": "Verantwortlich ist {Auftragnehmer}, {Anschrift}, erreichbar unter {Kontakt}. Rechtsgrundlage ist diese "
                 "Einwilligung (Art. 6 Abs. 1 lit. a DSGVO, § 22 KUG). Verarbeitet werden Name, Kontaktdaten, Unterschrift und die "
                 "Aufnahmen. Die Aufnahmen gehen an den Auftraggeber und an die genutzten Plattformen (z. B. Meta, TikTok, "
                 "YouTube), die Daten auch außerhalb der EU verarbeiten können. Diese Erklärung wird als Nachweis aufbewahrt, "
                 "solange die Aufnahmen genutzt werden, und danach bis zum Ablauf gesetzlicher Fristen. Ich habe das Recht auf "
                 "Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung, Widerruf und Beschwerde bei einer "
                 "Datenschutz-Aufsichtsbehörde. Eine Kopie dieser Erklärung erhalte ich auf Wunsch."},
    ]},
}
