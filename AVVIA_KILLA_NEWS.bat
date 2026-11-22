@echo off
chcp 65001 >nul
title KILLA NEWS
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% -c "import wx, feedparser, requests" >nul 2>nul
if errorlevel 1 (
  echo Prima installazione delle dipendenze di KILLA NEWS, attendere...
  %PY% -m pip install --upgrade pip
  %PY% -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Installazione non riuscita. Verifica di avere Python 3.11, 3.12 o 3.13 a 64 bit e la connessione a Internet.
    pause
    exit /b 1
  )
)
if "%PY%"=="py -3" (start "" pyw -3 main.py) else (start "" pythonw main.py)
