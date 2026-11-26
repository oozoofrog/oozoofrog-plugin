#!/usr/bin/env bash
set -euC
cat > timing.md <<'EOF'
# Timing sample
Old and new implementations read the same input. One run each.
Old: 820 ms, empty filesystem cache.
New: 210 ms, immediately after the old run, input still cached.
No other samples or source files are available.
EOF
