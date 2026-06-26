#!/bin/bash
# macOS double-clickable launcher. First time only, you may need to allow it:
#   right-click this file -> Open  (or in Terminal: chmod +x "Bit-Rate Brawl.command")
cd "$(dirname "$0")" || exit 1
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then
    echo "Starting Bit-Rate Brawl... your browser will open. Keep this window open while you play."
    echo "(If macOS asks to allow incoming network connections, click Allow.)"
    echo
    exec "$c" fight_server.py "$@"
  fi
done
echo "Python 3 not found. Install it from https://www.python.org/downloads/ and try again."
read -r -p "Press Enter to close."
