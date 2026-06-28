@echo off
REM Street Typer - launch the game locally (Windows).
REM No setup and no dependencies: the server uses only the Python standard library.
REM It serves the game, opens it in your default browser, and prints the URL.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py fight_server.py %*
) else (
  python fight_server.py %*
)
