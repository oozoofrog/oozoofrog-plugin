#!/bin/sh
# Download the exact published runtime. Uses only programs included with macOS.
set -eu
umask 077
skill_dir=$(CDPATH= cd -- "$(/usr/bin/dirname -- "$0")/.." && pwd)
manifest="$skill_dir/runtime/distribution.json"
version=$(/usr/bin/plutil -extract version raw "$manifest")
asset=$(/usr/bin/plutil -extract asset raw "$manifest")
main_sha=$(/usr/bin/plutil -extract mainSHA256 raw "$manifest")
helper_sha=$(/usr/bin/plutil -extract helperSHA256 raw "$manifest")
case $version in *[!0-9.]*|'') exit 1;; esac
case $asset in "MacPilot-$version-macos-universal.zip") ;; *) exit 1;; esac
for hash in "$main_sha" "$helper_sha"; do
    [ "${#hash}" -eq 64 ] || { printf '%s\n' 'Published runtime hashes are missing. Use build.sh only for explicit source development.' >&2; exit 1; }
    case $hash in *[!0-9a-f]*) exit 1;; esac
done
bin="$skill_dir/bin"; bundle="$bin/MacPilot.app"
[ ! -L "$bin" ] && [ ! -L "$bundle" ] || { printf '%s\n' 'Refusing symbolic-link runtime destination' >&2;exit 1; }
/bin/mkdir -p "$bin"
verify() {
    selected=$1
    [ -d "$selected" ] && [ ! -L "$selected/Contents/MacOS/macpilot" ] && [ ! -L "$selected/Contents/MacOS/macpilot-simulator-hid" ] || return 1
    [ "$(/usr/bin/plutil -extract CFBundleShortVersionString raw "$selected/Contents/Info.plist")" = "$version" ] || return 1
    [ "$(/usr/bin/shasum -a 256 "$selected/Contents/MacOS/macpilot" | /usr/bin/cut -d ' ' -f 1)" = "$main_sha" ] || return 1
    [ "$(/usr/bin/shasum -a 256 "$selected/Contents/MacOS/macpilot-simulator-hid" | /usr/bin/cut -d ' ' -f 1)" = "$helper_sha" ] || return 1
    /usr/bin/codesign --verify --deep --strict "$selected" >&2
}
if verify "$bundle" 2>/dev/null; then exit 0; fi
lock="$bin/.runtime-install.lock"
if ! /bin/mkdir "$lock" 2>/dev/null; then
    printf '%s\n' 'Another runtime installation owns the lock. Reconcile that installer before retrying.' >&2;exit 1
fi
stage=$(/usr/bin/mktemp -d "$bin/.runtime.XXXXXX")
cleanup() { /bin/rm -rf -- "$stage"; /bin/rmdir "$lock"; }
trap cleanup EXIT HUP INT TERM
url="https://github.com/oozoofrog/oozoofrog-plugin/releases/download/macpilot-v$version/$asset"
printf 'Downloading MacPilot %s prebuilt runtime\n' "$version" >&2
/usr/bin/curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 --max-time 180 \
    --output "$stage/runtime.zip" "$url" >&2
/usr/bin/ditto -x -k "$stage/runtime.zip" "$stage/unpacked"
new="$stage/unpacked/MacPilot.app"
verify "$new" || { printf '%s\n' 'Runtime hash/signature verification failed' >&2;exit 1; }
if [ -e "$bundle" ]; then
    [ -d "$bundle" ] || exit 1
    "$new/Contents/MacOS/macpilot-simulator-hid" --swap-bundles "$new" "$bundle"
    if ! verify "$bundle"; then
        "$bundle/Contents/MacOS/macpilot-simulator-hid" --swap-bundles "$new" "$bundle"
        exit 1
    fi
else
    /bin/mv "$new" "$bundle"
fi
