"""Cross-product contracts for gate-owned consent and executable plans."""
import copy
import itertools
import json
import unittest
from types import SimpleNamespace
import test_gate as f
from graphflow import checks, cli, core, decisions, gate, graph, learn, plan, server, state, store
from human_support import human_answer

PURPOSES = ('free','hold','human_check','lane3','node','trajectory','plan_approval')
ROLES = ('leader','worker','reviewer')
KINDS = ('direction','information','review','authorization')

class GateRules(unittest.TestCase):
    def test_every_rule_purpose_role_kind_agent_question_is_inert(self):
        for rule,purpose,role,kind,text in itertools.product(range(1,8),PURPOSES,ROLES,KINDS,('exact','OK?')):
            case=f.EvaluateTests();case.setUp()
            case.node['checks'].append({'id':'human','type':'human','prompt':'Accept?'})
            results=[]
            if rule in (1,2): results=[f.result(failed=True)];case.st['attempts']=3 if rule==2 else 1
            elif rule==3:case.node['checks'].append(dict(f.HOST))
            elif rule==4:
                case.node['checks'].append(dict(f.HOST));case.st['checks']['ide']={'loop':f.result('host',failed=True,id=8)}
            elif rule==5:case.lane(2);case.st['trajectory_clean']=False
            elif rule==7:case.node['checks']=[]
            baseline=case.evaluate(results);self.assertEqual(baseline['rule'],'R%d'%rule)
            request=gate._ask(case.node,case.st,purpose,check='human' if purpose=='human_check' else None,kind=kind)
            request.pop('issuer');request.update(actor={'role':role},status='answered',verified=True,outcome='approved',stale=False)
            if text!='exact':request['question']=text
            case.state['decisions']['agent']=request
            with self.subTest(rule=rule,purpose=purpose,role=role,kind=kind,text=text):
                self.assertEqual(case.evaluate(results),baseline)
                request.update(status='open',verified=False);self.assertEqual(case.evaluate(results),baseline)

    def test_only_current_evidence_ids_and_hashes_count(self):
        case=f.EvaluateTests();case.setUp();case.lane(2)
        case.st['reviews'][0].update(id=30,verdict='fail',findings=[{'text':'Audit log deleted'}])
        asked=case.evaluate()['asks'][0];self.assertEqual(asked['purpose'],'hold')
        self.assertEqual(asked['evidence']['records'][0]['id'],30)
        self.assertEqual(len(asked['evidence']['records'][0]['sha256']),64)
        case.state['decisions']['gate']=dict(asked,status='answered',verified=True,outcome='approved')
        self.assertEqual(case.evaluate()['verdict'],'pass')
        for field,value in [('id',31),('findings',[{'text':'New failure'}])]:
            saved=copy.deepcopy(case.st['reviews']);case.st['reviews'][0][field]=value
            self.assertEqual(case.evaluate()['verdict'],'hold');self.assertTrue(case.evaluate()['asks']);case.st['reviews']=saved

class PlanRules(unittest.TestCase):
    def test_every_check_type_field_and_node_kind(self):
        specific={'cmd':{'run':'true','cwd':'.','timeout_s':1,'from_constraint':'c','added':'date'},'scope':{},'cites':{},'host':{'tool':'IDE','expect':'green'},'human':{'prompt':'Accept?','context':{'why':'Needs eyes'}}}
        values=dict(id='check',type='cmd',title='Label',unknown='ignored?')
        for extra in specific.values():values.update(extra)
        for node_kind,check_kind,field in itertools.product(('work','review','decision'),specific,values):
            check=dict(id='check',type=check_kind,**specific[check_kind]);check[field]=check_kind if field=='type' else values[field]
            node={'work':f.work,'review':f.review,'decision':f.decision}[node_kind]();node['checks']=[check]
            if node_kind=='work':node['checks'].append({'id':'machine','type':'cmd','run':'true'})
            nodes=[f.work(),node] if node_kind=='review' else [node]
            problems=plan.validate({'schema_version':1,'goal':'test','nodes':nodes})
            compatible=check_kind in {'work':('cmd','scope','host','human'),'review':('cmd','cites','host','human'),'decision':()}[node_kind]
            allowed=field in {'id','type','title'}|set(specific[check_kind])
            with self.subTest(node=node_kind,check=check_kind,field=field):
                self.assertEqual(not problems,compatible and allowed,problems)
                if not allowed:self.assertTrue(any(field in p['message'] for p in problems))
                if compatible and allowed:
                    rendered=server._planned_check(check,node)
                    self.assertEqual(bool(rendered['command']),check_kind=='cmd');self.assertEqual(bool(rendered.get('prompt')),check_kind=='human')

    def test_node_kind_and_run_fields_reject_unenforced_contracts(self):
        for kind,field in itertools.product(('work','review','decision'),('target','lens','question','decision_kind','grade','max_attempts')):
            node={'work':f.work,'review':f.review,'decision':f.decision}[kind]()
            node[field]={'target':'w','decision_kind':'authorization','grade':'daily','max_attempts':2}.get(field,'text')
            doc={'schema_version':1,'goal':'test','nodes':[f.work(),node] if kind=='review' else [node]}
            problems=plan.validate(doc)
            if field not in {'work':('grade','max_attempts'),'review':('target','lens','grade','max_attempts'),'decision':('question','decision_kind')}[kind]:
                self.assertTrue(any(field in p['message'] for p in problems),(kind,field,problems))
        for field in ('run','cwd','timeout_s','tool','prompt','unknown'):
            self.assertTrue(any(field in p['message'] for p in plan.validate({'schema_version':1,'goal':'test','nodes':[f.work()],field:'ignored'})))

    def test_every_node_and_run_field_has_an_enforced_or_presentation_consumer(self):
        # Labels are intentionally instructions, not machine claims (plan.md).
        labels={'title','summary','goal','reads','context','requirement'}
        enforced={'id','kind','needs','owns','outputs','checks','lane','effective_lane','grade','max_attempts','target','lens','question','decision_kind'}
        values=dict(title='Readable title',summary='Summary',goal='Goal',reads=['README.md'],context={'why':'Reason'},requirement='R',needs=[],owns=[],outputs=['artifact'],checks=[],lane=1,effective_lane=1,grade='daily',max_attempts=2,target='w',lens='correctness',question='Accept?',decision_kind='authorization',unknown='ignored')
        for kind,field in itertools.product(('work','review','decision'),values):
            node={'work':f.work,'review':f.review,'decision':f.decision}[kind]()
            value=values[field]
            if field=='checks':value=node.get('checks',[])
            if field in ('lane','effective_lane'):value=node['lane']
            node[field]=value
            doc={'schema_version':1,'goal':'test','requirements':[{'id':'R','text':'Required'}],'nodes':[f.work(),node] if kind=='review' else [node]}
            accepted=not plan.validate(doc)
            allowed=field in labels|enforced and (field not in ('target','lens') or kind=='review') and (field not in ('question','decision_kind') or kind=='decision') and (field not in ('grade','max_attempts') or kind!='decision')
            with self.subTest(kind=kind,field=field):
                self.assertEqual(accepted,allowed,plan.validate(doc))
                if accepted:
                    normalized=plan.normalize(doc)[0]['nodes'][-1]
                    self.assertEqual(normalized[field],value)
                    self.assertIn(field,plan.node_contract(normalized))
        run_values=dict(schema_version=1,goal='test',title='Title',summary='Summary',context={'why':'Reason'},requirements=[{'id':'R','text':'Required'}],tags=['python'],integration_checks=[dict(f.CMD)],promoted_checks=[dict(f.CMD)],constraints=[{'id':'c','text':'Instruction'}],nodes=[f.work()])
        for field,value in run_values.items():
            doc={'schema_version':1,'goal':'test','nodes':[f.work()],field:value}
            with self.subTest(run_field=field):
                self.assertEqual(plan.validate(doc),[])
                self.assertEqual(plan.normalize(doc)[0][field],value) if field!='nodes' else None

    def test_only_accept_reject_nodes_can_release_dependents(self):
        for kind in KINDS:
            d=f.decision(decision_kind=kind,outputs=['answer']);w=f.work(needs=[{'from':'d','artifact':'answer'}])
            self.assertEqual(not plan.validate({'schema_version':1,'goal':'test','nodes':[d,w]}),kind in ('review','authorization'))

class LiveRules(f.GateCase):
    def test_every_agent_role_can_only_ask_free_direction_or_information(self):
        for role,purpose,kind in itertools.product(ROLES,PURPOSES,KINDS):
            actor=dict(f.ACTOR,role=role,node='w')
            with self.subTest(role=role,purpose=purpose,kind=kind):
                if purpose=='free' and kind in ('direction','information'):
                    self.assertNotIn('issuer',decisions.ask(self.run,kind,'Question?','w',None,purpose,None,actor))
                else:
                    with self.assertRaises(core.GFError):decisions.ask(self.run,kind,'Question?','w',None,purpose,None,actor)

    def test_review_command_runs_and_rejects(self):
        self.set_plan([f.work(),f.review(checks=[{'id':'run','type':'cmd','run':'printf evidence > scan.out; exit 1'}])])
        self.assign('w','a');self.start();self.submit();self.assign('v','b');self.start('v')
        checks.review_submit(self.run,'v','pass',[],f.ACTOR)
        self.assertEqual(self.gate('v')['verdict'],'reject');self.assertEqual((self.repo/'scan.out').read_text(),'evidence')

    def test_integration_outputs_never_enter_submitted_scope(self):
        self.set_plan([f.work(lane=2,checks=[dict(f.CMD),{'id':'eyes','type':'human','prompt':'Accept?'}]),f.review()],integration=[{'id':'integration','type':'cmd','run':'printf generated > outside.txt'}])
        self.assign('w','a');self.start();self.write('w.txt','changed');self.submit();self.assign('v','b');self.start('v')
        checks.review_submit(self.run,'v','pass',[],f.ACTOR);self.gate('v')
        outcome=self.gate();self.assertEqual(outcome['verdict'],'needs_approval')
        human_answer(self.run,outcome['asks'][0],'approved','Read result')
        self.assertEqual(self.gate()['verdict'],'pass');self.assertTrue((self.repo/'outside.txt').exists())

    def test_moved_project_repost_approve_with_answered_human_history(self):
        self.set_plan([f.work(checks=[dict(f.CMD),{'id':'eyes','type':'human','prompt':'Accept?'}]),f.work('x',needs=[{'from':'w','artifact':'w.txt'}])])
        self.start();self.write('w.txt','changed');self.submit();human_answer(self.run,self.gate()['asks'][0],'approved','Read result')
        self.assertEqual(self.gate()['verdict'],'pass');before=core.key_fingerprint();self.commit()
        old=self.repo;self.repo=self.root/'moved';old.rename(self.repo);self.run=self.repo/'.graph-flow/runs/gate-test'
        self.assertTrue(self.derived()['run']['location_mismatch'])
        file=self.root/'plan.json';file.write_text(json.dumps(self.plan))
        posted=cli._set_plan(SimpleNamespace(run=self.run,file=str(file),open=False),f.ACTOR)
        human_answer(self.run,posted['decision'],'approved','Moved project confirmed')
        self.assertFalse(self.derived()['run']['location_mismatch']);self.assertEqual(core.key_fingerprint(),before)
        self.assertIn('x',graph.ready(self.plan,self.derived()));self.start('x');self.submit('x');self.assertEqual(self.gate('x')['verdict'],'pass')

    def test_checks_file_drift_names_file_and_field(self):
        for field,value in [('cwd','../..'),('unknown','x'),('timeout_s',-1)]:
            (self.repo/'.graph-flow/checks.json').write_text(json.dumps({'schema_version':1,'checks':[dict(id='saved',type='cmd',run='true',**{field:value})]}))
            with self.assertRaises(core.GFError) as error:learn.fixed_checks(self.repo)
            self.assertIn('.graph-flow/checks.json',str(error.exception));self.assertIn(field,str(error.exception))

    def test_sent_back_node_not_ready_and_has_recovery_message(self):
        self.set_plan([f.decision()]);outcome=self.gate('d');human_answer(self.run,outcome['asks'][0],'revision_requested','Do not proceed')
        outcome=self.gate('d');self.assertEqual(outcome['verdict'],'hold');self.assertIn('re-post',outcome['message']);self.assertEqual(graph.ready(self.plan,self.derived()),[])

    def test_repin_uses_plan_language_and_tool_attribution(self):
        decisions.repin(self.run,f.HUMAN);self.assertEqual(state.plan_approval(self.derived())['question'],'Start with this plan?');self.assertEqual(store.events(self.run)[-1]['actor']['role'],'tool')

class PresentationRules(unittest.TestCase):
    def test_supplied_run_contracts_are_not_silently_replaced(self):
        saved={'id':'saved','type':'cmd','run':'exit 1'}
        other={'id':'other','type':'cmd','run':'true'}
        self.assertEqual(cli._merge_plan_records([saved],[other],'promoted_checks'),[saved,other])
        with self.assertRaises(core.GFError):cli._merge_plan_records([saved],[dict(saved,run='true')],'promoted_checks')

    def test_derived_lane_cannot_be_overridden(self):
        for kind in ('work','review','decision'):
            node={'work':f.work,'review':f.review,'decision':f.decision}[kind]()
            node['effective_lane']=99
            doc={'schema_version':1,'goal':'test','nodes':[f.work(),node] if kind=='review' else [node]}
            self.assertTrue(any('effective_lane' in p['message'] for p in plan.validate(doc)))

    def test_title_snapping_and_field_differences(self):
        import base64, shutil, subprocess
        executable=shutil.which('node')
        if not executable:self.skipTest('node unavailable')
        page=server.PAGE_PATH.with_name('page.js').read_bytes()
        url='data:text/javascript;base64,'+base64.b64encode(page).decode()
        source="""import assert from 'node:assert/strict';
import {snapTitleOffset,contractDiff,offscreenDirection} from %s;
const titles=[[20,180],[240,400],[470,630]];
for(let width of [200,300,500])for(let position=0;position<700-width;position+=7){
 const next=snapTitleOffset(position,width,700-width,titles);
 for(const [a,b] of titles){assert(!(a<next-.01&&b>next+.01));assert(!(a<next+width-.01&&b>next+width+.01));}
}
assert.equal(offscreenDirection({x:-1,y:-1,width:10,height:10},100,100),'offLeft');
const diff=contractDiff({checks:[{run:'true',timeout_s:5}]},{checks:[{run:'false',timeout_s:9}]});
assert.equal(diff.length,2);assert(diff.some(x=>x.before===5&&x.after===9));
""" % json.dumps(url)
        result=subprocess.run([executable,'--input-type=module','-e',source],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr[-1500:])

    def test_own_file_execution_marker_does_not_confuse_reading_with_execution(self):
        for command,cwd,owns,expected in [
            ('make test','evil',['evil/Makefile'],True),
            ('make test','.',['Makefile'],True),
            ('python3 test.py','.',['test.py'],True),
            ('./test.sh','.',['test.sh'],True),
            ('grep -q ready guide.txt','.',['guide.txt'],False),
            ('test -s a.txt','.',['a.txt'],False),
            ('true','tests',['tests/'],True),
        ]:
            with self.subTest(command=command,cwd=cwd,owns=owns):
                self.assertEqual(server._planned_check({'type':'cmd','run':command,'cwd':cwd},{'owns':owns})['runs_own_files'],expected)
