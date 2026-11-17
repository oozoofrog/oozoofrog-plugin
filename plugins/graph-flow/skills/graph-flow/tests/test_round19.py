"""Owner regressions: explanation first, complete card text, stable graph topology."""
import unittest
import test_page
import test_round17


class Owner19Tests(unittest.TestCase):
    run_controller = test_page.PageTests.run_controller
    run_dom = test_page.PageTests.run_dom
    js = test_round17.PresentationTests.js

    def test_u1_summary_goal_review_question_fallback(self):
        self.js(r"""
const nodes=[{id:'a',title:'안내'}];
for(const kind of ['work','review','decision','goal']) {
 const n={kind,summary:'한국어 요약',goal:'English goal',question:'질문?',target:'a',lens:['정확성','접근성']};
 assert.equal(nodeSentence(n,nodes,'ko'),'한국어 요약');
 delete n.summary;assert.equal(nodeSentence(n,nodes,'ko'),'English goal');delete n.goal;
 if(kind==='review')assert.equal(nodeSentence(n,nodes,'ko'),'안내을(를) 정확성 · 접근성의 눈으로 검토해요');
 if(kind==='decision')assert.equal(nodeSentence(n,nodes,'ko'),'질문?');
}
assert.equal(nodeSentence({runLevel:true,goal:'goal'},nodes,'ko'),STRINGS.ko.runChecksAfter);
""")

    def test_u1_first_text_after_title_for_every_kind_and_mode(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest, base=structuredClone(live);
for(const mode of ['plan','running','done','changed','old'])for(const kind of ['work','review','decision'])for(const summary of ['한국어 요약','']) {
 const n={...base.nodes[0],kind,summary,goal:'English goal',contract:{},planned_checks:[],title:'선택한 카드',status:mode==='done'?'passed':'running'};
 live={...base,nodes:[n],decisions:[],plan_approval:mode==='plan'||mode==='changed'?{id:'d20',status:'open',question:'시작?',identity:{revision:mode==='changed'?2:1}}:null,complete:mode==='done'};
 api.applyView(live);api.selectNode('work');if(get('panel').hidden)api.selectNode('work');
 const intro=get('panel').querySelector('.panel-intro');assert.equal(intro.children[0].textContent,n.title);assert.equal(intro.children[1].textContent,summary||n.goal);
 assert.equal(intro.children[1].tagName,'p');assert(!intro.querySelector('details'));
 api.selectNode('_run_checks');assert.equal(get('panel').querySelector('.node-sentence').textContent,'After all work is finished, check that the combined result meets the plan’s requirements.');
}
""")

    def test_u2_card_has_full_summary_check_and_remaining_count(self):
        self.run_dom(r"""
const api=globalThis.surfaceTest;
const n={...live.nodes[0],kind:'work',title:'가'.repeat(60),summary:'나'.repeat(300),planned_checks:[0,1,2,3].map(i=>({type:'cmd',title:'다'.repeat(120),run:'true',id:'c'+i}))};
const c=api.nodeCard(n);assert(c.textContent.includes(n.title));assert(c.textContent.includes(n.summary));assert(c.textContent.includes(n.planned_checks[0].title));assert(c.textContent.includes('3 more checks'));assert(!c.textContent.includes('…'));
const compact=api.nodeCard(n,false,'overview');assert.equal(compact.querySelector('.node-title').textContent,n.title);assert(!compact.querySelector('.node-essentials'));
""")

    def test_u2_measured_heights_preserve_order_and_dependencies(self):
        self.js(r"""
const ns=[{id:'a',title:'가'.repeat(60)},{id:'b',title:'나'.repeat(60)},{id:'r',kind:'review',target:'a'}],es=[{from:'a',to:'b'},{from:'r',to:'a',relation:'reviews'}];
for(const level of ['detail','overview']){
 const before=layeredLayout(ns,es,[],true,{level}),after=layeredLayout(ns,es,[],true,{level,measure:n=>n.id==='a'?900:600});
 assert.deepEqual(after.order,before.order);assert.deepEqual(after.routes.map(r=>[r.from,r.to]),forwardEdges(es).map(r=>[r.from,r.to]));
 assert(after.positions.a.height>=900);assert(after.positions.b.height>=600);
 const chain=Array.from({length:10},(_,i)=>({id:'n'+i,title:'가'.repeat(60)})),edges=chain.slice(1).map((n,i)=>({from:chain[i].id,to:n.id}));
 const wrapped=layeredLayout(chain,edges,[],true,{level,wrapLongChains:true,measure:()=>300});
 const a=wrapped.positions.n0,b=wrapped.positions.n7;assert(b.x>=a.x+a.width||b.y>=a.y+a.height);
}
""")
