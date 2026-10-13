import {test} from 'node:test';
import assert from 'node:assert/strict';
import {loadPublic,renderPublic,matches} from '../../site/help/reader.mjs';
const config={url:'https://example.supabase.co',publishableKey:'sb_publishable_fixture'};
const id='11111111-1111-4111-8111-111111111111';
const p={name:'Central <script>alert(1)</script>',published_at:'2026-10-13T00:00:00Z',documents:[{id:'one',title:'First',body:'[Next](two.md) <img src=x onerror=alert(1)> [unsafe](javascript:alert)'}],links:[{id:'one',filename:'two.md'}]};
test('public reader sends only publishable key and id, no user authentication or browser credentials',async()=>{
 let calls=0;const actual=await loadPublic(config,id,async(url,opt)=>{calls++;assert(url.endsWith('/kw_read_help'));assert.equal(opt.credentials,'omit');assert.equal(opt.cache,'no-store');assert.equal(opt.headers.Authorization,undefined);assert.deepEqual(JSON.parse(opt.body),{p_public_id:id});return new Response(JSON.stringify(p));});assert.equal(calls,1);assert.deepEqual(actual,p);
});
test('unpublished and invalid links never become a login screen or cached private content',async()=>{
 await assert.rejects(()=>loadPublic(config,'bad',()=>{throw Error('Should not fetch');}),/inválido/);
 await assert.rejects(()=>loadPublic(config,id,async()=>new Response('{}',{status:404})),/retirada/);
 await assert.rejects(()=>loadPublic(config,id,async()=>{throw Error('Network');}),/conexão/);
});
test('public rendering escapes active HTML, rejects unsafe links and resolves public internal aliases',()=>{
 const rendered=renderPublic(p);assert(!rendered.includes('<script>'));assert(!rendered.includes('<img'));assert(!rendered.includes('href="javascript:'));assert(rendered.includes('href="#article-one"'));assert(rendered.includes('&lt;script&gt;'));
});
test('public search handles accents, multiple words and empty results',()=>{
 assert(matches('Publicação de artigos','publicacao artigos'));assert(!matches('Publicação de artigos','publicacao senha'));assert(matches('Any',''));
});
