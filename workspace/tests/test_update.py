"""File maintenance: atomicity, immutable releases and explicit review boundaries."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import engine as e
import intake

ACTOR={'kind':'ai_assisted','label':'test-local'}
class UpdateTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();r=Path(self.t.name).resolve();self.d=e.Desk(r/'db',r/'releases');self.p=self.d.create_project({'name':'Central'})
  self.original='# Início\nVeja [ajuda](Ajuda.md).\n'
  data={'original_owned':True,'limits':'Somente conteúdo próprio.','files':[{'name':'Inicio.md','content':self.original},{'name':'Ajuda.md','content':'# Ajuda\nPassos próprios.\n'}]}
  v=intake.preview(self.d,self.p['id'],data,self.p['revision']);self.p=intake.apply(self.d,self.p['id'],dict(data,plan=v['plan'],confirmed=True),self.p['revision'])
  self.aid=self.p['articles'][0]['id'];self.sid=self.p['sources'][0]['id']
  self.data={'article_id':self.aid,'original_owned':True,'files':[{'name':'Inicio.md','content':'# Início atualizado\nVeja [ajuda](Ajuda.md).\nAgora com passos novos.\n'}]}
 def tearDown(self):self.t.cleanup()
 def preview(self,data=None):return intake.update_preview(self.d,self.p['id'],data or self.data,self.p['revision'])
 def apply(self,v=None,data=None):
  data=data or self.data;v=v or self.preview(data);return intake.update_apply(self.d,self.p['id'],dict(data,plan=v['plan'],confirmed=True),self.p['revision'])
 def test_change_invalidates_review_retains_source_and_article_and_old_release(self):
  for a in self.p['articles']:self.p=self.d.review_article(self.p['id'],a['id'],{'actor':ACTOR,'note':'Texto próprio conferido'},self.p['revision'])
  self.p=self.d.publish(self.p['id'],{'actor':ACTOR,'note':'Original','public_fields_reviewed':True},self.p['revision']);rid=self.p['active_release_id'];old=self.d.export_release(self.p['id'],rid)
  before=self.p;v=self.preview();self.assertEqual(before,self.d.project(self.p['id']));self.assertIn('(ajuda.html)',v['after']['markdown']);self.assertIn('+Agora',v['diffs']['markdown'])
  self.p=self.apply(v);self.assertEqual(self.p['articles'][0]['review']['status'],'stale');self.assertEqual(self.p['articles'][1]['review']['status'],'current');self.assertEqual(self.p['articles'][0]['slug'],'inicio')
  self.assertEqual(self.p['history'][-1]['details']['previous_article']['markdown'],before['articles'][0]['markdown']);self.assertIsNotNone(self.p['history'][-1]['details']['previous_review'])
  snapshots=self.d.snapshots(self.p['id'],self.sid);self.assertEqual([x['content'] for x in snapshots],[self.original,self.data['files'][0]['content']])
  with self.assertRaises(e.DeskError):self.d.publish(self.p['id'],{'actor':ACTOR,'note':'Changed','public_fields_reviewed':True},self.p['revision'])
  self.assertEqual(old,self.d.export_release(self.p['id'],rid))
  self.p=self.d.review_article(self.p['id'],self.aid,{'actor':ACTOR,'note':'Alteração conferida'},self.p['revision']);self.p=self.d.publish(self.p['id'],{'actor':ACTOR,'note':'Changed','public_fields_reviewed':True},self.p['revision']);self.assertNotEqual(rid,self.p['active_release_id'])
 def test_identical_file_is_noop_including_snapshots_history(self):
  data=dict(self.data,files=[{'name':'Inicio.md','content':self.original}]);v=self.preview(data);self.assertFalse(v['changed']);self.assertFalse(v['can_apply']);self.assertEqual(self.apply(v,data),self.p);self.assertEqual(len(self.d.snapshots(self.p['id'],self.sid)),1)
 def test_tamper_and_replay_rejected(self):
  v=self.preview();changed=dict(self.data,files=[{'name':'Inicio.md','content':'# Outro\nMudou'}])
  with self.assertRaises(e.DeskError):self.apply(v,changed)
  old=self.p;self.p=self.apply(v)
  with self.assertRaises(e.DeskError):intake.update_apply(self.d,self.p['id'],dict(self.data,plan=v['plan'],confirmed=True),old['revision'])
  self.assertEqual(len(self.d.snapshots(self.p['id'],self.sid)),2)
 def test_final_write_failure_rolls_back_source_snapshot_and_article(self):
  v=self.preview()
  with patch.object(self.d,'_event',side_effect=RuntimeError('late failure')):
   with self.assertRaises(RuntimeError):self.apply(v)
  self.assertEqual(self.d.project(self.p['id']),self.p);self.assertEqual(len(self.d.snapshots(self.p['id'],self.sid)),1)
 def test_wrong_filename_cross_project_linkage_and_unsafe_content_rejected(self):
  with self.assertRaises(e.DeskError):self.preview(dict(self.data,files=[{'name':'Other.md','content':'text'}]))
  other=self.d.create_project({'name':'Outro'})
  with self.assertRaises(e.DeskError):intake.update_preview(self.d,other['id'],self.data,other['revision'])
  for text in ['# A\n[missing](missing.md)', '# A\n![image](x.png)']:
   data=dict(self.data,files=[{'name':'Inicio.md','content':text}]);v=self.preview(data);self.assertFalse(v['can_apply'])
   with self.assertRaises(e.DeskError):self.apply(v,data)
  self.assertEqual(self.d.project(self.p['id']),self.p)
  a=self.p['articles'][0];self.p=self.d.update_article(self.p['id'],self.aid,dict(a,source_ids=[self.p['sources'][1]['id']]),self.p['revision'])
  with self.assertRaises(e.DeskError):self.preview()
 def test_existing_manual_article_changes_explicitly_visible_and_preserved(self):
  a=self.p['articles'][0];self.p=self.d.update_article(self.p['id'],self.aid,dict(a,markdown='Edição manual própria.'),self.p['revision']);v=self.preview();self.assertEqual(v['before']['markdown'],'Edição manual própria.');self.p=self.apply(v);self.assertEqual(self.p['history'][-1]['details']['previous_article']['markdown'],'Edição manual própria.')
 def test_shared_source_dependents_listed_and_stale(self):
  a=self.p['articles'][1];self.p=self.d.update_article(self.p['id'],a['id'],dict(a,source_ids=[self.sid]),self.p['revision']);self.p=self.d.review_article(self.p['id'],a['id'],{'actor':ACTOR,'note':'Shared'},self.p['revision']);v=self.preview();self.assertEqual(len(v['affected_articles']),2);self.p=self.apply(v);self.assertEqual(self.p['articles'][1]['review']['status'],'stale')
if __name__=='__main__':unittest.main()
