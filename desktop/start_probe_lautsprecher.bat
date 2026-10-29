@echo off
rem LUNA-Probe L1 -- Ton ueber die Creative-Lautsprecher (Unterbrechen schwieriger)
cd /d %~dp0
venv\Scripts\python.exe probe\probe_l1.py --modus lautsprecher %*
pause
