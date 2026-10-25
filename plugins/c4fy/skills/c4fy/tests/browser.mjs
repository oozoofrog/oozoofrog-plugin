// Optional development verification; the generated HTML needs no Playwright.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const input=resolve(process.argv[2]||''),out=resolve(process.argv[3]||'c4fy-browser-evidence');
const {chromium}=await import(process.env.C4FY_PLAYWRIGHT_PATH?pathToFileURL(process.env.C4FY_PLAYWRIGHT_PATH).href:'playwright');
mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,...(process.env.C4FY_CHROME?{executablePath:process.env.C4FY_CHROME}:{channel:'chrome'})});
const context=await browser.newContext({viewport:{width:1440,height:1000},colorScheme:'light',reducedMotion:'no-preference',acceptDownloads:true});
const page=await context.newPage(),errors=[],requests=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
const bytes=readFileSync(input),receipt={schemaVersion:1,status:'running',artifact:{path:input,sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length},checks:[],screenshots:[],visualReview:'pending'};
const check=(name,details)=>receipt.checks.push({name,status:'pass',...details});
try{
 await page.goto(pathToFileURL(input).href);await page.locator('.scene .node').first().waitFor();
 assert.equal(errors.length,0,errors.join('\n'));check('initial-render');
 const viewIDs=await page.evaluate(()=>JSON.parse(document.getElementById('c4fy-data').textContent).model.views.map(v=>({id:v.id,level:v.level})));
 async function go(v){await page.locator(`.tab[data-level="${v.level}"]`).click();if(await page.locator('#view-select option').count()>1)await page.selectOption('#view-select',v.id);await page.waitForFunction(id=>document.querySelector('.scene:not(.old)')?.dataset.view===id,v.id);await page.waitForTimeout(650);}
 for(const viewport of [{width:1440,height:900},{width:1600,height:1000},{width:1920,height:1080},{width:2048,height:1320},{width:390,height:844}]){
  await page.setViewportSize(viewport);await page.waitForTimeout(100);
  for(const v of viewIDs){await go(v);const metrics=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,scenes:document.querySelectorAll('.scene').length,nodes:document.querySelectorAll('.scene .node').length,stage:document.querySelector('#stage').getBoundingClientRect().toJSON(),nodeWidths:[...document.querySelectorAll('.scene .node')].map(n=>n.getBoundingClientRect().width)}));assert.ok(metrics.scrollWidth<=viewport.width,JSON.stringify(metrics));assert.equal(metrics.scenes,1);check(`viewport-${viewport.width}-${viewport.height}-${v.id}`,metrics);
   if(viewport.width===1440||viewport.width===390){const file=`${v.id}-${viewport.width}-light.png`;await page.screenshot({path:join(out,file),fullPage:true});receipt.screenshots.push(file);}}
 }
 await page.setViewportSize({width:1440,height:1000});await go(viewIDs[0]);
 // Measure real interpolation, not merely the presence of animation declarations.
 const scope=await page.evaluate(()=>JSON.parse(document.getElementById('c4fy-data').textContent).model.views[1].scope);
 const oldBox=await page.locator(`.scene .node[data-id="${scope}"]`).boundingBox();
 await page.locator('.tab[data-level="2"]').click();await page.waitForTimeout(45);
 const motion=await page.evaluate(()=>({count:document.getAnimations().filter(a=>a.playState==='running').length,transforms:[...document.querySelectorAll('.scene:not(.old) .node')].map(n=>getComputedStyle(n).transform)}));assert.ok(motion.count>0,JSON.stringify(motion));
 await page.screenshot({path:join(out,'transition-c1-c2.png'),fullPage:true});receipt.screenshots.push('transition-c1-c2.png');await page.waitForTimeout(650);
 const boundary=await page.locator('.scene .scope-box').boundingBox();assert.ok(boundary.width>oldBox.width&&boundary.height>oldBox.height);check('semantic-transition',{runningAnimations:motion.count,from:oldBox,to:boundary});
 await page.locator('.tab[data-level="3"]').click();await page.locator('.tab[data-level="1"]').click();await page.locator('.tab[data-level="2"]').click();await page.waitForTimeout(700);assert.equal(await page.locator('.scene').count(),1);assert.equal(await page.locator('.scene').getAttribute('data-view'),viewIDs.find(v=>v.level===2).id);check('rapid-navigation-last-selection-wins');
 await page.emulateMedia({reducedMotion:'reduce'});await page.locator('.tab[data-level="3"]').click();assert.equal(await page.locator('.scene').count(),1);assert.equal(await page.evaluate(()=>document.getAnimations().filter(a=>a.playState==='running').length),0);check('reduced-motion');
 await page.locator('#search').fill('not-a-matching-node-xyz');assert.equal(await page.locator('.empty-search').count(),1);await page.locator('#search').press('Escape');assert.equal(await page.locator('.empty-search').count(),0);check('search-and-escape');
 await page.locator('.scene .node').first().click();assert.equal(await page.locator('.scene .node[aria-pressed="true"]').count(),1);check('node-details');
 await page.locator('.tab[aria-selected="true"]').focus();await page.keyboard.press('ArrowLeft');assert.equal(await page.locator('.tab[aria-selected="true"]').getAttribute('data-level'),'2');check('keyboard-navigation');
 for(const [button,filename] of [['#svg-export','diagram.svg'],['#json-export','model.json']]){const downloadPromise=page.waitForEvent('download');await page.locator(button).click();const download=await downloadPromise;await download.saveAs(join(out,filename));const content=readFileSync(join(out,filename),'utf8');if(filename.endsWith('.json'))JSON.parse(content);else{const parsed=await page.evaluate(s=>new DOMParser().parseFromString(s,'image/svg+xml').querySelector('parsererror')?.textContent||'',content);assert.equal(parsed,'');assert.ok(!content.includes('<script'));}check(`export-${filename}`);}
 await page.locator('#theme').click();assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');for(const v of viewIDs){await go(v);const file=`${v.id}-1440-dark.png`;await page.screenshot({path:join(out,file),fullPage:true});receipt.screenshots.push(file);}check('dark-theme');
 assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);check('no-runtime-errors-or-network-requests');receipt.status='pass';
}catch(error){receipt.status='fail';receipt.error=error.stack;await page.screenshot({path:join(out,'failure.png'),fullPage:true}).catch(()=>{});process.exitCode=1;}
finally{await browser.close();writeFileSync(join(out,'browser-receipt.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify({status:receipt.status,checks:receipt.checks.length,error:receipt.error,receipt:join(out,'browser-receipt.json')}));}
