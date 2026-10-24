import sys,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
CATALOG=[{'model':'gpt-6-astra','supportedReasoningEfforts':[{'reasoningEffort':'ultra'}],'serviceTiers':[{'id':'priority','name':'Fast','description':'catalogue declared'}]}]
NORMAL=[{'model':'gpt-6-astra','supportedReasoningEfforts':[{'reasoningEffort':'high'}],'defaultServiceTier':'priority','serviceTiers':[{'id':'priority','name':'Fast','description':'synthetic additional tier'}]}]
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
  for role in ['leader','advisor']:self.assertEqual({'model':'gpt-6-astra','reasoning_effort':'high','service_tier':'normal'},p.role_request(policy,role))
  for role in ['core','reviewer']:self.assertEqual({'model':'gpt-6.1-sol','reasoning_effort':'high','service_tier':'normal'},p.role_request(policy,role))
  self.assertEqual({'model':'gpt-6-luna','reasoning_effort':'medium','service_tier':'normal'},p.role_request(policy,'support'))
 def test_normal_uses_explicit_standard_despite_priority_catalogue_default(self):
  import profile_defaults as p
  params,resolved=p.start_parameters(NORMAL,{'model':'gpt-6-astra','reasoning_effort':'high','service_tier':'normal'})
  self.assertNotIn('serviceTier',params);self.assertEqual('default',resolved['wire_id']);self.assertEqual('high',params['config']['model_reasoning_effort']);self.assertEqual('normal',resolved['requested_label']);self.assertEqual('resolved_from_protocol',resolved['status'])
 def test_normal_does_not_require_an_additional_tier_or_use_guessed_aliases(self):
  import profile_defaults as p
  for options in (None,[],[{'id':'priority','name':'Fast'}],[{'id':'default','name':'Standard'}],[{'id':None,'name':'Normal'}],[{'id':'','name':'Normal'}],[{'id':'a','name':'Normal'},{'id':'b','name':'Normal'}]):
   with self.subTest(options=options):
    entry=dict(NORMAL[0],serviceTiers=options,defaultServiceTier=None,additionalSpeedTiers=['fast'])
    params,resolution=p.start_parameters([entry],{'model':'gpt-6-astra','reasoning_effort':'high','service_tier':'normal'})
    self.assertNotIn('serviceTier',params);self.assertEqual('default',resolution['wire_id'])
 def test_normal_turn_local_and_settings_clear_have_distinct_scope(self):
  import profile_defaults as p
  resolution=p.resolve_service_tier(NORMAL,'gpt-6-astra','normal')
  self.assertEqual({'serviceTierForTurn':'default'},p.tier_parameters(resolution,'turn/start'))
  self.assertEqual({},p.tier_parameters(resolution,'thread/start'))
  self.assertEqual({},p.tier_parameters(resolution,'thread/resume'))
  self.assertEqual({'serviceTier':None},p.tier_parameters(resolution,'thread/settings/update'))
  self.assertEqual({},p.tier_parameters(p.resolve_service_tier(NORMAL,'gpt-6-astra',None),'thread/settings/update'))
 def test_null_configured_receipt_remains_unknown_even_after_standard_request(self):
  import profile_defaults as p
  observation=p.configured({'thread':{'id':'owned'},'serviceTier':None},'thread/start')
  self.assertEqual('unavailable',observation['status']);self.assertFalse(p.tier_matches(observation,p.resolve_service_tier(NORMAL,'gpt-6-astra','normal')))
 def test_normal_rejects_unknown_protocol_and_stale_nonstandard_resolution(self):
  import profile_defaults as p
  class RPC:tier_contract=p.CURRENT_TIER_CONTRACT
  resolution=p.resolve_service_tier(NORMAL,'gpt-6-astra','normal')
  with self.assertRaises(p.ProfileError):p.require_tier_contract(object(),resolution)
  with self.assertRaises(p.ProfileError):p.require_tier_contract(RPC(),dict(resolution,wire_id='priority'))
 def test_normal_missing_model_or_reasoning_support_refused(self):
  import profile_defaults as p
  for requested in ({'model':'other','reasoning_effort':'high','service_tier':'normal'},{'model':'gpt-6-astra','reasoning_effort':'ultra','service_tier':'normal'}):
   with self.assertRaises(p.ProfileError):p.start_parameters(NORMAL,requested)
 def test_normal_requires_exact_tier_model_effort_receipt(self):
  import profile_defaults as p
  resolution=p.resolve_service_tier(NORMAL,'gpt-6-astra','normal');receipt={'status':'observed','wire_service_tier':'default','model':'gpt-6-astra','reasoning_effort':'high'}
  self.assertTrue(p.tier_matches(receipt,resolution,'gpt-6-astra','high'))
  for field,value in [('wire_service_tier','priority'),('wire_service_tier',None),('model','gpt-6.1-sol'),('reasoning_effort','ultra'),('status','unavailable')]:
   with self.subTest(field=field,value=value):self.assertFalse(p.tier_matches(dict(receipt,**{field:value}),resolution,'gpt-6-astra','high'))
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
