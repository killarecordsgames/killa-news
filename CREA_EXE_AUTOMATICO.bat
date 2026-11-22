@echo off
chcp 65001 >nul
title KILLA NEWS - creazione automatica dell'eseguibile
cd /d "%~dp0"
echo KILLA NEWS - creazione automatica dell'eseguibile.
echo Non chiudere questa finestra. Ci vorranno da 5 a 15 minuti.
echo.

set "PYEXE="
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul && set "PYEXE=python"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if not defined PYEXE (
  echo Passo 1 di 4: installazione di Python 3.12...
  winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
  if not exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    echo winget non disponibile: scarico Python dal sito ufficiale python.org...
    curl.exe -L -o "%TEMP%\python-3.12.10-amd64.exe" https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
    "%TEMP%\python-3.12.10-amd64.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0
  )
  if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PYEXE (
  echo ERRORE: non sono riuscito a installare Python. Installalo da python.org e riprova.
  goto fine_errore
)
echo Python trovato.
echo.
echo Passo 2 di 4: installazione dei componenti del programma...
"%PYEXE%" -m pip install --upgrade pip
"%PYEXE%" -m pip install -r requirements-build.txt || goto fine_errore
echo.
echo Passo 3 di 4: test automatici...
"%PYEXE%" -m unittest discover -s tests || goto fine_errore
echo.
echo Passo 4 di 4: creazione dell'eseguibile...
set KILLANEWS_ONEFILE=1
"%PYEXE%" -m PyInstaller --clean -y --distpath dist --workpath build\portatile installer\killa_news.spec || goto fine_errore
set KILLANEWS_ONEFILE=
copy /y dist\KillaNews_Portatile.exe "%~dp0KillaNews.exe" >nul
echo.
echo FATTO. L'eseguibile e' pronto: %~dp0KillaNews.exe
echo Si trova nella cartella Documenti, KILLA_NEWS. Premi un tasto per chiudere.
pause >nul
exit /b 0

:fine_errore
echo.
echo ERRORE: la creazione non e' stata completata. Leggi i messaggi qui sopra
echo oppure copiali a Claude. Premi un tasto per chiudere.
pause >nul
exit /b 1
