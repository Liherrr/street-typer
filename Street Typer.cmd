@echo off
title Street Typer
cd /d "%~dp0"
set "PY=python"
where python >nul 2>nul || set "PY=py"
where %PY% >nul 2>nul || (
  echo Python 3 was not found. Install it from https://www.python.org/downloads/ then double-click again.
  echo.
  pause
  exit /b 1
)

rem --- one-time: open the Windows firewall so the OTHER computer can reach this host ---
if not exist "%~dp0.firewall_ok" (
  echo One-time setup: allowing Street Typer through the Windows firewall.
  echo A Windows prompt will appear -- click YES  ^(needed so the other laptop can connect^).
  powershell -NoProfile -Command "try{ Start-Process -Verb RunAs -Wait -WindowStyle Hidden -FilePath '%~dp0_firewall_rules.cmd' }catch{}"
  echo.
)

echo ============================================================
echo  STREET TYPER  -  starting...
echo  Your browser opens automatically. KEEP THIS WINDOW OPEN
echo  while you play. (Close it or press Ctrl+C to stop.)
echo ============================================================
echo.
%PY% fight_server.py %*
echo.
echo  Game server stopped. Press any key to close this window.
pause >nul
