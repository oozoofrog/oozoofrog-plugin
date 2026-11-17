"""Round 18: screenshot findings stay tied to rendered content and relations."""
import test_round17
import unittest


class Rendering18Tests(unittest.TestCase):
    js = test_round17.PresentationTests.js

    def test_e6_measured_content_controls_both_layout_levels(self):
        self.js(r"""
const nodes=[{id:'a',kind:'work',title:'A'},{id:'b',kind:'work',title:'B'}];
for(const level of ['detail','overview']) {
 const l=layeredLayout(nodes,[{from:'a',to:'b'}],[],true,{level,measure:n=>n.id==='a'?350:220});
 assert(l.positions.a.height>=350);assert(l.positions.b.height>=220);
 const c=compactOverview(l,180);assert(c.positions.a.height>=350);
 assert(c.positions.b.y>=c.positions.a.y+c.positions.a.height || c.positions.b.x>=c.positions.a.x+c.positions.a.width);
}
""")

    def test_e7_every_change_kind_hides_internal_check_tokens(self):
        self.js(r"""
const checks=['cmd','scope','cites','human','host'].map((type,i)=>({id:'internal_'+i,type,...(type==='cmd'?{run:'test -s guide.txt',timeout_s:600,cwd:'.',shell:'/bin/sh',environment:'inherited'}:type==='human'?{prompt:'Does it read well?'}:type==='host'?{tool:'browser',expect:'page opens'}:{})}));
for(const check of checks)for(const [before,after] of [[{}, {checks:[check]}],[{checks:[check]},{}],[{checks:[check]},{checks:[{...check,title:'A named check'}]}],[{checks:[check]},{checks:[{...check,type:'host',tool:'browser',expect:'ready'}]}]])for(const lang of ['ko','en']){
 const changes=contractDiff(before,after);assert(changes.length);
 const text=changes.map(f=>contractDiffText(f,lang)).join('\n');
 assert(!/internal_|\b(?:cmd|scope|cites|human|host)\b|\[object Object\]/.test(text),text);
 if(check.timeout_s&&(!before.checks||!after.checks))assert(text.includes(STRINGS[lang].field_timeout_s),text);
}
const named={id:'text',type:'cmd',title:'내용 검사',run:'test -s guide.txt'};
const changed=contractDiff({checks:[named]},{checks:[{...named,run:'test -r guide.txt'}]});
assert(contractDiffText(changed[0],'ko').includes('검사 · 내용 검사 · 실행 명령'));
assert(!contractDiffText(changed[0],'ko').includes('text'));
""")

    def test_e7_contract_field_and_enum_sweep(self):
        self.js(r"""
const before={kind:'work',grade:'daily',decision_kind:'authorization',status:'active',isolation:'shared or worktree, selected at assignment',merge:'committed submissions must be merged into project HEAD; merge --no-ff',checks:[{id:'x',type:'cmd',run:'echo exact-command',cwd:'docs',timeout_s:600,shell:'/bin/sh',environment:'inherited'}],needs:[{from:'node_id',artifact:'document'}],target:'node_id',requirement:'req_id',context:{why:'Reason',if_approved:'Proceed',if_rejected:'Revise',undo:'Revert'},summary:'Summary',goal:'Goal',owns:['guide.txt'],outputs:['document'],reads:['readme.md'],lane:1,effective_lane:1,max_attempts:3,requirements:[{id:'req_id',text:'Requirement'}],constraints:[{id:'c',text:'Constraint',status:'promoted',scope:{paths:['docs'],tags:['docs']},derived_from:{run:'run_internal',node:'node_id',attempt:1,evidence:'evidence/check.log'},review_when:'Later',created:'2026-11-17'}]};
const names={node_id:'A named task',req_id:'A requirement',c:'A constraint'};
for(const lang of ['ko','en'])for(const [a,b] of [[{},before],[before,{}],[before,{...before,grade:'security',decision_kind:'direction',status:'promoted'}]]){
 const text=contractDiff(a,b).map(f=>contractDiffText(f,lang,names)).join('\n');
 assert(!/run_internal|node_id|req_id|effective_lane|max_attempts|timeout_s|decision_kind|if_approved|if_rejected|\bdaily\b|\bsecurity\b|\bauthorization\b|\binherited\b|shared or worktree|merge --no-ff/.test(text),text);
 assert(!text.includes(STRINGS[lang].diffOther),text);
 assert(text.includes('echo exact-command')||a===before&&b.grade==='security');
}
""")

    def test_e10_every_panel_relation_equals_a_drawn_edge(self):
        self.js(r"""
const original={nodes:[{id:'a',title:'Work',kind:'work'},{id:'r',title:'Review',kind:'review'},{id:'q',title:'Permission',kind:'decision'}],edges:[{from:'r',to:'a',relation:'reviews'},{from:'a',to:'q',relation:'waits_for_decision'}]};
for(const lang of ['ko','en']){
 const flow=planFlow(original,lang),edges=forwardEdges(flow.edges);
 for(const n of flow.nodes){
  assert.deepEqual(n.inputs.map(r=>r.other_id),edges.filter(e=>e.to===n.id).map(e=>e.from));
  assert.deepEqual(n.outputs.map(r=>r.other_id),edges.filter(e=>e.from===n.id).map(e=>e.to));
 }
 assert(flow.nodes.find(n=>n.id==='r').outputs.some(r=>r.other_id==='_run_checks'&&r.runLevel));
 assert(flow.nodes.find(n=>n.id==='r').inputs.some(r=>r.other_id==='a'));
 for(const level of ['detail','overview'])assert.deepEqual(layeredLayout(flow.nodes,flow.edges,[],true,{level}).routes.map(r=>r.from+'>'+r.to).sort(),edges.map(e=>e.from+'>'+e.to).sort());
}
assert.equal(original.nodes[0].inputs,undefined,'presentation never mutates recorded relations');
""")

    def test_e12_small_copy_names_units_roles_and_checkbox(self):
        self.js(r"""
assert(STRINGS.ko.workerNote.includes(STRINGS.ko.roleWorker));assert(STRINGS.ko.ownCheckEffect.includes(STRINGS.ko.roleWorker));
assert.notEqual(STRINGS.ko.roleWorker,STRINGS.ko.roleLeader);
assert(STRINGS.ko.planItemsTable.includes('일·검토·결정 카드'));
assert(STRINGS.ko.repeatedSteps.includes('일 {n}개'));assert(!STRINGS.ko.repeatedSteps.includes('단계'));
assert(STRINGS.ko.replacesRefused.includes('허락하지 않은'));assert(STRINGS.ko.refuse.includes('허락하지'));
assert(STRINGS.ko.replacesReturned.includes('돌려보낸'));
for(const key of ['permissionBlindHint','blindHint'])assert(STRINGS.ko[key].includes('확인 상자를 선택'));
for(const language of ['ko','en'])assert(STRINGS[language].planUnverifiedSource.includes('{source}')&&STRINGS[language].planUnverifiedSource.includes('{id}'));
""")


import test_page


class Content18Tests(unittest.TestCase):
    run_controller = test_page.PageTests.run_controller
    run_dom = test_page.PageTests.run_dom

    def test_e8_change_list_uses_the_marked_card_title(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest;
const a={id:'d20',purpose:'plan_approval',kind:'authorization',status:'open',question:'Start?',files:[],failed:[],context:{},identity:{revision:1}};
live={...live,decisions:[a],plan_approval:a,run_contract:{goal:'Old goal'},nodes:[{...live.nodes[0],contract:{goal:'Old'}}]};api.applyView(live);
live={...live,plan_approval:{...a,id:'d21',identity:{revision:2}},run_contract:{goal:'New goal'},nodes:[{...live.nodes[0],contract:{goal:'New'}}]};live.decisions=[live.plan_approval];api.applyView(live);
const summaries=get('attention').querySelector('.plan-change-list').querySelectorAll('summary').map(e=>e.textContent);
assert(summaries.includes('Changed · Check the whole result'));assert(!summaries.some(t=>t.includes('Flow')));
const marked=get('map').querySelectorAll('.node-card').filter(c=>c.querySelector('.change-mark')).map(c=>c.querySelector('.node-title').textContent);
assert.deepEqual(summaries.map(t=>t.split(' · ')[1]).sort(),marked.sort());
""")

    def test_e9_unread_reason_names_card_and_existing_read_action(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest;
const a={id:'d20',purpose:'plan_approval',kind:'authorization',status:'open',question:'Start?',files:[],failed:[],context:{},identity:{revision:1}};
live={...live,decisions:[a],plan_approval:a,nodes:[{...live.nodes[0],contract:{}}]};api.applyView(live);
matchMedia=()=>({matches:false});api.graphRead.clear();api.graphRead.add('_run_checks');
assert.equal(api.graphReadReason(),'Unread cards: Work. Scroll to show each whole card.');
api.updateUnreadMarks();assert.equal(get('map').querySelector('.node-card').querySelector('.unread-mark').textContent,'Unread');
api.graphRead.add('work');api.updateUnreadMarks();assert.equal(api.graphReadReason(),'');
assert.equal(get('map').querySelector('.node-card').querySelector('.unread-mark'),null);
""")

    def test_e11_question_once_in_panel_and_no_duplicate_passed_checks(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest,q='Is this wording clear?';
const node={...live.nodes[0],contract:{},planned_checks:[{type:'human',prompt:q}],declared_outputs:[]};
live={...live,nodes:[node],planned_questions:[{node:node.id,when:'after_work',question:q}]};api.applyView(live);
const parent=new Element('section');api.planFacts(parent,node);
assert.equal(parent.textContent.split(q).length-1,1);assert(parent.textContent.includes('For your response'));
live.decisions=[{...d,purpose:'human_check',failed:[],verified:['Unit passes'],worker_note:null}];live.timeline[0].checks[0].result='passed';api.applyView(live);
get('attention').querySelectorAll('button').at(-1).click();
assert.equal(get('decision').querySelectorAll('.card').filter(c=>c.firstElementChild?.textContent==='Already verified').length,0);
""")

    def test_e4_command_has_value_without_a_stranded_visible_label(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest,node={...live.nodes[0],contract:{},planned_checks:[{type:'cmd',command:'test -s guide.txt',run:'test -s guide.txt',cwd:'.',timeout_s:600,shell:'/bin/sh',environment:'inherited'}]};
live.nodes=[node];api.applyView(live);const parent=new Element('section');api.planFacts(parent,node);
const command=parent.querySelector('.planned-command');assert.equal(command.textContent,'test -s guide.txt');assert.equal(command['aria-label'],'Planned command');
assert.equal(parent.querySelectorAll('p').filter(e=>e.textContent==='Planned command').length,0);
""")

    def test_e12_counts_roles_outcome_and_question_are_explicit(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest;
live={...live,language:'ko',decisions:[],nodes:[{...live.nodes[0],kind:'decision',status:'pending',contract:{decision_kind:'authorization'},attempts:0}],answered:[{id:'d1',node:'work',verified:true,kind:'authorization',outcome:'approved',answer:'확인했어요'}],planned_questions:[{node:'work',question:'이 안내를 시험 환경에 공개할까요?',answered:true,kind:'authorization',outcome:'approved',answer:'확인했어요'}]};
api.applyView(live);
assert(get('subtitle').textContent.includes('시작 전이에요 2'));
const c=api.nodeCard(live.nodes[0]);assert(c.querySelector('.planned-question').textContent.includes('이 안내를 시험 환경에 공개할까요?'));assert(c.querySelector('.answered-result').textContent.includes('허락하기로 답했어요'));
assert(c.querySelector('.answered-result').textContent.includes('확인했어요'));
""")

    def test_e12_evidence_hold_source_and_replacement_words(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest;
live={...live,language:'ko',decisions:[{...d,files:[],failed:['문구 검토'],failed_reviews:1,context:{why:'이유'}}]};api.applyView(live);
get('attention').querySelectorAll('button').at(-1).click();
assert(get('decision').textContent.includes('읽을 파일은 없어요. 자세한 근거를 열어'));
assert(!get('decision').querySelector('.evidence').querySelector('summary').classList.contains('primary'));
const effect=get('decision').querySelectorAll('[data-effect]').find(e=>e.dataset.effect==='approved');
assert(effect.textContent.includes('통과하지 못한 검토 의견'));assert(!effect.textContent.includes('실패한 검사'));
assert(effect.textContent.includes('진행 담당자가 남은 통과 조건을 확인해요'));
get('flow-tab').click();live.plan_approval={id:'d20',status:'answered',verified:false,source:'terminal',question:'이 계획대로 시작할까요?'};live.decisions=[];api.applyView(live);
assert(get('attention').textContent.includes('계획에 대한 내 답'));assert(get('attention').textContent.includes('터미널에서 보낸 내 답'));assert(get('attention').textContent.includes('결정 d20'));
""")

    def test_e12_changed_file_notice_names_decision_and_card(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest;
get('attention').querySelectorAll('button').at(-1).click();api.showChangedDecision();
assert(get('decision').textContent.includes('d7'));assert(get('decision').textContent.includes('Work'));
assert(get('decision').textContent.includes('Missing case'));
""")


import test_plan_approval
from graphflow import server, store


class Model18Tests(unittest.TestCase):
    setUp = test_plan_approval.PlanApprovalTests.setUp
    call = test_plan_approval.PlanApprovalTests.call
    set_plan = test_plan_approval.PlanApprovalTests.set_plan
    snapshot = test_plan_approval.PlanApprovalTests.snapshot
    accept = test_plan_approval.PlanApprovalTests.accept

    def test_e12_answer_source_kind_and_replacement_outcome_are_presentation_data(self):
        self.accept(self.set_plan()['decision'])
        plan, derived = self.snapshot()
        view = server._view(plan, derived, store.events(self.run), self.project.resolve())
        self.assertEqual(view['plan_approval']['source'], 'terminal')
        self.assertEqual(view['answered'][0]['kind'], 'authorization')
        self.assertTrue(view['plan_approval']['verified'])
