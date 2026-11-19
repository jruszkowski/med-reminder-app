#!/bin/bash
# Generates MedicationReminder.xcodeproj from project.yml and opens it in Xcode.
# Works without admin rights: downloads XcodeGen into ~/.xcodegen if it isn't installed.
set -euo pipefail
cd "$(dirname "$0")"

if command -v xcodegen >/dev/null 2>&1; then
  XCODEGEN=xcodegen
else
  XCODEGEN="$HOME/.xcodegen/xcodegen/bin/xcodegen"
  if [ ! -x "$XCODEGEN" ]; then
    echo "Downloading XcodeGen..."
    mkdir -p "$HOME/.xcodegen"
    curl -fsSL -o "$HOME/.xcodegen/xcodegen.zip" \
      https://github.com/yonaskolb/XcodeGen/releases/latest/download/xcodegen.zip
    unzip -q -o "$HOME/.xcodegen/xcodegen.zip" -d "$HOME/.xcodegen"
  fi
fi

"$XCODEGEN" generate
open MedicationReminder.xcodeproj
