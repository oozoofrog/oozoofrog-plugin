"""Complete individual check lines, with current observation marks."""
import unittest
import test_page

class CheckLines20Tests(unittest.TestCase):
    run_dom=test_page.PageTests.run_dom
    run_controller=test_page.PageTests.run_controller
    def test_r5_separate_complete_titles_and_current_result_marks(self):
        self.run_dom(r"""
const n={...live.nodes[0],planned_checks:[{id:'a',type:'cmd',title:'검사 하나',result:'passed'},{id:'b',type:'cmd',title:'검사 둘',result:'failed'},{id:'c',type:'cmd',title:'검사 셋'}, {id:'d',type:'cmd',title:'검사 넷'}]};
const card=globalThis.surfaceTest.nodeCard(n),lines=card.querySelectorAll('.card-check');assert.equal(lines.length,3);assert(lines[0].textContent.includes('✓'));assert(lines[1].textContent.includes('✕'));assert(lines[2].textContent.includes('○'));assert(card.textContent.includes('1 more checks'));
for(let i=0;i<3;i++){assert(lines[i].textContent.includes(n.planned_checks[i].title));assert(!lines[i].textContent.includes(n.planned_checks[(i+1)%3].title));}
""")

    def test_r5_results_belong_to_the_current_attempt(self):
        import os
        from pathlib import Path
        import tempfile
        from unittest import mock
        from test_questions20 import OUTPUT, fixtures
        from graphflow import server, store
        with tempfile.TemporaryDirectory(dir=OUTPUT) as scratch:
            data=fixtures.build(Path(scratch),'check-lines')
            with mock.patch.dict(os.environ,{'GF_HOME':data['home'],'GF_NO_OPEN':'1'},clear=True):
                project=Path(data['project']).resolve()
                p,events,state=store.snapshot(project/'.graph-flow/runs'/data['run'])
                node=server._view(p,state,events,project)['nodes'][0]
                self.assertEqual(node['check_results'],{'text':'passed','restore':'failed'})
                self.assertNotIn('readable',node['check_results'])
