"""Local PostgreSQL authorization/transaction tests; not hosted Supabase auth QA.
Requires a disposable, network-disabled container selected by KW_TEST_CONTAINER.
"""
import concurrent.futures,json,os,subprocess,uuid
from pathlib import Path
BASE=Path(__file__).resolve().parent
ENV=dict(os.environ)
CONTAINER=os.environ.get('KW_TEST_CONTAINER')
if not CONTAINER:raise SystemExit('Set KW_TEST_CONTAINER to a disposable, empty PostgreSQL container. Never use production.')
A='11111111-1111-4111-8111-111111111111';B='22222222-2222-4222-8222-222222222222';C='33333333-3333-4333-8333-333333333333'
def sql(query,identity=None,role=None,ok=True):
 pre=("set role "+role+";" if role else '')+("set request.jwt.claim.sub='"+identity+"';" if identity else '')
 r=subprocess.run(['docker','exec','-i',CONTAINER,'psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','postgres'],input=pre+query,text=True,capture_output=True,env=ENV)
 if ok and r.returncode:raise AssertionError(r.stderr)
 if not ok and not r.returncode:raise AssertionError('Expected refusal')
 return r.stdout.strip() if ok else r.stderr
quote=lambda x:"'"+json.dumps(x).replace("'","''")+"'::jsonb"
def project(name='Own',version=0):return dict(id=str(uuid.uuid4()),name=name,version=version,createdAt='2026-10-13T00:00:00Z',documents=[],publications=[])
def listing(who):return json.loads(sql('select public.kw_list_projects();',who,'authenticated'))
sql("create role anon nologin;create role authenticated nologin;create schema auth;create table auth.users(id uuid primary key);create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;grant usage on schema auth to authenticated,anon;")
sql(BASE.joinpath('schema.sql').read_text())
sql("insert into auth.users values('"+A+"'),('"+B+"'),('"+C+"');insert into kw_private.members values('"+A+"'),('"+B+"');")
assert 'permission denied' in sql('select public.kw_list_projects();',role='anon',ok=False)
assert 'membership required' in sql('select public.kw_list_projects();',C,'authenticated',ok=False)
assert 'permission denied' in sql('select * from kw_private.workspaces;',A,'authenticated',ok=False)
p=project();saved=json.loads(sql('select public.kw_save_project('+quote(p)+',null);',A,'authenticated'));assert saved['version']==1
assert listing(B)==[];assert len(listing(A))==1
# Owner B cannot update A's project; separate B namespace is empty.
assert 'version conflict' in sql('select public.kw_save_project('+quote(saved)+',1);',B,'authenticated',ok=False)
# Two concurrent writers: exactly one commits, one receives PT409.
def write(name):
 x=dict(saved,name=name)
 try:return json.loads(sql('select public.kw_save_project('+quote(x)+',1);',A,'authenticated'))
 except AssertionError as e:return str(e)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(write,['Device one','Device two']))
assert sum(isinstance(x,dict) for x in results)==1
assert sum('version conflict' in x for x in results if isinstance(x,str))==1
before=listing(A);assert before[0]['version']==2
# Invalid second document makes the whole import fail; no partial first item.
a=project('First',1);bad=project('Bad',1);bad['documents']=[{}]
assert 'Invalid document' in sql('select public.kw_restore_projects('+quote([a,bad])+');',A,'authenticated',ok=False)
assert listing(A)==before
# Duplicate ids and count/byte limits are enforced by the server.
assert 'id conflict' in sql('select public.kw_restore_projects('+quote([a,a])+');',A,'authenticated',ok=False)
assert 'quota exceeded' in sql('select public.kw_restore_projects('+quote([project(version=1) for _ in range(20)])+');',A,'authenticated',ok=False)
large=project('Large',1)
large['documents']=[dict(id=str(uuid.uuid4()),title='Own',filename='',body='x'*131072,original='y'*131072,revision=1,review=None,history=[]) for _ in range(20)]
large2=dict(large,id=str(uuid.uuid4()))
assert 'quota exceeded' in sql('select public.kw_restore_projects('+quote([large,large2])+');',A,'authenticated',ok=False)
assert listing(A)==before
copies=json.loads(sql('select public.kw_restore_projects('+quote([a])+');',A,'authenticated'));assert copies==[a];assert len(listing(A))==2;assert listing(B)==[]
# A separate database session (device) sees the committed projects.
assert listing(A)[-1]['id']==a['id']
print(json.dumps({'database':'PostgreSQL 17 isolated local container','identity':'simulated JWT claims, not real hosted authentication','anonymous_denied':True,'unlisted_user_denied':True,'direct_table_access_denied':True,'account_isolation':True,'concurrent_compare_and_swap':True,'atomic_restore':True,'count_and_byte_quotas':True,'second_session_reads_saved_projects':True}))
