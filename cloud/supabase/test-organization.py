"""Organization assertions on disposable PostgreSQL only."""
import json,runpy
from pathlib import Path
e=runpy.run_path(str(Path(__file__).with_name('test-branding.py')))
sql,quote,call,p,pid,link=[e[k] for k in ('sql','quote','call','p','pid','link')]
before=json.loads(call('kw_read_help',link,None,'anon'))
sql(Path(__file__).with_name('organization.sql').read_text())
assert json.loads(call('kw_read_help',link,None,'anon'))==before
cats=[dict(id='start',name='Começar'),dict(id='manage',name='Gerenciar'),dict(id='empty',name='PRIVATE EMPTY')]
for invalid in [None,{},[dict(id='x',name='')],[dict(id='x',name=' A')],[dict(id='x',name='A',extra='SECRET')],[dict(id='x',name='A'),dict(id='x',name='B')],[dict(id='x',name='A'),dict(id='y',name='a')],[dict(id=str(i),name=str(i)) for i in range(21)]]:
 assert 'ERROR' in call('kw_save_project',quote(dict(p,categories=invalid))+',5',ok=False)
p['categories']=cats;p['documents'][0]['categoryId']='missing'
assert 'Article category not found' in call('kw_save_project',quote(p)+',5',ok=False)
p['documents'][0]['categoryId']='start';p['documents'][1]['categoryId']='manage'
p['documents'].reverse();p['categories']=[cats[1],cats[0],cats[2]]
p=json.loads(call('kw_save_project',quote(p)+',5'))
assert json.loads(call('kw_read_help',link,None,'anon'))==before
assert 'version conflict' in call('kw_publish_help',pid+',5,5',ok=False)
updated=json.loads(call('kw_publish_help',pid+',6,5'))
after=json.loads(call('kw_read_help',link,None,'anon'))
assert after['categories']==p['categories'][:2]
assert [d['id'] for d in after['documents']]==[d['id'] for d in p['documents']]
assert all(set(d)=={'id','title','body','categoryId'} for d in after['documents'])
assert 'PRIVATE EMPTY' not in json.dumps(after) and 'SECRET' not in json.dumps(after)
assert after['branding']==before['branding'] and updated['public_id']==e['updated']['public_id']
assert 'permission denied' in call('kw_publish_help',pid+',6,5',None,'anon',False)
print(json.dumps({'organization':'PASS','legacy_preserved':True,'invalid_categories_and_references_refused':True,'draft_private':True,'snapshot_whitelist_and_order':True,'empty_category_names_excluded':True,'stable_link_brand_preserved':True,'no_new_grants':True}))
