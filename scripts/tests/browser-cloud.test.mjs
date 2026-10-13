import {test} from 'node:test';
import assert from 'node:assert/strict';
import {cloudStore} from '../../site/browser/cloud.mjs';
import {newProject} from '../../site/browser/model.mjs';
const config={url:'https://example-project.supabase.co',publishableKey:'sb_publishable_fixture'};
const session={access_token:'fixture-access',refresh_token:'fixture-refresh',expires_in:3600,user:{id:'fixture-user',email:'fixture@example.invalid'}};
const json=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}});
function client(handler){const calls=[];const api=cloudStore(config,{fetcher:async(url,options)=>{calls.push({url,options});return handler(url,options,calls);}});return {api,calls};}
test('accepts only fixed HTTPS Supabase host and public key, rejecting secrets and URL overrides',()=>{
 for(const url of ['http://example-project.supabase.co','https://evil.invalid','https://example-project.supabase.co:8443','https://user@example-project.supabase.co','https://example-project.supabase.co/?x=1'])assert.throws(()=>cloudStore({...config,url}));
 assert.throws(()=>cloudStore({...config,publishableKey:'sb_secret_private'}));
});
test('login checks server access; save waits for validated acknowledgement and sends expected version',async()=>{
 const p=newProject('Own project');const {api,calls}=client((url,opt)=>url.includes('/token?')?json(session):url.endsWith('kw_list_projects')?json([]):json({...p,version:1}));
 await api.signIn('fixture@example.invalid','fixture-password');const saved=await api.saveProject(p,null);assert.equal(saved.version,1);
 const save=calls.at(-1);assert.equal(save.options.headers.Authorization,'Bearer fixture-access');assert.equal(save.options.credentials,'omit');assert.equal(save.options.redirect,'error');assert.deepEqual(JSON.parse(save.options.body),{p_project:p,p_expected_version:null});assert(!save.options.body.includes('owner'));
});
test('conflict is reported without automatic overwrite or retry',async()=>{
 const {api,calls}=client(url=>url.includes('/token?')?json(session):url.endsWith('kw_list_projects')?json([]):json({},409));await api.signIn('x','y');await assert.rejects(()=>api.saveProject(newProject('Draft'),null),/outro dispositivo/);assert.equal(calls.length,3);
});
test('lost save response is uncertain, does not claim success or retry',async()=>{
 const {api,calls}=client(url=>{if(url.includes('/token?'))return json(session);if(url.endsWith('kw_list_projects'))return json([]);throw Error('Network');});await api.signIn('x','y');await assert.rejects(()=>api.saveProject(newProject('Draft'),null),/pode ter salvo/);assert.equal(calls.length,3);
});
test('denied account is not retained and cannot read or write',async()=>{
 const {api,calls}=client(url=>url.includes('/token?')?json(session):json({},403));await assert.rejects(()=>api.signIn('x','y'),/não tem acesso/);assert.equal(api.user,null);await assert.rejects(()=>api.listProjects(),/Entre/);assert.equal(calls.length,2);
});
test('expired session refreshes once for simultaneous reads and is kept only in memory',async()=>{
 let at=0,refreshes=0;const api=cloudStore(config,{now:()=>at,fetcher:async url=>{if(url.includes('refresh_token')){refreshes++;return json({...session,access_token:'new-token'});}return url.includes('/token?')?json(session):json([]);}});
 await api.signIn('x','y');at=3600001;await Promise.all([api.listProjects(),api.listProjects()]);assert.equal(refreshes,1);
 const other=cloudStore(config,{fetcher:()=>{throw Error('must not call');}});await assert.rejects(()=>other.listProjects(),/Entre/);
});
test('logout clears local session even if server revocation cannot be confirmed',async()=>{
 const {api}=client(url=>url.includes('/token?')?json(session):url.endsWith('kw_list_projects')?json([]):Promise.reject(Error('Network')));await api.signIn('x','y');await assert.rejects(()=>api.signOut());assert.equal(api.user,null);await assert.rejects(()=>api.listProjects(),/Entre/);
});
test('restore creates new ids and retains the input unchanged',async()=>{
 const p=newProject('Existing');p.version=7;const before=structuredClone(p);const {api}=client((url,opt)=>url.includes('/token?')?json(session):url.endsWith('kw_list_projects')?json([]):json(JSON.parse(opt.body).p_projects));await api.signIn('x','y');const saved=await api.restoreCopies([p]);assert.deepEqual(p,before);assert.notEqual(saved[0].id,p.id);assert.equal(saved[0].version,1);assert.equal(saved[0].name,'Existing · recuperado');
});
test('unexpected save acknowledgement cannot be presented as a successful save',async()=>{
 const p=newProject('Own');const {api}=client(url=>url.includes('/token?')?json(session):url.endsWith('kw_list_projects')?json([]):json({...p,version:99}));await api.signIn('x','y');await assert.rejects(()=>api.saveProject(p,null),/inesperada/);
});
const memory=()=>{const m=new Map();return {getItem:k=>m.get(k)||null,setItem:(k,v)=>m.set(k,v),removeItem:k=>m.delete(k)};};
test('persistent session resumes after reload without password, logout removes it',async()=>{
 const storage=memory();let passwords=0;const fetcher=async url=>{if(url.includes('grant_type=password')){passwords++;return json(session);}return url.includes('logout')?new Response(null,{status:204}):json([]);};
 const first=cloudStore(config,{storage,fetcher});await first.signIn('fixture','never-persist-password');assert(!storage.getItem(first.sessionKey).includes('never-persist-password'));
 const reload=cloudStore(config,{storage,fetcher});assert.deepEqual(await reload.resume(),[]);assert.equal(passwords,1);await reload.signOut();assert.equal(await cloudStore(config,{storage,fetcher}).resume(),null);
});
test('parallel tabs serialize refresh and read latest rotated session',async()=>{
 const storage=memory();let at=0,refreshes=0,queue=Promise.resolve();const locks={request:(key,fn)=>{const p=queue.then(fn);queue=p.catch(()=>{});return p;}};
 const fetcher=async url=>{if(url.includes('refresh_token')){refreshes++;return json({...session,access_token:'rotated'});}return url.includes('token?')?json(session):json([]);};
 const a=cloudStore(config,{storage,locks,fetcher,now:()=>at});await a.signIn('x','y');const b=cloudStore(config,{storage,locks,fetcher,now:()=>at});at=3600001;
 await Promise.all([a.listProjects(),b.resume()]);assert.equal(refreshes,1);
});
test('transient refresh failure preserves login for reconnection; revoked refresh clears it',async()=>{
 const storage=memory();let at=0,mode='online';const fetcher=async url=>{if(url.includes('refresh_token')){if(mode==='offline')throw Error('Network');if(mode==='revoked')return json({},400);}return url.includes('token?')?json(session):json([]);};
 const a=cloudStore(config,{storage,fetcher,now:()=>at});await a.signIn('x','y');at=3600001;mode='offline';await assert.rejects(a.listProjects());assert(storage.getItem(a.sessionKey));mode='online';await a.listProjects();at=7200002;mode='revoked';await assert.rejects(a.listProjects());assert.equal(storage.getItem(a.sessionKey),null);
});
test('late refresh cannot resurrect a session signed out in another tab',async()=>{
 const storage=memory();let at=0,release;const response=new Promise(r=>release=r);const fetcher=async url=>url.includes('refresh_token')?response:url.includes('token?')?json(session):url.includes('logout')?new Response(null,{status:204}):json([]);
 const a=cloudStore(config,{storage,fetcher,now:()=>at});await a.signIn('x','y');const b=cloudStore(config,{storage,fetcher,now:()=>at});at=3600001;const refresh=a.listProjects();await b.signOut();release(json(session));await assert.rejects(refresh);assert.equal(storage.getItem(a.sessionKey),null);
});
test('a dirty tab cannot write under another account after shared login changes',async()=>{
 const storage=memory();let who=session,writeCalls=0;const fetcher=async url=>{if(url.includes('token?'))return json(who);if(url.endsWith('kw_save_project'))writeCalls++;return json([]);};
 const a=cloudStore(config,{storage,fetcher});await a.signIn('a','a');const b=cloudStore(config,{storage,fetcher});who={...session,user:{id:'second-user'}};await b.signIn('b','b');await assert.rejects(()=>a.saveProject(newProject('Draft'),null),/conta mudou/);assert.equal(writeCalls,0);
});
