#!/usr/bin/env python3
"""Durable dashboard fixtures. Normal history is produced only by scripts/gf."""
import argparse
import contextlib
import io
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest import mock

HERE = Path(__file__).resolve().parent
SKILL = HERE.parents[1] / 'skills/graph-flow'
sys.path[:0] = [str(SKILL / 'scripts'), str(SKILL / 'tests')]
from human_support import human_answer
from test_review11 import Review11Tests
from graphflow import cli

SCENARIOS = {
    'demo': '여섯 작업의 진행, 근거가 있는 확인 요청과 자유 질문',
    'real': '명령 검사, lane 2 검토, lane 3 허가를 포함한 코드 작업',
    'many': '열세 작업이 분기하고 합쳐지는 진행 화면',
    'files': '제출한 안내 파일을 읽고 판단하는 사람 검사',
    'nothing': '첨부 근거가 없는 허가 결정',
    'plan': '사람 검사와 결정 시점이 포함된 새 계획',
    'sent-back': '사람이 수정 요청을 보낸 계획',
    'large-plan': '열세 작업의 승인 대기 계획',
    'large-run': '열세 작업 중 일부가 끝나고 실행 중인 작업',
    'thirty-plan': '서른 작업의 승인 대기 계획',
    'thirty-run': '서른 작업의 진행 화면',
    'tampered': '저장된 계획 파일이 변조된 상태',
    'unverified': '승인 답변의 서명이 변조된 상태',
    'superseded': '문구 변경 뒤 게이트가 다시 요청한 결정의 이전 링크',
    'old': '테스트에 보존된 실제 0.2.1 실행 기록',
    'old-continue': '0.2.1 제출물을 유지하고 새 계획 승인을 기다림',
    'old-reasked': '0.2.1 계획 승인 후 현재 게이트가 다시 묻는 확인',
    'key-mismatch': '승인 후 격리 홈의 키가 바뀐 상태',
    'key-repinned': '테스트의 사람 터미널 경로로 키를 복구한 새 승인',
    'replaced': '변조된 계획을 정상 CLI로 교체한 상태',
    'constraints': '통합 검사와 승격 검사, 적용 지침을 담은 계획',
    'moved': '승인 후 프로젝트 경로가 이동한 상태',
    'changed-live': '열린 승인 화면에서 검사 계약을 바꾸는 계획',
    'check-options': '검사의 작업 폴더와 제한 시간이 있는 계획',
    'file-changed-live': '열린 판단 화면에서 첨부 파일의 내용이 달라짐',
    'key-recovery-live': '현재 화면에서 키 복구 확인을 펼침',
    'hold': '검토 실패 후 게이트가 요청하는 보류 판단',
    'outcomes': '후속 작업을 허용하는 허가 결정',
    'own-files': '소유한 검사 스크립트를 실행하는 계획',
    'answered': '이미 답한 결정이 남아 있는 진행 계획',
    'free': '에이전트가 보낸 비구속 자유 질문',
    'review-awaited': 'lane 1 작업의 예정된 검토를 기다림',
    'revised': '돌려보낸 결정 질문을 수정하고 다시 요청함',
    'wording': '질문 문구만 바꾼 재게시의 기록',
}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def work(node='a', title='안내 쓰기', needs=()):
    file = 'guide.txt' if node == 'a' else node + '.txt'
    return dict(id=node, kind='work', title=title, goal=title + ' 작업을 마치고 결과를 확인해요.',
                lane=1, grade='daily', owns=[file], outputs=['결과'],
                needs=[{'from': n, 'artifact': '결과'} for n in needs],
                checks=[dict(id='text', type='cmd', title='결과 파일에 내용이 있어요', run='test -s ' + file)])


def question():
    return dict(id='q', kind='decision', lane=1, title='배포 범위 확인', goal='배포할 범위를 확인해요.',
                question='이 안내를 시험 환경에 공개할까요?', decision_kind='authorization', outputs=['허가'],
                context={'why': '검토를 마친 안내를 시험 환경에서 확인하려고 해요.', 'undo': '공개한 안내는 다시 내릴 수 있어요.'})


def review(target='a', node='r'):
    return dict(id=node, kind='review', title={'html':'검색 화면 검토','guide':'배포 안내 검토','b':'예제 검토'}.get(target,'안내 검토'), goal='안내의 내용과 안전성을 검토해요.',
                target=target, lens='정확성 · 접근성 · 빠진 예외', lane=1, grade='daily')


class Fixture:
    def __init__(self, root, scenario):
        self.root = root / scenario
        self.root.mkdir()
        self.home = self.root / 'gf-home'
        self.project = self.root / 'project'
        self.project.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('GF_')}
        self.env.update(GF_HOME=str(self.home), GF_NO_OPEN='1', GF_ROLE='leader', GF_SESSION='screens-r17',
                        GIT_AUTHOR_DATE='2026-11-17T00:00:00+0000', GIT_COMMITTER_DATE='2026-11-17T00:00:00+0000')
        self.commands = []
        self.git('init', '-q')
        self.git('-c', 'user.name=Screens', '-c', 'user.email=screens@example.invalid', 'commit', '--allow-empty', '-qm', '화면 재현 기준')
        self.run = self.project / '.graph-flow/runs' / scenario
        self.call('init', scenario, initial=True)
        self.raw = dict(schema_version=1, title='안내 만들기', goal='확인할 수 있는 안내와 사용 설명서를 만들어요.', nodes=[work()])
        self.decision = None
        self.approval = None

    def git(self, *args, **kwargs):
        return subprocess.run(['git', '-C', str(self.project), *args], env=self.env, check=True, capture_output=True, **kwargs)

    def call(self, *args, code=0, initial=False):
        command = [sys.executable, '-I', '-S', '-B', str(SKILL / 'scripts/gf'), '--json', '--project', str(self.project)]
        if not initial:
            command += ['--run', str(self.run)]
        result = subprocess.run(command + list(args), cwd=self.project, env=self.env, capture_output=True, text=True)
        self.commands.append(dict(args=list(args), code=result.returncode))
        try:
            data = json.loads(result.stdout)
        except ValueError:
            raise AssertionError((args, result.stdout, result.stderr))
        assert result.returncode == code, (self.root.name, args, data, result.stderr)
        return data

    def post(self, approve=False):
        path = self.root / 'plan.json'
        write_json(path, self.raw)
        self.approval = self.call('plan', 'set', str(path))['decision']
        if approve:
            self.answer(self.approval)
        return self.approval

    def answer(self, decision, outcome='approved', text='내용과 결과를 확인했어요.'):
        # The same isolated human terminal and signing path used by the test suite.
        with mock.patch.dict(os.environ, self.env, clear=True):
            human_answer(self.run, decision, outcome, '내용과 결과를 확인했어요.' if outcome == 'approved' else text)

    def assign(self, node, reviewer=False):
        self.call('assign', node, '--executor', 'inline', '--model', '화면-검증', '--effort', 'high',
                  '--provider', 'fixture', '--family', 'openai' if reviewer else 'claude', '--isolation', 'shared')

    def submit(self, node='a', pass_gate=False):
        self.assign(node)
        self.call('start', node)
        entry = next(n for n in self.raw['nodes'] if n['id'] == node)
        for file in entry.get('owns', []):
            path = self.project / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('사용 안내\n\n1. 작업할 내용을 확인해요.\n2. 변경한 결과를 검사해요.\n3. 근거를 읽고 다음 단계를 결정해요.\n', encoding='utf-8')
        self.call('check', 'run', node, 'text')
        self.call('submit', node, '--notes', '안내 파일을 작성하고 명령 검사로 내용이 있는지 확인했어요.')
        if pass_gate:
            self.call('gate', node)

    def metadata(self):
        result = dict(scenario=self.root.name, project=str(self.project), run=self.run.name,
                      home=str(self.home), decision=self.decision, approval=self.approval,
                      plan=str(self.root / 'plan.json'), commands=self.commands)
        write_json(self.root / 'fixture.json', result)
        return result


def branching(count):
    deps = [[], [0], [0], [1], [1], [1], [2], [2], [2], [6, 7], [3, 4], [8, 9, 10], [5, 11]]
    titles = ['자료 읽기', '요약 작성', '화면 구성', '검색 구현', '목록 구현', '사용 안내', '입력 검증', '오류 안내', '접근성 확인', '화면 통합', '기능 통합', '통합 검사', '배포 준비']
    return [work('n%d' % i, titles[i] if i < 13 else '후속 작업 %02d' % (i + 1),
                 ['n%d' % n for n in (deps[i] if i < 13 else [i - 1])]) for i in range(count)]


def build(root, scenario):
    f = Fixture(root, scenario)
    if scenario.startswith('old'):
        legacy = json.loads((SKILL / 'tests/fixtures/legacy021.json').read_text().replace('Read this guide', '안내를 읽고 확인해 주세요'))
        # Localize the unsigned historical fixture consistently with its stored plan bytes.
        history = [json.loads(line) for line in legacy['files']['events.jsonl'].splitlines()]
        for event in history:
            if event['type'] == 'plan.set':
                plan_bytes = legacy['files']['plans/%04d.json' % event['data']['revision']].encode()
                event['data']['plan_sha256'] = hashlib.sha256(plan_bytes).hexdigest()
        legacy['files']['events.jsonl'] = ''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in history)
        shutil.rmtree(f.run)  # Only our just-created empty run is replaced by the preserved historical fixture.
        f.run.mkdir()
        for relative, text in legacy['files'].items():
            path = f.run / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')
        f.git('hash-object', '-t', 'commit', '-w', '--stdin', input=legacy['git_base_commit'].encode())
        (f.project / 'guide.txt').write_text('이전 버전에서 제출한 안내예요.\n', encoding='utf-8')
        f.raw = legacy['raw_plan']
        f.call('status')
        if scenario != 'old':
            f.post(approve=scenario == 'old-reasked')
        if scenario == 'old-reasked':
            f.decision = f.call('gate', 'a', code=1)['asks'][0]
        return f.metadata()
    if scenario in ('many', 'large-plan', 'large-run', 'thirty-plan', 'thirty-run'):
        f.raw.update(title='안내 서비스 만들기', nodes=branching(30 if scenario.startswith('thirty') else 13))
        f.post(approve=scenario in ('many', 'large-run', 'thirty-run'))
        if scenario in ('many', 'large-run', 'thirty-run'):
            f.submit('n0', True)
            f.submit('n1', True)
            if scenario == 'large-run':
                f.submit('n2', True)
                f.call('start', 'n3')
            else:
                f.call('start', 'n2')
        return f.metadata()
    if scenario == 'real':
        f.raw.update(title='검색 기능 개선', nodes=[work('reader', '기록 읽기'), work('summary', '검색 결과 정리', ['reader']),
            work('html', '검색 화면 구현', ['reader']), review('html', 'html-review'), work('guide', '배포 안내 작성', ['summary', 'html']), review('guide', 'guide-review')])
        f.raw['nodes'][2]['lane'] = 2
        f.raw['nodes'][4]['lane'] = 3
        f.post(True)
        f.submit('reader', True)
        f.submit('summary', True)
        f.submit('html')
        f.call('gate', 'html', code=1)
        f.call('start', 'html-review')
        return f.metadata()
    if scenario == 'demo':
        f.raw.update(title='사용 안내 개선', nodes=[work(), work('b', '예제 작성', ['a']), work('c', '설명 확인', ['a']),
            work('d', '화면 정리', ['b']), work('e', '최종 확인', ['c', 'd']), work('f', '안내 전달', ['e'])])
        f.raw['nodes'][1]['checks'].append(dict(id='human', type='human', prompt='예제의 순서와 설명이 충분한가요?'))
        f.post(True)
        f.submit('a', True)
        f.submit('c', True)
        f.submit('b')
        f.decision = f.call('gate', 'b', code=1)['asks'][0]
        f.call('decide', 'ask', '--kind', 'information', '--question', '처음 사용하는 분을 위한 예제를 더 넣을까요?')
        return f.metadata()
    if scenario in ('plan', 'sent-back', 'changed-live', 'constraints', 'check-options', 'own-files', 'wording'):
        f.raw['nodes'][0]['checks'].append(dict(id='human', type='human', title='안내 확인', prompt='안내의 순서를 확인해 주시겠어요?'))
        f.raw['nodes'] += [question(), work('b', '예제 작성', ['a']), review('b')]
        if scenario == 'constraints':
            planned = f.raw
            f.raw = dict(schema_version=1, title='지침 확인', goal='안내 작성에서 배운 지침을 남겨요.', nodes=[work()])
            f.post(True)
            f.submit('a', True)
            f.raw = planned
            f.raw['nodes'][0] = work()
            item = f.call('learn', 'add', '--from', 'a', '--text', '안내에는 실행 순서와 되돌리는 방법을 적어요.', '--review-when', '배포 방식이 바뀔 때')
            f.call('learn', 'promote', item['id'], '--run', 'test -s guide.txt')
            f.call('learn', 'add', '--from', 'a', '--text', '새 오류 메시지는 한국어로 작성해요.', '--review-when', '언어가 바뀔 때')
            f.raw['integration_checks'] = [dict(id='all', type='cmd', title='전체 안내를 검사해요', run='test -s guide.txt')]
        if scenario == 'check-options':
            (f.project / 'docs').mkdir()
            f.raw['nodes'][0]['owns'] = ['docs/guide.txt']
            f.raw['nodes'][0]['checks'][0].update(cwd='docs', timeout_s=12)
        if scenario == 'own-files':
            f.raw['nodes'][0]['owns'].append('check.sh')
            f.raw['nodes'][0]['checks'][0].update(run='bash check.sh', title='직접 작성한 검사 스크립트를 실행해요')
        if scenario == 'wording':
            f.raw['nodes'][0]['checks'][-1].pop('prompt')
        f.post(approve=scenario == 'wording')
        if scenario == 'sent-back':
            f.answer(f.approval, 'revision_requested', '설치 순서와 실패했을 때 되돌리는 방법을 추가해 주세요.')
        if scenario == 'changed-live':
            revised = json.loads(json.dumps(f.raw))
            revised['nodes'][0]['checks'][0]['run'] = 'test -s guide.txt && test -r guide.txt'
            revised['nodes'].append(work('extra', '복구 안내 작성', ['b']))
            write_json(f.root / 'changed-plan.json', revised)
        if scenario == 'wording':
            f.raw['nodes'][0]['checks'][-1]['title'] = '처음 사용하는 분도 안내 순서를 따라갈 수 있나요?'
            f.raw['nodes'][1]['context']['why'] = '공개 범위를 먼저 확인하고 안내를 전달해요.'
            f.post()
        return f.metadata()
    if scenario in ('nothing', 'outcomes', 'answered', 'revised'):
        f.raw['nodes'] = [question(), work()]
        f.raw['nodes'][1]['needs'] = [{'from': 'q', 'artifact': '허가'}]
        if scenario == 'nothing':
            f.raw['nodes'][0].pop('context')
        f.post(True)
        f.decision = f.call('gate', 'q', code=1)['asks'][0]
        if scenario == 'answered':
            f.answer(f.decision)
            f.call('gate', 'q')
            f.call('start', 'a')
        if scenario == 'revised':
            f.answer(f.decision, 'revision_requested', '전체 공개 전에 시험 환경에서 먼저 확인해 주세요.')
            f.call('gate', 'q', code=1)
            f.raw['nodes'][0]['question'] = '전체 공개 대신 내부 시험 환경에만 안내를 공개할까요?'
            f.post(True)
            f.decision = f.call('gate', 'q', code=1)['asks'][0]
        return f.metadata()
    if scenario in ('hold', 'review-awaited'):
        f.raw['nodes'].append(review())
        f.post(True)
        f.submit()
        if scenario == 'hold':
            f.assign('r', True)
            f.call('start', 'r')
            findings = f.root / 'findings.json'
            write_json(findings, [dict(file='guide.txt', line=2, text='실패했을 때 되돌리는 절차가 빠져 있어요.')])
            f.call('--role', 'reviewer', '--node', 'r', 'review', 'submit', 'r', '--verdict', 'fail', '--findings', str(findings))
            f.call('gate', 'r')
            f.decision = f.call('gate', 'a', code=1)['asks'][0]
        else:
            f.call('gate', 'a', code=1)
        return f.metadata()
    if scenario == 'free':
        f.post(True)
        f.call('start', 'a')
        f.decision = f.call('decide', 'ask', '--kind', 'information', '--question', '안내의 주 독자는 누구인가요? 처음 사용자에게 맞춰도 될까요?', '--node', 'a')['id']
        return f.metadata()
    if scenario in ('files', 'superseded', 'file-changed-live'):
        f.raw['nodes'][0]['checks'].append(dict(id='human', type='human', prompt='이 안내를 사용자가 따라갈 수 있을까요?', context={'why': '설명의 흐름은 사람이 읽고 확인해요.'}))
        f.post(True)
        f.submit()
        f.decision = f.call('gate', 'a', code=1)['asks'][0]
        if scenario == 'superseded':
            f.raw['nodes'][0]['checks'][-1]['context']['why'] = '수정한 안내를 공개하기 전에 설명을 확인해요.'
            f.post()
            f.call('gate', 'a', code=1)
        return f.metadata()
    f.post(True)
    if scenario in ('tampered', 'replaced'):
        # The exact damaged-plan operation used by IntegrityReadTests in test_round16.py.
        (f.run / 'plans/0001.json').write_text('{invalid', encoding='utf-8')
        if scenario == 'replaced':
            f.post()
    elif scenario == 'unverified':
        # Reuse the suite's tampering helper; do not fabricate an agent-role answer.
        with mock.patch.dict(os.environ, f.env, clear=True):
            Review11Tests.rewrite(f, lambda events: next(e['data'] for e in events if e['type'] == 'decision.answer').update(sig='tampered-signature'))
    elif scenario in ('key-mismatch', 'key-repinned', 'key-recovery-live'):
        f.raw['goal'] += ' 복구 절차도 함께 확인해요.'
        f.post()
        (f.home / 'human.key').write_bytes(b'rotated')
        if scenario == 'key-repinned':
            # Same terminal simulation as Review9Tests.test_n4; never an agent-role answer.
            with mock.patch.dict(os.environ, dict(f.env, GF_HUMAN_TERMINAL='1'), clear=True), mock.patch('sys.stdin.isatty', return_value=True), contextlib.redirect_stdout(io.StringIO()):
                assert cli.main(['--json', '--run', str(f.run), '--role', 'human', 'key', 'repin']) == 0
    elif scenario == 'moved':
        moved = f.root / 'moved-project'
        f.project.rename(moved)
        f.project = moved
        f.run = moved / '.graph-flow/runs' / scenario
        f.call('status')
    else:
        raise AssertionError(scenario)
    return f.metadata()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='durable output directory; creates fixtures/ beneath it')
    args = parser.parse_args()
    root = args.output.resolve() / 'fixtures'
    if str(root).startswith(('/tmp/', '/private/tmp/')) or root == Path.home() / '.graph-flow':
        parser.error('use a durable isolated output directory')
    marker = root / '.screens-fixtures'
    if root.exists():
        if not marker.is_file():
            parser.error('refusing to replace an unmarked fixture directory')
        shutil.rmtree(root)
    root.mkdir(parents=True)
    marker.write_text('Owned by graph-flow dev/screens/build_fixtures.py\n')
    entries = {}
    for scenario in SCENARIOS:
        print('Building ' + scenario, flush=True)
        entries[scenario] = build(root, scenario)
    write_json(root / 'index.json', entries)
    print('Built %d scenarios in %s' % (len(entries), root))


if __name__ == '__main__':
    main()
