import sys,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
CATALOG=[{'model':'gpt-6-astra','supportedReasoningEfforts':[{'reasoningEffort':'ultra'}],'serviceTiers':[{'id':'priority','name':'Fast','description':'catalogue declared'}]}]
class Profiles(unittest.TestCase):
 def test_profile_api_exists(self):self.assertTrue((ROOT/'payload/team-coordination/scripts/profile_defaults.py').exists(),'separate profile helper missing')
 def test_fast_label_resolves_only_catalogue_declared_wire(self):
  import profile_defaults as p
  r=p.resolve_service_tier(CATALOG,'gpt-6-astra','fast');self.assertEqual('fast',r['requested_label']);self.assertEqual('priority',r['wire_id']);self.assertIn('catalog_entry_sha256',r)
 def test_ultrafast_unknown_missing_and_deprecated_only_are_refused(self):
  import profile_defaults as p
  for label in ['ultrafast','priority','unknown']:
   with self.assertRaises(p.ProfileError):p.resolve_service_tier(CATALOG,'gpt-6-astra',label)
  with self.assertRaises(p.ProfileError):p.resolve_service_tier([{'model':'gpt-6-astra','additionalSpeedTiers':['fast']}],'gpt-6-astra','fast')
 def test_policy_default_roles_are_distinct(self):
  import profile_defaults as p
  policy=json.loads((ROOT/'payload/team-coordination/policy.json').read_text())
  for role in ['leader','advisor']:self.assertEqual({'model':'gpt-6-astra','reasoning_effort':'ultra','service_tier':'fast'},p.role_request(policy,role))
  self.assertEqual('gpt-6.1-sol',p.role_request(policy,'core')['model']);self.assertEqual('gpt-6-luna',p.role_request(policy,'support')['model'])
 def test_configured_receipt_and_thread_read_missing_are_not_execution(self):
  import profile_defaults as p
  response={'model':'gpt-6-astra','reasoningEffort':'ultra','serviceTier':'priority','thread':{'id':'owned'}}
  receipt=p.configured(response,'thread/start');self.assertEqual('priority',receipt['wire_service_tier']);self.assertEqual('configured',receipt['scope']);self.assertEqual('unavailable',p.execution_unknown()['status'])
  missing=p.configured({'thread':{'id':'owned'}},'thread/read');self.assertEqual('unavailable',missing['status']);self.assertIsNone(missing['wire_service_tier'])
 def test_settings_receipt_is_bound_to_exact_thread(self):
  import profile_defaults as p
  r=p.settings({'threadId':'owned','threadSettings':{'model':'gpt-6-astra','effort':'ultra','serviceTier':'priority'}},'owned');self.assertEqual('priority',r['wire_service_tier']);self.assertEqual('ultra',r['reasoning_effort'])
  with self.assertRaises(p.ProfileError):p.settings({'threadId':'other','threadSettings':{'serviceTier':'priority'}},'owned')
 def test_start_parameters_do_not_conflate_effort_and_tier(self):
  import profile_defaults as p
  params,resolved=p.start_parameters(CATALOG,{'model':'gpt-6-astra','reasoning_effort':'ultra','service_tier':'fast'})
  self.assertEqual('gpt-6-astra',params['model']);self.assertEqual('ultra',params['config']['model_reasoning_effort']);self.assertEqual('priority',params['serviceTier']);self.assertEqual('fast',resolved['requested_label'])
 def test_missing_or_substituted_tier_never_matches(self):
  import profile_defaults as p
  resolved=p.resolve_service_tier(CATALOG,'gpt-6-astra','fast')
  self.assertFalse(p.tier_matches({'status':'unavailable','wire_service_tier':None},resolved));self.assertFalse(p.tier_matches({'status':'observed','wire_service_tier':'default'},resolved))
  self.assertTrue(p.tier_matches({'status':'observed','wire_service_tier':'priority'},resolved))
if __name__=='__main__':unittest.main()
