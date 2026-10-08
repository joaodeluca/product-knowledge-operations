"""Recovery boundaries: private history, immutable publications, untrusted ZIP."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backup
import engine as e
import intake

class BackupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name).resolve()
  self.d=e.Desk(self.root/'original/content.sqlite3',self.root/'original/releases')
  self.p=self.d.create_project({'name':'Own help','purpose':'PRIVATE_PURPOSE'})
  data={'original_owned':True,'limits':'Own example','files':[{'name':'start.md','content':'# Start\nOwn text.'}]}
  v=intake.preview(self.d,self.p['id'],data,self.p['revision']);self.p=intake.apply(self.d,self.p['id'],dict(data,plan=v['plan'],confirmed=True),self.p['revision'])
  self.aid=self.p['articles'][0]['id']; self.sid=self.p['sources'][0]['id']
  actor={'kind':'ai_assisted','label':'INTERNAL_REVIEWER'}
  self.p=self.d.create_procedure(self.p['id'],{'title':'Own task','steps':'Own steps','source_ids':[self.sid]},self.p['revision'])
  self.p=self.d.review_article(self.p['id'],self.aid,{'actor':actor,'note':'INTERNAL_NOTE'},self.p['revision'])
  self.p=self.d.publish(self.p['id'],{'actor':actor,'note':'INTERNAL_RELEASE_NOTE'},self.p['revision'])
  self.rid=self.p['active_release_id'];self.public=self.d.export_release(self.p['id'],self.rid)
  update={'article_id':self.aid,'original_owned':True,'files':[{'name':'start.md','content':'# Start\nChanged own text.'}]}
  v=intake.update_preview(self.d,self.p['id'],update,self.p['revision']);self.p=intake.update_apply(self.d,self.p['id'],dict(update,plan=v['plan'],confirmed=True),self.p['revision'])
  self.other=self.d.create_project({'name':'Second'})
  (self.root/'original/session.json').write_text('SESSION_SECRET')
  (self.root/'original/orphan.txt').write_text('ORPHAN_SECRET')
  self.raw=backup.export(self.d);self.path=self.root/'private.zip';self.path.write_bytes(self.raw)
 def tearDown(self): self.tmp.cleanup()
 def entries(self):
  with zipfile.ZipFile(io.BytesIO(self.raw)) as z:return {n:z.read(n) for n in z.namelist()}
 def write(self,entries,rehash=False):
  if rehash:
   m=json.loads(entries['backup.json']);m['files']=[{'path':n,'bytes':len(b),'sha256':e._hash(b)} for n,b in entries.items() if n!='backup.json'];entries['backup.json']=e._json(m).encode()
  with zipfile.ZipFile(self.path,'w') as z:
   for n,b in entries.items():z.writestr(n,b)
 def refused(self):
  with self.assertRaises(e.DeskError):backup.restore(self.path,self.root/'restored')
  self.assertFalse((self.root/'restored').exists())
 def test_private_roundtrip_preserves_stale_reviews_snapshots_all_projects_and_public_bytes(self):
  entries=self.entries();joined=b'\n'.join(entries.values());self.assertIn(b'PRIVATE_PURPOSE',joined);self.assertIn(b'INTERNAL_NOTE',joined)
  for marker in (b'SESSION_SECRET',b'ORPHAN_SECRET',b'SQLite format 3'):self.assertNotIn(marker,joined)
  self.assertEqual(self.p,self.d.project(self.p['id']))
  result=backup.restore(self.path,self.root/'restored');self.assertEqual(result['counts']['projects'],2)
  restored=e.Desk(self.root/'restored/content.sqlite3',self.root/'restored/releases')
  self.assertEqual(restored.projects(),self.d.projects());self.assertEqual(restored.project(self.p['id']),self.p)
  self.assertEqual(restored.snapshots(self.p['id'],self.sid),self.d.snapshots(self.p['id'],self.sid))
  self.assertEqual(restored.export_release(self.p['id'],self.rid),self.public)
  self.assertEqual(restored.project(self.p['id'])['articles'][0]['review']['status'],'stale')
  self.assertFalse((self.root/'restored/session.json').exists())
  with zipfile.ZipFile(io.BytesIO(self.public)) as z:self.assertNotIn(b'PRIVATE_PURPOSE',b'\n'.join(z.read(n) for n in z.namelist()))
 def test_existing_destination_and_symlink_are_never_changed(self):
  dest=self.root/'restored';dest.mkdir();sentinel=dest/'keep';sentinel.write_text('keep')
  with self.assertRaises(e.DeskError):backup.restore(self.path,dest)
  self.assertEqual(list(dest.iterdir()),[sentinel]);self.assertEqual(sentinel.read_text(),'keep')
  link=self.root/'link';link.symlink_to(dest)
  with self.assertRaises(e.DeskError):backup.restore(self.path,link)
 def test_corruption_traversal_duplicate_symlink_and_extra_entries(self):
  entries=self.entries();entries['records.json']+=b' ';self.write(entries);self.refused()
  for name in ('../escape','/absolute','releases/../escape','extra.txt'):
   entries=self.entries();entries[name]=b'x';self.write(entries,rehash=True);self.refused()
  self.path.write_bytes(self.raw)
  with zipfile.ZipFile(self.path,'a') as z:
   import warnings
   with warnings.catch_warnings():warnings.simplefilter('ignore');z.writestr('records.json',b'{}')
  self.refused()
  self.path.write_bytes(self.raw)
  with zipfile.ZipFile(self.path,'a') as z:
   info=zipfile.ZipInfo('link');info.create_system=3;info.external_attr=0o120777<<16;z.writestr(info,'target')
  self.refused()
 def test_unsupported_schema_duplicate_json_and_broken_links(self):
  entries=self.entries();m=json.loads(entries['backup.json']);m['version']=2;entries['backup.json']=e._json(m).encode();self.write(entries);self.refused()
  entries=self.entries();entries['records.json']=b'{"projects":[],"projects":[]}';self.write(entries,True);self.refused()
  entries=self.entries();rows=json.loads(entries['records.json']);rows['articles'][0]['project_id']='p_'+'0'*32;entries['records.json']=e._json(rows).encode();self.write(entries,True);self.refused()
  entries=self.entries();rows=json.loads(entries['records.json']);rows['snapshots'][0]['content']='changed';entries['records.json']=e._json(rows).encode();self.write(entries,True);self.refused()
 def test_limits_and_missing_release_fail_without_partial_adoption(self):
  with patch.object(backup,'MAX_BYTES',100):self.refused()
  with patch.object(backup,'MAX_ENTRIES',2):self.refused()
  (self.d.releases_path/self.p['id']/self.rid/'index.html').unlink()
  with self.assertRaises(e.DeskError):backup.export(self.d)
 def test_interrupted_install_never_adopts_partial_destination(self):
  original=backup.os.rename;calls=[]
  def interrupted(a,b):
   calls.append(str(a))
   if len(calls)==2:raise OSError('simulated interruption')
   return original(a,b)
  with patch.object(backup.os,'rename',side_effect=interrupted):
   with self.assertRaises(OSError):backup.restore(self.path,self.root/'restored')
  self.assertTrue((self.root/'restored/content.sqlite3').is_file());self.assertFalse((self.root/'restored/workspace.json').exists())
  import serve
  with self.assertRaises(ValueError):serve.Server(self.root/'restored')
  backup.restore(self.path,self.root/'retry-new')
