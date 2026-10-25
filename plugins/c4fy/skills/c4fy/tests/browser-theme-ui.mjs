import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import {resolve,join} from 'node:path';
import {mkdirSync} from 'node:fs';
const {chromium}=await import(process.env.C4FY_PLAYWRIGHT_PATH?pathToFileURL(process.env.C4FY_PLAYWRIGHT_PATH).href:'playwright');
import {writeFileSync} from 'node:fs';
const base=resolve(process.argv[2]),out=resolve(process.argv[3]);mkdirSync(out,{recursive:true});
const b=await chromium.launch({channel:'chrome',headless:true});const p=await b.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'}),rows=[],errors=[];p.on('pageerror',e=>errors.push(e.message));await p.goto(pathToFileURL(base).href+'#containers');
for(const design of ['default','cyber','nouveau','bauhaus','rams','ive','material','liquid']){
 await p.locator('#design-picker').click();await p.locator('.design-choice[data-design='+design+']').click();await p.keyboard.press('Escape');
 for(const mode of (design==='cyber'?['dark']:['light','dark'])){
 if(await p.locator('html').getAttribute('data-theme')!==mode)await p.locator('#theme').click();
 for(const [width,height]of [[1440,900],[390,844],[320,568]]){await p.setViewportSize({width,height});await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
 const metrics=await p.evaluate(()=>{
 const ctx=document.createElement('canvas').getContext('2d');function rgb(c){ctx.clearRect(0,0,1,1);ctx.fillStyle=c;ctx.fillRect(0,0,1,1);return [...ctx.getImageData(0,0,1,1).data].slice(0,3)}function lum(c){return rgb(c).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0)}function contrast(a,b){const x=lum(a),y=lum(b);return +((Math.max(x,y)+.05)/(Math.min(x,y)+.05)).toFixed(2)}
 const ns=[...document.querySelectorAll('.scene .node')],stage=getComputedStyle(document.querySelector('#stage')),root=getComputedStyle(document.documentElement),edge=document.querySelector('.scene .edge'),nodes=ns.map(n=>{const c=getComputedStyle(n),t=getComputedStyle(n.querySelector('.node-description')),rect=n.getBoundingClientRect();return {id:n.dataset.id,fill:c.backgroundColor,image:c.backgroundImage,border:c.borderColor,radius:c.borderRadius,shadow:c.boxShadow,contrast:contrast(c.color,c.backgroundColor),mutedContrast:contrast(t.color,c.backgroundColor),font:c.fontFamily,px:rect.width/n.offsetWidth*parseFloat(t.fontSize)}});
 return {pageOverflow:document.documentElement.scrollWidth>innerWidth||document.documentElement.scrollHeight>innerHeight,nodes,edgeContrast:edge?contrast(getComputedStyle(edge).stroke,root.getPropertyValue('--surface')):null,detailsOverflow:document.querySelector('#details').scrollHeight>document.querySelector('#details').clientHeight,navOverflow:document.querySelector('.detail-heading').scrollWidth>document.querySelector('.detail-heading').clientWidth};
 });assert.equal(metrics.pageOverflow,false);assert.equal(metrics.navOverflow,false);for(const n of metrics.nodes)assert.ok(n.mutedContrast>=4.5,`${design}/${mode}/${n.id}: ${n.mutedContrast}`);assert.ok(metrics.edgeContrast>=3);rows.push({design,mode,width,...metrics});if(width===1440||width===320)await p.screenshot({path:join(out,`${design}-${mode}-${width}.png`)});
 }
 }
 await p.setViewportSize({width:1440,height:900});
 await p.locator('.scene .node[data-id=state]').click();await p.mouse.move(10,10);
 const node=p.locator('.scene .node[data-id=controller]');const before=await node.evaluate(n=>getComputedStyle(n).outlineStyle);await node.click();await p.mouse.move(10,10);const after=await node.evaluate(n=>getComputedStyle(n).outlineStyle);assert.equal(before,'none');assert.equal(after,'solid');
 const actual=await node.evaluate(n=>{const c=getComputedStyle(n);return {font:c.fontFamily,radius:c.borderRadius,image:c.backgroundImage,outline:c.outlineWidth}});
 assert.equal(await p.locator('.scene .node[data-id=codex]').evaluate(n=>getComputedStyle(n).borderTopStyle),'dashed');if(design==='nouveau')assert.ok(actual.radius.includes('8px'));if(design==='liquid')assert.ok(actual.image.includes('linear-gradient'));
 const dl=p.waitForEvent('download');await p.locator('#svg-export').click();const download=await dl;await download.saveAs(join(out,design+'.svg'));
 const svg=(await import('node:fs')).readFileSync(join(out,design+'.svg'),'utf8');const exported=await p.evaluate(s=>{const d=new DOMParser().parseFromString(s,'image/svg+xml');return {error:!!d.querySelector('parsererror'),font:d.documentElement.getAttribute('font-family'),gradient:!!d.querySelector('linearGradient'),shadow:!!d.querySelector('feDropShadow'),widths:[...d.querySelectorAll('[stroke-width]')].map(n=>n.getAttribute('stroke-width'))};},svg);
 assert.equal(exported.error,false);assert.equal(exported.font,actual.font);assert.ok(exported.shadow);if(design==='liquid')assert.ok(exported.gradient);if(design==='bauhaus')assert.ok(exported.widths.includes('2'));if(design==='cyber')assert.ok(exported.widths.includes('3px'));
 rows.push({design,selection:{before,after},exported});await p.keyboard.press('Escape');

}
assert.deepEqual(errors,[]);assert.ok(rows.some(r=>r.design==='cyber'&&r.mode==='dark'));assert.ok(!rows.some(r=>r.design==='cyber'&&r.mode==='light'));
writeFileSync(join(out,'metrics.json'),JSON.stringify({errors,rows},null,2));console.log(JSON.stringify({errors,rows:rows.length}));await b.close();
