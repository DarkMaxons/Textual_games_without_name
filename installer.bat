@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Installation impossible. Verifiez que Python est installe et accessible avec la commande py.
)
pause
