#!/usr/bin/env bash
# Copy the control surface script into Live's user Remote Scripts folder.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="APCAdvanced_MkII"

if [ -n "${ABLETON_USER_LIBRARY:-}" ]; then
  USER_LIBRARY="$ABLETON_USER_LIBRARY"
elif [ -d "$HOME/Music/Ableton/User Library" ]; then
  USER_LIBRARY="$HOME/Music/Ableton/User Library"
elif [ -d "$HOME/Documents/Ableton/User Library" ]; then
  USER_LIBRARY="$HOME/Documents/Ableton/User Library"
else
  echo "Could not find Live's User Library." >&2
  echo "Set ABLETON_USER_LIBRARY to it and run again." >&2
  exit 1
fi

DESTINATION="$USER_LIBRARY/Remote Scripts/$SCRIPT_NAME"

if [ -e "$DESTINATION" ]; then
  echo "$DESTINATION already exists."
  read -r -p "Replace it? [y/N] " reply
  case "$reply" in
    y|Y) rm -rf "$DESTINATION" ;;
    *) echo "Left alone."; exit 0 ;;
  esac
fi

mkdir -p "$USER_LIBRARY/Remote Scripts"
cp -R "$ROOT/$SCRIPT_NAME" "$DESTINATION"
find "$DESTINATION" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

echo "Installed to $DESTINATION"
echo "Restart Live, then pick $SCRIPT_NAME as a Control Surface in Preferences."
