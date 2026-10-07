"""New atomic intake boundaries; public search serialization."""
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import engine as e
import intake
import reader

class IntakeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();r=Path(self.temp.name).resolve();self.d=e.Desk(r/'db',r/'releases');self.p=self.d.create_project({'name':'Minha central'})
  self.data={'original_owned':True,'limits':'Texto próprio sem execução externa.','files':[{'name':'Início.md','content':'# Início\r\n\r\nVeja [configuração](Configuração.md).\r\n'},{'name':'Configuração.md','content':'# Configuração\n\nEscolha o fuso horário.\n'}]}
 def tearDown(self):self.temp.cleanup()
 def preview(self,data=None):return intake.preview(self.d,self.p['id'],data or self.data,self.p['revision'])
 def apply(self,preview=None,data=None):
  data=data or self.data;preview=preview or self.preview(data);return intake.apply(self.d,self.p['id'],dict(data,plan=preview['plan'],confirmed=True),self.p['revision'])
 def test_preview_no_write_apply_retains_original_and_links_unreviewed(self):
  before=self.d.project(self.p['id']);v=self.preview();self.assertEqual(before,self.d.project(self.p['id']));self.assertTrue(v['can_apply']);self.assertIn('(configuracao.html)',v['files'][0]['markdown'])
  p=self.apply(v);self.assertEqual(p['revision'],before['revision']+1);self.assertEqual([a['review']['status'] for a in p['articles']],['missing','missing'])
  self.assertEqual(p['sources'][0]['content'],self.data['files'][0]['content']);self.assertEqual(self.d.snapshots(p['id'],p['sources'][0]['id'])[0]['content'],self.data['files'][0]['content'])
  with self.assertRaises(e.DeskError):self.d.publish(p['id'],{'actor':{'kind':'operator','label':'test'},'note':'unreviewed'},p['revision'])
 def test_changed_plan_input_revision_and_duplicate_apply_rejected(self):
  v=self.preview();bad=dict(self.data,limits='changed')
  with self.assertRaises(e.DeskError):self.apply(v,bad)
  self.assertEqual(self.d.project(self.p['id'])['sources'],[])
  p=self.apply(v)
  with self.assertRaises(e.DeskError):self.apply(v)
  self.assertEqual(p,self.d.project(self.p['id']))
 def test_late_database_failure_rolls_back_every_item(self):
  v=self.preview();original=self.d._article;calls=[]
  def fail(*args):
   calls.append(1)
   if len(calls)==2:raise RuntimeError('forced final-row failure')
   return original(*args)
  with patch.object(self.d,'_article',side_effect=fail):
   with self.assertRaises(RuntimeError):self.apply(v)
  self.assertEqual(self.d.project(self.p['id']),self.p)
  with self.d._connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM snapshots').fetchone()[0],0)
 def test_conflicts_and_missing_links_do_not_partially_import(self):
  for files in ([{'name':'A.md','content':'# A'},{'name':'Á.md','content':'# B'}],[{'name':'a.md','content':'[missing](missing.md)'}],[{'name':'a.md','content':'![photo](https://example.org/a.png)'}],[{'name':'a.md','content':'---\nx: y\n---\n# A'}]):
   with self.subTest(files=files):
    data=dict(self.data,files=files);v=self.preview(data);self.assertFalse(v['can_apply'])
    with self.assertRaises(e.DeskError):self.apply(v,data)
    self.assertEqual(self.d.project(self.p['id']),self.p)
 def test_unsafe_and_oversize_inputs(self):
  for files in ([{'name':'../a.md','content':'x'}],[{'name':'a.md','content':'<script>x</script>'}],[{'name':'a.md','content':'x'*131073}],[{'name':'a.md','content':'\ud800'}],[] ):
   with self.subTest(files=str(files)[:100]):
    with self.assertRaises(e.DeskError):self.preview(dict(self.data,files=files))
  with self.assertRaises(e.DeskError):self.preview(dict(self.data,original_owned=False))
 def test_code_links_preserved_and_existing_slug_blocks(self):
  self.data['files'][0]['content']='# Início\n`[fake](absent.md)`\n```md\n[code](absent.md)\n```\n'
  v=self.preview();self.assertTrue(v['can_apply']);self.assertEqual(v['files'][0]['markdown'],self.data['files'][0]['content'].split('\n',1)[1]);self.p=self.apply(v)
  self.assertFalse(self.preview()['can_apply'])
 def test_title_extracted_once_and_code_heading_not_used(self):
  v=self.preview();self.assertTrue(v['files'][0]['title_extracted']);self.assertNotIn('# Início',v['files'][0]['markdown']);self.assertIn('# Início',v['files'][0]['original'])
  data=dict(self.data,files=[{'name':'code.md','content':'```md\n# Example\n```\nText'}]);v=self.preview(data);self.assertEqual(v['files'][0]['title'],'code');self.assertFalse(v['files'][0]['title_extracted'])
 def test_search_contains_only_public_fields_with_script_escape_and_hash(self):
  p=self.apply();p['articles'][0]['title']='</script><script>evil()</script>';p['sources'][0]['content']='PRIVATE-SOURCE'
  files,_=reader.build(p,'r_test',e._render,e._hash,e._json,e._now);index=files['index.html'].decode()
  self.assertNotIn('PRIVATE-SOURCE',index);self.assertNotIn('</script><script>',index);self.assertEqual(index.count('<script>'),1)
  script=index.split('<script>')[1].split('</script>')[0]
  import base64
  self.assertIn(base64.b64encode(hashlib.sha256(script.encode()).digest()).decode(),index)
  self.assertIn('Busca local, sem envio de dados.',index)
if __name__=='__main__':unittest.main()
