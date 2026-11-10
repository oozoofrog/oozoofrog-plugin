#!/usr/bin/env python3
"""Serve a local, read-only live dashboard for one guided-execution run.

Binds 127.0.0.1 only and requires the per-process token printed on startup.
Loop records are re-read on every request and never written. An optional AI
summary (labels and grouping only) is accepted from the launching host and
kept in memory; record statuses always come from the loop files.
Tool-call activity (metadata only) is accepted the same way, kept in memory,
and shown as session activity, never as a record.
Exits when its launching parent process goes away (POSIX re-parenting).
"""
import argparse
import os
from pathlib import Path
import re
from datetime import datetime, timezone
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit

# Read-only service: do not leave __pycache__ next to the skill scripts.
sys.dont_write_bytecode = True
from loop_workspace import SCOPE, load_workspace, status
from loop_control import validate_extra
from render_report import build_graph, render

MAX_BODY = 256 * 1024
MAX_FILE = 200 * 1024
MAX_PENDING = 20
MAX_EXPLAINED = 300
MAX_QUESTIONS = 10
SECRET = re.compile(r'(^|/)(\.ssh|\.gnupg|\.aws|\.kube)(/|$)|(^|/)(\.env[^/]*|\.netrc|\.npmrc|\.pypirc|\.git-credentials|'
                    r'credentials(\.json)?|id_(rsa|dsa|ecdsa|ed25519))$|\.(pem|key|p12|pfx|jks|keystore)$', re.IGNORECASE)
MAX_STAGES = 12
MAX_STAGE_EDGES = 24
MAX_REFS = 40
MAX_TIMELINE = 24
MAX_ACTIVITY = 120
ACTIVITY_PHASES = {'running', 'ok', 'error'}
SESSION_NODE = '__session'
STAGE_KINDS = {'plan', 'build', 'verify', 'decide', 'deliver', 'other'}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def clip(value, limit):
    if not isinstance(value, str):
        return None
    value = ' '.join(value.split())
    return value[:limit] if value else None


def timelines(state):
    """Recorded transitions per task, oldest first. A finish's result is the status that the
    next event touching the task saw before it, or the current status for the latest one."""
    history = [event for event in state.get('history', []) if isinstance(event, dict)]
    lines = {}
    for index, event in enumerate(history):
        origin = event.get('task')
        for name in event.get('previous_tasks') or {}:
            entry = dict(at=clip(event.get('timestamp'), 40), action=clip(event.get('action'), 30))
            if name != origin:
                entry.update(action='invalidated', by=origin)
            elif event.get('action') == 'record-check' and isinstance(event.get('record'), dict):
                entry.update(check=clip(event['record'].get('check_id'), 60),
                             result=clip(event['record'].get('result'), 20))
            elif event.get('action') == 'finish':
                later = next((e['previous_tasks'][name] for e in history[index + 1:]
                              if name in (e.get('previous_tasks') or {})), state['tasks'].get(name, {}))
                entry['result'] = clip(later.get('status'), 20) if isinstance(later, dict) else None
            if event.get('reason') and name == origin:
                entry['reason'] = clip(event['reason'], 200)
            lines.setdefault(name, []).append(entry)
    return lines


def snapshot(workspace):
    """One consistent read of the run: load_workspace rejects a mismatched plan/state pair."""
    validated, files, plan, state, warnings = load_workspace(workspace)
    validate_extra(validated, plan, state)
    summary = status(plan, state, warnings)
    graph = build_graph(plan, state)
    lines = timelines(state)
    tasks = []
    for task in plan['tasks']:
        item = state['tasks'][task['id']]
        results, paths = {}, {}
        for record in item['evidence']:
            results.setdefault(record['check_id'], []).append(record['result'])
            paths[record['check_id']] = record['path']
        timeline = lines.get(task['id'], [])
        starts = [entry['at'] for entry in timeline if entry['action'] == 'start']
        tasks.append(dict(
            id=task['id'], title=task['title'], status=item['status'],
            attempts=item['attempts'], max_attempts=task['max_attempts'],
            depends_on=task['depends_on'], decision_ids=task['decision_ids'],
            reads=task['reads'], writes=task['writes'],
            revision=item.get('running_revision') or item.get('verified_revision'),
            started_at=starts[-1] if starts else None, timeline=timeline[-MAX_TIMELINE:],
            block_reason=item.get('block_reason') if isinstance(item.get('block_reason'), str) else None,
            checks=[dict(id=check['id'], description=check.get('description', ''), evidence=paths.get(check['id']),
                         result=('stale' if item['status'] == 'stale' else
                                 'mixed' if len(results.get(check['id'], [])) > 1 else
                                 results[check['id']][0] if check['id'] in results else 'unrecorded'))
                    for check in task['checks']]))
    decisions = [dict(id=decision['id'], kind=decision['kind'], question=decision.get('question', ''),
                      status=state['decisions'][decision['id']]['status'],
                      outcome=state['decisions'][decision['id']].get('outcome'),
                      answer=clip(state['decisions'][decision['id']].get('answer'), 200))
                 for decision in plan.get('decisions', [])]
    fingerprint = hashlib.sha256(files['plan.json'] + b'\0' + files['state.json']).hexdigest()[:16]
    return dict(ok=True, run_id=state['run_id'], goal=plan.get('goal', ''), fingerprint=fingerprint,
                read_at=now(), status=summary, tasks=tasks, decisions=decisions,
                graph=dict(nodes=len(graph['nodes']), edges=len(graph['edges'])),
                verification_scope=SCOPE)


def validate_summary(raw, task_ids):
    """Keep only labels, grouping and references. Statuses never come from the summary."""
    if not isinstance(raw, dict):
        raise ValueError('summary must be an object')
    stages, seen = [], set()
    for stage in (raw.get('stages') or [])[:MAX_STAGES]:
        if not isinstance(stage, dict):
            continue
        identifier, label = clip(stage.get('id'), 40), clip(stage.get('label'), 60)
        if not identifier or not label or identifier in seen:
            continue
        seen.add(identifier)
        refs = [ref for ref in (stage.get('refs') or [])[:MAX_REFS]
                if isinstance(ref, str) and ref in task_ids]
        kind = stage.get('kind') if stage.get('kind') in STAGE_KINDS else 'other'
        stages.append(dict(id=identifier, label=label, kind=kind, refs=list(dict.fromkeys(refs)),
                           note=clip(stage.get('note'), 160)))
    if not stages:
        raise ValueError('summary needs at least one stage with an id and label')
    edges = []
    for edge in (raw.get('edges') or [])[:MAX_STAGE_EDGES]:
        if (isinstance(edge, dict) and edge.get('from') in seen and edge.get('to') in seen
                and edge['from'] != edge['to']):
            edges.append({'from': edge['from'], 'to': edge['to']})
    tokens = raw.get('usage_tokens')
    return dict(headline=clip(raw.get('headline'), 200), model=clip(raw.get('model'), 60) or 'unknown',
                generated_at=clip(raw.get('generated_at'), 40) or now(),
                usage_tokens=tokens if type(tokens) is int and tokens >= 0 else None,
                activity=clip(raw.get('activity'), 400), stages=stages, edges=edges,
                received_at=now(), basis='ai_summary_not_a_record')


def stamp(value):
    return value if type(value) in (int, float) and 0 <= value < 1e14 else None


def validate_activity(raw, task_ids):
    """Keep bounded tool-call metadata attributed to known tasks or the session node."""
    if not isinstance(raw, dict) or not isinstance(raw.get('events'), list):
        raise ValueError('activity needs an events array')
    events, seen = [], set()
    for event in raw['events'][-MAX_ACTIVITY:]:
        if not isinstance(event, dict):
            continue
        identifier, tool = clip(event.get('id'), 48), clip(event.get('tool'), 40)
        task = event.get('task') if event.get('task') in task_ids else SESSION_NODE
        started = stamp(event.get('started_at'))
        if not identifier or not tool or identifier in seen or started is None \
                or event.get('phase') not in ACTIVITY_PHASES:
            continue
        seen.add(identifier)
        path = event.get('path') if isinstance(event.get('path'), str) and event['path'].startswith('/') \
            and len(event['path']) <= 1000 and '\x00' not in event['path'] else None
        events.append(dict(id=identifier, task=task, tool=tool, target=clip(event.get('target'), 120),
                           phase=event['phase'], started_at=started, ended_at=stamp(event.get('ended_at')),
                           agent=clip(event.get('agent'), 48), via=clip(event.get('via'), 20), path=path,
                           command=event['command'][:600] if isinstance(event.get('command'), str) and event['command'].strip() else None))
    return dict(events=events, received_at=now(), basis='session_activity_not_a_record')


def read_quick(path):
    """Current text of one file the session touched: regular, non-secret, text, bounded."""
    if SECRET.search(path):
        raise PermissionError('secret-looking file')
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise FileNotFoundError('not a regular file')
    info = target.stat()
    with target.open('rb') as stream:
        data = stream.read(MAX_FILE + 1)
    if b'\x00' in data[:8192]:
        raise ValueError('binary file')
    return dict(path=path, size=info.st_size, modified=datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat(timespec='seconds'),
                truncated=len(data) > MAX_FILE, text=data[:MAX_FILE].decode('utf-8', errors='replace'))


def validate_questions(raw):
    questions = []
    for item in (raw if isinstance(raw, list) else [])[:4]:
        if not isinstance(item, dict) or not clip(item.get('question'), 300):
            continue
        options = [dict(label=clip(o.get('label'), 80), description=clip(o.get('description'), 200))
                   for o in (item.get('options') or [])[:4] if isinstance(o, dict) and clip(o.get('label'), 80)]
        questions.append(dict(question=clip(item['question'], 300), header=clip(item.get('header'), 30),
                              options=options, multi=item.get('multiSelect') is True))
    if not questions:
        raise ValueError('question needs at least one question text')
    return questions


def validate_answers(raw, questions):
    if not isinstance(raw, dict):
        raise ValueError('answers must be an object')
    texts = {q['question'] for q in questions}
    answers = {key: value.strip()[:500] for key, value in raw.items()
               if key in texts and isinstance(value, str) and value.strip()}
    if set(answers) != texts:
        raise ValueError('every question needs a nonempty answer')
    return answers


class Board:
    def __init__(self, workspace):
        self.workspace = workspace
        self.token = secrets.token_urlsafe(24)
        self.summary = None
        self.activity = None
        self.pending = {}       # explanation key -> command
        self.explained = {}     # explanation key -> {state, text}
        self.questions = []     # newest last
        self.last_good = None
        self.lock = threading.Lock()

    def records(self):
        try:
            current = snapshot(self.workspace)
        except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
            with self.lock:
                last = self.last_good
            return dict(ok=False, error=str(error)[:300], read_at=now(), last_good=last,
                        verification_scope=SCOPE)
        with self.lock:
            self.last_good = current
        return current

    def task_source(self):
        current = self.records()
        source = current if current.get('ok') else current.get('last_good')
        if not source:
            raise ValueError('no readable records to attach the summary to')
        return source

    def accept_activity(self, raw):
        accepted = validate_activity(raw, {task['id'] for task in self.task_source()['tasks']})
        with self.lock:
            self.activity = accepted
        return accepted

    def touched(self, path):
        with self.lock:
            events = (self.activity or {}).get('events', [])
            return any(event.get('path') == path for event in events)

    def explain(self, raw):
        command = raw.get('command') if isinstance(raw, dict) else None
        with self.lock:
            known = any(event.get('command') == command for event in (self.activity or {}).get('events', []))
            if not isinstance(command, str) or not known:
                raise ValueError('only observed commands can be explained')
            key = hashlib.sha256(command.encode()).hexdigest()[:16]
            if key in self.explained:
                return dict(key=key, **self.explained[key])
            self.pending[key] = command
            while len(self.pending) > MAX_PENDING:
                self.pending.pop(next(iter(self.pending)))
            return dict(key=key, state='pending')

    def explained_answer(self, raw):
        items = raw.get('items') if isinstance(raw, dict) else None
        if not isinstance(items, list):
            raise ValueError('items must be an array')
        stored = 0
        with self.lock:
            for item in items:
                key = item.get('key') if isinstance(item, dict) else None
                if key not in self.pending:
                    continue
                text = clip(item.get('text'), 400)
                self.explained[key] = dict(state='ready', text=text) if text else dict(state='failed', text=clip(item.get('error'), 160))
                del self.pending[key]
                stored += 1
            while len(self.explained) > MAX_EXPLAINED:
                self.explained.pop(next(iter(self.explained)))
        return stored

    def question(self, identifier):
        return next((q for q in self.questions if q['id'] == identifier), None)

    def ask(self, raw):
        identifier = clip(raw.get('id'), 64) if isinstance(raw, dict) else None
        if not identifier:
            raise ValueError('question needs an id')
        entry = dict(id=identifier, questions=validate_questions(raw.get('questions')), asked_at=now(),
                     status='open', answers=None, via=None)
        with self.lock:
            self.questions = [q for q in self.questions if q['id'] != identifier][-(MAX_QUESTIONS - 1):] + [entry]
        return entry

    def answer(self, raw):
        with self.lock:
            entry = self.question(raw.get('id') if isinstance(raw, dict) else None)
            if not entry:
                raise LookupError('unknown question')
            if entry['status'] != 'open':
                raise LookupError('question is no longer open')
            entry.update(answers=validate_answers(raw.get('answers'), entry['questions']), status='answered', via='dashboard')
            return entry

    def resolve(self, raw):
        with self.lock:
            entry = self.question(raw.get('id') if isinstance(raw, dict) else None)
            if not entry:
                raise LookupError('unknown question')
            answers = raw.get('answers') if isinstance(raw.get('answers'), dict) else {}
            entry.update(status='resolved' if answers else 'closed', via=clip(raw.get('via'), 20) or entry['via'],
                         answers={clip(k, 300): clip(v, 500) for k, v in answers.items() if clip(k, 300) and clip(v, 500)} or None)
            return entry

    def accept_summary(self, raw):
        source = self.task_source()
        accepted = validate_summary(raw, {task['id'] for task in source['tasks']})
        accepted['records_fingerprint'] = source['fingerprint']
        with self.lock:
            self.summary = accepted
        return accepted


def make_handler(board, port_holder):
    class Handler(BaseHTTPRequestHandler):
        server_version = 'guided-board'
        sys_version = ''

        def log_message(self, *args):
            pass

        def allowed(self):
            port = port_holder['port']
            if self.headers.get('Host') not in {f'127.0.0.1:{port}', f'localhost:{port}'}:
                return False
            query = parse_qs(urlsplit(self.path).query)
            supplied = self.headers.get('X-Board-Token') or (query.get('t') or [''])[0]
            return hmac.compare_digest(supplied.encode(), board.token.encode())

        def send(self, code, body, content_type, nonce=None):
            data = body.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            script = f"'nonce-{nonce}'" if nonce else "'none'"
            self.send_header('Content-Security-Policy',
                             f"default-src 'none'; style-src 'unsafe-inline'; script-src {script}; "
                             "connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'; "
                             "frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def send_json(self, code, value):
            self.send(code, json.dumps(value, ensure_ascii=False), 'application/json; charset=utf-8')

        def do_GET(self):
            if not self.allowed():
                return self.send(403, 'forbidden', 'text/plain; charset=utf-8')
            path = urlsplit(self.path).path
            if path == '/':
                nonce = secrets.token_urlsafe(16)
                return self.send(200, PAGE.replace('__NONCE__', nonce), 'text/html; charset=utf-8', nonce)
            if path == '/api/records':
                return self.send_json(200, board.records())
            if path == '/api/session':
                with board.lock:
                    return self.send_json(200, dict(summary=board.summary, activity=board.activity,
                                                    questions=board.questions))
            query = parse_qs(urlsplit(self.path).query)
            if path == '/api/file':
                target = (query.get('path') or [''])[0]
                if not board.touched(target):
                    return self.send_json(403, dict(ok=False, error='only files this session touched'))
                try:
                    return self.send_json(200, dict(ok=True, **read_quick(target)))
                except PermissionError:
                    return self.send_json(403, dict(ok=False, error='secret-looking file'))
                except (OSError, ValueError) as error:
                    return self.send_json(422, dict(ok=False, error=str(error)[:200]))
            if path == '/api/explain/pending':
                with board.lock:
                    return self.send_json(200, dict(items=[dict(key=k, command=c) for k, c in board.pending.items()]))
            if path == '/api/question':
                with board.lock:
                    entry = board.question((query.get('id') or [''])[0])
                    return self.send_json(200 if entry else 404, dict(question=entry))
            if path == '/report':
                try:
                    validated, files, plan, state, warnings = load_workspace(board.workspace)
                    validate_extra(validated, plan, state)
                    return self.send(200, render(plan, state, warnings, files['decisions.jsonl']),
                                     'text/html; charset=utf-8')
                except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
                    return self.send(503, 'records unreadable: ' + str(error)[:300], 'text/plain; charset=utf-8')
            return self.send(404, 'not found', 'text/plain; charset=utf-8')

        def do_POST(self):
            if not self.allowed() or 'X-Board-Token' not in self.headers:
                return self.send(403, 'forbidden', 'text/plain; charset=utf-8')
            path = urlsplit(self.path).path
            routes = {'/api/session', '/api/activity', '/api/explain', '/api/explain/answer',
                      '/api/question', '/api/question/answer', '/api/question/resolve'}
            if path not in routes:
                return self.send(404, 'not found', 'text/plain; charset=utf-8')
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                length = -1
            if not 0 < length <= MAX_BODY:
                return self.send_json(413, dict(ok=False, error='body size'))
            try:
                raw = json.loads(self.rfile.read(length))
                if path == '/api/activity':
                    return self.send_json(200, dict(ok=True, events=len(board.accept_activity(raw)['events'])))
                if path == '/api/explain':
                    return self.send_json(200, dict(ok=True, **board.explain(raw)))
                if path == '/api/explain/answer':
                    return self.send_json(200, dict(ok=True, stored=board.explained_answer(raw)))
                if path == '/api/question':
                    return self.send_json(200, dict(ok=True, question=board.ask(raw)))
                if path == '/api/question/answer':
                    return self.send_json(200, dict(ok=True, question=board.answer(raw)))
                if path == '/api/question/resolve':
                    return self.send_json(200, dict(ok=True, question=board.resolve(raw)))
                accepted = board.accept_summary(raw)
            except LookupError as error:
                return self.send_json(409, dict(ok=False, error=str(error)[:200]))
            except (ValueError, TypeError) as error:
                return self.send_json(422, dict(ok=False, error=str(error)[:200]))
            return self.send_json(200, dict(ok=True, stages=len(accepted['stages'])))

        def do_PUT(self):
            self.send(405, 'read-only', 'text/plain; charset=utf-8')

        do_DELETE = do_PATCH = do_PUT

    return Handler


def watch_parent(server, parent, interval=1.0):
    """Shut down once this process is no longer the child of `parent`."""
    def loop():
        while os.getppid() == parent:
            time.sleep(interval)
        server.shutdown()
    threading.Thread(target=loop, daemon=True).start()


def serve(workspace, port=0, stream=sys.stdout, parent=None):
    board = Board(workspace)
    first = board.records()
    if not first.get('ok'):
        raise ValueError(first['error'])
    holder = {}
    server = ThreadingHTTPServer(('127.0.0.1', port), make_handler(board, holder))
    server.daemon_threads = True
    holder['port'] = server.server_address[1]
    url = f"http://127.0.0.1:{holder['port']}/?t={board.token}"
    stream.write(json.dumps(dict(url=url, port=holder['port'], token=board.token,
                                 verification_scope=SCOPE)) + '\n')
    stream.flush()
    if parent is not None:
        watch_parent(server, parent)
    return server, board


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--parent-pid', type=int,
                        help='exit when no longer a child of this process (default: the launching parent)')
    parser.add_argument('--no-parent-watch', action='store_true',
                        help='keep serving after the launching process exits (stop with Ctrl-C)')
    args = parser.parse_args(argv)
    try:
        parent = None if args.no_parent_watch else (args.parent_pid or os.getppid())
        server, _ = serve(args.workspace, args.port, parent=parent)
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        print('error: ' + str(error), file=sys.stderr)
        return 1
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


PAGE = r'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Guided Board</title>
<style>
:root{--bg:#090c11;--grid:#18202b;--panel:#0f141b;--panel2:#141b24;--line:#243040;--line2:#33425a;--ink:#e6edf3;--sub:#8d9aab;--dim:#5d6a7c;
--ok:#2be4a0;--bad:#ff3d7f;--warn:#ffc53d;--run:#22d3ee;--muted:#6b7787;--ai:#b388ff;--focus:#22d3ee;
--mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;color-scheme:dark}
*{box-sizing:border-box}
html,body{background:var(--bg)}
body{margin:0;color:var(--ink);font:13px/1.45 system-ui,-apple-system,"Apple SD Gothic Neo",sans-serif}
h1,h2,h3,h4,p{margin:0}
button,input{font:inherit;color:inherit}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.mono{font-family:var(--mono)}
/* frame: corner brackets */
.frame{position:relative;background:var(--panel);border:1px solid var(--line)}
.frame::before,.frame::after{content:"";position:absolute;width:10px;height:10px;border-color:var(--run);border-style:solid;opacity:.7;pointer-events:none}
.frame::before{top:-1px;left:-1px;border-width:1px 0 0 1px}
.frame::after{bottom:-1px;right:-1px;border-width:0 1px 1px 0}
/* header */
.top{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 18px;align-items:center;padding:12px 16px 10px;border-bottom:1px solid var(--line);
background:linear-gradient(180deg,#0d131b,var(--bg))}
.id{display:flex;gap:10px;align-items:baseline;min-width:0}
.tag{font:700 10px/1 var(--mono);letter-spacing:.12em;color:var(--run);border:1px solid currentColor;padding:3px 6px;text-transform:uppercase;white-space:nowrap}
h1{font:600 17px/1.2 var(--mono);letter-spacing:.02em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#goal{color:var(--sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.tools{display:flex;gap:6px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
.pill{font:600 11px/1 var(--mono);letter-spacing:.04em;border:1px solid var(--line2);padding:5px 8px;color:var(--sub);white-space:nowrap}
.pill.live{color:var(--ok);border-color:currentColor}.pill.down{color:var(--bad);border-color:currentColor}.pill.warn{color:var(--warn);border-color:currentColor}
.pill.live::before{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;margin-right:6px;vertical-align:1px}
.btn{font:600 11px/1 var(--mono);letter-spacing:.04em;background:var(--panel2);border:1px solid var(--line2);padding:6px 9px;cursor:pointer;text-decoration:none;color:var(--ink)}
.btn:hover{border-color:var(--run);color:var(--run)}
.progress{grid-column:1/-1;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center}
.bar{display:flex;height:4px;background:var(--line);overflow:hidden}
.bar span{display:block;height:100%}
#counts{font:11px/1 var(--mono);color:var(--sub);white-space:nowrap}
/* shell */
.shell{display:grid;grid-template-columns:270px minmax(0,1fr);gap:0;min-height:calc(100vh - 92px)}
.shell.open{grid-template-columns:270px minmax(0,1fr) 360px}
.rail{border-right:1px solid var(--line);padding:12px;display:flex;flex-direction:column;gap:14px;min-width:0}
.rail h2,.detail h4,.lanes h2,.stage h2{font:700 10px/1 var(--mono);letter-spacing:.14em;color:var(--sub);text-transform:uppercase;margin-bottom:8px}
#attention{list-style:none;margin:0;padding:0;display:grid;gap:6px}
.att{width:100%;text-align:left;display:grid;grid-template-columns:18px minmax(0,1fr);gap:1px 8px;padding:7px 9px;background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--muted);cursor:pointer;position:relative}
.att .g{grid-row:1/3;font:700 13px/1.3 var(--mono)}
.att .k{font:700 10px/1.3 var(--mono);letter-spacing:.08em}
.att .t{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ink)}
.att .new{position:absolute;top:6px;right:7px;font:700 9px/1 var(--mono);padding:2px 4px;border:1px solid currentColor}
.att.fresh .t{padding-right:24px}
.k-decide,.k-blocked{border-left-color:var(--warn);color:var(--warn)}.k-failed{border-left-color:var(--bad);color:var(--bad)}
.k-running{border-left-color:var(--run);color:var(--run)}.k-ready{color:var(--sub)}.k-done{border-left-color:var(--ok);color:var(--ok)}
.more{font:11px var(--mono)}
.types{display:grid;gap:4px}
.type{display:grid;grid-template-columns:22px minmax(0,1fr) auto;align-items:center;gap:8px;padding:5px 8px;background:transparent;border:1px solid transparent;cursor:pointer;text-align:left}
.type:hover{border-color:var(--line2)}
.type[aria-pressed="true"]{border-color:var(--run);background:color-mix(in srgb,var(--run) 8%,transparent)}
.type .n{font:600 11px var(--mono);color:var(--sub)}
.type svg{display:block}
#search{width:100%;background:var(--panel);border:1px solid var(--line2);padding:7px 9px;font:12px var(--mono)}
#search::placeholder{color:var(--dim)}
details.all summary{cursor:pointer;font:700 10px/1 var(--mono);letter-spacing:.14em;color:var(--sub);text-transform:uppercase}
#list{margin:8px 0 0;padding:0;list-style:none;display:grid;gap:2px}
#list button{width:100%;text-align:left;background:none;border:1px solid transparent;padding:4px 6px;cursor:pointer;font-size:12px}
#list button[aria-pressed="true"]{border-color:var(--run)}
/* stage */
.stage{min-width:0;display:flex;flex-direction:column}
.ai{display:flex;gap:10px;align-items:baseline;padding:8px 14px;border-bottom:1px dashed color-mix(in srgb,var(--ai) 50%,transparent);font-size:12px;min-width:0}
.ai .tag{color:var(--ai)}
#ai-headline{color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;flex:1}
#ai-meta{font:11px var(--mono);color:var(--sub);white-space:nowrap}
.canvas{flex:1;overflow:auto;background-color:var(--bg);
background-image:radial-gradient(circle,var(--grid) 1px,transparent 1.2px);background-size:22px 22px;min-height:360px;position:relative}
.canvas::after{content:"";position:absolute;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,rgba(255,255,255,.018) 0 1px,transparent 1px 3px)}
svg{display:block}
.empty{padding:28px 18px;color:var(--sub);font-family:var(--mono)}
/* graph */
.node{cursor:pointer;outline:none}
.node .core{fill:var(--panel2);stroke:var(--line2);stroke-width:1.5}
.node .glyph{font:700 15px var(--mono);text-anchor:middle;dominant-baseline:central}
.node .halo{fill:none;stroke:var(--focus);stroke-width:1.5;opacity:0}
.node.selected .halo{opacity:1}
.node:focus-visible .core{stroke:var(--focus);stroke-width:2.5}
.node:hover .core{stroke:var(--sub)}
.node .track{fill:none;stroke:var(--line);stroke-width:3}
.node .seg{fill:none;stroke-width:3}
.node .spin{fill:none;stroke:var(--run);stroke-width:1.2;stroke-dasharray:4 7;opacity:.9;transform-box:fill-box;transform-origin:center}
.node.st-running .core{stroke:var(--run);filter:url(#glow)}
.node .title{fill:var(--ink);font-size:12px;font-weight:600;text-anchor:middle}
.node .meta{fill:var(--sub);font:10.5px var(--mono);text-anchor:middle}
.node .live{fill:var(--run);font:10.5px var(--mono);text-anchor:middle}
.node .live.idle{fill:var(--dim)}
.node .badge rect{fill:var(--bg);stroke:var(--run);stroke-width:1}
.node .badge text{fill:var(--run);font:700 9.5px var(--mono);text-anchor:middle;dominant-baseline:central}
.node .badge.err rect{stroke:var(--bad)}.node .badge.err text{fill:var(--bad)}
.hub .core{fill:color-mix(in srgb,var(--run) 10%,var(--panel2));stroke:var(--run);stroke-width:1.5}
.hub .glyph{fill:var(--run);font-size:11px;letter-spacing:.08em}
.gate polygon{fill:var(--panel2);stroke:var(--warn);stroke-width:1.5}
.gate.ok polygon{stroke:var(--ok)}
.gate text{font:700 11px var(--mono);text-anchor:middle;dominant-baseline:central;fill:var(--warn)}
.gate.ok text{fill:var(--ok)}
.gate .label{fill:var(--sub);font:10px var(--mono)}
.colhead text{fill:var(--dim);font:700 10px var(--mono);letter-spacing:.12em}
.colhead.ai text{fill:var(--ai)}
.colhead line{stroke:var(--line);stroke-dasharray:2 4}
.colhead.ai line{stroke:color-mix(in srgb,var(--ai) 60%,transparent)}
.link{fill:none;stroke:var(--line2);stroke-width:1.3;transition:opacity .2s,stroke .2s}
.link.dep{marker-end:url(#arrow)}
.link.gate-link{stroke:var(--warn);stroke-dasharray:2 4;opacity:.55}
.link.act{stroke:var(--run);stroke-dasharray:1 6;stroke-linecap:round;opacity:.55}
.link.stage{stroke:var(--ai);stroke-dasharray:6 5;opacity:.5}
.link.hot{stroke:var(--focus);stroke-width:2;opacity:1;marker-end:url(#arrow-hot)}
.link.hot.out{stroke-dasharray:7 4}
.motion .link.hot{animation:march 1.2s linear infinite}
.motion .link.act{animation:march 2.4s linear infinite}
.motion .node.st-running .spin{animation:spin 6s linear infinite}
.linklabel{fill:var(--focus);font:10px var(--mono);text-anchor:middle;opacity:0}
.has-sel .linklabel.hot{opacity:1}
.has-sel .node:not(.selected):not(.near),.dimmed{opacity:.28}
.has-sel .link.dep:not(.hot),.has-sel .link.gate-link{opacity:.15}
.packet{fill:var(--run);filter:url(#glow)}
.packet.err{fill:var(--bad)}
.ping{fill:none;stroke:var(--run);stroke-width:2}
.ping.err{stroke:var(--bad)}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes march{to{stroke-dashoffset:-22}}
@media (prefers-reduced-motion:reduce){.motion .link.hot,.motion .link.act,.motion .node.st-running .spin,.motion .dots{animation:none}}
/* lanes */
.lanes{border-top:1px solid var(--line);padding:10px 14px 12px}
.lanes-head{display:flex;justify-content:space-between;align-items:baseline}
.lanes-head span{font:10px var(--mono);color:var(--dim)}
#lanes{display:grid;gap:3px}
.lane{display:grid;grid-template-columns:160px minmax(0,1fr);gap:8px;align-items:center;cursor:pointer;background:none;border:0;padding:0;text-align:left}
.lane .name{font:11px var(--mono);color:var(--sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lane .track{position:relative;height:12px;background:color-mix(in srgb,var(--line) 45%,transparent)}
.lane .ev{position:absolute;top:2px;height:8px;min-width:3px;background:var(--ok);opacity:.8}
.lane .ev.error{background:var(--bad);opacity:1}
.lane .ev.running{background:var(--run);opacity:1;box-shadow:0 0 6px var(--run)}
.lane.sel .name{color:var(--run)}
/* detail */
.detail{border-left:1px solid var(--line);padding:12px 14px;min-width:0;overflow:auto;max-height:calc(100vh - 92px);position:sticky;top:0}
.detail-head{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px}
.detail h3{font-size:15px;line-height:1.35;margin:6px 0 2px}
.detail .sub{font:11px var(--mono);color:var(--sub)}
.detail h4{margin:16px 0 6px}
.props{display:grid;grid-template-columns:auto minmax(0,1fr);gap:4px 12px;font-size:12px}
.props dt{font:11px var(--mono);color:var(--dim)}
.props dd{margin:0;overflow-wrap:anywhere}
.detail ul{list-style:none;margin:0;padding:0;display:grid;gap:4px}
.row{display:grid;grid-template-columns:auto minmax(0,1fr);gap:0 8px;font-size:12px}
.row small{grid-column:2;color:var(--sub);font:10.5px var(--mono);overflow-wrap:anywhere}
.row .when{font:10.5px var(--mono);color:var(--dim)}
.detail .link-btn{width:100%;text-align:left;background:var(--panel);border:1px solid var(--line);padding:5px 8px;cursor:pointer;font-size:12px}
.detail .link-btn:hover{border-color:var(--run)}
.answer{margin-top:8px;padding:7px 9px;border-left:2px solid var(--ok);font-size:13px}
details.story{margin-top:16px}
details.story summary{cursor:pointer;font:700 10px/1 var(--mono);letter-spacing:.14em;color:var(--sub);text-transform:uppercase}
details.story ul{margin-top:8px}
.note{margin-top:10px;padding:7px 9px;border:1px solid var(--warn);color:var(--warn);font-size:12px}
.ask{padding:10px 12px;border-color:var(--warn)}
.ask h2{color:var(--warn)}
.ask-form{display:grid;gap:10px}
.ask fieldset{border:0;margin:0;padding:0;display:grid;gap:5px}
.ask legend{display:flex;gap:8px;align-items:baseline;margin-bottom:6px;padding:0}
.ask legend .tag{color:var(--warn)}
.qtext{font-size:13px;font-weight:600}
.opt{display:grid;grid-template-columns:18px minmax(0,1fr);gap:8px;align-items:start;padding:6px 8px;border:1px solid var(--line);cursor:pointer}
.opt:hover{border-color:var(--warn)}
.opt:has(input:checked){border-color:var(--warn);background:color-mix(in srgb,var(--warn) 9%,transparent)}
.opt input[type=radio],.opt input[type=checkbox]{margin:2px 0 0;accent-color:var(--warn)}
.opt small{display:block;color:var(--sub);font-size:11px}
.opt.other{grid-template-columns:minmax(0,1fr)}
.opt.other input{width:100%;background:var(--panel);border:1px solid var(--line2);padding:6px 8px;font-size:12px}
.ask-actions{display:flex;gap:10px;align-items:center}
.btn.primary{border-color:var(--warn);color:var(--warn)}
.btn:disabled{opacity:.5;cursor:default}
.ask-status{font:11px var(--mono);color:var(--sub)}
.ask-done{font-size:12px;color:var(--sub)}
.ask-done b{color:var(--ok);font-weight:600}
.cmd{border-bottom:1px dotted var(--sub);cursor:help}
.cmd:hover,.cmd:focus-visible{color:var(--run);border-bottom-color:var(--run)}
.peek{margin-left:6px;font:600 10px/1 var(--mono);padding:3px 6px}
.tip{position:absolute;z-index:20;width:330px;max-width:calc(100vw - 16px);padding:9px 11px;background:var(--panel2);border:1px solid var(--run);
box-shadow:0 0 0 1px rgba(0,0,0,.4),0 0 18px color-mix(in srgb,var(--run) 25%,transparent);font-size:12px;pointer-events:none}
.tip code{display:block;font:11px var(--mono);color:var(--sub);margin-bottom:6px;overflow-wrap:anywhere}
.tip .wait{color:var(--run)}
.dots{display:inline-block;width:8px;height:8px;margin-right:6px;border:1.5px solid var(--run);border-right-color:transparent;border-radius:50%;vertical-align:-1px}
.motion .dots{animation:spin .8s linear infinite}
.qv{position:fixed;inset:0;z-index:30;background:rgba(5,8,12,.72);display:grid;place-items:center;padding:16px}
.qv[hidden]{display:none}
.qv-panel{width:min(980px,100%);height:min(82vh,900px);display:flex;flex-direction:column;padding:12px 14px}
.qv-head{display:flex;justify-content:space-between;gap:12px;align-items:start;margin-bottom:8px}
.qv-head h2{font-size:14px;color:var(--run);overflow-wrap:anywhere}
.qv-body{flex:1;margin:0;overflow:auto;background:var(--bg);border:1px solid var(--line);padding:8px 0;font:12px/1.5 var(--mono);counter-reset:ln;white-space:pre;tab-size:4}
.qv-body .ln{display:block;padding-right:12px}
.qv-body .ln::before{counter-increment:ln;content:counter(ln);display:inline-block;width:4.2em;padding-right:12px;text-align:right;color:var(--dim);user-select:none}
.s-passed,.s-approved,.s-answered,.s-ok{color:var(--ok)}.s-failed,.s-rejected,.s-mixed,.s-error{color:var(--bad)}
.s-blocked,.s-stale,.s-revision_requested,.s-pending-decision{color:var(--warn)}.s-running{color:var(--run)}
.s-pending,.s-cancelled,.s-unrecorded,.s-not_run{color:var(--muted)}
.muted{color:var(--sub)}
@media (max-width:999px){
  .shell,.shell.open{grid-template-columns:minmax(0,1fr)}
  .rail{border-right:0;border-bottom:1px solid var(--line)}
  .detail{border-left:0;border-top:1px solid var(--line);max-height:none;position:static}
  .top{grid-template-columns:minmax(0,1fr)}.tools{justify-content:flex-start}
}
</style>
</head>
<body>
<header class="top">
  <div class="id"><span class="tag">run</span><h1 id="run">—</h1><p id="goal"></p></div>
  <div class="tools">
    <span id="conn" class="pill" role="status">연결 중</span>
    <button id="motion" class="btn" type="button" aria-pressed="true">움직임 끄기</button>
    <a id="report" class="btn" target="_blank" rel="noopener">기록 스냅샷</a>
  </div>
  <div class="progress"><div class="bar" id="bar" aria-hidden="true"></div><p id="counts"></p></div>
</header>
<div class="shell" id="shell">
  <aside class="rail" aria-label="탐색">
    <section class="ask frame" id="ask" aria-labelledby="ask-title" hidden>
      <h2 id="ask-title">Claude 질문</h2>
      <div id="ask-body"></div>
    </section>
    <section aria-labelledby="att-title">
      <h2 id="att-title">지금 필요한 것</h2>
      <ul id="attention"><li class="muted">기록을 불러오는 중입니다.</li></ul>
    </section>
    <section aria-labelledby="types-title">
      <h2 id="types-title">객체 · 상태</h2>
      <div class="types" id="types"></div>
    </section>
    <section>
      <label class="sr" for="search">작업 찾기</label>
      <input id="search" type="search" placeholder="작업 찾기" autocomplete="off">
    </section>
    <details class="all" id="all"><summary>전체 작업</summary><ul id="list"></ul></details>
  </aside>
  <main class="stage">
    <section class="ai" id="ai" aria-label="AI 요약"><span class="tag">AI 요약 · 참고용</span><p id="ai-headline">대기 중</p><span id="ai-meta"></span></section>
    <h2 class="sr" id="pipe-title">작업 그래프</h2>
    <div class="canvas" id="canvas"><p class="empty">기록을 불러오는 중입니다.</p></div>
    <section class="lanes" aria-labelledby="lanes-title">
      <div class="lanes-head"><h2 id="lanes-title">최근 10분 활동</h2><span id="lanes-axis">← 10분 전 · 지금 →</span></div>
      <div id="lanes"></div>
    </section>
  </main>
  <aside class="detail frame" id="detail" aria-labelledby="detail-title" hidden>
    <div class="detail-head"><h2 id="detail-title" class="tag">객체</h2><button id="clear" class="btn" type="button" aria-label="상세 닫기">✕ 닫기</button></div>
    <div id="detail-body"></div>
  </aside>
</div>
<p id="announce" class="sr" aria-live="polite"></p>
<div id="tip" class="tip" role="tooltip" hidden></div>
<div id="qv" class="qv" hidden>
  <div class="qv-panel frame" role="dialog" aria-modal="true" aria-labelledby="qv-title">
    <div class="qv-head"><div><h2 id="qv-title" class="mono"></h2><p id="qv-meta" class="sub"></p></div>
      <button id="qv-close" class="btn" type="button" aria-label="퀵뷰 닫기">✕ 닫기</button></div>
    <pre id="qv-body" class="qv-body" tabindex="0"></pre>
  </div>
</div>
<script nonce="__NONCE__">
(() => {
'use strict';
const token = new URLSearchParams(location.search).get('t') || '';
const headers = {'X-Board-Token': token};
const $ = id => document.getElementById(id);
const NS = 'http://www.w3.org/2000/svg';
const HUB = '__session';
const STATUS = {passed:['✓','통과'],running:['▶','진행'],failed:['✗','실패'],blocked:['⏸','차단'],stale:['↺','재검증'],
  cancelled:['⊘','취소'],pending:['○','대기']};
const RESULT = {passed:['✓','통과'],failed:['✗','실패'],not_run:['–','미실행'],unrecorded:['○','미기록'],stale:['↺','재검증'],mixed:['!','상충']};
const OUTCOME = {answered:'답변됨',approved:'승인',rejected:'반려',revision_requested:'수정 요청'};
const COLOR = {passed:'--ok',failed:'--bad',mixed:'--bad',blocked:'--warn',stale:'--warn',running:'--run',ok:'--ok',error:'--bad'};
const color = s => `var(${COLOR[s] || '--muted'})`;
const st = s => STATUS[s] || ['○', s];
const rs = r => RESULT[r] || ['○', r];
const WINDOW = 10 * 60 * 1000;
let records = null, summary = null, activity = null, drawnKey = '', firstLoad = true, failures = 0;
let filter = '', query = '';
let seenEvents = null, seenAttention = null, freshAttention = new Set();
let lastStatus = new Map();
const motionOn = () => document.body.classList.contains('motion') && !matchMedia('(prefers-reduced-motion: reduce)').matches;
let selected = '';
try { selected = decodeURIComponent((location.hash.match(/^#task=(.+)$/) || [])[1] || ''); } catch (_) { selected = ''; }
let motion = !matchMedia('(prefers-reduced-motion: reduce)').matches;
try { if (localStorage.getItem('guided-board-motion') === 'off') motion = false; } catch (_) {}
$('report').href = '/report?t=' + encodeURIComponent(token);
const measure = document.createElement('canvas').getContext('2d');

function setMotion(on) {
  motion = on;
  document.body.classList.toggle('motion', on);
  $('motion').setAttribute('aria-pressed', String(on));
  $('motion').textContent = on ? '움직임 끄기' : '움직임 켜기';
  try { localStorage.setItem('guided-board-motion', on ? 'on' : 'off'); } catch (_) {}
}
$('motion').addEventListener('click', () => setMotion(!motion));
setMotion(motion);

function el(name, attrs, parent, text) {
  const node = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs || {})) if (v !== undefined && v !== null) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  if (parent) parent.appendChild(node);
  return node;
}
function h(tag, props, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (k === 'class') node.className = v; else if (k === 'on') node.addEventListener('click', v);
    else if (v !== undefined && v !== null && v !== false) node.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false) node.append(kid);
  return node;
}
function cut(s, n) { s = String(s || ''); return s.length > n ? s.slice(0, n - 1) + '…' : s; }
function wrap(text, width, lines) {
  measure.font = '600 12px system-ui, -apple-system, sans-serif';
  const out = []; let line = '';
  for (const ch of Array.from(String(text || ''))) {
    if (measure.measureText(line + ch).width > width) {
      out.push(line); line = ch.trim() ? ch : '';
      if (out.length === lines) break;
    } else line += ch;
  }
  if (out.length < lines && line) out.push(line);
  if (out.join('').length < String(text || '').length) out[out.length - 1] = out[out.length - 1].replace(/.$/, '…');
  return out.length ? out : [''];
}
const clock = ms => { const t = Math.max(0, Math.floor(ms / 1000)), hh = Math.floor(t / 3600), m = Math.floor(t % 3600 / 60), s = t % 60;
  const p = n => String(n).padStart(2, '0'); return hh ? `${hh}:${p(m)}:${p(s)}` : `${p(m)}:${p(s)}`; };
const hhmm = iso => { const d = new Date(iso); return isNaN(d) ? String(iso || '') : d.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', second: '2-digit'}); };
const events = () => (activity && activity.events) || [];
const eventsOf = id => events().filter(e => e.task === id);
const runningCall = id => eventsOf(id).filter(e => e.phase === 'running').pop();
const lastCall = id => eventsOf(id).filter(e => e.phase !== 'running').pop();
const callCount = id => eventsOf(id).length;
const errorCount = id => eventsOf(id).filter(e => e.phase === 'error').length;
const recentlyActive = id => eventsOf(id).some(e => e.phase === 'running' || Date.now() - (e.ended_at || e.started_at) < 60000);

/* ---------- selection ---------- */
function select(id, opts) {
  const previous = selected;
  const known = id === HUB || (records && records.tasks.some(t => t.id === id)) || (records && records.decisions.some(d => 'd:' + d.id === id));
  selected = known ? id : '';
  history.replaceState(null, '', location.pathname + location.search + (selected && selected !== HUB && !selected.startsWith('d:') ? '#task=' + encodeURIComponent(selected) : ''));
  applySelection();
  renderDetail();
  const t = selected && records.tasks.find(x => x.id === selected);
  $('announce').textContent = t ? `선택: ${t.title}, ${st(t.status)[1]}` : selected === HUB ? '선택: 세션' : (previous ? '선택 해제' : '');
  if (!selected && previous && opts && opts.returnFocus) {
    const node = document.querySelector(`.node[data-id="${CSS.escape(previous)}"]`);
    if (node) node.focus();
  }
  if (opts && opts.reveal && selected && matchMedia('(max-width: 999px)').matches) $('detail').scrollIntoView({block: 'nearest'});
}
$('clear').addEventListener('click', () => select('', {returnFocus: true}));
addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  if (!$('qv').hidden) { closeQuick(); return; }
  if (selected) select('', {returnFocus: true});
});

function neighbors(id) {
  const set = new Set();
  if (!records) return set;
  if (id.startsWith('d:')) { records.tasks.forEach(t => { if (t.decision_ids.includes(id.slice(2))) set.add(t.id); }); return set; }
  if (id === HUB) { records.tasks.forEach(t => { if (t.status === 'running' || recentlyActive(t.id)) set.add(t.id); }); return set; }
  const t = records.tasks.find(x => x.id === id);
  (t ? t.depends_on : []).forEach(d => set.add(d));
  (t ? t.decision_ids : []).forEach(d => set.add('d:' + d));
  if (t && (t.status === 'running' || recentlyActive(t.id))) set.add(HUB);
  records.tasks.forEach(x => { if (x.depends_on.includes(id)) set.add(x.id); });
  return set;
}
function matches(t) {
  if (filter && (filter === 'decision' ? !t.decision_ids.length : t.status !== filter)) return false;
  if (query && !(t.title + ' ' + t.id).toLowerCase().includes(query)) return false;
  return true;
}
function applySelection() {
  const svg = document.querySelector('#canvas svg');
  const near = selected ? neighbors(selected) : new Set();
  if (svg) {
    svg.classList.toggle('has-sel', !!selected);
    svg.querySelectorAll('.node').forEach(n => {
      const id = n.dataset.id;
      n.classList.toggle('selected', id === selected);
      n.classList.toggle('near', near.has(id));
      n.setAttribute('aria-pressed', String(id === selected));
      const t = records.tasks.find(x => x.id === id);
      n.classList.toggle('dimmed', !selected && !!t && (!!filter || !!query) && !matches(t));
    });
    svg.querySelectorAll('[data-from]').forEach(p => {
      const into = !!selected && p.dataset.to === selected, out = !!selected && p.dataset.from === selected;
      p.classList.toggle('hot', into || out);
      p.classList.toggle('in', into);
      p.classList.toggle('out', out);
    });
  }
  document.querySelectorAll('#list button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.task === selected)));
  document.querySelectorAll('.lane').forEach(l => l.classList.toggle('sel', l.dataset.task === selected));
  $('detail').hidden = !selected;
  $('shell').classList.toggle('open', !!selected);
}

/* ---------- graph ---------- */
function columns(rec, sum) {
  const tasks = new Map(rec.tasks.map(t => [t.id, t]));
  if (sum && sum.stages && sum.stages.length) {
    const used = new Set();
    const cols = sum.stages.map(s => {
      const items = s.refs.filter(r => tasks.has(r) && !used.has(r));
      items.forEach(r => used.add(r));
      return {id: s.id, label: s.label, ai: true, items};
    }).filter(c => c.items.length);
    const rest = rec.tasks.filter(t => !used.has(t.id)).map(t => t.id);
    if (rest.length) cols.push({id: '__rest', label: '미분류', ai: false, items: rest});
    return cols;
  }
  const level = {};
  const depth = id => {
    if (level[id] !== undefined) return level[id];
    level[id] = 0;
    const t = tasks.get(id);
    level[id] = t.depends_on.length ? 1 + Math.max(...t.depends_on.filter(d => tasks.has(d)).map(depth), -1) : 0;
    return level[id];
  };
  rec.tasks.forEach(t => depth(t.id));
  const cols = [];
  rec.tasks.forEach(t => { (cols[level[t.id]] ||= {id: 'L' + level[t.id], label: (level[t.id] + 1) + '단계', ai: false, items: []}).items.push(t.id); });
  return cols.filter(Boolean);
}
const R = 22;
function arc(cx, cy, r, a0, a1) {
  const p = a => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  const [x0, y0] = p(a0), [x1, y1] = p(a1);
  return `M${x0.toFixed(2)},${y0.toFixed(2)} A${r},${r} 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${x1.toFixed(2)},${y1.toFixed(2)}`;
}
function liveText(t) {
  const now = runningCall(t.id);
  const say = e => { const d = doing(e); return cut(d.verb + (d.what ? ' ' + d.what : ''), 24); };
  if (now) return {text: `◌ ${say(now)}`, idle: false};
  const last = lastCall(t.id);
  return {text: last ? `● ${say(last)}` : '', idle: true};
}
function metaText(t) {
  const parts = [`${st(t.status)[0]} ${st(t.status)[1]}`];
  if (t.status === 'running' && t.started_at) parts.push(clock(Date.now() - Date.parse(t.started_at)));
  if (t.attempts > 1) parts.push(`${t.attempts}번째 시도`);
  return parts.join(' · ');
}
let geometry = {pos: new Map(), hub: null, paths: new Map()};
function structureKey() {
  const box = $('canvas');
  const active = records.tasks.filter(t => t.status === 'running' || recentlyActive(t.id)).map(t => t.id).join(',');
  return [records.fingerprint, summary ? summary.received_at : '', Math.round(box.clientWidth / 40), active].join('|');
}
function draw() {
  const box = $('canvas');
  if (!records) return;
  const key = structureKey();
  if (key === drawnKey) return liveUpdate();
  drawnKey = key;
  const focused = document.activeElement && document.activeElement.closest ? document.activeElement.closest('.node') : null;
  const focusedId = focused ? focused.dataset.id : '';
  const tasks = new Map(records.tasks.map(t => [t.id, t]));
  const decisions = new Map(records.decisions.map(d => [d.id, d]));
  const cols = columns(records, summary);
  const narrow = box.clientWidth < 640;
  const colW = narrow ? 170 : 210, rowH = 132, pad = 30, laneH = 104, X0 = pad + 110;
  const pos = new Map();
  cols.forEach((col, ci) => col.items.forEach((id, ri) => pos.set(id, {x: X0 + ci * colW, y: laneH + 40 + R + ri * rowH, col: ci})));
  const width = Math.max(X0 + (cols.length - 1) * colW + 120, 420);
  const height = laneH + 40 + Math.max(...cols.map(c => c.items.length), 1) * rowH + 10;
  box.textContent = '';
  const scale = Math.min(1.3, Math.max(0.6, (box.clientWidth - 2) / width));
  const svg = el('svg', {width: Math.round(width * scale), height: Math.round(height * scale), viewBox: `0 0 ${width} ${height}`, role: 'group',
    'aria-label': `작업 ${records.tasks.length}개, 결정 ${records.decisions.length}개 그래프`}, box);
  const defs = el('defs', {}, svg);
  const glow = el('filter', {id: 'glow', x: '-50%', y: '-50%', width: '200%', height: '200%'}, defs);
  el('feGaussianBlur', {stdDeviation: 2.4, result: 'b'}, glow);
  const merge = el('feMerge', {}, glow); el('feMergeNode', {in: 'b'}, merge); el('feMergeNode', {in: 'SourceGraphic'}, merge);
  [['arrow', 'var(--line2)'], ['arrow-hot', 'var(--focus)']].forEach(([mid, fill]) => {
    const m = el('marker', {id: mid, viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto', markerUnits: 'userSpaceOnUse'}, defs);
    el('path', {d: 'M0,0 L10,5 L0,10 z', style: `fill:${fill}`}, m);
  });
  const gLinks = el('g', {}, svg), gLabels = el('g', {}, svg), gNodes = el('g', {}, svg), gFx = el('g', {class: 'fx'}, svg);
  // column heads
  cols.forEach((col, ci) => {
    const x = X0 + ci * colW;
    const g = el('g', {class: 'colhead' + (col.ai ? ' ai' : '')}, gNodes);
    el('text', {x: x, y: laneH + 6, 'text-anchor': 'middle'}, g, cut((col.ai ? 'AI · ' : '') + col.label, 22).toUpperCase());
    el('line', {x1: x - colW / 2 + 14, x2: x + colW / 2 - 14, y1: laneH + 14, y2: laneH + 14}, g);
  });
  const paths = new Map();
  const curve = (a, b, ra, rb) => {
    if (Math.abs(a.x - b.x) < 1) return `M${a.x - ra},${a.y} C${a.x - ra - 70},${a.y} ${b.x - rb - 70},${b.y} ${b.x - rb},${b.y}`;
    return `M${a.x + ra},${a.y} C${a.x + ra + 60},${a.y} ${b.x - rb - 60},${b.y} ${b.x - rb},${b.y}`;
  };
  const label = (d, text, from, to) => {
    const p = el('path', {d, class: 'sr'}, gLabels); // invisible measuring path
    const len = p.getTotalLength ? p.getTotalLength() : 0; const m = len ? p.getPointAtLength(len / 2) : {x: 0, y: 0};
    p.remove();
    el('text', {x: m.x, y: m.y - 5, class: 'linklabel', 'data-from': from, 'data-to': to}, gLabels, text);
  };
  // dependency links
  records.tasks.forEach(t => t.depends_on.forEach(dep => {
    if (!pos.has(dep) || !pos.has(t.id)) return;
    const d = curve(pos.get(dep), pos.get(t.id), R + 6, R + 8);
    el('path', {d, class: 'link dep', 'data-from': dep, 'data-to': t.id}, gLinks);
    label(d, '선행', dep, t.id);
  }));
  // AI stage links between column heads
  if (summary && summary.stages && !narrow) {
    const heads = new Map(cols.map((c, i) => [c.id, X0 + i * colW]));
    (summary.edges && summary.edges.length ? summary.edges : summary.stages.slice(1).map((s, i) => ({from: summary.stages[i].id, to: s.id})))
      .forEach(e => { if (heads.has(e.from) && heads.has(e.to)) el('path', {d: `M${heads.get(e.from) + 50},${laneH + 2} L${heads.get(e.to) - 50},${laneH + 2}`, class: 'link stage'}, gLinks); });
  }
  // control lane: session hub and decision gates
  const hub = {x: pad + 18, y: 46};
  const gatePos = new Map();
  const perCol = new Map();
  records.decisions.forEach(dec => {
    const gated = records.tasks.filter(t => t.decision_ids.includes(dec.id)).map(t => pos.get(t.id)).filter(Boolean);
    const col = gated.length ? Math.min(...gated.map(p => p.col)) : 0;
    const k = perCol.get(col) || 0; perCol.set(col, k + 1);
    gatePos.set(dec.id, {x: X0 + col * colW - 30 + k * 46, y: 46});
  });
  records.tasks.forEach(t => t.decision_ids.forEach(d => {
    const a = gatePos.get(d), b = pos.get(t.id);
    if (!a || !b) return;
    const path = `M${a.x},${a.y + 12} C${a.x},${a.y + 50} ${b.x},${b.y - R - 50} ${b.x},${b.y - R - 6}`;
    el('path', {d: path, class: 'link gate-link', 'data-from': 'd:' + d, 'data-to': t.id}, gLinks);
  }));
  records.tasks.forEach(t => {
    if (!(t.status === 'running' || recentlyActive(t.id)) || !pos.has(t.id)) return;
    const b = pos.get(t.id);
    const d = `M${hub.x + 18},${hub.y} C${hub.x + 120},${hub.y} ${b.x},${b.y - R - 70} ${b.x},${b.y - R - 6}`;
    paths.set(t.id, el('path', {d, class: 'link act', 'data-from': HUB, 'data-to': t.id}, gLinks));
  });
  // hub node
  const hg = el('g', {class: 'node hub', 'data-id': HUB, tabindex: 0, role: 'button', 'aria-label': '세션 활동'}, gNodes);
  el('circle', {class: 'halo', cx: hub.x, cy: hub.y, r: 26}, hg);
  const oct = Array.from({length: 8}, (_, i) => { const a = Math.PI / 8 + i * Math.PI / 4; return `${(hub.x + 19 * Math.cos(a)).toFixed(1)},${(hub.y + 19 * Math.sin(a)).toFixed(1)}`; }).join(' ');
  el('polygon', {class: 'core', points: oct}, hg);
  el('text', {class: 'glyph', x: hub.x, y: hub.y}, hg, 'AI');
  el('text', {class: 'meta', x: hub.x, y: hub.y + 34, 'data-live': 'hub'}, hg, '');
  // decision gates
  records.decisions.forEach(dec => {
    const p = gatePos.get(dec.id);
    const ok = dec.status === 'resolved' && ['answered', 'approved'].includes(dec.outcome);
    const g = el('g', {class: 'node gate' + (ok ? ' ok' : ''), 'data-id': 'd:' + dec.id, tabindex: 0, role: 'button',
      'aria-label': `결정 ${dec.id}, ${ok ? '해결' : dec.status === 'resolved' ? (OUTCOME[dec.outcome] || dec.outcome) : '대기'}`}, gNodes);
    el('circle', {class: 'halo', cx: p.x, cy: p.y, r: 18}, g);
    el('polygon', {points: `${p.x},${p.y - 12} ${p.x + 12},${p.y} ${p.x},${p.y + 12} ${p.x - 12},${p.y}`}, g);
    el('text', {x: p.x, y: p.y}, g, ok ? '✓' : dec.status === 'resolved' ? '!' : '?');
    el('text', {class: 'label', x: p.x, y: p.y + 26, 'text-anchor': 'middle'}, g, cut(dec.id, 14));
  });
  // task nodes
  const changed = [];
  pos.forEach((p, id) => {
    const t = tasks.get(id);
    const g = el('g', {class: `node task st-${t.status}`, 'data-id': id, tabindex: 0, role: 'button',
      'aria-label': `${t.title}, ${st(t.status)[1]}, 시도 ${t.attempts}/${t.max_attempts}`}, gNodes);
    el('circle', {class: 'halo', cx: p.x, cy: p.y, r: R + 14}, g);
    if (t.status === 'running') el('circle', {class: 'spin', cx: p.x, cy: p.y, r: R + 10}, g);
    el('circle', {class: 'track', cx: p.x, cy: p.y, r: R + 5}, g);
    const n = t.checks.length, gap = n > 1 ? 0.18 : 0;
    t.checks.forEach((c, i) => {
      if (c.result === 'unrecorded') return;
      const a0 = -Math.PI / 2 + i * 2 * Math.PI / n + gap / 2, a1 = -Math.PI / 2 + (i + 1) * 2 * Math.PI / n - gap / 2;
      const seg = el('path', {class: 'seg', d: arc(p.x, p.y, R + 5, a0, Math.min(a1, a0 + 2 * Math.PI - 0.01)), style: `stroke:${color(c.result)}`}, g);
      el('title', {}, seg, `${c.id}: ${rs(c.result)[1]}`);
    });
    el('circle', {class: 'core', cx: p.x, cy: p.y, r: R, style: t.status === 'running' ? '' : `stroke:${color(t.status)}`}, g);
    el('text', {class: 'glyph', x: p.x, y: p.y, style: `fill:${color(t.status)}`}, g, st(t.status)[0]);
    const badge = el('g', {class: 'badge', 'data-badge': id}, g);
    el('rect', {x: p.x + R - 6, y: p.y - R - 8, width: 26, height: 14, rx: 2}, badge);
    el('text', {x: p.x + R + 7, y: p.y - R - 1}, badge, '');
    const lines = wrap(t.title, colW - 30, 2);
    lines.forEach((line, i) => el('text', {class: 'title', x: p.x, y: p.y + R + 22 + i * 15}, g, line));
    const y2 = p.y + R + 22 + lines.length * 15;
    el('text', {class: 'meta', x: p.x, y: y2, 'data-meta': id}, g, metaText(t));
    el('text', {class: 'live', x: p.x, y: y2 + 14, 'data-live': id}, g, '');
    g.addEventListener('click', () => select(selected === id ? '' : id, {reveal: true}));
    if (lastStatus.has(id) && lastStatus.get(id) !== t.status) changed.push(id);
  });
  svg.querySelectorAll('.gate, .hub').forEach(g => {
    const id = g.dataset.id;
    g.addEventListener('click', () => select(selected === id ? '' : id, {reveal: true}));
  });
  svg.querySelectorAll('.node').forEach(g => g.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); const id = g.dataset.id; select(selected === id ? '' : id, {reveal: true}); }
  }));
  geometry = {pos, hub, paths, fx: gFx};
  if (!firstLoad && motionOn()) changed.forEach(id => ping(id, records.tasks.find(t => t.id === id).status === 'failed'));
  lastStatus = new Map(records.tasks.map(t => [t.id, t.status]));
  applySelection();
  liveUpdate();
  if (focusedId) { const again = svg.querySelector(`.node[data-id="${CSS.escape(focusedId)}"]`); if (again) again.focus(); }
}

/* per-second updates without rebuilding the graph */
function liveUpdate() {
  if (!records) return;
  records.tasks.forEach(t => {
    const meta = document.querySelector(`[data-meta="${CSS.escape(t.id)}"]`);
    if (meta) meta.textContent = metaText(t);
    const live = document.querySelector(`[data-live="${CSS.escape(t.id)}"]`);
    if (live) { const l = liveText(t); live.textContent = l.text; live.classList.toggle('idle', l.idle); }
    const badge = document.querySelector(`[data-badge="${CSS.escape(t.id)}"]`);
    if (badge) {
      const n = callCount(t.id), errs = errorCount(t.id);
      badge.style.display = n ? '' : 'none';
      badge.classList.toggle('err', errs > 0);
      const label = (n > 99 ? '99+' : String(n)) + (errs ? ` ✗${errs}` : '');
      badge.querySelector('text').textContent = label;
      const w = 12 + label.length * 6.2;
      badge.querySelector('rect').setAttribute('width', w.toFixed(1));
      badge.querySelector('text').setAttribute('x', (Number(badge.querySelector('rect').getAttribute('x')) + w / 2).toFixed(1));
    }
  });
  const hubText = document.querySelector('[data-live="hub"]');
  if (hubText) { const now = runningCall(HUB); hubText.textContent = now ? `◌ ${doing(now).verb}` : '세션'; }
  // new tool calls travel from the session to their node
  const ids = new Set(events().map(e => e.id + ':' + e.phase));
  if (seenEvents && motionOn()) events().forEach(e => {
    if (seenEvents.has(e.id + ':' + e.phase)) return;
    if (e.phase === 'running' && !seenEvents.has(e.id + ':running')) packet(e.task, false);
    if (e.phase === 'error') ping(e.task, true);
  });
  seenEvents = ids;
  renderLanes();
  if (selected) refreshDetailLive();
}
function packet(task, err) {
  const path = geometry.paths.get(task);
  if (!path || !geometry.fx) { ping(task, err); return; }
  const len = path.getTotalLength();
  const dot = el('circle', {class: 'packet' + (err ? ' err' : ''), r: 3.5}, geometry.fx);
  const t0 = performance.now(), D = 700;
  const step = now => {
    const k = Math.min(1, (now - t0) / D), pt = path.getPointAtLength(len * (1 - Math.pow(1 - k, 3)));
    dot.setAttribute('cx', pt.x); dot.setAttribute('cy', pt.y);
    if (k < 1) requestAnimationFrame(step); else { dot.remove(); ping(task, err); }
  };
  requestAnimationFrame(step);
}
function ping(task, err) {
  const p = task === HUB ? geometry.hub : geometry.pos.get(task);
  if (!p || !geometry.fx) return;
  const ring = el('circle', {class: 'ping' + (err ? ' err' : ''), cx: p.x, cy: p.y, r: R,
    style: 'transform-box:fill-box;transform-origin:center'}, geometry.fx);
  ring.animate([{transform: 'scale(1)', opacity: 0.9}, {transform: 'scale(2)', opacity: 0}],
    {duration: 650, easing: 'cubic-bezier(0.2, 0, 0.38, 0.9)'}).onfinish = () => ring.remove();
}

/* ---------- activity lanes ---------- */
function renderLanes() {
  const box = $('lanes');
  const now = Date.now();
  const focusedLane = document.activeElement && document.activeElement.classList.contains('lane') ? document.activeElement.dataset.task : '';
  const recent = events().filter(e => e.phase === 'running' || now - (e.ended_at || e.started_at) < WINDOW);
  const order = [...(records ? records.tasks.map(t => t.id) : []), HUB].filter(id => recent.some(e => e.task === id));
  box.textContent = '';
  if (!order.length) { box.append(h('p', {class: 'muted mono'}, activity ? '최근 10분 활동 없음' : 'Mod 연결 대기')); return; }
  order.forEach(id => {
    const t = records && records.tasks.find(x => x.id === id);
    const track = h('span', {class: 'track'});
    recent.filter(e => e.task === id).forEach(e => {
      const end = e.phase === 'running' ? now : (e.ended_at || e.started_at);
      const left = Math.max(0, (e.started_at - (now - WINDOW)) / WINDOW * 100);
      const width = Math.max(0.3, (end - Math.max(e.started_at, now - WINDOW)) / WINDOW * 100);
      track.append(h('span', {class: 'ev ' + e.phase, style: `left:${left.toFixed(2)}%;width:${width.toFixed(2)}%`,
        title: `${doing(e).verb} ${doing(e).what} · ${e.phase === 'running' ? '진행 중' : e.phase === 'error' ? '실패' : '완료'}`}));
    });
    box.append(h('button', {type: 'button', class: 'lane' + (id === selected ? ' sel' : ''), 'data-task': id,
      'aria-label': `${t ? t.title : '세션'} 활동 ${recent.filter(e => e.task === id).length}건`, on: () => select(selected === id ? '' : id, {reveal: true})},
      h('span', {class: 'name'}, t ? t.title : '세션'), track));
  });
  if (focusedLane) { const again = box.querySelector(`.lane[data-task="${CSS.escape(focusedLane)}"]`); if (again) again.focus(); }
}

/* ---------- rail ---------- */
function attentionItems(r) {
  const s = r.status, out = [];
  const byId = new Map(r.tasks.map(t => [t.id, t]));
  r.decisions.filter(d => d.status === 'pending').forEach(d => {
    const gated = r.tasks.filter(t => t.decision_ids.includes(d.id));
    out.push({k: 'decide', g: '?', label: '결정 필요', text: d.question || d.id, task: gated[0] ? gated[0].id : 'd:' + d.id});
  });
  r.tasks.filter(t => t.status === 'blocked').forEach(t => out.push({k: 'blocked', g: '⏸', label: '차단', text: t.block_reason ? `${t.title} — ${t.block_reason}` : t.title, task: t.id}));
  (s.exhausted || []).forEach(id => byId.has(id) && out.push({k: 'failed', g: '✗', label: '시도 소진', text: `${byId.get(id).title} (${byId.get(id).attempts}/${byId.get(id).max_attempts})`, task: id}));
  r.tasks.filter(t => t.status === 'failed' && !(s.exhausted || []).includes(t.id)).forEach(t => out.push({k: 'failed', g: '✗', label: '실패 · 재시도 가능', text: `${t.title} (${t.attempts}/${t.max_attempts})`, task: t.id}));
  r.tasks.filter(t => t.status === 'running').forEach(t => out.push({k: 'running', g: '▶', label: '진행 중', text: t.title, task: t.id}));
  (s.ready || []).forEach(id => byId.has(id) && out.push({k: 'ready', g: '→', label: '다음 준비됨', text: byId.get(id).title, task: id}));
  return out;
}
function typeIcon(kind, fill) {
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('width', '18'); svg.setAttribute('height', '18'); svg.setAttribute('aria-hidden', 'true');
  if (kind === 'decision') el('polygon', {points: '9,2 16,9 9,16 2,9', style: `fill:none;stroke:${fill};stroke-width:1.6`}, svg);
  else el('circle', {cx: 9, cy: 9, r: 6.5, style: `fill:none;stroke:${fill};stroke-width:1.8`}, svg);
  return svg;
}
function renderRail() {
  const r = records, total = r.tasks.length;
  $('run').textContent = r.run_id;
  $('goal').textContent = r.goal;
  const groups = ['passed', 'running', 'failed', 'blocked', 'stale', 'cancelled', 'pending'];
  const counts = Object.fromEntries(groups.map(g => [g, r.tasks.filter(t => (groups.includes(t.status) ? t.status : 'pending') === g).length]));
  const bar = $('bar'); bar.textContent = '';
  groups.forEach(g => { if (counts[g]) bar.append(h('span', {style: `width:${counts[g] / total * 100}%;background:${color(g)}`})); });
  const waiting = r.decisions.filter(d => d.status === 'pending').length;
  $('counts').textContent = [`통과 ${counts.passed}/${total}`, ...groups.slice(1).filter(g => counts[g]).map(g => `${st(g)[0]} ${counts[g]}`),
    waiting ? `? ${waiting}` : ''].filter(Boolean).join('  ');
  // what needs the person
  const items = attentionItems(r);
  const keyOf = it => `${it.k}|${it.task || ''}|${it.text}`;
  const arrived = [];
  if (seenAttention) items.forEach(it => {
    if ((it.k === 'decide' || it.k === 'blocked') && !seenAttention.has(keyOf(it))) { freshAttention.add(keyOf(it)); arrived.push(it); }
  });
  seenAttention = new Set(items.map(keyOf));
  freshAttention = new Set([...freshAttention].filter(k => seenAttention.has(k)));
  if (arrived.length) $('announce').textContent = '새 항목: ' + arrived.map(it => `${it.label} ${it.text}`).join(', ');
  const list = $('attention'); list.textContent = '';
  if (!items.length) {
    const done = total && counts.passed === total;
    list.append(h('li', {}, h('div', {class: 'att ' + (done ? 'k-done' : 'k-ready')}, h('span', {class: 'g'}, done ? '✓' : '·'),
      h('span', {class: 'k'}, done ? '완료' : '대기'), h('span', {class: 't'}, done ? '모든 작업 통과' : '시작 가능한 작업 없음'))));
  }
  items.slice(0, 6).forEach(it => {
    const key = keyOf(it), fresh = freshAttention.has(key);
    const node = h('button', {class: 'att k-' + it.k + (fresh ? ' fresh' : ''), type: 'button', title: it.text},
      h('span', {class: 'g', 'aria-hidden': 'true'}, it.g), h('span', {class: 'k'}, it.label), h('span', {class: 't'}, it.text),
      fresh ? h('span', {class: 'new'}, '새') : null);
    node.addEventListener('click', () => {
      freshAttention.delete(key); node.classList.remove('fresh'); const badge = node.querySelector('.new'); if (badge) badge.remove();
      select(it.task, {reveal: true});
    });
    list.append(h('li', {}, node));
    if (arrived.includes(it) && motionOn()) node.animate(
      [{transform: 'translateX(-6px)', boxShadow: '0 0 0 3px currentColor'}, {transform: 'none', boxShadow: '0 0 0 0 transparent'}],
      {duration: 400, easing: 'cubic-bezier(0.4, 0.14, 0.3, 1)'});
  });
  if (items.length > 6) list.append(h('li', {class: 'more'}, h('button', {type: 'button', class: 'btn', on: () => { $('all').open = true; $('all').scrollIntoView({block: 'nearest'}); }}, `+${items.length - 6}개 더`)));
  // object types and status filters
  const types = $('types'); types.textContent = '';
  const chip = (key, icon, name, n) => types.append(h('button', {type: 'button', class: 'type', 'aria-pressed': String(filter === key),
    on: () => { filter = filter === key ? '' : key; renderRail(); applySelection(); }}, icon, h('span', {}, name), h('span', {class: 'n'}, String(n))));
  chip('', typeIcon('task', 'var(--ink)'), '작업', total);
  groups.filter(g => counts[g]).forEach(g => chip(g, typeIcon('task', color(g)), `${st(g)[0]} ${st(g)[1]}`, counts[g]));
  if (r.decisions.length) chip('decision', typeIcon('decision', 'var(--warn)'), '결정 게이트', r.decisions.length);
  const all = $('list'); all.textContent = '';
  r.tasks.forEach(t => all.append(h('li', {}, h('button', {type: 'button', 'data-task': t.id, 'aria-pressed': String(t.id === selected),
    on: () => select(selected === t.id ? '' : t.id, {reveal: true})},
    h('span', {class: 's-' + t.status}, `${st(t.status)[0]} `), `${t.title}`))));
  if (selected && selected !== HUB && !selected.startsWith('d:') && !r.tasks.some(t => t.id === selected)) select('');
}
$('search').addEventListener('input', e => { query = e.target.value.trim().toLowerCase(); applySelection(); });

/* ---------- detail (object view) ---------- */
const KIND = {direction: '방향 결정', information: '정보 요청', review: '검토', authorization: '실행 허락'};
const base = p => String(p || '').split('/').filter(Boolean).pop() || '';
function doing(e) {
  const t = e.target || '';
  const [verb, what] = ({Read: ['파일 읽기', base(t)], Edit: ['파일 수정', base(t)], MultiEdit: ['파일 수정', base(t)], Write: ['파일 작성', base(t)],
    NotebookEdit: ['노트북 수정', base(t)], Grep: ['코드 찾기', t], Glob: ['파일 찾기', t], Bash: ['명령 실행', t],
    WebFetch: ['웹 페이지 확인', t], WebSearch: ['웹 검색', t], Agent: ['보조 작업 맡김', t], Task: ['보조 작업 맡김', t],
    TodoWrite: ['할 일 정리', ''], AskUserQuestion: ['사용자에게 질문', '']})[e.tool] || [e.tool.startsWith('mcp__') ? '외부 도구 사용' : e.tool, t];
  return {verb, what: cut(what, 48), helper: !!e.agent};
}
function ago(ms) {
  const s = Math.max(0, Math.round((Date.now() - ms) / 1000));
  return s < 10 ? '방금' : s < 60 ? `${s}초 전` : s < 3600 ? `${Math.floor(s / 60)}분 전` : `${Math.floor(s / 3600)}시간 전`;
}
function span(ms) {
  const s = Math.max(0, Math.round(ms / 1000));
  return s < 60 ? `${s}초` : s < 3600 ? `${Math.floor(s / 60)}분` : `${Math.floor(s / 3600)}시간 ${Math.floor(s % 3600 / 60)}분`;
}
const whenText = e => e.phase === 'running' ? `${span(Date.now() - e.started_at)}째` : ago(e.ended_at || e.started_at);
function callRow(e) {
  const d = doing(e), err = e.phase === 'error';
  const label = `${d.verb}${d.what ? ' · ' + d.what : ''}${err ? ' (실패)' : ''}${d.helper ? ' · 보조' : ''}`;
  const text = e.command ? h('span', {class: 'cmd', tabindex: '0'}, label) : h('span', {}, label);
  if (e.command) {
    text.addEventListener('mouseenter', () => showTip(text, e.command));
    text.addEventListener('focus', () => showTip(text, e.command));
    text.addEventListener('mouseleave', () => hideTip(text));
    text.addEventListener('blur', () => hideTip(text));
  }
  const peek = e.path ? h('button', {type: 'button', class: 'btn peek', 'aria-label': `${base(e.path)} 내용 보기`}, '보기') : null;
  if (peek) peek.addEventListener('click', () => openQuick(e.path, peek));
  return h('li', {class: 'row'}, h('span', {class: 's-' + e.phase}, e.phase === 'running' ? '◌' : err ? '✗' : '●'),
    h('span', {}, text, peek, h('span', {class: 'when', 'data-when': e.id}, ' ' + whenText(e))));
}
const callsKey = id => eventsOf(id).map(e => e.id + e.phase).join('|');
function activitySection(id) {
  const mine = eventsOf(id).slice().reverse();
  const now = mine.filter(e => e.phase === 'running'), done = mine.filter(e => e.phase !== 'running').slice(0, 5);
  return h('div', {id: 'calls', 'data-key': callsKey(id)}, now.length ? [h('h4', {}, '지금 하는 일'), h('ul', {}, now.slice(0, 2).map(callRow))] : null,
    h('h4', {}, '최근 한 일'), done.length ? h('ul', {}, done.map(callRow)) : h('p', {class: 'muted'}, activity ? '아직 없음' : '연결 대기'));
}
function refreshDetailLive() {
  const calls = $('calls');
  if (calls && calls.dataset.key === callsKey(selected)) {
    const byId = new Map(events().map(e => [e.id, e]));
    calls.querySelectorAll('[data-when]').forEach(w => { const e = byId.get(w.dataset.when); if (e) w.textContent = ' ' + whenText(e); });
  } else if (calls) {
    if (tipFor && calls.contains(tipFor)) hideTip(tipFor);
    calls.replaceWith(activitySection(selected));
  }
  const t = records && records.tasks.find(x => x.id === selected);
  const line = $('elapsed');
  if (t && line && t.started_at) line.textContent = `시작한 지 ${span(Date.now() - Date.parse(t.started_at))}`;
}
function story(t) {
  const checks = new Map(t.checks.map(c => [c.id, c.description || c.id]));
  const titles = new Map(records.tasks.map(x => [x.id, x.title]));
  let n = 0;
  return t.timeline.map(e => {
    const reason = e.reason ? `: ${e.reason}` : '';
    if (e.action === 'start') return `${++n}차 시도 시작`;
    if (e.action === 'record-check') return `‘${checks.get(e.check) || e.check}’ ${e.result === 'passed' ? '통과' : e.result === 'failed' ? '실패' : '실행 안 함'}`;
    if (e.action === 'finish') return (e.result === 'passed' ? '완료' : e.result === 'failed' ? '실패' : '종료') + reason;
    if (e.action === 'invalidated') return `앞 작업 ‘${titles.get(e.by) || e.by}’이 바뀌어 다시 확인 필요`;
    if (e.action === 'invalidate') return '다시 확인 필요' + reason;
    if (e.action === 'block') return '멈춤' + reason;
    if (e.action === 'cancel') return '취소' + reason;
    return '';
  }).map((text, i) => [t.timeline[i], text]).filter(([, text]) => text);
}
function renderDetail() {
  const body = $('detail-body');
  body.textContent = '';
  if (!selected || !records) return;
  const byId = new Map(records.tasks.map(x => [x.id, x]));
  const taskLink = id => { const x = byId.get(id); return h('li', {}, h('button', {type: 'button', class: 'link-btn', on: () => select(id)},
    h('span', {class: 's-' + (x ? x.status : 'pending')}, x ? st(x.status)[0] : '·'), ` ${x ? x.title : id}`)); };
  if (selected === HUB) {
    $('detail-title').textContent = '세션';
    body.append(h('h3', {}, '작업에 묶이지 않은 활동'), activitySection(HUB));
    return;
  }
  if (selected.startsWith('d:')) {
    const d = records.decisions.find(x => x.id === selected.slice(2));
    if (!d) return;
    $('detail-title').textContent = '결정';
    const open = d.status !== 'resolved';
    body.append(h('h3', {}, d.question || d.id),
      h('p', {class: 'sub'}, h('span', {class: open ? 's-pending-decision' : 's-' + d.outcome}, open ? '? 답을 기다리는 중' : `✓ ${OUTCOME[d.outcome] || d.outcome}`), ` · ${KIND[d.kind] || d.kind}`),
      d.answer ? h('p', {class: 'answer'}, d.answer) : null,
      h('h4', {}, '이 결정을 기다리는 작업'), h('ul', {}, records.tasks.filter(t => t.decision_ids.includes(d.id)).map(t => taskLink(t.id))));
    return;
  }
  const t = byId.get(selected);
  if (!t) return;
  $('detail-title').textContent = '작업';
  const dependents = records.tasks.filter(x => x.depends_on.includes(t.id)).map(x => x.id);
  const ready = (records.status.ready || []).includes(t.id);
  const decisions = new Map(records.decisions.map(d => [d.id, d]));
  const waiting = t.decision_ids.map(id => decisions.get(id)).filter(d => d && !(d.status === 'resolved' && ['answered', 'approved'].includes(d.outcome)));
  const passed = t.checks.filter(c => c.result === 'passed').length;
  const lines = story(t);
  body.append(...[
    h('h3', {}, t.title),
    h('p', {class: 'sub'}, h('span', {class: 's-' + t.status}, `${st(t.status)[0]} ${st(t.status)[1]}`),
      t.attempts > 1 ? ` · ${t.attempts}번째 시도` : '', ready ? ' · 시작할 수 있음' : ''),
    t.status === 'running' && t.started_at ? h('p', {class: 'sub', id: 'elapsed'}, `시작한 지 ${span(Date.now() - Date.parse(t.started_at))}`) : null,
    t.block_reason ? h('p', {class: 'note'}, `멈춘 이유: ${t.block_reason}`) : null,
    waiting.length ? h('p', {class: 'note'}, `답이 필요해요: ${waiting.map(d => d.question || d.id).join(' / ')}`) : null,
    activitySection(t.id),
    h('h4', {}, `확인 결과 ${passed}/${t.checks.length}`),
    h('ul', {}, t.checks.map(c => h('li', {class: 'row'}, h('span', {class: 's-' + c.result}, rs(c.result)[0]),
      h('span', {}, `${c.description || c.id} `, h('span', {class: 'when'}, rs(c.result)[1]))))),
    t.depends_on.length ? [h('h4', {}, '먼저 끝나야 하는 작업'), h('ul', {}, t.depends_on.map(taskLink))] : null,
    dependents.length ? [h('h4', {}, '다음 작업'), h('ul', {}, dependents.map(taskLink))] : null,
    lines.length ? h('details', {class: 'story'}, h('summary', {}, `지나온 과정 ${lines.length}`),
      h('ul', {}, lines.slice().reverse().map(([e, text]) => h('li', {class: 'row'}, h('span', {class: 'when'}, hhmm(e.at)), h('span', {}, text))))) : null,
  ].flat().filter(Boolean));
}

/* ---------- command explanations ---------- */
const explained = new Map();
let tipFor = null, tipTimer = 0;
function showTip(anchor, command) {
  tipFor = anchor;
  clearTimeout(tipTimer);
  const tip = $('tip');
  const paint = state => {
    tip.textContent = '';
    tip.append(h('code', {}, cut(command, 200)),
      state.state === 'ready' ? h('p', {}, state.text)
        : state.state === 'failed' ? h('p', {class: 'muted'}, state.text || '설명을 만들지 못했어요')
        : h('p', {class: 'wait'}, h('span', {class: 'dots', 'aria-hidden': 'true'}), '설명 만드는 중…'));
    const r = anchor.getBoundingClientRect();
    tip.style.left = Math.max(8, Math.min(innerWidth - 346, r.left + scrollX)) + 'px';
    tip.style.top = (r.bottom + scrollY + 6) + 'px';
  };
  tip.hidden = false;
  anchor.setAttribute('aria-describedby', 'tip');
  const ask = async tries => {
    if (tipFor !== anchor) return;
    let state = explained.get(command);
    if (!state) {
      try {
        const res = await fetch('/api/explain', {method: 'POST', headers: {...headers, 'Content-Type': 'application/json'}, body: JSON.stringify({command})});
        state = res.ok ? await res.json() : {state: 'failed', text: '설명할 수 없는 명령이에요'};
      } catch (_) { state = {state: 'failed', text: '대시보드 연결이 끊겼어요'}; }
      if (state.state !== 'pending') explained.set(command, state);
    }
    if (tipFor !== anchor) return;
    if (state.state === 'pending' && tries >= 40) state = {state: 'failed', text: '설명이 오지 않아요 · 패널에서 Haiku 요약이 켜져 있는지 확인하세요'};
    paint(state);
    if (state.state === 'pending') tipTimer = setTimeout(() => ask(tries + 1), 1000);
  };
  paint(explained.get(command) || {state: 'pending'});
  ask(0);
}
function hideTip(anchor) {
  if (tipFor !== anchor) return;
  tipFor = null;
  clearTimeout(tipTimer);
  $('tip').hidden = true;
  anchor.removeAttribute('aria-describedby');
}

/* ---------- quick view ---------- */
let quickReturn = null;
const sizeText = n => n < 1024 ? `${n}B` : n < 1048576 ? `${(n / 1024).toFixed(1)}KB` : `${(n / 1048576).toFixed(1)}MB`;
const QUICK_ERROR = {'secret-looking file': '비밀 정보가 있을 수 있는 파일이라 열지 않아요', 'only files this session touched': '이 세션에서 접근한 파일만 열 수 있어요',
  'binary file': '텍스트 파일이 아니에요', 'not a regular file': '파일이 없거나 링크예요'};
async function openQuick(path, from) {
  quickReturn = from;
  $('qv').hidden = false;
  $('qv-title').textContent = base(path);
  $('qv-meta').textContent = '불러오는 중…';
  $('qv-body').textContent = '';
  $('qv-close').focus();
  try {
    const res = await fetch('/api/file?path=' + encodeURIComponent(path), {headers, cache: 'no-store'});
    const data = await res.json();
    if (!res.ok) { $('qv-meta').textContent = `${path} · ${QUICK_ERROR[data.error] || '열 수 없어요'}`; return; }
    $('qv-meta').textContent = `${path} · ${sizeText(data.size)} · 지금 내용, ${hhmm(data.modified)} 수정${data.truncated ? ' · 앞 200KB' : ''}`;
    const body = $('qv-body');
    const frag = document.createDocumentFragment();
    data.text.split('\n').forEach(line => frag.append(h('span', {class: 'ln'}, line || ' ')));
    body.append(frag);
  } catch (_) { $('qv-meta').textContent = `${path} · 대시보드 연결이 끊겼어요`; }
}
function closeQuick() {
  $('qv').hidden = true;
  if (quickReturn && quickReturn.isConnected) quickReturn.focus();
}
$('qv-close').addEventListener('click', closeQuick);
$('qv').addEventListener('click', e => { if (e.target === $('qv')) closeQuick(); });

/* ---------- Claude questions ---------- */
let questions = [], questionKey = '';
function answerText(q) { return Object.values(q.answers || {}).join(' / '); }
function askForm(q) {
  const waiting = q.status === 'answered';
  const form = h('form', {class: 'ask-form', 'data-q': q.id});
  q.questions.forEach((item, qi) => {
    const name = `${q.id}:${qi}`;
    const set = h('fieldset', {}, h('legend', {}, item.header ? h('span', {class: 'tag'}, item.header) : null, h('span', {class: 'qtext'}, item.question)));
    item.options.forEach(o => set.append(h('label', {class: 'opt'},
      h('input', {type: item.multi ? 'checkbox' : 'radio', name, value: o.label, disabled: waiting}),
      h('span', {}, h('b', {}, o.label), o.description ? h('small', {}, o.description) : null))));
    set.append(h('label', {class: 'opt other'}, h('span', {class: 'sr'}, '직접 입력'),
      h('input', {type: 'text', name: name + ':other', placeholder: '직접 입력', autocomplete: 'off', disabled: waiting})));
    form.append(set);
  });
  const status = h('p', {class: 'ask-status', role: 'status'}, waiting ? '보냄 · Claude에 전달 중…' : '');
  const send = h('button', {type: 'submit', class: 'btn primary', disabled: waiting}, '보내기');
  form.append(h('div', {class: 'ask-actions'}, send, status));
  form.addEventListener('submit', async ev => {
    ev.preventDefault();
    const answers = {};
    q.questions.forEach((item, qi) => {
      const name = `${q.id}:${qi}`;
      const other = form.querySelector(`[name="${CSS.escape(name + ':other')}"]`).value.trim();
      const picked = [...form.querySelectorAll(`[name="${CSS.escape(name)}"]:checked`)].map(i => i.value);
      if (other || picked.length) answers[item.question] = other || picked.join(', ');
    });
    if (Object.keys(answers).length !== q.questions.length) { status.textContent = '모든 질문에 답해 주세요'; return; }
    status.textContent = '보내는 중…';
    try {
      const res = await fetch('/api/question/answer', {method: 'POST', headers: {...headers, 'Content-Type': 'application/json'}, body: JSON.stringify({id: q.id, answers})});
      status.textContent = res.ok ? '보냄 · Claude에 전달 중…' : res.status === 409 ? '이미 답한 질문이에요' : '보내지 못했어요';
      if (res.ok) form.querySelectorAll('input,button').forEach(x => { x.disabled = true; });
    } catch (_) { status.textContent = '보내지 못했어요'; }
  });
  return form;
}
function renderAsk() {
  const key = JSON.stringify(questions.map(q => [q.id, q.status]));
  if (key === questionKey) return;
  const known = questionKey;
  questionKey = key;
  const open = questions.filter(q => q.status === 'open' || q.status === 'answered');
  const last = questions.filter(q => q.status === 'resolved' || q.status === 'closed').slice(-1);
  const body = $('ask-body');
  body.textContent = '';
  open.forEach(q => body.append(askForm(q)));
  last.forEach(q => body.append(h('p', {class: 'ask-done'}, q.status === 'closed' ? '질문이 닫혔어요' :
    [`${q.via === 'dashboard' ? '대시보드' : '터미널'}에서 답함: `, h('b', {}, cut(answerText(q), 80))])));
  $('ask').hidden = !open.length && !last.length;
  const fresh = open.filter(q => !known.includes(JSON.stringify(q.id)));
  if (fresh.length && known) {
    $('announce').textContent = 'Claude 질문: ' + fresh[0].questions.map(x => x.question).join(' / ');
    if (motionOn()) $('ask').animate([{boxShadow: '0 0 0 3px var(--warn)'}, {boxShadow: '0 0 0 0 transparent'}], {duration: 600, easing: 'cubic-bezier(0.4, 0.14, 0.3, 1)'});
  }
}

/* ---------- AI summary ---------- */
function renderSummary() {
  if (!summary) { $('ai-headline').textContent = '대기 중'; $('ai-meta').textContent = ''; return; }
  $('ai-headline').textContent = summary.headline || summary.activity || '';
  const when = new Date(summary.generated_at);
  const parts = [summary.model, isNaN(when) ? summary.generated_at : when.toLocaleTimeString()];
  if (typeof summary.usage_tokens === 'number') parts.push('토큰 ' + summary.usage_tokens.toLocaleString());
  if (records && summary.records_fingerprint !== records.fingerprint) parts.push('요약 이후 기록 바뀜');
  $('ai-meta').textContent = parts.join(' · ');
}

/* ---------- polling ---------- */
function setConn(kind, text) { const c = $('conn'); c.className = 'pill ' + kind; c.textContent = text; }
async function fetchJSON(path) {
  const res = await fetch(path, {headers, cache: 'no-store'});
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}
let lastMeta = '';
async function tick() {
  try {
    const [rec, ses] = await Promise.all([fetchJSON('/api/records'), fetchJSON('/api/session')]);
    failures = 0;
    if (rec.ok) { records = rec; setConn('live', 'LIVE ' + new Date(rec.read_at).toLocaleTimeString()); }
    else if (rec.last_good) { records = rec.last_good; setConn('warn', '기록 불일치 · 재시도'); }
    else setConn('warn', '기록 읽기 실패: ' + rec.error);
    summary = ses.summary || null;
    activity = ses.activity || null;
    questions = ses.questions || [];
    renderAsk();
    if (records) {
      if (records.fingerprint !== lastMeta) { lastMeta = records.fingerprint; renderRail(); renderDetail(); }
      renderSummary(); draw();
      firstLoad = false;
    }
  } catch (_) {
    if (++failures >= 2) setConn('down', '연결 끊김 · 패널에서 다시 열기');
  }
}
new ResizeObserver(() => { drawnKey = ''; draw(); }).observe($('canvas'));
tick();
setInterval(tick, 1000);
})();
</script>
</body>
</html>
'''

if __name__ == '__main__':
    sys.exit(main())
