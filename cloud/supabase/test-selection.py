"""Selection boundary assertions, only on disposable PostgreSQL."""
import json,runpy
from pathlib import Path
e=runpy.run_path(str(Path(__file__).with_name('test-organization.py')))
sql,quote,call,p,pid,link=[e[k] for k in ('sql','quote','call','p','pid','link')]
before=json.loads(call('kw_read_help',link,None,'anon'))
sql(Path(__file__).with_name('selection.sql').read_text())
assert json.loads(call('kw_read_help',link,None,'anon'))==before
meta=json.loads(call('kw_help_status',pid));assert meta['article_ids']==[d['id'] for d in p['documents']]
for invalid in [None,'false',0,{},[]]:
 bad=json.loads(json.dumps(p));bad['documents'][0]['publish']=invalid
 assert 'Invalid publication selection' in call('kw_save_project',quote(bad)+',6',ok=False)
# Hide one formerly published document, leave it unreviewed; the other can publish.
hidden=p['documents'][0];visible=p['documents'][1];hidden['publish']=False;hidden['review']=None
hidden['filename']='private-draft.md';hidden['title']='PRIVATE DRAFT TITLE';hidden['body']='PRIVATE DRAFT BODY'
visible['body']+=' [Internal](private-draft.md)';visible['publish']=True
p=json.loads(call('kw_save_project',quote(p)+',6'))
assert json.loads(call('kw_read_help',link,None,'anon'))==before
assert 'version conflict' in call('kw_publish_help',pid+',6,6',ok=False)
updated=json.loads(call('kw_publish_help',pid+',7,6'));after=json.loads(call('kw_read_help',link,None,'anon'))
assert [d['id'] for d in after['documents']]==[visible['id']]
assert updated['article_ids']==[visible['id']] and updated['public_id']==meta['public_id']
assert len(after['categories'])==1 and after['links']==[]
assert 'PRIVATE DRAFT' not in json.dumps(after) and hidden['id'] not in json.dumps(after)
# Unreviewed selected draft is refused, no mutation of live snapshot.
p['documents'][0]['publish']=True;p=json.loads(call('kw_save_project',quote(p)+',7'))
assert 'Review selected articles' in call('kw_publish_help',pid+',8,7',ok=False)
assert json.loads(call('kw_read_help',link,None,'anon'))==after
# Empty selection rejected; whole-site withdrawal remains explicit.
for d in p['documents']:d['publish']=False
p=json.loads(call('kw_save_project',quote(p)+',8'))
assert 'Select at least one' in call('kw_publish_help',pid+',9,7',ok=False)
assert json.loads(call('kw_read_help',link,None,'anon'))==after
assert 'permission denied' in call('kw_publish_help',pid+',9,7',None,'anon',False)
print(json.dumps({'selection':'PASS','legacy_snapshot_unchanged':True,'drafts_excluded_server_side':True,'only_selected_need_review':True,'draft_alias_category_excluded':True,'stale_and_empty_refused':True,'same_link_and_cas':True,'no_new_grants':True}))
