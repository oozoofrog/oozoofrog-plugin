"""Screenshot defects: presentation must agree with the recorded plan."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / 'scripts/graphflow/page.js'
HTML = ROOT / 'scripts/graphflow/page.html'
NODE = shutil.which('node')


class PresentationTests(unittest.TestCase):
    def js(self, code):
        if not NODE:
            self.skipTest('Node is required for pure presentation functions')
        source = PAGE.read_text().split("if (typeof document !== 'undefined')")[0]
        result = subprocess.run([NODE, '--input-type=module', '-'], input=source +
                                "\nimport assert from 'node:assert/strict';\n" + code,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_d1_fixture_edges_and_order_at_every_level_selection_and_width(self):
        path = ROOT.parents[1] / 'dev/screens/build_fixtures.py'
        spec = importlib.util.spec_from_file_location('screen_fixtures', path)
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        for name, count in [('many', 13), ('large', 13), ('30', 30)]:
            with self.subTest(fixture=name):
                self.js('const nodes=' + json.dumps(fixtures.branching(count)) + r''';
const edges=nodes.flatMap(n=>n.needs.map(e=>({from:e.from,to:n.id})));
const expected=edges.map(e=>e.from+'>'+e.to).sort();let order;
for(const level of ['detail','overview'])for(const width of [390,760,1000,1440])for(const selected of [null,...nodes.map(n=>n.id)]) {
 const raw=layeredLayout(nodes,edges,[],true,{level,expanded:selected});
 const l=level==='overview'?compactOverview(raw,width-(selected?320:0)):raw;
 assert.deepEqual(l.routes.map(e=>e.from+'>'+e.to).sort(),expected);
 if(order)assert.deepEqual(l.order,order);order=l.order;
 for(const r of l.routes){const a=l.positions[r.from],b=l.positions[r.to];assert.equal(r.start.x,a.x+a.width);assert.equal(r.end.x,b.x);}
 for(const r of l.routes)for(const c of l.cardRects)for(let i=1;i<r.points.length;i++){
  const a=r.points[i-1],b=r.points[i];
  const enters=a.x===b.x?a.x>c.x&&a.x<c.x+c.width&&Math.max(a.y,b.y)>c.y&&Math.min(a.y,b.y)<c.y+c.height:a.y>c.y&&a.y<c.y+c.height&&Math.max(a.x,b.x)>c.x&&Math.min(a.x,b.x)<c.x+c.width;
  assert(!enters,'route enters unrelated card '+c.id);
 }
}
''')

    def test_d2_check_changes_are_words_not_object_coercion(self):
        self.js(r'''
const check={id:'text',type:'cmd',title:'내용 검사',run:'test -s guide.txt',timeout_s:5};
for(const [before,after] of [[{}, {checks:[check]}],[{checks:[check]},{}],[{checks:[check]},{checks:[{...check,run:'test -r guide.txt'}]}],[{checks:[check]},{checks:[check,{...check,id:'new'}]}],[{checks:[check]},{checks:[{...check,timeout_s:12}]}]]){
 const diff=contractDiff(before,after);assert(diff.length);
 for(const lang of ['ko','en']){const text=diff.map(d=>contractDiffText(d,lang)).join('\n');assert(!text.includes('[object Object]'));assert(!text.includes('—'));assert(text.includes('text')||text.includes('내용 검사'));}
}
assert(contractDiffText(contractDiff({checks:[check]},{checks:[{...check,timeout_s:12}]})[0],'ko').includes('5초 → 12초'));
for(const [before,after] of [[{}, {id:'new',title:'새 일',checks:[check]}],[{id:'old',title:'이전 일',checks:[check]},{}]]){const text=contractDiff(before,after).map(d=>contractDiffText(d,'ko')).join(' ');assert(!text.includes('[object Object]'));assert(!text.includes('—'));}
assert(durationDiff({field:'title',before:null,after:'새 일'},'ko').includes('추가'));
assert(durationDiff({field:'title',before:'이전 일',after:null},'ko').includes('삭제'));
''')

    def test_d3_owned_execution_warning_has_a_slot_and_one_explanation(self):
        self.js(r'''
assert(STRINGS.ko.ownCheckEffect.includes('작업 담당자가'));
assert(!STRINGS.ko.ownCheckEffect.includes('자신이 검사하는'));
const n={id:'a',kind:'work',title:'제목',planned_checks:[{type:'cmd',runs_own_files:true}]};
assert(detailCardHeight(n)>=detailCardHeight({...n,planned_checks:[{type:'cmd'}]})+30);
assert(layeredLayout([n],[],[],true,{level:'overview'}).positions.a.height>=104);
''')
        source = PAGE.read_text()
        self.assertIn("if(ownChecks)box.append(el('p',t('ownCheckCards',", source)
        self.assertIn('.overview-card .own-check-mark{position:static;grid-column:1/-1}', HTML.read_text())

    def test_d4_action_counts_plan_counts_and_actual_title_rectangles(self):
        self.js(r'''
const d={decisions:[{id:'d1',node:'a'},{id:'d2',free:true}],nodes:[{id:'a'}]};
assert.equal(actionableDecisions(d).length,2);
assert.equal(actionableDecisions(d,['d1']).length,1);
assert.equal(actionableDecisions({...d,key_mismatch:true}).length,0);
assert.equal(actionableDecisions({...d,stale_decisions:[{id:'d1'}]}).length,1);
assert.equal(titleVisibility({x:0,y:80,width:100,height:20},100,100),true);
assert.equal(titleVisibility({x:0,y:81,width:100,height:20},100,100),false);
assert.equal(titleVisibility({x:-1,y:0,width:100,height:20},100,100),false);
assert(STRINGS.ko.countDecision.includes('단계'));assert(STRINGS.ko.countPlannedDecision.includes('응답'));
assert(STRINGS.ko.visiblePlan.includes('+ 전체 결과 확인 1개'));
assert(STRINGS.ko.planItemsTable.includes('일·검토·결정 카드'));
''')
        source = PAGE.read_text()
        self.assertIn('tr.left-vr.left', source)
        self.assertIn('String(actionableDecisions(view,unavailableDecisions).length)', source)

    def test_d5_panels_do_not_claim_absent_handoffs_or_cover_content(self):
        source, html = PAGE.read_text(), HTML.read_text()
        self.assertIn("relationFacts(parent,node)", source)
        self.assertIn('.panel-bar{position:static;', html)
        self.assertIn('#node-list>.card>button{position:static;', html)
        self.assertIn('padding-bottom:var(--plan-actions-height', html)
        self.assertIn('scrollbar-gutter:stable', html)

    def test_d6_waiting_and_hold_messages_have_the_right_target(self):
        self.js(r'''
assert(STRINGS.ko.planMissing.includes('기다려요'));
assert(STRINGS.ko.holdReviewExact.includes('검토 일의 의견'));
assert(!STRINGS.ko.holdAccept.includes('시작'));
assert(STRINGS.ko.holdAccept.includes('남은 통과 조건'));
assert(STRINGS.ko.supersededNotice.includes('{old}'));assert(STRINGS.ko.supersededNotice.includes('{new}'));
''')
        source = PAGE.read_text()
        changed = source.split('function showChangedDecision(){')[1].split('\n')[0]
        self.assertIn('unavailableDecisions.push', changed)
        self.assertIn('showGraph', changed)
        self.assertLess(source.index('const old=view.superseded'), source.index('const stale=view.stale_decisions'))

    def test_d7_reading_gates_explain_lock_and_prior_reading(self):
        self.js(r'''
assert(STRINGS.ko.readOffscreen.includes('화면 밖'));assert(!STRINGS.ko.graphReadDone.includes('화면 밖'));
assert(STRINGS.ko.changesReadReason.includes('읽어 주세요'));
assert(STRINGS.ko.oldReadReason.includes('계속'));
assert(STRINGS.ko.planGraphReason.includes('{action}'));
assert(!STRINGS.ko.preapprovalExplanation.includes('승인하면'));
''')
        source = PAGE.read_text()
        self.assertIn('graphReadDone()', source)
        self.assertIn("!oldResults.every(n=>planRead.has('result:'+n.id))?t('oldReadReason')", source)

    def test_d8_labels_commands_context_and_log_are_unambiguous(self):
        self.js(r'''
assert.notEqual(STRINGS.ko.plannedCheck,STRINGS.ko.questionsForNode);
assert.equal(STRINGS.ko.planIntegration,STRINGS.ko.runChecksTitle);
assert.notEqual(STRINGS.ko.authorWhy,STRINGS.ko.why);
assert(STRINGS.ko.evWording.includes('이전 계획 승인은 유지'));
assert.notEqual(STRINGS.ko.detailsSummary,STRINGS.ko.details);
const c={type:'cmd',command:'test -s a',cwd:'.',timeout_s:5};
assert.equal(uniqueChecks([c,{...c,id:'another'}]).length,1);
assert.equal(uniqueChecks([c,{...c,timeout_s:10}]).length,2);
''')
        source = PAGE.read_text()
        self.assertNotIn("n.title+' ('+n.node+')'", source)
        reading = source.split('function openDecision(')[1].split('function leaveDecision')[0]
        self.assertEqual(reading.count("t('freeEffect')"), 1)
        self.assertEqual(reading.count("t('details')"), 1)
        self.assertIn("t('qInspect')", reading)

    def test_d9_answers_scope_body_and_outputs_are_readable(self):
        self.js(r'''
assert(STRINGS.ko.replacesRefused.includes('허락하지 않은 결정'));
assert(STRINGS.ko.scopeBody.includes('변경한 파일'));
assert(STRINGS.ko.answerGiven.includes('{answer}'));
''')
        source = PAGE.read_text()
        self.assertIn("answer.append(el('summary',t('answerExpand'))", source)
        self.assertIn("if(c.type==='scope')item.append(el('p',t('scopeBody')))", source)
        self.assertIn("STRINGS.ko.genericOutput,STRINGS.en.genericOutput", source)
        self.assertIn('.answered-result p{white-space:normal;overflow:visible;', HTML.read_text())

    def test_d10_readable_size_and_running_shape(self):
        html = HTML.read_text()
        self.assertIn('.node-card.working{border-style:dashed}', html)
        self.assertIn('.overview-card .status-glyph{font-size:20px;', html)
        self.assertIn('.map-visible,.map-overflow button{font-size:13px}', html)
        self.assertNotIn('font-size:11px', html)
        self.js(r'''
assert.equal(statusGlyph('running'),'▶');assert.notEqual(statusGlyph('running'),statusGlyph('submitted'));
const luminance=hex=>hex.match(/\w\w/g).map(c=>parseInt(c,16)/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4).reduce((a,c,i)=>a+c*[.2126,.7152,.0722][i],0);
for(const ink of ['536174','79500c','245b8e','345bc1'])for(const paper of ['ffffff','f5f7f9'])assert((luminance(paper)+.05)/(luminance(ink)+.05)>=4.5);
assert(14*MIN_FIT_SCALE>=12);
''')


import test_plan_approval as fixture
from graphflow import server, store
from human_support import human_answer


class ModelPresentationTests(unittest.TestCase):
    setUp = fixture.PlanApprovalTests.setUp
    call = fixture.PlanApprovalTests.call
    set_plan = fixture.PlanApprovalTests.set_plan
    snapshot = fixture.PlanApprovalTests.snapshot
    accept = fixture.PlanApprovalTests.accept

    def view(self):
        plan, derived = self.snapshot()
        return server._view(plan, derived, store.events(self.run), self.project.resolve())

    def test_d4_verified_list_includes_implicit_scope_and_untitled_command(self):
        self.raw['nodes'][0]['checks'][0].pop('title')
        self.raw['nodes'][0]['checks'].append({'id':'human','type':'human','prompt':'읽을 수 있나요?'})
        self.accept(self.set_plan()['decision'])
        self.call('start','a');(self.project/'guide.txt').write_text('안내')
        self.call('submit','a');self.call('gate','a',code=1)
        decision = self.view()['decisions'][0]
        self.assertEqual(set(decision['verified']), {'test -s guide.txt','scope'})
        row = next(r for r in self.view()['timeline'] if r['kind']=='attempt')
        self.assertEqual(len(decision['verified']), len([c for c in row['checks'] if c['result']=='passed']))

    def test_d6_superseded_link_targets_matching_gate_not_plan_approval(self):
        self.raw['nodes'][0]['checks'].append({'id':'human','type':'human','prompt':'읽을 수 있나요?','context':{'why':'처음 안내예요'}})
        approval = self.set_plan()['decision'];self.accept(approval)
        self.call('start','a');(self.project/'guide.txt').write_text('안내')
        self.call('submit','a');old=self.call('gate','a',code=1)['asks'][0]
        self.raw['nodes'][0]['checks'][-1]['context']['why']='새 안내예요'
        self.set_plan();new=self.call('gate','a',code=1)['asks'][0]
        replacement=next(d for d in self.view()['superseded'] if d['id']==old)
        self.assertEqual(replacement['replacement'],new)
        self.assertNotEqual(new,approval)

    def test_d9_replacement_names_refused_decision_and_preserves_answer(self):
        self.raw['nodes']=[{'id':'q','kind':'decision','lane':1,'goal':'공개 범위',
                           'question':'공개할까요?','decision_kind':'authorization'}]
        self.accept(self.set_plan()['decision']);old=self.call('gate','q',code=1)['asks'][0]
        human_answer(self.run,old,'revision_requested','시험 환경부터 확인해 주세요')
        self.raw['nodes'][0]['question']='시험 환경에 공개할까요?'
        self.accept(self.set_plan()['decision']);new=self.call('gate','q',code=1)['asks'][0]
        self.assertEqual(next(d for d in self.view()['decisions'] if d['id']==new)['replaces_refused'],old)
        self.assertEqual(next(d for d in self.view()['timeline'] if d['kind']=='answered' and d.get('decision')==old)['answer'],'시험 환경부터 확인해 주세요')

    def test_d6_review_lens_is_plain_and_acceptance_leaves_gate_in_charge(self):
        from test_review15 import Recovery15Tests
        nid, did = Recovery15Tests.prepare(self, 'hold_review')
        decision = next(d for d in self.view()['decisions'] if d['id']==did)
        self.assertIn('safety', decision['review_lenses'])
        self.assertNotIn("['", decision['failed'][0])
        self.assertEqual(self.view()['nodes'][1]['status'], 'passed')
        self.accept(did)
        self.assertEqual(self.call('gate', nid)['verdict'], 'pass')
