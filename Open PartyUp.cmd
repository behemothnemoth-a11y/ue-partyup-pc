@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" -m ue_partyup
) else (
  "..\..\work\bluetooth-env\Scripts\python.exe" -m ue_partyup
  if errorlevel 1 pause
)
