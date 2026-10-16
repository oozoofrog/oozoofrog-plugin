#!/usr/bin/env node
// Actual Chromium + extension + Swift native-host acceptance, in a private profile.
import {spawn} from 'node:child_process';
import {mkdtemp,mkdir,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import http from 'node:http';
import {createHash} from 'node:crypto';
const skill=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const binary=process.argv[2]||path.join(skill,'bin/MacPilot.app/Contents/MacOS/macpilot');
const root=await mkdtemp(path.join(tmpdir(),'macpilot-browser-test-'));
const evidence=path.join(skill,'evidence','browser-'+Date.now());await mkdir(evidence,{recursive:true});
const state=path.join(root,'state'), profile=path.join(root,'chrome'), downloads=path.join(root,'downloads');await mkdir(downloads);
const checks=[];let serial=0, chrome, uploaded, nativeHosts=[];
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const check=(name,condition,detail)=>{checks.push({check:name,passed:!!condition,detail});console.log(name,condition?'PASS':'FAIL');if(!condition)throw new Error(name);};
const downloadBytes=Buffer.from('MacPilot download 한글 😀\n');
const server=http.createServer(async(req,res)=>{
 if(req.url==='/download'){res.writeHead(200,{'Content-Type':'application/octet-stream','Content-Disposition':'attachment; filename="synthetic.txt"'});res.end(downloadBytes);return;}
 if(req.url==='/upload'){const chunks=[];for await(const chunk of req)chunks.push(chunk);uploaded=Buffer.concat(chunks);res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify({sha256:sha(uploaded)}));return;}
 res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});
 if(req.url==='/frame'){res.end('<!doctype html><h2 id="frame-proof">Frame proof 한글</h2><input id="frame-input">');return;}
 if(req.url==='/second'){res.end('<!doctype html><title>Second page</title><h1 id="second">Second page</h1>');return;}
 res.end(`<!doctype html><title>MacPilot owned browser fixture</title><h1 id="heading">MacPilot browser fixture</h1><label for="answer">Answer</label><input id="answer" value="초기 값"><input id="password" type="password" value="synthetic-browser-secret"><button id="increment" onclick="document.querySelector('#counter').textContent=Number(document.querySelector('#counter').textContent)+1">Increment</button><p id="counter">0</p><select id="choice"><option value="a">A</option><option value="b">B</option></select><input id="upload" type="file"><p id="upload-result">Waiting</p><iframe title="Owned frame" src="/frame"></iframe><script>document.querySelector('#upload').onchange=async e=>{const reply=await fetch('/upload',{method:'POST',body:e.target.files[0]}).then(r=>r.json());document.querySelector('#upload-result').textContent=reply.sha256}</script>`);
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const url='http://127.0.0.1:'+server.address().port;
async function cli(operation){
 const id=++serial;
 return await new Promise((resolve,reject)=>{
  const child=spawn(binary,['call',operation.tool||'mac_browser','--json','-'],{env:{...process.env,MACPILOT_STATE_DIR:state},stdio:['pipe','pipe','pipe']});
  let out='',error='';child.stdout.on('data',d=>out+=d);child.stderr.on('data',d=>error+=d);
  const {tool,...input}=operation;child.stdin.end(JSON.stringify(input));
  const timer=setTimeout(()=>{child.kill('SIGTERM');reject(new Error('CLI timeout'));},90000);
  child.on('error',reject);child.on('exit',async code=>{
   clearTimeout(timer);await writeFile(path.join(evidence,String(id).padStart(3,'0')+'.json'),out);
   if(error)await writeFile(path.join(evidence,String(id)+'.stderr'),error);
   try{const data=JSON.parse(out);if(code)reject(Object.assign(new Error(data.message),{data}));else resolve(data);}catch(e){reject(e);}
  });
 });
}
let buffer=Buffer.alloc(0), seq=0;const pending=new Map();
function cdp(method,params={}){return new Promise((resolve,reject)=>{
 const id=++seq;const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout '+method));},10000);
 pending.set(id,{resolve,reject,timer});chrome.stdio[3].write(JSON.stringify({id,method,params})+'\0');
});}
let result={checks};
try{
 chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
  '--user-data-dir='+profile,'--remote-debugging-pipe','--enable-unsafe-extension-debugging','--no-first-run','--no-default-browser-check','--headless=new','about:blank'],{stdio:['ignore','ignore','pipe','pipe','pipe']});
 chrome.stderr.on('data',()=>{});
 chrome.stdio[4].on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);for(let i;(i=buffer.indexOf(0))>=0;){const raw=buffer.subarray(0,i);buffer=buffer.subarray(i+1);try{const d=JSON.parse(raw);const p=pending.get(d.id);if(p){pending.delete(d.id);clearTimeout(p.timer);if(d.error)p.reject(new Error(JSON.stringify(d.error)));else p.resolve(d.result);}}catch{}}});
 result.browser=await cdp('Browser.getVersion');
 const extension=await cdp('Extensions.loadUnpacked',{path:path.join(skill,'browser/extension')});
 check('real_chrome_extension_is_enabled',(await cdp('Extensions.getExtensions')).extensions.some(e=>e.id===extension.id&&e.enabled));
 const installed=await cli({operation:'install_host',extensionID:extension.id,browser:'chrome',manifestDirectory:path.join(profile,'NativeMessagingHosts')});
 check('native_host_manifest_is_isolated_to_test_profile',installed.manifest.startsWith(profile));
 let connections=[];
 for(let i=0;i<80;i++){connections=(await cli({operation:'connections'})).connections.filter(c=>c.live);if(connections.length)break;await new Promise(r=>setTimeout(r,150));}
 check('browser_and_swift_native_host_are_actually_connected',connections.length===1,connections);
 nativeHosts=connections;
 const connectionID=connections[0].id;
 const browser=fields=>cli({connectionID,...fields});
 const first=await browser({operation:'open',url});let tabID=first.tabID;
 async function observe(tab=tabID,frameID=0){
  let last;
  for(let i=0;i<30;i++){try{last=await browser({operation:'observe',tabID:tab,frameID});if(last.nodes?.length)return last;}catch(error){last=error.message;}await new Promise(r=>setTimeout(r,100));}throw new Error('Page not ready: '+JSON.stringify(last));
 }
 const byID=(o,id)=>{const node=o.nodes.find(n=>n.identifier===id);if(!node)throw new Error('Missing '+id);return node.id;};
 let o=await observe();check('DOM_observation_redacts_password',o.nodes.some(n=>n.identifier==='password'&&n.secure)&&!JSON.stringify(o).includes('synthetic-browser-secret'));
 const filled=await browser({operation:'fill',tabID,observation:o.observation,node:byID(o,'answer'),text:'한글 😀 browser'});
 check('background_DOM_fill_is_verified',filled.status==='value_verified',filled);
 try{await browser({operation:'fill',tabID,observation:o.observation,node:byID(o,'answer'),text:'stale'});throw new Error('stale mutation accepted');}catch(error){check('consumed_DOM_observation_is_rejected',error.data?.code==='stale_observation',error.data);}
 o=await observe();try{await browser({operation:'fill',tabID,observation:o.observation,node:byID(o,'password'),text:'forbidden'});throw new Error('secure fill accepted');}catch(error){check('secure_DOM_input_is_rejected',error.data?.code==='secure_or_inert_node',error.data);}
 o=await observe();await browser({operation:'click',tabID,observation:o.observation,node:byID(o,'increment')});
 o=await observe();check('DOM_click_changes_actual_page',(await browser({operation:'verify',tabID,observation:o.observation,node:byID(o,'counter'),equals:'1'})).matches);
 const frames=(await browser({operation:'frames',tabID})).frames;const frame=frames.find(f=>f.frameId!==0);
 const nested=await observe(tabID,frame.frameId);check('iframe_is_addressed_independently',nested.nodes.some(n=>n.identifier==='frame-proof'));
 o=await observe();await browser({operation:'select_option',tabID,observation:o.observation,node:byID(o,'choice'),text:'b'});
 o=await observe();check('select_option_roundtrip',(await browser({operation:'verify',tabID,observation:o.observation,node:byID(o,'choice'),equals:'b'})).matches);
 const original=Buffer.from('MacPilot 실제 업로드 😀\n');const upload=path.join(root,'upload.txt');await writeFile(upload,original);
 o=await observe();const attached=await browser({operation:'upload',tabID,observation:o.observation,node:byID(o,'upload'),path:upload,mime:'text/plain'});
 for(let i=0;i<30&&!uploaded;i++)await new Promise(r=>setTimeout(r,100));
 check('actual_HTTP_upload_matches_original_bytes',attached.sha256===sha(original)&&uploaded?.equals(original),attached);
 await cdp('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:downloads,eventsEnabled:true});
 const download=await browser({operation:'download',url:url+'/download',filename:'download.txt'});let downloaded;
 for(let i=0;i<40;i++){downloaded=await browser({operation:'download_status',downloadID:download.downloadID});if(downloaded.status==='download_complete')break;await new Promise(r=>setTimeout(r,100));}
 check('actual_download_matches_served_bytes',downloaded.status==='download_complete'&&(await readFile(downloaded.filename)).equals(downloadBytes),downloaded);
 const second=await browser({operation:'open',url:url+'/second'});await observe(second.tabID);
 const taskA=(await cli({tool:'mac_task',operation:'begin',goal:'Browser A'})).task.id;
 const taskB=(await cli({tool:'mac_task',operation:'begin',goal:'Browser B'})).task.id;
 o=await observe();const waiting=cli({operation:'wait',connectionID,taskID:taskA,tabID,observation:o.observation,node:byID(o,'counter'),equals:'not-matching',timeoutMs:2000});
 await new Promise(r=>setTimeout(r,200));const began=Date.now();const other=await cli({operation:'observe',connectionID,taskID:taskB,tabID:second.tabID});
 check('separate_browser_tabs_execute_concurrently',Date.now()-began<1100&&other.nodes.some(n=>n.identifier==='second'));
 await waiting;
 await browser({operation:'navigate',tabID:second.tabID,url});await observe(second.tabID);
 await browser({operation:'close',tabID:second.tabID});check('tab_close_is_verified_by_fresh_inventory',!(await browser({operation:'tabs'})).tabs.some(t=>t.tabID===second.tabID));
 const receipt=await cli({operation:'receipt',requestID:filled.requestID});check('browser_command_receipt_is_durable',receipt.status==='response_received');
 result.status='passed';
} catch(error){result.status='failed';result.error=error.stack;throw error;}
finally{
 for(const p of pending.values())clearTimeout(p.timer);
 server.close();
 if(chrome){chrome.kill('SIGTERM');await Promise.race([new Promise(r=>chrome.once('exit',r)),new Promise(r=>setTimeout(r,3000))]);}
 await new Promise(r=>setTimeout(r,500));
 await writeFile(path.join(evidence,'report.json'),JSON.stringify(result,null,2));
 await rm(root,{recursive:true,force:true});console.log('Evidence:',evidence);
}
