#!/bin/sh
set -eu
printf '%s\n' 'SWIFTLINT_RUN'
tool="${SRCROOT}/.tools/swiftlint"
if [ ! -f "$tool" ]; then
    echo 'error: SwiftLint executable is missing' >&2
    exit 127
fi
if [ ! -x "$tool" ]; then
    echo 'error: SwiftLint executable is not executable' >&2
    exit 126
fi
cd "$SRCROOT"
"$tool" version
exec "$tool" lint --no-cache --config "$SRCROOT/.swiftlint.yml" "$SRCROOT/Sources/main.swift"
