const HOST='com.oozoofrog.macpilot';
let port, connectionID, reconnect=1000;
const state={connected:false,error:'Native host is not connected'};
const fail=(code,message)=>{throw Object.assign(new Error(message),{code})};
async function dom(request){
  const target={tabId:request.tabID,frameIds:[request.frameID??0]};
  try {await chrome.scripting.executeScript({target,files:['content.js']});}
  catch(error){fail('permission_required',error.message);}
  const response=await chrome.tabs.sendMessage(request.tabID,request,{frameId:request.frameID??0});
  if(!response?.ok)fail(response?.error?.code||'browser_error',response?.error?.message||'No response from frame');
  return response.result;
}
async function dispatch(r){
  switch(r.operation){
    case 'tabs':return {status:'tabs',tabs:(await chrome.tabs.query({})).map(t=>({tabID:t.id,windowID:t.windowId,url:t.url,title:t.title,active:t.active,status:t.status}))};
    case 'open':{const t=await chrome.tabs.create({url:r.url,active:r.activate===true});return {status:'tab_opened',tabID:t.id,windowID:t.windowId,url:t.url,pendingURL:t.pendingUrl};}
    case 'select':{const t=await chrome.tabs.update(r.tabID,{active:true});if(r.activate)await chrome.windows.update(t.windowId,{focused:true});return {status:'tab_selected',tabID:t.id,windowID:t.windowId};}
    case 'close':await chrome.tabs.remove(r.tabID);return {status:'tab_closed',tabID:r.tabID};
    case 'navigate':await chrome.tabs.update(r.tabID,{url:r.url});return {status:'navigation_requested',tabID:r.tabID};
    case 'back':await chrome.tabs.goBack(r.tabID);return {status:'navigation_requested'};
    case 'forward':await chrome.tabs.goForward(r.tabID);return {status:'navigation_requested'};
    case 'reload':await chrome.tabs.reload(r.tabID);return {status:'navigation_requested'};
    case 'frames':return {status:'frames',frames:await chrome.webNavigation.getAllFrames({tabId:r.tabID})};
    case 'download':{const id=await chrome.downloads.download({url:r.url,filename:r.filename||undefined,saveAs:false});return {status:'download_started',downloadID:id};}
    case 'download_status':{const [d]=await chrome.downloads.search({id:r.downloadID});if(!d)fail('missing_download','Unknown download');return {status:d.state==='complete'?'download_complete':d.state==='interrupted'?'download_failed':'download_in_progress',downloadID:d.id,filename:d.filename,bytesReceived:d.bytesReceived,totalBytes:d.totalBytes,error:d.error};}
    case 'screenshot':{
      const t=await chrome.tabs.get(r.tabID);if(!t.active)fail('foreground_required','Tab must be selected within its browser window for a screenshot');
      const data=await chrome.tabs.captureVisibleTab(t.windowId,{format:'png'});
      const bitmap=await createImageBitmap(await (await fetch(data)).blob());
      const scale=Math.min(1,1280/Math.max(bitmap.width,bitmap.height)), canvas=new OffscreenCanvas(Math.max(1,Math.round(bitmap.width*scale)),Math.max(1,Math.round(bitmap.height*scale)));
      canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();
      const bytes=new Uint8Array(await (await canvas.convertToBlob({type:'image/png'})).arrayBuffer());
      if(bytes.length>650000)fail('image_too_large','Capture is too large for native messaging; use native window capture');
      let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));
      return {status:'captured',pngBase64:btoa(binary),width:canvas.width,height:canvas.height};
    }
    default:return await dom(r);
  }
}
function respond(id,body){
  let response={type:'response',id,...body};
  if(new TextEncoder().encode(JSON.stringify(response)).length>1048576)
    response={type:'response',id,error:{code:'response_too_large',message:'Response exceeds the native message limit; request a smaller result.'}};
  port.postMessage(response);
}
function connect(){
  port=chrome.runtime.connectNative(HOST);
  port.onMessage.addListener(message=>{
    if(message.type==='connected'){connectionID=message.connectionID;state.connected=true;state.error='';reconnect=1000;chrome.storage.local.set({bridgeState:{...state,connectionID}});return;}
    if(message.type!=='command')return;
    dispatch(message.payload).then(result=>respond(message.id,{result}),error=>respond(message.id,{error:{code:error.code||'browser_error',message:error.message}}));
  });
  port.onDisconnect.addListener(()=>{
    state.connected=false;state.error=chrome.runtime.lastError?.message||'Native host disconnected';
    chrome.storage.local.set({bridgeState:{...state}});setTimeout(connect,reconnect);reconnect=Math.min(30000,reconnect*2);
  });
  port.postMessage({type:'hello',browser:'chromium',extensionID:chrome.runtime.id,version:chrome.runtime.getManifest().version});
}
setInterval(()=>{if(state.connected)try{port.postMessage({type:'heartbeat'})}catch{}},3000);
connect();
