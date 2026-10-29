@echo off
rem LUNA-Probe L1 -- Kopfhoerer am RODE NT-USB (empfohlen)
cd /d %~dp0
venv\Scripts\python.exe probe\probe_l1.py --modus kopfhoerer %*
pause
