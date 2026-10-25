#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

LABEL="${LABEL:-com.oozoofrog.codex-skills-autosync}"
INTERVAL="${INTERVAL:-15}"
DEBOUNCE="${DEBOUNCE:-20}"
RETRY_COOLDOWN="${RETRY_COOLDOWN:-120}"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"

usage() {
  cat <<'EOF'
Usage: ./scripts/install_auto_sync_launchd.sh [options]

Options:
  --label <value>           launchd label
  --interval <seconds>      git status polling interval
  --debounce <seconds>      stable change wait time before sync
  --retry-cooldown <sec>    failed sync retry cooldown
  --python-bin <path>       python3 executable path
  --help                    show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --label)
      LABEL="${2:?missing label value}"
      shift 2
      ;;
    --interval)
      INTERVAL="${2:?missing interval value}"
      shift 2
      ;;
    --debounce)
      DEBOUNCE="${2:?missing debounce value}"
      shift 2
      ;;
    --retry-cooldown)
      RETRY_COOLDOWN="${2:?missing retry cooldown value}"
      shift 2
      ;;
    --python-bin)
      PYTHON_BIN="${2:?missing python path}"
      shift 2
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "python3 not found in PATH." >&2
  exit 1
fi

PLIST_DIR="${HOME}/Library/LaunchAgents"
PLIST_PATH="${PLIST_DIR}/${LABEL}.plist"
LOG_DIR="${HOME}/Library/Logs"
STDOUT_LOG="${LOG_DIR}/${LABEL}.out.log"
STDERR_LOG="${LOG_DIR}/${LABEL}.err.log"

mkdir -p "${PLIST_DIR}" "${LOG_DIR}"

"${PYTHON_BIN}" - "${PLIST_PATH}" "${LABEL}" "${PYTHON_BIN}" "${REPO_ROOT}" \
  "${INTERVAL}" "${DEBOUNCE}" "${RETRY_COOLDOWN}" "${STDOUT_LOG}" "${STDERR_LOG}" <<'PYTHON'
import plistlib
import sys

path, label, python, root, interval, debounce, cooldown, stdout, stderr = sys.argv[1:]
config = {
    "Label": label,
    "ProgramArguments": [python, root + "/scripts/auto_sync_daemon.py",
                         "--repo-root", root, "--sync-script", root + "/scripts/sync_repo.sh",
                         "--interval", interval, "--debounce", debounce, "--retry-cooldown", cooldown],
    "RunAtLoad": True,
    "KeepAlive": True,
    "WorkingDirectory": root,
    "ProcessType": "Background",
    "StandardOutPath": stdout,
    "StandardErrorPath": stderr,
}
with open(path, "wb") as output:
    plistlib.dump(config, output)
PYTHON

plutil -lint "${PLIST_PATH}" >/dev/null

launchctl bootout "gui/$(id -u)/${LABEL}" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "${PLIST_PATH}"
launchctl kickstart -k "gui/$(id -u)/${LABEL}"

cat <<EOF
Installed launchd auto-sync job.

- Label: ${LABEL}
- Plist: ${PLIST_PATH}
- Stdout log: ${STDOUT_LOG}
- Stderr log: ${STDERR_LOG}

Useful commands:
  launchctl print gui/$(id -u)/${LABEL}
  tail -f ${STDOUT_LOG}
  tail -f ${STDERR_LOG}
EOF
