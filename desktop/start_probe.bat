@echo off
rem LUNA-Probe L1 -- Ton ueber die Creative Stage (Standard, CEO 2026-10-30)
cd /d %~dp0
venv\Scripts\python.exe probe\probe_l1.py --modus lautsprecher %*
pause
