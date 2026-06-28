#!/usr/bin/env bash
# Street Typer - launch the game locally.
# No setup and no dependencies: the server uses only the Python standard library.
# It serves the game, opens it in your default browser, and prints the URL.
# (Pass --cloud to serve headless on $PORT for a hosted deployment.)
set -e
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python 3 is required. Install it from https://www.python.org/downloads/" >&2
  exit 1
fi
exec "$PY" fight_server.py "$@"
