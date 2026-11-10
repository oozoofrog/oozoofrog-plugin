#!/usr/bin/env python3
"""Serve a local, read-only live dashboard for one guided-execution run.

Binds 127.0.0.1 only and requires the per-process token printed on startup.
Loop records are re-read on every request and never written. An optional AI
summary (labels and grouping only) is accepted from the launching host and
kept in memory; record statuses always come from the loop files.
Exits when its launching parent process goes away (POSIX re-parenting).
"""
import argparse
import os
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

MAX_BODY = 64 * 1024
MAX_STAGES = 12
MAX_STAGE_EDGES = 24
MAX_REFS = 40
STAGE_KINDS = {'plan', 'build', 'verify', 'decide', 'deliver', 'other'}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def clip(value, limit):
    if not isinstance(value, str):
        return None
    value = ' '.join(value.split())
    return value[:limit] if value else None


def snapshot(workspace):
    """One consistent read of the run: load_workspace rejects a mismatched plan/state pair."""
    validated, files, plan, state, warnings = load_workspace(workspace)
    validate_extra(validated, plan, state)
    summary = status(plan, state, warnings)
    graph = build_graph(plan, state)
    tasks = []
    for task in plan['tasks']:
        item = state['tasks'][task['id']]
        results = {}
        for record in item['evidence']:
            results.setdefault(record['check_id'], []).append(record['result'])
        tasks.append(dict(
            id=task['id'], title=task['title'], status=item['status'],
            attempts=item['attempts'], max_attempts=task['max_attempts'],
            depends_on=task['depends_on'], decision_ids=task['decision_ids'],
            block_reason=item.get('block_reason') if isinstance(item.get('block_reason'), str) else None,
            checks=[dict(id=check['id'], description=check.get('description', ''),
                         result=('stale' if item['status'] == 'stale' else
                                 'mixed' if len(results.get(check['id'], [])) > 1 else
                                 results[check['id']][0] if check['id'] in results else 'unrecorded'))
                    for check in task['checks']]))
    decisions = [dict(id=decision['id'], kind=decision['kind'], question=decision.get('question', ''),
                      status=state['decisions'][decision['id']]['status'],
                      outcome=state['decisions'][decision['id']].get('outcome'))
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


class Board:
    def __init__(self, workspace):
        self.workspace = workspace
        self.token = secrets.token_urlsafe(24)
        self.summary = None
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

    def accept_summary(self, raw):
        current = self.records()
        source = current if current.get('ok') else current.get('last_good')
        if not source:
            raise ValueError('no readable records to attach the summary to')
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
                    return self.send_json(200, dict(summary=board.summary))
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
            if urlsplit(self.path).path != '/api/session':
                return self.send(404, 'not found', 'text/plain; charset=utf-8')
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                length = -1
            if not 0 < length <= MAX_BODY:
                return self.send_json(413, dict(ok=False, error='body size'))
            try:
                accepted = board.accept_summary(json.loads(self.rfile.read(length)))
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
:root{--bg:#f5f6f8;--panel:#ffffff;--ink:#17202b;--sub:#5b6878;--line:#d8dee6;--edge:#9aa9bb;
--ok:#14825c;--bad:#c23a4d;--warn:#9a6300;--run:#2360c4;--muted:#76828f;--ai:#7448cc;--focus:#2360c4}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f141b;--panel:#18202a;--ink:#e8eef6;--sub:#9fadbd;--line:#2c3744;--edge:#5a6b80;
--ok:#4fd6a0;--bad:#ff8a9a;--warn:#f2c46b;--run:#8cc2ff;--muted:#8d99a8;--ai:#b99cff;--focus:#8cc2ff}}
:root[data-theme="dark"]{--bg:#0f141b;--panel:#18202a;--ink:#e8eef6;--sub:#9fadbd;--line:#2c3744;--edge:#5a6b80;
--ok:#4fd6a0;--bad:#ff8a9a;--warn:#f2c46b;--run:#8cc2ff;--muted:#8d99a8;--ai:#b99cff;--focus:#8cc2ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Apple SD Gothic Neo",sans-serif}
h1,h2,h3,h4,p{margin:0}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.wrap{max-width:1440px;margin:0 auto;padding:0 16px 28px}
.top{max-width:1440px;margin:0 auto;padding:18px 16px 12px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px 20px;align-items:start}
h1{font-size:20px;letter-spacing:-.2px}
#goal{margin-top:3px;color:var(--sub);max-width:80ch}
.tools{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:flex-end}
.progress{grid-column:1/-1}
.bar{display:flex;height:8px;border-radius:99px;overflow:hidden;background:var(--line)}
.bar span{display:block;height:100%}
#counts{margin-top:6px;font-size:12px;color:var(--sub)}
.pill{border:1px solid var(--line);border-radius:999px;padding:3px 10px;font-size:12px;color:var(--sub);background:var(--panel)}
.pill.live{color:var(--ok);border-color:currentColor}.pill.down{color:var(--bad);border-color:currentColor}.pill.warn{color:var(--warn);border-color:currentColor}
button,.btn{font:inherit;font-size:12px;border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:8px;padding:5px 10px;cursor:pointer;text-decoration:none}
button:hover,.btn:hover{border-color:var(--sub)}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
section h2,aside h2{font-size:13px;color:var(--sub);font-weight:700;letter-spacing:.2px;margin-bottom:8px}
.attention{margin:4px 0 14px}
#attention{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px}
.att{width:100%;text-align:left;display:grid;grid-template-columns:auto minmax(0,1fr);gap:2px 10px;padding:9px 12px;border-radius:10px;border:1px solid var(--line);background:var(--panel);font-size:13px}
.att .g{grid-row:1/3;font-weight:700;font-size:15px;line-height:1.2}
.att .k{font-size:11px;font-weight:700;letter-spacing:.3px}
.att{position:relative}
.att .t{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.more{font-size:12px;align-self:center;justify-self:start}
.k-decide{border-left:4px solid var(--warn)}.k-decide .g,.k-decide .k{color:var(--warn)}
.k-blocked{border-left:4px solid var(--warn)}.k-blocked .g,.k-blocked .k{color:var(--warn)}
.k-failed{border-left:4px solid var(--bad)}.k-failed .g,.k-failed .k{color:var(--bad)}
.k-running{border-left:4px solid var(--run)}.k-running .g,.k-running .k{color:var(--run)}
.k-ready .g,.k-ready .k{color:var(--sub)}
.k-done{border-left:4px solid var(--ok)}.k-done .g,.k-done .k{color:var(--ok)}
.ai{border:1px dashed var(--ai);border-radius:12px;padding:10px 14px;margin:0 0 14px;background:color-mix(in srgb,var(--ai) 6%,var(--panel))}
.ai-head{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:12px;color:var(--sub)}
.ai-head h2{color:var(--ai);font-size:13px;margin:0}
.ai.waiting{padding:8px 14px}
#ai-headline{margin-top:4px;font-size:15px}
#ai-activity{margin-top:2px;color:var(--sub);font-size:12px}
.board{display:grid;grid-template-columns:minmax(0,1fr);gap:14px;align-items:start}
@media (min-width:1000px){.board.open{grid-template-columns:minmax(0,1fr) 340px}.detail{position:sticky;top:12px;margin-top:27px}}
.canvas{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow-x:auto}
svg{display:block}
.detail{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.detail h3{font-size:16px;line-height:1.35}
.detail h4{font-size:12px;color:var(--sub);margin:14px 0 6px;font-weight:700}
.detail ul{list-style:none;margin:0;padding:0;display:grid;gap:6px}
.detail .meta{margin-top:4px;color:var(--sub);font-size:12px}
.detail .row{display:grid;grid-template-columns:auto minmax(0,1fr);gap:0 8px;font-size:13px}
.detail .row small{grid-column:2;color:var(--sub);font-size:12px}
.detail .link{width:100%;text-align:left;font-size:13px}
.detail .note{margin-top:10px;padding:8px 10px;border-radius:8px;border:1px solid var(--warn);color:var(--warn);font-size:13px}
.detail-head{display:flex;justify-content:space-between;gap:8px;align-items:center}
.muted{color:var(--sub)}
details.all{margin-top:14px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:8px 14px}
details.all summary{cursor:pointer;font-weight:600}
#list{margin:8px 0 4px;padding:0;list-style:none;display:grid;gap:4px}
#list button{width:100%;text-align:left;border-color:transparent;font-size:13px}
#list button[aria-pressed="true"]{border-color:var(--focus);border-style:dashed}
.s-passed,.s-approved,.s-answered{color:var(--ok)}.s-failed,.s-rejected,.s-mixed{color:var(--bad)}
.s-blocked,.s-stale,.s-revision_requested,.s-pending-decision{color:var(--warn)}.s-running{color:var(--run)}
.s-pending,.s-cancelled,.s-unrecorded,.s-not_run{color:var(--muted)}
/* SVG */
.card{cursor:pointer;outline:none}
.card:hover rect.body{stroke:var(--sub)}
.card rect.body{fill:var(--panel);stroke:var(--line);stroke-width:1.2}
.card.st-running rect.body{stroke:var(--run);stroke-width:2}
.card .ring{fill:none;stroke:var(--focus);stroke-width:2;stroke-dasharray:6 4;opacity:0}
.card.selected .ring{opacity:1}
.card:focus-visible rect.body{stroke:var(--focus);stroke-width:2.5}
.card text{fill:var(--ink);font-size:13px;font-weight:600}
.card text.sub{font-size:11px;font-weight:600}
.card text.dim{fill:var(--sub);font-weight:500}
.chip text{font-size:10px;font-weight:700;fill:var(--bg)}
.gate polygon{stroke:var(--warn);stroke-width:1.4;fill:var(--panel)}
.gate text{font-size:10px;font-weight:800;fill:var(--warn)}
.gate.ok polygon{stroke:var(--ok)}.gate.ok text{fill:var(--ok)}
.col-head rect{fill:var(--panel);stroke:var(--line)}
.col-head.ai rect{stroke:var(--ai);stroke-dasharray:5 4;fill:color-mix(in srgb,var(--ai) 7%,var(--panel))}
.col-head text{fill:var(--sub);font-size:12px;font-weight:700}
.col-head.ai text{fill:var(--ai)}
.col-head text.note{font-weight:500;font-size:11px}
.edge{fill:none;stroke:var(--edge);stroke-width:1.5;transition:opacity .2s}
.edge.stage{stroke:var(--ai);stroke-dasharray:6 5;opacity:.75}
.edge.dep{marker-end:url(#arrow)}
.edge.hot{stroke:var(--focus);stroke-width:2.5;marker-end:url(#arrow-hot)}
.edge.hot.out{stroke-dasharray:8 4}
.flow{fill:none;stroke:var(--focus);stroke-width:3;stroke-linecap:round;opacity:0}
.flow.in{stroke-dasharray:3 997}
.flow.out{stroke-dasharray:3 9 3 985}
.motion .flow.hot{opacity:.9;animation:packet 3.2s linear infinite;animation-delay:var(--d,0s)}
.card .changed{fill:none;stroke:var(--focus);stroke-width:2.5;opacity:0;pointer-events:none}
.att.fresh{box-shadow:inset 0 0 0 1px currentColor}
.att .new{position:absolute;top:7px;right:9px;font-size:10px;font-weight:800;padding:0 6px;border-radius:99px;border:1px solid currentColor}
.att.fresh .t{padding-right:28px}
.swatch{vertical-align:middle;margin-left:6px}
.motion .enter{animation:enter .6s cubic-bezier(.16,1,.3,1) both;animation-delay:var(--e,0s)}
.has-sel .card:not(.selected):not(.near){opacity:.38}
.has-sel .edge.dep:not(.hot){opacity:.2}
@keyframes packet{from{stroke-dashoffset:1000}to{stroke-dashoffset:0}}
@keyframes enter{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){.motion .flow.hot,.motion .enter{animation:none}.motion .flow.hot{opacity:0}}
.empty{padding:28px 18px;color:var(--sub)}
@media (max-width:640px){.top{grid-template-columns:minmax(0,1fr)}.tools{justify-content:flex-start}}
</style>
</head>
<body>
<header class="top">
  <div>
    <h1 id="run">기록 읽는 중</h1>
    <p id="goal"></p>
  </div>
  <div class="tools">
    <span id="conn" class="pill" role="status">연결 중</span>
    <button id="motion" type="button" aria-pressed="true">움직임 끄기</button>
    <a id="report" class="btn" target="_blank" rel="noopener">기록 스냅샷</a>
  </div>
  <div class="progress">
    <div class="bar" id="bar" aria-hidden="true"></div>
    <p id="counts"></p>
  </div>
</header>
<main class="wrap">
  <section class="attention" aria-labelledby="att-title">
    <h2 id="att-title">지금 필요한 것</h2>
    <ul id="attention"><li class="muted">기록을 불러오는 중입니다.</li></ul>
  </section>
  <section class="ai waiting" id="ai" aria-labelledby="ai-title">
    <div class="ai-head"><h2 id="ai-title">AI 요약</h2><span class="pill">Haiku · 기록 아님</span><span id="ai-meta">대기 중</span></div>
    <p id="ai-headline" hidden></p>
    <p id="ai-activity" hidden></p>
  </section>
  <div class="board" id="board">
    <section aria-labelledby="pipe-title">
      <h2 id="pipe-title">작업 파이프라인</h2>
      <div class="canvas" id="canvas"><p class="empty">기록을 불러오는 중입니다.</p></div>
    </section>
    <aside class="detail" id="detail" aria-labelledby="detail-title" hidden>
      <div class="detail-head"><h2 id="detail-title">작업 상세</h2><button id="clear" type="button" aria-label="작업 상세 닫기">✕ 닫기</button></div>
      <div id="detail-body"></div>
    </aside>
  </div>
  <p id="announce" class="sr" aria-live="polite"></p>
  <details class="all" id="all"><summary>전체 작업 목록</summary><ul id="list"></ul></details>
</main>
<script nonce="__NONCE__">
(() => {
'use strict';
const token = new URLSearchParams(location.search).get('t') || '';
const headers = {'X-Board-Token': token};
const $ = id => document.getElementById(id);
const NS = 'http://www.w3.org/2000/svg';
const STATUS = {passed:['✓','통과'],running:['▶','진행'],failed:['✗','실패'],blocked:['⏸','차단'],stale:['↺','재검증'],
  cancelled:['⊘','취소'],pending:['○','대기']};
const RESULT = {passed:['✓','통과'],failed:['✗','실패'],not_run:['–','미실행'],unrecorded:['○','미기록'],stale:['↺','재검증'],mixed:['!','상충']};
const OUTCOME = {answered:'답변됨',approved:'승인',rejected:'반려',revision_requested:'수정 요청'};
const COLOR = {passed:'--ok',failed:'--bad',mixed:'--bad',blocked:'--warn',stale:'--warn',running:'--run'};
const color = s => `var(${COLOR[s] || '--muted'})`;
const st = s => STATUS[s] || ['○', s];
const rs = r => RESULT[r] || ['○', r];
let records = null, summary = null, drawnKey = '', firstDraw = true, failures = 0;
// Motion tokens (Carbon productive / expressive standard curves).
const PRODUCTIVE = 'cubic-bezier(0.2, 0, 0.38, 0.9)', EXPRESSIVE = 'cubic-bezier(0.4, 0.14, 0.3, 1)';
let lastLayout = new Map();            // task id -> {x, y, status} from the previous drawing
let seenAttention = null, freshAttention = new Set();
const motionOn = () => document.body.classList.contains('motion') && !matchMedia('(prefers-reduced-motion: reduce)').matches;
const cssColor = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const statusColorValue = s => cssColor(COLOR[s] || '--muted');
let selected = decodeURIComponent((location.hash.match(/^#task=(.+)$/) || [])[1] || '');
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
  for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
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
  measure.font = '600 13px system-ui, -apple-system, sans-serif';
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

let lastCard = '';
function select(id, opts) {
  const previous = selected;
  selected = records && records.tasks.some(t => t.id === id) ? id : '';
  if (selected) lastCard = selected;
  history.replaceState(null, '', location.pathname + location.search + (selected ? '#task=' + encodeURIComponent(selected) : ''));
  applySelection();
  renderDetail();
  const t = selected && records.tasks.find(x => x.id === selected);
  $('announce').textContent = t ? `선택: ${t.title}, ${st(t.status)[1]}` : (previous ? '선택 해제' : '');
  if (!selected && previous && opts && opts.returnFocus) {
    const card = document.querySelector(`.card[data-id="${CSS.escape(previous)}"]`);
    if (card) card.focus();
  }
  if (opts && opts.reveal && selected && matchMedia('(max-width: 999px)').matches) $('detail-body').scrollIntoView({block: 'nearest'});
}
$('clear').addEventListener('click', () => select('', {returnFocus: true}));
addEventListener('keydown', e => { if (e.key === 'Escape' && selected) select('', {returnFocus: true}); });

function neighbors(id) {
  const t = records.tasks.find(x => x.id === id);
  const set = new Set(t ? t.depends_on : []);
  records.tasks.forEach(x => { if (x.depends_on.includes(id)) set.add(x.id); });
  return set;
}
function applySelection() {
  const svg = document.querySelector('#canvas svg');
  const near = selected ? neighbors(selected) : new Set();
  if (svg) {
    svg.classList.toggle('has-sel', !!selected);
    svg.querySelectorAll('.card').forEach(c => {
      const id = c.dataset.id;
      c.classList.toggle('selected', id === selected);
      c.classList.toggle('near', near.has(id));
      c.setAttribute('aria-pressed', String(id === selected));
    });
    svg.querySelectorAll('[data-from]').forEach(p => {
      const into = !!selected && p.dataset.to === selected, out = !!selected && p.dataset.from === selected;
      p.classList.toggle('hot', into || out);
      p.classList.toggle('in', into);
      p.classList.toggle('out', out);
    });
  }
  document.querySelectorAll('#list button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.task === selected)));
  $('detail').hidden = !selected;
  $('board').classList.toggle('open', !!selected);
}

function columns(rec, sum) {
  const tasks = new Map(rec.tasks.map(t => [t.id, t]));
  if (sum && sum.stages && sum.stages.length) {
    const used = new Set();
    const cols = sum.stages.map(s => {
      const items = s.refs.filter(r => tasks.has(r) && !used.has(r));
      items.forEach(r => used.add(r));
      return {id: s.id, label: s.label, note: s.note, ai: true, items};
    });
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
  rec.tasks.forEach(t => { (cols[level[t.id]] ||= {id: 'L' + level[t.id], label: '단계 ' + (level[t.id] + 1), ai: false, items: []}).items.push(t.id); });
  return cols.filter(Boolean).map(c => ({...c, note: `작업 ${c.items.length}개`}));
}

function draw() {
  const box = $('canvas');
  if (!records) return;
  const vertical = box.clientWidth < 640;
  const key = records.fingerprint + '|' + (summary ? summary.received_at : '') + '|' + Math.round(box.clientWidth / 24);
  if (key === drawnKey) return;
  drawnKey = key;
  const focused = document.activeElement && document.activeElement.closest ? document.activeElement.closest('.card') : null;
  const focusedId = focused ? focused.dataset.id : '';
  const tasks = new Map(records.tasks.map(t => [t.id, t]));
  const decisions = new Map(records.decisions.map(d => [d.id, d]));
  const cols = columns(records, summary);
  const W = 240, colGap = vertical ? 0 : 84, headH = 50, rowGap = 16, pad = 22;
  const titles = new Map(records.tasks.map(t => [t.id, wrap(t.title, W - 30 - t.decision_ids.length * 22, 2)]));
  const cardH = t => 38 + titles.get(t.id).length * 17 + (t.checks.length ? 28 : 0);
  const pos = new Map(), heads = new Map();
  let x = pad, y = pad, maxH = 0;
  cols.forEach(col => {
    if (vertical) x = pad;
    heads.set(col.id, {x, y, w: W, h: headH - 10});
    let cy = y + headH;
    col.items.forEach(id => { const hgt = cardH(tasks.get(id)); pos.set(id, {x, y: cy, w: W, h: hgt}); cy += hgt + rowGap; });
    if (vertical) y = cy + 22; else { x += W + colGap; maxH = Math.max(maxH, cy); }
  });
  const width = vertical ? W + pad * 2 : x - colGap + pad;
  const height = vertical ? y : maxH + pad;
  // Fit wide pipelines into view down to 80% before falling back to horizontal scroll.
  const scale = Math.min(1, Math.max(0.8, (box.clientWidth - 2) / width));
  box.textContent = '';
  const svg = el('svg', {width: Math.round(width * scale), height: Math.round(height * scale), viewBox: `0 0 ${width} ${height}`, role: 'group',
    'aria-label': `작업 ${records.tasks.length}개, 단계 ${cols.length}개 파이프라인`}, box);
  const defs = el('defs', {}, svg);
  [['arrow', 'var(--edge)'], ['arrow-hot', 'var(--focus)']].forEach(([mid, fill]) => {
    const m = el('marker', {id: mid, viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto', markerUnits: 'userSpaceOnUse'}, defs);
    el('path', {d: 'M0,0 L10,5 L0,10 z', style: `fill:${fill}`}, m);
  });
  const edges = el('g', {}, svg), flows = el('g', {}, svg), nodes = el('g', {}, svg);
  let flowIndex = 0;
  const link = (a, b, cls, from, to) => {
    const stacked = vertical || Math.abs(a.x - b.x) < 1;
    const d = stacked
      ? `M${a.x + a.w / 2},${a.y + a.h} C${a.x + a.w / 2},${a.y + a.h + 30} ${b.x + b.w / 2},${b.y - 30} ${b.x + b.w / 2},${b.y}`
      : `M${a.x + a.w},${a.y + a.h / 2} C${a.x + a.w + 40},${a.y + a.h / 2} ${b.x - 40},${b.y + b.h / 2} ${b.x},${b.y + b.h / 2}`;
    const data = from ? {'data-from': from, 'data-to': to} : {};
    el('path', {d, class: 'edge ' + cls, ...data}, edges);
    if (from) el('path', {d, class: 'flow ' + cls, pathLength: 1000, style: `--d:${(flowIndex++ * 0.4) % 3.2}s`, ...data}, flows);
  };
  if (summary && summary.stages && !vertical) {
    const stageEdges = summary.edges && summary.edges.length ? summary.edges
      : summary.stages.slice(1).map((s, i) => ({from: summary.stages[i].id, to: s.id}));
    stageEdges.forEach(e => { if (heads.has(e.from) && heads.has(e.to)) link(heads.get(e.from), heads.get(e.to), 'stage'); });
  }
  records.tasks.forEach(t => t.depends_on.forEach(dep => { if (pos.has(dep) && pos.has(t.id)) link(pos.get(dep), pos.get(t.id), 'dep', dep, t.id); }));
  cols.forEach((col, ci) => {
    const hd = heads.get(col.id);
    const g = el('g', {class: 'col-head' + (col.ai ? ' ai' : '') + (firstDraw ? ' enter' : ''), style: `--e:${ci * 0.08}s`}, nodes);
    el('rect', {x: hd.x, y: hd.y, width: hd.w, height: hd.h, rx: 9}, g);
    el('text', {x: hd.x + 10, y: hd.y + 16}, g, cut((col.ai ? 'AI · ' : '') + col.label, 30));
    if (col.note) el('text', {x: hd.x + 10, y: hd.y + 31, class: 'note'}, g, cut(col.note, 38));
  });
  let n = 0;
  const changes = [];
  pos.forEach((p, id) => {
    const t = tasks.get(id);
    const [glyph, word] = st(t.status);
    const g = el('g', {class: `card st-${t.status}` + (firstDraw ? ' enter' : ''), 'data-id': id, tabindex: 0, role: 'button',
      'aria-label': `${t.title}, ${word}, 시도 ${t.attempts}/${t.max_attempts}`, style: `--e:${0.12 + n++ * 0.05}s`}, nodes);
    el('rect', {class: 'ring', x: p.x - 5, y: p.y - 5, width: p.w + 10, height: p.h + 10, rx: 14}, g);
    el('rect', {class: 'body', x: p.x, y: p.y, width: p.w, height: p.h, rx: 11}, g);
    const statusBar = el('rect', {x: p.x, y: p.y + 8, width: 4, height: p.h - 16, rx: 2, fill: color(t.status)}, g);
    const changedRing = el('rect', {class: 'changed', x: p.x - 2, y: p.y - 2, width: p.w + 4, height: p.h + 4, rx: 12}, g);
    changes.push({id, g, statusBar, changedRing, p, status: t.status});
    const lines = titles.get(id);
    lines.forEach((line, i) => el('text', {x: p.x + 14, y: p.y + 21 + i * 17}, g, line));
    const sy = p.y + 21 + lines.length * 17 + 2;
    const sub = el('text', {x: p.x + 14, y: sy, class: 'sub'}, g);
    el('tspan', {fill: color(t.status)}, sub, `${glyph} ${word}`);
    el('tspan', {class: 'dim', fill: 'var(--sub)'}, sub, ` · 시도 ${t.attempts}/${t.max_attempts}` + (t.block_reason ? ' · ' + cut(t.block_reason, 12) : ''));
    t.decision_ids.forEach((d, i) => {
      const dec = decisions.get(d);
      const ok = dec && dec.status === 'resolved' && ['answered', 'approved'].includes(dec.outcome);
      const gx = p.x + p.w - 18 - i * 22, gy = p.y + 17;
      const gate = el('g', {class: 'gate' + (ok ? ' ok' : '')}, g);
      el('polygon', {points: `${gx},${gy - 9} ${gx + 9},${gy} ${gx},${gy + 9} ${gx - 9},${gy}`}, gate);
      el('text', {x: gx, y: gy + 3.5, 'text-anchor': 'middle'}, gate, ok ? '✓' : '?');
    });
    t.checks.forEach((c, i) => {
      const cx = p.x + 14 + i * 70, cy = sy + 8;
      if (i > 2) { if (i === 3) el('text', {x: cx + 2, y: cy + 15, class: 'sub dim', fill: 'var(--sub)'}, g, `+${t.checks.length - 3}`); return; }
      const [cg] = rs(c.result);
      const chip = el('g', {class: 'chip'}, g);
      el('polygon', {points: `${cx + 6},${cy} ${cx + 58},${cy} ${cx + 64},${cy + 10} ${cx + 58},${cy + 20} ${cx + 6},${cy + 20} ${cx},${cy + 10}`, fill: color(c.result)}, chip);
      el('text', {x: cx + 32, y: cy + 14, 'text-anchor': 'middle'}, chip, `${cg} ${cut(c.id, 7)}`);
    });
    g.addEventListener('click', () => select(selected === id ? '' : id, {reveal: true}));
    g.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(selected === id ? '' : id, {reveal: true}); } });
  });
  // Staged change transitions (move first, then status), only for cards whose record changed.
  if (!firstDraw && motionOn()) {
    changes.forEach(c => {
      const before = lastLayout.get(c.id);
      if (!before) { c.g.animate([{opacity: 0}, {opacity: 1}], {duration: 240, easing: PRODUCTIVE}); return; }
      const dx = before.x - c.p.x, dy = before.y - c.p.y, moved = Math.abs(dx) + Math.abs(dy) > 0.5;
      if (moved) c.g.animate([{transform: `translate(${dx}px, ${dy}px)`}, {transform: 'translate(0, 0)'}], {duration: 240, easing: PRODUCTIVE});
      if (before.status !== c.status) {
        const delay = moved ? 240 : 0;
        c.statusBar.animate([{fill: statusColorValue(before.status)}, {fill: statusColorValue(c.status)}], {duration: 240, delay, easing: PRODUCTIVE, fill: 'backwards'});
        c.changedRing.animate([{opacity: 0}, {opacity: 1, offset: 0.3}, {opacity: 0}], {duration: 600, delay, easing: PRODUCTIVE});
      }
    });
  }
  lastLayout = new Map(changes.map(c => [c.id, {x: c.p.x, y: c.p.y, status: c.status}]));
  firstDraw = false;
  applySelection();
  if (focusedId) { const again = svg.querySelector(`.card[data-id="${CSS.escape(focusedId)}"]`); if (again) again.focus(); }
}

function attentionItems(r) {
  const s = r.status, out = [];
  const byId = new Map(r.tasks.map(t => [t.id, t]));
  r.decisions.filter(d => d.status === 'pending').forEach(d => {
    const gated = r.tasks.filter(t => t.decision_ids.includes(d.id));
    out.push({k: 'decide', g: '?', label: '결정 필요', text: d.question ? `${d.id} — ${d.question}` : d.id, task: gated[0] && gated[0].id});
  });
  r.tasks.filter(t => t.status === 'blocked').forEach(t => out.push({k: 'blocked', g: '⏸', label: '차단', text: t.block_reason ? `${t.title} — ${t.block_reason}` : t.title, task: t.id}));
  (s.exhausted || []).forEach(id => byId.has(id) && out.push({k: 'failed', g: '✗', label: '시도 소진', text: `${byId.get(id).title} (${byId.get(id).attempts}/${byId.get(id).max_attempts})`, task: id}));
  r.tasks.filter(t => t.status === 'failed' && !(s.exhausted || []).includes(t.id)).forEach(t => out.push({k: 'failed', g: '✗', label: '실패 · 재시도 가능', text: `${t.title} (${t.attempts}/${t.max_attempts})`, task: t.id}));
  r.tasks.filter(t => t.status === 'running').forEach(t => out.push({k: 'running', g: '▶', label: '진행 중', text: t.title, task: t.id}));
  (s.ready || []).forEach(id => byId.has(id) && out.push({k: 'ready', g: '→', label: '다음 준비됨', text: byId.get(id).title, task: id}));
  return out;
}

function renderMeta() {
  const r = records;
  $('run').textContent = r.run_id;
  $('goal').textContent = r.goal;
  const total = r.tasks.length;
  const groups = ['passed', 'running', 'failed', 'blocked', 'stale', 'cancelled', 'pending'];
  const counts = Object.fromEntries(groups.map(g => [g, r.tasks.filter(t => (groups.includes(t.status) ? t.status : 'pending') === g).length]));
  const bar = $('bar'); bar.textContent = '';
  groups.forEach(g => { if (counts[g]) bar.append(h('span', {style: `width:${counts[g] / total * 100}%;background:${color(g)}`})); });
  const waiting = r.decisions.filter(d => d.status === 'pending').length;
  $('counts').textContent = [`통과 ${counts.passed}/${total}`, ...groups.slice(1).filter(g => counts[g]).map(g => `${st(g)[0]} ${st(g)[1]} ${counts[g]}`),
    waiting ? `? 결정 대기 ${waiting}` : ''].filter(Boolean).join(' · ');
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
  items.slice(0, 8).forEach(it => {
    const key = keyOf(it), fresh = freshAttention.has(key);
    const node = h(it.task ? 'button' : 'div', {class: 'att k-' + it.k + (fresh ? ' fresh' : ''), type: it.task ? 'button' : undefined, title: it.text},
      h('span', {class: 'g', 'aria-hidden': 'true'}, it.g), h('span', {class: 'k'}, it.label), h('span', {class: 't'}, it.text),
      fresh ? h('span', {class: 'new'}, '새') : null);
    if (it.task) node.addEventListener('click', () => {
      freshAttention.delete(key); node.classList.remove('fresh'); const badge = node.querySelector('.new'); if (badge) badge.remove();
      select(it.task, {reveal: true});
    });
    list.append(h('li', {}, node));
    if (arrived.includes(it) && motionOn()) node.animate(
      [{transform: 'translateY(-6px)', boxShadow: '0 0 0 4px currentColor'}, {transform: 'none', boxShadow: '0 0 0 0 transparent'}],
      {duration: 400, easing: EXPRESSIVE});
  });
  if (items.length > 8) list.append(h('li', {class: 'more'}, h('button', {type: 'button', on: () => { $('all').open = true; $('all').scrollIntoView({block: 'nearest'}); }}, `+${items.length - 8}개 더`)));
  const all = $('list'); all.textContent = '';
  r.tasks.forEach(t => all.append(h('li', {}, h('button', {type: 'button', 'data-task': t.id, 'aria-pressed': String(t.id === selected),
    on: () => select(selected === t.id ? '' : t.id, {reveal: true})},
    h('span', {class: 's-' + t.status}, `${st(t.status)[0]} ${st(t.status)[1]}`), ` ${t.title} · 시도 ${t.attempts}/${t.max_attempts}`))));
  if (selected && !r.tasks.some(t => t.id === selected)) select('');
}

function swatch(dashed) {
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('width', '30'); svg.setAttribute('height', '8'); svg.setAttribute('class', 'swatch'); svg.setAttribute('aria-hidden', 'true');
  const line = el('line', {x1: 1, y1: 4, x2: 23, y2: 4, stroke: 'var(--focus)', 'stroke-width': 2.5, ...(dashed ? {'stroke-dasharray': '8 4'} : {})}, svg);
  el('path', {d: 'M22,0 L30,4 L22,8 z', style: 'fill:var(--focus)'}, svg);
  return svg;
}

function renderDetail() {
  const body = $('detail-body');
  const t = records && records.tasks.find(x => x.id === selected);
  body.textContent = '';
  if (!t) return;
  const [glyph, word] = st(t.status);
  const byId = new Map(records.tasks.map(x => [x.id, x]));
  const decisions = new Map(records.decisions.map(d => [d.id, d]));
  const taskLink = id => { const x = byId.get(id); return h('li', {}, h('button', {type: 'button', class: 'link', on: () => select(id)},
    h('span', {class: 's-' + (x ? x.status : 'pending')}, x ? st(x.status)[0] : '·'), ` ${x ? x.title : id}`)); };
  const dependents = records.tasks.filter(x => x.depends_on.includes(t.id)).map(x => x.id);
  const ready = (records.status.ready || []).includes(t.id);
  body.append(...[
    h('h3', {}, t.title),
    h('p', {class: 'meta'}, h('span', {class: 's-' + t.status}, `${glyph} ${word}`), ` · 시도 ${t.attempts}/${t.max_attempts} · ${t.id}` + (ready ? ' · 다음 준비됨' : '')),
    t.block_reason ? h('p', {class: 'note'}, `⏸ 차단 사유: ${t.block_reason}`) : null,
    h('h4', {}, `검증 ${t.checks.length}`),
    h('ul', {}, t.checks.map(c => h('li', {class: 'row'}, h('span', {class: 's-' + c.result}, `${rs(c.result)[0]} ${rs(c.result)[1]}`),
      h('b', {}, c.id), c.description ? h('small', {}, c.description) : null))),
    t.decision_ids.length ? [h('h4', {}, '결정'), h('ul', {}, t.decision_ids.map(id => {
      const d = decisions.get(id); const open = !d || d.status !== 'resolved';
      return h('li', {class: 'row'}, h('span', {class: open ? 's-pending-decision' : 's-' + (d.outcome || 'answered')}, open ? '? 대기' : `✓ ${OUTCOME[d.outcome] || d.outcome}`),
        h('b', {}, id), d && d.question ? h('small', {}, d.question) : null);
    }))] : null,
    h('h4', {}, '선행 작업', swatch(false)), t.depends_on.length ? h('ul', {}, t.depends_on.map(taskLink)) : h('p', {class: 'muted'}, '없음'),
    h('h4', {}, '이어지는 작업', swatch(true)), dependents.length ? h('ul', {}, dependents.map(taskLink)) : h('p', {class: 'muted'}, '없음'),
  ].flat().filter(Boolean));
}

function renderSummary() {
  $('ai').classList.toggle('waiting', !summary);
  $('ai-headline').hidden = !summary || !summary.headline;
  $('ai-activity').hidden = !summary || !summary.activity;
  if (!summary) { $('ai-meta').textContent = '대기 중'; return; }
  $('ai-headline').textContent = summary.headline || '';
  $('ai-activity').textContent = summary.activity || '';
  const when = new Date(summary.generated_at);
  const parts = [summary.model, isNaN(when) ? summary.generated_at : when.toLocaleTimeString()];
  if (typeof summary.usage_tokens === 'number') parts.push('토큰 ' + summary.usage_tokens.toLocaleString());
  if (records && summary.records_fingerprint !== records.fingerprint) parts.push('요약 이후 기록이 바뀜');
  $('ai-meta').textContent = parts.join(' · ');
}

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
    if (rec.ok) { records = rec; setConn('live', '실시간 · ' + new Date(rec.read_at).toLocaleTimeString()); }
    else if (rec.last_good) { records = rec.last_good; setConn('warn', '기록 읽기 불일치 · 다시 읽는 중'); }
    else setConn('warn', '기록을 읽을 수 없음: ' + rec.error);
    summary = ses.summary || null;
    if (records) {
      const metaKey = records.fingerprint;
      if (metaKey !== lastMeta) { lastMeta = metaKey; renderMeta(); renderDetail(); }
      renderSummary(); draw();
    }
  } catch (_) {
    if (++failures >= 2) setConn('down', '연결 끊김 · 패널에서 다시 열기');
  }
}
new ResizeObserver(() => draw()).observe($('canvas'));
tick();
setInterval(tick, 2000);
})();
</script>
</body>
</html>
'''

if __name__ == '__main__':
    sys.exit(main())
