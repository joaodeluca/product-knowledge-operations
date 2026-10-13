import {test} from 'node:test';
import assert from 'node:assert/strict';
import {newProject,newDocument,changeDocument,reviewDocument,current,markdown,publicHTML,makeBackup,readBackup,checksum} from '../../site/browser/model.mjs';
const fixture=()=>{const p=newProject('Ajuda');p.documents.push({...newDocument('Uso','Texto público','uso.md'),publish:true});return p;};
test('edits expire review, no-op does not create history and original is preserved',()=>{
 const p=fixture(),d=p.documents[0];reviewDocument(d,'Conferido');assert(current(d));assert.equal(changeDocument(d,d.title,d.body),false);assert.equal(d.history.length,0);
 changeDocument(d,'Uso novo','Nova instrução');assert(!current(d));assert.equal(d.original,'Texto público');assert.equal(d.history[0].body,'Texto público');assert.throws(()=>publicHTML(p));reviewDocument(d,'Conferência nova');assert(current(d));
});
test('public output excludes private notes, original and historical text',()=>{
 const p=fixture(),d=p.documents[0];d.original='PRIVATE_ORIGINAL';changeDocument(d,'Uso','CURRENT_PUBLIC');d.history[0].body='PRIVATE_HISTORY';reviewDocument(d,'PRIVATE_REVIEW');const html=publicHTML(p);
 assert(html.includes('CURRENT_PUBLIC'));for(const secret of ['PRIVATE_ORIGINAL','PRIVATE_HISTORY','PRIVATE_REVIEW'])assert(!html.includes(secret));
 const pub={id:crypto.randomUUID(),at:new Date().toISOString(),version:1,html};p.publications.push(pub);changeDocument(d,'Uso','Different');assert.equal(p.publications[0].html,html);
});
test('untrusted text is escaped and active links are bounded',()=>{
 const html=markdown('<script>alert(1)</script>\n[x](javascript:alert)\n[x](data:text/html,test)\n`<img src=x onerror=evil>`\n[ok](https://example.com)');
 assert(!html.includes('<script>'));assert(!html.includes('<img'));assert(!html.includes('href="javascript:'));assert(!html.includes('href="data:'));assert(html.includes('href="https://example.com/"'));
 const p=fixture();p.documents[0].body='</script><img src=x onerror=evil>';reviewDocument(p.documents[0],'ok');assert(!publicHTML(p).includes('<img'));
});
test('links between imported files target public article ids',()=>{const p=fixture();assert(markdown('[Uso](uso.md)',p.documents).includes('#article-'+p.documents[0].id));assert(!markdown('[missing](unknown.md)',p.documents).includes('<a'));});
test('backup round trip preserves stale review, history and immutable publication',async()=>{
 const p=fixture(),d=p.documents[0];reviewDocument(d,'note');p.publications.push({id:crypto.randomUUID(),at:new Date().toISOString(),version:1,html:publicHTML(p)});changeDocument(d,'Uso','New version');assert.deepEqual(await readBackup(await makeBackup([p])),[p]);
});
test('corrupt backup and structurally invalid payload are rejected',async()=>{
 const p=fixture(),env=JSON.parse(await makeBackup([p]));env.payload+=' ';await assert.rejects(()=>readBackup(JSON.stringify(env)));
 p.documents[0].revision=-1;env.payload=JSON.stringify({projects:[p]});env.sha256=await checksum(env.payload);await assert.rejects(()=>readBackup(JSON.stringify(env)));
});
test('unreviewed and empty projects cannot be exported',()=>{assert.throws(()=>publicHTML(newProject('Empty')));assert.throws(()=>publicHTML(fixture()));});
test('numbered instructions preserve order and explicit numbers',()=>{const html=markdown('3. Third\n4. Fourth\n\n- Bullet');assert(html.includes('<ol><li value="3">Third</li><li value="4">Fourth</li></ol>'));assert(html.includes('<ul><li>Bullet</li></ul>'));});
