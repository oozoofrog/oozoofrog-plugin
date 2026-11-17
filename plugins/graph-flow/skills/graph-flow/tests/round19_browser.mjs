import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {readFileSync} from 'node:fs';
const config=JSON.parse(readFileSync(process.argv[2]));
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const chrome=spawn(config.chrome,['--headless=new','--remote-debugging-port=0','--user-data-dir='+config.profile,'about:blank'],{stdio:['ignore','ignore','pipe']});
let ws;
const timeout=setTimeout(()=>{ws?.close();chrome.kill();},80000);
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
  const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP timeout: '+method));},15000);pending.set(id,[value=>{clearTimeout(timer);resolve(value)},error=>{clearTimeout(timer);reject(error)}]);ws.send(JSON.stringify({id,method,params}));});
  const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});assert(!r.exceptionDetails,JSON.stringify(r.exceptionDetails));return r.result?.value;};
  await send('Page.enable');await send('Runtime.enable');
  const hook=await send('Page.addScriptToEvaluateOnNewDocument',{source:`
    const originalFetch=window.fetch;
    window.fetch=async (...args)=>{const r=await originalFetch(...args);if(!String(args[0]).startsWith('/api/run'))return r;
      const data=await r.json(),v=data.view,mode=sessionStorage.getItem('test-mode')||'plan';
      if(mode!=='plan'){v.plan_approval={...v.plan_approval,status:'answered',verified:true,outcome:'approved'};v.decisions=[];}
      if(mode==='done'){v.complete=true;v.nodes.forEach(n=>n.status='passed');}
      if(mode==='running')v.nodes.forEach(n=>n.status='running');
      if(mode==='changed')v.plan_approval={...v.plan_approval,status:'open',verified:false};
      if(mode==='old'){v.plan_approval=null;v.legacy=true;}
      return new Response(JSON.stringify(data),{status:r.status,headers:r.headers});};`});
  const url=config.url+'#'+new URLSearchParams({project:config.project,run:config.run});
  const ready=async()=>{for(let i=0;i<80;i++){if(await evaluate("document.querySelectorAll('#phone-flow .node-card').length===4"))return;await delay(50);}assert.fail('cards did not load');};
  for(const [width,height] of [[1440,900],[1024,700],[390,844]]) {
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
    for(const mode of ['plan','running','done','changed','old']) {
      await send('Page.navigate',{url});await ready();
      await evaluate(`sessionStorage.setItem('test-mode',${JSON.stringify(mode)})`);
      await send('Page.navigate',{url});await ready();await delay(80);
      if(width===390&&mode==='plan'){
        const bottom=await evaluate('document.documentElement.scrollHeight');
        for(let y=0;y<bottom;y+=180){await evaluate(`window.scrollTo(0,${y})`);await delay(15);}
        assert(await evaluate("!document.querySelector('.plan-actions button.primary').disabled"),'U2 tall phone cards can be read by scrolling');
        await evaluate('window.scrollTo(0,0)');
      }
      if(width===390&&mode==='plan')assert(await evaluate("document.querySelector('.plan-actions').getBoundingClientRect().height<=innerHeight*.45"),'Q3 choices and consequences leave room for the question');
      for(const id of ['n0','n1','n2','_run_checks']) {
        await evaluate(`document.querySelector(${JSON.stringify((width<761?'#phone-flow':'#map')+' [data-node="'+id+'"] .node-header')}).click()`);
        const audit=await evaluate(`(()=>{const e=document.querySelector('.panel-intro .node-sentence'),r=e.getBoundingClientRect(),intro=e.parentElement;return {text:e.textContent,first:intro.children[1]===e,inside:r.top>=0&&r.left>=0&&r.bottom<=innerHeight&&r.right<=innerWidth,rect:r.toJSON()}})()`);
        assert(audit.first&&audit.inside,JSON.stringify({width,height,mode,id,audit}));
        if(id!=='_run_checks')assert.equal(audit.text.length,300);
        const check=async()=>{const bad=await evaluate(`(()=>{const selector=document.querySelector('#flow').classList.contains('phone-diagram')?'#map .node-card':${JSON.stringify(width<761?'#phone-flow .node-card':'#map .node-card')};return [...document.querySelectorAll(selector)].flatMap(c=>[c,...c.querySelectorAll('*')]).filter(e=>e.clientWidth&&e.clientHeight&&(e.scrollWidth>e.clientWidth+1||e.scrollHeight>e.clientHeight+1||(!e.children.length&&e.textContent.trim().endsWith('…')))).map(e=>({tag:e.tagName,cls:e.className,text:e.textContent,width:[e.scrollWidth,e.clientWidth],height:[e.scrollHeight,e.clientHeight]}))})()`);assert.deepEqual(bad,[],JSON.stringify({width,mode,id,bad}));};
        if(width<761)await evaluate("document.querySelector('#phone-view-toggle').click()");
        for(const label of ['상세 보기','간략 보기']){await evaluate(`[...document.querySelectorAll('.map-toolbar button')].find(b=>b.textContent===${JSON.stringify(label)}).click()`);await delay(30);await check();
          if(width>=761)assert(await evaluate(`(()=>{const v=document.querySelector('.map-viewport'),r=v.getBoundingClientRect(),left=r.left+v.clientLeft,top=r.top+v.clientTop;const count=[...document.querySelectorAll('#map .node-title')].filter(e=>{if(getComputedStyle(e).visibility==='hidden')return false;const range=document.createRange();range.selectNodeContents(e);const b=range.getBoundingClientRect();return b.left>=left-.5&&b.right<=left+v.clientWidth+.5&&b.top>=top-.5&&b.bottom<=top+v.clientHeight+.5}).length;return document.querySelector('.map-visible').textContent.includes(count+'개 제목')})()`),'V3 visible title count agrees with glyph bounds');
        }
        if(width>=761&&mode==='plan'){
          const bad=await evaluate(`(()=>{const v=document.querySelector('.map-viewport');v.scrollLeft+=31;v.scrollTop+=31;v.dispatchEvent(new Event('scroll'));const r=v.getBoundingClientRect(),top=r.top+v.clientTop,bottom=top+v.clientHeight;return [...document.querySelectorAll('#map .node-title,#map .node-essentials p')].filter(e=>{if(getComputedStyle(e).visibility==='hidden')return false;const range=document.createRange();range.selectNodeContents(e);return [...range.getClientRects()].some(l=>l.top<top-.5&&l.bottom>top+.5||l.top<bottom-.5&&l.bottom>bottom+.5)&&!e.style.clipPath;}).map(e=>e.textContent)})()`);assert.deepEqual(bad,[],'U2 viewport edges never bisect visible letters');
        }
        await evaluate("document.querySelector('.panel-close').click()");await check();
        if(width<761)assert(await evaluate("document.querySelector('#map').getBoundingClientRect().width>=innerWidth-48"),'Phone diagram uses the full content width below its toggle');
        if(width<761)await evaluate("document.querySelector('#phone-view-toggle').click()");
      }
    }
  }
  assert.deepEqual(errors,[]);
} finally {
  clearTimeout(timeout);
  ws?.close();
  if(chrome.exitCode===null){const exited=new Promise(r=>chrome.once('exit',r));chrome.kill();await exited;}
}
