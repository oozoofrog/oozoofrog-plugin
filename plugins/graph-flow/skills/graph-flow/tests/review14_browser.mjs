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
  await evaluate(`document.querySelector('.panel-body').scrollTop=25;document.querySelector('#find-text').focus()`);
  const focus=await evaluate('document.activeElement.id'),scroll=await evaluate("document.querySelector('.panel-body').scrollTop");
  await evaluate("document.dispatchEvent(new Event('visibilitychange'))");await delay(500);
  assert.deepEqual(await position(),before,'polling keeps the selected view');
  assert.equal(await evaluate('document.activeElement.id'),focus);
  assert.equal(await evaluate("document.querySelector('.panel-body').scrollTop"),scroll);
  await evaluate(`[...document.querySelectorAll('.map-toolbar button')].find(b=>b.dataset.action==='fit').click()`);await delay(150);
  assert(await evaluate(`(()=>{const v=document.querySelector('.map-viewport').getBoundingClientRect();return (Number(document.querySelector('#map').dataset.scale)>=6/7 && [...document.querySelectorAll('.map-overflow button')].some(b=>!b.hidden&&/→|↓|←|↑/.test(b.textContent))) || [...document.querySelectorAll('#map .node-card')].every(e=>{const r=e.getBoundingClientRect();return r.left>=v.left-.5&&r.right<=v.right+.5&&r.top>=v.top-.5&&r.bottom<=v.bottom+.5;});})()`),'fit with side panel contains every complete card or provides directions at the readable floor');
  // E1–E6: actual rectangles, not just stylesheet declarations.
  for(const width of [1440,1000,800]) {
    await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});await delay(100);
    for(const label of ['상세 보기','간략 보기','화면에 맞추기']) {
      await evaluate(`[...document.querySelectorAll('.map-toolbar button')].find(b=>b.textContent===${JSON.stringify(label)}||(${JSON.stringify(label)}==='화면에 맞추기'&&b.dataset.action==='fit')).click()`);await delay(100);
      assert(await evaluate(`(()=>{const e=document.querySelector('.map-visible'),r=e.getBoundingClientRect(),t=document.querySelector('.map-toolbar').getBoundingClientRect();return e.scrollWidth<=e.clientWidth+1&&r.left>=t.left&&r.right<=t.right})()`),'E1 whole count phrases fit the toolbar');
      assert(await evaluate(`(()=>{const e=document.querySelector('#map [data-node="n0"]'),r=e.getBoundingClientRect(),v=document.querySelector('.map-viewport').getBoundingClientRect();return r.left>=v.left&&r.right<=v.right&&r.top>=v.top&&r.bottom<=v.bottom})()`),'E3 selected card survives fit and level changes');
      assert(await evaluate(`(()=>{const v=document.querySelector('.map-viewport');return getComputedStyle(v).scrollbarGutter==='stable both-edges'&&v.offsetWidth>v.clientWidth})()`),'E5 reserve scrollbar gutter');
      assert(await evaluate(`[...document.querySelectorAll('#map .node-card')].every(e=>e.scrollHeight<=e.clientHeight+1 && e.getBoundingClientRect().height<=e.parentElement.getBoundingClientRect().height+1)`),'E6 measured content fits every card');
    }
    await evaluate(`document.querySelector('.panel-body').scrollTo(0,180)`);await delay(150);
    assert(await evaluate(`(()=>{const b=document.querySelector('.panel-bar').getBoundingClientRect(),p=document.querySelector('.panel-body').getBoundingClientRect();return b.bottom<=p.top+.5&&document.querySelector('.panel-bar').textContent.includes('안내 단계 0')})()`),'E2 header and selected title stay outside the scroll surface');
    assert(await evaluate(`(()=>{const b=document.querySelector('.panel-body'),top=b.getBoundingClientRect().top;return [...b.querySelectorAll('p,h3,summary,pre')].filter(e=>e.getClientRects().length).every(e=>{const r=document.createRange();r.selectNodeContents(e);const t=r.getBoundingClientRect();return !(t.top<top-.5&&t.bottom>top+.5)})})()`),'E2 no letters are clipped at the top after scrolling');
  }
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
  assert(await evaluate(`(()=>{const p=document.querySelector('#panel').getBoundingClientRect(),a=document.querySelector('.plan-actions').getBoundingClientRect();return p.bottom<=a.top&&getComputedStyle(document.querySelector('#accessible')).visibility==='hidden'&&getComputedStyle(document.querySelector('#flow'),'::before').position==='fixed'})()`),'E4 phone overlay closes the gap above the action bar '+JSON.stringify(await evaluate(`({panel:document.querySelector('#panel').getBoundingClientRect().toJSON(),actions:document.querySelector('.plan-actions').getBoundingClientRect().toJSON(),accessible:getComputedStyle(document.querySelector('#accessible')).visibility,backdrop:getComputedStyle(document.querySelector('#flow'),'::before').position,height:document.body.style.getPropertyValue('--plan-actions-height'),css:['position','top','bottom','height','minHeight','maxHeight'].map(k=>[k,getComputedStyle(document.querySelector('#panel'))[k]])})`)));
  assert.deepEqual(errors,[]);
} finally {
  ws?.close();
  if(chrome.exitCode===null){const exited=new Promise(r=>chrome.once('exit',r));chrome.kill();await exited;}
}
