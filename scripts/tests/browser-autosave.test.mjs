import {test} from 'node:test';
import assert from 'node:assert/strict';
import {autoSave,sameJSON} from '../../site/browser/autosave.mjs';
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
test('typing during a slow write is saved serially, never acknowledged as the older value',async()=>{
 let value='A';const writes=[],states=[],gate=deferred();
 const save=autoSave({read:()=>value,write:async v=>{writes.push(v);if(v==='A')await gate.promise;},onState:s=>states.push(s),schedule:()=>0,cancel:()=>{}});
 save.change();const done=save.flush();value='B';save.change();assert.equal(save.pending,true);assert(!states.includes('saved'));
 gate.resolve();await done;assert.deepEqual(writes,['A','B']);assert.equal(states.at(-1),'saved');assert.equal(save.pending,false);
});
test('conflict or lost response blocks automatic retry and retains latest input until explicit recovery',async()=>{
 let value='A',fail=true;const writes=[];
 const save=autoSave({read:()=>value,write:async v=>{writes.push(v);if(fail)throw Error('Conflict');},onState:()=>{},schedule:()=>0,cancel:()=>{}});
 save.change();await assert.rejects(save.flush(),/Conflict/);value='B';save.change();await assert.rejects(save.flush());assert.deepEqual(writes,['A']);assert(save.pending);
 fail=false;await save.retry();assert.deepEqual(writes,['A','B']);assert.equal(save.pending,false);
});
test('leaving awaits the pending write; stopping prevents scheduled writes on a different screen',async()=>{
 const gate=deferred();let callback,writes=0;
 const save=autoSave({read:()=>1,write:async()=>{writes++;await gate.promise;},onState:()=>{},schedule:fn=>(callback=fn),cancel:()=>{}});
 save.change();let left=false;const leaving=save.flush().then(()=>left=true);await Promise.resolve();assert.equal(left,false);gate.resolve();await leaving;assert(left);
 save.change();save.stop();callback();await Promise.resolve();assert.equal(writes,1);
});

test("uncertain acknowledgements compare JSONB structurally without ignoring array order",()=>{assert(sameJSON({a:1,b:[{x:2,y:3}]},{b:[{y:3,x:2}],a:1}));assert(!sameJSON({a:[1,2]},{a:[2,1]}));assert(!sameJSON({a:1},{a:2}));});
