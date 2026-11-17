"""One reading requirement and truthful spatial feedback."""
import unittest
import test_page
import test_round17

class Navigation19Tests(unittest.TestCase):
    run_controller = test_page.PageTests.run_controller
    run_dom = test_page.PageTests.run_dom
    js = test_round17.PresentationTests.js

    def test_v1_completed_reading_breakdown_and_neutral_note(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest;
live={...live,language:'ko',decisions:[],plan_approval:{id:'d20',status:'open',identity:{revision:1},question:'시작?'},nodes:[{...live.nodes[0],contract:{}}]};api.applyView(live);
matchMedia=()=>({matches:false});api.recordGraphRead();api.graphRead.add('work');api.graphRead.add('_run_checks');api.updateUnreadMarks();
const text=api.graphReadDone();assert(text.includes('계획 카드 1개와 전체 결과 확인 1개'));assert(!text.includes('화면 밖'));
api.recordGraphRead();assert(get('attention').querySelector('.action-hint').classList.contains('read-done'));
""")

    def test_v2_fit_respects_readable_floor_and_reports_failure(self):
        self.js(r"""
const small={bounds:{width:600,height:400}},large={bounds:{width:2000,height:1500}};
assert.deepEqual(fitGraph({detail:large,overview:small},800,500),{level:'overview',scale:1,fits:true});
const result=fitGraph({detail:large,overview:large},800,500);assert.equal(result.fits,false);assert(result.scale>=6/7);assert(STRINGS.ko.scrollView.includes('스크롤'));
""")

    def test_v3_visible_means_whole_title_inside_content_viewport(self):
        self.js(r"""
for(const rect of [{x:0,y:0,width:100,height:60},{x:10,y:10,width:90,height:50}])assert(titleVisibility(rect,100,60));
for(const rect of [{x:-1,y:0,width:100,height:60},{x:0,y:0,width:101,height:60},{x:0,y:0,width:100,height:61}])assert(!titleVisibility(rect,100,60));
""")

    def test_v5_unread_marks_and_reason_use_same_card_set_after_changes(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest;
const a={id:'d20',purpose:'plan_approval',status:'open',question:'Start?',identity:{revision:1},files:[],failed:[],context:{}};
live={...live,language:'ko',decisions:[a],plan_approval:a,nodes:[{...live.nodes[0],contract:{goal:'Before'}}]};api.applyView(live);
live={...live,plan_approval:{...a,id:'d21',identity:{revision:2}},nodes:[{...live.nodes[0],contract:{goal:'After'}}]};live.decisions=[live.plan_approval];api.applyView(live);
matchMedia=()=>({matches:false});api.recordGraphRead();api.graphRead.add('work');api.graphRead.add('_run_checks');api.updateUnreadMarks();
const remaining=api.unreadCards();assert(remaining.some(n=>n.id==='work'));const reason=api.graphReadReason();
for(const card of get('map').querySelectorAll('.node-card')){const marked=!!card.querySelector('.unread-mark');assert.equal(marked,remaining.some(n=>n.id===card.dataset.node));if(marked){assert(reason.includes(card.querySelector('.node-title').textContent));assert.equal(card.querySelector('.unread-mark').textContent,'아직 읽지 않음');}}
assert(!reason.includes('열지 않은'));
""")
