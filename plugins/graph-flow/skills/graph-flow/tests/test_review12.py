"""Round-twelve page recovery and readable-state contracts."""
import json
import os
import subprocess
import unittest

import test_server as fixture
from graphflow import core, decisions, server, state, store
from test_review11 import NODE


class PageRecoveryTests(unittest.TestCase):
    setUp = fixture.ServerTests.setUp
    request = fixture.ServerTests.request
    stop_server = fixture.ServerTests.stop_server
    git = fixture.ServerTests.git

    def test_recovery_requires_page_origin_token_confirmation_and_displayed_identity(self):
        run = self.runs[0]
        before = (self.home/'human.key').read_bytes()
        current, events, derived = server._snapshot(run)
        displayed = decisions.recovery_identity(derived)
        body = {'project': str(self.projects[0]), 'run':run.name, 'confirm':True, 'displayed':displayed}
        headers = {'Origin':'http://127.0.0.1:%d'%self.port, 'Sec-Fetch-Site':'same-origin'}
        self.assertEqual(self.request('POST','/api/key/repin',body,headers,token=False)[0],401)
        self.assertEqual(self.request('POST','/api/key/repin',body)[0],403)
        self.assertEqual(self.request('POST','/api/key/repin',dict(body,role='leader'),headers)[0],400)
        self.assertEqual(self.request('POST','/api/key/repin',dict(body,confirm=False),headers)[0],400)
        self.assertEqual(self.request('POST','/api/key/repin',dict(body,displayed={}),headers)[0],409)
        self.assertEqual((self.home/'human.key').read_bytes(), before)
        self.assertEqual(self.request('POST','/api/key/repin',body,headers)[0],200)
        self.assertNotEqual((self.home/'human.key').read_bytes(), before)
        _, _, derived = server._snapshot(run)
        self.assertEqual(state.plan_approval(derived)['status'], 'open')
        self.assertFalse(derived['run']['key_mismatch'])
        self.assertEqual(self.request('POST','/api/key/repin',body,headers)[0],409)

    def test_page_shows_recorded_title_when_plan_is_tampered(self):
        run=self.runs[0]
        with store.transaction(run) as tx:
            event=store._last_plan_set(tx.events)
        # Fixture events predate title recording; add a genuine revised plan event.
        with store.transaction(run) as tx:
            rev, sha=tx.write_plan(tx.plan)
            tx.append('plan.set',{'revision':rev,'plan_sha256':sha,'plan_title':'Real run title','fingerprints':{}},fixture.ACTOR)
        path=run/'plans'/('%04d.json'%rev)
        path.write_text('{}')
        current,events,derived=server._snapshot(run)
        self.assertEqual(server._view(current,derived,events,self.projects[0])['title'],'Real run title')


class ReadableStateTests(unittest.TestCase):
    @unittest.skipUnless(NODE, 'node unavailable')
    def test_clipped_titles_and_content_sized_cards_and_preapproval_status(self):
        page=server.PAGE_PATH.with_name('page.js').read_text()
        import base64
        url='data:text/javascript;base64,'+base64.b64encode(page.encode()).decode()
        code="""import assert from 'node:assert/strict';
import {offscreenDirection,intersectsViewport,detailCardHeight,displayState,statusGlyph} from %s;
assert.equal(offscreenDirection({x:-1,y:20,width:100,height:20},500,300),'offLeft');
assert.equal(intersectsViewport({x:-1,y:20,width:100,height:20},500,300),true);
assert.equal(offscreenDirection({x:401,y:20,width:100,height:20},500,300),'offRight');
assert.equal(offscreenDirection({x:400,y:20,width:100,height:20},500,300),null);
assert(detailCardHeight({})<detailCardHeight({planned_checks:[{}],deliverables:['a']}));
assert.equal(displayState({status:'submitted',preapproval_submission:true}),'preapprovalSubmitted');
assert.equal(statusGlyph('preapprovalSubmitted'),'⇥');
""" % json.dumps(url)
        result=subprocess.run([NODE,'--input-type=module','-e',code],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr[-2000:])
        css=server.PAGE_PATH.read_text()
        self.assertNotIn('.edge-clipped .node-card>*{visibility:hidden}',css)
        self.assertNotIn('.node-card.unused{border-style:dashed',css)
        self.assertIn("const direction=offscreenDirection(",page)
        self.assertIn("if(horizontal&&titleVisibility(rect,w,h))visible++",page)
