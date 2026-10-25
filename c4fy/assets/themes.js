(()=>{'use strict';
const root=document.documentElement,ko=root.lang==='ko',themes=[
 ['default','기본','Default',21,'ui-rounded,-apple-system,sans-serif',['#fbf8f3','#fffefa','#332f42','#706b80','#e5dfe9','#7456ad','#f0e8fc'],['#211e2a','#2b2736','#f4edf9','#bdb2ca','#4c435a','#d0b1ff','#443254']],
 ['cyber','사이버펑크','Cyberpunk',3,'ui-monospace,monospace',['#11121b','#171b28','#eafafb','#a0bdc9','#334953','#64f9e2','#143b3b'],['#11121b','#171b28','#eafafb','#a0bdc9','#334953','#64f9e2','#143b3b']],
 ['nouveau','아르누보','Art Nouveau',28,'Georgia,serif',['#eee9d8','#f8f3e6','#28443a','#596a51','#afa77d','#466d4e','#e0e8d0'],['#202b23','#29362b','#f0ead6','#c0c6aa','#5c6951','#c2cc8b','#384936']],
 ['bauhaus','바우하우스','Bauhaus',0,'Arial,sans-serif',['#f1eddf','#fffdf4','#18252e','#535751','#b9b5a8','#af3026','#f7e0d4'],['#21272d','#29323a','#fbf5e5','#c8c6bc','#64707a','#ff9b83','#4c3030']],
 ['rams','기능주의','Functionalism',5,'Arial,sans-serif',['#e7e6e1','#f4f3ed','#30332f','#65685f','#bcbfb4','#39734f','#e1e8dc'],['#252824','#30342e','#edf0e6','#bac2b2','#606956','#acd29d','#3c4c35']],
 ['ive','미니멀리즘','Minimalism',20,'-apple-system,BlinkMacSystemFont,sans-serif',['#f5f6f7','#ffffff','#20242a','#68717c','#e0e4e8','#2465af','#ecf4fd'],['#1d2024','#282d33','#f3f6fa','#b6c0cd','#4c5663','#a3ceff','#30445c']],
 ['material','매터리얼','Material',25,'-apple-system,sans-serif',['#f7f1fa','#eae0ef','#271e30','#665a70','#c6b8d0','#6e4689','#dfc7f1'],['#241d2b','#342b3d','#f2e7fa','#c5b6cf','#685675','#dbb4f4','#513c63']],
 ['liquid','리퀴드','Liquid',30,'-apple-system,sans-serif',['#e9f0f7','#f4f8fc','#263a50','#586e85','#c7d5e4','#386caa','#e0eefd'],['#1d2834','#293b4d','#edf6ff','#b4ccdf','#526e89','#afd5ff','#355775']]
];
const keys=['bg','surface','ink','muted','line','accent','soft'],extra=['person','system','container','component','code','external','edge','focus','shadow','design-radius','design-font'];
const trigger=document.createElement('button');trigger.id='design-picker';trigger.textContent=ko?'테마':'Themes';trigger.setAttribute('aria-haspopup','dialog');trigger.setAttribute('aria-controls','design-popover');trigger.setAttribute('aria-expanded','false');document.querySelector('.toolbar').prepend(trigger);
const panel=document.createElement('section');panel.id='design-popover';panel.setAttribute('popover','auto');panel.setAttribute('role','dialog');panel.setAttribute('aria-label',ko?'테마 선택':'Choose theme');
const heading=document.createElement('div');heading.className='design-heading';const title=document.createElement('strong');title.textContent=ko?'테마':'Themes';const close=document.createElement('button');close.textContent=ko?'닫기':'Close';close.onclick=()=>{panel.hidePopover();trigger.focus();};heading.append(title,close);panel.append(heading);
const grid=document.createElement('div');grid.className='design-grid';panel.append(grid);document.body.append(panel);
let selected='default';try{const saved=localStorage.getItem('c4fy-design');if(themes.some(t=>t[0]===saved))selected=saved;}catch{}
function palette(t){return t[root.dataset.theme==='dark'?6:5];}
function colorize(el,t){const colors=palette(t);keys.forEach((key,i)=>{if(colors)el.style.setProperty('--'+key,colors[i]);else el.style.removeProperty('--'+key);});}
function apply(save=false){const theme=themes.find(t=>t[0]===selected);root.dataset.design=selected;[...keys,...extra].forEach(k=>root.style.removeProperty('--'+k));colorize(root,theme);
 if(theme[0]!=='default'){for(const key of ['person','system','container','component','code','external'])root.style.setProperty('--'+key,palette(theme)[6]);root.style.setProperty('--edge',palette(theme)[5]);root.style.setProperty('--focus',palette(theme)[5]);root.style.setProperty('--design-font',theme[4]);root.style.setProperty('--shadow','0 5px 20px #0000000c');}root.style.setProperty('--design-radius',theme[3]+'px');
 for(const t of themes){const b=grid.querySelector('[data-design="'+t[0]+'"]');colorize(b,t);b.setAttribute('aria-pressed',String(t[0]===selected));b.querySelector('.design-check').textContent=t[0]===selected?'✓':'';}
 document.querySelectorAll('.scene .edge[data-route],.scene .flow-trace[data-route]').forEach(line=>line.setAttribute('points',window.c4fyThemePoints(JSON.parse(line.dataset.route)).map(p=>p.join(',')).join(' ')));
 trigger.setAttribute('aria-label',(ko?'테마: ':'Theme: ')+theme[ko?1:2]);if(save){try{localStorage.setItem('c4fy-design',selected);}catch{}document.querySelector('#status').textContent=(ko?'테마 적용: ':'Theme applied: ')+theme[ko?1:2];}}
for(const t of themes){const b=document.createElement('button');b.className='design-choice';b.dataset.design=t[0];b.style.setProperty('--preview-radius',Math.min(t[3],14)+'px');b.style.fontFamily=t[4];b.innerHTML='<span class="design-preview" aria-hidden="true"><span class="preview-node">A</span><span class="preview-wire">→</span><span class="preview-node">B</span></span><span class="design-label"></span><span class="design-check" aria-hidden="true"></span>';b.querySelector('.design-label').textContent=t[ko?1:2];b.onclick=()=>{selected=t[0];apply(true);};grid.append(b);}
function place(){const r=trigger.getBoundingClientRect(),w=Math.min(360,innerWidth-20);panel.style.width=w+'px';panel.style.left=Math.max(10,Math.min(innerWidth-w-10,r.right-w))+'px';panel.style.top=Math.min(r.bottom+8,Math.max(10,innerHeight-180))+'px';panel.style.maxHeight=Math.max(100,innerHeight-r.bottom-18)+'px';}
trigger.onclick=()=>{if(panel.matches(':popover-open'))panel.hidePopover();else{place();panel.showPopover();grid.querySelector('[aria-pressed=true]').focus({preventScroll:true});}};
panel.addEventListener('toggle',e=>trigger.setAttribute('aria-expanded',String(e.newState==='open')));window.addEventListener('resize',()=>{if(panel.matches(':popover-open'))place();});
new MutationObserver(()=>apply()).observe(root,{attributes:true,attributeFilter:['data-theme']});apply();
})();
