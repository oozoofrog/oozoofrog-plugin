"""Every dispatch surface against every plan-approval state, CLI and MCP.

This table is the fixed statement of "nothing unapproved is handed out or
accepted through ordinary commands". A refusal writes nothing, with one
intended exception: observing a moved project records the supersession of the
approval it invalidates, so moving back cannot revive it.
"""
import contextlib
import io
import json
import subprocess
import unittest

import test_plan_approval as fixture
from graphflow import cli, mcp, store
from human_support import human_answer

ASSIGN = dict(node='a', executor='inline', model='test', effort='high',
              provider='test', family='openai', isolation='shared')
ROWS = [
    ('ready', ('ready',), 'ready_nodes', {}),
    ('route', ('route', 'a'), 'route_node', {'node': 'a'}),
    ('assign', ('assign', 'a', '--executor', 'inline', '--model', 'test', '--effort', 'high',
                '--provider', 'test', '--family', 'openai', '--isolation', 'shared'),
     'assign_node', ASSIGN),
    ('brief', ('brief', 'a'), 'node_brief', {'node': 'a'}),
    ('start', ('start', 'a'), 'node_start', {'node': 'a'}),
    ('submit', ('submit', 'a'), 'node_submit', {'node': 'a'}),
    ('gate', ('gate', 'a'), 'gate_node', {'node': 'a'}),
    ('final', ('gate', '--final'), 'gate_node', {'final': True}),
    ('merge', ('merge', 'a'), 'merge_nodes', {'nodes': ['a']}),
    ('reopen', ('reopen', 'a', '--reason', 'Revisit'), 'node_reopen',
     {'node': 'a', 'reason': 'Revisit'}),
]
STATES = ['none', 'open', 'sent_back', 'structural', 'wording', 'moved', 'approved']
# A running attempt may always be handed in, and a finished node may always be
# reopened: both are continuation or recovery, neither hands out or accepts work.
ALWAYS_ALLOWED = {'submit', 'reopen'}
PNA, MOVED, ALLOWED = 'plan_not_approved', 'project_moved', 'ALLOWED'


def expected(command, approval):
    if command in ALWAYS_ALLOWED or approval in ('wording', 'approved'):
        return ALLOWED
    return MOVED if approval == 'moved' else PNA


class DispatchMatrixTests(unittest.TestCase):
    call = fixture.PlanApprovalTests.call
    set_plan = fixture.PlanApprovalTests.set_plan
    accept = fixture.PlanApprovalTests.accept

    def arrange(self, command, approval):
        self.accept(self.set_plan()['decision'])
        if command in ('submit', 'gate', 'final', 'merge', 'reopen'):
            self.call('start', 'a')
            (self.project / 'guide.txt').write_text('Guide')
        if command == 'merge':
            git = ['git', '-C', str(self.project)]
            subprocess.run(git + ['add', 'guide.txt'], check=True)
            subprocess.run(git + ['-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                                  'commit', '-qm', 'result'], check=True)
            commit = subprocess.check_output(git + ['rev-parse', 'HEAD'], text=True).strip()
            self.call('submit', 'a', '--commit', commit)
        elif command in ('gate', 'final', 'reopen'):
            self.call('submit', 'a')
        if command in ('final', 'reopen'):
            self.call('gate', 'a')
        if approval == 'none':
            events = store.events(self.run)
            for event in events:
                if event['type'] in ('decision.ask', 'decision.answer'):
                    event['type'] = 'fixture.absent'
            (self.run / 'events.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
        elif approval in ('open', 'sent_back', 'structural'):
            self.raw['goal'] = 'Revised run goal'
            new = self.set_plan()['decision']
            if approval == 'sent_back':
                human_answer(self.run, new, 'revision_requested', 'Revise scope')
        elif approval == 'wording':
            self.raw['title'] = 'Updated wording'
            self.set_plan()
        elif approval == 'moved':
            target = self.root / 'moved'
            self.project.rename(target)
            self.project = target
            self.run = (target / '.graph-flow/runs/approval').resolve()

    def invoke(self, surface, args, tool, params):
        if surface == 'cli':
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cli.main(['--json', '--run', str(self.run), *args])
            return json.loads(out.getvalue())
        response = mcp._call(mcp.TOOLS[tool], dict(run=str(self.run), **params))
        return json.loads(response['content'][0]['text'])

    def test_every_surface_in_every_approval_state(self):
        cells = 0
        for surface in ('cli', 'mcp'):
            for command, args, tool, params in ROWS:
                for approval in STATES:
                    with self.subTest(surface=surface, command=command, approval=approval):
                        fixture.PlanApprovalTests.setUp(self)
                        try:
                            self.arrange(command, approval)
                            before = len(store.events(self.run))
                            result = self.invoke(surface, args, tool, params)
                            outcome = ALLOWED if result.get('ok') else result.get('code')
                            self.assertEqual(outcome, expected(command, approval))
                            added = [e['type'] for e in store.events(self.run)[before:]]
                            if outcome == MOVED:
                                self.assertEqual(set(added), {'decision.superseded'})
                            elif outcome != ALLOWED:
                                self.assertEqual(added, [])
                        finally:
                            self.doCleanups()
                    cells += 1
        self.assertEqual(cells, 140)


if __name__ == '__main__':
    unittest.main()
