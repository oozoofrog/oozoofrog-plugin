const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm'), fs=require('node:fs'), path=require('node:path');
const {webcrypto}=require('node:crypto');
// Chromium DOM APIs are unavailable in the portable Node runner. Execute the
// shipped bridge unchanged against only the DOM surface consumed by the bridge.
class Element {
 constructor(tag,attrs={},value='') {this.tagName=tag.toUpperCase();this.attrs=attrs;this.id=attrs.id||'';this.parentElement=null;this.isConnected=true;this.disabled=false;this.innerText=value;if(tag==='input')this.value=value;}
 getAttribute(name){return this.attrs[name]??null;}
 getBoundingClientRect(){return{x:0,y:0,width:100,height:20};}
 matches(selector){return selector.split(',').some(s=>{let m=s.match(/^(\w+)?\[([^=]+)="([^"]*)"\]$/);return m && (!m[1]||m[1].toUpperCase()===this.tagName) && this.attrs[m[2]]===m[3];});}
 closest(){return null;}
 click(){this.clicked=true;}
}
function fixture(elements){
 let now=1000;
 const context=vm.createContext({crypto:webcrypto,TextEncoder,Date:class extends Date{static now(){return now}},document:{querySelectorAll:()=>elements,title:'Fixture'},location:{href:'https://example.invalid'},innerWidth:1024,innerHeight:768,scrollX:0,scrollY:0,getComputedStyle:()=>({display:'block',visibility:'visible'}),setTimeout,Uint8Array,atob,Blob});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/content.js'),'utf8'),context);
 return {dispatch:r=>context.__macpilotBridge.dispatch(r),advance:ms=>now+=ms};
}
async function observe(f){const s=await f.dispatch({operation:'observe'});return {observation:s.observation,node:'0'};}
test('native-style repeated verify follows text changes without relaxing mutation guards',async()=>{
 const e=new Element('button',{},'Waiting'),f=fixture([e]),target=await observe(f);
 assert.equal((await f.dispatch({operation:'verify',...target,equals:'Done'})).matches,false);
 e.innerText='Done';
 assert.equal((await f.dispatch({operation:'verify',...target,equals:'Done'})).matches,true);
 await assert.rejects(f.dispatch({operation:'click',...target}),{code:'stale_observation'});
 assert.equal(e.clicked,undefined);
});
for(const change of ['identity','disconnected','parent','expired'])test(`verify rejects ${change} changes`,async()=>{
 const e=new Element('p',{},'Waiting'),parent=new Element('div');e.parentElement=parent;
 const f=fixture([e]),target=await observe(f);
 if(change==='identity')e.id='new'; if(change==='disconnected')e.isConnected=false;
 if(change==='parent')parent.id='new';if(change==='expired')f.advance(30001);
 await assert.rejects(f.dispatch({operation:'verify',...target,equals:'Done'}),{code:'stale_observation'});
});
for(const content of ['x'.repeat(4096),'😀'.repeat(2048),'\u0000'.repeat(4096)])test('large observations stay inside native frame byte limit: '+content.codePointAt(0),async()=>{
 const f=fixture(Array.from({length:500},(_,i)=>new Element('p',{id:String(i)},content)));
 const s=await f.dispatch({operation:'observe',maxNodes:500});
 assert.ok(Buffer.byteLength(JSON.stringify({type:'response',id:'0'.repeat(36),result:s}))<=1048576);
 assert.equal(s.coverage,'partial');assert.ok(s.nodes.length>0);assert.ok(s.nodes.length<500);
});
test('expired uploads free all slots without a page reload',async()=>{
 const f=fixture([new Element('input',{type:'file'})]);let first;
 for(let i=0;i<4;i++){const upload=await begin(f);first??=upload;}
 f.advance(300001);
 await assert.rejects(f.dispatch({operation:'upload_chunk',uploadID:first.uploadID,offset:0,data:'YQ=='}),{code:'missing_upload'});
 assert.equal((await begin(f)).status,'upload_ready');
});
async function begin(f){return f.dispatch({operation:'upload_begin',...await observe(f),size:1,name:'fixture.txt'});}
test('live upload capacity remains bounded',async()=>{
 const f=fixture([new Element('input',{type:'file'})]);for(let i=0;i<4;i++)await begin(f);
 await assert.rejects(begin(f),{code:'busy'});
});
test('invalid chunks abandon their upload rather than reserving capacity',async()=>{
 const f=fixture([new Element('input',{type:'file'})]);let first=await begin(f);for(let i=1;i<4;i++)await begin(f);
 await assert.rejects(f.dispatch({operation:'upload_chunk',uploadID:first.uploadID,offset:2,data:'YQ=='}),{code:'invalid_chunk'});
 assert.equal((await begin(f)).status,'upload_ready');
});
