(()=>{'use strict';
const root=document.documentElement,stage=document.querySelector('#stage'),reduced=matchMedia('(prefers-reduced-motion: reduce)'),NS='http://www.w3.org/2000/svg';
const make=(tag,attrs={})=>{const e=document.createElementNS(NS,tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,v);return e;};
let frame=0,layer=null,rows=[],started=0;
function stop(){cancelAnimationFrame(frame);frame=0;layer?.remove();layer=null;rows=[];}
function start(){stop();const design=root.dataset.design||'default';if(design==='default'||reduced.matches||document.hidden)return;
 const scene=stage.querySelector('.scene:not(.old)'),svg=scene?.querySelector(':scope > svg');if(!svg)return;
 const paths=[...svg.querySelectorAll('.flow-trace.active:not(.dim):not(.flow-dim)')];if(!paths.length)return;
 layer=make('g',{class:'theme-circuit','data-effect':design,'aria-hidden':'true'});svg.append(layer);
 for(const [index,path]of paths.entries()){
  const group=make('g',{'data-relation':path.dataset.id}),trail=make('polyline',{points:path.getAttribute('points'),class:'circuit-trail'}),particle=make('g',{class:'circuit-particle'}),halo=make('circle',{class:'circuit-halo',r:0,opacity:0});group.append(trail,particle,halo);layer.append(group);
  if(design==='cyber'){for(let j=0;j<30;j++)particle.append(make('line',{'data-spark':j,'stroke-width':j%3===0?2.2:1.5,'stroke-linecap':'round',opacity:0}));}
  else if(design==='nouveau'){for(let j=0;j<5;j++)particle.append(make('path',{'data-wave':j,fill:'none','stroke-width':j===2?1.2:.7,opacity:j===2?.7:.32}));}
  else if(design==='bauhaus')particle.append(index%2?make('path',{d:'M-6 -6L7 0L-6 6Z'}):make('rect',{x:-5,y:-5,width:10,height:10}));
  else if(design==='rams')particle.append(make('rect',{x:-3,y:-2,width:6,height:4}));
  else if(design==='ive')particle.append(make('circle',{r:2.5}));
  else if(design==='material')particle.append(make('circle',{r:6}));
  else if(design==='liquid'){particle.append(make('path',{d:'M-13 0C-7 -1 -4 -7 2 -7C12 -7 12 7 2 7C-4 7 -7 1 -13 0Z'}),make('ellipse',{cx:4,cy:-2,rx:2.5,ry:1.4,class:'drop-highlight'}),make('circle',{'data-satellite':'',cx:-18,cy:1,r:2.4,opacity:.5}));}
  const length=path.getTotalLength();if(length>0)rows.push({path,group,trail,particle,halo,length,index});
 }
 started=performance.now();
 function tick(now){if(!layer?.isConnected||reduced.matches||document.hidden){stop();return;}
  const seconds=(now-started)/1000,cycle=seconds%3.2;
  for(const r of rows){const delay=(r.index%3)*.12,u=Math.max(0,Math.min(1,(cycle-delay)/2.016)),visible=cycle>delay&&u<1;let p=u;
   if(design==='bauhaus')p=Math.floor(u*14)/14;else if(['nouveau','ive','material','liquid'].includes(design))p=u*u*(3-2*u);
   const distance=p*r.length,pos=r.path.getPointAtLength(distance),a=r.path.getPointAtLength(Math.max(0,distance-1)),b=r.path.getPointAtLength(Math.min(r.length,distance+1)),angle=Math.atan2(b.y-a.y,b.x-a.x)*180/Math.PI;
   r.particle.setAttribute('opacity',visible?'1':'0');r.particle.setAttribute('transform',`translate(${pos.x} ${pos.y}) rotate(${angle})`);
   if(design==='cyber'){
    r.particle.setAttribute('transform','translate(0 0)');for(const [j,spark]of [...r.particle.children].entries()){const birth=.1+Math.floor(j/3)*.185,age=cycle-delay-birth,life=.2+(j%3)*.035;if(age<0||age>life){spark.setAttribute('opacity','0');continue;}
     const anchor=r.path.getPointAtLength(birth/2.016*r.length),theta=j*2.399+r.index*.8,speed=54+(j%4)*20.25,vx=Math.cos(theta)*speed,vy=Math.sin(theta)*speed-12,k=4.5,g=100;
     const at=t=>{const d=(1-Math.exp(-k*t))/k;return {x:anchor.x+vx*d,y:anchor.y+(vy-g/k)*d+g*t/k};};const head=at(age),tail=at(Math.max(0,age-.05));for(const [key,value]of Object.entries({x1:tail.x,y1:tail.y,x2:head.x,y2:head.y,opacity:.8*Math.pow(1-age/life,1.3)}))spark.setAttribute(key,value);
    }
   }
   if(design==='nouveau'){
    r.particle.setAttribute('transform','translate(0 0)');for(const [j,wave]of [...r.particle.children].entries()){const points=[],amp=(2+j*.65)*Math.sin(Math.PI*u);for(let n=0;n<=64;n++){const q=n/64,l=q*r.length,c=r.path.getPointAtLength(l),before=r.path.getPointAtLength(Math.max(0,l-1)),after=r.path.getPointAtLength(Math.min(r.length,l+1)),dx=after.x-before.x,dy=after.y-before.y,norm=Math.hypot(dx,dy)||1,offset=amp*Math.sin(Math.PI*q)*(Math.sin(q*Math.PI*(3+j*.7)-seconds*(2+j*.55)+j)+.35*Math.sin(q*Math.PI*(7+j)-seconds*1.3));points.push(`${n?'L':'M'}${c.x-dy/norm*offset} ${c.y+dx/norm*offset}`);}wave.setAttribute('d',points.join(' '));}
   }
   if(design==='liquid'){const stretch=Math.sin(u*Math.PI*2);r.particle.setAttribute('transform',`translate(${pos.x} ${pos.y}) rotate(${angle}) scale(${1+.25*stretch} ${1-.15*stretch})`);const satellite=r.particle.querySelector('[data-satellite]');satellite.setAttribute('cx',-18-5*Math.sin(u*Math.PI));satellite.setAttribute('r',1.5+1.2*Math.sin(u*Math.PI));}
   const tail={cyber:2,nouveau:0,bauhaus:10,rams:5,ive:36,material:18,liquid:12}[design]||0;r.trail.setAttribute('stroke-dasharray',`${tail} ${r.length+tail}`);r.trail.setAttribute('stroke-dashoffset',tail-distance);r.trail.setAttribute('opacity',visible?(design==='cyber'?.25:design==='nouveau'?0:design==='liquid'?.25:1):0);
   const arrival=(cycle-delay-2.016)/.45,end=r.path.getPointAtLength(r.length);r.halo.setAttribute('cx',end.x);r.halo.setAttribute('cy',end.y);r.halo.setAttribute('r',3+Math.max(0,arrival)*14);r.halo.setAttribute('opacity',['material','liquid'].includes(design)&&arrival>0&&arrival<1?1-arrival:0);
  }frame=requestAnimationFrame(tick);
 }frame=requestAnimationFrame(tick);
}
document.addEventListener('c4fy-flow-change',start);document.addEventListener('c4fy-view-changing',stop);new MutationObserver(start).observe(root,{attributes:true,attributeFilter:['data-design','data-theme']});reduced.addEventListener('change',start);document.addEventListener('visibilitychange',start);window.addEventListener('pagehide',stop);start();
})();
