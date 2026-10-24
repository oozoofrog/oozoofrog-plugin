"""Provider-free real CLI recovery and actual 48-coefficient Float32 conversion.

All identities, permissions, approvals, ACKs and coefficients are synthetic.
"""
import base64,hashlib,json,subprocess,sys,unittest
from pathlib import Path
import test_observation_followup as fixtures
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'));import harness as h

class CLIObservation(unittest.TestCase):
 setUp=fixtures.Followup.setUp
 tearDown=fixtures.Followup.tearDown
 ev=fixtures.Followup.ev
 ack=fixtures.Followup.ack
 method=fixtures.Followup.method
 approve=fixtures.Followup.approve
 request=fixtures.Followup.request
 def cli(self,*args):
  command=[sys.executable,'-I','-S','-B',str(ROOT/'run.py'),'harness','--state',str(self.path),*args];r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True);self.assertEqual(0,r.returncode,r.stdout+r.stderr);return json.loads(r.stdout)if r.stdout.strip()else None
 def apply_cli(self,e):
  event=self.root/'event.json';event.write_text(json.dumps(e));self.cli('apply','--event',str(event));self.s=json.loads(self.path.read_text())
 def ack_cli(self):
  packet=self.cli('packet','--member','owner');self.apply_cli({'op':'ack','member':'owner','revision':packet['revision'],'epoch':packet['epoch'],'digest':h.digest(packet)});return packet
 def workflow(self):
  self.s['harness'].update(schema=1,policy_hash='synthetic-old-contract',budget=100000,spent=100000,context_limit=16000,review_limit=2)
  prior=self.s['harness']['runs']['diag0'];prior.update(reserve=5000,charged=5000,observed_usage=None,measurement='reserved_missing_usage');self.s['harness']['runs']={'old-'+str(i):dict(task='task',member='owner',state='completed',reserve=5000,charged=5000,observed_usage=None,measurement='reserved_missing_usage',evidence='Synthetic historical terminal')for i in range(19)};self.s['harness']['runs']['diag0']=prior;self.s['harness']['diagnostics']['first']['request']['max_reserve']=5000
  h.save(self.path,self.s);raw=self.path.read_bytes();e=dict(op='contract_migrate',request_id='cli-migration',project='finish sample',project_root=str(self.root),source_sha256=h.digest(self.s),source_raw_sha256=hashlib.sha256(raw).hexdigest(),policy_hash=h.digest(h.effective_contract()),reason='Synthetic user-authorized removal of internal resource/count limits',requester='leader',approvals=str(self.approvals));self.approve(e);self.apply_cli(e)
  self.assertEqual(raw,base64.b64decode(self.s['harness']['legacy_archives']['cli-migration']['source_bytes_base64']));self.assertEqual(20,h.usage_summary(self.s)['unknown_runs']);self.assertEqual(7,len(self.s['tasks']['task']['paths']));self.assertEqual('fail',self.s['tasks']['task']['reviews'][0]['verdict'])
  converter=Path(self.new['collector']['path']);converter.write_text('''import json,struct,sys
values=json.load(open(sys.argv[1]))
assert len(values)==48
rows=[]
for i,value in enumerate(values):
 before=struct.pack('>f',value)
 float32=struct.unpack('>f',before)[0]
 after=struct.pack('>f',float32)
 rows.append({'index':i,'before_bits':before.hex(),'after_bits':after.hex()})
json.dump({'schema':'float32-48-pre-post-v1','actor_provenance':'synthetic fixture only','coefficients':rows,'reported_usage':None,'product_accepted':False},open(sys.argv[2],'w'))
''');self.new['collector']=h.ledger.evidence(str(converter));self.apply_cli(self.request());self.ack_cli();self.apply_cli(dict(op='begin',task='task',member='owner',run='bits-run',diagnostic_request_id='bits'))
  output=self.root/'coefficients.json';r=subprocess.run([sys.executable,'-I','-S','-B',str(converter),self.new['input']['evidence']['path'],str(output)],capture_output=True,text=True);self.assertEqual(0,r.returncode,r.stderr);self.apply_cli(dict(op='finish',run='bits-run',outcome='completed',evidence=str(output)))
  packet=self.cli('packet','--member','owner');result=json.loads(output.read_text());self.assertEqual(48,len(result['coefficients']));self.assertEqual('3eaaaaab',result['coefficients'][0]['before_bits']);self.assertEqual('3eaaaaab',result['coefficients'][47]['after_bits']);self.assertEqual('fail',self.s['tasks']['task']['reviews'][-1]['verdict']);self.assertFalse(result['product_accepted'])
  return {'provenance':'Real local CLI and conversion; synthetic actors/authority/ACKs, no provider or real project execution','legacy_raw_sha256':hashlib.sha256(raw).hexdigest(),'original_fail_count':len(self.s['tasks']['task']['reviews']),'product_state':self.s['tasks']['task']['state'],'packet':packet,'result':result,'purpose_summary':{'goal':packet['goal'],'purpose':packet['tasks'][0]['purpose'],'completion_criteria':packet['tasks'][0]['context'],'role':packet['role'],'owner':packet['task_obligations']['task']['owner'],'next_action':packet['next_action'],'failure_cause':json.loads(self.cause.read_text())['reason'],'alternative_method':self.new['schema'],'evidence':packet['diagnostics']['bits']['result']['evidence']}}
 def test_actual_cli_migrates_history_and_records_48_bits_without_product_pass(self):
  example=self.workflow();self.assertEqual('finish sample',example['purpose_summary']['goal']);self.assertIn('Original FAIL',example['purpose_summary']['completion_criteria']);self.assertEqual('owner',example['purpose_summary']['owner']);self.assertEqual('float32-48-pre-post-v1',example['purpose_summary']['alternative_method'])

if __name__=='__main__':unittest.main()
