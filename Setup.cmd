@echo off
cd /d "%~dp0"
echo This installs pinned Bluetooth dependencies into this folder's .venv.
python -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Setup complete. Open PartyUp.cmd launches the application.
pause
exit /b 0
:failed
echo Setup failed. Check that Python 3.13 is installed with tkinter and is on PATH.
pause
exit /b 1
