#!/usr/bin/env bash
# Render the 1024px master with AppKit, then compile a multi-resolution AppIcon.icns.
set -euo pipefail
cd "$(dirname "$0")"

TMP="$(mktemp -d)"
MASTER="$TMP/icon_1024.png"
ICONSET="$TMP/AppIcon.iconset"
mkdir -p "$ICONSET" Icon

echo "▶ Rendering master…"
swift Icon/make-icon.swift "$MASTER"
cp "$MASTER" Icon/icon-1024.png   # keep a preview/reference copy

echo "▶ Generating iconset sizes…"
for s in 16 32 128 256 512; do
  sips -z "$s" "$s" "$MASTER" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  s2=$(( s * 2 ))
  sips -z "$s2" "$s2" "$MASTER" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done

echo "▶ Compiling .icns…"
iconutil -c icns "$ICONSET" -o Icon/AppIcon.icns
echo "✓ Icon/AppIcon.icns"
