import test from 'node:test';
import assert from 'node:assert/strict';
import {newProject,newDocument,reviewDocument,changeDocument} from '../../site/browser/model.mjs';
import {nextStep} from '../../site/browser/onboarding.mjs';
test('guidance advances from empty to selection and review without mutating project',()=>{
 const p=newProject('Own software');assert.equal(nextStep(p).key,'content');
 p.documents.push(newDocument('Start','Own text'));const before=JSON.stringify(p);
 assert.equal(nextStep(p).key,'selection');assert.equal(JSON.stringify(p),before);
 p.documents[0].publish=true;assert.equal(nextStep(p).key,'review');
 reviewDocument(p.documents[0],'Checked own text');assert.equal(nextStep(p).key,'status');
 assert.equal(nextStep(p,null,'ready').key,'publish');
});
test('unselected drafts do not block, but changed selected versions require review',()=>{
 const p=newProject('Own software'),d=newDocument('Start','Own text');d.publish=true;reviewDocument(d,'Checked');p.documents.push(d,newDocument('Private','Not ready'));
 assert.equal(nextStep(p,null,'ready').key,'publish');changeDocument(d,d.title,'Changed');assert.equal(nextStep(p,null,'ready').key,'review');
});
test('publication unavailable, withdrawn, current and changed states stay distinct',()=>{
 const p=newProject('Own software'),d=newDocument('Start','Own text');d.publish=true;reviewDocument(d,'Checked');p.documents.push(d);p.version=5;
 assert.equal(nextStep(p,null,'error').target,'retry-publication');
 assert.equal(nextStep(p,{live:false,source_version:5},'ready').key,'publish');
 assert.equal(nextStep(p,{live:true,source_version:5},'loading').key,'status');
 assert.equal(nextStep(p,{live:true,source_version:5},'ready').key,'live');
 assert.equal(nextStep(p,{live:true,source_version:4},'ready').key,'update');
 assert.equal(nextStep(p,null,'ready',false).key,'export');
});
