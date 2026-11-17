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
const envFor = fixture => ({...baseEnv, GF_HOME:fixture.home, GF_NO_OPEN:'1', GF_ROLE:'leader', GF_SESSION:'screens-r17'});
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
    await evaluate(`(()=>{const b=[...document.querySelectorAll('.map-toolbar button')].find(e=>e.textContent===${JSON.stringify(action.text)});if(!b)throw Error('missing toolbar button');b.click()})()`);
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
  if(action.selector === '.file-choices button') await until("!!document.querySelector('.file-choices button[data-opened=true]')");
}
const derivedNumbers = new Set([1,3,5,7,15,20,22,23,24,41,44,52,53,58,59,61,62,63,64,65,66,67,68,69]);
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
  ws?.close();
  for(const child of [...owned].reverse()) await stop(child);
  // Check the dedicated profile too: Chrome may have spawned helper processes.
  const processes = spawnSync('/bin/ps',['-axo','pid=,command='],{encoding:'utf8'}).stdout;
  const remaining = processes.split('\n').filter(line=>line.includes(profile));
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
