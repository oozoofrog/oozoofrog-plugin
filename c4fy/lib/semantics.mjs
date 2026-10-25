// Offline, deterministic hints over model metadata. No source execution or remote AI calls.
export const semanticTypes=['actor','external','application','service','datastore','channel','device','contract','function','structure','unknown'];
export const semanticRoles=['api','storage','bridge','validation','ui','device','messaging','compute','unknown'];
export const semanticBases=['declared','inferred','inherited','fallback'];
const hash=s=>{let n=2166136261;for(const c of s){n^=c.codePointAt(0);n=Math.imul(n,16777619);}return n>>>0;};
const words=s=>String(s||'').replace(/([a-z])([A-Z])/g,'$1 $2').toLowerCase().split(/[^\p{L}\p{N}]+/u).filter(Boolean);
const generic=new Set('src source sources skill readme lib libs app apps test tests spec specs tool tools package packages module modules core common shared main index api store storage database cache queue service server client host worker engine manager handler controller adapter bridge model models domain domains config configuration utils util helper helpers actions action background extension frontend backend internal external thing opaque unit logic swift js ts m json md system application example validate validated payload command connection'.split(' '));
const rules=[['datastore',/postgres|mysql|sqlite|mongodb|database|redis|file\s*system|파일\s*시스템|데이터베이스|저장소|디렉터리/i],['channel',/rabbitmq|kafka|message\s*queue|\bqueue\b|메시지\s*큐|메시지\s*버스/i],['device',/indigohid|\bhid\b|simctl|hardware|센서|하드웨어|드라이버/i],['application',/appkit|swiftui|uikit|react|chrome\s*extension|사용자\s*화면|웹\s*앱/i],['service',/\bhttp\b|\brest\b|\bgrpc\b|json-rpc|\bmcp\b|stdio|native.host|\bapi\b/i]];
function classifyType(e){if(e.kind==='person')return ['actor','inferred','C4 kind: person'];if(e.external)return ['external','inferred','C4 external=true'];if(e.kind==='code')return [{interface:'contract',protocol:'contract',function:'function',method:'function',table:'datastore'}[e.codeType]||'structure','inferred','Declared codeType: '+e.codeType];
 const tech=String(e.technology||''),name=e.name+' '+(e.roleLabel||''),description=e.description||'',scores=rules.map(([type,re])=>({type,score:re.test(tech)?5:re.test(name)?3:re.test(description)?1:0})).filter(x=>x.score>=3).sort((a,b)=>b.score-a.score);
 if(scores.length&&(!scores[1]||scores[0].score>scores[1].score))return [scores[0].type,'inferred',scores[0].score===5?'Technology hint: '+tech:'Name/role hint: '+name];
 return ['unknown','fallback',scores.length?'Conflicting type hints; no type selected':'No strong type hint in model metadata'];
}
function classifyRole(e,type){const text=e.name+' '+(e.roleLabel||'');if(/validat|검증/i.test(text))return ['validation','inferred','Name/role indicates validation'];if(/bridge|브리지|중계/i.test(text))return ['bridge','inferred','Name/role indicates a bridge'];const mapped={datastore:'storage',channel:'messaging',device:'device',application:'ui',service:'api'}[type];if(mapped)return [mapped,'inferred','Role hint from classified type: '+type];if(/engine|worker|executor|compute|실행\s*조정|계산/i.test(text))return ['compute','inferred','Name/role indicates execution or computation'];return ['unknown','fallback','No strong role hint; retain C4/code icon fallback'];}
export function classifyModel(input){
 const m=structuredClone(input),es=new Map(m.elements.map(e=>[e.id,e])),domains=new Map((m.domains||[]).map(d=>[d.id,{...d,hue:d.hue??hash(d.id)%360}]));
 const project=[...words(m.title),words(m.title).join(''),...m.elements.filter(e=>e.kind==='system'&&!e.external).flatMap(e=>[...words(e.name),words(e.name).join('')])],ignored=w=>generic.has(w)||project.some(p=>p.length>2&&(w===p||w===p+'core'))||w.length<3;
 function token(text){return words(text).find(w=>!ignored(w));}
 function domainHint(e){
  const candidates=new Map();let covered=0;for(const source of e.sources||[]){const parts=source.path.split('/'),directory=parts.slice(0,-1).reverse().map(token).find(Boolean),file=token(parts.at(-1).replace(/\.[^.]+$/,''));const candidate=directory||file;if(candidate){covered++;candidates.set(candidate,source.path);}}
  if(candidates.size===1&&covered===(e.sources||[]).length){const [value,path]=[...candidates][0];return {value,reason:'Source path hint (not source-content proof): '+path};}
  if(candidates.size>0)return {ambiguous:true,reason:'Multiple source-domain candidates; retained neutral/inherited domain'};
  // CamelCase or natural-language project terms are hints, never a source-backed assertion.
  const value=token(e.name);return value?{value,reason:'Name hint (not source-content proof): '+e.name}:null;
 }
 function register(value){const existing=[...domains.values()].find(d=>d.id===value||d.label.toLowerCase()===value.toLowerCase());if(existing)return existing.id;const slug=value.replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,38),id='domain-'+(slug||'term')+'-'+hash(value).toString(36);if(!domains.has(id))domains.set(id,{id,label:value.slice(0,64),hue:hash(id)%360});return id;}
 const active=new Set();function resolve(e){if(e._resolved)return;if(active.has(e.id))return;active.add(e.id);const parent=es.get(e.parent);if(parent)resolve(parent);
  const s=e.semantic||{};s.basis={...s.basis};s.reasons={...s.reasons};
  const put=(key,value,basis,reason)=>{if(s[key]!==undefined){s.basis[key]??='declared';s.reasons[key]??='Provided in model';}else{s[key]=value;s.basis[key]=basis;s.reasons[key]=reason.slice(0,300);}};
  const hint=e.kind==='person'||e.external?null:domainHint(e);
  if(e.kind==='code'&&parent?.semantic?.domain)put('domain',parent.semantic.domain,'inherited','Code belongs to component: '+parent.id);
  else if(hint?.value)put('domain',s.domain??register(hint.value),'inferred',hint.reason);
  else if(parent?.semantic?.domain&&parent.semantic.domain!=='unclassified')put('domain',parent.semantic.domain,'inherited','Parent domain: '+parent.id);
  else put('domain','unclassified','fallback',hint?.reason||'No reliable project-domain hint');
  put('type',...classifyType(e));put('role',...classifyRole(e,s.type));e.semantic=s;e._resolved=true;active.delete(e.id);
 }
 for(const e of [...m.elements].sort((a,b)=>a.id.localeCompare(b.id)))resolve(e);
 // A single consistent adjacent domain is a weak fallback; never override an own or inherited hint.
 const initial=new Map(m.elements.map(e=>[e.id,e.semantic.domain]));for(const e of m.elements){const s=e.semantic;if(s.domain!=='unclassified'||s.basis.domain!=='fallback'||!['container','component'].includes(e.kind))continue;const connected=m.relationships.filter(r=>r.source===e.id||r.target===e.id).map(r=>r.source===e.id?r.target:r.source),hints=new Set(connected.map(id=>initial.get(id)).filter(id=>id&&id!=='unclassified'));if(hints.size===1&&connected.length&&connected.every(id=>initial.get(id)!=='unclassified')){s.domain=[...hints][0];s.basis.domain='inferred';s.reasons.domain='All directly connected nodes share one domain; relationship hint only';}}
 for(const e of m.elements)if(e.kind==='code'&&e.semantic.basis.domain==='inherited')e.semantic.domain=es.get(e.parent).semantic.domain;
 if(m.elements.some(e=>e.semantic.domain==='unclassified')&&!domains.has('unclassified'))domains.set('unclassified',{id:'unclassified',label:m.locale==='ko'?'미분류':'Unclassified',hue:0});
 for(const e of m.elements)delete e._resolved;m.domains=[...domains.values()].sort((a,b)=>a.id.localeCompare(b.id));return m;
}
