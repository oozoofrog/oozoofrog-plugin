"""Panel context, answer provenance and plain dashboard language."""
import unittest
import test_page
import test_round17

class Copy19Tests(unittest.TestCase):
    run_controller = test_page.PageTests.run_controller
    run_dom = test_page.PageTests.run_dom
    js = test_round17.PresentationTests.js

    def test_v4_worker_section_has_a_value_and_grouped_headings(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest;live={...live,language:'ko',decisions:[],nodes:[{...live.nodes[0],kind:'work',contract:{},worker:{model:'화면-검증'},status:'running'}]};api.applyView(live);api.selectNode('work');
const p=get('panel');assert(p.textContent.includes('모델: 화면-검증'));
const facts=p.querySelectorAll('.fact-section');assert(facts.length);assert(facts.every(f=>f.firstElementChild.tagName==='h3'&&f.children.length>1));
""")

    def test_v6_terminal_unverified_answer_same_statement_in_banner_and_record(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest;live={...live,language:'ko',decisions:[],plan_approval:{id:'d20',status:'answered',verified:false,source:'terminal',question:'시작할까요?'}};api.applyView(live);
const sentence='터미널에서 온 답이에요. 서명을 확인할 수 없어요.';
assert(get('attention').textContent.includes(sentence));assert.equal(api.rowSentence({kind:'answered',verified:false,source:'terminal'}),sentence);
assert(!get('attention').textContent.includes('보낸 내 답'));
""")

    def test_v7_review_activity_and_labelled_model_attempt(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest;live={...live,language:'ko',decisions:[],nodes:[{...live.nodes[0],kind:'review',status:'running',attempts:1,max_attempts:3,contract:{},worker:{model:'화면-검증'}}]};api.applyView(live);
live.timeline[0].by={role:'leader'};api.applyView(live);assert(get('home').querySelectorAll('.row-who').find(e=>e.textContent.includes('모델: m')).textContent.startsWith('작업 담당자'));
assert(get('phone-flow').textContent.includes('검토하고 있어요'));assert(!get('phone-flow').textContent.includes('만들고 있어요'));assert(get('phone-flow').textContent.includes('1번째 시도 · 최대 3번'));api.selectNode('work');assert(get('panel').textContent.includes('모델: 화면-검증'));
""")

    def test_v8_evidence_button_next_to_hint_and_legacy_question(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest;live={...live,language:'ko',decisions:[{...d,files:[],failed:['검토 의견'],failed_reviews:1,review_lenses:['접근성'],context:{}}]};api.applyView(live);get('attention').querySelectorAll('button').at(-1).click();
const panel=get('decision');assert(panel.querySelector('.evidence-action'));assert(panel.textContent.includes('자세한 근거를 먼저 열어 주세요.'));assert.equal(panel.querySelector('.review-lenses').textContent,'검토 관점 · 접근성');
get('flow-tab').click();live={...live,legacy:true,decisions:[{...d,purpose:'human_check',question:'Read this guide',files:[],failed:[],context:{}}]};api.applyView(live);get('attention').querySelectorAll('button').at(-1).click();assert(get('decision').querySelector('h2').textContent.endsWith('?'));assert(get('decision').textContent.includes('이전 실행에서 제출한 결과'));
""")

    def test_v8_no_orphan_record_number_and_explicit_words(self):
        self.js(r"""
assert(STRINGS.ko.freeQuestion.includes('통과 여부를 바꾸지 않아요'));assert(STRINGS.ko.offWorking.includes('진행 중 {n}개'));assert(STRINGS.ko.permissionNoEvidence.includes('채팅'));assert(!STRINGS.ko.oldRunApproval.includes('0.2.1'));assert(STRINGS.ko.oldVersionDetails.includes('0.2.1'));
for(const key of ['planStartEffect','planBackEffect','planWaitingRevision','idle'])assert(STRINGS.ko[key].includes('진행 담당자'));
""")

    def test_v8_panel_state_once_warning_names_card_and_no_orphan_record_order(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest;
live={...live,language:'ko',decisions:[],nodes:[{...live.nodes[0],kind:'work',title:'안내 쓰기',status:'running',contract:{},planned_checks:[{type:'cmd',title:'검사',run:'bash check.sh',runs_own_files:true}]}]};api.applyView(live);api.selectNode('work');
assert.equal(get('panel').querySelectorAll('p').filter(p=>p.textContent==='만들고 있어요').length,1);
assert(get('home').querySelectorAll('.row-time').every(e=>!e.children.length));
api.selectNode('work');live={...live,plan_approval:{id:'d20',status:'open',question:'시작?',identity:{revision:1}}};api.applyView(live);assert(get('attention').querySelector('.own-check-note').textContent.startsWith('안내 쓰기:'));
""")


import test_plan_approval
import test_review11
from graphflow import server, store

class Provenance19Tests(unittest.TestCase):
    setUp = test_plan_approval.PlanApprovalTests.setUp
    call = test_plan_approval.PlanApprovalTests.call
    set_plan = test_plan_approval.PlanApprovalTests.set_plan
    snapshot = test_plan_approval.PlanApprovalTests.snapshot
    accept = test_plan_approval.PlanApprovalTests.accept

    def test_v6_recorded_terminal_source_does_not_verify_signature(self):
        self.accept(self.set_plan()['decision'])
        test_review11.Review11Tests.rewrite(self, lambda events: next(e['data'] for e in events if e['type'] == 'decision.answer').update(sig='tampered-signature'))
        plan, derived = self.snapshot()
        view = server._view(plan, derived, store.events(self.run), self.project.resolve())
        row = next(r for r in view['timeline'] if r['kind'] == 'answered')
        self.assertEqual(row['source'], 'terminal')
        self.assertFalse(row['verified'])
        self.assertEqual(view['plan_approval']['source'], 'terminal')
        self.assertFalse(view['plan_approval']['verified'])
