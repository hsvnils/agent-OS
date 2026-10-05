"""Konzept-Mappe je Vorgang (KONZEPT_MAPPE_ROADMAP K1-K3, CEO-Entscheidungen 2026-10-05).

Eine Mappe gehoert zum **Vorgang** -- der Kette aus Angebot, Auftrag, Rechnungen … Ihre Kennung ist der erste Beleg:
das Angebot (`AN-…`) oder, wenn der Auftrag direkt angelegt wurde, der Auftrag (`AB-…`). Alle Belege der Kette zeigen
**denselben Stand**; nichts wird kopiert. Inhalte: Briefing, Ideen (mit Moodboard-Bildern), Skripte je Leistung
(Angebotsposition bzw. ab dem Auftrag das Posting „Reel 1“, „Reel 2“ … -- gleiche Position/Nummer, das Skript wandert
mit), Shotlist (im Drehmodus abhakbar), Drehplan und Kunden-Freigabe. Jede Aenderung ist ein Ereignis `konzept_*` in
der Hash-Kette (Verlauf); Bilder liegen wie Lieferungen nur auf der NAS (`lieferungen/<Vorgang>/konzept/`).
"""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import date, timedelta
from pathlib import Path

from .buchhaltung import Buchhaltung, jetzt

VORGANG = re.compile(r"^(AN|AB)-\d{4}-\d{4}$")
BRIEFING = (("ziel", "Ziel", 500), ("zielgruppe", "Zielgruppe", 500), ("botschaft", "Kernbotschaft", 500),
            ("tonalitaet", "Tonalität", 300), ("dos", "Do's", 1000), ("donts", "Don'ts", 1000),
            ("pflicht", "Pflichtangaben", 500), ("freigabe_an", "Freigaben durch", 200), ("notizen", "Notizen", 2000))
IDEE_STATUS = ("idee", "ausgewaehlt", "verworfen")
SKRIPT = (("hook", "Hook (erste 3 Sek.)", 500), ("text", "Text / Voice-over", 4000), ("einblendungen", "Einblendungen", 1000),
          ("musik", "Musik", 300), ("cta", "Call to Action", 500), ("laenge", "Länge", 40))
SKRIPT_STATUS = ("entwurf", "fertig", "freigegeben")
SZENE = (("titel", "Szene", 160), ("einstellung", "Einstellung", 300), ("ort", "Ort", 200), ("requisite", "Personen/Requisite", 300),
         ("dauer", "Dauer", 40), ("notiz", "Notiz", 500))
DREH = (("datum", "Datum", 10), ("zeit", "Uhrzeit", 20), ("ort", "Ort", 300), ("ansprechpartner", "Ansprechpartner vor Ort", 200),
        ("telefon", "Telefon", 60), ("mitbringen", "Mitbringen", 1000))
FREIGABE = ("entwurf", "beim_kunden", "freigegeben", "aenderung")
FREIGABE_TEXT = {"entwurf": "Entwurf", "beim_kunden": "beim Kunden", "freigegeben": "freigegeben", "aenderung": "Änderungswunsch"}
BILD_ENDUNGEN = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def _t(v, n) -> str:
    return str(v if v is not None else "").strip()[:n]


def vorgang_von(eintraege: list[dict], nummer: str) -> str:
    """Beleg -> Vorgang (erstes Angebot der Kette, sonst der direkt angelegte Auftrag)."""
    from .beauftragung import AuftragBuch
    from .rechnungen import RechnungStore
    n = (nummer or "").strip()
    n = n if n.startswith("E-") else n.upper()
    auftraege = AuftragBuch._falte(eintraege)
    if n.startswith("AN-"):
        return n
    if n.startswith("AB-"):
        a = auftraege.get(n)
        return (a or {}).get("angebot") or n
    entwuerfe, rechnungen = RechnungStore._falte(eintraege)
    r = rechnungen.get(n) or entwuerfe.get(n) or {}
    if r.get("art") == "storno":
        r = rechnungen.get(r.get("bezug")) or r
    if r.get("auftrag"):
        return vorgang_von(eintraege, r["auftrag"])
    if r.get("angebot"):
        return r["angebot"]
    raise KeyError(nummer)


class KonzeptStore:
    def __init__(self, bh: Buchhaltung, ordner: Path | str | None = None):
        self.bh = bh
        self.ordner = Path(ordner) if ordner else bh.dir.parent / "lieferungen"

    # -- Lesen ------------------------------------------------------------------------------------------------------
    @staticmethod
    def _leer(v: str) -> dict:
        return {"vorgang": v, "briefing": {}, "ideen": {}, "skripte": {}, "szenen": {}, "dreh": {}, "bilder": [],
                "freigabe": {"status": "entwurf", "versionen": []}, "verlauf": [], "angelegt": ""}

    @classmethod
    def _falte(cls, eintraege: list[dict]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in eintraege:
            t, d = e["typ"], e["daten"]
            if not str(t).startswith("konzept_"):
                continue
            m = out.setdefault(d["vorgang"], cls._leer(d["vorgang"]))
            m["angelegt"] = m["angelegt"] or e["ts"]
            m["geaendert"] = e["ts"]
            m["verlauf"].append({"ts": e["ts"], "von": e.get("von", ""), "typ": t, "was": d.get("was", "")})
            if t == "konzept_briefing":
                m["briefing"].update(d["felder"])
            elif t == "konzept_idee":
                m["ideen"][d["id"]] = m["ideen"].get(d["id"], {"id": d["id"], "angelegt": e["ts"]}) | d["felder"]
            elif t == "konzept_skript":
                m["skripte"][d["id"]] = m["skripte"].get(d["id"], {"id": d["id"], "angelegt": e["ts"]}) | d["felder"]
            elif t == "konzept_szene":
                m["szenen"][d["id"]] = m["szenen"].get(d["id"], {"id": d["id"], "angelegt": e["ts"], "erledigt": ""}) | d["felder"]
            elif t == "konzept_szene_erledigt" and d["id"] in m["szenen"]:
                m["szenen"][d["id"]]["erledigt"] = e["ts"] if d.get("erledigt") else ""
            elif t == "konzept_szene_entfernt":
                m["szenen"].pop(d["id"], None)
            elif t == "konzept_dreh":
                m["dreh"].update(d["felder"])
            elif t == "konzept_bild":
                m["bilder"].append({k: d.get(k) for k in ("pfad", "name", "sha256", "idee")} | {"ts": e["ts"]})
            elif t == "konzept_freigabe":
                f = m["freigabe"]
                f["status"] = d["status"]
                f[d["status"] + "_am"] = d.get("datum") or e["ts"][:10]
                if d.get("notiz"):
                    f["notiz"] = d["notiz"]
                if d.get("akte_id"):
                    f["versionen"].append({k: d.get(k) for k in ("akte_id", "an", "version", "sha256")} | {"ts": e["ts"]})
        for m in out.values():
            m["szenen_liste"] = sorted(m["szenen"].values(), key=lambda s: (int(s.get("reihe") or 0), s["angelegt"]))
        return out

    def mappe(self, vorgang: str, eintraege: list[dict] | None = None) -> dict:
        e = self.bh.eintraege() if eintraege is None else eintraege
        v = self._pruefe_vorgang(vorgang, e)
        return self._falte(e).get(v) or self._leer(v) | {"szenen_liste": []}

    def _pruefe_vorgang(self, vorgang: str, eintraege: list[dict]) -> str:
        from .angebote import AngebotStore
        from .beauftragung import AuftragBuch
        v = (vorgang or "").strip().upper()
        if not VORGANG.match(v):
            raise KeyError(vorgang)
        if v not in (AngebotStore._falte(eintraege) if v.startswith("AN-") else AuftragBuch._falte(eintraege)):
            raise KeyError(vorgang)
        return v

    def kontext(self, vorgang: str, eintraege: list[dict] | None = None) -> dict:
        """Leistungen fuer die Skripte: Angebotspositionen bzw. Postings des Auftrags (gleiche Position/Nummer)."""
        from .angebote import AngebotStore
        from .beauftragung import AuftragBuch
        from .postings import postings_aus
        e = self.bh.eintraege() if eintraege is None else eintraege
        v = self._pruefe_vorgang(vorgang, e)
        auftraege = AuftragBuch._falte(e)
        ab = next((a for a in auftraege.values() if a.get("angebot") == v), None) if v.startswith("AN-") else auftraege.get(v)
        an = AngebotStore._falte(e).get(v) if v.startswith("AN-") else None
        quelle = ab or an
        postings = {(p["position"], p["nr"]): p for p in postings_aus(ab)} if ab else {}
        slots = []
        for i, p in enumerate(quelle.get("positionen") or [], 1):
            try:
                n = float(str(p.get("menge") or 1).replace(",", "."))
            except ValueError:
                n = 1
            n = int(n) if n == int(n) and 1 <= n <= 20 else 1
            for k in range(1, n + 1):
                po = postings.get((i, k))
                slots.append({"position": i, "nr": k, "beschreibung": p.get("beschreibung", ""),
                              "titel": f"{po['titel']} · {po['plattform']}" if po else (p.get("beschreibung", "") + (f" #{k}" if n > 1 else "")),
                              "posting": po["id"] if po else ""})
        return {"vorgang": v, "firma": quelle["firma"], "titel": quelle.get("titel", ""), "angebot": an["nummer"] if an else (ab or {}).get("angebot", ""),
                "auftrag": ab["nummer"] if ab else "", "slots": slots}

    # -- Schreiben --------------------------------------------------------------------------------------------------
    def _schreiben(self, typ: str, vorgang: str, daten: dict, *, was: str = "", von: str = "") -> dict:
        v = self._pruefe_vorgang(vorgang, self.bh.eintraege())
        d = {"vorgang": v, **daten} | ({"was": was[:120]} if was else {})
        self.bh.erfassen(typ, d, von=von)
        return d

    def briefing(self, vorgang: str, felder: dict, *, von: str = "") -> dict:
        neu = {k: _t(felder[k], n) for k, _, n in BRIEFING if k in (felder or {})}
        if not neu:
            raise ValueError("Nichts zu speichern.")
        return self._schreiben("konzept_briefing", vorgang, {"felder": neu}, was="Briefing", von=von)

    def idee(self, vorgang: str, daten: dict, *, von: str = "") -> dict:
        iid = _t(daten.get("id"), 20) or "I-" + uuid.uuid4().hex[:8]
        f = {}
        for k, n in (("titel", 160), ("beschreibung", 2000), ("format", 60), ("ziel", 60)):
            if k in daten:
                f[k] = _t(daten[k], n)
        if "status" in daten:
            if daten["status"] not in IDEE_STATUS:
                raise ValueError("Status: idee, ausgewaehlt oder verworfen.")
            f["status"] = daten["status"]
        if not daten.get("id"):
            if not f.get("titel"):
                raise ValueError("Titel der Idee fehlt.")
            f.setdefault("status", "idee")
        self._schreiben("konzept_idee", vorgang, {"id": iid, "felder": f}, was=f"Idee {f.get('titel', iid)}", von=von)
        return {"id": iid}

    def skript(self, vorgang: str, daten: dict, *, von: str = "") -> dict:
        try:
            pos, nr = int(daten.get("position")), int(daten.get("nr") or 1)
        except (TypeError, ValueError):
            raise ValueError("Leistung (Position) fehlt.") from None
        slots = {(s["position"], s["nr"]) for s in self.kontext(vorgang)["slots"]}
        if (pos, nr) not in slots:
            raise ValueError("Diese Leistung gibt es im Vorgang nicht.")
        f = {k: _t(daten[k], n) for k, _, n in SKRIPT if k in daten} | {"position": pos, "nr": nr}
        if "status" in daten:
            if daten["status"] not in SKRIPT_STATUS:
                raise ValueError("Status: entwurf, fertig oder freigegeben.")
            f["status"] = daten["status"]
        sid = f"S-{pos}-{nr}"                                    # ein Skript je Leistung
        self._schreiben("konzept_skript", vorgang, {"id": sid, "felder": f}, was=f"Skript Pos. {pos}/{nr}", von=von)
        return {"id": sid}

    def szene(self, vorgang: str, daten: dict, *, von: str = "") -> dict:
        sid = _t(daten.get("id"), 20) or "Z-" + uuid.uuid4().hex[:8]
        f = {k: _t(daten[k], n) for k, _, n in SZENE if k in daten}
        if daten.get("quelle"):                                  # z. B. „Videograf-Agent (Vorschlag)“ (VIDEOGRAF V3)
            f["quelle"] = _t(daten["quelle"], 60)
        for k in ("reihe", "position", "nr"):
            if daten.get(k) not in (None, ""):
                try:
                    f[k] = int(daten[k])
                except (TypeError, ValueError):
                    raise ValueError(f"{k}: Zahl erwartet.") from None
        if not daten.get("id") and not f.get("titel"):
            raise ValueError("Bezeichnung der Szene fehlt.")
        if not daten.get("id") and "reihe" not in f:
            f["reihe"] = len(self.mappe(vorgang)["szenen"]) + 1
        self._schreiben("konzept_szene", vorgang, {"id": sid, "felder": f}, was=f"Szene {f.get('titel', sid)}", von=von)
        return {"id": sid}

    def szene_erledigt(self, vorgang: str, sid: str, erledigt: bool, *, von: str = "") -> dict:
        if sid not in self.mappe(vorgang)["szenen"]:
            raise KeyError(sid)
        self._schreiben("konzept_szene_erledigt", vorgang, {"id": sid, "erledigt": bool(erledigt)}, von=von)
        return {"id": sid, "erledigt": bool(erledigt)}

    def szene_entfernen(self, vorgang: str, sid: str, *, von: str = "") -> dict:
        if sid not in self.mappe(vorgang)["szenen"]:
            raise KeyError(sid)
        self._schreiben("konzept_szene_entfernt", vorgang, {"id": sid}, was="Szene entfernt", von=von)
        return {"id": sid}

    def dreh(self, vorgang: str, felder: dict, *, von: str = "") -> dict:
        neu = {k: _t(felder[k], n) for k, _, n in DREH if k in (felder or {})}
        if neu.get("datum"):
            try:
                date.fromisoformat(neu["datum"])
            except ValueError:
                raise ValueError("Drehdatum: JJJJ-MM-TT.") from None
        if not neu:
            raise ValueError("Nichts zu speichern.")
        return self._schreiben("konzept_dreh", vorgang, {"felder": neu}, was="Drehplan", von=von)

    def bild(self, vorgang: str, daten: bytes, name: str, *, idee: str = "", von: str = "") -> dict:
        v = self._pruefe_vorgang(vorgang, self.bh.eintraege())
        endung = Path(name or "bild.jpg").suffix.lower() or ".jpg"
        if endung not in BILD_ENDUNGEN:
            raise ValueError("Bitte ein Bild (JPG, PNG, WEBP, HEIC).")
        if not daten or len(daten) > 20 * 1024 * 1024:
            raise ValueError("Bild leer oder groesser als 20 MB.")
        sha = hashlib.sha256(daten).hexdigest()
        ziel = self.ordner / v / "konzept"
        ziel.mkdir(parents=True, exist_ok=True)
        datei = ziel / f"{sha[:12]}{endung}"
        datei.write_bytes(daten)
        d = {"pfad": str(datei.relative_to(self.ordner)), "name": _t(name, 120) or datei.name, "sha256": sha, "idee": _t(idee, 20)}
        self._schreiben("konzept_bild", v, d, was="Bild", von=von)
        return d

    def bild_datei(self, vorgang: str, i: int) -> Path | None:
        b = self.mappe(vorgang)["bilder"]
        if not 0 <= i < len(b):
            return None
        f = (self.ordner / b[i]["pfad"]).resolve()
        return f if f.is_file() and self.ordner.resolve() in f.parents else None

    def freigabe(self, vorgang: str, status: str, *, notiz: str = "", datum: str = "", akte_id: str = "", an: str = "",
                 version: int = 0, sha256: str = "", von: str = "") -> dict:
        if status not in FREIGABE:
            raise ValueError("Status: entwurf, beim_kunden, freigegeben oder aenderung.")
        if status == "aenderung" and not _t(notiz, 10):
            raise ValueError("Bitte den Aenderungswunsch kurz notieren.")
        if datum:
            date.fromisoformat(datum[:10])
        d = {"status": status, "notiz": _t(notiz, 1000), "datum": (datum or "")[:10]}
        if akte_id:
            d |= {"akte_id": akte_id, "an": an, "version": version, "sha256": sha256}
        return self._schreiben("konzept_freigabe", vorgang, d, was=f"Freigabe: {FREIGABE_TEXT[status]}", von=von)


def todos(eintraege: list[dict], heute: date) -> list[dict]:
    """K3: Handlungsbedarf -- Freigabe seit 3 Tagen beim Kunden; Dreh heute/morgen mit offenen Szenen."""
    out = []
    h = heute.isoformat()
    for m in KonzeptStore._falte(eintraege).values():
        v = m["vorgang"]
        f = m["freigabe"]
        if f["status"] == "beim_kunden" and f.get("beim_kunden_am", "9") <= (heute - timedelta(days=3)).isoformat():
            out.append({"id": f"konzept-freigabe:{v}", "bereich": "Aufträge", "icon": "🎬", "titel": f"Konzept-Freigabe ausstehend: {v}",
                        "detail": f"beim Kunden seit {f['beim_kunden_am'][8:10]}.{f['beim_kunden_am'][5:7]}. – nachhaken",
                        "act": "konzept", "act_id": v, "faellig": f["beim_kunden_am"], "dringend": False, "stufe": "woche",
                        "erledigen": None})
        d = m["dreh"].get("datum") or ""
        offen = [s for s in m["szenen_liste"] if not s.get("erledigt")]
        if d and h <= d <= (heute + timedelta(days=1)).isoformat() and offen:
            out.append({"id": f"konzept-dreh:{v}", "bereich": "Aufträge", "icon": "🎬",
                        "titel": f"Dreh {'heute' if d == h else 'morgen'}: {v}",
                        "detail": f"{len(offen)} Szene(n) in der Shotlist · {m['dreh'].get('ort', '')}".strip(" ·"),
                        "act": "konzept", "act_id": v, "faellig": d, "dringend": d == h, "stufe": "dringend" if d == h else "woche",
                        "erledigen": None})
    return out


def pdf(m: dict, kontext: dict, *, firmendaten: dict, firma_name: str, art: str = "kunde", logo: Path | None = None,
        version: int = 0) -> bytes:
    """K3: „Konzept fuer den Kunden“ (Briefing, ausgewaehlte Ideen, Skripte) oder „Drehliste intern“ (Shotlist + Drehplan)."""
    from fpdf import FPDF
    from .beleg_pdf import BLAU, DEJAVU, GRAU, LINIE, ROT, _latin1, datum_de
    uni = (DEJAVU / "DejaVuSans.ttf").exists() and (DEJAVU / "DejaVuSans-Bold.ttf").exists()
    T = (lambda x: str(x or "")) if uni else _latin1
    titel = "Konzept" if art == "kunde" else "Drehliste"

    class _Pdf(FPDF):
        def footer(self):
            self.set_y(-14)
            self.set_font(S, size=7)
            self.set_text_color(120, 120, 120)
            self.cell(0, 4, T(f"{firmendaten.get('firma', '')} · {titel} {kontext['vorgang']} · Seite {self.page_no()}/{{nb}}"),
                      align="C")

    p = _Pdf(format="A4")
    S = "Helvetica"
    if uni:
        p.add_font("DejaVu", "", str(DEJAVU / "DejaVuSans.ttf"))
        p.add_font("DejaVu", "B", str(DEJAVU / "DejaVuSans-Bold.ttf"))
        S = "DejaVu"
    p.set_title(T(f"{titel} {kontext['vorgang']}"))
    p.set_creator("LUNA-OS")
    p.set_margins(18, 14, 18)
    p.set_auto_page_break(True, margin=20)
    p.alias_nb_pages()
    p.add_page()
    B = p.w - 36
    y = 14
    if logo and Path(logo).exists():
        try:
            p.image(str(logo), x=(p.w - 50) / 2, y=y, w=50)
            y += 50 * 221 / 560 + 3
        except Exception:
            pass
    p.set_fill_color(*BLAU)
    p.rect(18, y, B / 2, 1.6, style="F")
    p.set_fill_color(*ROT)
    p.rect(18 + B / 2, y, B / 2, 1.6, style="F")
    p.set_xy(18, y + 6)
    p.set_font(S, "B", 18)
    p.cell(B, 9, T(titel + (f" (Version {version})" if version > 1 else "")), new_x="LMARGIN", new_y="NEXT")
    p.set_font(S, size=10)
    p.set_text_color(85, 85, 85)
    p.multi_cell(B, 5, T(" · ".join(x for x in (firma_name, kontext.get("titel"), f"Vorgang {kontext['vorgang']}") if x)),
                 new_x="LMARGIN", new_y="NEXT")
    p.set_text_color(0, 0, 0)
    p.ln(3)

    def kopf(t):
        if p.get_y() > p.h - 45:
            p.add_page()
        p.ln(2)
        p.set_font(S, "B", 12)
        p.set_text_color(*BLAU)
        p.cell(B, 7, T(t), new_x="LMARGIN", new_y="NEXT")
        p.set_text_color(0, 0, 0)

    def feld(label, wert):
        if not wert:
            return
        p.set_font(S, "B", 9)
        p.cell(B, 5, T(label), new_x="LMARGIN", new_y="NEXT")
        p.set_font(S, size=10)
        p.multi_cell(B, 5, T(wert), new_x="LMARGIN", new_y="NEXT")
        p.ln(1)

    slots = {(s["position"], s["nr"]): s for s in kontext["slots"]}
    if art == "kunde":
        b = m["briefing"]
        if any(b.get(k) for k, _, _ in BRIEFING if k != "notizen"):
            kopf("Briefing")
            for k, label, _ in BRIEFING:
                if k != "notizen":
                    feld(label, b.get(k))
        ideen = [i for i in m["ideen"].values() if i.get("status") == "ausgewaehlt"]
        if ideen:
            kopf("Ideen")
            for i in ideen:
                p.set_font(S, "B", 10)
                p.multi_cell(B, 5, T("• " + i.get("titel", "")), new_x="LMARGIN", new_y="NEXT")
                rest = " · ".join(x for x in (i.get("beschreibung"), i.get("format"), i.get("ziel")) if x)
                if rest:
                    p.set_font(S, size=10)
                    p.multi_cell(B, 5, T("   " + rest), new_x="LMARGIN", new_y="NEXT")
                p.ln(1)
        skripte = sorted(m["skripte"].values(), key=lambda s: (s["position"], s["nr"]))
        if skripte:
            kopf("Skripte")
            for s in skripte:
                sl = slots.get((s["position"], s["nr"]), {})
                p.set_fill_color(*GRAU)
                p.set_font(S, "B", 10.5)
                p.cell(B, 7, T(f"  {sl.get('titel') or 'Pos. ' + str(s['position'])}"), fill=True, new_x="LMARGIN", new_y="NEXT")
                p.ln(1)
                for k, label, _ in SKRIPT:
                    feld(label, s.get(k))
    else:
        d = m["dreh"]
        if any(d.values()):
            kopf("Drehplan")
            feld("Termin", " ".join(x for x in (datum_de(d.get("datum", "")) if d.get("datum") else "", d.get("zeit", "")) if x))
            for k in ("ort", "ansprechpartner", "telefon", "mitbringen"):
                feld(dict((a, b) for a, b, _ in DREH)[k], d.get(k))
        kopf("Shotlist")
        p.set_font(S, "B", 8.5)
        sp = [("", 8), ("#", 8), ("Szene", 52), ("Einstellung", 42), ("Ort / Requisite", 44), ("Dauer", 20)]
        for t, w in sp:
            p.cell(w, 6, T(t), border="B")
        p.ln()
        p.set_font(S, size=8.5)
        p.set_draw_color(*LINIE)
        for n, z in enumerate(m["szenen_liste"], 1):
            werte = ["☑" if z.get("erledigt") and uni else ("x" if z.get("erledigt") else "☐" if uni else "[ ]"), str(n),
                     z.get("titel", ""), z.get("einstellung", ""), " · ".join(x for x in (z.get("ort"), z.get("requisite")) if x),
                     z.get("dauer", "")]
            for (t, w), v in zip(sp, werte):
                p.cell(w, 6, T(v)[:40], border="B")
            p.ln()
        if not m["szenen_liste"]:
            p.cell(B, 6, T("Noch keine Szenen."), new_x="LMARGIN", new_y="NEXT")
    return bytes(p.output())


def mail_text(kontext: dict, ap: dict | None, firmendaten: dict, version: int) -> tuple[str, str]:
    name = " ".join(x for x in ((ap or {}).get("vorname"), (ap or {}).get("nachname")) if x)
    betreff = f"Konzept zur Freigabe – {kontext.get('titel') or kontext['vorgang']}" + (f" (Version {version})" if version > 1 else "")
    text = (f"Moin{' ' + name if name else ''},\n\nanbei unser Konzept{' zu „' + kontext['titel'] + '“' if kontext.get('titel') else ''} "
            "mit Briefing, Ideen und Skripten. Bitte schauen Sie es sich an und geben Sie uns kurz Ihre Freigabe oder "
            "Ihre Änderungswünsche.\n\nViele Grüße\n" + "\n".join(x for x in (firmendaten.get("inhaber"), firmendaten.get("firma")) if x))
    return betreff, text
