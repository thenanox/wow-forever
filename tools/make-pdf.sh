#!/bin/sh
# Regenera la guía y el PDF. Uso: sh tools/make-pdf.sh
cd "$(dirname "$0")/.." || exit 1
python3 tools/build.py --offline || exit 1
# Chrome en macOS; Chromium o Chrome en Linux
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || CHROME=$(command -v chromium || command -v chromium-browser || command -v google-chrome-stable || command -v google-chrome)
[ -n "$CHROME" ] || { echo "No encuentro Chrome ni Chromium para generar el PDF" >&2; exit 1; }
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
  --generate-pdf-document-outline --virtual-time-budget=20000 \
  --print-to-pdf="Enano-Chaman-WoW-Forever.pdf" "file://$PWD/dist/print.html" 2>/dev/null
ls -la Enano-Chaman-WoW-Forever.pdf
