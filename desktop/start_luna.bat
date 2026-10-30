@echo off
rem LUNA-Desktop L2 -- mit Fenster (Ton ueber die Creative Stage)
cd /d %~dp0
venv\Scripts\python.exe probe\luna_desktop.py --modus lautsprecher %*
pause
