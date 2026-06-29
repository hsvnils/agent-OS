#!/usr/bin/env bash
# Baut den LUNA-Orb als echtes macOS-.app-Bundle (Info.plist in Contents/), damit macOS-TCC
# die Mikrofon-/Spracherkennungs-Berechtigungen findet (sonst Crash beim ersten Zugriff).
# Aufruf:  ./build_app.sh [debug|release]   (Default: release)
set -euo pipefail
cd "$(dirname "$0")"

CONFIG="${1:-release}"
APP="LunaOrb.app"

echo "==> swift build (-c $CONFIG)"
swift build -c "$CONFIG"
BIN=".build/$CONFIG/LunaOrb"

echo "==> Bundle $APP zusammensetzen"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
cp "$BIN" "$APP/Contents/MacOS/LunaOrb"
cp Info.plist "$APP/Contents/Info.plist"
printf 'APPL????' > "$APP/Contents/PkgInfo"

echo "==> Ad-hoc-Signatur (stabile TCC-Identitaet)"
codesign --force --sign - "$APP"

echo "==> fertig: $APP"
echo "    Starten:  open $APP"
