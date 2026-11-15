"""Dashboard assets and a reusable real-library demonstration run.

From the repository root (use fresh demo directories):
python3 -B -c 'import sys; sys.path.insert(0,"plugins/graph-flow/skills/graph-flow/tests"); from test_page import build_demo_run; build_demo_run("/tmp/gf-demo-home", "/tmp/gf-demo-project"); from graphflow.server import serve; serve()'
"""
import contextlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

S = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(S / 'scripts'))
from graphflow import checks, decisions, gate, learn, plan, server, state, store

ACTOR = {'role': 'leader', 'node': None, 'session': 'dashboard-demo'}


def build_demo_run(gf_home, project_dir):
    """Create a fresh isolated project/run and set GF_HOME; return its run Path.

    Only the supplied project is initialized with git; the plugin checkout is untouched.
    """
    os.environ['GF_HOME'] = str(pathlib.Path(gf_home).resolve())
    project = pathlib.Path(project_dir).resolve()
    project.mkdir(parents=True, exist_ok=True)
    if (project / '.git').exists() or (project / '.graph-flow').exists():
        raise ValueError('demo requires a fresh project directory')
    def git(*args):
        return subprocess.check_output(['git', '-C', str(project)] + list(args), stderr=subprocess.PIPE)
    git('init', '-q')
    git('-c', 'user.name=Dashboard demo', '-c', 'user.email=demo@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-q', '--allow-empty', '-m', 'Demo foundation')
    head = git('rev-parse', 'HEAD').decode().strip()
    decisions.ensure_key()
    run = store.init_run(project, 'dashboard-demo', ACTOR)
    context = {'why': '처음 읽는 사람이 따라 할 수 있는지는 직접 읽어 주셔야 해요.',
               'if_approved': '읽기 쉬운 설명으로 받아들이고 내보내기를 준비해요.',
               'if_rejected': '적어 주신 곳을 고쳐 다시 가져와요.',
               'undo': '통과시킨 뒤에도 다시 열어 고칠 수 있어요.'}
    titles = [('promise', '약속 정하기', '무엇을 만들지 함께 정한 약속이에요.'),
              ('records', '기록 저장', '정한 약속에 따라 진행 기록을 남겨요.'),
              ('checks', '통과 판정', '고친 결과를 다시 확인해서 다음 일에 넘겨요.'),
              ('guide', '사용 설명서', '처음 쓰는 분이 따라 할 수 있게 설명을 써요.'),
              ('screen', '현황판 화면', '지금 하는 일과 다음 결정을 한눈에 보여 드려요.'),
              ('export', '내보내기', '완성한 결과를 쓰실 수 있게 모아 드려요.')]
    raw = {'schema_version': 1, 'title': '실행 현황판 만들기', 'goal': '진행 상황을 편하게 함께 살펴봐요.', 'nodes': []}
    for nid, title, summary in titles:
        raw['nodes'].append({'id': nid, 'kind': 'work', 'title': title, 'summary': summary,
                            'goal': summary, 'lane': 1, 'grade': 'scoped', 'owns': [nid + '.txt'],
                            'checks': [{'id': 'quality', 'type': 'cmd', 'title': '약속한 결과가 빠짐없이 있어요',
                                        'run': 'test -f retry-ready.txt' if nid == 'checks' else 'printf checked'}]})
    by_id = {n['id']: n for n in raw['nodes']}
    def need(target, source, label):
        by_id[target].setdefault('needs', []).append({'from': source, 'artifact': source + '.txt', 'label': label})
    need('records', 'promise', '함께 정한 약속')
    need('checks', 'records', '저장 기록')
    need('guide', 'records', '기록 사용법')
    need('screen', 'checks', '판정 규칙')
    need('screen', 'guide', '읽기 쉬운 설명')
    need('export', 'screen', '완성한 화면')
    by_id['guide']['checks'].append({'id': 'readability', 'type': 'human', 'title': '처음 읽는 분도 따라 할 수 있어요',
                                     'prompt': '사용 설명서를 통과시킬까요?', 'context': context})
    problems = plan.validate(raw)
    if problems:
        raise AssertionError(problems)
    normalized, _ = plan.normalize(raw)
    with store.transaction(run) as tx:
        revision, sha = tx.write_plan(normalized)
        tx.append('plan.set', {'revision': revision, 'plan_sha256': sha,
                  'fingerprints': {n['id']: state.fingerprint(n) for n in normalized['nodes']},
                  'constraints_applied': []}, ACTOR)
    with contextlib.redirect_stderr(io.StringIO()):
        for nid in ('promise', 'records'):
            checks.start(run, nid, None, ACTOR)
            checks.submit(run, nid, head, None, '약속한 결과를 정리했어요.', [], None, ACTOR)
            assert gate.gate(run, nid, None, ACTOR)['verdict'] == 'pass'
        checks.start(run, 'checks', None, ACTOR)
        checks.submit(run, 'checks', head, None, '빠진 경우를 확인해 주세요.', [], None, ACTOR)
        assert gate.gate(run, 'checks', None, ACTOR)['verdict'] == 'reject'
        checks.start(run, 'guide', None, ACTOR)
        checks.submit(run, 'guide', head, None, '설치 순서 부분은 자신이 없어요.',
                      ['설치 순서가 처음 쓰는 분께 자연스러운지는 확인하지 못했어요.'], None, ACTOR)
        assert gate.gate(run, 'guide', None, ACTOR)['verdict'] == 'needs_approval'
        checks.start(run, 'checks', None, ACTOR)
    learn.add(project, run, 'records', '늦게 온 판정이 앞선 판정을 덮어쓰지 않게 확인해요.',
              '판정 방식이 바뀌면 다시 살펴봐요.', [], [], ACTOR)
    return run


class PageTests(unittest.TestCase):
    def test_local_assets_safe_dom_and_nonce(self):
        html = (S / 'scripts/graphflow/page.html').read_text(encoding='utf-8')
        js = (S / 'scripts/graphflow/page.js').read_text(encoding='utf-8')
        for source in (html, js):
            for forbidden in ('http://', 'https://', 'innerHTML', 'insertAdjacentHTML', 'document.write', 'eval(', 'new Function'):
                self.assertNotIn(forbidden, source)
            self.assertNotRegex(source, r'\bstyle\s*=\s*[\"\']')
        self.assertIn('<style nonce="__NONCE__">', html)
        self.assertIn('<script type="module" nonce="__NONCE__" src="/static/page.js">', html)
        self.assertEqual(html.count('<script'), 1)
        self.assertNotIn('unsafe-inline', html)
        self.assertNotIn('unsafe-eval', html)

    def test_translation_keys_match(self):
        js = (S / 'scripts/graphflow/page.js').read_text(encoding='utf-8')
        literal = js.split('// UI_STRINGS_START\nconst STRINGS = ', 1)[1].split(';\n// UI_STRINGS_END', 1)[0]
        strings = json.loads(literal)
        self.assertEqual(set(strings), {'ko', 'en'})
        self.assertEqual(set(strings['ko']), set(strings['en']))
        self.assertTrue(all(isinstance(v, str) and v for table in strings.values() for v in table.values()))
        used = re.findall(r"\bt\('([A-Za-z_]+)'", js)
        self.assertEqual(set(used) - set(strings['en']), set())

    @unittest.skipUnless(shutil.which('node'), 'node is not on PATH; ES module syntax validation skipped')
    def test_es_module_syntax(self):
        result = subprocess.run([shutil.which('node'), '--input-type=module', '--check'],
                                input=(S / 'scripts/graphflow/page.js').read_bytes(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    @unittest.skipUnless(shutil.which('node'), 'node is not on PATH; dashboard decision behavior tests skipped')
    def test_decision_behavior(self):
        script = r'''
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source = readFileSync(process.argv[2], 'utf8');
const {captureDecision, answerTarget, draftKey, reconcileDecision, decisionIsCurrent, canApprove, purposeWording, purposeAction} = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const first = {project:'/project', run:'first'}, second = {project:'/project', run:'second'};
const decision = {id:'d7', purpose:'lane3', kind:'authorization'};
let chosen = {...first};
const open = captureDecision(chosen, decision);
chosen.run = second.run;
assert.deepEqual(answerTarget(open), {...first, id:'d7'}, 'POST must use the captured target');
assert(Object.isFrozen(open.target));
const other = captureDecision(chosen, decision);
const key = draftKey(open.target), otherKey = draftKey(other.target);
assert.notEqual(key, otherKey, 'same id in different runs must have separate drafts');
assert.notEqual(key, draftKey({...open.target, project:'/other'}));
assert.notEqual(draftKey({project:'a,b',run:'c',id:'d'}), draftKey({project:'a',run:'b,c',id:'d'}));
const drafts = {[key]:'first draft', [otherKey]:'second draft'};
const changed = reconcileDecision(open, chosen, [decision], drafts);
assert.equal(changed.open, null);
assert.equal(changed.reason, 'runChanged');
assert.equal(changed.drafts[key], undefined, 'run change must discard the old draft');
assert.equal(changed.drafts[otherKey], 'second draft');
assert.equal(drafts[key], 'first draft', 'reconciliation must be pure');
const missing = reconcileDecision(open, first, [], drafts);
assert.equal(missing.open, null);
assert.equal(missing.reason, 'decisionClosed');
assert.equal(missing.drafts[key], undefined);
assert.equal(reconcileDecision(open, first, [decision], drafts).open, open);
assert.equal(reconcileDecision(open, null, [decision], drafts).open, null);
assert.equal(reconcileDecision(open, {...first, project:'/other'}, [decision], drafts).open, null);
assert.equal(decisionIsCurrent(open, open, first, [decision]), true);
assert.equal(decisionIsCurrent(open, open, chosen, [decision]), false);
assert.equal(decisionIsCurrent(open, null, first, [decision]), false, 'late POST must not revive a closed view');
assert.equal(decisionIsCurrent(open, captureDecision(first, decision), first, [decision]), false, 'late POST must not affect a reopened view');
assert.equal(canApprove(open), false);
assert.equal(canApprove({...open, detailsOpened:true}), true);
assert.equal(canApprove(captureDecision(first, {...decision, purpose:'authorization'})), false);
assert.equal(canApprove(captureDecision(first, {...decision, purpose:'future-purpose'})), false, 'authorization kind retains the details gate');
assert.equal(canApprove(captureDecision(first, {...decision, purpose:'human_check', kind:'review'})), true);
assert.equal(canApprove(null), false);
for (const language of ['ko','en']) {
  const meanings = ['human_check','lane3','trajectory','hold','direction','information'].map(p => purposeWording(p, language));
  assert.equal(new Set(meanings).size, meanings.length, 'decision purposes must remain distinct');
  assert.equal(purposeWording('authorization', language), purposeWording('lane3', language));
  assert.equal(purposeWording('review', language), purposeWording('human_check', language));
  for (const purpose of ['future-purpose','node','free',undefined,'toString','__proto__']) {
    assert.equal(typeof purposeWording(purpose, language), 'string');
    assert(!/approv|통과|승인|허락/i.test(purposeWording(purpose, language)), 'unknown purpose must use neutral wording');
    assert(!/approv|통과|승인|허락/i.test(purposeAction(purpose, language)), 'unknown purpose must use a neutral action');
  }
}
'''
        result = subprocess.run([shutil.which('node'), '--input-type=module', '-',
                                 str(S / 'scripts/graphflow/page.js')], input=script,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_demo_and_decision_view(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ):
            root = pathlib.Path(directory)
            run = build_demo_run(root / 'home', root / 'project')
            current, events, derived = server._snapshot(run)
            view = server._view(current, derived, events, root / 'project')
            self.assertEqual(view['counts'], {'done': 2, 'doing': 1, 'waiting': 2, 'needs_you': 1, 'returned': 1})
            self.assertEqual([n['laps'] for n in view['nodes']], [['passed'], ['passed'], ['returned', 'current'], ['waiting_for_you'], [], []])
            decision = view['decisions'][0]
            self.assertEqual(decision['purpose'], 'human_check')
            self.assertEqual(decision['verified'], ['약속한 결과가 빠짐없이 있어요'])
            self.assertEqual(decision['unverified'], ['처음 읽는 분도 따라 할 수 있어요', '설치 순서가 처음 쓰는 분께 자연스러운지는 확인하지 못했어요.'])
            self.assertEqual(decision['worker_note'], '설치 순서 부분은 자신이 없어요.')
            self.assertTrue(decision['context']['why'])
            self.assertEqual(view['nodes'][3]['inputs'], [{'label': '기록 사용법', 'other_title': '기록 저장', 'delivered': True}])
            self.assertEqual(view['nodes'][3]['outputs'], [{'label': '읽기 쉬운 설명', 'other_title': '현황판 화면', 'delivered': False}])
            self.assertTrue(view['lessons'])


if __name__ == '__main__':
    unittest.main()
