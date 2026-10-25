(()=>{'use strict';
const {model,layouts}=JSON.parse(document.getElementById('c4fy-data').textContent);
// Reserve a separate navigation row so the parent card cannot cover model edges.
for(const layout of layouts){if(model.views.find(v=>v.id===layout.id)?.level>1){
 const offset=110;layout.height+=offset;
 for(const n of layout.nodes)n.y+=offset;
 for(const e of layout.edges){for(const p of e.points)p[1]+=offset;e.label.y+=offset;}
 if(layout.boundary)layout.boundary.y+=offset;
}}
const ko=model.locale==='ko';
const L=ko?{context:'시스템 맥락',container:'실행 단위',component:'내부 구성',person:'사용자',system:'소프트웨어 시스템',external:'외부 시스템',containerKind:'컨테이너',componentKind:'컴포넌트',light:'라이트',dark:'다크',search:'노드 검색',fit:'맞춤',relations:'관계 자세히',tech:'기술 · 프로토콜',source:'소스 근거',none:'기록된 소스 근거가 없습니다.',open:'내부 살펴보기',scope:'범위',svg:'SVG 저장',json:'모델 저장',noMatch:'일치하는 노드가 없습니다.',back:'상위 구조로',optional:'선택 경로',evidence:'소스 기반 구조 · 런타임 동작 검증과 별개',generic:'작성된 모델 · 런타임 검증과 별개',boundary:'경계',view:'구조도 선택',transition:'구조도 전환 완료',select:'선택',zoomIn:'확대',zoomOut:'축소'}:{context:'Context',container:'Containers',component:'Components',person:'Person',system:'Software system',external:'External system',containerKind:'Container',componentKind:'Component',light:'Light',dark:'Dark',search:'Find a node',fit:'Fit',relations:'Relationships',tech:'Technology · Protocol',source:'Source evidence',none:'No source evidence recorded.',open:'Explore inside',scope:'Scope',svg:'Save SVG',json:'Save model',noMatch:'No matching nodes.',back:'Parent view',optional:'Optional path',evidence:'Source-backed structure · not runtime verification',generic:'Authored model · not runtime verification',boundary:'boundary',view:'Choose view',transition:'View changed',select:'Select',zoomIn:'Zoom in',zoomOut:'Zoom out'};
const $=s=>document.querySelector(s), h=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const es=new Map(model.elements.map(e=>[e.id,e])),rs=new Map(model.relationships.map(e=>[e.id,e]));
const kind=e=>e.external?L.external:({person:L.person,system:L.system,container:L.containerKind,component:L.componentKind}[e.kind]);
const levelName=n=>[L.context,L.container,L.component][n-1];
const icons={person:'<circle cx="12" cy="7" r="3.5"/><path d="M5 21v-3a7 7 0 0 1 14 0v3"/>',system:'<rect x="3" y="4" width="18" height="14" rx="4"/><path d="M8 22h8M12 18v4M7 9h3m4 0h3"/>',container:'<rect x="3" y="3" width="18" height="18" rx="5"/><path d="M3 9h18M8 6h.01m4 0h.01M8 14h8m-8 3h5"/>',component:'<rect x="5" y="5" width="14" height="14" rx="4"/><path d="M9 1v4m6-4v4M9 19v4m6-4v4M1 9h4m-4 6h4m14-6h4m-4 6h4"/>'};
const icon=k=>`<svg class="node-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[k]||icons.system}</svg>`;
const mark='<svg class="brand-mark" viewBox="0 0 40 40" aria-hidden="true"><rect x="2" y="2" width="17" height="17" rx="7" fill="#bba3e4"/><rect x="21" y="2" width="17" height="17" rx="7" fill="#a8d6bd"/><rect x="2" y="21" width="17" height="17" rx="7" fill="#f1cca0"/><rect x="21" y="21" width="17" height="17" rx="7" fill="#adc7ee"/><circle cx="8" cy="10" r="1.2" fill="#4b3d62"/><circle cx="13" cy="10" r="1.2" fill="#4b3d62"/><path d="M8 13q2.5 2 5 0" fill="none" stroke="#4b3d62" stroke-linecap="round"/></svg>';
let current=model.views[0], currentLayout=layouts[0],selected=current.scope,zoom=1,scale=1,generation=0,animations=[],scene=null;
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
let requested='';try{requested=decodeURIComponent(location.hash.slice(1));}catch{}if(model.views.some(v=>v.id===requested)){current=model.views.find(v=>v.id===requested);currentLayout=layouts.find(l=>l.id===requested);selected=current.scope;}
function drill(id){return model.views.find(v=>v.scope===id&&v.level===({system:2,container:3}[es.get(id)?.kind]));}
function parentView(){return model.views.find(v=>v.level===current.level-1&&(current.level===2?v.scope===current.scope:v.scope===es.get(current.scope)?.parent));}
$('#app').innerHTML=`<header class="topbar"><div class="brand">${mark}<span>C4fy</span></div><span class="title-divider"></span><h1>${h(model.title)}</h1><div class="toolbar"><button id="theme" class="theme-button"></button><button id="svg-export">${L.svg}</button><button id="json-export">${L.json}</button></div></header><section class="intro"><div><div class="eyebrow" id="eyebrow"></div><h2 id="view-title"></h2><p id="view-description"></p></div><nav class="tabs" role="tablist" aria-label="C4"></nav></section><main><div class="workspace"><section class="diagram-panel" aria-labelledby="view-title"><div class="diagram-top"><nav class="breadcrumbs" aria-label="${L.scope}" id="breadcrumbs"></nav><div class="view-menu" hidden><select id="view-select" aria-label="${L.view}"></select></div><div class="search-wrap"><label class="sr-only" for="search">${L.search}</label><input id="search" type="search" placeholder="${L.search}" autocomplete="off"></div></div><div id="stage" role="tabpanel" aria-labelledby="view-title" tabindex="0"></div><div class="diagram-bottom"><div class="legend"></div><span class="pan-hint" hidden></span><div class="zoom-controls"><button id="zoom-out" aria-label="${L.zoomOut}">−</button><output id="zoom-value"></output><button id="zoom-in" aria-label="${L.zoomIn}">+</button><button id="fit">${L.fit}</button></div></div></section><aside class="side-panel" id="details" aria-label="${L.select}"></aside></div><details class="relations"><summary id="relations-summary"></summary><ol id="relations-list"></ol></details></main><footer class="footer"><span id="evidence-note"></span><span id="revision"></span></footer><div role="status" class="sr-only" id="status" aria-live="polite"></div>`;
const stage=$('#stage');
function theme(value){document.documentElement.dataset.theme=value;$('#theme').textContent=value==='dark'?`☾ ${L.dark}`:`☀ ${L.light}`;$('#theme').setAttribute('aria-label',value==='dark'?L.light:L.dark);try{localStorage.setItem('c4fy-theme',value);}catch{}}
let stored;try{stored=localStorage.getItem('c4fy-theme');}catch{}theme(['light','dark'].includes(stored)?stored:(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'));
$('#theme').onclick=()=>theme(document.documentElement.dataset.theme==='dark'?'light':'dark');
function sourceHTML(s){const label=`${s.path}:${s.line}${s.endLine&&s.endLine!==s.line?'–'+s.endLine:''}`;let url;try{const r=new URL(model.repository?.url);if(r.hostname==='github.com'){r.pathname=r.pathname.replace(/\.git\/?$/,'').replace(/\/$/,'')+'/blob/'+model.repository.revision+'/'+s.path.split('/').map(encodeURIComponent).join('/');r.hash=`L${s.line}${s.endLine?'-L'+s.endLine:''}`;url=r.href;}}catch{}return `<li>${url?`<a href="${h(url)}" target="_blank" rel="noopener noreferrer" title="${h(label)}">${h(s.path.split('/').at(-1)+':'+s.line+(s.endLine&&s.endLine!==s.line?'–'+s.endLine:''))}</a>`:h(label)}</li>`;}
let flow=null;
function details(id,isRelation=false,showFlow=true){selected=id;const e=isRelation?rs.get(id):es.get(id);if(!e)return;
 const candidate=isRelation?null:drill(id),next=candidate?.id!==current.id?candidate:null;
 let section='description',page=0;
 const renderDetail=()=>{const labels=ko?{description:'책임',technology:'기술',sources:'근거',relationships:'관계'}:{description:'Responsibility',technology:'Technology',sources:'Evidence',relationships:'Relationships'};
 const related=current.relationships.filter(rid=>{const r=rs.get(rid);return isRelation?rid===id:r.source===id||r.target===id;});
 let entries=section==='sources'?(e.sources||[]).map(sourceHTML):section==='relationships'?related.map(rid=>{const r=rs.get(rid);return `<button class="detail-relation" data-relation="${rid}">${h(es.get(r.source).name)} → ${h(es.get(r.target).name)} · ${h(r.description)}${r.technology?' · '+h(r.technology):''}</button>`;}):String(section==='technology'?e.technology||L.none:e.description).match(/[^]{1,120}/g)?.map(h)||[];
 if(!entries.length)entries=[h(L.none)];page=Math.min(page,entries.length-1);
 $('#details').innerHTML=`<div class="detail-heading"><strong>${h(isRelation?e.description:e.name)}</strong><nav>${Object.entries(labels).map(([key,label])=>`<button data-section="${key}" aria-pressed="${key===section}">${label}</button>`).join('')}</nav>${next?`<button class="drill-button" data-view="${next.id}">${L.open} ↗</button>`:''}</div><div class="detail-content">${section==='sources'?'<ul class="source-list">'+entries[page]+'</ul>':entries[page]}</div><div class="detail-pages"><button data-page="-1" aria-label="${ko?'이전 항목':'Previous item'}" ${page===0?'disabled':''}>‹</button><span>${page+1} / ${entries.length}</span><button data-page="1" aria-label="${ko?'다음 항목':'Next item'}" ${page===entries.length-1?'disabled':''}>›</button></div>`;
 $('#details').querySelectorAll('[data-section]').forEach(b=>b.onclick=()=>{section=b.dataset.section;page=0;renderDetail();});$('#details').querySelectorAll('[data-page]').forEach(b=>b.onclick=()=>{page+=Number(b.dataset.page);renderDetail();});$('#details').querySelectorAll('[data-relation]').forEach(b=>b.onclick=()=>details(b.dataset.relation,true));const b=$('#details [data-view]');if(b)b.onclick=()=>switchView(b.dataset.view,id);
 };renderDetail();
 stage.querySelectorAll('.node').forEach(n=>n.setAttribute('aria-pressed',String(!isRelation&&n.dataset.id===id)));
 flow=showFlow?{id,isRelation}:null;filter();
 if(flow){$('.relations').open=true;$('#status').textContent=ko?'선택한 카드의 연결 관계 표시':'Showing selected connections';}
}
function edgeSVG(edge,index,exportMode=false){const r=rs.get(edge.id),label=edge.label;const points=edge.points.map(p=>p.join(',')).join(' ');return `<polyline class="edge ${r.optional?'optional':''}" data-id="${edge.id}" points="${points}" marker-end="url(#arrow)"/><polyline class="flow-trace" data-id="${edge.id}" points="${points}" aria-hidden="true"/><g class="edge-label" data-id="${edge.id}" role="button" tabindex="0" aria-label="${h(r.description)}"><title>${h(`${es.get(r.source).name} → ${es.get(r.target).name}: ${r.description}${r.technology?' · '+r.technology:''}`)}</title><rect x="${label.x}" y="${label.y}" width="${label.width}" height="${label.height}" rx="10"/><text x="${label.x+label.width/2}" y="${label.y+label.height/2+1}">${h(label.text)}</text></g>`;}
function buildScene(layout,view){const div=document.createElement('div');div.className='scene';div.style.width=layout.width+'px';div.style.height=layout.height+'px';div.dataset.view=view.id;
 const b=layout.boundary;div.innerHTML=`<svg width="${layout.width}" height="${layout.height}" viewBox="0 0 ${layout.width} ${layout.height}" aria-label="${h(view.title)}"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M1 1 L9 5 L1 9" fill="none" stroke="var(--edge)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>${b?`<g class="scope-group" data-entity="${b.id}"><rect class="scope-box" x="${b.x}" y="${b.y}" width="${b.width}" height="${b.height}" rx="27"/><text class="scope-label" x="${b.x+17}" y="${b.y+25}">${h(es.get(view.scope).name)} · ${h(L.boundary)}</text></g>`:''}<g class="edges">${layout.edges.map(edgeSVG).join('')}</g></svg>`;
 const parent=parentView();
 if(parent){const scope=es.get(view.scope),card=document.createElement('button');card.className='parent-card';card.style.left=(b?.x||24)+'px';card.style.top='18px';card.setAttribute('aria-label',`${L.back}: ${scope.name}`);card.innerHTML=`<span class="parent-card-label">↑ C${parent.level} · ${h(L.back)}</span><strong>${h(scope.name)}</strong>`;card.onclick=()=>switchView(parent.id,view.scope);div.append(card);}
 for(const n of layout.nodes){const e=es.get(n.id),next=drill(e.id),button=document.createElement('button');button.className='node';button.dataset.id=e.id;button.dataset.entity=e.id;button.dataset.kind=e.kind;button.dataset.external=String(!!e.external);button.style.cssText=`left:${n.x}px;top:${n.y}px;width:${n.width}px;height:${n.height}px`;button.setAttribute('aria-pressed','false');button.setAttribute('aria-label',`${e.name}. ${e.description}${next?'. '+L.open:''}`);button.title=e.name;button.innerHTML=`<span class="node-top"><span class="node-type">${icon(e.kind)}${h(kind(e))}</span>${next?'<span class="drill-hint" aria-hidden="true">↗</span>':''}</span><span class="node-name">${h(e.name)}</span><span class="node-description">${h(e.description)}</span>${e.technology?`<span class="node-tech">${h(e.technology)}</span>`:''}`;button.onclick=()=>details(e.id);button.ondblclick=()=>{if(next)switchView(next.id,e.id);};button.onkeydown=event=>{if(event.key==='ArrowDown'&&event.altKey&&next){event.preventDefault();switchView(next.id,e.id);}};div.append(button);}
 div.querySelectorAll('.edge,.edge-label').forEach(el=>{const select=()=>details(el.dataset.id,true);el.addEventListener('click',select);el.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();select();}});});return div;
}
function transformFor(layout){const fit=Math.min((stage.clientWidth-22)/layout.width,(stage.clientHeight-22)/layout.height,1.4);const s=Math.max(.1,fit)*zoom;return {s,x:Math.max(12,(stage.clientWidth-layout.width*s)/2),y:Math.max(12,(stage.clientHeight-layout.height*s)/2)};}
function resize(){if(!scene)return;const t=transformFor(currentLayout);scale=t.s;scene.style.transform=`translate(${t.x}px,${t.y}px) scale(${t.s})`;$('#zoom-value').value=Math.round(t.s*100)+'%';const hint=$('.pan-hint');hint.hidden=currentLayout.width*t.s<=stage.clientWidth;hint.textContent=ko?'드래그 또는 스크롤로 이동':'Drag or scroll to pan';}
function clearMorph(){stage.querySelectorAll('.scope-morph,.morph-wires').forEach(n=>n.remove());stage.querySelectorAll('[data-morph-hidden]').forEach(n=>{n.style.visibility='';delete n.dataset.morphHidden;});}
function cancelMotion(){clearMorph();generation++;for(const a of animations)a.cancel();animations=[];stage.querySelectorAll('.scene.old').forEach(n=>n.remove());}
function motion(el,frames,options={}){const a=el.animate(frames,{duration:460,easing:'cubic-bezier(.22,.8,.24,1)',...options});animations.push(a);return a;}
function refreshChrome(){
 $('#eyebrow').textContent=`C${current.level} / ${levelName(current.level)}`;$('#view-title').textContent=current.title;$('#view-description').textContent=current.description||'';
 $('.tabs').innerHTML=[1,2,3].filter(n=>model.views.some(v=>v.level===n)).map(n=>`<button class="tab" role="tab" aria-controls="stage" aria-selected="${n===current.level}" tabindex="${n===current.level?0:-1}" data-level="${n}"><span class="level">C${n}</span>${h(levelName(n))}</button>`).join('');
 $('.tabs').querySelectorAll('button').forEach(b=>{b.onclick=()=>{const n=Number(b.dataset.level);const candidate=model.views.find(v=>v.level===n&&(v.scope===current.scope||es.get(v.scope)?.parent===current.scope||v.scope===es.get(current.scope)?.parent))||model.views.find(v=>v.level===n);switchView(candidate.id);$('.tab[aria-selected=true]')?.focus({preventScroll:true});};b.onkeydown=e=>{const all=[...$('.tabs').querySelectorAll('button')],i=all.indexOf(b);let target;if(e.key==='ArrowRight')target=all[(i+1)%all.length];if(e.key==='ArrowLeft')target=all[(i+all.length-1)%all.length];if(e.key==='Home')target=all[0];if(e.key==='End')target=all.at(-1);if(target){e.preventDefault();target.click();}};});
 $('#breadcrumbs').textContent=es.get(current.scope).name;
 const same=model.views.filter(v=>v.level===current.level);$('.view-menu').hidden=same.length<2;$('#view-select').innerHTML=same.map(v=>`<option value="${v.id}" ${v.id===current.id?'selected':''}>${h(v.title)}</option>`).join('');$('#view-select').onchange=e=>switchView(e.target.value);
 const used=[...new Set(current.nodes.map(id=>es.get(id).kind))];$('.legend').innerHTML=used.map(k=>`<span><i style="background:var(--${k})"></i>${h(kind({kind:k}))}</span>`).join('');
 $('.relations').open=currentLayout.edges.some(e=>e.label.compact);$('#relations-summary').textContent=`${L.relations} · ${current.relationships.length}`;$('#relations-list').innerHTML=current.relationships.map((id,i)=>{const r=rs.get(id);return `<li class="relation-row"><button data-id="${id}"><span class="relation-number">${i+1}</span><span class="relation-body"><span>${h(r.description)}${r.optional?' · '+L.optional:''}</span><small>${h(es.get(r.source).name)} → ${h(es.get(r.target).name)}${r.technology?' · '+h(r.technology):''}</small></span></button></li>`;}).join('');$('#relations-list').querySelectorAll('button').forEach(b=>b.onclick=()=>details(b.dataset.id,true));
 $('#evidence-note').textContent=model.repository?L.evidence:L.generic;$('#revision').textContent=model.repository?`${model.repository.revision.slice(0,12)} · C4fy 0.1.0`:'C4fy 0.1.0';
}
function morphScope(cardBox,card,expanded,layout,view,reverse){
 const boundary=expanded.querySelector('.scope-group');if(!boundary||!layout.boundary)return false;
 const box=boundary.getBoundingClientRect(),origin=stage.getBoundingClientRect(),b=layout.boundary;
 const factor=box.width/b.width,layer=document.createElement('div');layer.className='scope-morph';layer.dataset.transition=reverse?'fold':'unfold';layer.inert=true;layer.setAttribute('aria-hidden','true');
 const frame=r=>({left:`${r.left-origin.left}px`,top:`${r.top-origin.top}px`,width:`${r.width}px`,height:`${r.height}px`,borderRadius:r===cardBox?'21px':'27px'});
 Object.assign(layer.style,frame(box));stage.append(layer);
 const hide=n=>{n.dataset.morphHidden='true';n.style.visibility='hidden';};
 const run=(el,frames,options={})=>motion(el,reverse?frames.map(f=>({...f,...(f.offset===undefined?{}:{offset:1-f.offset})})).reverse():frames,{duration:520,fill:'both',...(reverse?{easing:'cubic-bezier(.76,0,.78,.2)'}:{}),...options});
 const previousTransition=card.style.transition;card.style.transition='none';
 const cardStyle=getComputedStyle(card),cardScale=cardBox.width/parseFloat(cardStyle.width);
 const scaled=value=>value.replace(/(-?[\d.]+)px/g,(_,n)=>`${Number(n)*cardScale}px`);
 const cardFrame={...frame(cardBox),backgroundColor:cardStyle.backgroundColor,borderColor:cardStyle.borderTopColor,borderWidth:scaled(cardStyle.borderTopWidth),borderRadius:scaled(cardStyle.borderTopLeftRadius),boxShadow:scaled(cardStyle.boxShadow)};
 card.style.transition=previousTransition;
 const scopeStyle=getComputedStyle(layer);
 const scopeFrame={...frame(box),backgroundColor:scopeStyle.backgroundColor,borderColor:scopeStyle.borderTopColor,borderWidth:scopeStyle.borderTopWidth,borderRadius:`${27*factor}px`,boxShadow:'none'};
 run(layer,[cardFrame,scopeFrame]);
 const title=document.createElement('div');title.className='morph-title';title.style.zIndex='4';title.textContent=es.get(view.scope).name;layer.append(title);
 const name=card.querySelector('.node-name'),nameBox=name.getBoundingClientRect(),heading=boundary.querySelector('.scope-label'),headingBox=heading.getBoundingClientRect();
 const startTitle={transform:`translate(${nameBox.left-cardBox.left}px, ${nameBox.top-cardBox.top}px)`,fontSize:`${parseFloat(getComputedStyle(name).fontSize)*cardScale}px`,lineHeight:getComputedStyle(name).lineHeight==='normal'?'normal':`${parseFloat(getComputedStyle(name).lineHeight)*cardScale}px`};
 run(title,[startTitle,{...startTitle,offset:.25},{transform:`translate(${headingBox.left-box.left}px, ${headingBox.top-box.top}px)`,fontSize:`${11*factor}px`,lineHeight:`${headingBox.height}px`}]);
 const suffix=document.createElement('span');suffix.textContent=' · '+L.boundary;title.append(suffix);run(suffix,[{opacity:0},{opacity:0,offset:.65},{opacity:1}],{easing:'linear'});
 const cardFace=card.cloneNode(true);cardFace.classList.add('morph-card-face');cardFace.removeAttribute('data-entity');cardFace.removeAttribute('data-id');cardFace.classList.remove('dim','flow-dim');
 cardFace.style.cssText=`position:absolute;left:${-parseFloat(cardFrame.borderWidth)}px;top:${-parseFloat(cardFrame.borderWidth)}px;width:${cardStyle.width};height:${cardStyle.height};transform:scale(${cardScale});transform-origin:0 0;visibility:visible;background:transparent;border-color:transparent;box-shadow:none;pointer-events:none;z-index:3`;
 cardFace.querySelector('.node-name').style.visibility='hidden';layer.append(cardFace);run(cardFace,[{opacity:1},{opacity:0,offset:.25},{opacity:0}],{easing:'linear'});
 const svg=expanded.querySelector(':scope > svg').cloneNode(true);svg.classList.add('morph-wires');svg.querySelector('.scope-group')?.remove();svg.querySelectorAll('.flow-trace').forEach(n=>n.remove());
 const expandedBox=expanded.getBoundingClientRect();svg.style.cssText=`position:absolute;left:${expandedBox.left-origin.left}px;top:${expandedBox.top-origin.top}px;transform:scale(${factor});transform-origin:0 0;overflow:visible;pointer-events:none;z-index:5`;stage.append(svg);
 const marker=svg.querySelector('marker');if(marker){marker.id='morph-arrow';svg.querySelectorAll('[marker-end]').forEach(n=>n.setAttribute('marker-end','url(#morph-arrow)'));}
 run(svg,[{opacity:0},{opacity:0,offset:.3},{opacity:1,offset:.8},{opacity:1}],{easing:'linear'});
 const moving=new Map();
 for(const node of expanded.querySelectorAll('.node')){if(es.get(node.dataset.id)?.parent!==view.scope)continue;
  const rect=node.getBoundingClientRect(),clone=node.cloneNode(true);clone.removeAttribute('data-entity');clone.style.cssText=`position:absolute;left:${rect.left-box.left}px;top:${rect.top-box.top}px;width:${node.offsetWidth}px;height:${node.offsetHeight}px;transform-origin:0 0;transform:scale(${factor})`;clone.classList.remove('flow-dim','dim');layer.append(clone);moving.set(node.dataset.id,clone);hide(node);
  const dx=cardBox.width/2-(rect.left-box.left)-rect.width/2,dy=cardBox.height/2-(rect.top-box.top)-rect.height/2;
  run(clone,[{transform:`translate(${dx}px,${dy}px) scale(${factor})`},{transform:`scale(${factor})`}]);
  run(clone,[{opacity:0},{opacity:0,offset:.3},{opacity:1,offset:.8},{opacity:1}],{easing:'linear'});
 }
 const byID=new Map(layout.nodes.map(n=>[n.id,n]));
 const routes=layout.edges.map(edge=>({edge,rel:rs.get(edge.id),line:svg.querySelector(`.edge[data-id="${edge.id}"]`),label:svg.querySelector(`.edge-label[data-id="${edge.id}"]`)}));
 for(const route of routes){if(!moving.has(route.rel.source)||!moving.has(route.rel.target)){for(const el of [route.line,route.label].filter(Boolean))run(el,[{opacity:0},{opacity:0,offset:.75},{opacity:1}],{easing:'linear'});}}
 const tick=()=>{if(!layer.isConnected||!svg.isConnected)return;
  const inverse=svg.getScreenCTM()?.inverse();if(!inverse)return;
  const endpoint=(id,port)=>{const element=moving.get(id)||scene.querySelector(`.node[data-id="${id}"]`)||expanded.querySelector(`.node[data-id="${id}"]`),base=byID.get(id);if(!element||!base)return port;
   const rect=element.getBoundingClientRect(),point=new DOMPoint(rect.left+(port[0]-base.x)/base.width*rect.width,rect.top+(port[1]-base.y)/base.height*rect.height).matrixTransform(inverse);return [point.x,point.y];};
  for(const {edge,rel,line,label} of routes){const first=edge.points[0],last=edge.points.at(-1),start=endpoint(rel.source,first),end=endpoint(rel.target,last);
   const lengths=[0];for(let i=1;i<edge.points.length;i++)lengths.push(lengths.at(-1)+Math.hypot(edge.points[i][0]-edge.points[i-1][0],edge.points[i][1]-edge.points[i-1][1]));const total=lengths.at(-1)||1;
   const points=edge.points.map((p,i)=>{const t=lengths[i]/total;return [p[0]+(start[0]-first[0])*(1-t)+(end[0]-last[0])*t,p[1]+(start[1]-first[1])*(1-t)+(end[1]-last[1])*t];});line.setAttribute('points',points.map(p=>p.join(',')).join(' '));
   if(label)label.setAttribute('transform',`translate(${((start[0]-first[0])+(end[0]-last[0]))/2},${((start[1]-first[1])+(end[1]-last[1]))/2})`);
  }
  requestAnimationFrame(tick);
 };tick();
 hide(boundary);hide(expanded.querySelector('.edges'));return true;
}
function switchView(id,focusID){const next=model.views.find(v=>v.id===id);if(!next||scene&&next.id===current.id)return;
 stage.scrollTo({left:0,top:0,behavior:'instant'});
 const old=scene,oldView=current,oldLayout=currentLayout,oldBoxes=new Map();if(old)old.querySelectorAll('[data-entity]').forEach(n=>oldBoxes.set(n.dataset.entity,n.getBoundingClientRect()));
 cancelMotion();const token=generation;current=next;currentLayout=layouts.find(l=>l.id===id);zoom=1;scene=buildScene(currentLayout,current);stage.append(scene);refreshChrome();resize();details(current.scope,false,false);filter();
 const anchor=oldBoxes.get(focusID||((next.level>oldView.level)?next.scope:oldView.scope));
 const nextBoxes=new Map([...scene.querySelectorAll('[data-entity]')].map(n=>[n.dataset.entity,n.getBoundingClientRect()]));
 if(old&&!reduced.matches){old.classList.add('old');old.inert=true;old.setAttribute('aria-hidden','true');old.style.pointerEvents='none';const folding=next.level<oldView.level&&nextBoxes.has(oldView.scope),unfolding=next.level>oldView.level&&!!anchor;
  const morphed=folding?morphScope(nextBoxes.get(oldView.scope),scene.querySelector(`.node[data-id="${oldView.scope}"]`),old,oldLayout,oldView,true):unfolding?morphScope(anchor,old.querySelector(`.node[data-id="${next.scope}"]`),scene,currentLayout,current,false):false;
  motion(old,[{opacity:1},{opacity:0}],{duration:200,fill:'forwards'});
  scene.querySelectorAll('.node').forEach(node=>{const box=nextBoxes.get(node.dataset.entity),before=oldBoxes.get(node.dataset.entity);
   if(morphed&&unfolding&&es.get(node.dataset.id)?.parent===current.scope)return;
   if(morphed&&folding&&node.dataset.id===oldView.scope){motion(node,[{opacity:0},{opacity:0,offset:.85},{opacity:1}],{duration:520,fill:'both'});return;}
   if(before){old.querySelector(`[data-entity="${node.dataset.entity}"]`).style.visibility='hidden';motion(node,[{transform:`translate(${(before.x-box.x)/scale}px,${(before.y-box.y)/scale}px)`,opacity:1},{transform:'none',opacity:1}],{duration:520});}
   else motion(node,[{opacity:0},{opacity:1}],{duration:520});
  });
  if(!morphed)motion(scene.querySelector('.edges'),[{opacity:0},{opacity:1}],{duration:520});
  Promise.allSettled(animations.map(a=>a.finished)).then(()=>{if(token===generation){clearMorph();old.remove();animations=[];$('#status').textContent=`${L.transition}: ${current.title}`;}});
 }else{if(old)old.remove();$('#status').textContent=`${L.transition}: ${current.title}`;}
 try{history.replaceState(null,'','#'+id);}catch{}
 stage.scrollTo({left:0,top:0,behavior:'instant'});
}
function filter(){if(!scene)return;
 const edges=new Set(flow?current.relationships.filter(id=>{const r=rs.get(id);return flow.isRelation?id===flow.id:r.source===flow.id||r.target===flow.id;}):[]);
 const nodes=new Set(flow&&!flow.isRelation?[flow.id]:[]);for(const id of edges){const r=rs.get(id);nodes.add(r.source);nodes.add(r.target);}
 scene.querySelectorAll('.node').forEach(n=>n.classList.toggle('flow-dim',!!flow&&!nodes.has(n.dataset.id)));
 scene.querySelectorAll('.edge,.edge-label,.flow-trace').forEach(n=>{n.classList.toggle('flow-dim',!!flow&&!edges.has(n.dataset.id));n.classList.toggle('active',!!flow&&edges.has(n.dataset.id));});
 $('#relations-list').querySelectorAll('.relation-row').forEach(n=>n.hidden=!!flow&&!edges.has(n.querySelector('button').dataset.id));
 $('#relations-summary').textContent=flow?(ko?'연결 플로우':'Connected flow')+' · '+edges.size:L.relations+' · '+current.relationships.length;
const q=$('#search').value.trim().toLocaleLowerCase();const match=new Set(current.nodes.filter(id=>{const e=es.get(id);return `${e.name} ${e.description} ${e.technology||''}`.toLocaleLowerCase().includes(q);}));scene.querySelectorAll('.node').forEach(n=>n.classList.toggle('dim',q&&!match.has(n.dataset.id)));scene.querySelectorAll('.edge,.edge-label,.flow-trace').forEach(n=>{const r=rs.get(n.dataset.id);n.classList.toggle('dim',q&&!match.has(r.source)&&!match.has(r.target));});stage.querySelector('.empty-search')?.remove();if(q&&!match.size){const n=document.createElement('div');n.className='empty-search';n.textContent=L.noMatch;stage.append(n);}}
stage.addEventListener('click',e=>{if(!e.target.closest('.node,.edge,.edge-label,.parent-card')){flow=null;filter();}});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'){flow=null;filter();}});
 $('#search').oninput=filter;$('#search').onkeydown=e=>{if(e.key==='Escape'){$('#search').value='';filter();}};
$('#zoom-in').onclick=()=>{cancelMotion();zoom=Math.min(2.8,zoom*1.2);resize();};$('#zoom-out').onclick=()=>{cancelMotion();zoom=Math.max(.6,zoom/1.2);resize();};$('#fit').onclick=()=>{cancelMotion();zoom=1;resize();stage.scrollTo(0,0);};
new ResizeObserver(()=>{cancelMotion();resize();}).observe(stage);
reduced.addEventListener('change',()=>{if(reduced.matches){cancelMotion();resize();}});
function download(text,mime,name){const url=URL.createObjectURL(new Blob([text],{type:mime})),a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);}
function wrap(text,limit){const lines=[];let line='',units=0;for(const c of text){const n=c.codePointAt(0)>255||/[MW@%#&]/.test(c)?2:1;if(units+n>limit){lines.push(line);line='';units=0;}line+=c;units+=n;}if(line)lines.push(line);return lines;}
function exportSVG(){const lay=currentLayout,palette={person:'#fff0d9',system:'#e9e0fa',container:'#dff3e9',component:'#e2edff'},text=(x,y,s,size=12,fill='#332f42')=>`<text x="${x}" y="${y}" font-size="${size}" fill="${fill}">${h(s)}</text>`;let body='';
 if(lay.boundary){const b=lay.boundary;body+=`<rect x="${b.x}" y="${b.y}" width="${b.width}" height="${b.height}" rx="25" fill="#faf7ff" stroke="#b5a1c9" stroke-dasharray="5 5"/>`+text(b.x+16,b.y+25,es.get(current.scope).name+' · '+L.boundary,11);}
 for(const edge of lay.edges){const r=rs.get(edge.id);body+=`<polyline points="${edge.points.map(p=>p.join(',')).join(' ')}" fill="none" stroke="#8b789d" stroke-width="1.8" ${r.optional?'stroke-dasharray="5 5"':''} marker-end="url(#a)"/>`;const l=edge.label;body+=`<rect x="${l.x}" y="${l.y}" width="${l.width}" height="${l.height}" rx="10" fill="#fffefa" stroke="#e5dfe9"/><text x="${l.x+l.width/2}" y="${l.y+17}" text-anchor="middle" font-size="10" fill="#706b80">${h(l.text)}</text>`;}
 for(const n of lay.nodes){const e=es.get(n.id);body+=`<rect x="${n.x}" y="${n.y}" width="${n.width}" height="${n.height}" rx="21" fill="${e.external?'#efeef3':palette[e.kind]}" stroke="#baa8c9"/>`+text(n.x+17,n.y+25,kind(e),10,'#706b80');wrap(e.name,26).slice(0,2).forEach((s,i)=>body+=text(n.x+17,n.y+54+i*19,s,15));const nameLines=Math.min(2,wrap(e.name,26).length);wrap(e.description,36).slice(0,2).forEach((s,i)=>body+=text(n.x+17,n.y+61+nameLines*18+i*16,s,11,'#706b80'));if(e.technology)body+=text(n.x+17,n.y+n.height-13,wrap(e.technology,40)[0],9,'#706b80');}
 const compact=lay.edges.filter(e=>e.label.compact);let extra=0;for(const edge of compact){const r=rs.get(edge.id);const key=`${edge.label.text}. ${r.description} (${es.get(r.source).name} → ${es.get(r.target).name})`;for(const line of wrap(key,Math.max(20,Math.floor((lay.width-60)/6.5)))){extra+=20;body+=text(30,lay.height+extra,line,11);}extra+=4;}
 download(`<svg xmlns="http://www.w3.org/2000/svg" width="${lay.width}" height="${lay.height+extra+60}" viewBox="0 0 ${lay.width} ${lay.height+extra+60}" font-family="system-ui,sans-serif"><title>${h(model.title+' · '+current.title)}</title><rect width="100%" height="100%" fill="#fffefa"/><defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M1 1L9 5L1 9" fill="none" stroke="#8b789d" stroke-width="1.6"/></marker></defs>${body}${text(30,lay.height+extra+40,model.title+' · '+current.title,12)}</svg>`,'image/svg+xml',`c4fy-${current.id}.svg`);
}
$('#svg-export').onclick=exportSVG;$('#json-export').onclick=()=>download(JSON.stringify(model,null,2),'application/json','c4fy-model.json');
let drag;stage.addEventListener('pointerdown',e=>{if(e.pointerType!=='mouse'||e.button!==0||e.target.closest('button,.edge,.edge-label'))return;drag={x:e.clientX,y:e.clientY,left:stage.scrollLeft,top:stage.scrollTop};stage.setPointerCapture(e.pointerId);stage.classList.add('dragging');});stage.addEventListener('pointermove',e=>{if(drag){stage.scrollLeft=drag.left+drag.x-e.clientX;stage.scrollTop=drag.top+drag.y-e.clientY;}});for(const event of ['pointerup','pointercancel','lostpointercapture'])stage.addEventListener(event,()=>{drag=null;stage.classList.remove('dragging');});
// First render is static. Motion only describes explicit navigation.
const first=current.id;scene=null;switchView(first);
})();
