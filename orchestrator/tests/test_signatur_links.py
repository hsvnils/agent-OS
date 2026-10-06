"""Signatur mit klickbaren Links: [Wort](https://…) -> HTML-Teil mit <a>, Textteil „Wort (https://…)“; nur http(s)."""
import email
import unittest
from email import policy

from orchestrator.core.textbausteine import als_html, eml, nur_text
from orchestrator.governance.allinkl_mail import nachricht
from orchestrator.governance.google_workspace import _mime

SIG = ("Herzliche Grüße aus Hamburg\nNils Krüger\n\nHier vernetzen:\n@hanserautisch: [Instagram](https://instagram.com/hanserautisch)"
       " - [Facebook](https://facebook.com/hanserautisch) - Twitter")


def teile(roh: bytes) -> dict:
    m = email.message_from_bytes(roh, policy=policy.default)
    return {"text": m.get_body(("plain",)).get_content(), "html": (m.get_body(("html",)) or None) and m.get_body(("html",)).get_content(),
            "anhaenge": [a.get_filename() for a in m.iter_attachments()]}


class TestLinks(unittest.TestCase):
    def test_umwandeln(self):
        self.assertEqual(nur_text("[Instagram](https://instagram.com/x)"), "Instagram (https://instagram.com/x)")
        h = als_html("Moin <b>\n[Instagram](https://instagram.com/x?a=1&b=2)")
        self.assertIn('<a href="https://instagram.com/x?a=1&amp;b=2">Instagram</a>', h)
        self.assertIn("Moin &lt;b&gt;<br>", h)                                   # Text wird nie als HTML ausgefuehrt
        self.assertNotIn("<a", als_html("[Klick](javascript:alert(1))"))         # nur http(s)

    def test_mails(self):
        t = teile(nachricht("a@b.de", "Hallo", "Moin\n\n" + SIG, [("A.pdf", b"%PDF", "application/pdf")], "LUNA <luna@hanserautisch.de>",
                            "hanserautisch.de", "luna-x").as_bytes())
        self.assertIn("Instagram (https://instagram.com/hanserautisch)", t["text"])
        self.assertIn('<a href="https://facebook.com/hanserautisch">Facebook</a>', t["html"])
        self.assertEqual(t["anhaenge"], ["A.pdf"])
        t = teile(eml("a@b.de", "Hallo", SIG, ("A.pdf", b"%PDF")))
        self.assertIn('<a href="https://instagram.com/hanserautisch">Instagram</a>', t["html"])
        import base64
        t = teile(base64.urlsafe_b64decode(_mime("a@b.de", "Hallo", SIG)))
        self.assertIn("Facebook (https://facebook.com/hanserautisch)", t["text"])
        t = teile(nachricht("a@b.de", "Hallo", "ohne Links", None, "x@y.de", "y.de", "k").as_bytes())
        self.assertIsNone(t["html"])                                             # ohne Links bleibt es reiner Text


if __name__ == "__main__":
    unittest.main()
