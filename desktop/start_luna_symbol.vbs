Rem LUNA-Desktop L2 -- ohne Fenster, nur Symbol in der Taskleiste (Rechtsklick: Stopp / Beenden)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
sh.Run """venv\Scripts\pythonw.exe"" probe\luna_desktop.py --symbol --modus lautsprecher", 0, False
