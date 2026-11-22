@echo off
chcp 65001 >nul
title KILLA NEWS - creazione dell'installatore
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
echo Installazione degli strumenti di compilazione...
%PY% -m pip install -r requirements-build.txt || goto errore
echo Esecuzione dei test automatici...
%PY% -m unittest discover -s tests || goto errore
echo Creazione della cartella del programma (alcuni minuti)...
set KILLANEWS_ONEFILE=
%PY% -m PyInstaller --clean -y --distpath dist --workpath build\installer installer\killa_news.spec || goto errore
set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set ISCC="%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo.
  echo Inno Setup 6 non e' installato. Scaricalo gratuitamente da https://jrsoftware.org/isdl.php
  echo e poi esegui di nuovo questo file. La cartella del programma e' gia' pronta in dist\KillaNews
  pause
  exit /b 1
)
%ISCC% installer\killa_news.iss || goto errore
echo.
echo Fatto. Installatore: dist\KillaNews_Installazione.exe
pause
exit /b 0
:errore
echo.
echo ERRORE: la creazione non e' stata completata. Leggi i messaggi qui sopra.
pause
exit /b 1
