import sys,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
class Overlay(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.home=Path(self.temp.name).resolve();self.agents=self.home/'AGENTS.md';self.before=b'Original user guidance\n<!-- team-coordination:v3:begin -->\nOriginal managed instructions\n<!-- team-coordination:v3:end -->\n';self.agents.write_bytes(self.before);(self.home/'team-coordination-install.json').write_text('{"version":"0.3.0","preserve":true}\n');self.payload={'schema':1,'requested_scope':'all_existing_and_future_projects','roles':{'leader':{'model':'gpt-6-astra','reasoning_effort':'ultra','service_tier':'fast'},'advisor':{'model':'gpt-6-astra','reasoning_effort':'ultra','service_tier':'fast'},'core':{'model':'gpt-6.1-sol'},'support':{'model':'gpt-6-luna'}},'adoption':'pending_explicit_owner_safe_boundary','execution_authorized':False}
 def tearDown(self):self.temp.cleanup()
 def test_plan_readonly_then_idempotent_apply_and_exact_rollback(self):
  import profile_overlay as p
  old=(self.home/'team-coordination-install.json').read_bytes();plan=p.plan(self.home,self.payload);self.assertEqual(self.before,self.agents.read_bytes());self.assertEqual(2,len(plan['changes']));self.assertEqual(2,p.apply(self.home,self.payload)['changed']);self.assertEqual(0,p.apply(self.home,self.payload)['changed']);self.assertTrue(p.doctor(self.home)['integrity_ok']);self.assertEqual(old,(self.home/'team-coordination-install.json').read_bytes());p.rollback(self.home);self.assertEqual(self.before,self.agents.read_bytes());self.assertFalse((self.home/'team-coordination-desired-profiles.json').exists())
 def test_block_is_outside_original_managed_region(self):
  import profile_overlay as p
  p.apply(self.home,self.payload);text=self.agents.read_text();self.assertGreater(text.index('desired-profile:v1:begin'),text.index('team-coordination:v3:end'))
 def test_concurrent_edit_refuses_rollback_without_overwrite(self):
  import profile_overlay as p
  p.apply(self.home,self.payload);self.agents.write_bytes(self.agents.read_bytes()+b'concurrent');before=self.agents.read_bytes()
  with self.assertRaises(p.OverlayError):p.rollback(self.home)
  self.assertEqual(before,self.agents.read_bytes())
 def test_unknown_existing_profile_preserved(self):
  import profile_overlay as p
  target=self.home/'team-coordination-desired-profiles.json';target.write_text('{"custom":true}')
  with self.assertRaises(p.OverlayError):p.apply(self.home,self.payload)
  self.assertEqual('{"custom":true}',target.read_text())
 def test_ultrafast_or_claimed_effective_profile_is_rejected(self):
  import profile_overlay as p
  self.payload['roles']['leader']['service_tier']='ultrafast'
  with self.assertRaises(p.OverlayError):p.plan(self.home,self.payload)
 def test_legacy_journal_change_refuses_apply(self):
  import profile_overlay as p
  p.apply(self.home,self.payload);(self.home/'team-coordination-install.json').write_text('changed')
  with self.assertRaises(p.OverlayError):p.apply(self.home,self.payload)
 def test_tampered_journal_paths_schema_and_endpoint_hashes_refused(self):
  import profile_overlay as p,copy
  p.apply(self.home,self.payload);journal=self.home/p.JOURNAL;original=json.loads(journal.read_text());before=self.agents.read_bytes()
  variants=[]
  for path in ('../outside','/tmp/outside',p.PROFILE):
   value=copy.deepcopy(original);value['changes'][0]['path']=path;variants.append(value)
  value=copy.deepcopy(original);value['schema']=99;variants.append(value)
  value=copy.deepcopy(original);value['changes'][0]['before_sha256']='0'*64;variants.append(value)
  for value in variants:
   journal.write_text(json.dumps(value))
   with self.assertRaises(p.OverlayError):p.rollback(self.home)
   self.assertEqual(before,self.agents.read_bytes())
  journal.write_text(json.dumps(original));p.rollback(self.home)
if __name__=='__main__':unittest.main()
