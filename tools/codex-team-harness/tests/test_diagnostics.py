"""Retained diagnostic integrity, without resource/count quota assumptions."""
import sys,unittest
from pathlib import Path
import test_observation_followup as fixtures
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'));import harness as h

class Diagnostics(unittest.TestCase):
 setUp=fixtures.Followup.setUp
 tearDown=fixtures.Followup.tearDown
 ev=fixtures.Followup.ev
 ack=fixtures.Followup.ack
 method=fixtures.Followup.method
 approve=fixtures.Followup.approve
 request=fixtures.Followup.request
 def test_original_grant_duplicate_is_historical_conflicting_payload_refused(self):
  e=next(x['event']for x in self.s['history']if x['event']['op']=='diagnostic_grant');self.assertEqual(self.s,h.apply(self.s,e,self.root))
  with self.assertRaises(h.Invalid):h.apply(self.s,dict(e,evidence_goal='changed'),self.root)
 def test_tampered_original_snapshot_is_refused(self):
  self.s['harness']['diagnostics']['first']['original_task']['purpose']='tampered'
  with self.assertRaises(h.Invalid):self.ev('change',instruction='must not hide historical corruption')
 def test_path_alias_drift_is_not_new_permission(self):
  (self.root/'collector.py').symlink_to(self.root/'outside')
  with self.assertRaises(h.Invalid):self.ev('change',instruction='must not hide alias drift')
 def test_not_executed_closes_observation_without_synthetic_charge(self):
  self.s=h.apply(self.s,self.request(),self.root);self.ack();self.ev('begin',task='task',member='owner',run='bits-run',diagnostic_request_id='bits');self.ev('finish',run='bits-run',outcome='not_executed',evidence='observed no turn dispatched')
  self.assertEqual('closed',self.s['harness']['diagnostics']['bits']['state']);self.assertNotIn('charged',self.s['harness']['runs']['bits-run']);self.assertEqual('fail',self.s['tasks']['task']['reviews'][-1]['verdict'])
 def test_uncertainty_requires_supported_terminal_reconcile(self):
  self.s=h.apply(self.s,self.request(),self.root);self.ack();self.ev('begin',task='task',member='owner',run='bits-run',diagnostic_request_id='bits');self.ev('finish',run='bits-run',outcome='uncertain',evidence='transport lost')
  self.assertEqual('uncertain',self.s['harness']['diagnostics']['bits']['state']);self.ev('reconcile',run='bits-run',outcome='failed',evidence='supported terminal receipt');self.assertEqual('closed',self.s['harness']['diagnostics']['bits']['state'])
 def test_fresh_evidence_cannot_be_replaced_by_new_id(self):
  e=self.request();Path(e['method']['collector']['path']).write_text('changed after review')
  with self.assertRaises(h.Invalid):h.apply(self.s,e,self.root)

if __name__=='__main__':unittest.main()
