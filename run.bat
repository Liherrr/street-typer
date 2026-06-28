@echo off
setlocal EnableDelayedExpansion
REM Street Typer - launch the game locally (Windows).
REM The server is pure Python standard library, so there is nothing to install.
REM It serves the game, opens it in your default browser, and prints the URL.
REM
REM First run also fetches the offline voice model (about 39 MB) if it is missing,
REM so Emma's voice mode works locally. Without it the keyboard modes are unaffected
REM and voice mode falls back to the browser's own speech engine.
cd /d "%~dp0"

set "MODEL=assets\vosk-model-en.tar.gz"
set "MINBYTES=30000000"
set "URL1=https://raw.githubusercontent.com/Liherrr/street-typer/main/assets/vosk-model-en.tar.gz"
set "URL2=https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.tar.gz"

call :model_ok
if "!OK!"=="1" goto launch

echo Setting up the offline voice model (about 39 MB, one time)...
if not exist assets mkdir assets

call :download "!URL1!"
call :model_ok
if "!OK!"=="1" goto launch

call :download "!URL2!"
call :model_ok
if "!OK!"=="1" goto launch

echo   Could not fetch the voice model (no internet, or no downloader available).
echo   The game still runs: keyboard modes work, and voice mode uses the browser's speech engine.

:launch
where py >nul 2>nul
if !errorlevel!==0 (
  py fight_server.py %*
) else (
  python fight_server.py %*
)
goto :eof

:model_ok
set "OK=0"
set "SZ=0"
if exist "%MODEL%" for %%A in ("%MODEL%") do set "SZ=%%~zA"
if !SZ! GEQ %MINBYTES% set "OK=1"
goto :eof

:download
echo   Downloading from %~1
if exist "%MODEL%.part" del /q "%MODEL%.part"
where curl >nul 2>nul
if !errorlevel!==0 (
  curl -fL --retry 3 --connect-timeout 30 -o "%MODEL%.part" "%~1"
) else (
  powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%~1' -OutFile '%MODEL%.part' -UseBasicParsing } catch { exit 1 }"
)
set "DSZ=0"
if exist "%MODEL%.part" for %%A in ("%MODEL%.part") do set "DSZ=%%~zA"
if !DSZ! GEQ %MINBYTES% (
  move /y "%MODEL%.part" "%MODEL%" >nul
  echo   Voice model ready.
) else (
  if exist "%MODEL%.part" del /q "%MODEL%.part"
)
goto :eof
