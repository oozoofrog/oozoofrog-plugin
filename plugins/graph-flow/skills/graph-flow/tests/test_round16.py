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
from test_review11 import NODE

CAPTURE = os.environ.get('ROUND16_CAPTURE')


class MetricsTests(unittest.TestCase):
    setUp = fixture.PlanApprovalTests.setUp
    call = fixture.PlanApprovalTests.call
    set_plan = fixture.PlanApprovalTests.set_plan
    snapshot = fixture.PlanApprovalTests.snapshot
    accept = fixture.PlanApprovalTests.accept

    def test_conformance_human_answers_waits_and_mcp(self):
        with mock.patch.object(store, 'now', return_value='2026-11-17T00:00:00Z'):
            self.run = store.init_run(self.project, 'timed', {'role': 'leader'})
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

    def test_conformance_attempt_budget_does_not_sum_reopened_attempts(self):
        self.accept(self.set_plan()['decision'])
        with store.transaction(self.run) as tx:
            for attempt in (1, 2, 1):
                tx.append('node.start', {'node': 'a', 'attempt': attempt}, {'role': 'leader'})
        result = self.call('trace', '--conformance')['conformance']
        self.assertEqual(result['P2']['max_attempts'], 2)
        self.assertEqual(result['P12']['attempts'], 3)

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

    def test_run_level_checks_include_failure_history(self):
        self.raw['integration_checks'] = [{'id': 'all', 'type': 'cmd', 'run': 'test -s guide.txt'}]
        self.accept(self.set_plan()['decision'])
        self.assertFalse(self.call('gate', '--final', code=1)['result'] == 'passed')
        self.call('start', 'a'); (self.project / 'guide.txt').write_text('Guide')
        self.call('submit', 'a'); self.call('gate', 'a'); self.call('gate', '--final')
        observed = self.call('trace')['run_cmd_checks']['all']
        self.assertTrue(observed['failure_observed'])
        self.assertTrue(observed['passes'][0]['failed_before'])

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


class WordingTests(unittest.TestCase):
    setUp = fixture.PlanApprovalTests.setUp
    call = fixture.PlanApprovalTests.call
    set_plan = fixture.PlanApprovalTests.set_plan
    snapshot = fixture.PlanApprovalTests.snapshot
    accept = fixture.PlanApprovalTests.accept

    def test_wording_reuses_approval_updates_dashboard_and_logs_future_question(self):
        self.raw['nodes'][0]['checks'].append({'id': 'human', 'type': 'human', 'title': 'Accept draft?', 'context': {'why': 'Draft'}})
        self.raw['nodes'].append({'id': 'q', 'kind': 'decision', 'lane': 1, 'goal': 'Choose',
                                 'question': 'Which format?', 'decision_kind': 'direction'})
        approval = self.set_plan()['decision']; self.accept(approval)
        old_plan, _ = self.snapshot()
        self.raw['nodes'][0]['checks'][-1].update(title='Accept final draft?', context={'why': 'Updated draft'})
        self.raw['nodes'][1]['context'] = {'why': 'Choose final format'}
        self.raw['nodes'][0]['title'] = '새 안내 쓰기'
        self.raw['nodes'].reverse()
        before = store.events(self.run)
        result = self.set_plan()
        self.assertEqual(result['decision'], approval)
        self.assertEqual(result['revision'], 2)
        self.assertNotIn('show', result)
        current, derived = self.snapshot()
        self.assertEqual(state.plan_identity(old_plan), state.plan_identity(current))
        self.assertEqual({e['type'] for e in store.events(self.run)[len(before):]}, {'plan.set', 'constraint.apply'})
        self.call('ready')
        view = server._view(current, derived, store.events(self.run), self.project.resolve())
        self.assertEqual(next(n for n in view['nodes'] if n['id'] == 'a')['title'], '새 안내 쓰기')
        row = [r for r in view['timeline'] if r['kind'] == 'planned'][-1]
        self.assertTrue(row['wording_only'])
        self.assertEqual({r['node']: r['fields'] for r in row['question_wording_changed']},
                         {'a': ['checks.human.title', 'checks.human.context'], 'q': ['context']})
        # Execute the existing JS log renderer to check the visible revision line.
        import subprocess
        if not NODE:
            self.skipTest("Node.js unavailable for dashboard log renderer")
        source = (Path(__file__).parents[1] / 'scripts/graphflow/page.js').read_text()
        prelude = source[:source.index("if (typeof document !== 'undefined')")]
        translate = next(line for line in source.splitlines() if line.startswith('const t = '))
        renderer = 'function rowSentence' + source.split('function rowSentence', 1)[1].split('function rowTone', 1)[0]
        script = prelude + '\nlet language="ko";\n' + translate + '\n' + renderer + '\nconsole.log(rowSentence('+json.dumps(row, ensure_ascii=False)+'));'
        rendered = subprocess.run([NODE, '--input-type=module', '-e', script], text=True, capture_output=True, check=True).stdout
        self.assertIn('질문에 쓰일 문구가 바뀌었어요', rendered)
        self.assertIn('새 안내 쓰기', rendered); self.assertIn('Choose', rendered)
        self.assertNotIn('(a)', rendered); self.assertNotIn('(q)', rendered)
        self.assertIn('이전 계획 승인은 유지돼요', rendered)

    def test_explicit_prompt_title_is_only_a_label(self):
        self.raw['nodes'][0]['checks'].append({'id': 'human', 'type': 'human', 'title': 'Label', 'prompt': 'Accept?'})
        approval = self.set_plan()['decision']; self.accept(approval)
        self.raw['nodes'][0]['checks'][-1]['title'] = 'New label'
        self.assertEqual(self.set_plan()['decision'], approval)
        event = next(e for e in reversed(store.events(self.run)) if e['type'] == 'plan.set')
        self.assertEqual(event['data']['question_wording_changed'], [])
        self.call('ready')

    def test_open_and_answered_gate_questions_keep_text_then_supersede_at_gate(self):
        for purpose in ('human_title', 'human_context', 'decision_context'):
            for answered in (False, True):
                with self.subTest(purpose=purpose, answered=answered):
                    self.run = store.init_run(self.project, purpose + str(int(answered)), {'role': 'leader'})
                    if purpose == 'decision_context':
                        self.raw['nodes'] = [{'id': 'q', 'kind': 'decision', 'lane': 1, 'goal': 'Choose',
                                              'question': 'Choose format?', 'decision_kind': 'authorization'}]
                        node = 'q'
                    else:
                        self.raw['nodes'] = [{'id': 'a', 'kind': 'work', 'lane': 1, 'grade': 'daily', 'goal': 'Draft',
                            'owns': ['guide.txt'], 'checks': [{'id': 'cmd', 'type': 'cmd', 'run': 'true'},
                            {'id': 'human', 'type': 'human', 'title': 'Accept draft?'}]}]
                        node = 'a'
                    approval = self.set_plan()['decision']; self.accept(approval)
                    if node == 'a':
                        self.call('start', 'a'); self.call('submit', 'a')
                    old = self.call('gate', node, code=1)['asks'][0]
                    if answered: self.accept(old)
                    old_decision = copy.deepcopy(self.snapshot()[1]['decisions'][old])
                    if purpose == 'human_title': self.raw['nodes'][0]['checks'][-1]['title'] = 'Accept published draft?'
                    elif purpose == 'human_context': self.raw['nodes'][0]['checks'][-1]['context'] = {'why': 'Publication'}
                    else: self.raw['nodes'][0]['context'] = {'why': 'Publication'}
                    self.assertEqual(self.set_plan()['decision'], approval)
                    retained = self.snapshot()[1]['decisions'][old]
                    self.assertEqual(retained['question'], old_decision['question'])
                    self.assertEqual(retained['evidence'], old_decision['evidence'])
                    new = self.call('gate', node, code=1)['asks'][0]
                    self.assertNotEqual(new, old)
                    decisions = self.snapshot()[1]['decisions']
                    self.assertEqual(decisions[old]['status'], 'superseded')
                    self.assertEqual(decisions[new]['status'], 'open')
                    self.assertEqual([e['data']['reason'] for e in store.events(self.run)
                        if e['type'] == 'decision.superseded' and e['data']['id'] == old], ['evidence_changed'])


class IntegrityReadTests(unittest.TestCase):
    setUp = fixture.PlanApprovalTests.setUp
    call = fixture.PlanApprovalTests.call
    set_plan = fixture.PlanApprovalTests.set_plan
    snapshot = fixture.PlanApprovalTests.snapshot
    accept = fixture.PlanApprovalTests.accept

    def test_plan_tamper_reads_work_dispatch_refuses_and_repost_recovers(self):
        self.accept(self.set_plan()['decision'])
        damaged = self.run / 'plans/0001.json'
        damaged.write_text('{invalid')
        before = (self.run / 'events.jsonl').read_bytes()
        for command in [('status',), ('trace', '--conformance'), ('decide', 'list')]:
            result = self.call(*command)
            self.assertEqual(result['integrity'][0]['code'], 'plan_tampered')
            self.assertIn('gf plan set <file>', result['integrity'][0]['recovery'])
        for name in ('run_status', 'run_trace', 'decision_list'):
            result = mcp._call(mcp.TOOLS[name], {'run': str(self.run)})
            self.assertFalse(result['isError'], result)
            self.assertIn('plan_tampered', result['content'][0]['text'])
        for command in [('ready',), ('route', 'a'), ('start', 'a'), ('gate', 'a'), ('gate', '--final')]:
            self.assertEqual(self.call(*command, code=4)['code'], 'plan_tampered')
        self.assertEqual((self.run / 'events.jsonl').read_bytes(), before)
        # Use the real HTTP handler, with resolved registry paths on macOS.
        import http.client
        import threading
        from urllib.parse import urlencode
        httpd, token = server.make_server()
        thread = threading.Thread(target=httpd.serve_forever, kwargs={'poll_interval': .01})
        thread.start()
        try:
            connection = http.client.HTTPConnection('127.0.0.1', httpd.server_address[1], timeout=5)
            try:
                connection.request('GET', '/api/run?' + urlencode({'project': str(self.project.resolve()), 'run': self.run.name}), headers={'X-GF-Token': token})
                response = connection.getresponse()
                result = json.loads(response.read())
                self.assertEqual(response.status, 200, result)
                self.assertTrue(result['view']['plan_error'])
                self.assertEqual(result['view']['integrity'][0]['code'], 'plan_tampered')
                self.assertIn('gf plan set', result['trace']['integrity'][0]['recovery'])
            finally: connection.close()
        finally:
            httpd.shutdown(); httpd.server_close(); thread.join(5)
        self.assertFalse(thread.is_alive())
        new = self.set_plan()['decision']; self.accept(new)
        self.call('ready')

    def test_damaged_log_reads_report_unavailable_metrics_without_repairing(self):
        self.set_plan()
        logfile = self.run / 'events.jsonl'
        original = logfile.read_bytes()
        for code, content in [('log_corrupt', b'not json\n{}\n'), ('log_sequence', b'{"seq":7}\n')]:
            with self.subTest(code=code):
                logfile.write_bytes(content)
                for command in [('status',), ('trace', '--conformance'), ('decide', 'list')]:
                    self.assertEqual(self.call(*command)['integrity'][0]['code'], code)
                result = self.call('trace', '--conformance')
                self.assertTrue(all(p['observation'] == 'not measurable from records' for p in result['conformance'].values()))
                self.assertEqual(server._snapshot(self.run)[2]['run']['integrity'][0]['code'], code)
                self.assertEqual(logfile.read_bytes(), content)
        logfile.write_bytes(original)
