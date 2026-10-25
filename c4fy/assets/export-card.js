// Serialize the live card's visual surface without embedding HTML or external CSS.
(()=>{'use strict';
window.c4fyExportCard=(node,n)=>{
 const c=getComputedStyle(node),esc=s=>String(s).replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
 const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');
 const color=value=>{ctx.clearRect(0,0,1,1);ctx.fillStyle=value;ctx.fillRect(0,0,1,1);const [r,g,b,a]=ctx.getImageData(0,0,1,1).data;return {rgb:`rgb(${r}, ${g}, ${b})`,alpha:a/255};};
 const id='card-'+n.id,r=[c.borderTopLeftRadius,c.borderTopRightRadius,c.borderBottomRightRadius,c.borderBottomLeftRadius].map(x=>Math.min(parseFloat(x)||0,n.width/2,n.height/2));
 const geometry=r.every(x=>x===r[0])?`rect x="0" y="0" width="${n.width}" height="${n.height}" rx="${r[0]}"`:`path d="M${r[0]} 0 H${n.width-r[1]} Q${n.width} 0 ${n.width} ${r[1]} V${n.height-r[2]} Q${n.width} ${n.height} ${n.width-r[2]} ${n.height} H${r[3]} Q0 ${n.height} 0 ${n.height-r[3]} V${r[0]} Q0 0 ${r[0]} 0Z"`;
 let defs='',fill=c.backgroundColor;
 if(c.backgroundImage!=='none'){
  const start=color(c.getPropertyValue('--semantic-fill')),end=color(`color-mix(in srgb,${c.getPropertyValue('--semantic-fill')} 86%,${getComputedStyle(document.documentElement).getPropertyValue('--surface')})`);
  defs+=`<linearGradient id="${id}-gradient" x1="21%" y1="9%" x2="79%" y2="91%"><stop stop-color="${start.rgb}"/><stop offset="1" stop-color="${end.rgb}"/></linearGradient>`;fill=`url(#${id}-gradient)`;
 }
 let shadows='';for(const m of c.boxShadow.matchAll(/(rgba?\([^)]*\)|color\([^)]*\))\s+(-?[\d.]+)px\s+(-?[\d.]+)px\s+([\d.]+)px\s+(-?[\d.]+)px(\s+inset)?/g)){
  const tint=color(m[1]);if(m[6])shadows+=`<feOffset in="SourceAlpha" dx="${m[2]}" dy="${m[3]}" result="offset"/><feGaussianBlur in="offset" stdDeviation="${Number(m[4])/2}" result="blur"/><feComposite in="SourceAlpha" in2="blur" operator="out" result="mask"/><feFlood flood-color="${tint.rgb}" flood-opacity="${tint.alpha}"/><feComposite in2="mask" operator="in" result="inner"/><feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="inner"/></feMerge>`;
  else shadows+=`<feDropShadow dx="${m[2]}" dy="${m[3]}" stdDeviation="${Number(m[4])/2}" flood-color="${tint.rgb}" flood-opacity="${tint.alpha}"/>`;
 }
 if(shadows)defs+=`<filter id="${id}-shadow" x="-30%" y="-30%" width="160%" height="160%" color-interpolation-filters="sRGB">${shadows}</filter>`;
 const stroke=color(c.borderTopColor),width=parseFloat(c.borderTopWidth),dash=c.borderTopStyle==='dashed'?' stroke-dasharray="6 4"':'';
 let face=`<${geometry} fill="${esc(fill)}" stroke="${stroke.rgb}" stroke-opacity="${stroke.alpha}" stroke-width="${width}"${dash}${shadows?` filter="url(#${id}-shadow)"`:''}/>`;
 if(parseFloat(c.borderLeftWidth)>width)face+=`<path d="M${parseFloat(c.borderLeftWidth)/2} ${r[0]} V${n.height-r[3]}" stroke="${stroke.rgb}" stroke-width="${c.borderLeftWidth}" fill="none"/>`;
 if(node.getAttribute('aria-pressed')==='true')face+=`<${geometry} fill="none" stroke="${esc(c.outlineColor)}" stroke-width="${parseFloat(c.outlineWidth)}" transform="translate(-6 -6) scale(${(n.width+12)/n.width} ${(n.height+12)/n.height})"/>`;
 return `<defs>${defs}</defs><g transform="translate(${n.x} ${n.y})">${face}</g>`;
};
})();
