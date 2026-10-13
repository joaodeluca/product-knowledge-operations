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
