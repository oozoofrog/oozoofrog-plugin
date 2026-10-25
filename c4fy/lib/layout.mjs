// Original rectilinear router. Explicit view cells preserve author intent.
const W=244,H=158,DX=360,DY=240,M=66;
const eq=(a,b)=>a[0]===b[0]&&a[1]===b[1];
const length=p=>p.slice(1).reduce((s,b,i)=>s+Math.abs(p[i][0]-b[0])+Math.abs(p[i][1]-b[1]),0);
function simplify(p){p=p.filter((v,i)=>!i||!eq(v,p[i-1]));return p.filter((v,i)=>!i||i===p.length-1||!((p[i-1][0]===v[0]&&v[0]===p[i+1][0])||(p[i-1][1]===v[1]&&v[1]===p[i+1][1])));}
export function segmentHitsRect(a,b,r,pad=0){const l=r.x-pad,t=r.y-pad,rr=r.x+r.width+pad,bb=r.y+r.height+pad;
 if(a[0]===b[0])return a[0]>l&&a[0]<rr&&Math.max(a[1],b[1])>t&&Math.min(a[1],b[1])<bb;
 if(a[1]===b[1])return a[1]>t&&a[1]<bb&&Math.max(a[0],b[0])>l&&Math.min(a[0],b[0])<rr;
 return true;}
function segmentConflict(a,b,c,d){
 if(a[0]===b[0]&&c[0]===d[0])return a[0]===c[0]&&Math.min(Math.max(a[1],b[1]),Math.max(c[1],d[1]))>Math.max(Math.min(a[1],b[1]),Math.min(c[1],d[1]))?4:0;
 if(a[1]===b[1]&&c[1]===d[1])return a[1]===c[1]&&Math.min(Math.max(a[0],b[0]),Math.max(c[0],d[0]))>Math.max(Math.min(a[0],b[0]),Math.min(c[0],d[0]))?4:0;
 const [v1,v2,h1,h2]=a[0]===b[0]?[a,b,c,d]:[c,d,a,b];
 return v1[0]>Math.min(h1[0],h2[0])&&v1[0]<Math.max(h1[0],h2[0])&&h1[1]>Math.min(v1[1],v2[1])&&h1[1]<Math.max(v1[1],v2[1])?1:0;
}
const overlap=(a,b)=>a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y;
function ports(n){return [0,-28,28].flatMap(offset=>[[n.x,n.y+H/2+offset,-1,0],[n.x+W,n.y+H/2+offset,1,0],[n.x+W/2+offset,n.y,0,-1],[n.x+W/2+offset,n.y+H,0,1]]);}
function route(a,b,nodes,existing){
 const xs=[24,...new Set(nodes.flatMap(n=>[n.x-30,n.x+W+30]))],ys=[24,...new Set(nodes.flatMap(n=>[n.y-30,n.y+H+30]))];let best,bestScore=Infinity;
 for(const s of ports(a))for(const t of ports(b)){
 const sp=[s[0]+s[2]*24,s[1]+s[3]*24],tp=[t[0]+t[2]*24,t[1]+t[3]*24];
 const inner=[[sp,tp],[sp,[tp[0],sp[1]],tp],[sp,[sp[0],tp[1]],tp]];
 for(const x of [...xs,(sp[0]+tp[0])/2])inner.push([sp,[x,sp[1]],[x,tp[1]],tp]);
 for(const y of [...ys,(sp[1]+tp[1])/2])inner.push([sp,[sp[0],y],[tp[0],y],tp]);
 for(const mid of inner){const p=simplify([[s[0],s[1]],...mid,[t[0],t[1]]]);if(p.some((v,i)=>i&&v[0]!==p[i-1][0]&&v[1]!==p[i-1][1]))continue;
 if(p.slice(1).some((v,i)=>nodes.some(n=>segmentHitsRect(p[i],v,n,0))))continue;
 // Require the departure/arrival direction selected by each port.
 if((p[1][0]-s[0])*s[2]+(p[1][1]-s[1])*s[3]<=0)continue;
 const before=p.at(-2);if((before[0]-t[0])*t[2]+(before[1]-t[1])*t[3]<=0)continue;
 let conflicts=0;for(let i=1;i<p.length;i++)for(const e of existing)for(let j=1;j<e.points.length;j++)conflicts+=segmentConflict(p[i-1],p[i],e.points[j-1],e.points[j]);
 const score=length(p)+28*(p.length-2)+conflicts*800;if(score<bestScore){best=p;bestScore=score;}
 }}
 if(!best)throw new Error(`No unobstructed route: ${a.id} -> ${b.id}; move the connected nodes`);return best;
}
function defaultCells(model,view){const map=new Map(), used=new Set(Object.values(view.positions||{}).map(p=>p.join(',')));let next=0;for(const id of view.nodes){if(Object.hasOwn(view.positions||{},id)){map.set(id,view.positions[id]);continue;}while(used.has(`${next%3},${Math.floor(next/3)}`))next++;const p=[next%3,Math.floor(next/3)];map.set(id,p);used.add(p.join(','));next++;}return map;}
export function layoutView(model,view){
 const cells=defaultCells(model,view), seen=new Set(), nodes=view.nodes.map(id=>{const [col,row]=cells.get(id);const key=`${col},${row}`;if(seen.has(key))throw new Error('Duplicate position');seen.add(key);return {id,x:M+col*DX,y:M+row*DY,width:W,height:H};});
 const byID=new Map(nodes.map(n=>[n.id,n]));const edges=[];
 for(const id of view.relationships){const r=model.relationships.find(x=>x.id===id);if(!r)throw new Error(`Unknown relationship ${id}`);edges.push({id,points:route(byID.get(r.source),byID.get(r.target),nodes,edges)});}
 const labels=[];for(let index=0;index<edges.length;index++){
 const edge=edges[index], rel=model.relationships.find(r=>r.id===edge.id),text=rel.description;
 const measured=[...text].reduce((s,c)=>s+(c.codePointAt(0)>255?11.5:/[MW@%#&]/.test(c)?10:7.5),0), desired=Math.max(54,measured+24);let label;
 for(const width of (desired<=210?[desired,30]:[30])){if(label)break;for(let i=1;i<edge.points.length;i++){const a=edge.points[i-1],b=edge.points[i];const horizontal=a[1]===b[1],dist=Math.abs(a[0]-b[0])+Math.abs(a[1]-b[1]);if(dist<(horizontal?width+16:52))continue;
 for(const f of [.5,.35,.65]){const x=a[0]+(b[0]-a[0])*f,y=a[1]+(b[1]-a[1])*f;const box={x:x-width/2,y:y-13,width,height:26};if(nodes.some(n=>overlap({...n,x:n.x-8,y:n.y-8,width:n.width+16,height:n.height+16},box))||labels.some(l=>overlap(l,box)))continue;
 if(edges.some(e=>e!==edge&&e.points.slice(1).some((p,j)=>segmentHitsRect(e.points[j],p,box,4))))continue;
 label={...box,text:width===30?String(index+1):text,compact:width===30};break;}if(label)break;}}
 if(!label)throw new Error(`No clear relationship label: ${edge.id}; increase cell spacing or change node positions`);edge.label=label;labels.push(label);
 }
 const inner=nodes.filter(n=>model.elements.find(e=>e.id===n.id)?.parent===view.scope);let boundary=null;
 if(view.level>1&&inner.length){const x=Math.min(...inner.map(n=>n.x))-22,y=Math.min(...inner.map(n=>n.y))-42;boundary={id:view.scope,x,y,width:Math.max(...inner.map(n=>n.x+W))-x+22,height:Math.max(...inner.map(n=>n.y+H))-y+22};for(const n of nodes.filter(n=>!inner.includes(n)))if(overlap(boundary,n))throw new Error(`Scope boundary includes supporting node ${n.id}; group children in a rectangular area`);}
 const width=Math.max(...nodes.map(n=>n.x+W),...edges.flatMap(e=>e.points.map(p=>p[0])),boundary?boundary.x+boundary.width:0)+M;
 const height=Math.max(...nodes.map(n=>n.y+H),...edges.flatMap(e=>e.points.map(p=>p[1])),boundary?boundary.y+boundary.height:0)+M;
 let crossings=0,sharedCorridors=0;for(let i=0;i<edges.length;i++)for(let j=i+1;j<edges.length;j++)for(let a=1;a<edges[i].points.length;a++)for(let b=1;b<edges[j].points.length;b++){const c=segmentConflict(edges[i].points[a-1],edges[i].points[a],edges[j].points[b-1],edges[j].points[b]);if(c===1)crossings++;if(c===4)sharedCorridors++;}
 return {id:view.id,nodes,edges,boundary,width,height,diagnostics:{crossings,sharedCorridors,compactLabels:edges.filter(e=>e.label.compact).length}};
}
