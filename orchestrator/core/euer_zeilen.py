"""Amtliche Zeilen der Anlage EUeR je Formularjahr (Eingabehilfe fuer ELSTER, KUNDEN_FINANZEN Etappe 9).

Die Zeilennummern aendern sich von Jahr zu Jahr. Hier stehen nur **belegte** Werte (Quelle je Jahr im Kommentar);
fuer ein Jahr ohne eigene Tabelle wird die juengste bekannte verwendet und das in der Oberflaeche deutlich gesagt.
Neues Formularjahr: Tabelle aus der amtlichen Anleitung ergaenzen (Register-Eintrag + Changelog).
"""
from __future__ import annotations

# Quellen (Formular + Anleitung, Zeilen am Formulartext und an den Zeilenverweisen der Anleitung geprueft, 2026-09-28):
# - 2025: BMF-Schreiben 29.08.2025, IV C 6 - S 2142/00023/010/001 (bundesfinanzministerium.de, 2025-08-29-anlage-EUER-2025.pdf)
# - 2026: BMF-Schreiben 01.09.2026, IV C 6 - S 2142/00024/010/001 (2026-09-01-anlage-EUER-2026.pdf) -- ab Zeile 27 neue
#   Zeile „Rücklage Tierbewertung“ (Land-/Forstwirte), dadurch verschieben sich alle folgenden Zeilen.
# - 2024: gleiche Zeilen wie 2025 (Formulartext verglichen), Wortlaut Zeile 12 ohne Zusatz.
# Summen und Gewinn berechnet ELSTER selbst -> bewusst ohne Zeilennummer (Gewinnzeile in der Recherche nicht eindeutig).
# Kennzahl (Kz) = ELSTER-Feldnummer, stabiler als die Zeile.
_T = {
    "umsatz": ("Betriebseinnahmen als umsatzsteuerlicher Kleinunternehmer (nach § 19 Abs. 1 UStG)", "111"),
    "wareneinkauf": ("Waren, Rohstoffe und Hilfsstoffe einschließlich der Nebenkosten", "100"),
    "fremdleistungen": ("Bezogene Fremdleistungen", "110"),
    "anlage": ("AfA auf bewegliche Wirtschaftsgüter (Übertrag aus der Anlage AVEÜR)", "130"),
    "gwg": ("Aufwendungen für geringwertige Wirtschaftsgüter nach § 6 Abs. 2 EStG", "132"),
    "telekommunikation": ("Aufwendungen für Telekommunikation (z. B. Telefon, Internet)", "280"),
    "reise": ("Übernachtungs- und Reisenebenkosten bei Geschäftsreisen des Steuerpflichtigen", "221"),
    "fortbildung": ("Fortbildungskosten (ohne Reisekosten)", "281"),
    "gebuehren": ("Beiträge, Gebühren, Abgaben und Versicherungen (ohne solche für Gebäude und Kfz)", "223"),
    "software": ("Laufende EDV-Kosten (z. B. Beratung, Wartung, Reparatur)", "228"),
    "buero": ("Arbeitsmittel (z. B. Bürobedarf, Porto, Fachliteratur)", "229"),
    "werbung": ("Werbekosten (z. B. Inserate, Werbespots, Plakate)", "224"),
    "sonstiges": ("Übrige unbeschränkt abziehbare Betriebsausgaben", "183"),
    "bewirtung": ("Bewirtungsaufwendungen, Spalte „abziehbar“ (70 %)", "175"),
    "bewirtung_nicht_abziehbar": ("Bewirtungsaufwendungen, Spalte „nicht abziehbar“ (30 %)", "165"),
    "fahrzeug": ("Sonstige tatsächliche Fahrtkosten ohne AfA und Zinsen (betriebliches Kfz, Treibstoff, ÖPNV)", "146"),
    # Anleitung Zeile 12/13 (2025 und 2026 wortgleich): Kleinunternehmer tragen ALLE Betriebseinnahmen in Zeile 12 ein,
    # nicht steuerbare (z. B. Verzugszinsen, Mahnkosten = Schadensersatz, UStAE 1.3 Abs. 6) zusaetzlich nachrichtlich in 13
    "nebenforderung": ("davon nicht steuerbare Umsätze (nachrichtlich): Verzugszinsen, Mahnkosten, Verzugspauschale", "119"),
}
_Z2025 = {"umsatz": "12", "nebenforderung": "13", "wareneinkauf": "27", "fremdleistungen": "29", "anlage": "33", "gwg": "36",
          "telekommunikation": "43", "reise": "44", "fortbildung": "45", "gebuehren": "49", "software": "50",
          "buero": "51", "werbung": "54", "sonstiges": "60", "bewirtung": "63", "bewirtung_nicht_abziehbar": "63",
          "fahrzeug": "70"}
_Z2026 = {"umsatz": "12", "nebenforderung": "13", "wareneinkauf": "29", "fremdleistungen": "30", "anlage": "34", "gwg": "37",
          "telekommunikation": "44", "reise": "45", "fortbildung": "46", "gebuehren": "50", "software": "51",
          "buero": "52", "werbung": "55", "sonstiges": "61", "bewirtung": "64", "bewirtung_nicht_abziehbar": "64",
          "fahrzeug": "71"}
ZEILEN: dict[int, dict[str, tuple[str, str, str]]] = {   # {jahr: {kategorie: (zeile, amtliche Bezeichnung, Kz)}}
    j: {k: (z[k], _T[k][0], _T[k][1]) for k in z} for j, z in ((2024, _Z2025), (2025, _Z2025), (2026, _Z2026))
}


def zeile(jahr: int, kategorie: str) -> dict:
    """-> {zeile, text, kz, formularjahr}; leer, wenn fuer die Kategorie keine belegte Zeile existiert."""
    fj = formularjahr(jahr)
    z, text, kz = (ZEILEN.get(fj) or {}).get(kategorie, ("", "", ""))
    return {"zeile": z, "text": text, "kz": kz, "formularjahr": fj}


def formularjahr(jahr: int) -> int | None:
    bekannt = sorted(j for j in ZEILEN if j <= jahr) or sorted(ZEILEN)
    return bekannt[-1] if bekannt else None


def zeilen_hinweis(jahr: int) -> str:
    fj = formularjahr(jahr)
    if fj is None:
        return "Zeilennummern der Anlage EÜR noch nicht hinterlegt -- Positionen nach Bezeichnung übertragen."
    if fj != jahr:
        return (f"Zeilennummern aus der Anlage EÜR {fj} -- für {jahr} vor der Eingabe mit dem aktuellen Formular "
                "abgleichen (die Nummern ändern sich jährlich).")
    return (f"Zeilen und Kennzahlen (Kz) laut Anlage EÜR {fj} (BMF-Vordruck). Summen und Gewinn berechnet ELSTER selbst; "
            "bei Abschreibungen zusätzlich die Anlage AVEÜR (Anlageverzeichnis) ausfüllen.")
