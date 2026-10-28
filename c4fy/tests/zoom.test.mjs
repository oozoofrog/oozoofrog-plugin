import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Execute the shipped transform and button handlers without a browser layout engine.
const source=readFileSync(new URL('../assets/viewer.js',import.meta.url),'utf8');
function viewer(width,height,layout){
 const buttons=new Map(['#zoom-in','#zoom-out','#fit'].map(id=>[id,{}]));
 const context=vm.createContext({stage:{clientWidth:width,clientHeight:height,scrollTo(){}},
   currentLayout:layout,zoom:1,cancelMotion(){},resize(){},$:id=>buttons.get(id)});
 vm.runInContext(source.slice(source.indexOf('function transformFor('),source.indexOf('function resize(')),context);
 vm.runInContext(source.split('\n').find(line=>line.startsWith("$('#zoom-in').onclick=")),context);
 return {click:id=>buttons.get(id).onclick(),scale:()=>vm.runInContext('transformFor(currentLayout).s',context)};
}
test('large diagram on narrow stage can zoom to readable 1:1 scale',()=>{
 const v=viewer(370,300,{width:2800,height:2200});
 for(let n=0;n<40;n++)v.click('#zoom-in');
 assert.ok(v.scale()>=1,`maximum scale ${v.scale()} cannot render normal-sized text`);
 assert.ok(v.scale()<=4,'zoom remains bounded');
 v.click('#fit');assert.ok(v.scale()<.2,'fit restores overview');
});
test('zoom buttons retain bounded, reversible behavior on small diagrams',()=>{
 const v=viewer(1000,700,{width:500,height:400});
 const initial=v.scale();v.click('#zoom-in');assert.ok(v.scale()>initial);
 v.click('#zoom-out');assert.ok(Math.abs(v.scale()-initial)<1e-9);
 for(let n=0;n<100;n++)v.click('#zoom-out');assert.ok(v.scale()>0);
 v.click('#fit');assert.equal(v.scale(),initial);
});
