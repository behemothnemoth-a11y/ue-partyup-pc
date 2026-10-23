@echo off
cd /d "%~dp0"
if exist "PartyUpPC\PartyUpPC.exe" (
  start "" "PartyUpPC\PartyUpPC.exe" --install
  exit /b 0
)
if exist "dist\PartyUpPC\PartyUpPC.exe" (
  start "" "dist\PartyUpPC\PartyUpPC.exe" --install
  exit /b 0
)
echo Private build not found. Extract the complete release folder or build the app first.
pause
exit /b 1
