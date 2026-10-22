#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"
if [ "${JEV_REDACT_BUILD_PATHS:-0}" = "1" ]; then
    # Skill lookup is portable at runtime. Strip debug data before public signing.
    swift build -c release -Xswiftc -gnone
else
    swift build -c release
fi
app_dir="$project_dir/dist/JevNative.app"
mkdir -p "$app_dir/Contents/MacOS"
cp .build/release/jev-native "$app_dir/Contents/MacOS/jev-native"
if [ "${JEV_REDACT_BUILD_PATHS:-0}" = "1" ]; then
    strip -S "$app_dir/Contents/MacOS/jev-native"
fi
mkdir -p "$app_dir/Contents/Resources/skills/jev-native"
cp "$project_dir/skill/jev-native/SKILL.md" "$app_dir/Contents/Resources/skills/jev-native/SKILL.md"
cp "$project_dir/Assets/JevNative.icns" "$app_dir/Contents/Resources/JevNative.icns"
cat > "$app_dir/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>com.oozoofrog.JevComputerUse</string>
<key>CFBundleName</key><string>JEV Native</string>
<key>CFBundleDisplayName</key><string>JEV Native</string>
<key>CFBundleExecutable</key><string>jev-native</string>
<key>CFBundleIconFile</key><string>JevNative.icns</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleVersion</key><string>11</string>
<key>CFBundleShortVersionString</key><string>0.6.3</string>
<key>LSMinimumSystemVersion</key><string>14.0</string>
<key>NSPrincipalClass</key><string>NSApplication</string>
</dict></plist>
PLIST
codesign --force --sign - "$app_dir"
printf '%s\n' "$app_dir/Contents/MacOS/jev-native"
