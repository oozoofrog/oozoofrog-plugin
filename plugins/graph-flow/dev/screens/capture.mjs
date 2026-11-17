#!/usr/bin/env node
// CDP transport and Chrome discovery follow tests/review14_browser.mjs and its wrapper.
import assert from 'node:assert/strict';
import {spawn, spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync, copyFileSync, readdirSync, unlinkSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const skill = path.resolve(here, '../../skills/graph-flow');
const output = path.resolve(process.argv[2] || '');
assert(process.argv[2] && !/^\/(private\/)?tmp\//.test(output), 'supply a durable output directory');
const only = process.argv[3] ? new Set(process.argv[3].split(',').map(Number)) : null;
const manifest = JSON.parse(readFileSync(path.join(here, 'screens.json')));
const fixtures = JSON.parse(readFileSync(path.join(output, 'fixtures/index.json')));
const which = name => (process.env.PATH || '').split(path.delimiter).map(p => path.join(p, name)).find(p => existsSync(p));
const chromePath = which('chromium') || which('google-chrome') || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
assert(existsSync(chromePath), 'headless Chrome is required; see test_review14_browser.py');
const ffmpeg = which('ffmpeg');
assert(ffmpeg, 'ffmpeg is required for verification images');
const python = process.env.SCREENS_PYTHON || which('python3');
const final = path.join(output, 'final'), verify = path.join(output, 'verify');
mkdirSync(final, {recursive:true}); mkdirSync(verify, {recursive:true});
const runtime = mkdtempSync(path.join(output, 'capture-'));
const profile = path.join(runtime, 'chrome-profile');
const delay = ms => new Promise(r => setTimeout(r, ms));
const baseEnv = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GF_')));
const envFor = fixture => ({...baseEnv, GF_HOME:fixture.home, GF_NO_OPEN:'1', GF_ROLE:'leader', GF_SESSION:'screens-r19'});
const evidence = path.join(output, 'screen-status.json');
let records = only && existsSync(evidence) ? JSON.parse(readFileSync(evidence)) : [];
const owned = [], lifecycle = [];
let chrome, ws, sequence = 0;
const pending = new Map(), errors = [];
let activeServer;
const persist = () => writeFileSync(evidence, JSON.stringify(records, null, 2) + '\n');
function start(command, args, options={}) {
  const child = spawn(command, args, {...options, stdio:['ignore','pipe','pipe']});
  child.on('error', error => {child.startError = error;});
  owned.push(child);
  lifecycle.push({pid:child.pid, command, args, started:new Date().toISOString()});
  return child;
}
async function stop(child) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  const exited = new Promise(resolve => child.once('exit', resolve));
  child.kill('SIGTERM');
  await Promise.race([exited, delay(5000)]);
  if (child.exitCode === null && child.signalCode === null) {child.kill('SIGKILL'); await exited;}
}
async function lineMatching(child, stream, expression) {
  return new Promise((resolve, reject) => {
    let buffer = '';
    const timeout = setTimeout(() => finish(Error('startup timeout: ' + buffer)), 15000);
    const onData = chunk => {buffer += chunk; const match = buffer.match(expression); if(match) finish(null, match);};
    const onExit = () => finish(Error('process exited at startup: ' + buffer));
    const onError = error => finish(error);
    function finish(error, result) {
      clearTimeout(timeout); stream.off('data', onData); child.off('exit', onExit); child.off('error', onError);
      error ? reject(error) : resolve(result);
    }
    stream.on('data', onData); child.once('exit', onExit); child.once('error', onError);
  });
}
function send(method, params={}) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {pending.delete(id); reject(Error('CDP timeout: '+method));}, 15000);
    pending.set(id, [value => {clearTimeout(timer); resolve(value);}, error => {clearTimeout(timer); reject(error);}]);
    ws.send(JSON.stringify({id, method, params}));
  });
}
async function evaluate(expression) {
  const result = await send('Runtime.evaluate', {expression, returnByValue:true, awaitPromise:true});
  assert(!result.exceptionDetails, JSON.stringify(result.exceptionDetails));
  return result.result?.value;
}
async function until(expression) {
  for (let i=0;i<100;i++) {if(await evaluate(expression)) return; await delay(100);}
  throw Error('UI did not reach: '+expression);
}
function cli(fixture, args, expected=0) {
  const result = spawnSync(python, ['-I','-S','-B',path.join(skill,'scripts/gf'),'--json','--run',path.join(fixture.project,'.graph-flow/runs',fixture.run),...args],
    {env:envFor(fixture), cwd:fixture.project, encoding:'utf8', timeout:20000});
  assert.equal(result.status, expected, result.stdout + result.stderr);
  return JSON.parse(result.stdout);
}
async function interaction(action, fixture) {
  const selector = JSON.stringify(action.selector);
  if (action.action === 'live-plan') {
    cli(fixture, ['plan','set',path.join(path.dirname(fixture.plan),'changed-plan.json')]);
    await evaluate("document.dispatchEvent(new Event('visibilitychange'))");
    await until("!!document.querySelector('.plan-change-list')");
  } else if (action.action === 'change-file') {
    writeFileSync(path.join(fixture.project,'guide.txt'), '질문 이후 안내가 수정되었어요. 새 근거 확인이 필요해요.\n');
    // Click the recorded attachment so the real evidence endpoint detects changed bytes.
    await evaluate("document.querySelector('.file-choices button').click()");
    await until("document.querySelector('#decision').classList.contains('decision-changed')");
  } else if (action.action === 'button') {
    await evaluate(`(()=>{const b=[...document.querySelectorAll('.map-toolbar button')].find(e=>(e.textContent===${JSON.stringify(action.text)}||(${JSON.stringify(action.text)}==='화면에 맞추기'&&e.dataset.action==='fit')));if(!b)throw Error('missing toolbar button');b.click()})()`);
  } else if (action.action === 'lower-rows') {
    const moved=await evaluate("(()=>{const v=document.querySelector('.map-viewport'),before={left:v.scrollLeft,top:v.scrollTop};v.scrollTo(before.left,v.scrollHeight-v.clientHeight);return {before,after:{left:v.scrollLeft,top:v.scrollTop}}})()");
    action.observedScroll=moved;
    assert(moved.after.top>moved.before.top&&moved.after.left===moved.before.left,'lower rows require vertical movement without sideways movement');
  } else if (action.action === 'scroll') {
    await evaluate(action.selector === 'window' ? `window.scrollTo(${action.x},${action.y})` : `document.querySelector(${selector}).scrollTo(${action.x},${action.y})`);
  } else {
    await until(`!!document.querySelector(${selector})`);
    if(action.action === 'click') await evaluate(`document.querySelector(${selector}).click()`);
    else if(action.action === 'open') await evaluate(`document.querySelector(${selector}).open=true`);
    else if(action.action === 'into') await evaluate(`document.querySelector(${selector}).scrollIntoView({block:'start'})`);
    else throw Error('unknown action '+action.action);
  }
  await delay(350);
  if(action.selector === '.key-recovery button')await until("!document.querySelector('.key-recovery') && !!document.querySelector('.plan-actions')");
  if(action.selector === '.file-choices button') await until("!!document.querySelector('.file-choices button[data-opened=true]')");
}
const derivedNumbers = new Set([1,2,3,5,7,10,15,17,18,19,20,21,22,23,24,29,33,34,37,38,41,44,52,53,58,59,61,62,63,64,65,66,67,68,69,...manifest.filter(s=>s.number>=70).map(s=>s.number)]);
try {
  chrome = start(chromePath, ['--headless=new','--remote-debugging-port=0','--user-data-dir='+profile,'--no-first-run','--no-default-browser-check','--lang=ko','about:blank']);
  const endpoint = (await lineMatching(chrome, chrome.stderr, /DevTools listening on (ws:\/\/\S+)/))[1];
  chrome.stderr.on('data', chunk => { /* Drain Chrome logs without exposing unrelated browser state. */ });
  const targets = await (await fetch('http://127.0.0.1:'+new URL(endpoint).port+'/json')).json();
  ws = new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
  await new Promise((resolve,reject) => {ws.onopen=resolve; ws.onerror=reject;});
  ws.onmessage = event => {
    const message = JSON.parse(event.data);
    if(message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails);
    if(pending.has(message.id)) {const [resolve,reject]=pending.get(message.id);pending.delete(message.id);message.error?reject(Error(JSON.stringify(message.error))):resolve(message.result);}
  };
  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setLocaleOverride', {locale:'ko-KR'});
  await send('Emulation.setTimezoneOverride', {timezoneId:'Asia/Seoul'});
  await send('Emulation.setEmulatedMedia', {features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  for (const screen of manifest.filter(row => !only || only.has(row.number))) {
    const fixture = fixtures[screen.scenario];
    const filename = String(screen.number).padStart(2,'0')+'-'+screen.name+'.png';
    const record = {number:screen.number,name:screen.name,scenario:screen.scenario,filename,group:screen.group};
    records = records.filter(row => row.number !== screen.number);
    const file = path.join(fixture.project,'guide.txt');
    const originalFile = screen.scenario === 'file-changed-live' ? readFileSync(file) : null;
    try {
      if(screen.scenario === 'changed-live') cli(fixture, ['plan','set',fixture.plan]);
      if(screen.scenario === 'file-changed-live'){const gate=cli(fixture,['gate','a'],1);fixture.decision=gate.asks[0]||gate.show?.match(/--decision (d\d+)/)?.[1];assert(fixture.decision,'current file decision is required');}
      activeServer = start(python, ['-I','-S','-B',path.join(skill,'scripts/gf'),'serve'], {cwd:fixture.project,env:envFor(fixture)});
      const started = JSON.parse((await lineMatching(activeServer, activeServer.stdout, /(\{"ok": true[^\n]+\})/))[1]);
      const base = new URL(started.url);
      const values = {token:base.searchParams.get('t'),project:fixture.project,run:fixture.run,decision:fixture.decision};
      const relative = screen.url.replace(/\{(\w+)\}/g, (_, key) => encodeURIComponent(values[key]));
      record.deepLink = relative.replace(encodeURIComponent(values.token), '{token}');
      errors.length = 0;
      await send('Emulation.setDeviceMetricsOverride', {width:screen.viewport.width,height:screen.viewport.height,deviceScaleFactor:1,mobile:false});
      await send('Page.navigate', {url:base.origin+relative});
      await until("document.querySelector('#title')?.textContent!=='Graph flow' && document.documentElement.lang==='ko'");
      await delay(450);
      for(const action of screen.interactions) await interaction(action, fixture);
      await evaluate('document.fonts.ready');
      const dom = await evaluate(`({title:document.querySelector('#title').textContent,language:document.documentElement.lang,text:document.body.innerText,level:document.querySelector('#map').dataset.level,scale:document.querySelector('#map').dataset.scale,scrollY,buttons:[...document.querySelectorAll('button')].filter(b=>b.getBoundingClientRect().width).map(b=>({text:b.textContent,disabled:b.disabled}))})`);
      assert.equal(dom.language,'ko');
      assert(dom.text.length > 100 && !/서버에 연결할 수 없|ERR_CONNECTION|사이트에 연결할 수 없/.test(dom.text), 'blank or connection error page');
      assert.equal(errors.length, 0, JSON.stringify(errors));
      assert(!dom.text.includes('[object Object]'), 'raw object in rendered text');
      if(screen.number === 64) assert.equal(dom.text.split('이 답만으로는 아무것도 통과되지 않아요').length-1,1,'free-answer limit is stated once');
      if(screen.number === 69) assert(dom.text.includes('질문에 쓰일 문구가 바뀌었어요'), 'wording-only log line missing');
      if(screen.number === 68) assert(await evaluate("document.querySelector('.plan-actions button.primary').disabled"), 'phone plan must remain locked');
      const audit=await evaluate(`(()=>{
        const map=document.querySelector('#map'),v=document.querySelector('.map-viewport'),vr=v.getBoundingClientRect();
        const shown=map.getBoundingClientRect().width>0&&!map.closest('[hidden]');
        const count=document.querySelector('.map-visible'),toolbar=document.querySelector('.map-toolbar');
        const panel=document.querySelector('#panel'),body=panel.querySelector('.panel-body'),bar=panel.querySelector('.panel-bar');
        const cards=[...document.querySelectorAll('#map .node-card')];
        const selected=cards.find(c=>c.classList.contains('expanded'));const sentence=panel.querySelector('.node-sentence'),sr=sentence?.getBoundingClientRect();
        const relation=direction=>[...panel.querySelectorAll('[data-relations="'+direction+'"] [data-other-node]')].map(e=>e.dataset.otherNode).sort();
        const routes=[...map.querySelectorAll('.edge-path')];
        const leafRects=body?[...body.querySelectorAll('p,li,summary,h3,pre')].filter(e=>e.getClientRects().length&&!e.querySelector('p,li,summary,h3,pre')).map(e=>{const range=document.createRange();range.selectNodeContents(e);return {text:e.textContent,rect:range.getBoundingClientRect().toJSON()}}):[];
        const visibleTitles=cards.filter(c=>{if(getComputedStyle(c).visibility==='hidden')return false;const t=c.querySelector('.node-title'),range=document.createRange();range.selectNodeContents(t);const r=range.getBoundingClientRect(),left=vr.left+v.clientLeft,top=vr.top+v.clientTop;return r.left>=left-.5&&r.right<=left+v.clientWidth+.5&&r.top>=top-.5&&r.bottom<=top+v.clientHeight+.5}).map(c=>c.querySelector('.node-title').textContent);
        return {shown,firstSentence:panel.hidden||!!sentence&&sentence.parentElement.children[1]===sentence&&sr.top>=0&&sr.bottom<=innerHeight,scroll:{left:v.scrollLeft,top:v.scrollTop},visibleTitles,
          toolbar:!shown||count.scrollWidth<=count.clientWidth+1&&count.getBoundingClientRect().left>=toolbar.getBoundingClientRect().left,
          panel:panel.hidden||bar.getBoundingClientRect().bottom<=body.getBoundingClientRect().top+.5,
          panelTitle:bar?.querySelector('strong')?.textContent,
          panelFirstLines:leafRects.filter(r=>r.rect.bottom>body.getBoundingClientRect().top&&r.rect.top<body.getBoundingClientRect().top),
          contentFits:!shown||cards.every(c=>c.scrollHeight<=c.clientHeight+1&&c.getBoundingClientRect().height<=c.parentElement.getBoundingClientRect().height+1),
          selectedVisible:!selected||(()=>{const r=selected.getBoundingClientRect();return r.left>=vr.left-.5&&r.right<=vr.right+.5&&r.top>=vr.top-.5&&r.bottom<=vr.bottom+.5})(),
          relations:!selected||panel.hidden?null:{incoming:relation('from'),outgoing:relation('to'),drawnIn:routes.filter(e=>e.dataset.to===selected.dataset.node).map(e=>e.dataset.from).sort(),drawnOut:routes.filter(e=>e.dataset.from===selected.dataset.node).map(e=>e.dataset.to).sort()},
          changeTitles:[...document.querySelectorAll('.plan-change-list>details>summary')].map(e=>e.textContent.split(' · ').slice(1).join(' · ')).sort(),
          markedTitles:cards.filter(c=>c.querySelector('.change-mark')).map(c=>c.querySelector('.node-title').textContent).sort()};
      })()`);
      assert(audit.firstSentence,'U1 first explanation is visible below the title');
      assert(audit.toolbar,'E1 count phrases must not be clipped');
      assert(audit.panel,'E2 panel body starts below its pinned title');
      assert.equal(audit.panelFirstLines.length,0,'E2 no text is sliced at the top of the panel scroll area');
      assert(audit.contentFits,'E6 content must fit the measured card');
      if(audit.relations){assert.deepEqual(audit.relations.incoming,audit.relations.drawnIn,'E10 incoming panel relations');assert.deepEqual(audit.relations.outgoing,audit.relations.drawnOut,'E10 outgoing panel relations');}
      if(audit.changeTitles.length)assert.deepEqual(audit.changeTitles,audit.markedTitles,'E8 change list names the marked cards');
      if(screen.number===11){assert(audit.scroll.top>0);audit.lowerRows=screen.interactions.find(a=>a.action==='lower-rows').observedScroll;assert.equal(audit.scroll.left,audit.lowerRows.before.left);assert(audit.visibleTitles.includes('접근성 확인'),'E13 lower branch is visible');}
      if(screen.number===27)assert(await evaluate("!document.querySelector('#home').hidden && document.querySelector('#flow').hidden"),'E13 answer record view');
      if(screen.number===36)assert(await evaluate("!document.querySelector('#flow').hidden && document.querySelector('#home').hidden"),'E13 graph banner view');
      if(screen.number===56)assert(dom.text.includes('확인 키를 새로 만들었어요')&&audit.panelTitle==='전체 결과 확인','V8 on-page recovery shows the new final check');
      if(screen.number===66){assert(dom.text.includes('허락하지 않은 결정'));assert(!dom.text.includes('내가 돌려보낸 결정'));}
      if(screen.number===67)assert(audit.selectedVisible,'E3 fit keeps selected card visible');
      if(screen.number===63){assert(/허락하기로 답했어요|받아들이기로 답했어요|받아들이지 않기로 답했어요/.test(dom.text));assert(dom.text.includes('이 안내를 시험 환경에 공개할까요?'));}
      if(screen.number===19)assert(await evaluate("getComputedStyle(document.querySelector('#accessible')).visibility==='hidden' && !!document.querySelector('#panel .planned-command')?.textContent"),'E4 opaque overlay and a real command');
      dom.audit=audit;
      const shot = await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,fromSurface:true});
      const bytes = Buffer.from(shot.data,'base64');
      writeFileSync(path.join(final,filename),bytes);
      copyFileSync(path.join(final,filename),path.join(verify,filename));
      if(derivedNumbers.has(screen.number)) {
        for(const [suffix,filter] of [['glance','scale=iw/4:ih/4,gblur=sigma=1.2,scale=iw*4:ih*4'],['gray','format=gray']]) {
          const result = spawnSync(ffmpeg,['-hide_banner','-loglevel','error','-y','-i',path.join(final,filename),'-vf',filter,'-frames:v','1',path.join(verify,filename.replace('.png','-'+suffix+'.png'))],{encoding:'utf8'});
          assert.equal(result.status,0,result.stderr);
        }
      }
      record.status='captured'; record.sha256=createHash('sha256').update(bytes).digest('hex');
      writeFileSync(path.join(runtime,filename.replace('.png','.json')),JSON.stringify(dom,null,2)+'\n');
      record.observation=path.join(runtime,filename.replace('.png','.json'));
      console.log('Captured '+filename);
    } catch(error) {
      record.status='could not reproduce'; record.reason=String(error.stack || error);
      for(const dir of [final,verify]) for(const name of readdirSync(dir).filter(n=>n===filename || n.startsWith(filename.replace('.png','-')))) unlinkSync(path.join(dir,name));
      console.error('FAILED '+filename+': '+error.message);
    } finally {
      await send('Page.navigate',{url:'about:blank'});
      await stop(activeServer); activeServer=null;
      if(originalFile) writeFileSync(file,originalFile);
      if(screen.scenario === 'changed-live') cli(fixture,['plan','set',fixture.plan]);
      records.push(record);records.sort((a,b)=>a.number-b.number);persist();
    }
  }
} finally {
  if(ws?.readyState===1)await send('Browser.close').catch(()=>{});
  ws?.close();
  for(const child of [...owned].reverse()) await stop(child);
  // Check the dedicated profile too: Chrome may have spawned helper processes.
  let remaining=[];
  for(let attempt=0;attempt<100;attempt++) {
    remaining=spawnSync('/bin/ps',['-axo','pid=,command='],{encoding:'utf8'}).stdout.split('\n').filter(line=>line.includes(profile));
    if(!remaining.length)break;
    await delay(100); // Helpers can finish just after the owned browser exits.
  }
  for(const item of lifecycle) {const child=owned.find(c=>c.pid===item.pid);item.stopped=child.exitCode!==null || child.signalCode!==null;item.exitCode=child.exitCode;item.signal=child.signalCode;}
  writeFileSync(path.join(runtime,'processes.json'),JSON.stringify({lifecycle,remaining},null,2)+'\n');
  assert(remaining.length===0,'Chrome profile still running: '+remaining.join('\n'));
  assert(lifecycle.every(item=>item.stopped),'owned process still running');
  console.log('Confirmed: all '+lifecycle.length+' owned server/Chrome processes stopped; no profile helpers remain.');
}
const hashes = new Map();
for(const record of records.filter(r=>r.status==='captured')) {
  const others=hashes.get(record.sha256)||[];others.push(record.number);hashes.set(record.sha256,others);
}
writeFileSync(path.join(output,'duplicate-hashes.json'),JSON.stringify([...hashes.values()].filter(group=>group.length>1),null,2)+'\n');
assert(records.every(row=>row.status==='captured'), 'some screens failed; see screen-status.json');
