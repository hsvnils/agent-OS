"""Firmenakte: Dokumente und Mailverlauf je Firma (KUNDEN_FINANZEN Etappe 24, CEO 2026-09-30).

- **Dokumente hochladen** (z. B. Anwaltsschreiben, Vertrag) an einer Stammdaten-Firma (`K-`/`L-`/`P-`), optional mit Bezug
  (Rechnung/Auftrag/Angebot) -- unveraendert abgelegt mit Hash, Aufbewahrung als Geschaeftsbrief.
- **Mails**: vom CEO an LUNA weitergeleitete Mails, die kein Beleg sind, und Mails, in denen LUNA in CC/BCC steht, landen
  als `.eml` (Original) + lesbare PDF-Ansicht in der Akte der passenden Firma. Zuordnung ueber Adressen/Domains aus den
  Stammdaten (Rechnungs-Mail, Rechnungs-Absender, Ansprechpartner, Website). Ohne eindeutige Firma: „Mail zuordnen“.
  Der Text des CEO ueber einer Weiterleitung wird Notiz. LUNA liest und legt nur ab -- sie antwortet nie.

Ereignisse: `akte_dokument` (abgelegt), `akte_mail_offen` (wartet auf Zuordnung), `akte_mail_zugeordnet`.
"""
from __future__ import annotations

import email
import re
import uuid
from email import policy
from email.utils import getaddresses, parseaddr

from .buchhaltung import jetzt

ARTEN = {"schreiben": "Schreiben/Brief", "anwalt": "Anwaltsschreiben", "vertrag": "Vertrag", "mail": "Mail",
         "notiz": "Notiz/Protokoll", "sonstiges": "Sonstiges"}
MAX_BYTES = 15 * 1024 * 1024
FREEMAIL = {"gmail.com", "googlemail.com", "web.de", "gmx.de", "gmx.net", "icloud.com", "me.com", "mac.com", "outlook.com",
            "hotmail.com", "hotmail.de", "live.com", "live.de", "t-online.de", "yahoo.com", "yahoo.de", "aol.com", "freenet.de",
            "posteo.de", "proton.me", "protonmail.com", "mail.de"}
_BEZUG = re.compile(r"^(RE|AN|AB|RG|MA|ER|EB)-[A-Z0-9\-]{3,30}$")


def _domain(url_oder_mail: str) -> str:
    s = (url_oder_mail or "").strip().lower()
    if "@" in s:
        return s.rsplit("@", 1)[1]
    s = re.sub(r"^https?://", "", s).split("/")[0]
    return s[4:] if s.startswith("www.") else s


def firma_zu_adresse(firmen: list[dict], adresse: str) -> str:
    """Firma zu einer Mailadresse: exakte Adresse (Rechnungs-Mail, Absender, Ansprechpartner) > Domain (nicht Freemail)."""
    a = (adresse or "").strip().lower()
    if "@" not in a:
        return ""
    dom = _domain(a)
    for f in firmen:
        adressen = {x.strip().lower() for x in re.split(r"[,;\s]+", " ".join(
            [f.get("rechnungsmail") or "", f.get("rechnungs_absender") or ""]
            + [p.get("mail") or "" for p in f.get("ansprechpartner_liste") or []])) if "@" in x}
        if a in adressen:
            return f["nummer"]
    if dom in FREEMAIL:
        return ""
    for f in firmen:
        doms = {_domain(f.get("website") or "")} | {_domain(x) for x in re.split(r"[,;\s]+", " ".join(
            [f.get("rechnungsmail") or "", f.get("rechnungs_absender") or ""]
            + [p.get("mail") or "" for p in f.get("ansprechpartner_liste") or []])) if x.strip()}
        doms.discard("")
        if any(dom == d or dom.endswith("." + d) for d in doms):
            return f["nummer"]
    return ""


def _falte(eintraege: list[dict]) -> tuple[dict, dict]:
    """-> (dokumente {id: doc}, offene Mails {id: mail})."""
    docs, offen = {}, {}
    for e in eintraege:
        d, t = e["daten"], e["typ"]
        if t == "akte_dokument":
            docs[d["id"]] = dict(d) | {"ts": e["ts"], "von": e.get("von", "")}
        elif t == "akte_mail_offen":
            offen[d["id"]] = dict(d) | {"ts": e["ts"]}
        elif t == "akte_mail_zugeordnet" and d.get("id") in offen:
            m = offen.pop(d["id"])
            if d.get("firma"):
                docs[d["id"]] = m | {"firma": d["firma"], "ts": m["ts"]}
    return docs, offen


def bekannte_mail_ids(eintraege: list[dict]) -> set[str]:
    return {e["daten"].get("mail_id") for e in eintraege
            if e["typ"] in ("akte_dokument", "akte_mail_offen") and e["daten"].get("mail_id")}


class Firmenakte:
    def __init__(self, bh, kunden):
        self.bh, self.kunden = bh, kunden

    def akte(self, firma: str) -> list[dict]:
        f = self.kunden.firma(firma)
        if not f:
            raise KeyError(firma)
        docs, _ = _falte(self.bh.eintraege())
        return sorted((x for x in docs.values() if x["firma"] == f["nummer"]), key=lambda x: (x.get("datum") or "", x["ts"]),
                      reverse=True)

    def zu_bezug(self, bezug: str) -> list[dict]:
        docs, _ = _falte(self.bh.eintraege())
        return [x for x in docs.values() if x.get("bezug") == (bezug or "").upper()]

    def offene(self) -> list[dict]:
        return sorted(_falte(self.bh.eintraege())[1].values(), key=lambda x: x["ts"], reverse=True)

    def dokument(self, did: str) -> dict | None:
        return _falte(self.bh.eintraege())[0].get(did)

    def hochladen(self, firma: str, daten: bytes, name: str, *, titel: str = "", art: str = "sonstiges", datum: str = "",
                  bezug: str = "", notiz: str = "", von: str = "") -> dict:
        f = self.kunden.firma(firma)
        if not f:
            raise KeyError(firma)
        if not daten:
            raise ValueError("Leere Datei.")
        if len(daten) > MAX_BYTES:
            raise ValueError("Datei groesser als 15 MB.")
        if art not in ARTEN:
            raise ValueError("Unbekannte Dokumentart.")
        bezug = (bezug or "").strip().upper()
        if bezug and not _BEZUG.match(bezug):
            raise ValueError("Bezug bitte als Belegnummer (z. B. RG-11052026, RE-2026-0001, AB-2026-0001).")
        tag = (datum or "")[:10] or jetzt().date().isoformat()
        titel = (titel or "").strip()[:200] or name
        b = self.bh.beleg_ablegen(daten, name or "dokument", jahr=int(tag[:4]), art="geschaeftsbrief", bezug=f["nummer"],
                                  von=von)["daten"]
        did = "D-" + uuid.uuid4().hex[:8]
        self.bh.erfassen("akte_dokument", {"id": did, "firma": f["nummer"], "titel": titel, "art": art, "datum": tag,
                                           "bezug": bezug, "notiz": (notiz or "").strip()[:500], "quelle": "upload",
                                           "dateien": [{"pfad": b["pfad"], "sha256": b["sha256"], "name": name}]}, von=von)
        return {"id": did, "firma": f["nummer"]}

    # -- Mails -------------------------------------------------------------------------------------------------------

    def _firmen_mit_ansprechpartnern(self) -> list[dict]:
        """`firmen()` liefert die Ansprechpartner nicht mit -- fuer die Zuordnung ueber deren Mailadressen noetig."""
        return [self.kunden.firma(f["nummer"]) or f for f in self.kunden.firmen()]

    def mail_aufnehmen(self, roh: bytes, mid: str, *, eigene: list[str], weitergeleitet: bool, von: str = "LUNA-Mail",
                       bezug: str = "") -> dict:
        """Mail in die Akte (oder „zuordnen“). `eigene` = Adressen des CEO und von LUNA (zaehlen nie als Firma).
        Weitergeleitet: Firma aus dem Original-Absender, Text darueber = Notiz. Rueckgabe {id, firma|""}."""
        from .eingangsbelege import mail_pdf, mail_text, weiterleitung, zweck_aus_mail
        eigene = [a.lower() for a in eigene if a]
        m = email.message_from_bytes(roh, policy=policy.default)
        text = mail_text(roh)
        orig, rest, markiert = weiterleitung(roh, text)
        firmen = self._firmen_mit_ansprechpartnern()
        if weitergeleitet and markiert:
            kandidaten = [orig.get("von", "")]
            notiz = zweck_aus_mail(roh)
        else:
            kandidaten = [a for _, a in getaddresses([str(m.get(h, "")) for h in ("From", "To", "Cc", "Reply-To")])]
            notiz = ""
        treffer = []
        for a in kandidaten:
            a = (a or "").lower()
            if a and a not in eigene and not any(a.endswith("@" + _domain(x)) and _domain(x) not in FREEMAIL for x in eigene):
                nr = firma_zu_adresse(firmen, a)
                if nr and nr not in treffer:
                    treffer.append(nr)
        betreff = re.sub(r"^\s*(?:fwd?|wg|wtr|aw|re)\s*:\s*", "", orig.get("betreff") or str(m.get("Subject", "")),
                         flags=re.I).strip()[:200] or "(ohne Betreff)"
        forderung, bezug = bezug, ""
        if forderung:                                         # BF-49: Post zu eigener Rechnung -> Firma dieser Rechnung
            bezug, nr = self._beleg_firma(forderung)
            if nr:
                treffer = [nr]
        if len(treffer) != 1:                                 # Belegnummer im Betreff/Text -> Firma dieses Belegs
            bezug, nr = self._beleg_firma(f"{betreff}\n{rest[:3000]}")
            if nr:
                treffer = [nr]
        datum = jetzt().date().isoformat()
        try:
            from email.utils import parsedate_to_datetime
            datum = parsedate_to_datetime(str(m.get("Date"))).date().isoformat()
        except Exception:
            pass
        stamm = re.sub(r"[^\w.-]+", "_", betreff, flags=re.UNICODE).strip("_")[:50] or "Mail"
        dateien = []
        for inhalt, name in ((roh, f"Mail-{stamm}.eml"), (mail_pdf(orig, rest, parseaddr(str(m.get("From", "")))[1]
                                                                   if weitergeleitet else ""), f"Mail-{stamm}.pdf")):
            b = self.bh.beleg_ablegen(inhalt, name, jahr=int(datum[:4]), art="geschaeftsbrief", bezug=mid, von=von)["daten"]
            dateien.append({"pfad": b["pfad"], "sha256": b["sha256"], "name": name})
        did = "D-" + uuid.uuid4().hex[:8]
        daten = {"id": did, "titel": betreff, "art": "mail", "datum": datum, "bezug": bezug, "notiz": notiz, "quelle": "mail",
                 "mail_id": mid, "mail_von": orig.get("von") or parseaddr(str(m.get("From", "")))[1],
                 "dateien": list(reversed(dateien))}                      # PDF-Ansicht zuerst, .eml dahinter
        if len(treffer) == 1:
            self.bh.erfassen("akte_dokument", daten | {"firma": treffer[0]}, von=von)
            return {"id": did, "firma": treffer[0]}
        self.bh.erfassen("akte_mail_offen", daten | {"kandidaten": treffer}, von=von)
        return {"id": did, "firma": ""}

    def _beleg_firma(self, text: str) -> tuple[str, str]:
        """„Angebot AN-2026-0002“ -> (AN-2026-0002, Firma des Angebots); auch Auftrag, Rechnung (auch Altrechnung RG-...)."""
        from .angebote import AngebotStore
        from .beauftragung import AuftragBuch
        from .rechnungen import RechnungStore
        e = self.bh.eintraege()
        belege = {**{k: v["firma"] for k, v in AngebotStore._falte(e).items()},
                  **{k: v["firma"] for k, v in AuftragBuch._falte(e).items()},
                  **{k: v["firma"] for k, v in RechnungStore._falte(e)[1].items()}}
        for nr in re.findall(r"\b(?:AN|AB|RE|MA)-\d{4}-\d{4}\b|\bRG-\d{6,8}\b", text or "", flags=re.I):
            if nr.upper() in belege:
                return nr.upper(), belege[nr.upper()]
        return "", ""

    def zuordnen(self, did: str, firma: str, *, von: str = "") -> dict:
        f = self.kunden.firma(firma) if firma else None
        if firma and not f:
            raise KeyError(firma)
        if did not in _falte(self.bh.eintraege())[1]:
            raise ValueError("Diese Mail wartet nicht (mehr) auf eine Zuordnung.")
        self.bh.erfassen("akte_mail_zugeordnet", {"id": did, "firma": f["nummer"] if f else ""}, von=von)
        return {"id": did, "firma": f["nummer"] if f else ""}


_FORDERUNG = re.compile(r"(?i)offene forderung|mahnverfahren|mahnbescheid|zahlungsverzug|rechtsanw[aä]lt|anwaltskanzlei|"
                        r"inkasso|mandant(?:in|en)?\b")
_EIGENE_KOSTEN = re.compile(r"(?i)kostennote|verg[üu]tungs(?:berechnung|rechnung)|honorar(?:rechnung|note)")
_RECHTSFORM_W = {"gmbh", "mbh", "ug", "ag", "kg", "ohg", "co", "ek", "gbr", "haftungsbeschraenkt", "gastro", "und"}


def _stamm(name: str) -> str:
    """„Kiez Alm Gastro GmbH“ -> „kiezalm“ (erste zwei Woerter ohne Rechtsform, nur Buchstaben/Ziffern)."""
    w = [x for x in re.findall(r"[a-z0-9äöüß]+", (name or "").lower()) if x not in _RECHTSFORM_W]
    return "".join(w[:2])


def eigene_forderung(text: str, eintraege: list[dict]) -> str:
    """BF-49 (Etappe 28): Ist das Post zu einer EIGENEN Ausgangsrechnung (Anwalt, Mahnverfahren, Kunde)? -> Rechnungsnummer,
    sonst ''. Erkennt die volle Nummer (RG-11052026, RE-2026-0007), „Rechnung Nr. 11052026“ ohne Praefix sowie
    Forderungs-/Anwaltsvokabular zusammen mit dem Namen einer Firma, die eine offene eigene Rechnung hat. Eine Kosten-
    oder Honorarnote AN UNS bleibt ein Beleg."""
    from .rechnungen import RechnungStore
    t = text or ""
    if _EIGENE_KOSTEN.search(t):
        return ""
    rechnungen = {k: v for k, v in RechnungStore._falte(eintraege)[1].items() if v.get("art") != "storno"}
    for nr in re.findall(r"\b(?:RE-\d{4}-\d{4}|RG-\d{6,8})\b", t, flags=re.I):
        if nr.upper() in rechnungen:
            return nr.upper()
    ziffern = {re.sub(r"\D", "", k): k for k in rechnungen if k.upper().startswith("RG-")}
    for m in re.finditer(r"(?i)rechnung(?:s?-?nummer|s?-?nr\.?)?\s*(?:nr\.?|nummer)?\s*[:#]?\s*([A-Z]{0,2}-?\d{6,8})\b", t):
        if (k := ziffern.get(re.sub(r"\D", "", m.group(1)))):
            return k
    if _FORDERUNG.search(t):
        norm = re.sub(r"[^a-z0-9äöüß]", "", t.lower())
        namen: dict[str, str] = {}
        for e in eintraege:
            if e["typ"] == "firma_angelegt":
                namen[e["daten"]["nummer"]] = e["daten"].get("name", "")
        offen = [(k, v) for k, v in rechnungen.items() if v.get("status") == "offen"]
        for k, v in sorted(offen, key=lambda x: x[1].get("rechnungsdatum", "")):
            st = _stamm(namen.get(v.get("firma", ""), ""))
            if len(st) >= 5 and st in norm:
                return k
    return ""


def anhang_texte(roh: bytes) -> str:
    """Text aller PDF-/Bild-Anhaenge einer Mail (fuer die Zuordnung; OCR nur wenn noetig)."""
    from .eingangsbelege import anhaenge, auslesen
    teile = []
    for name, daten in anhaenge(roh):
        try:
            teile.append(auslesen(daten, name).get("text") or "")
        except Exception:
            continue
    return "\n".join(teile)


def mails_pruefen(akte: Firmenakte, google, *, ceo: list[str], luna: str, tage: int = 14, gesehen: set | None = None) -> list[str]:
    """LUNAs Postfach: Mails mit LUNA in CC/BCC oder vom CEO weitergeleitete Nicht-Beleg-Mails in die Akte.
    Beleg-Mails (schon im Kassenbuch) und bereits abgelegte Mails werden uebersprungen. Rueckgabe: neue Dokument-IDs."""
    if google is None or not google.verfuegbar() or not luna:
        return []
    ceo = [a.strip().lower() for a in ceo if "@" in a]
    luna = luna.strip().lower()
    from .eingangsbelege import EingangStore, absender_echt, mail_ist_beleg, mail_text, weiterleitung
    eintraege = akte.bh.eintraege()
    bekannt = bekannte_mail_ids(eintraege) | {x.get("mail_id") for x in EingangStore._falte(eintraege).values()}
    gesehen = gesehen if gesehen is not None else set()
    r = google.mail_suchen(f"in:anywhere -in:trash -in:spam newer_than:{tage}d {{cc:{luna} bcc:{luna} from:({' OR '.join(ceo)})}}",
                           max_results=50)
    neu = []
    for m in r.get("mails", []) if r.get("ok") else []:
        mid = m.get("id", "")
        if not mid or mid in bekannt or mid in gesehen:
            continue
        gesehen.add(mid)
        roh = google.mail_roh(mid)
        if not roh.get("ok"):
            gesehen.discard(mid)
            continue
        roh = roh["roh"]
        kopf = email.message_from_bytes(roh, policy=policy.default)
        von_ceo = parseaddr(str(kopf.get("From", "")))[1].lower() in ceo
        cc = luna in " ".join(str(kopf.get(h, "")) for h in ("Cc", "Bcc", "Delivered-To", "X-Original-To")).lower()
        orig, rest, markiert = weiterleitung(roh, mail_text(roh))
        if von_ceo and markiert:
            if not absender_echt(roh, ceo):
                continue                                         # gefaelscht
            fo = eigene_forderung(f"{orig.get('betreff', '')}\n{rest}\n{anhang_texte(roh)}", eintraege)   # BF-49
            if not fo and mail_ist_beleg(orig.get("betreff", ""), rest):
                continue                                         # Beleg -> Beleg-Abruf ist zustaendig
            neu.append(akte.mail_aufnehmen(roh, mid, eigene=ceo + [luna], weitergeleitet=True, bezug=fo)["id"])
        elif cc or von_ceo:
            neu.append(akte.mail_aufnehmen(roh, mid, eigene=ceo + [luna], weitergeleitet=False)["id"])
    return neu
