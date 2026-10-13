"""Branding on disposable PostgreSQL only; never connects to production."""
import json,runpy
from pathlib import Path
e=runpy.run_path(str(Path(__file__).with_name('test-publication.py')))
sql,quote,call,p,pid,link=[e[k] for k in ('sql','quote','call','p','pid','link')]
before=json.loads(call('kw_read_help',link,None,'anon'))
sql(Path(__file__).with_name('branding.sql').read_text())
assert json.loads(call('kw_read_help',link,None,'anon'))==before
logo='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLttAAAAABJRU5ErkJggg=='
brand=dict(primaryColor='#663399',headerColor='#101010',logo=logo)
for invalid in [None,[],dict(brand,privateNote='SECRET'),dict(brand,logo='https://example.test/logo.png'),dict(brand,logo='data:image/svg+xml;base64,PHN2Zz4='),dict(brand,logo='data:image/png;base64,AAAA'),dict(brand,primaryColor='#fff;url(x)'),dict(brand,logo='x'*196609)]:
 q=dict(p,branding=invalid)
 assert 'Invalid branding' in call('kw_save_project',quote(q)+',4',ok=False)
p['branding']=brand;p['name']='Own branded demo';p=json.loads(call('kw_save_project',quote(p)+',4'))
assert json.loads(call('kw_read_help',link,None,'anon'))==before
assert 'version conflict' in call('kw_save_project',quote(dict(p,version=4))+',4',ok=False)
updated=json.loads(call('kw_publish_help',pid+',5,4'))
after=json.loads(call('kw_read_help',link,None,'anon'))
assert after['branding']==brand and after['name']==p['name']
assert set(after)=={'name','documents','links','branding','published_at'} and 'SECRET' not in json.dumps(after)
assert updated['public_id']==e['pub']['public_id']
assert 'permission denied' in call('kw_save_project',quote(p)+',5',None,'anon',False)
assert sql("select has_function_privilege('anon','kw_publish_help(text,bigint,bigint)','execute');")=='f'
print(json.dumps({'branding':'PASS','legacy_snapshot_unchanged':True,'rejects_invalid_logo_colors_extra_fields':True,'draft_private':True,'stable_link':True,'owner_only_save':True,'CAS_conflict_protected':True,'public_projection_exact':True}))
