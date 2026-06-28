#!/usr/bin/env bash
# Street Typer - launch the game locally.
# The server is pure Python standard library, so there is nothing to install.
# It serves the game, opens it in your default browser, and prints the URL.
#
# First run also fetches the offline voice model (about 39 MB) if it is missing,
# so Emma's voice mode works locally. Without it the keyboard modes are unaffected
# and voice mode falls back to the browser's own speech engine.
#
# (Pass --cloud to serve headless on $PORT for a hosted deployment.)
set -e
cd "$(dirname "$0")"

MODEL="assets/vosk-model-en.tar.gz"
MIN_BYTES=30000000   # a complete model is about 41 MB; smaller means missing or partial
MODEL_URLS="
https://raw.githubusercontent.com/Liherrr/street-typer/main/assets/vosk-model-en.tar.gz
https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.tar.gz
"

filesize() { wc -c < "$1" 2>/dev/null | tr -d '[:space:]'; }

model_ok() {
  [ -f "$MODEL" ] || return 1
  local s; s=$(filesize "$MODEL")
  [ -n "$s" ] && [ "$s" -ge "$MIN_BYTES" ]
}

download() {   # download URL -> places "$MODEL" and returns 0 only if it looks complete
  local url="$1" tmp="$MODEL.part"
  rm -f "$tmp"
  echo "  downloading from $url"
  if command -v curl >/dev/null 2>&1; then
    curl -fL --retry 3 --connect-timeout 30 -o "$tmp" "$url" || return 1
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$tmp" "$url" || return 1
  else
    echo "  neither curl nor wget is available."
    return 1
  fi
  local s; s=$(filesize "$tmp")
  if [ -n "$s" ] && [ "$s" -ge "$MIN_BYTES" ]; then
    mv -f "$tmp" "$MODEL"; return 0
  fi
  rm -f "$tmp"; return 1
}

if ! model_ok; then
  echo "Setting up the offline voice model (about 39 MB, one time)..."
  mkdir -p assets
  got=0
  for url in $MODEL_URLS; do
    if download "$url"; then got=1; echo "  voice model ready."; break; fi
  done
  if [ "$got" -ne 1 ]; then
    echo "  Could not fetch the voice model (no internet, or no curl/wget)."
    echo "  The game still runs: keyboard modes work, and voice mode uses the browser's speech engine."
  fi
fi

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python 3 is required. Install it from https://www.python.org/downloads/" >&2
  exit 1
fi
exec "$PY" fight_server.py "$@"
