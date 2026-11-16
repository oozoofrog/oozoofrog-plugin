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
        (project / 'guide.txt').write_text('사용 설명서\n\n1. 흐름을 열고 지금 하는 일을 살펴보세요.\n2. 파일을 읽고 통과할지 정해 주세요.\n3. 고칠 곳이 있다면 이유를 적어 돌려보내세요.\n', encoding='utf-8')
        git('add', 'guide.txt')
        git('-c', 'user.name=Dashboard demo', '-c', 'user.email=demo@example.invalid',
            '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'Readable demo guide')
        guide_head = git('rev-parse', 'HEAD').decode().strip()
        checks.submit(run, 'guide', guide_head, None, '설치 순서 부분은 자신이 없어요.',
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
        for removed in ('three.module', 'CSS2DRenderer', 'WebGL', 'canvas'):
            self.assertNotIn(removed, html + js)
        self.assertIn('createElementNS', js)
        self.assertFalse((S / 'scripts/graphflow/vendor').exists())

    def test_motion_is_declared_in_css_and_stops_for_reduced_motion(self):
        html = (S / 'scripts/graphflow/page.html').read_text(encoding='utf-8')
        js = (S / 'scripts/graphflow/page.js').read_text(encoding='utf-8')
        style = html[html.index('<style'):html.index('</style>')]
        declared = set(re.findall(r'@keyframes ([a-z]+)', style))
        self.assertEqual(declared, {'step', 'flow', 'arrive'})
        used = {name for rule in re.findall(r'animation:([^;}]+)', style)
                for name in re.findall(r'(?:^|,)([a-z]+) ', rule)}
        self.assertEqual(used, declared)
        reduced = '@media(prefers-reduced-motion:reduce){*,*:before,*:after{transition:none!important;animation:none!important'
        self.assertGreater(style.index(reduced), max(style.rindex('@keyframes'), style.rindex('animation:flow')))
        # The native play mark remains visible when animation is disabled.
        self.assertIn("el('span','▶','walker')", js)
        for used_class in ('working', 'changed', 'flowing', 'walker'):
            self.assertIn("'" + used_class, js.replace("' " + used_class, "'" + used_class))
        self.assertNotIn('frog-walk', js)
        self.assertNotIn('requestAnimationFrame', js)

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

    def run_controller(self, body):
        if not shutil.which('node'):
            self.skipTest('node is not on PATH; dashboard decision behavior tests skipped')
        script = r"""
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source = readFileSync(process.argv[2], 'utf8');
const {createDecisionController, decisionQuestion, purposeWording, purposeAction, viewLanguage, edgeRelationLabel, fitScale, MIN_FIT_SCALE, edgeChipText, cometCount, layeredLayout, crossingCount, displayState, statusGlyph, checkWording, checkTitle, offscreenDirection} = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const first = {project:'/project', run:'first'}, second = {project:'/project', run:'second'};
const decision = {id:'d7', purpose:'lane3', kind:'authorization', failed:[], files:[{name:'Result',path:'result.txt'}]};
const controller = createDecisionController();
const show = (decisions = [decision], run = first) => controller.refresh({decisions}, run);
show();
""" + body
        result = subprocess.run([shutil.which('node'), '--input-type=module', '-',
                                 str(S / 'scripts/graphflow/page.js')], input=script,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_language_attempt_segments_and_record_counts(self):
        self.run_controller(r"""
assert.equal(viewLanguage({language:'ko'}, 'en-US'),'ko');
assert.equal(viewLanguage({language:'en'}, 'ko-KR'),'en');
assert.equal(viewLanguage({}, 'ko-KR'),'en');
assert.equal(viewLanguage(null,'ko-KR'),'ko');
assert.equal(cometCount({laps:['returned','returned','passed'],returned_reasons:[[],[],[]]}),2);
assert.equal(cometCount({laps:[],returned_reasons:[[]]}),0);
""")

    def test_layout_rectangles_depth_reviews_and_fit(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ):
            root=pathlib.Path(directory)
            run=build_demo_run(root/'home',root/'project')
            current,events,derived=server._snapshot(run)
            demo=server._view(current,derived,events,root/'project')
        self.run_controller('const demo = '+json.dumps(demo)+r';'+r"""
const nodes=Array.from({length:12},(_,i)=>({id:'n'+i,kind:'work',title:'Work item '+i,returned_reasons:i===5?[['A required case did not pass']]:[]}));
const edges=[];
for(let i=3;i<12;i++) { const layer=Math.floor(i/3); for(const p of [(i%3),(i+1)%3]) edges.push({from:'n'+((layer-1)*3+p),to:'n'+i,label:'Readable handoff '+i,relation:'hands_over',gate:'closed'}); }
const crossed={nodes:nodes.slice(0,6),edges:[{from:'n0',to:'n5'},{from:'n1',to:'n4'},{from:'n2',to:'n3'}]};
const reviewed={nodes:[{id:'work',kind:'work'},{id:'review',kind:'review',target:'work'},{id:'next',kind:'work'}],edges:[{from:'review',to:'work',relation:'reviews'},{from:'work',to:'review',relation:'hands_over'},{from:'review',to:'next',relation:'hands_over'}]};
const overlap=(a,b)=>a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y;
for(const data of [demo,{nodes,edges},crossed,reviewed]) for(const expanded of [null,data.nodes[0].id,data.nodes.at(-1).id]) {
  const options={expanded,language:'en'}, layout=layeredLayout(data.nodes,data.edges,data.decisions,true,options);
  const depth=id=>{const node=data.nodes.find(n=>n.id===id);return node.kind==='review'?depth(node.target)+1:Math.max(0,...data.edges.filter(e=>e.to===id&&e.relation!=='reviews').map(e=>depth(e.from)+1));};
  for(const node of data.nodes) {
    const p=layout.positions[node.id];assert.equal(p.depth,depth(node.id));
    assert.equal(p.layer,depth(node.id));assert(layout.layers[p.depth].includes(node.id));
  }
  const rects=[...layout.cardRects,...layout.chips];
  rects.forEach((a,i)=>rects.slice(i+1).forEach(b=>assert(!overlap(a,b),'cards and chips must never overlap: '+JSON.stringify([a,b]))));
  // Only one source's identical output may merge into a common trunk.
  const segments=r=>r.points.slice(1).map((p,i)=>[r.points[i],p]);
  for(const [i,r] of layout.routes.entries()) for(const other of layout.routes.slice(i+1)) {
    if(r.bundle===other.bundle)continue;
    for(const [a,b] of segments(r)) for(const [c,d] of segments(other)) {
      if(a.x===b.x && c.x===d.x && a.x===c.x)assert(Math.min(Math.max(a.y,b.y),Math.max(c.y,d.y))-Math.max(Math.min(a.y,b.y),Math.min(c.y,d.y))<=.001,'vertical routes must not merge');
      if(a.y===b.y && c.y===d.y && a.y===c.y)assert(Math.min(Math.max(a.x,b.x),Math.max(c.x,d.x))-Math.max(Math.min(a.x,b.x),Math.min(c.x,d.x))<=.001,'horizontal routes must not merge '+JSON.stringify([r,other]));
    }
  }
  const unsorted=layeredLayout(data.nodes,data.edges,data.decisions,false,options);
  const deps=data.edges.filter(e=>e.relation!=='reviews');
  assert(crossingCount(deps,layout.positions)<=crossingCount(deps,unsorted.positions));
  assert.deepEqual(layout,layeredLayout(data.nodes,data.edges,data.decisions,true,options));
  assert(layout.bounds.width>=Math.max(...Object.values(layout.positions).map(p=>p.x+p.width)));
  for(const [w,h] of [[1680,960],[1280,800],[845,912],[390,844]])assert(fitScale(layout.bounds,w,h,w<760)>=MIN_FIT_SCALE);
}
const layout=layeredLayout(reviewed.nodes,reviewed.edges);
assert.equal(layout.positions.review.layer,layout.positions.work.layer+1);
assert(layout.routes.some(e=>e.from==='work'&&e.to==='review'&&e.relation==='reviews'));
const back=layout.routes.find(e=>e.relation==='reviews'), forward=layout.routes.find(e=>e.from==='work'&&e.relation!=='reviews');
assert.notEqual(back.start.y,forward.start.y,'review and handoff use separate ports');
const measured=layeredLayout([{id:'a',kind:'work'}],[],[],true,{heights:{a:127}});
assert.equal(measured.positions.a.height,127,'ports and spacing use the rendered card height');
assert(layout.order.includes('review'));
assert.equal(fitScale({width:10000,height:10000},300,300),MIN_FIT_SCALE);
// Identical fan-out shares one source port, one label and a visible junction.
const fork=layeredLayout([{id:'a',kind:'work'},{id:'b',kind:'work'},{id:'c',kind:'work'}],[{from:'a',to:'b',label:'Parsed record',relation:'hands_over',gate:'open'},{from:'a',to:'c',label:'Parsed record',relation:'hands_over',gate:'open'}],[],true,{language:'en'});
assert.equal(fork.chips.length,0,'a long label is dropped if it cannot fit its segment');
assert.equal(fork.routes[0].start.y,fork.routes[1].start.y);
assert(fork.routes.every(r=>r.junction));
assert.equal(fork.routes.length,2);
for(const r of fork.routes)assert.equal(r.chip,null);
assert.deepEqual(fork.terminals,['b','c']);
const outputs=layeredLayout(['a','b','c'].map(id=>({id,kind:'work'})),[{from:'a',to:'b',label:'One'},{from:'a',to:'c',label:'Two'}]);
assert.equal(outputs.chips.length,2,'different outputs never share a label');
assert.notEqual(outputs.routes[0].bundle,outputs.routes[1].bundle);
const skips=layeredLayout(['a','b','c','d'].map(id=>({id,kind:'work'})),[{from:'a',to:'b',label:'One'},{from:'b',to:'c',label:'Two'},{from:'a',to:'c',label:'One'},{from:'a',to:'d',label:'One'}]);
assert.equal(skips.chips.filter(c=>skips.routes.find(r=>r.chip===c).from==='a').length,1,'one output retains one label even across layers');
assert(skips.routes.find(r=>r.from==='a'&&r.to==='c').skip);
assert.deepEqual(skips.routes[0].start,skips.routes[2].start,'skip and adjacent branches share a source port');

const tall=layeredLayout(nodes,edges,[],true,{heights:Object.fromEntries(nodes.map(n=>[n.id,150])),maxHeight:440});
for(const p of Object.values(tall.positions))assert(p.y%440+p.height<=416,'page breaks keep whole cards within the initial view');
const down=layeredLayout(reviewed.nodes,reviewed.edges,[],true,{heights:{work:110,review:140,next:120},vertical:true});
assert(down.vertical);assert(down.bounds.width<600,'explicit vertical layout remains supported independently of selection');
for(const r of down.routes) {
  const source=down.positions[r.from],target=down.positions[r.to];
  assert.equal(r.start.y,r.reverse?source.y:source.y+source.height);
  assert.equal(r.end.y,r.reverse?target.y+target.height:target.y);
  for(const p of r.points)for(const c of down.cardRects)assert(!(p.x>c.x&&p.x<c.x+c.width&&p.y>c.y&&p.y<c.y+c.height),'routes never enter a card except at a port');
}

// A line's text has one meaning: the name of what is handed over. Reviews, decisions and unnamed handoffs carry none.
assert.equal(edgeChipText({relation:'hands_over',label:'Parsed record'},'en'),'Parsed record');
for(const edge of [{relation:'hands_over',label:''},{relation:'reviews',label:'x'},{relation:'waits_for_decision',label:'approval'},{relation:'toward_goal',label:''}]) assert.equal(edgeChipText(edge),'');
const review=layeredLayout([{id:'a',kind:'work'},{id:'r',kind:'review',target:'a'}],[{from:'r',to:'a',label:'',relation:'reviews',gate:'closed'}],[{id:'d1',node:'a'}]);
assert.equal(review.chips.length,0,'a review line and a waiting decision add no label');
// A graph too wide for the map keeps its words readable and scrolls instead of shrinking past the minimum.
const chain=layeredLayout(['a','b','c','d'].map(id=>({id,kind:'work'})),[['a','b'],['b','c'],['c','d']].map(([from,to])=>({from,to,relation:'hands_over'})),[],true,{language:'ko'});
assert.equal(fitScale(chain.bounds,860,2000),MIN_FIT_SCALE); assert.equal(MIN_FIT_SCALE*14,13);
assert(chain.bounds.width*MIN_FIT_SCALE>860);
""")

    def test_offscreen_cards_have_one_direction_and_fit_uses_both_dimensions(self):
        self.run_controller(r"""
const cases=[
 [{x:-30,y:-5,width:100,height:100},'offTop'],
 [{x:320,y:40,width:100,height:100},'offRight'],
 [{x:-150,y:300,width:100,height:100},'offBottom'],
 [{x:20,y:20,width:100,height:100},null],
];
for(const [rect,expected] of cases)assert.equal(offscreenDirection(rect,300,300),expected);
const counts={}; for(const [rect] of cases){const direction=offscreenDirection(rect,300,300);if(direction)counts[direction]=(counts[direction]||0)+1;}
assert.equal(Object.values(counts).reduce((a,b)=>a+b,0),3);
assert.equal(fitScale({width:900,height:400},855,500),.95);
assert.equal(fitScale({width:900,height:400},855,500,true),.95);
""")

    def test_relation_labels_and_loop_states(self):
        self.run_controller(r"""
for(const [lang,labels] of [['ko',['넘겨줌','검토를 맡겼어요','결정을 기다림']],['en',['hands over','reviewed by','waits for a decision']]]) {
  ['hands_over','reviews','waits_for_decision'].forEach((relation,i)=>assert.equal(edgeRelationLabel({relation,label:''},lang),labels[i]));
  assert.equal(edgeRelationLabel({relation:'hands_over',label:'Readable result'},lang),labels[0]+': Readable result');
}
""")

    def test_displayed_states_and_failed_expectations(self):
        self.run_controller(r"""
const states=['passed','running','retrying','awaiting','notStarted','exhausted','submitted','held','returned'];
assert.equal(new Set(states.map(statusGlyph)).size,states.length,'each state has a distinct stable shape');
for(const status of ['running','submitted','awaiting_approval','replan']) {
  assert.equal(displayState({id:'work',status,attempts:2},[{node:'work'}]),'awaiting');
}
assert.equal(displayState({id:'work',status:'running',attempts:2},[]),'retrying');
for(const language of ['en','ko']) {
  const failed=checkWording({id:'screen',title:'A screen exists',result:'failed'},language);
  assert(failed.startsWith('✕'));assert(failed.includes('“A screen exists”'));
  assert(checkWording({id:'screen',title:'A screen exists',result:'passed'},language).startsWith('✓'));
  assert(checkWording({id:'screen',title:'A screen exists',result:'failed'},language,2).includes('2'));
  assert(!checkTitle({id:'scope',title:'scope'},language).includes('scope'));
}
""")

    def test_controller_bound_request(self):
        self.run_controller(r"""
let chosen = {...first};
controller.refresh({decisions:[decision]}, chosen);
const session = controller.open('d7');
assert(Object.isFrozen(session.target));
controller.openDetails();
chosen.run = second.run;
const request = controller.buildRequest('approved', '  Read it  ');
assert.deepEqual(request, {...first, id:'d7', outcome:'approved', answer:'Read it'}, 'POST must use the bound target');
assert.equal(session.busy, true);
assert.equal(controller.buildRequest('approved', ''), null, 'double sends must be refused');
assert.equal(controller.close(), false, 'a pending POST must keep the view open');
assert.equal(show([], second), '', 'a pending POST suspends view-closing');
assert.equal(controller.session, session);
assert.equal(controller.open('different'), null);
const result = controller.onResult(request);
assert.deepEqual(result, {notice:'answered', close:true, refresh:false}, 'always report the real result, without refreshing a different run');
assert.equal(controller.session, null);
""")

    def test_controller_details_gate(self):
        self.run_controller(r"""
for (const changes of [
  {}, {purpose:'authorization'}, {purpose:'future-purpose'},
  {purpose:'hold',kind:'review'},
  {purpose:'human_check',kind:'review',failed:['A case did not pass']},
  {purpose:'trajectory',kind:'review',failed:['A reviewer found a problem']}
]) {
  const d = {...decision, ...changes}; show([d]); controller.open(d.id);
  assert.equal(controller.canSubmit('approved', ''), false, 'affirmative button must be disabled until details open');
  assert.equal(controller.buildRequest('approved', ''), null, 'sending must enforce the same details gate');
  assert.equal(controller.canSubmit('revision_requested', ''), false);
  assert.equal(controller.canSubmit('revision_requested', 'Please fix this'), true);
  controller.openFile();
  assert.equal(controller.canSubmit('approved', ''), !(d.failed.length || d.purpose==='hold'), 'files cannot unlock failed or held work');
  controller.openDetails(); assert.equal(controller.canSubmit('approved', ''), true);
  const request = controller.buildRequest('approved', ''); assert(request);
  controller.onResult(request);
}
show([{...decision,purpose:'human_check',kind:'review'}]); controller.open('d7');
assert.equal(controller.canSubmit('approved', ''), false);
controller.openFile();assert.equal(controller.canSubmit('approved', ''), true);
controller.close();
show([{...decision,kind:'direction'}]); controller.open('d7');
assert.equal(controller.canSubmit('approved', 'text'), false);
assert.equal(controller.buildRequest('answered', '  '), null);
assert.equal(controller.canSubmit('answered', 'This way'), true);
""")

    def test_controller_sessions_are_per_decision(self):
        self.run_controller(r"""
const another = {...decision,id:'d8'}; show([decision,another]);
const old = controller.open('d7'); controller.setDraft('첫 답'); controller.openDetails();
assert.equal(controller.canSubmit('approved', ''), true);
const fresh = controller.open('d8');
assert.notEqual(fresh, old, 'opening another id must create a new session');
assert.equal(fresh.draft, ''); assert.equal(fresh.detailsOpened, false);
assert.equal(controller.canSubmit('approved', ''), false, 'details for one decision must not unlock another');
controller.setDraft('새 답'); show([decision,another]);
assert.equal(controller.open('d8'), fresh, 'ordinary refresh must preserve the session and draft');
assert.equal(fresh.draft, '새 답');
assert.equal(show([decision]), 'decisionClosed'); assert.equal(controller.session, null);
controller.open('d7'); controller.setDraft('draft');
assert.equal(show([decision],second), 'runChanged'); assert.equal(controller.session,null);
assert.equal(controller.open('d7').draft, '');
""")

    def test_controller_reports_late_results_and_errors(self):
        self.run_controller(r"""
controller.open('d7'); controller.openDetails();
const request = controller.buildRequest('approved', '');
assert.deepEqual(controller.onResult(request, {status:503}), {notice:'answerFailed', close:false, refresh:true});
assert.equal(controller.session.busy, false);
controller.close(); show([decision],second); const other = controller.open('d7');
assert.deepEqual(controller.onResult(request), {notice:'answered', close:false, refresh:false}, 'a result after closure must still be reported');
assert.equal(controller.session, other, 'late results cannot close another run');
controller.openDetails(); const newer = controller.buildRequest('approved', '');
assert.equal(controller.onResult(request).close, false, 'a repeated callback cannot settle a newer request');
assert.equal(other.busy,true);
assert.equal(controller.onResult(newer,{status:409}).notice,'stale');
assert.equal(controller.session,null);
""")

    def test_decision_wording_and_exact_generated_question(self):
        self.run_controller(r"""
for (const language of ['ko','en']) {
  const meanings = ['human_check','lane3','trajectory','hold','direction','information'].map(p => purposeWording(p, language));
  assert.equal(new Set(meanings).size, meanings.length);
  assert.equal(purposeWording('authorization', language), purposeWording('lane3', language));
  assert.equal(purposeWording('review', language), purposeWording('human_check', language));
  for (const purpose of ['future-purpose','node','free',undefined,'toString','__proto__']) {
    assert.equal(typeof purposeWording(purpose, language), 'string');
    assert(!/approv|통과|승인|허락/i.test(purposeWording(purpose, language)));
    assert(!/approv|통과|승인|허락/i.test(purposeAction(purpose, language)));
  }
  assert.equal(purposeAction('hold',language), language === 'ko' ? '그래도 받아들이기' : 'Accept anyway');
  assert.equal(purposeAction('human_check',language,['A failure']), purposeAction('hold',language));
}
assert.equal(decisionQuestion({purpose:'lane3',node:'build',question:'Approve lane3 for build?'}),'');
assert.equal(decisionQuestion({purpose:'review',record_purpose:'free',node:'build',question:'Approve free for build?'}),'Approve free for build?');
assert.equal(decisionQuestion({purpose:'direction',record_purpose:'node',node:'pick',question:'Approve node for pick?'}),'Approve node for pick?');
for (const question of ['Approve deploy for prod?','Approve hold for another?','Approve lane3 for build? ']) {
  assert.equal(decisionQuestion({purpose:'lane3',node:'build',question}),question);
}
""")

    def test_dom_uses_controller_and_preserves_composing_input_on_refresh(self):
        self.run_controller(r"""
class Element {
  constructor(tag) { this.tagName=tag; this.children=[]; this.dataset={}; this.listeners={}; this.hidden=false; this.disabled=false; this.value=''; this._text=''; this.style={}; this.classList={add:name=>{this.className=((this.className||'')+' '+name).trim();},toggle:(name,on)=>{const classes=new Set((this.className||'').split(' ').filter(Boolean));if(on??!classes.has(name))classes.add(name);else classes.delete(name);this.className=[...classes].join(' ');return classes.has(name);}}; }
  prepend(...children) { for(const c of children){if(c.parent)c.remove();c.parent=this;} this.children.unshift(...children); }
  remove() { if(this.parent)this.parent.children=this.parent.children.filter(c=>c!==this); }
  get firstElementChild() { return this.children[0]; }
  append(...children) { for (const c of children) { if(c.parent)c.remove(); c.parent=this; this.children.push(c); } }
  replaceChildren(...children) { for (const c of this.children) { if (c.contains(document.activeElement)) document.activeElement=null; c.parent=null; } this.children=[]; this._text=''; this.append(...children); }
  contains(node) { return this===node || this.children.some(c=>c.contains(node)); }
  set textContent(text) { this.replaceChildren(); this._text=String(text); }
  get textContent() { return this._text + this.children.map(c=>c.textContent).join(' '); }
  setAttribute(key,value) { this[key]=String(value); }
  addEventListener(type,fn) { (this.listeners[type] ||= []).push(fn); }
  dispatchEvent(event) { for (const fn of this.listeners[event.type] || []) fn(event); }
  click() { if (!this.disabled) this.dispatchEvent({type:'click'}); }
  focus() { document.activeElement=this; }
  querySelectorAll(selector) {
    const matches = c => selector==='button[data-outcome]' ? c.tagName==='button' && !!c.dataset.outcome : selector==='[data-i18n]' ? false : c.tagName===selector || selector===`#${c.id}`;
    return this.children.flatMap(c=>[...(matches(c)?[c]:[]),...c.querySelectorAll(selector)]);
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}
const body=new Element('body'), root=new Element('html'), docEvents={};
globalThis.document={body,documentElement:root,hidden:false,activeElement:null,
  createElement:tag=>new Element(tag), createElementNS:(_,tag)=>new Element(tag), getElementById:id=>body.querySelector(`#${id}`),
  querySelector:selector=>body.querySelector(selector), querySelectorAll:selector=>body.querySelectorAll(selector),
  addEventListener:(type,fn)=>{docEvents[type]=fn;}};
body.append(new Element('nav'));
for (const id of ['map','notice','picker','picker-label','find','find-text','home','flow','decision','home-tab','flow-tab','where','title','subtitle','node-list','edge-list','decision-list','panel','attention','accessible','phone-flow','phone-view-toggle']) {
  const e=new Element(id==='picker'?'select':'div'); e.id=id; body.append(e);
}
Object.defineProperty(globalThis,'navigator',{value:{language:'ko-KR'},configurable:true});
globalThis.location={href:'http://localhost:5000/?t=demo',port:'5000',hash:'',pathname:'/',search:''};
globalThis.addEventListener=()=>{};
globalThis.history={replaceState(){}}; globalThis.sessionStorage={getItem(){return 'demo'},setItem(){}};
globalThis.ResizeObserver=class { observe(){} };
globalThis.matchMedia=()=>({matches:true,addEventListener(){}});
globalThis.setTimeout=()=>0; globalThis.clearTimeout=()=>{};
const d={...decision,purpose:'hold',kind:'review',node:'work',question:'Approve hold for work?',record_purpose:'hold',
  files:[{name:'guide.md',path:'docs/guide.md'}],context:{},verified:['A verified fact'],unverified:[],worker_note:'Read me',has_evidence:false,failed:['Missing case'],trajectory_reasons:[]};
let live={title:'Flow',language:'en',nodes:[{id:'work',title:'Work',summary:'Summary',status:'submitted',attempts:1,max_attempts:3,laps:[],returned_reasons:[],inputs:[],outputs:[]}],edges:[],decisions:[d],lessons:[],timeline:[{id:'e3',seq:3,ts:'2026-11-15T14:16:37Z',kind:'attempt',by:{role:'worker',session:'t3:0123456789abcdef'},node:'work',node_title:'Work',attempt:1,state:'returned',worker:{model:'m'},checks:[{id:'unit',title:'Unit passes',result:'failed',phase:'gate',command:'run tests',exit_code:1,duration_ms:90,log:'evidence/work/unit/a1.log',violations:[]}],notes:'Tried',files:['a.py'],unsure:[],reason:'check unit exited 1',findings:[]},{id:'e9',seq:9,ts:'2026-11-15T14:20:00Z',kind:'asked',by:{role:'leader',session:null},decision:'d7',node:'work',node_title:'Work',question:'Approve hold for work?'}],counts:{done:0,doing:0,waiting:0,needs_you:1,returned:0},complete:false};
const posts=[]; let resolvePost;
globalThis.fetch=async (path,options)=>{
  if (options.method==='POST') { posts.push(JSON.parse(options.body)); return new Promise(resolve=>{resolvePost=()=>resolve({ok:true,json:async()=>({ok:true})});}); }
  if(path.startsWith('/api/file?')) return {ok:true,text:async()=>'<script>literal Markdown</script>\n# Guide'};
  return {ok:true,json:async()=>path==='/api/projects'?{projects:[{root:first.project,name:'Project',runs:[{id:first.run,status:'open'}]}]}:{plan:{},view:structuredClone(live),state:{decisions:{}}}};
};
const settle=async()=>{ for(let i=0;i<12;i++) await new Promise(setImmediate); };
await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64')+'#dom'); await settle();
const get=id=>document.getElementById(id);
assert.equal(document.documentElement.lang,'en','plan language must override Korean browser');
// The graph opens first, and a waiting decision is answered from its card.
assert.equal(get('flow').hidden,false); assert.equal(get('home').hidden,true);
assert.match(get('map').textContent,/d7 · Read and decide/);
assert.equal(get('panel').hidden,true,'no idle legend occupies the graph');
assert.equal(get('attention').hidden,false);
assert.match(get('attention').textContent,/d7/);
assert.match(get('attention').textContent,/Approve hold for work/);
const before=get('map').querySelectorAll('article'); docEvents.visibilitychange(); await settle();
assert.deepEqual(get('map').querySelectorAll('article'),before,'unchanged polling preserves card elements');
live.decisions.push({...d,id:'d8',node:null,node_title:null,question:'Which language?'});
docEvents.visibilitychange(); await settle();
assert.match(get('attention').textContent,/Which language\?/,'unbound decisions are visible above the graph');
get('attention').querySelectorAll('button').at(-1).click();
assert(get('answer-text'),'unbound decision opens in one click');
get('answer-actions').children.at(-1).click();
live.decisions.pop();
live.decisions.push({...d,id:'d8',node:null,node_title:null,question:'Which language?',kind:'direction',purpose:'direction',failed:[],files:[],verified:[],worker_note:null});
docEvents.visibilitychange();await settle();get('attention').querySelectorAll('button').at(-1).click();
assert.equal(get('decision').querySelectorAll('details').find(e=>e.className==='evidence').hidden,true,'a question without evidence must not advertise an empty disclosure');
get('answer-actions').children.at(-1).click();live.decisions.pop();
const saved=structuredClone(live);
live.decisions[0]={...d,purpose:'human_check',failed:[],files:[],has_evidence:false};live.timeline=[];
docEvents.visibilitychange();await settle();get('decision-list').querySelector('button').click();
const emptyActions=get('answer-actions').children;
assert.equal(emptyActions[0].dataset.outcome,'revision_requested','request evidence first');
assert.equal(emptyActions[1].className,'','acceptance is secondary');
assert.equal(emptyActions[1].disabled,true,'empty acceptance needs explicit confirmation');
assert.match(get('decision').textContent,/There is nothing here to judge by/);
get('blind-confirm').checked=true;get('blind-confirm').dispatchEvent({type:'change'});
assert.equal(emptyActions[1].disabled,false,'explicit confirmation retains the ability to accept');
get('answer-actions').children.at(-1).click();live=saved;docEvents.visibilitychange();await settle();

const originalNode=structuredClone(live.nodes[0]);
live.nodes[0].attempts=2;live.nodes[0].laps=['returned','current'];live.nodes[0].returned_reasons=[['Unit passes']];
docEvents.visibilitychange();await settle();
assert.match(get('map').textContent,/Earlier attempt 1 returned/);
assert.doesNotMatch(get('map').textContent,/✕|Unit passes/,'earlier failure cannot dominate the current card');
assert.match(get('map').textContent,/Your turn/);
live.nodes[0]=originalNode;docEvents.visibilitychange();await settle();

live.nodes.push({id:'choice',kind:'decision',title:'Pick a direction',status:'pending',answered:true,inputs:[],outputs:[],laps:[],returned_reasons:[]});
docEvents.visibilitychange();await settle();
assert.match(get('map').textContent,/Decision · Finished/,'answered decisions use finished words as well as colour');
live.nodes.pop();docEvents.visibilitychange();await settle();
// The other view is the inbox and the record, newest entry first, with the real check of a returned attempt.
get('home-tab').click(); assert.equal(get('home').hidden,false); assert.equal(get('flow').hidden,true);
const entries=get('home').querySelectorAll('li').filter(e=>e.id);
assert.deepEqual(entries.map(e=>e.id),['e9','e3']);
const words=e=>e.textContent;
assert.match(words(entries[1]),/attempt 1 came back/); assert.match(words(entries[1]),/Unit passes/); assert.match(words(entries[1]),/run tests/); assert.match(words(entries[1]),/T3 thread 01234567/);
assert.equal(entries[1].querySelector('details').open,true,'a returned attempt shows its checks without a click');
get('flow-tab').click(); assert.equal(get('flow').hidden,false); assert.equal(get('home').hidden,true);
// Open through the HTML fallback; map and panel route to the same openDecision.
get('decision-list').querySelector('button').click();
assert.match(get('decision').textContent,/attempt 1 came back/);
assert.match(get('decision').textContent,/In attempt 1, “Unit passes” did not pass/);
assert.match(get('decision').textContent,/a.py/);
assert.equal(get('flow-tab')['aria-pressed'],'true','reading retains its parent tab');
const input=get('answer-text'), actions=get('answer-actions'), buttons=[...actions.children];
assert(input, 'fallback must open the decision');
assert.equal(buttons[0].textContent,'Accept anyway'); assert.equal(buttons[0].disabled,true, 'real affirmative button must use controller.canSubmit');
buttons[0].dispatchEvent({type:'click'}); await settle();
assert.equal(posts.length,0,'even a programmatic click must pass through buildRequest');
input.value='고쳐 주세요'; input.dispatchEvent({type:'input'}); input.focus(); input.selectionStart=2; input.selectionEnd=4;
input.dispatchEvent({type:'compositionstart'});
live.title='Updated flow'; live.decisions[0].worker_note='Updated note';
docEvents.visibilitychange(); await settle();
assert.equal(get('title').textContent,'Updated flow', 'refresh must actually apply changed content');
assert.equal(get('answer-text'),input,'refresh must preserve the textarea node');
assert.equal(get('answer-actions'),actions,'refresh must preserve the actions node');
assert.deepEqual(actions.children,buttons,'refresh must preserve every action button');
assert.equal(document.activeElement,input); assert.equal(input.value,'고쳐 주세요');
assert.equal(input.selectionStart,2); assert.equal(input.selectionEnd,4);
input.dispatchEvent({type:'compositionend'});
const fileButton=get('decision').querySelectorAll('button').find(b=>b.textContent==='guide.md');
assert(fileButton);fileButton.click();await settle();
assert.match(get('decision').querySelectorAll('pre').find(p=>!p.hidden).textContent,/<script>literal Markdown<\/script>/);
assert.equal(buttons[0].disabled,true,'a worker-chosen file cannot unlock failed or held work');
get('decision').querySelectorAll('details').find(e=>e.className==='evidence').open=true;
get('decision').querySelectorAll('details').find(e=>e.className==='evidence').dispatchEvent({type:'toggle'});
assert.equal(buttons[0].disabled,false);
buttons[0].click(); await settle();
assert.deepEqual(posts,[{...first,id:'d7',outcome:'approved',answer:'고쳐 주세요'}],'real POST must use the controller request');
assert.equal(get('picker').disabled,true);
live.decisions=[]; docEvents.visibilitychange(); get('flow-tab').click(); await settle();
assert.equal(get('answer-text'),input,'a refresh or navigation must not close a pending POST');
resolvePost(); await settle();
assert.match(get('notice').textContent,/Answer sent/,'real outcome must survive the deferred decision-closing refresh');
assert.equal(get('picker').disabled,false);
assert.equal(get('answer-text'),null);
""")


    def test_no_evidence_confirmation_is_bound_and_not_a_reading_bypass(self):
        self.run_controller(r"""
const empty={...decision,purpose:'human_check',kind:'review',files:[]};
show([empty]);controller.open('d7');
assert.equal(controller.canSubmit('approved',''),false);
assert.equal(controller.buildRequest('approved',''),null);
controller.openDetails();assert.equal(controller.canSubmit('approved',''),false);
controller.confirmBlind(true);assert.equal(controller.canSubmit('approved',''),true);
show([empty]);assert.equal(controller.canSubmit('approved',''),true,'polling preserves confirmation');
controller.close();controller.open('d7');assert.equal(controller.canSubmit('approved',''),false,'reopening resets consent');
show([{...empty,purpose:'hold',failed:['Failed check']}]);controller.open('d7');
controller.confirmBlind(true);assert.equal(controller.canSubmit('approved',''),false,'confirmation never bypasses the reading gate');
controller.openDetails();assert.equal(controller.canSubmit('approved',''),true);
""")

    def test_selection_keeps_geometry_and_disclosures_use_chevrons(self):
        html=(S / 'scripts/graphflow/page.html').read_text()
        js=(S / 'scripts/graphflow/page.js').read_text()
        self.assertIn('summary::-webkit-details-marker{display:none}',html)
        self.assertIn('details[open]>summary:before{transform:rotate(45deg)',html)
        self.assertNotIn('content:"▶"',html)
        self.assertNotIn('if(chosenNode && layout.bounds',js)
        self.assertIn('#flow.has-selection{grid-template-columns:minmax(0,1fr)}',html)
        self.run_controller(r"""
const nodes=['a','b','c'].map(id=>({id,title:id,kind:'work'})), edges=[{from:'a',to:'b'},{from:'b',to:'c'}];
const before=layeredLayout(nodes,edges);
for(const expanded of ['a','b','c'])assert.deepEqual(layeredLayout(nodes,edges,[],true,{expanded}).positions,before.positions);
assert.equal(statusGlyph('running'),'▶');
""")

    def test_card_history_never_competes_with_current_status(self):
        js=(S / 'scripts/graphflow/page.js').read_text()
        card=js.split('function nodeCard(',1)[1].split('function createMap()',1)[0]
        self.assertIn("t('pastReturn'",card)
        self.assertNotIn('checkWording',card)
        self.assertNotIn('failure-mark',card)
        self.assertLess(card.index('statusLine'),card.index("t('pastReturn'"))

    def test_real_demo_and_decision_view(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ):
            root = pathlib.Path(directory)
            run = build_demo_run(root / 'home', root / 'project')
            current, events, derived = server._snapshot(run)
            view = server._view(current, derived, events, root / 'project')
            self.assertEqual(view['counts'], {'done': 2, 'doing': 1, 'waiting': 2, 'needs_you': 1, 'returned': 1, 'returns_total': 1})
            self.assertEqual([n['laps'] for n in view['nodes']], [['passed'], ['passed'], ['returned', 'current'], ['waiting_for_you'], [], []])
            # The record is in the order things happened, one row per attempt with its real checks.
            rows = view['timeline']
            self.assertEqual([r['seq'] for r in rows], sorted(r['seq'] for r in rows))
            self.assertEqual([r['kind'] for r in rows[:2]], ['started', 'planned'])
            returned = [r for r in rows if r['kind'] == 'attempt' and r['state'] == 'returned']
            self.assertEqual(len(returned), 1)
            failed = [c for c in returned[0]['checks'] if c['result'] == 'failed']
            self.assertTrue(failed and all(c['command'] and c['phase'] == 'gate' for c in failed))
            self.assertTrue(returned[0]['reason'])
            self.assertEqual(len({r['id'] for r in rows}), len(rows))
            asked = [r for r in rows if r['kind'] == 'asked']
            self.assertEqual([r['decision'] for r in asked], [d['id'] for d in view['decisions']])
            self.assertEqual(view['run'], run.name)
            decision = view['decisions'][0]
            self.assertEqual(decision['purpose'], 'human_check')
            self.assertEqual(decision['verified'], ['약속한 결과가 빠짐없이 있어요'])
            self.assertEqual(decision['unverified'], ['처음 읽는 분도 따라 할 수 있어요', '설치 순서가 처음 쓰는 분께 자연스러운지는 확인하지 못했어요.'])
            self.assertEqual(decision['worker_note'], '설치 순서 부분은 자신이 없어요.')
            self.assertTrue(decision['context']['why'])
            self.assertEqual(decision['files'], [{'name':'guide.txt','path':'guide.txt'}])
            self.assertEqual(view['language'],'ko')
            self.assertEqual(view['nodes'][3]['inputs'], [{'label': '기록 사용법', 'other_title': '기록 저장', 'delivered': True}])
            self.assertEqual(view['nodes'][3]['outputs'], [{'label': '읽기 쉬운 설명', 'other_title': '현황판 화면', 'delivered': False}])
            self.assertTrue(view['lessons'])


if __name__ == '__main__':
    unittest.main()
