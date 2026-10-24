"""Synthetic JSON-RPC fixture, never evidence of real model availability."""
import json,sys
mode,log=sys.argv[1:]
for line in sys.stdin:
 o=json.loads(line);method=o.get('method')
 with open(log,'a')as f:f.write(method+'\n')
 with open(log+'.rpc.jsonl','a')as f:f.write(json.dumps(o)+'\n')
 if 'id'not in o:continue
 result={}
 if method=='model/list':result={'data':[{'model':'gpt-6.1-sol','defaultReasoningEffort':'low','defaultServiceTier':'priority','supportedReasoningEfforts':[{'reasoningEffort':'low'},{'reasoningEffort':'high'}],'serviceTiers':[]if mode=='empty-tiers'else[{'id':'priority','name':'Fast'}]}],'nextCursor':None}
 if method=='thread/read':result={'thread':{'id':'synthetic-thread','model':'gpt-6.1-sol','reasoningEffort':'high','status':{'type':'idle'}}}
 if method=='thread/start':result={'model':'gpt-6-luna' if mode=='mismatch' else 'gpt-6.1-sol','reasoningEffort':'high','serviceTier':'priority'if mode=='inherited-fast'else None,'thread':{'id':'synthetic-thread'}}
 if method=='turn/start':
  if mode=='disconnect':sys.exit(0)
  if mode=='provider-quota':
   print(json.dumps({'id':o['id'],'error':{'code':429,'message':'Synthetic provider quota/capacity refusal'}}),flush=True)
   continue
  result={'turn':{'id':'synthetic-turn'}}
 print(json.dumps({'id':o['id'],'result':result}),flush=True)
 if method=='turn/start':
  if mode=='request':
   print(json.dumps({'id':999,'method':'permissions/request','params':{}}),flush=True)
   continue
  if mode!='missing-usage':print(json.dumps({'method':'thread/tokenUsage/updated','params':{'threadId':'synthetic-thread','tokenUsage':{'last':{'totalTokens':35 if mode=='high-usage'else 5},'total':{'totalTokens':100005}}}}),flush=True)
  print(json.dumps({'method':'turn/completed','params':{'threadId':'synthetic-thread','turn':{'id':'synthetic-turn','status':'completed'}}}),flush=True)
