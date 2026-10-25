import test from 'node:test';
import assert from 'node:assert/strict';
import {validateModel} from '../lib/model.mjs';
import {layoutView} from '../lib/layout.mjs';
import {renderHTML} from '../lib/render.mjs';
export function fixture(){return {version:1,title:'Tea app',locale:'en',elements:[
{id:'person',kind:'person',name:'Reader',description:'Reads notes'},
{id:'system',kind:'system',name:'Notes',description:'Stores notes'},
{id:'app',kind:'container',parent:'system',name:'Desktop app',description:'Edits notes',technology:'Swift'},
{id:'core',kind:'component',parent:'app',name:'Editor',description:'Updates notes',technology:'Swift'}],relationships:[
{id:'uses',source:'person',target:'system',description:'Reads notes'},
{id:'opens',source:'person',target:'app',description:'Opens',technology:'UI'},
{id:'edits',source:'person',target:'core',description:'Edits',technology:'UI'}],views:[
{id:'context',level:1,scope:'system',title:'Context',nodes:['person','system'],relationships:['uses']},
{id:'containers',level:2,scope:'system',title:'Containers',nodes:['person','app'],relationships:['opens']},
{id:'components',level:3,scope:'app',title:'Components',nodes:['person','core'],relationships:['edits']} ]};}
test('accepts linked C1 C2 C3 model',()=>assert.deepEqual(validateModel(fixture()),[]));
test('rejects parent level mismatch and dangling relationships',()=>{const m=fixture();m.elements[3].parent='system';m.relationships[0].target='missing';assert.ok(validateModel(m).length>=2);});
test('rejects mixed levels and hidden relationship endpoints',()=>{const m=fixture();m.views[0].nodes.push('core');m.views[1].relationships.push('uses');assert.ok(validateModel(m).length>=2);});
test('rejects duplicate ids, unsafe source paths and invalid ranges',()=>{const m=fixture();m.elements.push({...m.elements[0]});m.elements[0].sources=[{path:'../secret',line:0,endLine:4}];assert.ok(validateModel(m).length>=2);});
test('rejects unowned components, cycles and unrelated containers in C3',()=>{const m=fixture();m.elements[2].parent='core';m.views[2].nodes.push('app');assert.ok(validateModel(m).length>=2);});
test('layout avoids opaque node interiors and duplicate positions',()=>{const m=fixture(), v=m.views[0];const l=layoutView(m,v);assert.equal(l.nodes.length,2);assert.equal(l.edges.length,1);assert.ok(l.width>0&&l.height>0);v.positions={person:[0,0],system:[0,0]};assert.throws(()=>layoutView(m,v),/position|overlap/);});
test('HTML is self contained and escapes script-closing input',()=>{const m=fixture();m.title='</script><script>alert(1)</script>';m.elements[0].name='<img src=x onerror=alert(1)>';const html=renderHTML(m);assert.ok(!html.includes('</script><script>alert(1)'));assert.ok(!html.includes('<img src=x'));assert.ok(html.includes('prefers-reduced-motion'));assert.ok(!/<script[^>]+src=/.test(html));});
test('rejects IDs which only become valid after string coercion',()=>{for(const collection of ['elements','views','relationships']){const m=fixture();m[collection][0].id=[m[collection][0].id];assert.ok(validateModel(m).length>0,collection);}});
test('rejects XML-invalid characters and lone surrogates',()=>{for(const value of ['hi\u0001','hi\uFFFF','hi\uD800']){const m=fixture();m.title=value;assert.ok(validateModel(m).length>0);}const m=fixture();m.title='Hello 🌿';assert.deepEqual(validateModel(m),[]);});
test('long relationship labels use compact key rather than overflow',()=>{const m=fixture();m.relationships[0].description='W'.repeat(150);m.views[0].positions={person:[0,0],system:[0,1]};const l=layoutView(m,m.views[0]);assert.equal(l.edges[0].label.compact,true);assert.equal(l.edges[0].label.text,'1');});
test('prototype-like stable IDs do not acquire inherited positions',()=>{const m=fixture();m.elements[0].id='constructor';for(const r of m.relationships)r.source='constructor';for(const v of m.views){v.nodes[0]='constructor';v.positions={};}assert.deepEqual(validateModel(m),[]);assert.doesNotThrow(()=>layoutView(m,m.views[0]));});
test('project role labels and generic icons are optional and validated',()=>{const m=fixture();m.elements[1].roleLabel='검색 <API>';m.elements[1].icon='server';assert.deepEqual(validateModel(m),[]);for(const value of ['unknown','__proto__','<svg/>',3]){m.elements[1].icon=value;assert.ok(validateModel(m).length>0);}delete m.elements[1].icon;for(const value of ['',false,'x'.repeat(49)]){m.elements[1].roleLabel=value;assert.ok(validateModel(m).length);}delete m.elements[1].roleLabel;assert.deepEqual(validateModel(m),[]);});
