@echo off
cd /d "%~dp0"
py main.py
if errorlevel 1 (
    echo.
    echo Le jeu a rencontre une erreur. Lancez d'abord installer.bat.
)
pause
