"""KUNDEN_CHECKLISTE C1: Fragenkatalog als PDF (A4 hochkant) und Word, nur Kopf (Logo + blau-roter Balken) wie die
Konzept-Vorlage. Aufruf: python scripts/kunden_checkliste_dokument.py <logo.jpg> vorlagen
(Logo = `buchhaltung/logo.jpg` von der NAS; Ergebnis in `vorlagen/`, nicht im Git)."""
import sys
import zipfile
from html import escape
from pathlib import Path

from fpdf import FPDF

BLAU, ROT, GRAU = (0, 64, 135), (204, 0, 0), (110, 110, 110)
LOGO, ZIEL = Path(sys.argv[1]), Path(sys.argv[2])
FONT = Path("/usr/share/fonts/truetype/dejavu")
LOGO_B = 50.0
LOGO_H = LOGO_B * 221 / 560
TITEL = "Kunden-Checkliste – Content-Konzept & Skripte"
EINLEITUNG = ("Diese Fragen klären wir mit euch, bevor wir Konzept und Skripte schreiben. Mit ★ markierte Blöcke brauchen "
              "wir auf jeden Fall – der Rest hilft, Content zu machen, der wirklich nach euch klingt.")
KOPFFELDER = ["Kunde", "Gesprächspartner", "Datum", "Projekt / Kampagne"]

BLOECKE = [
    ("A", "Unternehmen & Angebot", False, [
        "Was macht ihr – in einem Satz?",
        "Welches Produkt oder Angebot steht im Mittelpunkt?",
        "Was unterscheidet euch von anderen (warum zu euch und nicht zur Konkurrenz)?",
        "Gibt es Aktionen, Termine oder Saisons, die wir treffen müssen?"]),
    ("B", "Ziel", True, [
        "Was soll der Content erreichen (Bekanntheit, Besucher, Anfragen, Verkauf, Bewerber)?",
        "Woran messen wir Erfolg (Reichweite, Klicks, Reservierungen, Anfragen)?",
        "Gibt es ein konkretes Ziel bis zu einem bestimmten Datum?"]),
    ("C", "Zielgruppe", True, [
        "Wen wollt ihr erreichen (Alter, Ort, Interessen)?",
        "Wer sind heute eure besten Kunden?",
        "Was ist deren größtes Problem oder größter Wunsch?"]),
    ("D", "Kernbotschaft & Ton", True, [
        "Was soll man nach dem Video über euch denken?",
        "Wie sprecht ihr eure Kunden an (du/Sie, locker/seriös, Humor ja/nein)?",
        "Gibt es Wörter oder Themen, die tabu sind?"]),
    ("E", "Marke & Pflichtangaben", False, [
        "Logo, Farben, Schrift, Claim – was müssen wir verwenden?",
        "Pflichtangaben (z. B. Werbekennzeichnung, Preise, Allergene, Gewinnspielbedingungen)?",
        "Marken oder Partner, die genannt werden müssen – oder nicht genannt werden dürfen?"]),
    ("F", "Inhalte & Formate", False, [
        "Auf welchen Plattformen (Instagram, Facebook, TikTok, LinkedIn)?",
        "Welche Formate (Reel, Story, Karussell, Foto)?",
        "Wie viele Postings, in welchem Zeitraum?",
        "Beispiele, die euch gefallen – und welche gar nicht?",
        "Gibt es vorhandenes Material (Fotos, Videos, Texte)?"]),
    ("G", "Personen & Rechte", False, [
        "Wer darf oder soll vor die Kamera?",
        "Liegen Einwilligungen der Personen vor (sonst holen wir sie ein)?",
        "Sind Gäste oder Mitarbeitende im Hintergrund in Ordnung?",
        "Musik: eigene Rechte oder Musik der Plattform?"]),
    ("H", "Dreh & Organisation", False, [
        "Drehorte und gute Zeiten (Öffnungszeiten, ruhige Phasen)?",
        "Ansprechpartner vor Ort (Name, Telefon)?",
        "Welche Produkte oder Requisiten müssen bereitstehen?",
        "Parken, Strom, Zugang – gibt es etwas zu beachten?"]),
    ("I", "Freigabe & Zusammenarbeit", True, [
        "Wer gibt Skripte und Videos frei (Name, Kontakt)?",
        "Wie schnell kommt eine Freigabe (Frist)?",
        "Über welchen Kanal (Mail, WhatsApp, Link zum Kundenordner)?",
        "Wer postet – wir oder ihr? Auf welchem Konto?"]),
    ("J", "Call to Action", True, [
        "Was soll der Zuschauer am Ende tun (folgen, reservieren, Link klicken, anrufen, vorbeikommen)?",
        "Gibt es einen Link, Rabattcode oder eine Aktion?"]),
]


# -- PDF ---------------------------------------------------------------------------------------------------------------
class PDF(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", size=7)
        self.set_text_color(*GRAU)
        self.cell(0, 4, f"Seite {self.page_no()}/{{nb}}", align="R")


p = PDF(format="A4", orientation="P")
p.add_font("DejaVu", "", str(FONT / "DejaVuSans.ttf"))
p.add_font("DejaVu", "B", str(FONT / "DejaVuSans-Bold.ttf"))
p.set_title(TITEL); p.set_creator("LUNA-OS")
p.set_margins(18, 14, 18); p.set_auto_page_break(True, margin=18)
p.alias_nb_pages()
p.add_page()
B = p.w - 36
p.image(str(LOGO), x=(p.w - LOGO_B) / 2, y=14, w=LOGO_B)
y = 14 + LOGO_H + 3
p.set_fill_color(*BLAU); p.rect(18, y, B / 2, 1.6, style="F")
p.set_fill_color(*ROT); p.rect(18 + B / 2, y, B / 2, 1.6, style="F")
p.set_y(y + 7)
p.set_font("DejaVu", "B", 15); p.set_text_color(0, 0, 0)
p.multi_cell(0, 7, TITEL)
p.ln(1)
p.set_font("DejaVu", size=9); p.set_text_color(*GRAU)
p.multi_cell(0, 4.6, EINLEITUNG)
p.ln(3)
p.set_text_color(0, 0, 0)
for i in range(0, len(KOPFFELDER), 2):                        # zwei Felder je Zeile
    yz = p.get_y()
    for j, feld in enumerate(KOPFFELDER[i:i + 2]):
        x = 18 + j * (B / 2 + 2)
        p.set_xy(x, yz); p.set_font("DejaVu", size=8); p.set_text_color(*GRAU)
        p.cell(B / 2 - 2, 4, feld)
        p.set_draw_color(160, 160, 160)
        p.line(x, yz + 11, x + B / 2 - 4, yz + 11)
    p.set_y(yz + 14)
p.ln(2)


def zeilen(n: int):
    p.set_draw_color(200, 200, 200)
    for _ in range(n):
        yy = p.get_y() + 6.5
        p.line(24, yy, 18 + B, yy)
        p.set_y(yy)


for buchstabe, titel, pflicht, fragen in BLOECKE:
    if p.get_y() > p.h - 60:                                  # Block nicht mit nur einer Frage unten anfangen
        p.add_page()
    p.ln(3)
    p.set_fill_color(*BLAU); p.rect(18, p.get_y() + 0.8, 1.4, 5.2, style="F")
    p.set_x(22)
    p.set_font("DejaVu", "B", 11); p.set_text_color(*BLAU)
    p.cell(0, 7, f"{buchstabe}. {titel}" + ("   ★ Pflicht" if pflicht else ""), new_x="LMARGIN", new_y="NEXT")
    p.set_text_color(0, 0, 0)
    for frage in fragen:
        if p.get_y() > p.h - 36:
            p.add_page()
        p.set_font("DejaVu", size=9.5)
        yq = p.get_y() + 1.5
        p.set_draw_color(*BLAU)
        p.rect(18.5, yq + 0.6, 3.2, 3.2)                      # Haekchen-Kasten
        p.set_xy(24, yq)
        p.multi_cell(B - 6, 4.6, frage)
        zeilen(2)
        p.ln(1)

p.ln(4)
if p.get_y() > p.h - 40:
    p.add_page()
p.set_font("DejaVu", "B", 11); p.set_text_color(*BLAU)
p.cell(0, 7, "Notizen", new_x="LMARGIN", new_y="NEXT")
p.set_text_color(0, 0, 0)
zeilen(5)
(ZIEL / "Kunden-Checkliste.pdf").write_bytes(bytes(p.output()))

# -- Word (ohne Zusatzbibliothek, gleicher Aufbau wie die Konzept-Vorlage) ---------------------------------------------
TW = lambda mm: round(mm * 56.6929)
EMU = lambda mm: round(mm * 36000)
breite = TW(210 - 36)
halb = breite // 2
CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="jpg" ContentType="image/jpeg"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""
RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""
CORE = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>{escape(TITEL)}</dc:title></cp:coreProperties>"""
DOCRELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rIdLogo" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/logo.jpg"/>
</Relationships>"""
STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial" w:eastAsia="Arial"/><w:sz w:val="20"/><w:szCs w:val="20"/><w:lang w:val="de-DE"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="60" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Standard"><w:name w:val="Normal"/><w:qFormat/></w:style>
<w:style w:type="paragraph" w:styleId="berschrift1"><w:name w:val="heading 1"/><w:basedOn w:val="Standard"/><w:next w:val="Standard"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="160" w:after="80"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="berschrift2"><w:name w:val="heading 2"/><w:basedOn w:val="Standard"/><w:next w:val="Standard"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="60"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:color w:val="004087"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>
<w:style w:type="table" w:default="1" w:styleId="NormaleTabelle"><w:name w:val="Normal Table"/><w:tblPr><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="0" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>
</w:styles>"""
cx, cy = EMU(LOGO_B), EMU(LOGO_H)
zelle = lambda w, farbe: (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="{farbe}"/></w:tcPr>'
                          '<w:p><w:pPr><w:spacing w:after="0" w:line="20" w:lineRule="exact"/></w:pPr></w:p></w:tc>')


def absatz(text: str, *, stil: str = "", grau: bool = False, fett: bool = False, keep: bool = False) -> str:
    ppr = (f'<w:pStyle w:val="{stil}"/>' if stil else "") + ("<w:keepNext/>" if keep else "")
    rpr = ("<w:b/>" if fett else "") + ('<w:color w:val="6E6E6E"/><w:sz w:val="18"/>' if grau else "")
    return f'<w:p><w:pPr>{ppr}</w:pPr><w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def linie(einzug_mm: float = 6) -> str:                      # Antwortzeile: leerer Absatz mit Linie unten
    return (f'<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="4" w:space="1" w:color="C8C8C8"/></w:pBdr>'
            f'<w:spacing w:before="160" w:after="0"/><w:ind w:left="{TW(einzug_mm)}"/></w:pPr></w:p>')


teile = [f"""<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:after="{TW(3)}"/></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">
<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="1" name="Logo"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>
<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="1" name="logo.jpg"/><pic:cNvPicPr/></pic:nvPicPr>
<pic:blipFill><a:blip r:embed="rIdLogo"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>
</wp:inline></w:drawing></w:r></w:p>
<w:tbl><w:tblPr><w:tblW w:w="{breite}" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders></w:tblPr>
<w:tblGrid><w:gridCol w:w="{halb}"/><w:gridCol w:w="{breite - halb}"/></w:tblGrid>
<w:tr><w:trPr><w:trHeight w:val="{TW(1.6)}" w:hRule="exact"/></w:trPr>{zelle(halb, "004087")}{zelle(breite - halb, "CC0000")}</w:tr></w:tbl>""",
         absatz(TITEL, stil="berschrift1"), absatz(EINLEITUNG, grau=True)]
for feld in KOPFFELDER:
    teile += [absatz(feld, grau=True, keep=True), linie(0)]
for buchstabe, titel, pflicht, fragen in BLOECKE:
    teile.append(absatz(f"{buchstabe}. {titel}" + ("   ★ Pflicht" if pflicht else ""), stil="berschrift2"))
    for frage in fragen:
        teile += [absatz(f"☐  {frage}", keep=True), linie(), linie()]
teile.append(absatz("Notizen", stil="berschrift2"))
teile += [linie(0) for _ in range(5)]
DOC = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body>
{"".join(teile)}
<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="{TW(14)}" w:right="{TW(18)}" w:bottom="{TW(18)}" w:left="{TW(18)}" w:header="709" w:footer="709" w:gutter="0"/></w:sectPr>
</w:body></w:document>"""
with zipfile.ZipFile(ZIEL / "Kunden-Checkliste.docx", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", CT); z.writestr("_rels/.rels", RELS); z.writestr("docProps/core.xml", CORE)
    z.writestr("word/document.xml", DOC); z.writestr("word/_rels/document.xml.rels", DOCRELS)
    z.writestr("word/styles.xml", STYLES); z.write(LOGO, "word/media/logo.jpg")
print("ok", p.pages_count, "Seiten")
