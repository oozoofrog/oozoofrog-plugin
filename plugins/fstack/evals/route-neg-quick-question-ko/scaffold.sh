#!/usr/bin/env bash
# Delegates to the shared fixture. Writes only inside the run's workspace.
set -euo pipefail
exec bash "$(dirname "$0")/../_fixtures/pager-repo.sh"
