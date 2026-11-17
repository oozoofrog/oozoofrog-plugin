"""Test-only human terminal: isolated GF_HOME, real CLI role checks and signing."""
import contextlib
import io
import json
import os
from pathlib import Path
from unittest import mock
from graphflow import cli, state, store


def approve_plan(run):
    with store.transaction(run) as tx:
        approval = state.plan_approval(state.derive(tx.plan, tx.events))
    if approval and approval["status"] == "open":
        return human_answer(run, approval["id"], "approved", "계획을 확인했어요.")


def human_answer(run, decision, outcome, answer):
    assert os.environ.get("GF_HOME") and Path(os.environ["GF_HOME"]).resolve() != Path.home() / ".graph-flow"
    out = io.StringIO()
    with mock.patch.dict(os.environ, {"GF_HUMAN_TERMINAL": "1"}), mock.patch("sys.stdin.isatty", return_value=True), contextlib.redirect_stdout(out):
        code = cli.main(["--json", "--run", str(run), "--role", "human", "decide", "answer", decision, "--outcome", outcome, "--answer", answer])
    result = json.loads(out.getvalue())
    assert code == 0, result
    return result
