"""Gemeinsame Test-Einstellungen: keine echten Netzabrufe aus Hintergrund-Helfern (z. B. EZB-Kurse, Etappe 20)."""
import os

os.environ.setdefault("LUNA_EZB_OFFLINE", "1")
