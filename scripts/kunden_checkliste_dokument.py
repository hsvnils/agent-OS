"""KUNDEN_CHECKLISTE C1: leere Checkliste als PDF (A4 hochkant) und Word, nur Kopf wie die Konzept-Vorlage.
Fragen stehen in `orchestrator/core/leitfaden.py` (eine Quelle fuer Dokument und Gespraechsleitfaden in LUNA-OS; dort
gibt es die Dateien auch zum Herunterladen). Aufruf vom Repo-Root:
    python scripts/kunden_checkliste_dokument.py <logo.jpg> vorlagen
(Logo = `buchhaltung/logo.jpg` von der NAS; Ergebnis in `vorlagen/`, nicht im Git)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrator.core.leitfaden import dokument_docx, dokument_pdf  # noqa: E402

logo, ziel = Path(sys.argv[1]), Path(sys.argv[2])
(ziel / "Kunden-Checkliste.pdf").write_bytes(dokument_pdf(logo=logo))
(ziel / "Kunden-Checkliste.docx").write_bytes(dokument_docx(logo=logo))
print("ok")
