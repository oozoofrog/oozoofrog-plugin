#!/usr/bin/env node
// Development-only: real, headful Chrome + ScreenCaptureKit, on an owned profile.
// CDP uses inherited pipes only for playback setup/readback; recording is MacPilot.
import {spawn} from 'node:child_process';
import {mkdtemp,mkdir,readFile,writeFile,copyFile} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const skill=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const binary=path.join(skill,'scripts/macpilot');
const root=await mkdtemp(path.join(os.tmpdir(),'macpilot-recording-chrome-'));
const evidence=path.join(skill,'evidence','recording-chrome-'+Date.now());await mkdir(evidence,{recursive:true});
const url='https://www.youtube.com/watch?v=aqz-KE-bpKQ&t=150s';
const scope=process.env.MACPILOT_RECORDING_SCOPE||'region';
let chrome,buffer=Buffer.alloc(0),sequence=0;const pending=new Map();
const report={status:'running',url,profile:path.join(root,'profile'),checks:[],evidence};
const check=(name,condition,detail)=>{report.checks.push({name,passed:!!condition,detail});console.log(name,condition?'PASS':'FAIL');if(!condition)throw new Error(name);};
async function run(executable,args,input,timeout=60000,environment={}){
 return await new Promise((resolve,reject)=>{
  const p=spawn(executable,args,{env:{...process.env,...environment},stdio:['pipe','pipe','pipe']});
  let stdout='',stderr='';p.stdout.on('data',d=>stdout+=d);p.stderr.on('data',d=>stderr+=d);p.stdin.end(input);
  const timer=setTimeout(()=>{p.kill();reject(new Error('Command deadline: '+executable));},timeout);
  p.on('error',reject);p.on('exit',code=>{clearTimeout(timer);resolve({code,stdout,stderr});});
 });
}
async function cli(tool,args){
 const r=await run(binary,['call',tool,'--json','-'],JSON.stringify(args),65000,{MACPILOT_STATE_DIR:path.join(root,'state')});
 if(r.code)throw new Error(r.stdout+'\n'+r.stderr);return JSON.parse(r.stdout);
}
function cdp(method,params={},sessionId){return new Promise((resolve,reject)=>{
 const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP deadline '+method));},15000);
 pending.set(id,{resolve,reject,timer});chrome.stdio[3].write(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})})+'\0');
});}
let session;
async function evaluate(expression){
 const result=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true},session);
 if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));return result.result.value;
}
const playerExpression=`(()=>{const v=document.querySelector('video');return {url:location.href,title:document.title,video:!!v,paused:v?.paused,muted:v?.muted,volume:v?.volume,currentTime:v?.currentTime,duration:v?.duration,readyState:v?.readyState,ad:!!document.querySelector('.ad-showing')}})()`;
try{
 const built=await run(binary,['tools']);if(built.code)throw new Error(built.stderr);
 chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
  '--user-data-dir='+report.profile,'--remote-debugging-pipe','--no-first-run','--no-default-browser-check',
  '--autoplay-policy=no-user-gesture-required','--force-renderer-accessibility','about:blank'],
  {stdio:['ignore','ignore','pipe','pipe','pipe']});
 let chromeErrors='';chrome.stderr.on('data',d=>{chromeErrors+=d;});
 chrome.stdio[4].on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);for(let i;(i=buffer.indexOf(0))>=0;){
  const raw=buffer.subarray(0,i);buffer=buffer.subarray(i+1);try{const v=JSON.parse(raw),p=pending.get(v.id);if(p){pending.delete(v.id);clearTimeout(p.timer);if(v.error)p.reject(new Error(JSON.stringify(v.error)));else p.resolve(v.result);}}catch{}
 }});
 report.browser=await cdp('Browser.getVersion');
 const target=await cdp('Target.createTarget',{url});session=(await cdp('Target.attachToTarget',{targetId:target.targetId,flatten:true})).sessionId;
 await cdp('Runtime.enable',{},session);
 await cdp('Page.enable',{},session);
 await cdp('Page.navigate',{url},session);
 let player;
 const readyDeadline=Date.now()+90000;
 while(Date.now()<readyDeadline){
  player=await evaluate(playerExpression);
  await writeFile(path.join(evidence,'player-latest.json'),JSON.stringify(player,null,2));
  if(player.video&&player.readyState>=2&&!player.ad&&player.title.includes('Big Buck Bunny'))break;
  await new Promise(r=>setTimeout(r,350));
 }
 check('actual_YouTube_content_is_loaded_without_ad',player?.video&&player.readyState>=2&&!player.ad&&player.title.includes('Big Buck Bunny'),player);
 await evaluate(`(async()=>{const v=document.querySelector('video');v.muted=false;v.volume=.7;v.currentTime=150;await v.play();return true})()`);
 await new Promise(r=>setTimeout(r,1500));report.before=await evaluate(playerExpression);
 check('YouTube_playback_is_unmuted_and_progressing',!report.before.paused&&!report.before.muted&&report.before.currentTime>150,report.before);
 const app=(await cli('mac_apps',{})).apps.find(a=>a.pid===chrome.pid&&a.bundleID==='com.google.Chrome');
 check('recording_targets_the_owned_real_Chrome_process',!!app,{pid:chrome.pid});
 const windows=(await cli('mac_windows',{pid:chrome.pid})).windows.filter(w=>w.onScreen&&w.title.includes('Big Buck Bunny'));
 check('native_Chrome_window_is_uniquely_identified',windows.length===1,windows);
 let request={operation:'record',source:'window',pid:app.pid,processStartID:app.processStartID,windowID:windows[0].windowID,durationSeconds:12,systemAudio:true,maxDimension:1920,fps:30};
 if(['display','region'].includes(scope)){
  const observation=await cli('mac_observe',{pid:app.pid,processStartID:app.processStartID,windowID:windows[0].windowID,screenshot:false,maxNodes:1,maxDepth:1});
  const focus=await cli('mac_focus',{observation:observation.observation.id});check('owned_Chrome_window_is_visible_for_display_capture',focus.status==='focus_verified',focus);
  const displays=(await cli('mac_doctor',{})).displays,w=windows[0].frame;
  const display=displays.find(d=>w.x+w.width/2>=d.frame.x&&w.x+w.width/2<d.frame.x+d.frame.width&&w.y+w.height/2>=d.frame.y&&w.y+w.height/2<d.frame.y+d.frame.height);
  if(!display)throw new Error('No display contains the owned Chrome window');
  request={operation:'record',source:'display',displayID:display.id,durationSeconds:12,systemAudio:true,maxDimension:1920,fps:30};
  if(scope==='region')request.region={x:w.x-display.frame.x,y:w.y-display.frame.y,width:w.width,height:w.height};
 }
 report.scope=scope;
 await writeFile(path.join(evidence,'request.json'),JSON.stringify(request,null,2));
 report.recording=await cli('mac_record',request);report.after=await evaluate(playerExpression);
 await evaluate(`document.querySelector('video').pause()`);
 const movie=path.join(evidence,'chrome-youtube-screen-audio.mp4');await copyFile(report.recording.path,movie);report.movie=movie;
 for(let i=0;i<report.recording.frames.length;i++)await copyFile(report.recording.frames[i].path,path.join(evidence,'frame-'+(i+1)+'.png'));
 report.sha256=createHash('sha256').update(await readFile(movie)).digest('hex');
 check('playback_advanced_through_the_recording',report.after.currentTime-report.before.currentTime>=11&&!report.after.ad,{before:report.before,after:report.after});
 check('saved_MP4_has_real_video_and_audio_signal',report.recording.status==='recorded'&&report.recording.videoTracks===1&&report.recording.audioTracks===1&&report.recording.audioSignalDetected&&report.recording.audioRMS>0.0001,report.recording);
 check('saved_video_contains_different_decoded_frames',report.recording.sampledFramesDiffer);
 const probe=await run('/opt/homebrew/bin/ffprobe',['-v','error','-show_streams','-show_format','-of','json',movie]);
 await writeFile(path.join(evidence,'ffprobe.json'),probe.stdout);const meta=JSON.parse(probe.stdout);
 check('independent_probe_confirms_H264_AAC',probe.code===0&&meta.streams.some(s=>s.codec_name==='h264')&&meta.streams.some(s=>s.codec_name==='aac'&&s.sample_rate==='48000'&&s.channels===2));
 const decode=await run('/opt/homebrew/bin/ffmpeg',['-v','error','-i',movie,'-f','null','-']);await writeFile(path.join(evidence,'decode.log'),decode.stderr);
 check('independent_full_movie_decode_has_no_errors',decode.code===0&&!decode.stderr.trim());
 await writeFile(path.join(evidence,'chrome.stderr'),chromeErrors);
 report.status='passed';
}catch(error){report.status='failed';report.error=error.stack;process.exitCode=1;}
finally{
 for(const p of pending.values()){clearTimeout(p.timer);p.reject(new Error('test ended'));}pending.clear();
 if(chrome&&chrome.exitCode===null){chrome.kill('SIGTERM');await Promise.race([new Promise(r=>chrome.once('exit',r)),new Promise(r=>setTimeout(r,3000))]);if(chrome.exitCode===null)chrome.kill('SIGKILL');}
 report.ownedBrowserStopped=!chrome||chrome.exitCode!==null||chrome.signalCode!==null;
 await writeFile(path.join(evidence,'report.json'),JSON.stringify(report,null,2));console.log('Evidence:',evidence);
}
