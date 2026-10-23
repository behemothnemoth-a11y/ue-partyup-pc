@echo off
cd /d "%~dp0"
echo Installing pinned app dependencies into this folder's .venv.
py -3.13 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Setup complete. Open PartyUp.cmd launches the application.
pause
exit /b 0
:failed
echo Setup failed. Install Python 3.13 with tkinter and the Python launcher, then retry.
pause
exit /b 1
