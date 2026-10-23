@echo off
cd /d "%~dp0"
if exist "dist\PartyUpPC\PartyUpPC.exe" (
  start "" "dist\PartyUpPC\PartyUpPC.exe"
  exit /b 0
)
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" -m ue_partyup
  exit /b 0
)
echo Run Setup.cmd first, or use the private standalone Windows build.
pause
exit /b 1
