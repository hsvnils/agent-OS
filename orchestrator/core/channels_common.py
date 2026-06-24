"""Leichte, kanaluebergreifende Helfer fuer finance/ (Lesen/Schreiben).

Wiederverwendet die vorhandene Implementierung aus dem Voice-Panel (Single Source of Truth) per
funktionslokalem Import; so bleibt der Text-Kanal (Telegram) ohne Code-Dublette. (Eine spaetere
Verschiebung der finance-I/O nach core/ ist als Aufraeumschritt denkbar.)
"""
from __future__ import annotations


def finance_text(finance_dir, secrets):
    from ..channels.voice.panels import finance_summary
    return finance_summary(finance_dir, secrets)


def set_budget(betrag_eur, finance_dir):
    from ..channels.voice.panels import set_monatsbudget
    return set_monatsbudget(betrag_eur, finance_dir)
