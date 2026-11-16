"""Errors, exit codes, actor identity, clock and home directory."""
import hashlib
import hmac
import os
import pathlib
from datetime import datetime, timezone

EXIT_OK = 0
EXIT_NEGATIVE = 1
EXIT_USAGE = 2
EXIT_FORBIDDEN = 3
EXIT_STATE = 4
EXIT_IO = 5

ROLES = ("leader", "worker", "reviewer", "human")


class GFError(Exception):
    def __init__(self, code, message, exit_code=EXIT_USAGE):
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


def actor_from_env(role=None, node=None):
    role = role or os.environ.get("GF_ROLE") or "leader"
    if role not in ROLES:
        raise GFError("bad_role", "unknown role: %s" % role, EXIT_USAGE)
    return {
        "role": role,
        "node": node or os.environ.get("GF_NODE") or None,
        "session": os.environ.get("GF_SESSION") or None,
    }


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gf_home():
    env = os.environ.get("GF_HOME")
    if env:
        return pathlib.Path(env)
    return pathlib.Path.home() / ".graph-flow"


def human_sig(run_id, decision_id, outcome, answer_text):
    """HMAC-SHA256 hex over the answer, keyed with $GF_HOME/human.key; None when unreadable."""
    try:
        key = (gf_home() / "human.key").read_bytes()
    except OSError:
        return None
    if not key:
        return None
    message = "\n".join([str(run_id), str(decision_id), str(outcome), answer_text or ""])
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()
