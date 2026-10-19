"""BF-72 (2026-10-19): archivierte Mails (.eml) mit Umlauten scheiterten beim Drive-Upload -- die Google-Bibliothek baut eine
MIME-Huelle, und mit `message/rfc822` verlangt Pythons E-Mail-Modul reines ASCII. Der Test baut die Huelle genau so wie
`googleapiclient.discovery` (MIMENonMultipart + BytesGenerator) und prueft, dass der Inhalt unveraendert hochgeht."""
import unittest
from email.generator import BytesGenerator
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from io import BytesIO
from unittest import mock

from orchestrator.governance.google_workspace import GoogleWorkspace

EML = "From: kunde@example.com\r\nSubject: Rechnung RE-2026-0001\r\n\r\nViele Grüße aus Hamburg – 714 €\r\n".encode("utf-8")


class _Dateien:
    def __init__(self, gesehen):
        self.gesehen = gesehen

    def create(self, body, media_body, fields):
        root = MIMEMultipart("related")                       # wie googleapiclient.discovery (multipart-Upload)
        teil = MIMENonMultipart(*media_body.mimetype().split("/"))
        teil.set_payload(media_body.getbytes(0, media_body.size()))
        root.attach(teil)
        fp = BytesIO()
        BytesGenerator(fp, mangle_from_=False).flatten(root, unixfrom=False)
        self.gesehen.append((media_body.mimetype(), media_body.getbytes(0, media_body.size())))
        return mock.Mock(execute=lambda: {"id": "D1", "md5Checksum": "abc"})


class TestDriveUpload(unittest.TestCase):
    def test_mail_mit_umlauten(self):
        gesehen = []
        svc = mock.Mock()
        svc.files.return_value = _Dateien(gesehen)
        gw = GoogleWorkspace.__new__(GoogleWorkspace)
        gw._guard = lambda: None
        gw.auth = mock.Mock(service=lambda *a: svc)
        r = gw.drive_datei_hochladen(EML, "Mail_RE-2026-0001.eml", "ORDNER", "message/rfc822")
        self.assertTrue(r.get("ok"), r)
        self.assertEqual(gesehen, [("application/octet-stream", EML)])      # Inhalt Byte fuer Byte unveraendert
        gw.drive_datei_hochladen(b"%PDF-1.4", "a.pdf", "ORDNER", "application/pdf")
        self.assertEqual(gesehen[-1][0], "application/pdf")                   # andere Typen unveraendert


if __name__ == "__main__":
    unittest.main()
