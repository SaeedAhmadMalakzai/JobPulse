#!/usr/bin/env bash
# Build the SwiftUI executable and wrap it into a native JobPulse.app bundle.
set -euo pipefail
cd "$(dirname "$0")"

CONFIG="${1:-release}"
APP="JobPulse.app"
BIN_NAME="JobPulse"

echo "▶ Building ($CONFIG)…"
swift build -c "$CONFIG"
BIN_PATH="$(swift build -c "$CONFIG" --show-bin-path)/$BIN_NAME"

if [ ! -f Icon/AppIcon.icns ]; then
  echo "▶ Icon missing — generating…"
  ./make-icon.sh
fi

echo "▶ Assembling ${APP}…"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN_PATH" "$APP/Contents/MacOS/$BIN_NAME"
cp Icon/AppIcon.icns "$APP/Contents/Resources/AppIcon.icns"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>            <string>JobPulse</string>
  <key>CFBundleDisplayName</key>     <string>JobPulse</string>
  <key>CFBundleExecutable</key>      <string>JobPulse</string>
  <key>CFBundleIdentifier</key>      <string>af.jobpulse.native</string>
  <key>CFBundleVersion</key>         <string>1.0.0</string>
  <key>CFBundleShortVersionString</key> <string>1.0.0</string>
  <key>CFBundlePackageType</key>     <string>APPL</string>
  <key>CFBundleIconFile</key>        <string>AppIcon</string>
  <key>CFBundleIconName</key>        <string>AppIcon</string>
  <key>LSMinimumSystemVersion</key>  <string>14.0</string>
  <key>NSHighResolutionCapable</key> <true/>
  <key>LSApplicationCategoryType</key> <string>public.app-category.productivity</string>
</dict>
</plist>
PLIST

# Ad-hoc sign so Gatekeeper lets it launch locally.
codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || true

echo "✓ Built $APP"
echo "  Launch with:  open $APP"
