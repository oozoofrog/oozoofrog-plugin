#!/usr/bin/env python3
"""Compatibility entry point for session-bound visible input verification.

The shared runner retains delayed-host/no-input, transparent-panel/mouse-pass,
normal release, task cancellation and host-loss cleanup coverage. It also checks
explicit focused handoff and persistent idle revocation. AX acceptance is owned
fixture automation, not a human-consent claim.
"""
import os
from pathlib import Path
import sys

runner = Path(__file__).with_name('verify_control_handoff.py')
os.execv(sys.executable, [sys.executable, str(runner), *sys.argv[1:]])
