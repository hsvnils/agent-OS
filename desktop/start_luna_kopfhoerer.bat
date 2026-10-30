@echo off
rem LUNA-Desktop L2 -- Kopfhoerer am RODE NT-USB (ohne Echo-Gefahr)
cd /d %~dp0
venv\Scripts\python.exe probe\luna_desktop.py --modus kopfhoerer %*
pause
