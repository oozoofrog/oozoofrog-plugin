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


def legacy_run(project, name, actor):
    """Explicit 0.2 fixture: no approval marker/identity anywhere in its history."""
    run = store.init_run(project, name, actor)
    events = store.events(run)
    events[0]["data"] = {"run_id": name, "project_root": str(project.resolve()), "schema_version": 1}
    (run / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    return run


def approve_current_plan(run):
    """Explicit consent for low-level execution fixtures that write plan events directly."""
    with store.transaction(run) as tx:
        identity = state.plan_identity(tx.plan)
        recorded = next(e['data'] for e in reversed(tx.events) if e['type'] == 'plan.set')
        tx.append('plan.set', dict(recorded, plan_identity=identity), {'role':'leader'})
        data = {'purpose':'plan_approval', 'kind':'authorization', 'plan_identity':identity,
                'question':'Approve test plan?', 'evidence':{'command':None,'files':[],'checks':[]}}
        ev = tx.append('decision.ask', data, {'role':'leader'})
        data['id'] = 'd%d' % ev['seq']
    return human_answer(run, data['id'], 'approved', 'Reviewed fixture')


def refresh_contract(run, **fields):
    """Freeze changed run-level instructions and approve the new test contract."""
    from graphflow import learn
    with store.transaction(run) as tx:
        current = dict(tx.plan)
        current['promoted_checks'] = fields.get('promoted_checks') if 'promoted_checks' in fields else learn.fixed_checks(store.project_of(run))
        current['constraints'] = fields.get('constraints') if 'constraints' in fields else learn.applying(store.project_of(run), current)
        current.update(fields)
        rev, sha = tx.write_plan(current)
        tx.append('plan.set', {'revision':rev, 'plan_sha256':sha,
                  'plan_identity':state.plan_identity(current),
                  'fingerprints':{n['id']:state.fingerprint(n) for n in current['nodes']}}, {'role':'leader'})
    approve_current_plan(run)
