"""Tests for the independent distribution and public/private boundary."""
import hashlib
import http.client
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import serve
import engine

ACTOR={'kind':'operator','label':'LOCAL_REVIEWER_SECRET'}

class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name).resolve()
        self.server=serve.Server(self.root/'workspace'); self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.origin=self.server.origin; self.cookie=''
        code,headers,_=self.req('GET','/start/'+self.server.bootstrap)
        self.assertEqual(code,303); self.cookie=headers['Set-Cookie'].split(';')[0]
        self.p=self.ok('POST','/api/projects',{'name':'Central própria','purpose':'PURPOSE_SECRET','authority':'AUTHORITY_SECRET','limits':'PROJECT_LIMIT_SECRET'})
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.temp.cleanup()
    def req(self,method,path,data=None,extra=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        headers={'Cookie':self.cookie,'Origin':self.origin,'X-Workspace':'1','Content-Type':'application/json'};headers.update(extra or {})
        c.request(method,path,json.dumps(data) if data is not None else None,headers);r=c.getresponse();body=r.read();status=r.status;headers=dict(r.getheaders());c.close();return status,headers,body
    def ok(self,method,path,data=None):
        code,_,raw=self.req(method,path,data);self.assertIn(code,(200,201),raw);return json.loads(raw)
    def change(self,path,data,method='POST'):
        self.p=self.ok(method,path,dict(data,project_id=self.p['id'],expected_revision=self.p['revision']));return self.p
    def content(self):
        self.source={'title':'SOURCE_TITLE_SECRET','content':'ORIGINAL_SOURCE_SECRET','version':'1','evidence':'SOURCE_EVIDENCE_SECRET','limits':'SOURCE_LIMITS_SECRET','original_owned':True}
        self.change('/api/sources',self.source); self.sid=self.p['sources'][0]['id']
        self.change('/api/procedures',{'title':'PROCEDURE_TITLE_SECRET','steps':'PROCEDURE_STEPS_SECRET','source_ids':[self.sid],'evidence':'PROCEDURE_EVIDENCE_SECRET','limits':'PROCEDURE_LIMITS_SECRET'})
        self.tid=self.p['procedures'][0]['id']
        self.article={'title':'Criar um espaço','slug':'criar-espaco','markdown':'## Passos\n1. Abra o produto.\n2. Escolha Novo espaço.','source_ids':[self.sid],'procedure_id':self.tid,'evidence':'ARTICLE_EVIDENCE_SECRET','limits':'Somente versão 1.'}
        self.change('/api/articles',self.article);self.aid=self.p['articles'][0]['id']
    def review(self): self.change('/api/articles/'+self.aid+'/review',{'actor':ACTOR,'note':'REVIEW_NOTE_SECRET'})
    def publish(self):
        self.change('/api/publish',{'actor':ACTOR,'note':'RELEASE_NOTE_SECRET','public_fields_reviewed':True});return self.p['active_release_id']
    def download(self,rid):
        code,_,body=self.req('GET',f'/api/releases/{self.p["id"]}/{rid}/download');self.assertEqual(code,200,body);return body
    def test_public_reader_excludes_all_internal_fields_and_hashes_match(self):
        self.content();self.review();rid=self.publish();raw=self.download(rid)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertEqual(set(z.namelist()),{'index.html','articles/criar-espaco.html','manifest.json'})
            self.assertNotIn(b'_SECRET',b'\n'.join(z.read(n) for n in z.namelist()))
            manifest=json.loads(z.read('manifest.json'))
            for entry in manifest['files']:
                b=z.read(entry['path']);self.assertEqual(entry['bytes'],len(b));self.assertEqual(entry['sha256'],hashlib.sha256(b).hexdigest())
            self.assertIn('Somente versão 1.'.encode(),z.read('articles/criar-espaco.html'))
        self.assertEqual(raw,self.download(rid))
    def test_source_change_blocks_release_and_old_download_stays_unchanged(self):
        self.content();self.review();rid=self.publish();old=self.download(rid)
        self.change('/api/sources/'+self.sid,dict(self.source,content='Fonte corrigida',version='2'),'PATCH')
        self.assertEqual(self.p['articles'][0]['review']['status'],'stale');before=self.p
        code,_,_=self.req('POST','/api/publish',{'project_id':self.p['id'],'expected_revision':self.p['revision'],'actor':ACTOR,'note':'changed','public_fields_reviewed':True});self.assertEqual(code,409)
        self.assertEqual(self.server.desk.project(self.p['id']),before)
        self.assertEqual(old,self.download(rid));self.review();new=self.publish();self.assertNotEqual(new,rid)
    def test_cross_project_links_and_stale_updates_rejected(self):
        self.content();other=self.ok('POST','/api/projects',{'name':'Outra central'})
        code,_,_=self.req('POST','/api/articles',dict(self.article,project_id=other['id'],expected_revision=other['revision']));self.assertIn(code,(400,404))
        self.assertEqual(self.server.desk.project(other['id'])['articles'],[])
        code,_,_=self.req('PATCH','/api/sources/'+self.sid,dict(self.source,project_id=self.p['id'],expected_revision=1));self.assertEqual(code,409)
    def test_anonymous_origin_and_public_confirmation_guards(self):
        self.assertEqual(self.req('GET','/api/state',extra={'Cookie':''})[0],401)
        self.assertEqual(self.req('POST','/api/projects',{'name':'Injected'},extra={'Origin':'https://other.example'})[0],403)
        self.assertEqual(self.req('GET','/api/state',extra={'Host':'other.example'})[0],421)
        self.content();self.review()
        code,_,_=self.req('POST','/api/publish',{'project_id':self.p['id'],'expected_revision':self.p['revision'],'actor':ACTOR,'note':'x'});self.assertEqual(code,400)
    def test_reviewer_not_silently_codex_or_verified_identity(self):
        self.content()
        code,_,_=self.req('POST','/api/articles/'+self.aid+'/review',{'project_id':self.p['id'],'expected_revision':self.p['revision'],'note':'x'});self.assertEqual(code,400)
        self.review();r=self.p['articles'][0]['review'];self.assertEqual(r['actor']['label'],ACTOR['label']);self.assertFalse(r['actor']['identity_verified'])
    def test_html_source_rejected_and_titles_escaped(self):
        self.content()
        code,_,_=self.req('PATCH','/api/articles/'+self.aid,dict(self.article,markdown='<script>alert(1)</script>',project_id=self.p['id'],expected_revision=self.p['revision']));self.assertEqual(code,400)
        self.change('/api/articles/'+self.aid,dict(self.article,title='<script>unsafe title</script>'),'PATCH');self.review();rid=self.publish()
        with zipfile.ZipFile(io.BytesIO(self.download(rid))) as z:
            self.assertNotIn(b'<script>',z.read('index.html'));self.assertIn(b'&lt;script&gt;',z.read('index.html'))
    def test_foreign_store_and_second_process_refused(self):
        foreign=self.root/'foreign';foreign.mkdir();(foreign/'notes.txt').write_text('existing')
        with self.assertRaises(ValueError): serve.Server(foreign)
        process=subprocess.run([sys.executable,str(Path(serve.__file__)),'--store',str(self.root/'workspace')],capture_output=True,timeout=5)
        self.assertEqual(process.returncode,2);self.assertIn('outro processo',process.stderr.decode())
    def test_source_history_and_tampering_rejected(self):
        self.content();self.change('/api/sources/'+self.sid,dict(self.source,content='Versão dois'),'PATCH')
        history=self.ok('GET',f'/api/sources/{self.p["id"]}/{self.sid}/history');self.assertEqual(len(history),2)
        self.review();rid=self.publish();path=self.root/'workspace'/'releases'/self.p['id']/rid/'index.html';path.write_text('tampered')
        self.assertEqual(self.req('GET',f'/api/releases/{self.p["id"]}/{rid}/download')[0],409)
if __name__=='__main__':unittest.main()
