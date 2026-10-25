(()=>{'use strict';
const typeKO={actor:'사용자',external:'외부 시스템',application:'애플리케이션',service:'서비스',datastore:'저장소',channel:'메시지 채널',device:'장치',contract:'계약',function:'함수',structure:'자료 구조',unknown:'미분류'};
const roleKO={api:'API',storage:'저장',bridge:'중계',validation:'검증',ui:'화면',device:'장치 제어',messaging:'메시징',compute:'실행·계산',unknown:'미분류'};
const roleIcons={api:'server',storage:'database',bridge:'bridge',validation:'validation',ui:'app',device:'device',messaging:'queue',compute:'component'};
window.c4fySemantic={
 label:(axis,value,ko)=>ko?(axis==='type'?typeKO:roleKO)[value]||value:value,
 icon:e=>e.icon||roleIcons[e.semantic?.role]||e.kind,
 radius:(type,base)=>({actor:36,datastore:24,channel:4,contract:4,function:4,structure:4,device:12,application:12}[type]??base),
 // Keep marks in the padding: text starts 15px below the top and ends 7px above the bottom.
 marks:(type,w,h)=>({datastore:`M24 4 Q${w/2} 10 ${w-24} 4 M24 ${h-3} Q${w/2} ${h-7} ${w-24} ${h-3}`,channel:`M8 1 V${h-1} M${w-8} 1 V${h-1}`,application:`M1 7 H${w-1}`,device:`M${w/2-12} ${h-6} H${w/2+12}`,function:`M5 1 V${h-1}`,structure:`M${w-33} 1 V8 H${w-1}`,contract:`M${w-30} 6 H${w-8} M${w-30} 10 H${w-8}`}[type]||''),
 dashed:type=>['external','contract'].includes(type)
};
})();
