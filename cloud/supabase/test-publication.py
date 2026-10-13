"""Real disposable PostgreSQL; identity claims simulated, not hosted authentication."""
import json,runpy
from pathlib import Path
env=runpy.run_path(str(Path(__file__).with_name('test-database.py')))
sql,quote,project,A,B,C=[env[k] for k in ('sql','quote','project','A','B','C')]
sql(Path(__file__).with_name('publication.sql').read_text())
def call(name,args,who=A,role='authenticated',ok=True):
    return sql('select public.'+name+'('+args+');',who,role,ok)
p=project('Public title');p['documents']=[dict(id='article-one',title='Public article',body='Safe body [Second](SECOND.md)',filename='private-filename.md',original='SECRET ORIGINAL',revision=1,review=None,history=[]),dict(id='article-two',title='Second',body='Another safe body',filename='second.md',original='SECRET SECOND',revision=1,review=None,history=[])]
p['untrustedExtra']='SECRET EXTRA'
p=json.loads(call('kw_save_project',quote(p)+',null'))
pid="'"+p['id']+"'"
assert 'permission denied' in call('kw_publish_help',pid+',1,0',None,'anon',False)
assert 'membership required' in call('kw_publish_help',pid+',1,0',C,ok=False)
assert 'version conflict' in call('kw_publish_help',pid+',1,0',B,ok=False)
assert 'Review every article' in call('kw_publish_help',pid+',1,0',ok=False)
for d in p['documents']:d['review']=dict(revision=1,note='SECRET REVIEW',at='2026-10-13')
p=json.loads(call('kw_save_project',quote(p)+',1'))
pub=json.loads(call('kw_publish_help',pid+',2,0'));link="'"+pub['public_id']+"'::uuid"
assert pub['live'] and pub['revision']==1
public=json.loads(call('kw_read_help',link,None,'anon'))
assert set(public)=={'name','documents','links','published_at'}
assert all(set(d)=={'id','title','body'} for d in public['documents'])
assert 'SECRET' not in json.dumps(public) and 'private-filename' not in json.dumps(public)
assert public['links']==[dict(id='article-two',filename='second.md')]
assert 'permission denied' in sql('select * from kw_private.help_sites;',role='anon',ok=False)
assert 'permission denied' in sql('select * from kw_private.help_sites;',A,'authenticated',ok=False)
assert 'permission denied' in call('kw_help_status',pid,None,'anon',False)
assert json.loads(call('kw_publish_help',pid+',2,0'))==pub # lost acknowledgement is idempotent
assert call('kw_help_status',pid,B)=='' # cannot inspect another owner's management metadata
assert call('kw_unpublish_help',pid+',1',B)==''
# Saving a draft never updates the live snapshot; stale reviews and versions cannot publish.
p['documents'][0]['revision']=2;p['documents'][0]['body']='New public body'
p=json.loads(call('kw_save_project',quote(p)+',2'))
assert json.loads(call('kw_read_help',link,None,'anon'))==public
assert 'version conflict' in call('kw_publish_help',pid+',2,1',ok=False)
assert 'Review every article' in call('kw_publish_help',pid+',3,1',ok=False)
p['documents'][0]['review']['revision']=2;p=json.loads(call('kw_save_project',quote(p)+',3'))
assert 'Publication version conflict' in call('kw_publish_help',pid+',4,0',ok=False)
updated=json.loads(call('kw_publish_help',pid+',4,1'));assert updated['public_id']==pub['public_id'] and updated['revision']==2
assert json.loads(call('kw_read_help',link,None,'anon'))['documents'][0]['body']=='New public body'
assert 'Publication version conflict' in call('kw_unpublish_help',pid+',1',ok=False)
off=json.loads(call('kw_unpublish_help',pid+',2'));assert off['live'] is False
assert 'Publication unavailable' in call('kw_read_help',link,None,'anon',False)
again=json.loads(call('kw_publish_help',pid+',4,3'));assert again['public_id']==pub['public_id'] and again['live']
assert sql('select jsonb_array_length(versions) from kw_private.help_sites where project_id='+pid+';')=='2'
assert 'Publication unavailable' in call('kw_read_help',"'99999999-9999-4999-8999-999999999999'",None,'anon',False)
print(json.dumps({'publication_migration':'PASS','private_tables_denied':True,'owner_only_management':True,'anonymous_read_selected_fields_only':True,'server_review_and_version_gate':True,'draft_not_published':True,'stable_link_update':True,'unpublish_anonymous404':True,'republish_preserves_link_and_history':True,'idempotent_retry':True,'identity':'simulated claims in isolated PostgreSQL17'}))
