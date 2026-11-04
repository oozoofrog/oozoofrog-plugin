const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function background(){
 const sent=[];let listener;
 const port={postMessage:m=>sent.push(m),onMessage:{addListener:f=>listener=f},onDisconnect:{addListener(){}}};
 const chrome={runtime:{connectNative:()=>port,id:'a'.repeat(32),getManifest:()=>({version:'test'})},storage:{local:{set(){}}},tabs:{query:async()=>[{id:1,title:'😀'.repeat(400000)}]}};
 const context=vm.createContext({chrome,TextEncoder,setInterval(){},setTimeout});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/background.js'),'utf8'),context);
 return {sent,command:m=>listener(m)};
}
test('oversized non-DOM responses become bounded errors without disconnecting native host',async()=>{
 const f=background();f.command({type:'command',id:'fixture',payload:{operation:'tabs'}});
 await new Promise(r=>setImmediate(r));
 const response=f.sent.find(m=>m.id==='fixture');
 assert.equal(response.error?.code,'response_too_large');
 assert.ok(Buffer.byteLength(JSON.stringify(response))<=1048576);
 f.command({type:'command',id:'next',payload:{operation:'tabs'}});
 await new Promise(r=>setImmediate(r));
 assert.equal(f.sent.find(m=>m.id==='next').error?.code,'response_too_large');
});
