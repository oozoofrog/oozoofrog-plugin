"""Synthetic JSON-RPC fixture, never evidence of real model availability."""
import json,sys
mode,log=sys.argv[1:]
for line in sys.stdin:
 o=json.loads(line);method=o.get('method')
 with open(log,'a')as f:f.write(method+'\n')
 if 'id'not in o:continue
 result={}
 if method=='model/list':result={'data':[{'model':'gpt-6.1-sol'}],'nextCursor':None}
 if method=='thread/start':result={'model':'gpt-6-luna' if mode=='mismatch' else 'gpt-6.1-sol','thread':{'id':'synthetic-thread'}}
 if method=='turn/start':
  if mode=='disconnect':sys.exit(0)
  result={'turn':{'id':'synthetic-turn'}}
 print(json.dumps({'id':o['id'],'result':result}),flush=True)
 if method=='turn/start':
  if mode=='request':
   print(json.dumps({'id':999,'method':'permissions/request','params':{}}),flush=True)
   continue
  print(json.dumps({'method':'thread/tokenUsage/updated','params':{'threadId':'synthetic-thread','tokenUsage':{'total':{'totalTokens':5}}}}),flush=True)
  print(json.dumps({'method':'turn/completed','params':{'threadId':'synthetic-thread','turn':{'id':'synthetic-turn','status':'completed'}}}),flush=True)
