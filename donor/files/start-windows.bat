@echo off
cd /d "%~dp0"
where py >nul 2>nul || (echo Python 3 is needed. Install it from python.org ^(tick "Add to PATH"^), then double-click this again. & pause & exit /b 1)
py -c "import requests" 2>nul || py -m pip install --user requests
if not exist .env (copy .env.example .env >nul & echo Open the file named .env in this folder with Notepad, paste your token after GT_DONOR_TOKEN= , save, then double-click this again. & notepad .env & pause & exit /b 0)
py donor_worker.py %*
echo.
pause
