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
