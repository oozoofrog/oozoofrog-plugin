#!/usr/bin/env bash
set -euC
cat > package-notes.md <<'EOF'
# Package notes

The upstream pstack package contains a prototype workflow for comparing runnable alternatives, a benchmark checklist that asks what limited the measurement, and workflows for formal verification and parallel review.
The fstack package bundles those workflows alongside host profiles, a project journal convention and a checker that links numbered acceptance criteria to plans and test names.
EOF
