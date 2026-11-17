import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {readFileSync} from 'node:fs';
const config=JSON.parse(readFileSync(process.argv[2]));
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const chrome=spawn(config.chrome,['--headless=new','--remote-debugging-port=0','--user-data-dir='+config.profile,'about:blank'],{stdio:['ignore','ignore','pipe']});
let ws;
try {
  const endpoint=await new Promise((resolve,reject)=>{
    chrome.on('error',reject);
    chrome.stderr.on('data',b=>{const m=String(b).match(/DevTools listening on (ws:\/\/\S+)/);if(m)resolve(m[1]);});
  });
  const targets=await (await fetch('http://127.0.0.1:'+new URL(endpoint).port+'/json')).json();
  ws=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
  await new Promise(r=>ws.onopen=r);
  let sequence=0;const pending=new Map(),errors=[];
  ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text);if(pending.has(m.id)){const [resolve,reject]=pending.get(m.id);pending.delete(m.id);m.error?reject(Error(JSON.stringify(m.error))):resolve(m.result);}};
  const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;pending.set(id,[resolve,reject]);ws.send(JSON.stringify({id,method,params}));});
  const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});assert(!r.exceptionDetails,JSON.stringify(r.exceptionDetails));return r.result?.value;};
  await send('Page.enable');await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:config.url+'#'+new URLSearchParams({project:config.project,run:config.run})});
  let ready=false;
  for(let i=0;i<80;i++){ready=await evaluate("document.querySelectorAll('#map .node-card').length===13");if(ready)break;await delay(100);}
  assert(ready,'twelve planned pieces and final card render');await delay(300);
  const bounds=await evaluate(`(()=>{const v=document.querySelector('.map-viewport').getBoundingClientRect();return [...document.querySelectorAll('#map .node-card')].map(e=>{const r=e.getBoundingClientRect();return {id:e.dataset.node,rect:r.toJSON(),viewport:v.toJSON(),scale:document.querySelector('#map').dataset.scale,stage:document.querySelector('.map-stage').style.cssText,position:e.parentElement.style.cssText,inside:r.x>=v.x-.5&&r.right<=v.right+.5&&r.y>=v.y-.5&&r.bottom<=v.bottom+.5}})})()`);
  assert(bounds.every(b=>b.inside),JSON.stringify(bounds));
  const position=()=>evaluate(`(()=>{const m=document.querySelector('#map'),v=document.querySelector('.map-viewport'),s=document.querySelector('.map-stage');return {level:m.dataset.level,scale:m.dataset.scale,x:v.scrollLeft,y:v.scrollTop,origin:s.style.left+','+s.style.top}})()`);
  const before=await position();
  await evaluate(`document.querySelector('#map [data-node="n0"] .node-header').click()`);
  assert.deepEqual(await position(),before,'selecting a still-visible card preserves level, scale and position');
  await evaluate(`document.querySelector('#panel').scrollTop=25;document.querySelector('#find-text').focus()`);
  const focus=await evaluate('document.activeElement.id'),scroll=await evaluate("document.querySelector('#panel').scrollTop");
  await evaluate("document.dispatchEvent(new Event('visibilitychange'))");await delay(500);
  assert.deepEqual(await position(),before,'polling keeps the selected view');
  assert.equal(await evaluate('document.activeElement.id'),focus);
  assert.equal(await evaluate("document.querySelector('#panel').scrollTop"),scroll);
  await evaluate(`[...document.querySelectorAll('.map-toolbar button')].find(b=>b.textContent==='화면에 맞추기').click()`);await delay(150);
  assert(await evaluate(`(()=>{const v=document.querySelector('.map-viewport').getBoundingClientRect();return [...document.querySelectorAll('#map .node-card')].every(e=>{const r=e.getBoundingClientRect();return r.left>=v.left-.5&&r.right<=v.right+.5&&r.top>=v.top-.5&&r.bottom<=v.bottom+.5;});})()`),'fit with side panel contains every complete card');
  await evaluate(`document.querySelector('#accessible').open=true`);await delay(100);
  assert(await evaluate(`document.querySelector('.plan-actions button.primary').disabled`),'list view cannot approve');
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:config.url+'#'+new URLSearchParams({project:config.project,run:config.run})});
  for(let i=0;i<80;i++){if(await evaluate(`document.querySelectorAll('#phone-flow .node-card').length===13`))break;await delay(100);}
  assert(await evaluate(`document.querySelector('.plan-actions button.primary').disabled`),'phone starts locked');
  assert(await evaluate(`!!document.querySelector('.plan-actions .action-hint').textContent`),'lock has a visible reason');
  const bottom=await evaluate('document.documentElement.scrollHeight');
  for(let y=0;y<bottom;y+=120){await evaluate(`window.scrollTo(0,${y})`);await delay(50);}
  assert(await evaluate(`!document.querySelector('.plan-actions button.primary').disabled`),'reading all phone cards unlocks approval');
  await evaluate(`document.querySelector('#phone-flow [data-node="n0"] .node-header').click()`);await delay(100);
  assert(await evaluate(`document.querySelector('.plan-actions button.primary').disabled`),'detail overlay cannot approve');
  assert.deepEqual(errors,[]);
} finally {
  ws?.close();
  if(chrome.exitCode===null){const exited=new Promise(r=>chrome.once('exit',r));chrome.kill();await exited;}
}
