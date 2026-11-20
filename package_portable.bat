@echo off
REM Cree le dossier portable MaVideotheque_Portable (a copier sur cle USB)
REM puis l'archive MaVideotheque_Portable.zip prete pour GitHub.
REM Lance d'abord build_exe.bat.

cd /d "%~dp0"
if not exist dist\Videotheque.exe (
  echo Lance d'abord build_exe.bat.
  pause
  exit /b 1
)

set DEST=MaVideotheque_Portable
if exist "%DEST%" rmdir /s /q "%DEST%"
mkdir "%DEST%"
mkdir "%DEST%\donnees"

copy /y dist\Videotheque.exe "%DEST%\" >nul
copy /y LISEZMOI.txt "%DEST%\" >nul
if exist logo.ico copy /y logo.ico "%DEST%\" >nul

REM Marqueur : en mode portable, les donnees restent dans %DEST%\donnees
echo portable > "%DEST%\portable.flag"

REM VLC portable inclus (dossier VLC, ou vlc-3.0.21 du projet)
if exist VLC\vlc.exe (
  xcopy /e /i /q /y VLC "%DEST%\VLC" >nul
) else if exist vlc-3.0.21\vlc.exe (
  xcopy /e /i /q /y vlc-3.0.21 "%DEST%\VLC" >nul
) else (
  mkdir "%DEST%\VLC"
  echo Mets ici le dossier VLC portable si tu veux un lecteur inclus. > "%DEST%\VLC\LISEZMOI.txt"
)

REM Archive ZIP (utilisable directement sur GitHub Releases)
if exist MaVideotheque_Portable.zip del /q MaVideotheque_Portable.zip
tar -a -c -f MaVideotheque_Portable.zip "%DEST%"

echo.
if exist MaVideotheque_Portable.zip (
  echo OK : dossier %DEST% et archive MaVideotheque_Portable.zip prets.
) else (
  echo OK : dossier %DEST% pret ^(archive ZIP non creee^).
)
pause
