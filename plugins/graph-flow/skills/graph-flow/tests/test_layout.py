"""Geometric invariants of the DOM-free layered router, including the scratch ro plan."""
import json
import pathlib
import shutil
import subprocess
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('node'), 'Node is required to execute the JavaScript layout')
class LayoutTests(unittest.TestCase):
    def check_graph(self, data):
        script=r'''
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(process.argv[2],'utf8');
const {layeredLayout,roundedRoute}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const data=JSON.parse(process.argv[3]);
for(const level of ['detail','overview']) {
const options={level};
const layout=layeredLayout(data.nodes,data.edges,[],true,options);
const portGap=level==='overview'?8:14;
const overlap=(a,b)=>a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y;
const segments=r=>r.points.slice(1).map((p,i)=>[r.points[i],p]);
const enters=(a,b,c)=>a.x===b.x?a.x>c.x&&a.x<c.x+c.width&&Math.max(a.y,b.y)>c.y&&Math.min(a.y,b.y)<c.y+c.height:a.y>c.y&&a.y<c.y+c.height&&Math.max(a.x,b.x)>c.x&&Math.min(a.x,b.x)<c.x+c.width;
const rects=[...layout.cardRects,...layout.chips];
rects.forEach((a,i)=>rects.slice(i+1).forEach(b=>assert(!overlap(a,b),'rectangles overlap')));
assert.equal(layout.routes.length,data.edges.length);
for(const r of layout.routes){
 const a=layout.positions[r.from],b=layout.positions[r.to];
 assert.equal(r.start.x,a.x+a.width);assert.equal(r.end.x,b.x);
 assert(r.end.y>b.y&&r.end.y<b.y+b.height,'arrowhead touches the target edge');
 assert.deepEqual(r.points.at(-1),r.end);
 assert(r.points.at(-2).x<r.end.x,'arrowhead approaches in the direction of meaning');
 assert(roundedRoute(r.points).endsWith(`L${r.end.x} ${r.end.y}`));
 for(const [p,q] of segments(r)){
   assert(p.x===q.x||p.y===q.y,'all segments must be orthogonal');
   for(const c of layout.cardRects)assert(!enters(p,q,c),'route enters card '+c.id+' '+JSON.stringify(r));
 }
}
// No shared trunks are used: even relations between the same pair have separate ports.
layout.routes.forEach((r,i)=>layout.routes.slice(i+1).forEach(other=>{
 if(r.from===other.from)assert(Math.abs(r.start.y-other.start.y)>=portGap,'outgoing tracks need separate ports');
 if(r.to===other.to)assert(Math.abs(r.end.y-other.end.y)>=portGap,'incoming tracks need separate ports');
 for(const [a,b] of segments(r))for(const [c,d] of segments(other)){
  if(a.x===b.x&&c.x===d.x&&a.x===c.x)assert(Math.min(Math.max(a.y,b.y),Math.max(c.y,d.y))<=Math.max(Math.min(a.y,b.y),Math.min(c.y,d.y)),'vertical overlap');
  if(a.y===b.y&&c.y===d.y&&a.y===c.y)assert(Math.min(Math.max(a.x,b.x),Math.max(c.x,d.x))<=Math.max(Math.min(a.x,b.x),Math.min(c.x,d.x)),'horizontal overlap');
 }
}));
assert.deepEqual(layout,layeredLayout(data.nodes,data.edges,[],true,options),'determinism');
for(const n of data.nodes)assert.deepEqual(layout.cardRects,layeredLayout(data.nodes,data.edges,[{id:'d1',node:n.id}],true,{...options,expanded:n.id,heights:{[n.id]:999},maxHeight:10}).cardRects,'selection, evidence and viewport cannot change geometry');
const changed=data.nodes.map(n=>({...n,status:'running',attempts:3,laps:['returned','returned','current']}));
assert.deepEqual(layout.cardRects,layeredLayout(changed,data.edges.map(e=>({...e,gate:'returned'})),[],true,options).cardRects,'status polling cannot move cards');
for(const layer of layout.layers)assert.equal(new Set(layer.map(id=>layout.positions[id].width)).size,1);
if(level==='overview')assert.equal(layout.chips.length,0);
}
'''
        result=subprocess.run([shutil.which('node'),'--input-type=module','-',str(ROOT/'scripts/graphflow/page.js'),json.dumps(data)],input=script,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def graph(self, ids, pairs):
        return {'nodes':[{'id':n,'title':n,'kind':'work'} for n in ids], 'edges':[{'from':a,'to':b,'label':'결과','relation':'hands_over'} for a,b in pairs]}

    def test_chain(self):
        self.check_graph(self.graph('abcd',[('a','b'),('b','c'),('c','d')]))

    def test_diamond(self):
        self.check_graph(self.graph('abcd',[('a','b'),('a','c'),('b','d'),('c','d')]))

    def test_fan_out_five(self):
        self.check_graph(self.graph('abcdef',[('a',n) for n in 'bcdef']))

    def test_fan_in_five(self):
        self.check_graph(self.graph('abcdef',[(n,'f') for n in 'abcde']))

    def test_span_three_layers(self):
        self.check_graph(self.graph('abcd',[('a','b'),('b','c'),('c','d'),('a','d')]))

    def test_two_relations_one_pair(self):
        data=self.graph('ab',[('a','b')]);data['nodes'][1].update(kind='review',target='a')
        data['edges'].append({'from':'b','to':'a','relation':'reviews'})
        self.check_graph(data)

    def test_real_ro_plan(self):
        self.check_graph(json.loads((ROOT/'tests/fixtures/real_layout.json').read_text()))

    def test_dense_layers(self):
        self.check_graph(self.graph('abcdefghi',[(a,b) for layer in [('abc','def'),('def','ghi')] for a in layer[0] for b in layer[1]]))

    def test_large_fans_keep_ports_available_at_both_levels(self):
        ids=['n'+str(i) for i in range(30)]
        self.check_graph(self.graph(ids,[(ids[0],n) for n in ids[1:]]))
        self.check_graph(self.graph(ids,[(n,ids[-1]) for n in ids[:-1]]))

    def test_long_chain_reuses_ports_in_unrelated_channels(self):
        ids=['n'+str(i) for i in range(60)]
        self.check_graph(self.graph(ids,list(zip(ids,ids[1:]))))
