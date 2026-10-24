"""No-follow ownership inventory and side-effect-free compatibility checks."""
import hashlib,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'payload/team-coordination/scripts'))
import external_handoff as x,harness as h

class SymlinkBaseline(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.claim=self.root/'evidence';self.claim.mkdir()
 def tearDown(self):self.tmp.cleanup()
 def test_swiftpm_link_is_literal_metadata_and_not_a_second_directory_tree(self):
  target=self.claim/'out/Products/Debug';target.mkdir(parents=True);(target/'binary').write_bytes(b'actual bytes');link=self.claim/'debug';link.symlink_to('out/Products/Debug')
  value=x.baseline([str(self.claim)])[str(self.claim)];entry=value['entries']['debug']
  self.assertEqual('symlink',entry['kind']);self.assertEqual(link.lstat().st_mode&0o7777,entry['mode']);self.assertEqual('out/Products/Debug',entry['target']);self.assertIn('identity',entry)
  self.assertNotIn('debug/binary',value['entries']);self.assertEqual(hashlib.sha256(b'actual bytes').hexdigest(),value['entries']['out/Products/Debug/binary']['sha256'])
 def test_dangling_absolute_contained_and_chain_are_opaque(self):
  (self.claim/'dangling').symlink_to('missing');(self.claim/'absolute').symlink_to(self.claim/'missing');(self.claim/'chain').symlink_to('dangling');(self.claim/'cycle').symlink_to('cycle')
  with mock.patch.object(Path,'resolve',side_effect=AssertionError('No target resolution')):
   entries=x.baseline([str(self.claim)])[str(self.claim)]['entries']
  self.assertEqual('missing',entries['dangling']['target']);self.assertEqual('dangling',entries['chain']['target'])
 def test_link_target_mode_replacement_addition_and_deletion_change_baseline(self):
  link=self.claim/'link';link.symlink_to('one');before=x.baseline([str(self.claim)])
  link.unlink();link.symlink_to('two');self.assertNotEqual(before,x.baseline([str(self.claim)]))
  link.unlink();link.write_text('one');self.assertNotEqual(before,x.baseline([str(self.claim)]))
  link.unlink();self.assertNotEqual(before,x.baseline([str(self.claim)]))
  link.symlink_to('one');self.assertNotEqual(before,x.baseline([str(self.claim)]))
 def test_escape_root_alias_and_aliased_ancestor_are_refused(self):
  link=self.claim/'escape';link.symlink_to('../outside')
  with self.assertRaisesRegex(h.Invalid,'escape'):x.baseline([str(self.claim)])
  link.unlink();link.symlink_to(self.root/'outside')
  with self.assertRaisesRegex(h.Invalid,'escape'):x.baseline([str(self.claim)])
  alias=self.root/'alias';alias.symlink_to(self.claim)
  for path in (alias,alias/'child'):
   with self.assertRaises(h.Invalid):x.baseline([str(path)])
 def test_alias_ancestor_is_rejected_before_any_lookup_below_it(self):
  alias=self.root/'alias';alias.symlink_to(self.claim);original=Path.is_symlink
  def checked(path):
   if alias in path.parents:raise AssertionError('Metadata lookup followed aliased ancestor')
   return original(path)
  with mock.patch.object(Path,'is_symlink',checked):
   with self.assertRaises(h.Invalid):x.baseline([str(alias/'child')])
 def test_fifo_socket_and_other_special_entries_are_rejected_without_open(self):
  fifo=self.claim/'fifo';os.mkfifo(fifo)
  with self.assertRaisesRegex(h.Invalid,'Special'):x.baseline([str(self.claim)])
 def test_file_replaced_by_symlink_before_open_is_never_followed(self):
  file=self.claim/'file';file.write_text('inside');outside=self.root/'outside';outside.write_text('private outside');original=os.open
  def race(name,*args,**kwargs):
   if name=='file':file.unlink();file.symlink_to(outside)
   return original(name,*args,**kwargs)
  with mock.patch.object(x.os,'open',side_effect=race):
   with self.assertRaises((h.Invalid,OSError)):x.baseline([str(self.claim)])
 def test_directory_replaced_by_symlink_before_open_is_never_descended(self):
  directory=self.claim/'dir';directory.mkdir();outside=self.root/'outside';outside.mkdir();(outside/'secret').write_text('private');original=os.open
  def race(name,*args,**kwargs):
   if name=='dir':directory.rmdir();directory.symlink_to(outside)
   return original(name,*args,**kwargs)
  with mock.patch.object(x.os,'open',side_effect=race):
   with self.assertRaises((h.Invalid,OSError)):x.baseline([str(self.claim)])
 def test_file_content_and_mode_changes_and_empty_directory_are_recorded(self):
  file=self.claim/'file';file.write_text('before');(self.claim/'empty').mkdir();before=x.baseline([str(self.claim)])
  file.write_text('after');self.assertNotEqual(before,x.baseline([str(self.claim)]));file.write_text('before');file.chmod(0o700);self.assertNotEqual(before,x.baseline([str(self.claim)]))
  self.assertEqual('directory',before[str(self.claim)]['entries']['empty']['kind'])
 def test_link_mode_change_and_escaping_target_prefix_are_detected(self):
  link=self.claim/'link';link.symlink_to('missing');before=x.baseline([str(self.claim)])
  if hasattr(os,'lchmod'):
   os.lchmod(link,0o700);self.assertNotEqual(before,x.baseline([str(self.claim)]))
  (self.claim/'escape').symlink_to('../outside');link.unlink();link.symlink_to('escape/child')
  with self.assertRaisesRegex(h.Invalid,'escape'):x.baseline([str(self.claim)])
 def test_special_types_are_refused_before_open(self):
  import stat
  file=self.claim/'special';file.write_text('placeholder');original=os.stat
  for kind in (stat.S_IFSOCK,stat.S_IFCHR,stat.S_IFBLK):
   def metadata(name,*args,**kwargs):
    value=original(name,*args,**kwargs)
    if name=='special':value=os.stat_result((kind|0o600,*tuple(value)[1:]))
    return value
   with mock.patch.object(x.os,'stat',side_effect=metadata):
    with self.assertRaisesRegex(h.Invalid,'Special'):x.baseline([str(self.claim)])
 def test_link_replaced_during_readlink_is_rejected(self):
  link=self.claim/'link';link.symlink_to('one');original=os.readlink
  def race(*args,**kwargs):
   value=original(*args,**kwargs);link.unlink();link.symlink_to('two');return value
  with mock.patch.object(x.os,'readlink',side_effect=race):
   with self.assertRaisesRegex(h.Invalid,'changed'):x.baseline([str(self.claim)])
 def test_full_twelve_claim_preflight_is_readonly_and_reports_all_types(self):
  admin=self.root/'.codex-team';admin.mkdir();state=admin/'state.json';state.write_text('{}');(admin/'state.json.lock').write_bytes(b'');(admin/'retained-fail.json').write_text('{"verdict":"fail"}')
  claims=[str(admin),str(self.claim)]
  (self.claim/'empty').mkdir();(self.claim/'debug').symlink_to('missing')
  for index in range(10):
   p=self.root/('consumer-'+str(index));p.write_text('source '+str(index));claims.append(str(p))
  before=state.read_bytes();before_names=sorted(p.relative_to(self.root).as_posix()for p in self.root.rglob('*'))
  result=x.preflight(claims,state_path=str(state))
  self.assertTrue(result['ok']);self.assertEqual(12,result['claims']);self.assertEqual(1,result['types']['symlink']);self.assertTrue(result['management_guard_prepared']);self.assertEqual([],result['failures'])
  self.assertEqual(before,state.read_bytes());self.assertEqual(before_names,sorted(p.relative_to(self.root).as_posix()for p in self.root.rglob('*')))
 def test_preflight_collects_all_failed_claims(self):
  (self.claim/'escape').symlink_to('../outside');other=self.root/'other';other.mkdir();os.mkfifo(other/'fifo')
  result=x.preflight([str(self.claim),str(other)])
  self.assertFalse(result['ok']);self.assertEqual(2,len(result['failures']))

if __name__=='__main__':unittest.main()
