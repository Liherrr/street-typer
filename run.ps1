<#
Bit-Rate Brawl - two-PC live typing fight (Windows launcher).
Pure Python standard library: NO pip installs, no model, no mic.

  Both players just run this on the same network:
    powershell -ExecutionPolicy Bypass -File run.ps1
  The first becomes the host; the second auto-discovers it and opens the fight.
  (If a locked-down network blocks discovery, open the URL shown on the host screen.)
#>
Set-Location -Path $PSScriptRoot
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $py) { Write-Error "Python 3.7+ not found. Install from https://www.python.org/downloads/ and re-run."; exit 1 }
Write-Host ">> using $(& $py --version)"
Write-Host ">> starting Bit-Rate Brawl (no dependencies). Windows may ask to allow Python on the network -> click Allow."
& $py fight_server.py @args
