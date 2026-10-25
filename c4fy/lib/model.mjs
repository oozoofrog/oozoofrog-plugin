import {iconPaths} from './icons.mjs';
// C4fy model validation. Original implementation; no renderer dependency.
const ID = /^[a-z][a-z0-9_-]{0,63}$/;
const kinds = new Set(['person', 'system', 'container', 'component', 'code']);
const codeTypes = new Set(['class','interface','struct','enum','protocol','function','method','type','module','object','table']);
const object = x => x !== null && typeof x === 'object' && !Array.isArray(x);
export function validateModel(m) {
  const errors=[];
  const fail=(path,message)=>errors.push({path,message});
  const keys=(o,allowed,path)=>{if(!object(o)){fail(path,'Expected object');return false;}for(const k of Object.keys(o))if(!allowed.includes(k))fail(`${path}.${k}`,'Unknown field');return true;};
  const str=(v,p,max=200)=>{if(typeof v!=='string'||!v.trim()||v.length>max||[...v].some(c=>{const n=c.codePointAt(0);return (n<32&&![9,10,13].includes(n))||(n>=0xD800&&n<=0xDFFF)||n===0xFFFE||n===0xFFFF;}))fail(p,`Expected nonempty text, at most ${max} characters`);};
  const sources=(list,p)=>{if(list===undefined)return;if(!Array.isArray(list)||list.length>12){fail(p,'Expected up to 12 source references');return;}list.forEach((s,i)=>{const q=`${p}[${i}]`;if(!keys(s,['path','line','endLine'],q))return; if(typeof s.path!=='string'||s.path.length>240||s.path.startsWith('/')||/[:\\\x00-\x1f]/.test(s.path)||s.path.split('/').some(x=>!x||x==='.'||x==='..'))fail(q,'Source path must be a safe repository-relative path');if(!Number.isSafeInteger(s.line)||s.line<1||s.line>1000000)fail(q,'Invalid start line');if(s.endLine!==undefined&&(!Number.isSafeInteger(s.endLine)||s.endLine<s.line||s.endLine>1000000))fail(q,'Invalid end line');});};
  if(!keys(m,['version','title','description','locale','repository','elements','relationships','views'],'model'))return errors;
  if(m.version!==1)fail('version','Expected 1');str(m.title,'title',120);if(m.description!==undefined)str(m.description,'description',500);
  if(m.locale!==undefined&&!['ko','en'].includes(m.locale))fail('locale','Supported locales: ko, en');
  if(m.repository!==undefined&&keys(m.repository,['url','revision'],'repository')){
    if(typeof m.repository.url!=='string'||!/^https:\/\/[^/@\s]+\//.test(m.repository.url))fail('repository.url','Expected credential-free HTTPS repository URL');
    else {try{const u=new URL(m.repository.url);if(u.username||u.password||u.search||u.hash)fail('repository.url','Credentials, query and fragment are not allowed');}catch{fail('repository.url','Invalid URL');}}
    if(!/^[a-f0-9]{40}$/.test(m.repository.revision||''))fail('repository.revision','Expected full commit SHA');
  }
  for(const k of ['elements','relationships','views'])if(!Array.isArray(m[k])||m[k].length>(k==='views'?30:300))fail(k,'Expected bounded array');
  if(errors.length)return errors;
  if(!m.elements.length||!m.views.length)fail('model','At least one element and view required');
  const es=new Map(),rs=new Map(),vs=new Set();
  const add=(o,map,p)=>{if(typeof o.id!=='string'||!ID.test(o.id))fail(p+'.id','Use a lowercase stable ID');if(map.has(o.id))fail(p+'.id','Duplicate ID');map.set(o.id,o);};
  m.elements.forEach((e,i)=>{const p=`elements[${i}]`;if(!keys(e,['id','kind','name','description','parent','technology','external','sources','roleLabel','icon','codeType'],p))return;add(e,es,p);if(!kinds.has(e.kind))fail(p+'.kind','Invalid C4 kind');str(e.name,p+'.name',80);if(e.roleLabel!==undefined)str(e.roleLabel,p+'.roleLabel',48);if(e.icon!==undefined&&(typeof e.icon!=='string'||!Object.hasOwn(iconPaths,e.icon)))fail(p+'.icon','Unknown icon identifier');str(e.description,p+'.description',500);if(e.technology!==undefined)str(e.technology,p+'.technology',100);if(['container','component'].includes(e.kind)&&!e.technology)fail(p+'.technology','Container/component requires technology');if(e.external!==undefined&&typeof e.external!=='boolean')fail(p+'.external','Expected boolean');sources(e.sources,p+'.sources');
    if(e.kind==='code'){if(!codeTypes.has(e.codeType))fail(p+'.codeType','Expected a supported code classification');if(!e.sources?.length)fail(p+'.sources','Code elements require source evidence');}
    else if(e.codeType!==undefined)fail(p+'.codeType','Only code elements use codeType');
  });
  for(const e of es.values()){
    const wanted={container:'system',component:'container',code:'component'}[e.kind];
    if(wanted&&es.get(e.parent)?.kind!==wanted)fail(`elements.${e.id}.parent`,`${e.kind} must belong to ${wanted}`);
    if(!wanted&&e.parent!==undefined)fail(`elements.${e.id}.parent`,'Person/system cannot have a parent');
    if(e.parent===e.id)fail(`elements.${e.id}.parent`,'Cannot own itself');
    if(e.external&&e.kind!=='system')fail(`elements.${e.id}.external`,'Only external systems use external=true');
  }
  m.relationships.forEach((r,i)=>{const p=`relationships[${i}]`;if(!keys(r,['id','source','target','description','technology','optional','sources'],p))return;add(r,rs,p);if(!es.has(r.source)||!es.has(r.target))fail(p,'Relationship endpoint does not exist');if(r.source===r.target)fail(p,'Self relationship is not supported');str(r.description,p+'.description',160);if(r.technology!==undefined)str(r.technology,p+'.technology',100);if(r.optional!==undefined&&typeof r.optional!=='boolean')fail(p+'.optional','Expected boolean');sources(r.sources,p+'.sources');if([r.source,r.target].some(id=>es.get(id)?.kind==='code')&&!r.sources?.length)fail(p+'.sources','Code relationships require source evidence');});
  m.views.forEach((v,i)=>{const p=`views[${i}]`;if(!keys(v,['id','title','description','level','scope','nodes','relationships','positions'],p))return;
    if(typeof v.id!=='string'||!ID.test(v.id)||vs.has(v.id))fail(p+'.id','Invalid or duplicate view ID');vs.add(v.id);str(v.title,p+'.title',120);if(v.description!==undefined)str(v.description,p+'.description',500);
    const scope=es.get(v.scope);if(![1,2,3,4].includes(v.level)||!scope||scope.kind!==({1:'system',2:'system',3:'container',4:'component'}[v.level])||scope.external)fail(p+'.scope','Scope must be an internal system for C1/C2, container for C3 or component for C4');
    if(!Array.isArray(v.nodes)||!v.nodes.length||v.nodes.length>40||new Set(v.nodes).size!==v.nodes.length){fail(p+'.nodes','Expected 1–40 unique nodes');return;}
    if(!Array.isArray(v.relationships)||new Set(v.relationships).size!==v.relationships.length){fail(p+'.relationships','Expected unique relationship IDs');return;}
    if(v.level===1&&!v.nodes.includes(v.scope))fail(p,'Context must include its scoped system');
    let inside=0;
    for(const id of v.nodes){const e=es.get(id);if(!e){fail(p+'.nodes',`Unknown node ${id}`);continue;}
      if(v.level===1&&!['person','system'].includes(e.kind))fail(p,'C1 only admits persons/systems');
      if(v.level===2&&!(e.kind==='person'||(e.kind==='system'&&e.id!==v.scope)||(e.kind==='container'&&e.parent===v.scope)))fail(p,'C2 shows scoped containers and supporting persons/systems');
      if(v.level===3&&!(e.kind==='person'||(e.kind==='system'&&e.id!==scope?.parent)||(e.kind==='container'&&e.id!==v.scope&&e.parent===scope?.parent)||(e.kind==='component'&&e.parent===v.scope)))fail(p,'C3 shows scoped components and supporting sibling containers/persons/systems');
      if(v.level===4){const container=es.get(scope?.parent),system=container?.parent;
        if(!(e.kind==='person'||(e.kind==='system'&&e.id!==system)||(e.kind==='container'&&e.id!==container?.id&&e.parent===system)||(e.kind==='component'&&e.id!==v.scope&&e.parent===scope?.parent)||(e.kind==='code'&&e.parent===v.scope)))fail(p,'C4 shows scoped code and supporting sibling components/containers/persons/systems');
      }
      if(e.parent===v.scope)inside++;
    }
    if(v.level>1&&!inside)fail(p,'Expanded view needs at least one child of its scope');
    for(const id of v.relationships){const r=rs.get(id);if(!r||!v.nodes.includes(r.source)||!v.nodes.includes(r.target))fail(p+'.relationships',`Missing or hidden endpoints: ${id}`);}
    if(v.positions!==undefined){if(!object(v.positions))fail(p+'.positions','Expected mapping');else {const occupied=new Set();for(const [id,pos] of Object.entries(v.positions)){if(!v.nodes.includes(id)||!Array.isArray(pos)||pos.length!==2||pos.some(x=>!Number.isInteger(x)||x<0||x>12))fail(p+'.positions','Expected node: [column,row], integers 0–12');else if(occupied.has(pos.join(',')))fail(p+'.positions','Duplicate position');else occupied.add(pos.join(','));}}}
  });
  return errors;
}
export function assertModel(m){const e=validateModel(m);if(e.length)throw new Error(e.map(x=>`${x.path}: ${x.message}`).join('\n'));return m;}
