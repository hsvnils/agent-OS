"""Self-Checks Werkzeugauswahl (WERKZEUGAUSWAHL_ROADMAP.md, Etappe 1) -- offline, ohne LLM.

Der TESTKATALOG ist der Massstab: typische CEO-Nachrichten und das Werkzeug, das LUNA dafuer braucht. Gate: das
erwartete Werkzeug ist in >= 95 % der Faelle in der Auswahl, und die Auswahl kostet im Mittel <= 5.000 Token
(System-Prompt + Werkzeuge). Neue typische Anfragen hier ergaenzen, statt Stichwoerter blind zu erweitern.
"""
import collections
import unittest

from orchestrator.core import werkzeugauswahl as w
from orchestrator.core.hoa_conversation import TEXT_SYSTEM_PROMPT
from orchestrator.core.hoa_tools import tool_specs

# (CEO-Nachricht, erwartete Werkzeuge) -- Umlaute, Umgangssprache und Grenzfaelle bewusst dabei.
TESTKATALOG = [
    ("Hallo LUNA", []),
    ("Guten Morgen, was steht heute an?", ["lagebild"]),
    ("Welche Anträge sind gerade offen?", ["antraege_zeigen"]),
    ("Zeig mir den Antrag mit der Endung 3f2a", ["antrag_details"]),
    ("Gib den Antrag 3f2a frei", ["antrag_freigeben"]),
    ("Lehn den Antrag zur Logging-Umstellung ab, zu teuer", ["antrag_ablehnen"]),
    ("Mach den Antrag günstiger, am besten kostenlos", ["antrag_revidieren"]),
    ("Setz den freigegebenen Antrag bitte um", ["antrag_umsetzen"]),
    ("Merge den erledigten Antrag nach main", ["antrag_mergen"]),
    ("Schieb den Branch zu GitHub, ich will den Pull Request sehen", ["antrag_pushen"]),
    ("Stell einen Antrag für ein besseres Backup", ["antrag_stellen"]),
    ("Welche Tickets hat der CTO schon erledigt?", ["abteilung_tickets"]),
    ("Was ist alles noch offen bei uns?", ["offene_tickets"]),
    ("Lass die IT einen Verbesserungsvorschlag machen", ["selbstentwicklung"]),
    ("Wie läuft mein Depot?", ["paper_konto"]),
    ("Kauf für 30 Dollar Bitcoin", ["paper_order_freigabe"]),
    ("Verkauf meine Apple-Position", ["paper_order_freigabe"]),
    ("Welche Investment-Vorschläge gibt es?", ["investment_vorschlaege"]),
    ("Wie gut waren die Prognosen bisher?", ["investment_scorecard"]),
    ("Gibt es neue Insider-Käufe?", ["insider_signale_zeigen"]),
    ("Nimm Nvidia auf die Watchlist", ["watchlist_hinzufuegen"]),
    ("Mach einen Markt-Screen", ["investment_screen"]),
    ("Zeig mir das Collab-CRM", ["crm_zeigen"]),
    ("Gibt es neue Kooperationsanfragen per DM?", ["crm_dm_abrufen"]),
    ("Was hat die Firma Kärcher uns geschrieben?", ["crm_konversation"]),
    ("Setz Kärcher im CRM auf Angebot", ["crm_status_setzen"]),
    ("Wie entwickeln sich unsere Instagram-Follower?", ["social_media_analyzer"]),
    ("Welche Collabs laufen gerade laut Radar?", ["ig_analyse"]),
    ("Füttere die Content-Pipeline mit neuen Trends", ["content_feed_lauf"]),
    ("Hab ich neue Mails?", ["posteingang"]),
    ("Such die Mail von der Sparkasse", ["mail_suchen"]),
    ("Schreib Thomas eine Mail, dass ich später komme", ["mail_entwurf"]),
    ("Schick die Mail jetzt ab", ["mail_senden"]),
    ("Markier die Mail als gelesen", ["mail_markieren"]),
    ("Was steht diese Woche im Kalender?", ["kalender_agenda"]),
    ("Leg mir morgen um 10 Uhr einen Termin mit dem Steuerberater an", ["termin_anlegen"]),
    ("Verschieb das Meeting am Freitag auf 15 Uhr", ["termin_aendern"]),
    ("Sag den Termin am Montag ab", ["termin_loeschen"]),
    ("Überschneiden sich Termine nächste Woche?", ["kalender_kollisionen"]),
    ("Gib mir das Morgen-Briefing", ["briefing_jetzt"]),
    ("Notier dir: Reifen wechseln", ["notiz_hinzufuegen"]),
    ("Such im Drive nach dem Businessplan", ["drive_suchen"]),
    ("Trag die Zahlen in die Tabelle ein", ["tabelle_schreiben"]),
    ("Zeichne mir ein Organigramm der Firma", ["visualisiere"]),
    ("Füge in meiner Mindmap einen Knoten Marketing hinzu", ["xmind_bearbeiten"]),
    ("Exportier den Wissensstand nach Obsidian", ["obsidian_export"]),
    ("Recherchier, welche lokalen LLMs gut Werkzeuge nutzen", ["recherche_beauftragen"]),
    ("Was ist aus meiner Recherche zu Mini-PCs geworden?", ["recherche_tickets_zeigen"]),
    ("Welche GitHub-Repos wachsen gerade schnell?", ["github_trends"]),
    ("Was gibt es Neues bei KI-Agenten?", ["watch_digest"]),
    ("Starte die Innovations-Pipeline", ["innovation_scouting"]),
    ("Was weiß der CISO-Fachbereich aktuell?", ["wissensstand"]),
    ("Öffne Spotify", ["rechner_aktion"]),
    ("Was ist gerade auf meinem Bildschirm offen?", ["bildschirm_sehen"]),
    ("Läuft alles?", ["systemcheck"]),
    ("Mach einen Sicherheits-Audit", ["sicherheits_audit"]),
    ("Stopp alle autonomen Abläufe", ["autonomie_pausieren"]),
    ("Was habt ihr heute gemacht?", ["aktivitaet_protokoll"]),
    ("Wie viel Geld haben wir diesen Monat für KI ausgegeben?", ["kosten_statistik"]),
    ("Setz das Monatsbudget auf 150 Euro", ["set_budget"]),
    ("Wo können wir Kosten sparen?", ["kosten_optimierung"]),
    ("Wie haben wir das letzte Mal das Backup-Problem gelöst?", ["erfahrung_abrufen"]),
    ("Merk dir, dass Thomas unser Steuerberater ist", ["brain_merken"]),
    ("Frag den Berater, ob sich ein zweiter Kanal lohnt", ["delegate"]),
]

GATE_TREFFER = 0.95
GATE_TOKEN = 5000


def _ergebnis():
    specs = tool_specs()
    system = int(len(TEXT_SYSTEM_PROMPT) / 3.5)
    zeilen = []
    for nachricht, erwartet in TESTKATALOG:
        namen, gruppen = w.auswahl(nachricht)
        token = system + w.token_schaetzung(w.filtere(specs, namen))
        zeilen.append((nachricht, erwartet, all(e in namen for e in erwartet), token, sorted(gruppen)))
    return zeilen


class TestWerkzeugauswahl(unittest.TestCase):
    def test_1_jedes_werkzeug_genau_einmal_zugeordnet(self):
        namen = {t["name"] for t in tool_specs()}
        zugeordnet = [x for d in w.GRUPPEN.values() for x in d["werkzeuge"]] + w.KERN
        doppelt = [k for k, v in collections.Counter(zugeordnet).items() if v > 1]
        self.assertEqual(doppelt, [], "Werkzeug in mehreren Gruppen")
        self.assertEqual(sorted(namen - set(zugeordnet)), [], "neues Werkzeug ohne Gruppe -> in GRUPPEN eintragen")
        self.assertEqual(sorted(set(zugeordnet) - namen), [], "Gruppe nennt ein Werkzeug, das es nicht mehr gibt")

    def test_2_katalog_hat_mindestens_50_eintraege_und_nur_echte_werkzeuge(self):
        self.assertGreaterEqual(len(TESTKATALOG), 50)
        namen = {t["name"] for t in tool_specs()}
        for _, erwartet in TESTKATALOG:
            self.assertTrue(set(erwartet) <= namen, erwartet)

    def test_3_gate_trefferquote_und_groesse(self):
        zeilen = _ergebnis()
        treffer = sum(1 for z in zeilen if z[2]) / len(zeilen)
        mittel = sum(z[3] for z in zeilen) / len(zeilen)
        fehlend = [(z[0], z[1], z[4]) for z in zeilen if not z[2]]
        self.assertGreaterEqual(treffer, GATE_TREFFER, f"Trefferquote {treffer:.0%}, fehlend: {fehlend}")
        self.assertLessEqual(mittel, GATE_TOKEN, f"mittlere Groesse {mittel:.0f} Token")

    def test_4_umlaute_und_wortanfang(self):
        self.assertIn("finanzen", w.gruppen_fuer("Was hat das gekostet? Kosten bitte"))
        self.assertIn("rechner", w.gruppen_fuer("Öffne bitte XMind"))
        self.assertNotIn("crm_social", w.gruppen_fuer("Das ist wichtig"))       # 'ig' nur am Wortanfang
        self.assertEqual(w.gruppen_fuer("Hallo LUNA"), set())

    def test_5_bisherige_gruppen_bleiben_geladen(self):
        namen, gruppen = w.auswahl("Und der zweite?", {"antraege"})
        self.assertIn("antrag_freigeben", namen)
        self.assertEqual(gruppen, {"antraege"})

    def test_6_kern_immer_dabei(self):
        namen, _ = w.auswahl("Hallo")
        self.assertEqual(namen, w.KERN)


if __name__ == "__main__":
    for nachricht, erwartet, ok, token, gruppen in _ergebnis():
        print(f"{'OK ' if ok else 'FEHLT'} {token:5d} Tok  {','.join(gruppen) or '-':32s} {nachricht}")
    unittest.main()
