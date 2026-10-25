import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const cli=new URL('../bin/c4fy.mjs',import.meta.url).pathname;
const sample={version:1,title:'Test',elements:[{id:'user',kind:'person',name:'User',description:'Uses the system'},{id:'app',kind:'system',name:'App',description:'A real system'}],relationships:[{id:'uses',source:'user',target:'app',description:'Uses'}],views:[{id:'context',level:1,scope:'app',title:'Context',nodes:['user','app'],relationships:['uses']}]};
function run(args){return spawnSync(process.execPath,[cli,...args],{encoding:'utf8'});}
test('CLI writes standalone HTML with exact-byte receipt',()=>{const d=mkdtempSync(join(tmpdir(),'c4fy-'));try{const input=join(d,'model.json'),output=join(d,'diagram.html');writeFileSync(input,JSON.stringify(sample));const r=run(['render',input,output]);assert.equal(r.status,0,r.stderr);const receipt=JSON.parse(r.stdout);assert.equal(receipt.artifact.sha256,createHash('sha256').update(readFileSync(output)).digest('hex'));assert.equal(receipt.visualReview,'not-run');assert.equal(receipt.browserEvidence,'not-run');}finally{rmSync(d,{recursive:true,force:true});}});
test('failed validation preserves an existing output and receipt',()=>{const d=mkdtempSync(join(tmpdir(),'c4fy-'));try{const input=join(d,'model.json'),output=join(d,'diagram.html');writeFileSync(input,JSON.stringify({...sample,views:[]}));writeFileSync(output,'last-good');writeFileSync(output+'.receipt.json','receipt');const r=run(['render',input,output]);assert.notEqual(r.status,0);assert.match(r.stderr,/At least one element and view required/);assert.equal(readFileSync(output,'utf8'),'last-good');assert.equal(readFileSync(output+'.receipt.json','utf8'),'receipt');}finally{rmSync(d,{recursive:true,force:true});}});
test('unknown CLI flags are errors',()=>{const r=run(['validate','missing.json','--trust-me']);assert.notEqual(r.status,0);assert.match(r.stderr,/Unknown/);});
test('receipt path cannot replace the source specification',()=>{const d=mkdtempSync(join(tmpdir(),'c4fy-'));try{const output=join(d,'diagram.html'),input=output+'.receipt.json',source=JSON.stringify(sample);writeFileSync(input,source);const r=run(['render',input,output]);assert.notEqual(r.status,0);assert.equal(readFileSync(input,'utf8'),source);}finally{rmSync(d,{recursive:true,force:true});}});
