import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bootstrap',ROOT/'bootstrap.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class Installer(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.home=self.root/'home'
 def tearDown(self):self.tmp.cleanup()
 def apply(self):return b.install(ROOT,self.home,True,b.install(ROOT,self.home))
 def test_clean_idempotent_rollback_restore(self):
  self.assertFalse(self.home.exists());self.assertGreater(self.apply()['changed'],0);self.assertEqual(self.apply()['changed'],0);self.assertTrue(b.doctor(ROOT,self.home)['integrity_ok']);b.rollback(self.home);self.assertFalse((self.home/'AGENTS.md').exists());self.apply();self.assertTrue(b.doctor(ROOT,self.home)['integrity_ok'])
 def test_preserves_unmanaged_bytes(self):
  self.home.mkdir();p=self.home/'AGENTS.md';p.write_bytes(b'Original user guidance\n');self.apply();self.assertTrue(p.read_bytes().startswith(b'Original user guidance\n'));b.rollback(self.home);self.assertEqual(p.read_bytes(),b'Original user guidance\n')
 def test_stale_plan_and_missing_plan_refused(self):
  plan=b.install(ROOT,self.home);self.home.mkdir();p=self.home/'AGENTS.md';p.write_text('concurrent')
  with self.assertRaises(ValueError):b.install(ROOT,self.home,True,plan)
  with self.assertRaises(ValueError):b.install(ROOT,self.home,True)
  self.assertEqual(p.read_text(),'concurrent');self.assertFalse((self.home/'team-coordination-install.json').exists())
 def test_tamper_symlink_traversal_and_unknown_file(self):
  bundle=self.root/'bundle';shutil.copytree(ROOT,bundle,ignore=shutil.ignore_patterns('.git','dist','__pycache__'));(bundle/'payload/team-coordination/policy.json').write_text('tamper')
  with self.assertRaises(ValueError):b.install(bundle,self.home)
  with self.assertRaises(ValueError):b.safe(self.root,'../escape')
  self.home.mkdir();outside=self.root/'outside';outside.mkdir();(self.home/'skills').symlink_to(outside)
  with self.assertRaises(ValueError):b.install(ROOT,self.home)
  (self.home/'skills').unlink();unknown=self.home/'skills/team-coordination/unknown';unknown.parent.mkdir(parents=True);unknown.write_text('preserve')
  with self.assertRaises(ValueError):b.install(ROOT,self.home)
 def test_rollback_conflict_and_write_gap(self):
  self.apply();p=self.home/'AGENTS.md';original=p.read_bytes();p.write_bytes(original+b'concurrent')
  with self.assertRaises(ValueError):b.rollback(self.home)
  p.write_bytes(original);b.rollback(self.home);self.assertFalse(p.exists())
if __name__=='__main__':unittest.main()
