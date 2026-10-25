// Smooth only corner neighborhoods of the validated route; retain endpoints and corridors.
window.c4fyThemePoints=(points,design=document.documentElement.dataset.design)=>{
 const radius={nouveau:24,ive:18,material:20,liquid:26}[design];if(!radius||points.length<3)return points;
 const result=[points[0]];
 for(let i=1;i<points.length-1;i++){
  const a=points[i-1],b=points[i],c=points[i+1],before=Math.hypot(b[0]-a[0],b[1]-a[1]),after=Math.hypot(c[0]-b[0],c[1]-b[1]);
  if(!before||!after){result.push(b);continue;}
  const r=Math.min(radius,before*.45,after*.45),start=[b[0]+(a[0]-b[0])*r/before,b[1]+(a[1]-b[1])*r/before],end=[b[0]+(c[0]-b[0])*r/after,b[1]+(c[1]-b[1])*r/after];result.push(start);
  for(let n=1;n<=12;n++){const t=n/12,q=1-t;result.push([q*q*start[0]+2*q*t*b[0]+t*t*end[0],q*q*start[1]+2*q*t*b[1]+t*t*end[1]]);}
 }
 result.push(points.at(-1));return result;
};
