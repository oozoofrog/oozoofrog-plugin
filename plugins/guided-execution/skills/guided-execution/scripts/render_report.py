#!/usr/bin/env python3
"""Render an offline, read-only HTML snapshot of validated loop records.

No project commands, evidence log text, execution controls, or external resources
are used. Optional CSS motion only decorates the saved snapshot.
Stop the single writer while taking a snapshot. This is not a live controller.
"""
import argparse
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import re
import sys

# Avoid creating __pycache__ when this read-only command imports the validator.
sys.dont_write_bytecode = True
from loop_workspace import SCOPE, decode, load_workspace, require, status
from loop_control import validate_extra


HISTORY_FIELDS = ('action', 'timestamp', 'time', 'task', 'task_id', 'decision', 'decision_id', 'kind', 'status',
                  'outcome', 'answer', 'reason', 'artifact_version')


def build_graph(plan, state):
    """Build a pure typed graph of declarations and records, never runtime claims.

    Optional agents: plan.agents [{id,label}], task.agent_id (planned), or
    state.tasks[id].agent_id with nonempty agent_source (recorded attribution).
    Unknown or malformed optional metadata is ignored; no identity is inferred.
    """
    nodes, edges, tasks, checks, decisions, agents = [], [], {}, {}, {}, {}

    def node(kind, label, value, provenance, reference):
        identifier = 'n' + str(len(nodes))
        nodes.append(dict(id=identifier, kind=kind, label=label, status=value,
                          provenance=provenance, reference=reference))
        return identifier

    def edge(source, target, kind, provenance='planned'):
        edges.append(dict(source=source, target=target, kind=kind, provenance=provenance))

    records = plan.get('agents', [])
    for record in records if isinstance(records, list) else []:
        if (isinstance(record, dict) and isinstance(record.get('id'), str)
                and record['id'].strip() and isinstance(record.get('label'), str)
                and record['label'].strip() and record['id'] not in agents):
            agents[record['id']] = node('agent', record['label'], '선언', 'planned', record['id'])
    for decision in plan.get('decisions', []):
        item = state['decisions'][decision['id']]
        recorded = item['status'] == 'resolved'
        decisions[decision['id']] = node('decision', decision['id'],
            item.get('outcome') if recorded else 'pending',
            'recorded' if recorded else 'planned', decision['id'])
    for task in plan['tasks']:
        name, item = task['id'], state['tasks'][task['id']]
        tasks[name] = node('task', task['title'], item['status'], 'recorded', name)
        checks[name] = []
        for check in task['checks']:
            evidence = [r for r in item['evidence'] if r['check_id'] == check['id']]
            result = ('stale' if item['status'] == 'stale' else
                      'mixed' if len(evidence) > 1 else evidence[0]['result']) if evidence else '미기록'
            identifier = node('verification', check['id'], result,
                              'recorded' if evidence else 'planned', name + ':' + check['id'])
            checks[name].append(identifier)
            edge(tasks[name], identifier, 'verification', 'recorded' if evidence else 'planned')
        recorded_agent = item.get('agent_id')
        source = item.get('agent_source')
        if isinstance(recorded_agent, str) and recorded_agent in agents and isinstance(source, str) and source.strip():
            edge(agents[recorded_agent], tasks[name], 'assignment', 'recorded')
        elif isinstance(task.get('agent_id'), str) and task['agent_id'] in agents:
            edge(agents[task['agent_id']], tasks[name], 'assignment')
    for task in plan['tasks']:
        for dependency in task['depends_on']:
            for predecessor in checks[dependency] or [tasks[dependency]]:
                edge(predecessor, tasks[task['id']], 'dependency')
        for decision in task['decision_ids']:
            edge(decisions[decision], tasks[task['id']], 'gate')
    # A failed current status or retry budget alone is not a recorded restart.
    for event in state.get('history', []):
        if event.get('action') != 'start':
            continue
        for name, previous in event.get('previous_tasks', {}).items():
            if name in tasks and previous.get('status') == 'failed' and isinstance(previous.get('attempts'), int) and previous['attempts'] > 0:
                failed = next((n for n in nodes if n['kind'] == 'verification' and
                               n['reference'] == name + ':' + next((r['check_id'] for r in previous.get('evidence', [])
                                                                  if r.get('result') == 'failed'), '')), None)
                edge(failed['id'] if failed else tasks[name], tasks[name], 'rework', 'recorded')
    return dict(nodes=nodes, edges=edges)


def layout_graph(graph, mobile=False):
    """Stable layered DAG layout; mobile uses a separate full-size vertical flow."""
    incoming = {node['id']: [] for node in graph['nodes']}
    for edge in graph['edges']:
        if edge['kind'] != 'rework':
            incoming[edge['target']].append(edge['source'])
    levels, remaining = {}, list(incoming)
    while remaining:
        ready = [key for key in remaining if all(parent in levels for parent in incoming[key])]
        require(bool(ready), 'graph dependency cycle')
        for key in ready:
            levels[key] = max((levels[parent] + 1 for parent in incoming[key]), default=0)
            remaining.remove(key)
    order = sorted(incoming, key=lambda key: (levels[key], int(key[1:])))
    positions, rows = {}, {}
    for index, key in enumerate(order):
        level = levels[key]
        row = rows.get(level, 0)
        rows[level] = row + 1
        positions[key] = dict(x=90 if mobile else 56 + level * 250,
                              y=48 + (index if mobile else row) * 124,
                              width=180, height=76)
    return dict(positions=positions, width=360 if mobile else max(440, 112 + (max(levels.values(), default=0) + 1) * 250),
                height=max(200, 96 + (len(order) if mobile else max(rows.values(), default=0)) * 124))


GRAPH_BASE_STYLE = '''
svg{font-family:system-ui,sans-serif;background:transparent;color:#edf5ff}
.node-body{stroke:#7ebdff;stroke-width:1.5}
.node.verification .node-body{stroke:#53e4bf}.node.decision .node-body{stroke:#f1c577}.node.agent .node-body{stroke:#c2a1ff}
.node.planned .node-body{stroke-dasharray:5 4}
.node text{text-anchor:middle;font-size:13px;font-weight:600;pointer-events:none}
.node .kind{fill:#7ebdff;font-size:9px;letter-spacing:1.6px;font-weight:600}
.node.verification .kind{fill:#53e4bf}.node.decision .kind{fill:#f1c577}.node.agent .kind{fill:#c2a1ff}
.node .status{font-size:10px;font-weight:600;letter-spacing:.3px}
.edge{fill:none;stroke:#6383a5;stroke-width:1.4}
.edge.verification{stroke:#458e88}.edge.assignment{stroke:#8b76b3}.edge.gate{stroke:#a58e62}
.edge.planned{stroke-dasharray:5 5}.edge.rework{stroke:#ee8297;stroke-width:1.9}
.focus-ring{fill:none;stroke:#eef7ff;stroke-width:3;opacity:0;pointer-events:none}
.status-mark{stroke:none}
.node-content{opacity:1}
.flow-overlay{display:none}
.node-halo{display:none}
'''

# Keep advanced CSS separate: static SVG tools that reject custom properties or
# :has must still parse the basic semantic stylesheet and presentation values.
GRAPH_STYLE = '''
.node{--type:#7ebdff;--status:#b1c1d6;outline:none}
.node.verification{--type:#53e4bf}.node.decision{--type:#f1c577}.node.agent{--type:#c2a1ff}
.node-body{filter:drop-shadow(0 7px 9px #0006)}
.node .kind{fill:var(--type)}.node .status{fill:var(--status)}
.node.state-passed,.node.state-approved{--status:#77f1c3}
.node.state-failed,.node.state-rejected,.node.state-mixed{--status:#ff9ca9}
.node.state-blocked,.node.state-stale,.node.state-revision_requested{--status:#f5ce83}
.node.state-running,.node.state-answered{--status:#a5d4ff}
.node.state-cancelled{--status:#a9b5c5}
.status-mark{fill:var(--status);stroke:none}
.node-halo{display:inline;fill:none;stroke:var(--status);stroke-width:2.8;stroke-linecap:round;stroke-dasharray:90 910;filter:drop-shadow(0 0 4px var(--status));opacity:.75;animation:graph-orbit 5.4s linear infinite;animation-delay:var(--halo-delay,0ms);pointer-events:none}
.node:is(:hover,:focus-visible) .focus-ring{opacity:1}
.node:focus-visible{outline:2px solid #eef7ff;outline-offset:7px;border-radius:12px}
.node-content{opacity:1;transform:none;transform-box:fill-box;transform-origin:center;animation:graph-enter .78s cubic-bezier(.16,1,.3,1) both;animation-delay:var(--enter-delay,0ms)}
.flow-overlay{display:inline;pointer-events:none}
.flow-bundle{--flow:#8ecaff;opacity:.9}
.flow-bundle.verification{--flow:#68f5cb}.flow-bundle.assignment{--flow:#c6a2ff}
.flow-bundle.gate{--flow:#ffdc91}.flow-bundle.rework{--flow:#ff8eaa}
.flow-bundle.planned{opacity:.48}
.flow-bundle path{fill:none;stroke:var(--flow);stroke-linecap:round;animation:graph-flow var(--flow-duration,3600ms) linear infinite;animation-delay:var(--flow-delay,0ms)}
.flow-beam{stroke-width:6;stroke-dasharray:110 890;opacity:.2;filter:drop-shadow(0 0 5px var(--flow))}
.flow-trace{stroke-width:2;stroke-dasharray:72 928;opacity:.65}
.flow-bundle .flow-packet{stroke:#f3fcff;stroke-width:3.4;stroke-dasharray:2 998;filter:drop-shadow(0 0 3px var(--flow));animation-name:graph-packet}
@keyframes graph-enter{from{opacity:0;transform:translateY(14px) scale(.96)}to{opacity:1;transform:translateY(0) scale(1)}}
@keyframes graph-flow{from{stroke-dashoffset:1000}to{stroke-dashoffset:0}}
@keyframes graph-packet{from{stroke-dashoffset:930}to{stroke-dashoffset:-70}}
@keyframes graph-orbit{from{stroke-dashoffset:1000}to{stroke-dashoffset:0}}
@supports selector(:has(*)){
svg:has(.node:is(:hover,:focus-visible)) .node-body{fill-opacity:.35}
svg:has(.node:is(:hover,:focus-visible)) .flow-bundle{opacity:.05}
svg:has(.node:is(:hover,:focus-visible)) .flow-bundle path,
svg:has(.node:is(:hover,:focus-visible)) .node-halo{animation-play-state:paused}
svg:has(.node:focus-visible) .node:not(:focus-visible) .focus-ring{opacity:0}
}
'''

# Hard limits apply only to decorative copies, never to nodes or relationships.
MAX_FLOW_EFFECTS = 24
MAX_NODE_EFFECTS = 24
NODE_SHAPES = {
    'task': ('rect', 'width="180" height="76" rx="15"'),
    'verification': ('polygon', 'points="18,0 162,0 180,38 162,76 18,76 0,38"'),
    'decision': ('polygon', 'points="90,0 180,38 90,76 0,38"'),
    'agent': ('ellipse', 'cx="90" cy="38" rx="90" ry="38"'),
}
TYPE_COLORS = {'task': '#7ebdff', 'verification': '#53e4bf', 'decision': '#f1c577', 'agent': '#c2a1ff'}
STATUS_COLORS = {'passed': '#77f1c3', 'approved': '#77f1c3', 'failed': '#ff9ca9',
                 'rejected': '#ff9ca9', 'mixed': '#ff9ca9', 'blocked': '#f5ce83',
                 'stale': '#f5ce83', 'revision_requested': '#f5ce83', 'running': '#a5d4ff',
                 'answered': '#a5d4ff', 'cancelled': '#a9b5c5'}

# Only known states become CSS classes; untrusted record values stay in text.
STATE_LABELS = {'pending': '대기', 'running': '진행', 'passed': '통과', 'failed': '실패',
                'blocked': '차단', 'stale': '재검증', 'cancelled': '취소', 'approved': '승인',
                'rejected': '반려', 'answered': '답변', 'revision_requested': '수정 요청', 'mixed': '상충 기록'}


def render_graph(graph, text, mobile=False):
    """Only generated IDs enter SVG attributes; all record strings are text nodes."""
    layout = layout_graph(graph, mobile)
    prefix = 'mobile' if mobile else 'desktop'
    sizing = '' if mobile else f' style="width:{layout["width"]}px"'
    parts = [f'<svg{sizing} xmlns="http://www.w3.org/2000/svg" class="graph-{prefix}" role="group" aria-labelledby="{prefix}-title {prefix}-desc" viewBox="0 0 {layout["width"]} {layout["height"]}">',
             f'<title id="{prefix}-title">작업 · 검증 · 결정 파이프라인</title>',
             f'<desc id="{prefix}-desc">사각형 작업, 육각형 검증, 마름모 결정, 타원 에이전트. 점선은 계획, 실선은 기록, 붉은 곡선은 기록된 재시도. Tab 또는 마우스로 노드의 인접 관계를 강조합니다. 연출 모션은 실시간 실행이나 이력 재생이 아닙니다. 전체 항목과 관계는 아래 상세 기록에 있습니다.</desc>',
             '<style>' + GRAPH_BASE_STYLE + '</style>', '<style>' + GRAPH_STYLE + '</style>',
             f'<defs><marker id="{prefix}-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="#90a9c6"/></marker>',
             f'<marker id="{prefix}-retry" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="#ff8c91"/></marker>']
    for kind, light, dark in (('task', '#193d60', '#0d2038'),
                               ('verification', '#13453f', '#0b282d'),
                               ('decision', '#4a3b26', '#292331'),
                               ('agent', '#3c315b', '#221d38')):
        parts.append(f'<linearGradient id="{prefix}-surface-{kind}" x1="0" y1="0" x2="1" y2="1">'
                     f'<stop offset="0" stop-color="{light}"/><stop offset="1" stop-color="{dark}"/></linearGradient>')
    parts.append('</defs>')
    # Progressive enhancement: if :has is unsupported the full graph stays
    # readable and native focus rings still work. IDs come from build_graph,
    # never record labels. The neighborhood is derived from real edges only.
    neighbors = {node['id']: {node['id']} for node in graph['nodes']}
    for edge in graph['edges']:
        neighbors[edge['source']].add(edge['target'])
        neighbors[edge['target']].add(edge['source'])
    focus_rules = ['@supports selector(:has(*)){']
    for node in graph['nodes']:
        identifier = node['id']
        # A stationary pointer must not create a second highlighted scene while
        # keyboard focus moves. Focus takes precedence, without JavaScript.
        scope = (f'.graph-{prefix}:is(:has(#{prefix}-{identifier}:focus-visible),'
                 f':not(:has(.node:focus-visible)):has(#{prefix}-{identifier}:hover))')
        related = ','.join(f'#{prefix}-{key}' for key in sorted(neighbors[identifier], key=lambda key: int(key[1:])))
        relation = f':is([data-source="{identifier}"],[data-target="{identifier}"])'
        focus_rules.append(f'{scope} :is({related}) .node-body' + '{fill-opacity:1}')
        focus_rules.append(f'{scope} :is(.edge,.flow-bundle){relation}' + '{opacity:1}')
        focus_rules.append(f'{scope} .edge{relation}' + '{stroke-width:2.4}')
        focus_rules.append(f'{scope} .flow-bundle{relation} path,{scope} #{prefix}-{identifier} .node-halo'
                           + '{animation-play-state:running}')
    parts.append('<style>' + '\n'.join(focus_rules) + '\n}</style>')
    # Recorded retry edges get presentation priority without inventing events;
    # all base paths remain present even when dense graphs exhaust this budget.
    effect_order = sorted(range(len(graph['edges'])), key=lambda i: (
        graph['edges'][i]['kind'] != 'rework', graph['edges'][i]['provenance'] != 'recorded', i))
    animated_edges = set(effect_order[:MAX_FLOW_EFFECTS])
    highlights = []
    for index, edge in enumerate(graph['edges']):
        a, b = (layout['positions'][edge[key]] for key in ('source', 'target'))
        retry = edge['kind'] == 'rework'
        if mobile:
            x1, y1, x2, y2 = a['x'], a['y'] + 38, b['x'], b['y'] + 38
            lane = 18 + (index % 5) * 12
            if retry:
                x1, x2, lane = 270, 270, 342
            if edge['source'] == edge['target']:
                y1, y2 = a['y'] + 58, a['y'] + 18
            path = f'M{x1},{y1} C{lane},{y1} {lane},{y2} {x2},{y2}'
        else:
            x1, y1, x2, y2 = a['x'] + 180, a['y'] + 38, b['x'], b['y'] + 38
            if retry:
                left, right = x2 - 24, x1 + 24
                path = (f'M{x1},{y1} Q{right},{y1} {right},{y1 - 20} '
                        f'L{right},28 Q{right},8 {right - 20},8 L{left + 20},8 '
                        f'Q{left},8 {left},28 L{left},{y2 - 20} Q{left},{y2} {x2},{y2}')
            elif x2 - x1 > 70:
                path = f'M{x1},{y1} L{x1 + 20},{y1} L{x1 + 20},24 L{x2 - 20},24 L{x2 - 20},{y2} L{x2},{y2}'
            else:
                mid = (x1 + x2) / 2
                path = f'M{x1},{y1} C{mid},{y1} {mid},{y2} {x2},{y2}'
        endpoints = f'data-source="{edge["source"]}" data-target="{edge["target"]}"'
        parts.append(f'<path class="edge {edge["kind"]} {edge["provenance"]}" {endpoints} d="{path}" fill="none" marker-end="url(#{prefix}-{"retry" if retry else "arrow"})"><title>{text(edge["kind"])} · {text(edge["provenance"])}</title></path>')
        # The original path and arrow stay fixed. Its optional highlight has no
        # semantic title, marker or ID, and cannot create another relationship.
        if index in animated_edges:
            # Normalized path lengths keep packets directional even on long
            # bypass/retry routes. These are never timestamps or event speeds.
            duration = 4800 if retry else 3200 + (index % 4) * 350
            highlights.append(f'<g class="flow-bundle {edge["kind"]} {edge["provenance"]}" {endpoints} '
                              f'style="--flow-delay:-{(index % 11) * 310}ms;--flow-duration:{duration}ms">'
                              + ''.join(f'<path class="{layer}" d="{path}" pathLength="1000"/>'
                                        for layer in ('flow-beam', 'flow-trace', 'flow-packet')) + '</g>')
    parts.append('<g class="flow-overlay" aria-hidden="true" focusable="false">' + ''.join(highlights) + '</g>')
    labels = {'task': '작업', 'verification': '검증', 'decision': '결정', 'agent': '에이전트'}
    # Layout order is topological, independent of the order records were read.
    # Cap the stagger so even large graphs finish revealing promptly.
    entrance = {identifier: min(index * 55, 660)
                for index, identifier in enumerate(layout['positions'])}
    for index, node in enumerate(graph['nodes']):
        box = layout['positions'][node['id']]
        x, y = box['x'], box['y']
        state_class = node['status'] if node['status'] in STATE_LABELS else 'unknown'
        description = labels[node['kind']] + ' · ' + ' · '.join(
            text(node[key]) for key in ('reference', 'label', 'status', 'provenance'))
        parts.append(f'<g id="{prefix}-{node["id"]}" class="node {node["kind"]} {node["provenance"]} state-{state_class}" transform="translate({x} {y})" tabindex="0" role="img" aria-label="{description}">')
        parts.append('<title>' + description + '</title>')
        parts.append(f'<g class="node-content" style="--enter-delay:{entrance[node["id"]]}ms">')
        shape, geometry = NODE_SHAPES[node['kind']]
        parts.append(f'<{shape} class="node-body" {geometry} fill="url(#{prefix}-surface-{node["kind"]})"/>')
        parts.append(f'<{shape} class="focus-ring" {geometry} aria-hidden="true" focusable="false"/>')
        if index < MAX_NODE_EFFECTS:
            parts.append(f'<{shape} class="node-halo" {geometry} pathLength="1000" aria-hidden="true" focusable="false" style="--halo-delay:-{(index % 9) * 480}ms"/>')
        status_color = STATUS_COLORS.get(state_class, '#b1c1d6')
        parts.append(f'<circle class="status-mark" cx="90" cy="9" r="2" fill="{status_color}" aria-hidden="true" focusable="false"/>')
        label = node['label']
        # Clamp visible labels only; full escaped text remains in titles/details.
        limit = 9 if node['kind'] == 'decision' else 13
        short = label if len(label) <= limit else label[:limit - 1] + '…'
        parts.append(f'<text x="90" y="22" class="kind" fill="{TYPE_COLORS[node["kind"]]}">' + labels[node['kind']] + '</text>')
        parts.append('<text x="90" y="42" fill="#edf5ff">' + text(short) + '</text>')
        value = STATE_LABELS.get(node['status'], str(node['status'] or '미기록'))
        parts.append(f'<text x="90" y="59" class="status" fill="{status_color}">' + text(value[:16]) + '</text></g></g>')
    parts.append('</svg>')
    return '\n'.join(parts)


def render(plan, state, warnings, history):
    """Render only selected metadata; all record text is escaped and inert."""
    root = state['project_root']

    def text(value):
        if value is None:
            return '—'
        raw = str(value).replace(root, '[project]')
        # Free-text fields can contain other local absolute paths. Redact those
        # too; this is path minimization, not a promise to remove all secrets.
        raw = re.sub(r'(?<![\w:/])(?:[A-Za-z]:[\\/]|/)[^\s<>"\']+', '[absolute path]', raw)
        return escape(raw, quote=True)

    def field(label, value):
        return '<dt>' + text(label) + '</dt><dd>' + text(value) + '</dd>'

    summary = status(plan, state, warnings)
    parts = ['''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Guided execution · 기록 보고서</title>
<style>
:root{color-scheme:light dark;font-family:system-ui,sans-serif;line-height:1.6}
body{max-width:1440px;margin:auto;padding:40px 28px;background:#080f1d;color:#e8eef8}
h1,h2,h3{line-height:1.3}h2{margin-top:2rem}p,dd,td,li{overflow-wrap:anywhere}
.panel,article{background:#1b2638;border:1px solid #46546c;border-radius:12px;padding:18px;margin:16px 0}
.notice{border-left:5px solid #ffc663}dt{color:#abbcd3;font-size:.9rem}dd{margin:0 0 10px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:9px;border-bottom:1px solid #46546c;vertical-align:top}
.badge{display:inline-block;border:1px solid #8495af;border-radius:6px;padding:2px 8px;margin:3px}
.scroll{overflow:auto}small{color:#becbe0}
.graph-shell{overflow-x:auto;border:1px solid #36506c;border-radius:22px;margin:18px 0;background-color:#0b1525;background-image:radial-gradient(#9db9d51a .7px,transparent .7px),radial-gradient(ellipse at 24% 0,#1a46664d,transparent 62%),radial-gradient(ellipse at 86% 100%,#41346633,transparent 55%);background-size:20px 20px,100% 100%,100% 100%;box-shadow:0 24px 70px #0005,inset 0 1px #c5ddff12;scrollbar-color:#42617d #0b1525}
.graph-desktop{display:block;width:100%;min-width:900px;height:auto}.graph-mobile{display:none}
.graph-caption{display:inline-block;margin:10px 18px 4px 0;font-size:12px;color:#bed0e5}.focus-hint{font-size:11px;color:#829ab7;margin-left:14px}
#graph-motion{width:16px;height:16px;vertical-align:middle;margin:0 5px 0 0;accent-color:#91c8ee;cursor:pointer}
.motion-switch{display:inline-block;vertical-align:middle;font-size:12px;color:#bed0e5;padding:5px 6px;cursor:pointer;border-radius:5px}
#graph-motion:focus-visible{outline:2px solid #bfddff;outline-offset:5px}
.motion-switch:hover{background:#283b51}.motion-reduced-note{display:none;font-size:11px;color:#aabdd1;margin-left:8px}
#graph-motion:not(:checked)~.graph-shell *{animation:none!important;transition:none!important}
#graph-motion:not(:checked)~.graph-shell .node-content{opacity:1;transform:none}
#graph-motion:not(:checked)~.graph-shell .flow-overlay{display:none}
#graph-motion:not(:checked)~.graph-shell .node-halo{display:none}
.legend{display:flex;flex-wrap:wrap;gap:10px 22px;color:#b7c9de;font-size:13px;margin:12px 0}
.task-key{color:#78b8ff}.check-key{color:#5ed5bf}.decision-key{color:#e9c46a}.agent-key{color:#bc9bfa}
summary{cursor:pointer;padding:14px 0;font-weight:650}details{border-top:1px solid #344c65;margin-top:24px}
header p{font-size:10px;letter-spacing:3px;color:#85a6ca}h1{font-size:34px;font-weight:700;letter-spacing:-1.2px;margin:8px 0}
.subtitle{font-size:13px;color:#b7c9de}.goal{font-size:16px;max-width:70ch}
@media(max-width:600px){body{padding:20px 10px}.graph-desktop{display:none}.graph-mobile{display:block;width:100%;height:auto}.graph-mobile .node text{font-size:14px}.graph-mobile .node .kind{font-size:10px}.graph-mobile .node .status{font-size:11px}.graph-shell{overflow:hidden;border-radius:16px}h1{font-size:27px}.panel,article{padding:12px}.legend{gap:8px 16px}.focus-hint{display:block;margin:6px 0}}
@media(prefers-reduced-motion:reduce){
.graph-shell *{animation:none!important;transition:none!important}
.graph-shell .node-content{opacity:1;transform:none}
.graph-shell .flow-overlay{display:none}
.graph-shell .node-halo{display:none}
.motion-reduced-note{display:inline}
}

</style></head><body><header><p>GUIDED EXECUTION · ONTOLOGY</p><h1>작업 파이프라인</h1></header>''']
    graph = build_graph(plan, state)
    parts.append('<p class="goal">' + text(plan['goal']) + '</p>')
    parts.append('<p class="subtitle">정적 기록 · 실시간 실행·이력 재생 아님</p>')
    parts.append('<section class="graph-view" aria-label="기록 시각화"><p class="graph-caption">기록 시각화 · 연출 모션</p> '
                 '<input type="checkbox" id="graph-motion" checked aria-controls="graph-canvas">'
                 '<label class="motion-switch" for="graph-motion">모션 켜기</label>'
                 '<span class="motion-reduced-note">기기 설정: 모션 줄임</span>'
                 '<span class="focus-hint">노드에 마우스 · Tab → 연결 강조</span>'
                 '<div class="graph-shell" id="graph-canvas">' + render_graph(graph, text) + render_graph(graph, text, mobile=True) + '</div></section>')
    parts.append('<div class="legend" aria-label="범례"><span class="task-key">▢ 작업</span><span class="check-key">⬡ 검증</span><span class="decision-key">◇ 결정</span><span class="agent-key">◯ 에이전트</span><span>┄→ 계획</span><span>━→ 기록</span><span style="color:#ff8c91">↶ 재시도 기록</span></div>')
    if not any(node['kind'] == 'agent' for node in graph['nodes']):
        parts.append('<p class="subtitle">에이전트 기록 없음</p>')
    parts.append('<details><summary>범위 · 범례 · 기록 해석</summary><section class="panel notice"><h2>검증 범위: record_integrity_only</h2><p>저장된 기록의 구조·참조·해시만 확인했습니다. 명령 실행 여부, 의미적 정확성, 실제 제품의 현재 버전은 증명하지 않습니다. 실시간 화면이나 실행 제어기가 아닙니다. 등장 순서와 선의 움직임은 읽기를 돕는 연출이며 실제 실행·상태 전이·시간 재생이 아닙니다. 모션 켜기는 이 연출만 바꾸며 기기의 모션 줄임 설정이 우선합니다.</p><p>사각형은 작업, 육각형은 검사, 마름모는 결정 게이트, 타원은 명시된 에이전트입니다. 점선은 계획의 관계·미기록 검사, 실선은 저장된 결과·배정입니다. 의존성은 선행 검증에서 후속 작업으로 연결되며 실제 실행 순서를 증명하지 않습니다. 붉은 곡선은 실패 상태에서 재시작한 이력만 나타냅니다. 현재 노드로 돌아오는 이력이며 현재 검사 실패를 뜻하지 않습니다. 에이전트 배정은 작성자 기록이며 인증된 실행 관찰이 아닙니다.</p><p>증거 로그 원문·브리프·학습 기록은 표시하지 않습니다. 공유 전 민감한 텍스트를 검토하고, 기록 작성자를 멈춘 상태에서 생성하세요.</p></section></details>')
    parts.append('<details><summary>상세 기록 · 상태 · 증거 · 이력</summary>')
    parts.append('<section><h2>그래프 관계</h2><ul>')
    node_by_id = {node['id']: node for node in graph['nodes']}
    for node in graph['nodes']:
        parts.append('<li>' + text(node['kind']) + ' · ' + text(node['reference']) + ' · ' +
                     text(node['label']) + ' · ' + text(node['status']) + ' · ' +
                     text(node['provenance']) + '</li>')
    parts.append('</ul><ul>')
    for edge in graph['edges']:
        parts.append('<li>' + text(node_by_id[edge['source']]['reference']) + ' → ' +
                     text(node_by_id[edge['target']]['reference']) + ' · ' +
                     text(edge['kind']) + ' · ' + text(edge['provenance']) + '</li>')
    parts.append('</ul></section>')
    parts.append('<section class="panel"><h2>목표</h2><p>' + text(plan['goal']) + '</p><dl>')
    parts.append(field('Run', state['run_id']))
    parts.append(field('생성 시각 (UTC)', datetime.now(timezone.utc).isoformat(timespec='seconds')))
    parts.append(field('Plan SHA-256', state['plan_sha256']))
    parts.append(field('기록상 전체 통과 (제품 완료 보증 아님)', str(summary['complete']).lower()))
    parts.append(field('질문 / 라운드 사용', str(state['question_usage']['questions']) + ' / ' + str(state['question_usage']['rounds'])))
    parts.append('</dl></section><section><h2>상태 분류</h2><div class="grid">')
    for category, names in summary.items():
        if isinstance(names, list) and category != 'serialization_warnings':
            parts.append('<div class="panel"><strong>' + text(category) + '</strong><p>' +
                         text(', '.join(names) or '없음') + '</p></div>')
    parts.append('</div></section><section><h2>작업과 의존성</h2>')
    for task in plan['tasks']:
        item = state['tasks'][task['id']]
        parts.append('<article><h3>' + text(task['id']) + ' · ' + text(task['title']) + '</h3>')
        parts.append('<span class="badge">' + text(item['status']) + '</span><dl>')
        for label, value in [('선행 작업', ', '.join(task['depends_on']) or '없음'),
                             ('관련 결정', ', '.join(task['decision_ids']) or '없음'),
                             ('시도 / 한도', str(item['attempts']) + ' / ' + str(task['max_attempts'])),
                             ('차단 이유', item.get('block_reason')), ('기록된 검증 버전', item.get('verified_revision'))]:
            parts.append(field(label, value))
        parts.append('</dl><h4>선언된 검사</h4><ul>')
        for check in task['checks']:
            # Commands are deliberately omitted, not executed or turned into controls.
            parts.append('<li>' + text(check['id']) + ': ' + text(check['description']) + '</li>')
        parts.append('</ul><h4>현재 기록된 증거 메타데이터</h4>')
        if item['evidence']:
            parts.append('<div class="scroll"><table><thead><tr><th>검사 / 결과</th><th>상대 경로</th><th>버전 / SHA-256</th></tr></thead><tbody>')
            for record in item['evidence']:
                parts.append('<tr><td>' + text(record['check_id']) + ' / ' + text(record['result']) +
                             '</td><td>' + text(record['path']) + '</td><td>' + text(record['artifact_version']) +
                             '<br>' + text(record['sha256']) + '</td></tr>')
            parts.append('</tbody></table></div>')
        else:
            parts.append('<p>기록된 증거 없음</p>')
        parts.append('</article>')
    parts.append('</section><section><h2>결정 기록</h2>')
    for decision in plan.get('decisions', []):
        item = state['decisions'][decision['id']]
        parts.append('<article><h3>' + text(decision['id']) + '</h3><dl>')
        for label, value in [('종류', decision['kind']), ('질문', decision['question']),
                             ('상태', item['status']), ('결과', item.get('outcome')),
                             ('답변 / 이유', item.get('answer')), ('버전', item.get('artifact_version'))]:
            parts.append(field(label, value))
        parts.append('</dl></article>')
    if not plan.get('decisions'):
        parts.append('<p>결정 없음</p>')
    parts.append('</section><section><h2>기록 이력</h2><p>이력은 사용자 입력의 진위나 승인 권한을 검증하지 않은 참고 기록입니다. 선택된 메타데이터만 표시합니다.</p><ol>')
    entries = list(state.get('history', []))
    try:
        for line in history.decode('utf-8').splitlines():
            if line.strip():
                entry = decode(line)
                require(isinstance(entry, dict), 'history must be an object')
                entries.append(entry)
    except (ValueError, TypeError, RecursionError) as error:
        # Never echo malformed history or parser diagnostics containing its text.
        raise ValueError('invalid decisions.jsonl history') from error
    for entry in entries:
        fields = [(key, entry[key]) for key in HISTORY_FIELDS
                  if key in entry and isinstance(entry[key], (str, int, float, bool))]
        parts.append('<li><dl>' + ''.join(field(key, value) for key, value in fields) +
                     '</dl>' + ('' if fields else '표시 가능한 메타데이터 없음') + '</li>')
    if not entries:
        parts.append('<li>이력 없음</li>')
    parts.append('</ol></section><section><h2>직렬화 경고</h2><ul>')
    for warning in warnings:
        parts.append('<li>' + text(json.dumps(warning, ensure_ascii=False)) + '</li>')
    if not warnings:
        parts.append('<li>없음</li>')
    parts.append('</ul></section></details><footer><small>정적 스냅샷 · ' + text(SCOPE) + '</small></footer></body></html>')
    return '\n'.join(parts)


def write_report(workspace, output):
    destination = Path(os.path.abspath(output))
    for component in (destination, *destination.parents):
        require(not component.is_symlink(), 'output symlinks are forbidden')
    source = Path(workspace).resolve(strict=True)
    require(not destination.resolve().is_relative_to(source), 'output must be outside the workspace')
    require(not destination.exists(), 'output must be a new file')
    validated_workspace, files, plan, state, warnings = load_workspace(workspace)
    validate_extra(validated_workspace, plan, state)
    html = render(plan, state, warnings, files['decisions.jsonl'])
    # Exclusive creation never truncates existing data, including a symlink
    # appearing at the final filename between the check and the open.
    with destination.open('x', encoding='utf-8') as handle:
        handle.write(html)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        write_report(args.workspace, args.output)
        print(json.dumps({'created': True, 'verification_scope': SCOPE}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        print('error: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
