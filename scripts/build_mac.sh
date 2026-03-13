#!/usr/bin/env bash
# Build JobPulse for macOS. Run from project root with venv active.
# Output: dist/JobPulse.app and JobPulse-mac.dmg

set -e
cd "$(dirname "$0")/.."

echo "Building JobPulse for macOS..."
pip install pyinstaller -q
pyinstaller --noconfirm jobpulse.spec

if [[ ! -d dist/JobPulse.app ]]; then
  echo "Expected dist/JobPulse.app not found."
  exit 1
fi

echo "Creating JobPulse-mac.dmg..."
DMG_NAME="JobPulse-mac.dmg"
DMG_VOL="JobPulse"
VOL_PATH="dist/${DMG_VOL}"
rm -rf "$VOL_PATH" "$DMG_NAME"
mkdir -p "$VOL_PATH"
cp -R dist/JobPulse.app "$VOL_PATH/"
ln -s /Applications "$VOL_PATH/Applications"
hdiutil create -volname "JobPulse" -srcfolder "$VOL_PATH" -ov -format UDZO "dist/${DMG_NAME}"
rm -rf "$VOL_PATH"
echo "Done. App: dist/JobPulse.app  |  DMG: dist/${DMG_NAME}"
