#!/bin/sh
set -eu
umask 077

skill_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin_dir="$skill_dir/bin"
bundle="$bin_dir/MacPilot.app"

if [ -L "$bin_dir" ] || [ -L "$bundle" ]; then
    printf '%s\n' 'Refusing to install through a symbolic link' >&2
    exit 1
fi
/bin/mkdir -p "$bin_dir"

build_root=$(/usr/bin/mktemp -d "${TMPDIR:-/tmp}/macpilot-build.XXXXXX")
install_root=$(/usr/bin/mktemp -d "$bin_dir/.macpilot-install.XXXXXX")
staged_bundle="$install_root/MacPilot.app"
cleanup() {
    /bin/rm -rf -- "$build_root" "$install_root"
}
trap cleanup EXIT HUP INT TERM

# A private scratch directory prevents a prior SwiftPM product from entering the
# installed bundle. The current bundle stays untouched until the staged app is
# signed and strictly verified.
/bin/mkdir -p "$staged_bundle/Contents/MacOS"
archs=$(/usr/bin/uname -m)
if [ "${MACPILOT_UNIVERSAL:-0}" = 1 ]; then archs="arm64 x86_64"; fi
for arch in $archs; do
    for product in macpilot macpilot-simulator-hid; do
        /usr/bin/xcrun swift build --package-path "$skill_dir/tool" \
            --scratch-path "$build_root/$arch" --configuration release \
            --triple "$arch-apple-macosx14.0" --product "$product" >&2
    done
    product_dir=$(/usr/bin/xcrun swift build --package-path "$skill_dir/tool" \
        --scratch-path "$build_root/$arch" --configuration release \
        --triple "$arch-apple-macosx14.0" --show-bin-path)
    for product in macpilot macpilot-simulator-hid; do
        /bin/cp "$product_dir/$product" "$build_root/$product-$arch"
    done
done
for product in macpilot macpilot-simulator-hid; do
    if [ "${MACPILOT_UNIVERSAL:-0}" = 1 ]; then
        /usr/bin/lipo -create "$build_root/$product-arm64" "$build_root/$product-x86_64" \
            -output "$staged_bundle/Contents/MacOS/$product"
    else
        /bin/cp "$build_root/$product-$archs" "$staged_bundle/Contents/MacOS/$product"
    fi
    /bin/chmod 0755 "$staged_bundle/Contents/MacOS/$product"
    /usr/bin/codesign --force --sign - --identifier "local.$product" "$staged_bundle/Contents/MacOS/$product" >&2
done

# Bundle the same native app icon used by Finder and the permission drag panel.
iconset="$build_root/MacPilot.iconset"
/bin/mkdir -p "$iconset" "$staged_bundle/Contents/Resources"
/bin/mkdir -p "$staged_bundle/Contents/Resources/ImageSearch"
/bin/cp "$skill_dir/runtime/image_search_worker.py" "$skill_dir/runtime/embeddinggemma2-manifest.json" \
    "$skill_dir/runtime/requirements-image-search.txt" "$staged_bundle/Contents/Resources/ImageSearch/"
for size in 16 32 128 256 512; do
    /usr/bin/sips -z "$size" "$size" "$skill_dir/assets/app-icon.png" \
        --out "$iconset/icon_${size}x${size}.png" >/dev/null
    pixels=$((size * 2))
    /usr/bin/sips -z "$pixels" "$pixels" "$skill_dir/assets/app-icon.png" \
        --out "$iconset/icon_${size}x${size}@2x.png" >/dev/null
done
/usr/bin/iconutil -c icns "$iconset" \
    -o "$staged_bundle/Contents/Resources/MacPilot.icns"

/bin/cat > "$staged_bundle/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>local.macpilot</string>
<key>CFBundleExecutable</key><string>macpilot</string>
<key>CFBundleName</key><string>MacPilot</string>
<key>CFBundleIconFile</key><string>MacPilot.icns</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>3.5.0</string>
<key>CFBundleVersion</key><string>36</string>
<key>LSMinimumSystemVersion</key><string>14.0</string>
<key>LSUIElement</key><true/>
<key>NSHighResolutionCapable</key><true/>
<key>NSAppleEventsUsageDescription</key><string>MacPilot uses Apple Events only for an explicitly requested automation task.</string>
<key>NSScreenCaptureUsageDescription</key><string>MacPilot captures explicitly selected windows or displays for observation and verification.</string>
<key>NSAudioCaptureUsageDescription</key><string>MacPilot records system audio only with an explicitly requested screen recording. Microphone audio is not captured.</string>
</dict></plist>
PLIST
/usr/bin/plutil -lint "$staged_bundle/Contents/Info.plist" >&2
/usr/bin/codesign --force --sign - --identifier local.macpilot "$staged_bundle" >&2
/usr/bin/codesign --verify --strict "$staged_bundle" >&2

swap_bundles() {
    "$staged_bundle/Contents/MacOS/macpilot-simulator-hid" --swap-bundles "$1" "$2"
}

if [ -e "$bundle" ]; then
    if [ ! -d "$bundle" ]; then
        printf '%s\n' 'Existing MacPilot.app is not a directory' >&2
        exit 1
    fi
    # renamex_np(RENAME_SWAP) replaces a live installation in one filesystem
    # operation. A process already using the old executable can finish safely.
    swap_bundles "$staged_bundle" "$bundle"
    if ! /usr/bin/codesign --verify --strict "$bundle" >&2; then
        printf '%s\n' 'Installed bundle verification failed; restoring the prior bundle' >&2
        "$bundle/Contents/MacOS/macpilot-simulator-hid" --swap-bundles "$staged_bundle" "$bundle"
        exit 1
    fi
else
    /bin/mv "$staged_bundle" "$bundle"
    /usr/bin/codesign --verify --strict "$bundle" >&2
fi

printf '%s\n' "$bundle/Contents/MacOS/macpilot"
