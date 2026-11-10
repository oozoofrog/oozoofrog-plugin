"""Read-only report CLI tests on actual workspaces and hostile record text."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import render_report


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.attrs = []
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs.extend(attrs)
        self.elements.append((tag, dict(attrs)))


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        self.workspace = self.project / '.agent-loop' / 'report-test'
        self.output = self.root / 'report.html'
        self.plan = {'schema_version': 1, 'goal': '안전한 작업 <script>alert(1)</script>',
                     'decisions': [{'id': 'review', 'kind': 'review', 'question': '검토할까요?'}],
                     'tasks': [{'id': name, 'title': name + ' 작업', 'depends_on': deps,
                                'reads': ['source.txt'], 'writes': [name + '.txt'],
                                'max_attempts': 2, 'decision_ids': decisions,
                                'checks': [{'id': 'unit', 'description': '검증',
                                            'command': 'touch SHOULD_NOT_RUN'}]}
                               for name, deps, decisions in [('build', [], []),
                                    ('blocked', ['build'], ['review']), ('stale', [], []),
                                    ('cancelled', [], []), ('exhausted', [], [])]]}
        plan = self.root / 'plan.json'
        plan.write_text(json.dumps(self.plan), encoding='utf-8')
        brief = self.root / 'brief.md'
        brief.write_text('Private brief must not be copied wholesale', encoding='utf-8')
        result = subprocess.run([sys.executable, str(SCRIPTS / 'loop_workspace.py'), 'init',
                                 '--project', str(self.project), '--run-id', 'report-test',
                                 '--plan', str(plan), '--brief', str(brief)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.state = json.loads((self.workspace / 'state.json').read_text())
        self.state['tasks']['blocked'].update(status='blocked', block_reason='환경 준비 필요')
        self.state['tasks']['stale']['status'] = 'stale'
        self.state['tasks']['cancelled']['status'] = 'cancelled'
        self.state['tasks']['exhausted'].update(status='failed', attempts=2)
        self.state['decisions']['review'].update(status='resolved', outcome='rejected', answer='범위를 줄여 주세요')
        self.save()

    def save(self):
        (self.workspace / 'state.json').write_text(json.dumps(self.state), encoding='utf-8')

    def snapshot(self):
        return {str(p.relative_to(self.workspace)): p.read_bytes()
                for p in self.workspace.rglob('*') if p.is_file()}

    def run_report(self, output=None):
        return subprocess.run([sys.executable, str(SCRIPTS / 'render_report.py'),
                               '--workspace', str(self.workspace), '--output', str(output or self.output)],
                              cwd=self.root, capture_output=True, text=True)

    def test_snapshot_shows_classifications_without_mutation_or_execution(self):
        before = self.snapshot()
        result = self.run_report()
        self.assertEqual(result.returncode, 0, result.stderr)
        html = self.output.read_text(encoding='utf-8')
        for expected in ('안전한 작업', 'record_integrity_only', 'blocked_by_dependencies',
                         'blocked_by_decisions', 'needs_revalidation', 'exhausted', 'cancelled',
                         '환경 준비 필요', '범위를 줄여 주세요', 'rejected', '2 / 2'):
            self.assertIn(expected, html)
        self.assertNotIn(str(self.project), html)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.root / 'SHOULD_NOT_RUN').exists())

    def test_hostile_strings_are_text_and_evidence_is_metadata_only(self):
        log = self.workspace / 'evidence' / 'unit.log'
        log.write_text('SECRET_RAW_LOG', encoding='utf-8')
        self.state['tasks']['build'].update(status='passed', attempts=1, verified_revision='revision-1',
            evidence=[{'check_id': 'unit', 'result': 'passed', 'path': 'evidence/unit.log',
                       'sha256': hashlib.sha256(log.read_bytes()).hexdigest(), 'artifact_version': 'revision-1'}])
        self.state['tasks']['blocked']['block_reason'] = '<img src=x onerror=alert(1)> https://evil.example'
        self.save()
        history = {'reason': '<svg onload=alert(1)> ' + str(self.project / 'secret.txt'),
                   'outcome': 'rejected', 'raw_log': 'SECRET_HISTORY_LOG'}
        (self.workspace / 'decisions.jsonl').write_text(json.dumps(history) + '\n', encoding='utf-8')
        result = self.run_report()
        self.assertEqual(result.returncode, 0, result.stderr)
        html = self.output.read_text(encoding='utf-8')
        parser = Tags()
        parser.feed(html)
        self.assertFalse(set(parser.tags) & {'script', 'img', 'a', 'button', 'form', 'iframe', 'foreignobject', 'animate', 'set'})
        self.assertFalse(any(k.startswith('on') or k in {'href', 'src'} for k, _ in parser.attrs))
        for expected in ('&lt;script&gt;', '&lt;img', '&lt;svg', 'evidence/unit.log', 'revision-1', history['outcome']):
            self.assertIn(expected, html)
        for secret in ('SECRET_RAW_LOG', 'SECRET_HISTORY_LOG', str(self.project)):
            self.assertNotIn(secret, html)

    def test_graph_is_typed_and_does_not_invent_agents_or_retries(self):
        self.assertTrue(hasattr(render_report, 'build_graph'), 'pure graph builder required')
        graph = render_report.build_graph(self.plan, self.state)
        kinds = {node['kind'] for node in graph['nodes']}
        self.assertEqual(kinds, {'task', 'verification', 'decision'})
        self.assertFalse(any(edge['kind'] == 'rework' for edge in graph['edges']))
        self.assertTrue(any(edge['kind'] == 'dependency' for edge in graph['edges']))
        self.assertTrue(any(edge['kind'] == 'gate' for edge in graph['edges']))
        for node in graph['nodes']:
            self.assertRegex(node['id'], r'^n[0-9]+$')
        checks = [node for node in graph['nodes'] if node['kind'] == 'verification']
        self.assertTrue(all(node['provenance'] == 'planned' for node in checks))

    def test_agents_only_resolve_explicit_metadata_with_assignment_provenance(self):
        self.assertTrue(hasattr(render_report, 'build_graph'), 'pure graph builder required')
        self.plan['agents'] = [{'id': 'worker', 'label': 'Builder'}]
        self.plan['tasks'][0]['agent_id'] = 'worker'
        graph = render_report.build_graph(self.plan, self.state)
        self.assertEqual(len([n for n in graph['nodes'] if n['kind'] == 'agent']), 1)
        edge = next(e for e in graph['edges'] if e['kind'] == 'assignment')
        self.assertEqual(edge['provenance'], 'planned')
        self.state['tasks']['build'].update(agent_id='worker', agent_source='coordinator record')
        graph = render_report.build_graph(self.plan, self.state)
        edge = next(e for e in graph['edges'] if e['kind'] == 'assignment')
        self.assertEqual(edge['provenance'], 'recorded')
        self.plan['tasks'][0]['agent_id'] = 'unknown'
        self.state['tasks']['build']['agent_id'] = 'unknown'
        graph = render_report.build_graph(self.plan, self.state)
        self.assertFalse(any(e['kind'] == 'assignment' for e in graph['edges']))

    def test_rework_requires_recorded_failed_attempt_and_restart(self):
        self.assertTrue(hasattr(render_report, 'build_graph'), 'pure graph builder required')
        self.state['history'] = [{'action': 'invalidate', 'previous_tasks': {
            'build': {'status': 'failed', 'attempts': 1}}}]
        graph = render_report.build_graph(self.plan, self.state)
        self.assertFalse(any(edge['kind'] == 'rework' for edge in graph['edges']))
        self.state['history'][0]['action'] = 'start'
        graph = render_report.build_graph(self.plan, self.state)
        edges = [edge for edge in graph['edges'] if edge['kind'] == 'rework']
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['provenance'], 'recorded')

    def test_layouts_are_deterministic_nonoverlapping_and_mobile_width_fixed(self):
        self.assertTrue(hasattr(render_report, 'layout_graph'), 'pure layout required')
        graph = render_report.build_graph(self.plan, self.state)
        for mobile in (False, True):
            layout = render_report.layout_graph(graph, mobile=mobile)
            self.assertEqual(layout, render_report.layout_graph(graph, mobile=mobile))
            if mobile:
                self.assertEqual(layout['width'], 360)
            boxes = list(layout['positions'].values())
            for i, a in enumerate(boxes):
                for b in boxes[i + 1:]:
                    self.assertTrue(a['x'] + a['width'] <= b['x'] or
                                    b['x'] + b['width'] <= a['x'] or
                                    a['y'] + a['height'] <= b['y'] or
                                    b['y'] + b['height'] <= a['y'])

    def test_report_leads_with_responsive_accessible_graph_and_collapses_details(self):
        result = self.run_report()
        self.assertEqual(result.returncode, 0, result.stderr)
        html = self.output.read_text()
        self.assertIn('class="graph-desktop"', html)
        self.assertIn('class="graph-mobile"', html)
        self.assertIn('role="img"', html)
        self.assertIn('<details', html)
        self.assertIn('에이전트 기록 없음', html)
        self.assertLess(html.index('<svg'), html.index('<details'))
        self.assertNotIn('<details open', html)

    def test_graph_relations_have_full_accessible_text_and_safe_svg_attributes(self):
        self.plan['agents'] = [{'id': '\"><script>bad()</script>', 'label': '긴 에이전트 이름 전체 보존 <script>x</script>'}]
        self.plan['tasks'][0]['agent_id'] = self.plan['agents'][0]['id']
        html = render_report.render(self.plan, self.state, [], b'')
        self.assertIn('그래프 관계', html)
        self.assertIn('긴 에이전트 이름 전체 보존 &lt;script&gt;x', html)
        self.assertIn('edge assignment planned', html)
        parser = Tags()
        parser.feed(html)
        self.assertNotIn('script', parser.tags)
        for key, value in parser.attrs:
            self.assertFalse(key.startswith('on') or key in {'href', 'xlink:href', 'src'})
            if key == 'id':
                self.assertRegex(value, r'^((desktop|mobile)-(n[0-9]+|title|desc|arrow|retry|surface-(task|verification|decision|agent))|graph-(motion|canvas))$')
            if key == 'marker-end':
                self.assertRegex(value, r'^url\(#(desktop|mobile)-(arrow|retry)\)$')
            if key == 'fill' and value.startswith('url('):
                self.assertRegex(value, r'^url\(#(desktop|mobile)-surface-(task|verification|decision|agent)\)$')
        self.state['tasks']['build'].update(agent_id=self.plan['agents'][0]['id'], agent_source='record')
        html = render_report.render(self.plan, self.state, [], b'')
        self.assertIn('edge assignment recorded', html)

    def test_stale_and_ambiguous_evidence_never_looks_like_current_pass(self):
        self.state['tasks']['stale']['evidence'] = [{'check_id': 'unit', 'result': 'passed'}]
        graph = render_report.build_graph(self.plan, self.state)
        stale = next(n for n in graph['nodes'] if n['reference'] == 'stale:unit')
        self.assertEqual(stale['status'], 'stale')
        self.state['tasks']['build']['evidence'] = [
            {'check_id': 'unit', 'result': 'passed'}, {'check_id': 'unit', 'result': 'failed'}]
        graph = render_report.build_graph(self.plan, self.state)
        mixed = next(n for n in graph['nodes'] if n['reference'] == 'build:unit')
        self.assertEqual(mixed['status'], 'mixed')

    def test_long_desktop_edges_use_outside_routes(self):
        graph = render_report.build_graph(self.plan, self.state)
        svg = render_report.render_graph(graph, lambda value: str(value))
        # The decision gate skips an intermediate task/check layer.
        parser = Tags()
        parser.feed(svg)
        paths = [value for key, value in parser.attrs if key == 'd' and value.startswith('M236,')]
        self.assertTrue(any(' L' in path for path in paths), paths)

    def test_long_gate_status_uses_short_readable_label(self):
        self.state['decisions']['review']['outcome'] = 'revision_requested'
        graph = render_report.build_graph(self.plan, self.state)
        svg = render_report.render_graph(graph, lambda value: str(value))
        ns = {'s': 'http://www.w3.org/2000/svg'}
        labels = ET.fromstring(svg).findall('.//s:text[@class="status"]', ns)
        self.assertIn('수정 요청', [label.text for label in labels])
        self.assertIn('revision_requested', svg)

    def test_desktop_svg_preserves_layout_scale_in_overflow_container(self):
        graph = render_report.build_graph(self.plan, self.state)
        width = render_report.layout_graph(graph)['width']
        svg = render_report.render_graph(graph, lambda value: str(value))
        self.assertIn('style="width:' + str(width) + 'px"', svg)
        mobile = render_report.render_graph(graph, lambda value: str(value), mobile=True)
        self.assertNotIn('style="width:', mobile)

    def test_layered_directional_light_uses_only_existing_relation_paths(self):
        # A missing beam/packet or an invented visual relation breaks the
        # presentation contract, independently of animation timing choices.
        self.state['history'] = [{'action': 'start', 'previous_tasks': {
            'build': {'status': 'failed', 'attempts': 1}}}]
        graph = render_report.build_graph(self.plan, self.state)
        ns = {'s': 'http://www.w3.org/2000/svg'}
        for mobile in (False, True):
            svg = ET.fromstring(render_report.render_graph(graph, str, mobile))
            base = svg.findall('s:path', ns)
            overlay = svg.find('s:g[@class="flow-overlay"]', ns)
            bundles = overlay.findall('s:g', ns)
            self.assertEqual(len(bundles), 8)
            for bundle, edge in zip(bundles, base):
                self.assertEqual(bundle.attrib['data-source'], edge.attrib['data-source'])
                self.assertEqual(bundle.attrib['data-target'], edge.attrib['data-target'])
                self.assertEqual({p.attrib['class'] for p in bundle},
                                 {'flow-beam', 'flow-packet', 'flow-trace'})
                for path in bundle:
                    self.assertEqual(path.attrib['d'], edge.attrib['d'])
                    self.assertEqual(path.attrib['pathLength'], '1000')
                    self.assertNotIn('marker-end', path.attrib)
                    self.assertEqual(len(path), 0)
            self.assertIn('rework', bundles[-1].attrib['class'].split())

    def test_keyboard_spotlight_targets_only_the_selected_neighborhood(self):
        # Incorrect neighbor selectors would visually assert false adjacency.
        graph = render_report.build_graph(self.plan, self.state)
        ns = {'s': 'http://www.w3.org/2000/svg'}
        for mobile in (False, True):
            prefix = 'mobile' if mobile else 'desktop'
            svg = ET.fromstring(render_report.render_graph(graph, str, mobile))
            self.assertEqual(svg.attrib['role'], 'group')
            nodes = svg.findall('s:g[@tabindex="0"]', ns)
            self.assertEqual(len(nodes), 11)
            for node in nodes:
                self.assertEqual(node.attrib['role'], 'img')
                self.assertIn('aria-label', node.attrib)
                self.assertRegex(node.attrib['aria-label'], r'^(작업|검증|결정) · ')
                self.assertIsNotNone(node.find('.//*[@class="focus-ring"]'))
            css = ''.join(el.text or '' for el in svg.findall('s:style', ns))
            # n1 (build) touches n2 (its check), not n3 (downstream task).
            rule = re.search(r'[^{}]*:has\(#' + prefix +
                             r'-n1:focus-visible\)[^{]*\{[^}]*\}', css)
            self.assertIsNotNone(rule, 'keyboard/pointer spotlight rules required')
            self.assertIn(':not(:has(.node:focus-visible)):has(#' + prefix + '-n1:hover)', rule[0],
                          'keyboard focus must take priority over a stationary pointer')
            self.assertIn('#' + prefix + '-n1', rule[0])
            self.assertIn('#' + prefix + '-n2', rule[0])
            self.assertNotIn('#' + prefix + '-n3', rule[0])
            for path in svg.findall('s:path', ns):
                for attribute in ('data-source', 'data-target'):
                    self.assertRegex(path.attrib[attribute], r'^n\d+$')

    def test_spotlight_does_not_dim_record_labels_or_base_relationships(self):
        # Spotlight may mute surfaces and ornament, but not make actual states
        # or declared relationships unreadable while keyboard focus moves.
        graph = render_report.build_graph(self.plan, self.state)
        svg = ET.fromstring(render_report.render_graph(graph, str))
        ns = {'s': 'http://www.w3.org/2000/svg'}
        css = '\n'.join(el.text or '' for el in svg.findall('s:style', ns))
        for rule in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
            if re.search(r'(?<![-\w])(?:\.node|\.edge)\s*$', rule[1]):
                self.assertNotRegex(rule[2], r'(?<![-\w])opacity:\s*\.[0-9]',
                                    'do not fade whole semantic nodes or edges')
        self.assertRegex(css, r':has\([^{}]+\.node-body\{fill-opacity:')

    def test_static_svg_fallback_does_not_require_modern_css_for_readability(self):
        # Unsupported modern selector/custom-property parsers must not discard
        # the only style block that makes semantic SVG content readable.
        graph = render_report.build_graph(self.plan, self.state)
        svg = ET.fromstring(render_report.render_graph(graph, str))
        ns = {'s': 'http://www.w3.org/2000/svg'}
        styles = svg.findall('s:style', ns)
        self.assertGreaterEqual(len(styles), 3)
        baseline = styles[0].text
        self.assertNotRegex(baseline, r'var\(|--[a-z]|:has\(|:is\(|@supports|@keyframes')
        self.assertRegex(baseline, r'\.edge\{[^}]*fill:none')
        self.assertRegex(baseline, r'\.node text\{[^}]*text-anchor:middle')
        self.assertNotRegex(baseline, r'\.node text\{[^}]*fill:',
                            'generic CSS must not override per-status presentation colors')
        self.assertRegex(baseline, r'\.flow-overlay\{[^}]*display:none')
        self.assertRegex(baseline, r'\.node-halo\{[^}]*display:none')
        for edge in svg.findall('s:path', ns):
            self.assertEqual(edge.attrib.get('fill'), 'none')
        for label in svg.findall('.//s:text', ns):
            self.assertRegex(label.attrib.get('fill', ''), r'^#[0-9a-f]{6}$')

    def test_dense_graph_caps_decorative_effects_but_preserves_all_facts(self):
        # Density must not produce unbounded animations or remove real records.
        graph = {'nodes': [dict(id='n' + str(i), kind='task', label=str(i),
                               status='pending', provenance='recorded', reference=str(i))
                           for i in range(80)],
                 'edges': [dict(source='n' + str(i), target='n' + str(i + 1),
                                kind='dependency', provenance='planned') for i in range(79)]}
        graph['edges'].append(dict(source='n79', target='n79', kind='rework', provenance='recorded'))
        before = json.dumps(graph, sort_keys=True)
        ns = {'s': 'http://www.w3.org/2000/svg'}
        for mobile in (False, True):
            svg = ET.fromstring(render_report.render_graph(graph, str, mobile))
            self.assertEqual(len(svg.findall('s:path', ns)), 80)
            self.assertEqual(len(svg.findall('s:g[@tabindex="0"]', ns)), 80)
            bundles = svg.findall('s:g[@class="flow-overlay"]/s:g', ns)
            self.assertGreater(len(bundles), 0)
            self.assertLessEqual(len(bundles), 24)
            self.assertTrue(any('rework' in b.attrib['class'].split() for b in bundles))
            accents = svg.findall('.//*[@class="node-halo"]')
            self.assertGreater(len(accents), 0)
            self.assertLessEqual(len(accents), 24)
        self.assertEqual(json.dumps(graph, sort_keys=True), before)

    def test_every_type_has_a_fixed_surface_and_a_decorative_status_outline(self):
        self.plan['agents'] = [{'id': 'worker', 'label': 'Builder'}]
        graph = render_report.build_graph(self.plan, self.state)
        ns = {'s': 'http://www.w3.org/2000/svg'}
        svg = ET.fromstring(render_report.render_graph(graph, str))
        shapes = {'task': 'rect', 'verification': 'polygon', 'decision': 'polygon', 'agent': 'ellipse'}
        nodes = svg.findall('s:g[@tabindex="0"]', ns)
        self.assertEqual(len(nodes), 12)
        for node in nodes:
            kind = node.attrib['class'].split()[1]
            body = node.find('.//*[@class="node-body"]')
            self.assertEqual(body.tag, '{' + ns['s'] + '}' + shapes[kind])
            self.assertEqual(body.attrib['fill'], 'url(#desktop-surface-' + kind + ')')
            accent = node.find('.//*[@class="node-halo"]')
            self.assertEqual(accent.attrib['aria-hidden'], 'true')
            self.assertEqual(accent.attrib['focusable'], 'false')
            self.assertEqual(len(node.findall('.//s:text', ns)), 3)

    def test_motion_overlay_follows_existing_edges_without_duplicate_relationships(self):
        # Removing the decorative layer, fabricating a retry, or treating a
        # highlight as another semantic edge must fail this contract.
        self.state['history'] = [{'action': 'start', 'previous_tasks': {
            'build': {'status': 'failed', 'attempts': 1}}}]
        graph = render_report.build_graph(self.plan, self.state)
        before = json.dumps(graph, sort_keys=True)
        ns = {'s': 'http://www.w3.org/2000/svg'}
        for mobile in (False, True):
            svg = ET.fromstring(render_report.render_graph(graph, str, mobile=mobile))
            base = svg.findall('s:path', ns)
            self.assertEqual(len(base), 8)
            self.assertEqual([p.attrib['class'] for p in base], [
                'edge verification planned', 'edge verification planned',
                'edge verification planned', 'edge verification planned',
                'edge verification planned', 'edge dependency planned',
                'edge gate planned', 'edge rework recorded'])
            overlay = svg.find('s:g[@class="flow-overlay"]', ns)
            self.assertIsNotNone(overlay, 'decorative flow layer is missing')
            self.assertEqual(overlay.attrib['aria-hidden'], 'true')
            self.assertEqual(overlay.attrib['focusable'], 'false')
            bundles = list(overlay)
            highlights = [bundle.find('s:path[@class="flow-trace"]', ns) for bundle in bundles]
            self.assertEqual([p.attrib['d'] for p in highlights], [p.attrib['d'] for p in base])
            for path in highlights:
                self.assertNotIn('edge', path.attrib['class'].split())
                self.assertNotIn('id', path.attrib)
                self.assertNotIn('marker-end', path.attrib)
                self.assertEqual(len(path), 0, 'decorative paths must not duplicate accessible titles')
            self.assertIn('rework', bundles[-1].attrib['class'])
            self.assertIn('recorded', bundles[-1].attrib['class'])
        self.assertEqual(json.dumps(graph, sort_keys=True), before)

    def test_node_entrance_is_staggered_without_changing_recorded_status(self):
        graph = render_report.build_graph(self.plan, self.state)
        ns = {'s': 'http://www.w3.org/2000/svg'}
        for mobile in (False, True):
            svg = ET.fromstring(render_report.render_graph(graph, str, mobile=mobile))
            nodes = [item for item in svg.findall('s:g', ns)
                     if 'node' in item.attrib.get('class', '').split()]
            self.assertEqual(len(nodes), 11)
            expected = ['rejected', 'pending', 'unknown', 'blocked', 'unknown',
                        'stale', 'unknown', 'cancelled', 'unknown', 'failed', 'unknown']
            delays = []
            for node, state in zip(nodes, expected):
                self.assertIn('state-' + state, node.attrib['class'].split())
                content = node.find('s:g[@class="node-content"]', ns)
                self.assertIsNotNone(content, 'entrance must not replace the stable layout transform')
                delay = re.fullmatch(r'--enter-delay:(\d+)ms', content.attrib['style'])
                self.assertIsNotNone(delay)
                delays.append(int(delay[1]))
                self.assertIsNotNone(node.find('s:title', ns))
                self.assertIn('translate(', node.attrib['transform'])
            self.assertGreater(len(set(delays)), 1)
            self.assertLessEqual(max(delays), 1000, 'large graphs must remain promptly readable')
            # Dependency target enters after its source; no fake status changes.
            self.assertGreater(delays[3], delays[2])

    def test_motion_switch_is_accessible_and_cannot_control_execution(self):
        before = self.snapshot()
        result = self.run_report()
        self.assertEqual(result.returncode, 0, result.stderr)
        html = self.output.read_text()
        parser = Tags()
        parser.feed(html)
        inputs = [attrs for tag, attrs in parser.elements if tag == 'input']
        self.assertEqual(len(inputs), 1)
        control = inputs[0]
        self.assertEqual(control['type'], 'checkbox')
        self.assertIn('checked', control)
        self.assertNotIn('name', control)
        self.assertNotIn('form', control)
        self.assertTrue(any(tag == 'label' and attrs.get('for') == control['id']
                            for tag, attrs in parser.elements))
        self.assertTrue(any(attrs.get('id') == control['aria-controls'] and
                            attrs.get('class') == 'graph-shell' for _, attrs in parser.elements))
        self.assertIn('기록 시각화 · 연출 모션', html)
        self.assertRegex(html, r':focus-visible\s*\{[^}]*outline:')
        self.assertIn("default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'", html)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.root / 'SHOULD_NOT_RUN').exists())

    def test_motion_off_and_reduced_motion_reveal_all_records_without_overlays(self):
        html = render_report.render(self.plan, self.state, [], b'')
        # These are output CSS contracts, not a claim of browser or AT testing.
        # Complete disabling, rather than pausing mid-entrance, keeps text visible.
        media = re.search(r'@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{(.*?)\n\}', html, re.S)
        self.assertIsNotNone(media, 'system reduced-motion preference must be honored')
        for css, prefix in ((html, r'#graph-motion:not\(:checked\)\s*~\s*'),
                            (media[1], '')):
            self.assertRegex(css, prefix + r'\.graph-shell \*\s*\{[^}]*animation:none!important')
            self.assertRegex(css, prefix + r'\.graph-shell \*\s*\{[^}]*transition:none!important')
            self.assertRegex(css, prefix + r'\.graph-shell \.node-content\s*\{[^}]*opacity:1[^}]*transform:none')
            self.assertRegex(css, prefix + r'\.graph-shell \.flow-overlay\s*\{[^}]*display:none')
            self.assertRegex(css, prefix + r'\.graph-shell \.node-halo\s*\{[^}]*display:none')
        self.assertIn('@keyframes graph-enter', html)
        self.assertIn('@keyframes graph-flow', html)
        entrance = re.search(r'(?:^|\n)\.node-content\s*\{([^}]*animation:[^}]*)\}', html)
        self.assertIsNotNone(entrance)
        self.assertIn('graph-enter', entrance[1])
        self.assertNotIn('infinite', entrance[1], 'record labels must not move indefinitely')
        # Stable semantic paths are never animated or hidden by the motion style.
        for rule in re.finditer(r'([^{}]+)\{([^{}]*)\}', html):
            if re.search(r'(?<![-\w])\.edge\b', rule[1]):
                self.assertNotRegex(rule[2], r'animation:|transition:|opacity:0|display:none')

    def test_hostile_status_cannot_inject_motion_classes_or_svg_references(self):
        self.plan['agents'] = [{'id': 'evil\" id=\"graph-motion', 'label': '<script>evil</script>'}]
        self.state['tasks']['build']['status'] = '\" style=\"animation:evil 1s infinite'
        graph = render_report.build_graph(self.plan, self.state)
        html = render_report.render_graph(graph, render_report.escape)
        parser = Tags()
        parser.feed(html)
        ids = [value for key, value in parser.attrs if key == 'id']
        self.assertEqual(len(ids), len(set(ids)))
        for value in ids:
            self.assertRegex(value, r'^desktop-(n[0-9]+|title|desc|arrow|retry|surface-(task|verification|decision|agent))$')
        for tag, attrs in parser.elements:
            if 'node' in attrs.get('class', '').split():
                self.assertRegex(attrs['class'], r'^node (task|verification|decision|agent) (planned|recorded) state-[a-z_]+$')
            self.assertNotIn('evil', attrs.get('style', ''))
        self.assertNotIn('script', parser.tags)
        self.assertIn('&lt;script&gt;evil&lt;/script&gt;', html)
        self.assertIn('state-unknown', html)

    def test_rejects_overwrite_inside_workspace_and_symlinks(self):
        self.output.write_text('KEEP', encoding='utf-8')
        link = self.root / 'link.html'
        link.symlink_to(self.output)
        alias = self.root / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        before = self.snapshot()
        for target in (self.output, link, self.workspace / 'new.html', alias / 'new.html'):
            with self.subTest(target=target):
                result = self.run_report(target)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('error:', result.stderr)
                self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(self.output.read_text(), 'KEEP')
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.root / 'new.html').exists())

    def test_invalid_integrity_produces_no_report(self):
        self.state['plan_sha256'] = 'invalid'
        self.save()
        before = self.snapshot()
        result = self.run_report()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())
        self.assertEqual(before, self.snapshot())

    def test_controller_state_history_is_visible_without_archived_raw_records(self):
        self.state['history'] = [{'action': 'invalidate', 'timestamp': '2026-11-10T10:00:00Z',
                                 'task': 'build', 'reason': '요구사항 변경',
                                 'previous_tasks': {'build': {'raw': 'SECRET_ARCHIVE'}}}]
        self.save()
        result = self.run_report()
        self.assertEqual(result.returncode, 0, result.stderr)
        html = self.output.read_text(encoding='utf-8')
        for expected in ('invalidate', '2026-11-10T10:00:00Z', '요구사항 변경'):
            self.assertIn(expected, html)
        self.assertNotIn('SECRET_ARCHIVE', html)

    def test_tampered_archived_evidence_rejects_report_without_mutating_source(self):
        log = self.workspace / 'evidence' / 'attempt-1.log'
        log.write_bytes(b'original failure evidence')
        record = {'check_id': 'unit', 'result': 'failed', 'path': 'evidence/attempt-1.log',
                  'sha256': hashlib.sha256(log.read_bytes()).hexdigest(), 'artifact_version': 'r1'}
        self.state['history'] = [{'action': 'start', 'timestamp': '2026-11-10T10:00:00Z',
            'previous_tasks': {'build': {'status': 'failed', 'attempts': 1, 'evidence': [record]}}}]
        current = self.workspace / 'evidence' / 'attempt-2.log'
        current.write_bytes(b'current pass evidence')
        self.state['tasks']['build'].update(status='passed', attempts=2, verified_revision='r2',
            evidence=[{'check_id': 'unit', 'result': 'passed', 'path': 'evidence/attempt-2.log',
                       'sha256': hashlib.sha256(current.read_bytes()).hexdigest(), 'artifact_version': 'r2'}])
        self.save()
        result = self.run_report(self.root / 'before.html')
        self.assertEqual(result.returncode, 0, result.stderr)
        log.write_bytes(b'TAMPERED_SECRET_HISTORY')
        before = self.snapshot()
        result = self.run_report()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('digest mismatch', result.stderr)
        self.assertNotIn('TAMPERED_SECRET_HISTORY', result.stderr)
        self.assertFalse(self.output.exists())
        self.assertEqual(before, self.snapshot())

    def test_malformed_histories_fail_cleanly_without_disclosing_raw_text(self):
        for state_history, jsonl in [('SECRET_BAD_STATE_HISTORY', ''),
                                     ([{'reason': 'SECRET_MISSING_ACTION'}], ''),
                                     ([], 'SECRET_INVALID_HISTORY\n')]:
            with self.subTest(state_history=state_history):
                self.output.unlink(missing_ok=True)
                self.state['history'] = state_history
                self.save()
                (self.workspace / 'decisions.jsonl').write_text(jsonl, encoding='utf-8')
                before = self.snapshot()
                result = self.run_report()
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr.startswith('error:'), result.stderr)
                self.assertNotIn('SECRET', result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertFalse(self.output.exists())
                self.assertEqual(before, self.snapshot())


if __name__ == '__main__':
    unittest.main()
