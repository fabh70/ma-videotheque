@echo off
REM Construit Videotheque.exe (un seul fichier, sans fenetre console).
REM Prerequis : Python 3.10+ installe (cocher "Add Python to PATH").

cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo ERREUR : Python n'est pas installe ou n'est pas dans le PATH.
  pause
  exit /b 1
)

python -m pip install --upgrade requests pyinstaller
if errorlevel 1 goto echec

set ICONE=
if exist logo.ico set ICONE=--icon logo.ico

python -m PyInstaller --noconfirm --clean --onefile --noconsole --name Videotheque ^
  %ICONE% --add-data "index.html;." videotheque_app.py

if exist dist\Videotheque.exe (
  echo.
  echo OK : dist\Videotheque.exe est pret.
  echo Pour la version portable, lance package_portable.bat
) else (
  goto echec
)
pause
exit /b 0

:echec
echo.
echo ERREUR : la construction a echoue. Copie le message ci-dessus.
pause
exit /b 1
