#!/bin/sh
# Build jev-client in release mode and install it as ~/.local/bin/jev-client.
# Build caches go to JEV_CLIENT_BUILD_DIR (default /Volumes/eyedisk/build/jev-client/release).
set -eu
package_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build_dir=${JEV_CLIENT_BUILD_DIR:-/Volumes/eyedisk/build/jev-client/release}
install_dir=${JEV_CLIENT_INSTALL_DIR:-$HOME/.local/bin}
swift build -c release --package-path "$package_dir" --scratch-path "$build_dir"
mkdir -p "$install_dir"
install -m 0755 "$build_dir/release/jev-client" "$install_dir/jev-client"
codesign --force --sign - --identifier local.jev-client "$install_dir/jev-client"
printf '%s\n' "$install_dir/jev-client"
