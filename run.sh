#!/usr/bin/env bash
# Street Typer - two-PC live typing fight (macOS/Linux launcher).
# Pure Python standard library: NO pip installs, no model, no mic.
#
#   Both players just run this on the same network:
#     ./run.sh
#   The first becomes the host; the second auto-discovers it and opens the fight.
#   (If a locked-down network blocks discovery, open the URL shown on the host screen.)
cd "$(dirname "$0")" || exit 1
PY=""
for c in python3 python; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
if [ -z "$PY" ]; then
  echo "ERROR: Python 3.7+ not found. Install from https://www.python.org/downloads/ and re-run."; exit 1
fi
echo ">> using $("$PY" --version 2>&1)"
echo ">> starting Street Typer (no dependencies)."
exec "$PY" fight_server.py "$@"
