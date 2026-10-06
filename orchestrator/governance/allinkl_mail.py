"""MAILVERSAND_ALLINKL M1: Kundenmails ueber das eigene Postfach bei All-Inkl (luna@hanserautisch.de) statt Gmail.

Gleicher Aufruf wie `GoogleWorkspace.mail_senden` (an, betreff, text, anhaenge, absender_name, bestaetigt) -- die
Senden-Ablaeufe (PDF-Ablage, Firmenakte, Status, Erinnerungen) bleiben unveraendert. Versand per SMTP (SSL 465 bzw.
STARTTLS 587), danach Ablage der identischen Mail per IMAP in „Gesendet“ und als .eml ueber `mail_roh`.

Welcher Weg gilt, entscheidet allein der Schalter `KUNDENVERSAND` (gmail | allinkl) in `orchestrator/.env`; es gibt
**keinen automatischen Rueckfall** auf Gmail, damit kein Kunde Mails von zwei Absendern bekommt. Zugangsdaten nur aus
der `.env`, nie in Fehlertexten oder Logs.
"""
from __future__ import annotations

import imaplib
import re
import smtplib
import ssl
import time
import uuid
from email.message import EmailMessage
from email.utils import formatdate

SCHLUESSEL = ("ALLINKL_SMTP_HOST", "ALLINKL_IMAP_HOST", "ALLINKL_MAIL_USER", "ALLINKL_MAIL_PASSWORT", "ALLINKL_ABSENDER")
GESENDET_KANDIDATEN = ("Gesendet", "Sent", "INBOX.Gesendet", "INBOX.Sent", "Gesendete Objekte", "Sent Items")


def kundenversand(env: dict) -> str:
    """'allinkl' oder 'gmail' (Standard) -- nur der Schalter zaehlt."""
    return "allinkl" if (env.get("KUNDENVERSAND") or "").strip().lower() == "allinkl" else "gmail"


def versandweg(env: dict, google):
    """Kundenversand nach Schalter: All-Inkl (muss eingerichtet sein -- sonst klarer Fehler statt Rueckfall) oder Gmail."""
    if kundenversand(env) != "allinkl":
        return google
    a = AllInklMail(env)
    if not a.verfuegbar():
        raise ValueError("Kundenversand steht auf All-Inkl, aber das Postfach ist nicht eingerichtet (fehlt in der .env: "
                         + ", ".join(a.fehlend() or ["ALLINKL_ABSENDER"]) + ").")
    return a


def nachricht(an: str, betreff: str, text: str, anhaenge: list | None, absender: str, domain: str,
              kennung: str) -> EmailMessage:
    """Message-ID = <kennung@domain> -- aus der gespeicherten Kennung wieder herleitbar (Antworten, M2)."""
    msg = EmailMessage()
    msg["From"] = absender
    msg["To"] = an
    msg["Subject"] = betreff
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = f"<{kennung}@{domain or 'localhost'}>"
    from ..core.textbausteine import mail_inhalt
    mail_inhalt(msg, text)                                    # Text + ggf. HTML mit klickbaren Links (Signatur)
    for name, daten, typ in anhaenge or []:
        haupt, _, unter = (typ or "application/octet-stream").partition("/")
        msg.add_attachment(daten, maintype=haupt, subtype=unter or "octet-stream", filename=name)
    return msg


class AllInklMail:
    """Versandweg „All-Inkl“. `smtp_fabrik`/`imap_fabrik` sind fuer Tests austauschbar (kein echter Versand)."""

    kanal = "allinkl"

    def __init__(self, env: dict, *, smtp_fabrik=None, imap_fabrik=None):
        g = lambda k, d="": (env.get(k) or d).strip()
        self.smtp_host, self.smtp_port = g("ALLINKL_SMTP_HOST"), int(g("ALLINKL_SMTP_PORT", "465") or 465)
        self.imap_host, self.imap_port = g("ALLINKL_IMAP_HOST"), int(g("ALLINKL_IMAP_PORT", "993") or 993)
        self.user, self._pw = g("ALLINKL_MAIL_USER"), env.get("ALLINKL_MAIL_PASSWORT") or ""
        self.adresse, self.ordner = g("ALLINKL_ABSENDER"), g("ALLINKL_GESENDET_ORDNER")
        self._smtp = smtp_fabrik or self._smtp_echt
        self._imap = imap_fabrik or (lambda: imaplib.IMAP4_SSL(self.imap_host, self.imap_port,
                                                               ssl_context=ssl.create_default_context(), timeout=30))
        self._roh: dict[str, bytes] = {}

    # -- Zustand --------------------------------------------------------------------------------------------------

    def fehlend(self) -> list[str]:
        werte = {"ALLINKL_SMTP_HOST": self.smtp_host, "ALLINKL_IMAP_HOST": self.imap_host,
                 "ALLINKL_MAIL_USER": self.user, "ALLINKL_MAIL_PASSWORT": self._pw, "ALLINKL_ABSENDER": self.adresse}
        return [k for k in SCHLUESSEL if not werte[k]]

    def verfuegbar(self) -> bool:
        return not self.fehlend() and "@" in self.adresse

    def absender(self, name: str = "") -> str:
        return f"{name} <{self.adresse}>" if name else self.adresse

    # -- Senden ---------------------------------------------------------------------------------------------------

    def _smtp_echt(self):
        ctx = ssl.create_default_context()
        if self.smtp_port == 465:
            return smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=ctx, timeout=30)
        s = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
        s.starttls(context=ctx)
        return s

    def mail_senden(self, an: str, betreff: str, text: str, *, bestaetigt: bool = False,
                    anhaenge: list | None = None, absender_name: str = "") -> dict:
        """Gated wie Gmail: ohne bestaetigt=True nur Vorschau. Rueckgabe: id = Kennung (Message-ID <id@domain>), thread_id leer
        (Antworten erkennt erst M2 per IMAP -- der Gmail-Verlaufs-Poll ueberspringt leere thread_ids)."""
        if not self.verfuegbar():
            return {"ok": False, "hinweis": "All-Inkl-Postfach ist nicht eingerichtet (fehlt in der .env: "
                                            + ", ".join(self.fehlend() or ["ALLINKL_ABSENDER"]) + ")."}
        if not bestaetigt:
            return {"ok": False, "bestaetigung_noetig": True, "vorschau": {"an": an, "betreff": betreff, "text": text},
                    "hinweis": "Senden braucht CEO-Bestaetigung -- erneut mit bestaetigt=true aufrufen."}
        kennung = "luna-" + uuid.uuid4().hex[:24]                  # dateinamen-tauglich (Archiv-.eml)
        msg = nachricht(an, betreff, text, anhaenge, self.absender(absender_name), self.adresse.partition("@")[2], kennung)
        roh = msg.as_bytes()
        try:
            s = self._smtp()
            try:
                s.login(self.user, self._pw)
                s.send_message(msg)
            finally:
                try:
                    s.quit()
                except Exception:
                    pass
        except smtplib.SMTPAuthenticationError:
            return {"ok": False, "hinweis": "All-Inkl hat die Anmeldung abgelehnt -- Benutzer/Passwort in der .env pruefen."}
        except smtplib.SMTPRecipientsRefused:
            return {"ok": False, "hinweis": "Der Mailserver hat den Empfaenger abgelehnt -- Adresse pruefen."}
        except Exception as exc:                            # ohne Fehlertext (koennte Zugangsdaten enthalten)
            return {"ok": False, "hinweis": f"Senden ueber All-Inkl fehlgeschlagen ({exc.__class__.__name__})."}
        self._roh[kennung] = roh
        ablage = self._gesendet_ablegen(roh)
        return {"ok": True, "gesendet": True, "id": kennung, "message_id": msg["Message-ID"], "thread_id": "", "kanal": self.kanal,
                "absender": self.adresse, "gesendet_ordner": ablage}

    def _gesendet_ablegen(self, roh: bytes) -> str:
        """Kopie in „Gesendet“ (IMAP APPEND, als gelesen). Fehler hier stoppen den Versand nicht -- die Mail ist raus,
        die .eml liegt trotzdem in der Firmenakte; Rueckgabe = Ordnername oder ''."""
        try:
            i = self._imap()
            try:
                i.login(self.user, self._pw)
                ordner = self.ordner or self._sent_ordner(i)
                if not ordner:
                    return ""
                typ, _ = i.append(_imap_name(ordner), r"(\Seen)", imaplib.Time2Internaldate(time.time()), roh)
                return ordner if typ == "OK" else ""
            finally:
                try:
                    i.logout()
                except Exception:
                    pass
        except Exception:
            return ""

    @staticmethod
    def _sent_ordner(i) -> str:
        typ, zeilen = i.list()
        if typ != "OK":
            return ""
        namen = []
        for z in zeilen or []:
            z = z.decode("utf-8", "replace") if isinstance(z, bytes) else str(z)
            m = re.match(r'\((?P<flags>[^)]*)\)\s+(?:"[^"]*"|NIL)\s+(?P<name>.+)$', z)
            if not m:
                continue
            name = m["name"].strip().strip('"')
            if "\\sent" in m["flags"].lower():
                return name
            namen.append(name)
        return next((k for k in GESENDET_KANDIDATEN if k in namen), "")

    def mail_roh(self, kennung: str) -> dict:
        """Die eben gesendete Mail (identische Bytes) zum Archivieren als .eml."""
        roh = self._roh.get(kennung)
        return {"ok": True, "roh": roh} if roh else {"ok": False, "hinweis": "Mail nicht im Zwischenspeicher."}

    def posteingang(self, *, tage: int = 30, max_mails: int = 200) -> list[dict]:
        """MAILVERSAND_ALLINKL M2: Mails im Posteingang der letzten `tage` als Rohdaten -- nur lesen (BODY.PEEK, der
        Gelesen-Status bleibt unveraendert, nichts wird verschoben oder geloescht). Rueckgabe [{uid, roh}]."""
        from datetime import date, timedelta
        if not self.verfuegbar():
            return []
        monate = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
        d = date.today() - timedelta(days=tage)
        seit = f"{d.day:02d}-{monate[d.month - 1]}-{d.year}"              # IMAP will englische Monate (unabh. von Locale)
        out = []
        i = self._imap()
        try:
            i.login(self.user, self._pw)
            typ, _ = i.select("INBOX", readonly=True)
            if typ != "OK":
                return []
            typ, daten = i.uid("SEARCH", None, "SINCE", seit)
            uids = (daten[0].split() if typ == "OK" and daten and daten[0] else [])[-max_mails:]
            for uid in uids:
                typ, teile = i.uid("FETCH", uid, "(BODY.PEEK[])")
                roh = next((t[1] for t in teile or [] if isinstance(t, tuple) and len(t) > 1), None) if typ == "OK" else None
                if roh:
                    out.append({"uid": uid.decode() if isinstance(uid, bytes) else str(uid), "roh": roh})
        finally:
            try:
                i.logout()
            except Exception:
                pass
        return out

    def verbindung_pruefen(self) -> dict:
        """Nur Anmeldung an SMTP und IMAP (kein Versand) -- fuer den Einrichtungs-Check."""
        if not self.verfuegbar():
            return {"ok": False, "fehlend": self.fehlend()}
        out = {"ok": True, "smtp": False, "imap": False, "gesendet_ordner": ""}
        try:
            s = self._smtp()
            try:
                s.login(self.user, self._pw)
                out["smtp"] = True
            finally:
                s.quit()
        except Exception as exc:
            out["smtp_fehler"] = exc.__class__.__name__
        try:
            i = self._imap()
            try:
                i.login(self.user, self._pw)
                out["imap"] = True
                out["gesendet_ordner"] = self.ordner or self._sent_ordner(i)
            finally:
                i.logout()
        except Exception as exc:
            out["imap_fehler"] = exc.__class__.__name__
        out["ok"] = out["smtp"] and out["imap"] and bool(out["gesendet_ordner"])
        return out


def _imap_name(ordner: str) -> str:
    return f'"{ordner}"' if " " in ordner and not ordner.startswith('"') else ordner
