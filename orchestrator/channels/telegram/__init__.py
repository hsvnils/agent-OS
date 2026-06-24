"""Telegram-Kanal: Text- und Sprachnachrichten an den Head of Agents (mobil, async).

Nutzt das kanal-unabhaengige HoA-Gehirn (`core.hoa_conversation`) mit denselben Werkzeugen wie der
Voice-Kanal. Token via orchestrator/.env (Capability-Muster). Antworten als Text; Sprachnachrichten werden
per STT transkribiert. Echter Telegram-Anruf ist nicht moeglich (Bots nehmen keine Anrufe an).
"""
