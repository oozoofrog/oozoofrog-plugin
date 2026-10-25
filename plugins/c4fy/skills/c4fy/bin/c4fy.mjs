#!/usr/bin/env node
import {readFileSync,writeFileSync,mkdirSync,renameSync,rmSync,lstatSync,existsSync,mkdtempSync,realpathSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {assertModel} from '../lib/model.mjs';
import {layoutView} from '../lib/layout.mjs';
import {renderHTML} from '../lib/render.mjs';
const digest=data=>createHash('sha256').update(data).digest('hex');
function evidence(model,repoRoot){
 const refs=[...model.elements,...model.relationships].flatMap(e=>(e.sources||[]).map(s=>({...s,owner:e.id})));
 if(!repoRoot)return {status:'not-checked',references:refs.length};
 if(!model.repository)throw new Error('--repo-root requires repository identity and revision');
 const root=resolve(repoRoot),revision=model.repository.revision;
 const run=args=>execFileSync('git',['-C',root,...args],{encoding:'utf8',maxBuffer:8*1024*1024,stdio:['ignore','pipe','pipe']});
 let remote=run(['remote','get-url','origin']).trim();
 const canonical=u=>u.replace(/^git@([^:]+):/,'https://$1/').replace(/\.git\/?$/,'').replace(/\/$/,'');
 if(canonical(remote)!==canonical(model.repository.url))throw new Error('Repository origin does not match model identity');
 const cache=new Map();for(const s of refs){if(!cache.has(s.path)){const mode=run(['ls-tree',revision,'--',s.path]).split(' ')[0];if(!['100644','100755'].includes(mode))throw new Error(`Source is not a committed regular file: ${s.path}`);cache.set(s.path,run(['show',`${revision}:${s.path}`]).split('\n'));}const lines=cache.get(s.path);const count=lines.length-(lines.at(-1)===''?1:0);if((s.endLine||s.line)>count)throw new Error(`Source range exceeds committed file: ${s.path}:${s.line}`);}
 const missing=[...model.elements,...model.relationships].filter(e=>!e.sources?.length).map(e=>e.id);
 return {status:missing.length?'partial':'ranges-verified',references:refs.length,missing,revision,entailment:'Requires source review; line existence is not semantic proof'};
}
function deliver(output,html,receipt){
 mkdirSync(dirname(output),{recursive:true});const receiptPath=output+'.receipt.json';
 for(const p of [output,receiptPath])if(existsSync(p)&&(!lstatSync(p).isFile()||lstatSync(p).isSymbolicLink()))throw new Error(`Output must be a regular file: ${p}`);
 const temp=mkdtempSync(join(dirname(output),'.c4fy-'));const fresh=join(temp,'artifact.html'),freshReceipt=join(temp,'receipt.json');let hadHTML=false,hadReceipt=false,installedHTML=false,installedReceipt=false;
 try{writeFileSync(fresh,html);writeFileSync(freshReceipt,JSON.stringify(receipt,null,2)+'\n');if(existsSync(output)){renameSync(output,join(temp,'old.html'));hadHTML=true;}if(existsSync(receiptPath)){renameSync(receiptPath,join(temp,'old.json'));hadReceipt=true;}renameSync(fresh,output);installedHTML=true;renameSync(freshReceipt,receiptPath);installedReceipt=true;}
 catch(error){try{if(installedHTML)rmSync(output);if(installedReceipt)rmSync(receiptPath);if(hadHTML)renameSync(join(temp,'old.html'),output);if(hadReceipt)renameSync(join(temp,'old.json'),receiptPath);}catch(rollback){throw new Error(`Delivery and rollback failed; recovery retained at ${temp}: ${error.message}; ${rollback.message}`);}rmSync(temp,{recursive:true,force:true});throw error;}
 rmSync(temp,{recursive:true,force:true});
}
try{
 const args=process.argv.slice(2);if(!args.length||args[0]==='--help'){console.log('C4fy 0.2.0\nnode bin/c4fy.mjs validate model.json [--repo-root PATH]\nnode bin/c4fy.mjs render model.json output.html [--repo-root PATH]\nIndependent C1/C2/C3/C4 renderer. No Archify installation required.');process.exit(0);}
 const command=args.shift();if(!['validate','render'].includes(command))throw new Error(`Unknown command: ${command}`);
 let repoRoot;const positional=[];for(let i=0;i<args.length;i++){if(args[i]==='--repo-root'){if(repoRoot||!args[i+1]||args[i+1].startsWith('--'))throw new Error('Expected one --repo-root PATH');repoRoot=args[++i];}else if(args[i].startsWith('--'))throw new Error(`Unknown flag: ${args[i]}`);else positional.push(args[i]);}
 if(positional.length!==(command==='render'?2:1))throw new Error('Expected model.json and, for render, output.html');
 const input=resolve(positional[0]),inputBytes=readFileSync(input);if(inputBytes.length>4*1024*1024)throw new Error('Model exceeds 4 MiB');
 const model=assertModel(JSON.parse(inputBytes.toString('utf8'))),layouts=model.views.map(v=>layoutView(model,v)),sourceEvidence=evidence(model,repoRoot);
 const receipt={schemaVersion:1,tool:'c4fy',version:'0.2.0',status:'pass',command,specification:{path:input,sha256:digest(inputBytes),bytes:inputBytes.length},validation:{model:'pass',layout:'pass',views:layouts.map(l=>({id:l.id,...l.diagnostics}))},sourceEvidence,browserEvidence:'not-run',visualReview:'not-run'};
 if(command==='render'){const output=resolve(positional[1]);if(!output.endsWith('.html'))throw new Error('Output must be a separate .html file');const inputIdentity=realpathSync(input);for(const target of [output,output+'.receipt.json']){const identity=existsSync(target)?realpathSync(target):target;if(identity===inputIdentity)throw new Error('Output or receipt would replace the input specification');}const html=renderHTML(model);receipt.artifact={path:output,sha256:digest(html),bytes:Buffer.byteLength(html)};deliver(output,html,receipt);}
 console.log(JSON.stringify(receipt,null,2));
}catch(error){console.error(JSON.stringify({status:'fail',error:error.message},null,2));process.exitCode=1;}
