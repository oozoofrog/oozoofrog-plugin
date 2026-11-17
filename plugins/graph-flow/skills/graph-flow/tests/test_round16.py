"""Human-path observations and wording revisions, without extra approval stops."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import unittest
from unittest import mock

import test_plan_approval as fixture
from graphflow import checks, cli, core, gate, mcp, plan, server, state, store, trace
from human_support import human_answer

CAPTURE = os.environ.get('ROUND16_CAPTURE')


class MetricsTests(unittest.TestCase):
    setUp = fixture.PlanApprovalTests.setUp
    call = fixture.PlanApprovalTests.call
    set_plan = fixture.PlanApprovalTests.set_plan
    snapshot = fixture.PlanApprovalTests.snapshot
    accept = fixture.PlanApprovalTests.accept

    def test_conformance_human_answers_waits_and_mcp(self):
        with mock.patch.object(store, 'now', return_value='2026-11-17T00:00:00Z'):
            did = self.set_plan()['decision']
        with mock.patch.object(store, 'now', return_value='2026-11-17T00:00:10Z'):
            self.accept(did)
        with mock.patch.object(store, 'now', return_value='2026-11-17T00:00:12Z'):
            free = self.call('decide', 'ask', '--kind', 'information', '--question', 'Which audience?')['id']
        with mock.patch.object(store, 'now', return_value='2026-11-17T00:00:42Z'):
            human_answer(self.run, free, 'answered', 'Maintainers')
        with mock.patch.object(store, 'now', return_value='2026-11-17T00:00:45Z'):
            opened = self.call('decide', 'ask', '--kind', 'direction', '--question', 'Next?')['id']
        before = store.events(self.run)
        result = self.call('trace', '--conformance')
        self.assertEqual(result['human']['answers']['total'], 2)
        self.assertEqual(result['human']['answers']['planned'], 1)
        self.assertEqual(result['human']['answers']['unplanned'], 1)
        self.assertEqual(result['human']['answers']['by_kind']['free'], 1)
        self.assertEqual(result['human']['wait']['total_ms'], 40000)
        self.assertEqual(result['human']['wait']['longest_ms'], 30000)
        self.assertEqual(result['human']['wait']['open'], [opened])
        self.assertEqual(result['stuck']['refusals'], 'not measurable from records')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(cli.main(['--run', str(self.run), 'trace', '--conformance']), 0)
        self.assertEqual(len(output.getvalue().splitlines()), 12)
        self.assertIn('human answers 2 (planned 1, unplanned 1); waited 0m40s', output.getvalue())
        called = mcp._call(mcp.TOOLS['run_trace'], {'run': str(self.run), 'conformance': True})
        self.assertFalse(called.get('isError'))
        self.assertEqual(json.loads(called['content'][0]['text'])['conformance'], result['conformance'])
        self.assertEqual(store.events(self.run), before)
        if CAPTURE:
            Path(CAPTURE).write_text(output.getvalue() + '\n' + json.dumps(result, ensure_ascii=False, indent=2) + '\n')

    def test_all_human_kinds_and_superseded_waits(self):
        # Historical activity is counted from records, not re-authorized today.
        events = []
        def event(kind, data, role='tool'):
            events.append({'seq': len(events)+1, 'ts': '2026-11-17T00:00:%02dZ' % len(events),
                           'type': kind, 'data': data, 'actor': {'role': role}})
        purposes = [('plan', 'plan_approval'), ('gate', 'node'), ('gate', 'lane3'),
                    ('gate', 'human_check'), ('gate', 'hold'), ('gate', 'trajectory'), ('agent', 'free')]
        for issuer, purpose in purposes:
            for repeat in (False, True):
                event('decision.ask', {'id': str(len(events)), 'issuer': issuer, 'purpose': purpose, 'node': 'a'})
                did = events[-1]['data']['id']
                event('decision.answer', {'id': did}, 'human')
                event('decision.superseded', {'id': did, 'reason': 'evidence_changed'})
        result = trace.human_metrics(events, {'decisions': {}})
        self.assertEqual(result['answers']['total'], 14)
        self.assertEqual(result['answers']['planned'], 4)
        self.assertEqual(result['answers']['by_kind'], dict(plan_approval=1, decision_node=1, lane3=1,
            human_check=1, hold=1, trajectory=1, evidence_reask=5, plan_reapproval=1, reask=0, free=2))
        self.assertEqual(result['wait']['total_ms'], 14000)
        event('decision.answer', {'id': did}, 'human')
        self.assertEqual(trace.human_metrics(events, {'decisions': {}}), result)

    def test_red_and_prior_failure_are_bound_to_node_and_command(self):
        self.accept(self.set_plan()['decision'])
        self.call('assign', 'a', '--executor', 'inline', '--model', 'test-model', '--effort', 'high',
                  '--provider', 'test', '--family', 'openai', '--isolation', 'shared')
        self.call('start', 'a')
        self.call('red', 'a', 'text')
        (self.project / 'guide.txt').write_text('Guide')
        passed = self.call('check', 'run', 'a', 'text')
        self.assertTrue(passed['failed_before'])
        result = self.call('trace')
        node = result['nodes']['a']
        self.assertEqual((node['executor'], node['model'], node['attempts']), ('inline', 'test-model', 1))
        self.assertTrue(node['cmd_checks']['text']['red_recorded'])
        self.assertTrue(node['cmd_checks']['text']['passes'][0]['failed_before'])
        self.assertFalse(checks.failure_observed(store.events(self.run), 'other', 'test -s guide.txt', self.run))
        self.assertFalse(checks.failure_observed(store.events(self.run), 'a', 'true', self.run))
        # Legacy red rows have no command: recover it from their immutable revision.
        red = next(e for e in store.events(self.run) if e['type'] == 'check.red')
        red['data'].pop('command')
        self.assertEqual(checks.recorded_command(red, self.run), 'test -s guide.txt')

    def test_prior_failed_attempt_and_never_failed_pass_do_not_change_gate(self):
        self.accept(self.set_plan()['decision'])
        self.call('start', 'a')
        self.call('check', 'run', 'a', 'text', code=1)
        self.call('submit', 'a'); self.call('gate', 'a', code=1)
        self.call('start', 'a')
        (self.project / 'guide.txt').write_text('Guide')
        self.assertTrue(self.call('check', 'run', 'a', 'text')['failed_before'])
        self.call('submit', 'a'); self.call('gate', 'a')
        self.assertFalse(self.call('trace')['nodes']['a']['cmd_checks']['text']['red_recorded'])
        self.run = store.init_run(self.project, 'green', {'role': 'leader'})
        self.accept(self.set_plan()['decision']); self.call('start', 'a')
        self.assertFalse(self.call('check', 'run', 'a', 'text')['failed_before'])
        self.call('submit', 'a'); self.call('gate', 'a')
        self.assertEqual(self.call('trace')['conformance']['P1']['passed_checks_never_observed_failing'], 1)

    def test_trivial_checks_are_notices_in_validate_and_set(self):
        for index, command in enumerate((' true ', ':', 'exit 0', '', '  ', 'test -f guide.txt')):
            with self.subTest(command=command):
                self.raw['nodes'][0]['checks'][0]['run'] = command
                self.file.write_text(json.dumps(self.raw))
                result = self.call('plan', 'validate', str(self.file))
                notices = [n for n in result['notices'] if n['code'] == 'unfalsifiable_check']
                self.assertEqual(len(notices), int(index < 5))
                result = self.set_plan()
                self.assertEqual(result['normalization_notices'], notices)
