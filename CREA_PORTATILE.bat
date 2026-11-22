@echo off
chcp 65001 >nul
title KILLA NEWS - creazione della versione portatile
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
echo Installazione degli strumenti di compilazione...
%PY% -m pip install -r requirements-build.txt || goto errore
echo Esecuzione dei test automatici...
%PY% -m unittest discover -s tests || goto errore
echo Creazione dell'eseguibile portatile (alcuni minuti)...
set KILLANEWS_ONEFILE=1
%PY% -m PyInstaller --clean -y --distpath dist --workpath build\portatile installer\killa_news.spec || goto errore
set KILLANEWS_ONEFILE=
if exist "dist\KILLA NEWS Portatile" rmdir /s /q "dist\KILLA NEWS Portatile"
mkdir "dist\KILLA NEWS Portatile"
copy /y dist\KillaNews_Portatile.exe "dist\KILLA NEWS Portatile\KillaNews_Portatile.exe" >nul
copy /y README.md "dist\KILLA NEWS Portatile\" >nul
copy /y CHECKLIST_NVDA.md "dist\KILLA NEWS Portatile\" >nul
echo I dati personali di questa copia portatile vengono salvati nella sottocartella "dati". Elimina questo file per usare invece la cartella AppData.> "dist\KILLA NEWS Portatile\portable.flag"
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\KILLA NEWS Portatile' -DestinationPath 'dist\KillaNews_Portatile.zip'"
echo.
echo Fatto. Versione portatile: dist\KILLA NEWS Portatile\KillaNews_Portatile.exe
echo Archivio da distribuire: dist\KillaNews_Portatile.zip
pause
exit /b 0
:errore
echo.
echo ERRORE: la creazione non e' stata completata. Leggi i messaggi qui sopra.
pause
exit /b 1
