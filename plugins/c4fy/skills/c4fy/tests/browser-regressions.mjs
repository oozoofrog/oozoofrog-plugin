import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import assert from 'node:assert/strict';
const {chromium}=await import(process.env.C4FY_PLAYWRIGHT_PATH?pathToFileURL(process.env.C4FY_PLAYWRIGHT_PATH).href:'playwright');
const browser=await chromium.launch({headless:true,channel:'chrome'});
const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});const failures=[];
const check=(name,fn)=>{try{fn();console.log('PASS',name);}catch(e){failures.push(name+': '+e.message);}};
try{
 await page.goto(pathToFileURL(resolve(process.argv[2])).href);await page.locator('.node').first().waitFor();
 const metrics=await page.locator('.node').first().evaluate(n=>{const r=n.getBoundingClientRect(),i=n.querySelector('.node-icon').getBoundingClientRect();return {width:r.width,inset:i.left-r.left};});
 check('mobile cards stay readable',()=>assert.ok(metrics.width>=170,JSON.stringify(metrics)));
 check('icons follow node padding',()=>assert.ok(metrics.inset>=8,JSON.stringify(metrics)));
 const compactVisible=await page.locator('.relations').getAttribute('open');check('compact edge labels expose relationship key',()=>assert.notEqual(compactVisible,null));
 await page.locator('.tab[data-level="2"]').click();
}catch(e){failures.push(e.message);}
// Keep async assertions outside the synchronous check helper.
const selfDrill=await page.locator('#details [data-view="containers"]').count();check('current scope button is absent',()=>assert.equal(selfDrill,0));
await page.goto(pathToFileURL(resolve(process.argv[2])).href+'#%zz');await page.reload();
const ready=await page.locator('.node').count();check('invalid hash cannot stop initialization',()=>assert.ok(ready>0));
await page.setViewportSize({width:1440,height:1000});await page.emulateMedia({reducedMotion:'no-preference'});await page.waitForTimeout(60);await page.locator('.tab[data-level="2"]').click();await page.waitForTimeout(320);const outgoing=await page.locator('.scene.old').evaluateAll(nodes=>nodes.map(n=>Number(getComputedStyle(n).opacity)));check('outgoing view stays faded until shared motion completes',()=>assert.ok(outgoing.length===0||outgoing.every(n=>n<.01),JSON.stringify(outgoing)));await browser.close();if(failures.length){console.error(failures.join('\n'));process.exitCode=1;}
