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
