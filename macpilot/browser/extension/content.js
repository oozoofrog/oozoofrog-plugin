(() => {
  if (globalThis.__macpilotBridge) return;
  const documentID = crypto.randomUUID(), snapshots = new Map(), uploads = new Map();
  const fail = (code, message) => { throw Object.assign(new Error(message), {code}); };
  const secure = e => e.matches?.('input[type="password"],input[type="hidden"],[autocomplete="current-password"],[autocomplete="new-password"],[autocomplete="cc-number"]');
  const text = e => secure(e) ? undefined : String('value' in e ? e.value : e.innerText || e.textContent || '').slice(0, 4096);
  const identity = e => [e.tagName, e.id, e.getAttribute('name'), e.getAttribute('type'), e.getAttribute('role'), e.getAttribute('aria-label')].join('\u0001');
  const fingerprint = e => [identity(e), text(e)].join('\u0001');
  const parents = e => { const list=[]; for(let p=e.parentElement; p && list.length<5;p=p.parentElement) list.push([p,p.tagName,p.id,p.getAttribute('role')]); return list; };
  function resolve(request, consume = false, readOnly = false) {
    const snapshot=snapshots.get(request.observation);
    if (!snapshot || Date.now()>snapshot.expires || snapshot.documentID!==documentID) fail('stale_observation','Observe this frame again');
    const entry=snapshot.nodes.get(request.node);
    if(!entry || !entry.element.isConnected || (readOnly ? identity(entry.element)!==entry.identity : fingerprint(entry.element)!==entry.fingerprint) || entry.parents.some(([p,tag,id,role])=>!p.isConnected||p.tagName!==tag||p.id!==id||p.getAttribute('role')!==role)) fail('stale_observation','DOM node or its ancestors changed');
    if(secure(entry.element) || entry.element.closest('[inert]')) fail('secure_or_inert_node','Target is secure or inert');
    if(entry.element.disabled || entry.element.getAttribute('aria-disabled')==='true') fail('disabled_control','Target is disabled');
    if(consume) snapshots.delete(request.observation);
    return entry.element;
  }
  function observe(request) {
    for(const [id,value] of snapshots) if(value.expires<Date.now()) snapshots.delete(id);
    if(snapshots.size>=32) snapshots.delete(snapshots.keys().next().value);
    const id=crypto.randomUUID(), nodes=new Map(), rows=[];
    const maxNodes=Math.max(1,Math.min(500,request.maxNodes??200));
    const candidates=document.querySelectorAll('a,button,input,textarea,select,[role],[contenteditable="true"],label,h1,h2,h3,p,td,th');
    let visited=0, rowBytes=0, truncated=false;
    const encoder=new TextEncoder();
    for(const element of candidates) {
      if(++visited>10000 || rows.length>=maxNodes) break;
      const rect=element.getBoundingClientRect(), style=getComputedStyle(element);
      if(!rect.width||!rect.height||style.display==='none'||style.visibility==='hidden') continue;
      const node=String(rows.length), isSecure=!!secure(element);
      const row={id:node,tag:element.tagName.toLowerCase(),role:(element.getAttribute('role')||'').slice(0,512),
        name:(element.getAttribute('aria-label')||element.labels?.[0]?.innerText||element.getAttribute('name')||'').slice(0,512),
        identifier:element.id.slice(0,512), type:(element.getAttribute('type')||'').slice(0,512),text:isSecure?undefined:text(element),
        secure:isSecure,enabled:!element.disabled&&element.getAttribute('aria-disabled')!=='true',
        rect:{x:rect.x,y:rect.y,width:rect.width,height:rect.height}};
      // Reserve room for metadata and the native response envelope. Count the
      // serialized UTF-8 bytes (including JSON escaping), not JS code units.
      const bytes=encoder.encode(JSON.stringify(row)).length+1;
      if(rowBytes+bytes>900000){truncated=true;break;}
      rowBytes+=bytes;rows.push(row);
      nodes.set(node,{element,identity:identity(element),fingerprint:fingerprint(element),parents:parents(element)});
    }
    snapshots.set(id,{documentID,nodes,expires:Date.now()+30000});
    return {status:'observed',observation:id,documentID,url:location.href.slice(0,4096),title:document.title.slice(0,4096),nodes:rows,
      coverage:truncated||visited>10000||rows.length>=maxNodes?'partial':'visible_candidates',
      viewport:{width:innerWidth,height:innerHeight,scrollX,scrollY},ttlSeconds:30};
  }
  async function dispatch(request) {
    for(const [id,item] of uploads) if(Date.now()>item.expires) uploads.delete(id);
    if(request.operation==='observe') return observe(request);
    if(request.operation==='upload_chunk') {
      const item=uploads.get(request.uploadID);
      if(!item||Date.now()>item.expires) fail('missing_upload','Upload expired');
      let bytes;
      try {
        if(request.offset!==item.length) fail('invalid_chunk','Upload offset mismatch');
        bytes=Uint8Array.from(atob(request.data),c=>c.charCodeAt(0));
        if(item.length+bytes.length>item.size) fail('invalid_chunk','Upload exceeds declared size');
      } catch(error) { uploads.delete(request.uploadID); throw error; }
      item.chunks.push(bytes); item.length+=bytes.length;
      return {status:'upload_chunk_received',bytes:item.length};
    }
    if(request.operation==='upload_end') {
      const item=uploads.get(request.uploadID); uploads.delete(request.uploadID);
      if(!item||Date.now()>item.expires||item.length!==item.size||!item.element.isConnected||secure(item.element)) fail('invalid_upload','Upload is incomplete or target changed');
      const blob=new Blob(item.chunks), digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await blob.arrayBuffer()))).map(x=>x.toString(16).padStart(2,'0')).join('');
      if(digest!==request.sha256) fail('invalid_upload','Upload hash mismatch');
      const transfer=new DataTransfer(); transfer.items.add(new File([blob],item.name,{type:item.mime}));
      item.element.files=transfer.files;
      item.element.dispatchEvent(new Event('input',{bubbles:true}));item.element.dispatchEvent(new Event('change',{bubbles:true}));
      return {status:'files_assigned',names:Array.from(item.element.files,f=>f.name),bytes:item.size,sha256:digest,
        verification:'Files assigned to the selected input. Server-side upload completion requires a separate postcondition.'};
    }
    if(request.operation==='verify'||request.operation==='wait') {
      const node=resolve(request,false,true), deadline=Date.now()+(request.operation==='wait'?Math.min(request.timeoutMs??3000,30000):0);
      let actual, matches;
      do {
        resolve(request,false,true);
        actual=text(node); matches=request.equals!==undefined?actual===request.equals:actual.includes(request.contains);
        if(matches||Date.now()>=deadline)break;
        await new Promise(r=>setTimeout(r,100));
      } while(true);
      return {status:matches?'predicate_verified':'predicate_not_met',matches,actual};
    }
    const element=resolve(request,true);
    switch(request.operation) {
      case 'click': element.click();return {status:'action_requested',verification:'DOM click invoked; observe the requested result.'};
      case 'fill': {
        if(element.matches('input[type="file"]')) fail('unsupported_action','Use upload for file inputs');
        if(element.isContentEditable) element.textContent=request.text;
        else {
          const prototype=element instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
          const setter=Object.getOwnPropertyDescriptor(prototype,'value')?.set;
          if(!setter)fail('not_settable','Element is not a text input');
          setter.call(element,request.text);
        }
        element.dispatchEvent(new Event('input',{bubbles:true}));element.dispatchEvent(new Event('change',{bubbles:true}));
        return {status:text(element)===request.text?'value_verified':'value_unverified',actual:text(element)};
      }
      case 'select_option': {
        if(!(element instanceof HTMLSelectElement))fail('not_select','Element is not a select');
        element.value=request.text;element.dispatchEvent(new Event('change',{bubbles:true}));
        return {status:element.value===request.text?'value_verified':'value_unverified',actual:element.value};
      }
      case 'scroll': element.scrollBy({left:request.x??0,top:request.y??0,behavior:'instant'});return {status:'scroll_requested',left:element.scrollLeft,top:element.scrollTop};
      case 'key': element.dispatchEvent(new KeyboardEvent('keydown',{key:request.key,bubbles:true}));element.dispatchEvent(new KeyboardEvent('keyup',{key:request.key,bubbles:true}));return {status:'dispatched_unverified',verification:'Synthetic DOM keyboard events; use native keyboard tools for browser shortcuts or trusted input.'};
      case 'upload_begin': {
        if(!element.matches('input[type="file"]')||!Number.isSafeInteger(request.size)||request.size<0||request.size>33554432)fail('invalid_upload','Select a file input and a file of at most 32 MiB');
        if(uploads.size>=4)fail('busy','Too many uploads');
        const id=crypto.randomUUID();uploads.set(id,{element,name:request.name,mime:request.mime||'application/octet-stream',size:request.size,length:0,chunks:[],expires:Date.now()+300000});
        return {status:'upload_ready',uploadID:id};
      }
      default: fail('unsupported_action','Unsupported DOM operation');
    }
  }
  globalThis.__macpilotBridge={dispatch,documentID};
  if(globalThis.chrome?.runtime?.onMessage) chrome.runtime.onMessage.addListener((request,sender,respond)=>{
    if(sender.id!==chrome.runtime.id)return false;
    dispatch(request).then(result=>respond({ok:true,result}),error=>respond({ok:false,error:{code:error.code||'browser_error',message:error.message}}));return true;
  });
})();
