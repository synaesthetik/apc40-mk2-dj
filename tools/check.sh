#!/usr/bin/env bash
# Verify the script against Live 11's own remote-script sources.
#
#   tools/check.sh [work directory]
#
# Fetches a decompilation of Live 11's MIDI Remote Scripts, prepares an
# importable copy of it, imports this package against it and runs the tests.
# Live itself ships bytecode only, so a decompilation is the only way to get at
# the API outside Ableton.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${1:-${TMPDIR:-/tmp}/apc40mk2-live11-check}"
REFERENCE_REPO="https://github.com/gluon/AbletonLive11_MIDIRemoteScripts.git"

mkdir -p "$WORK"
cd "$WORK"

if [ ! -d live11 ]; then
  echo "==> fetching Live 11 reference sources"
  git clone --depth 1 "$REFERENCE_REPO" live11
fi

if [ ! -d venv ]; then
  echo "==> creating virtualenv"
  python3 -m venv venv
  # The decompiled sources import the future/past compatibility shims
  ./venv/bin/pip install -q future
fi

PYTHON="$WORK/venv/bin/python"

echo "==> preparing reference tree"
"$PYTHON" "$ROOT/tools/prepare_reference.py" "$WORK/live11" "$WORK/ref" 2>/dev/null | grep -v '^ ' || true

echo "==> compiling the script"
"$PYTHON" -m compileall -q "$ROOT/APCAdvanced_MkII" > /dev/null

echo "==> checking against the Live 11 API"
"$PYTHON" "$ROOT/tools/verify.py" --reference "$WORK/ref" 2>/dev/null

echo "==> running tests"
cd "$ROOT"
LIVE11_REFERENCE="$WORK/ref" "$PYTHON" -m unittest discover -s tests 2>&1 | tail -3
