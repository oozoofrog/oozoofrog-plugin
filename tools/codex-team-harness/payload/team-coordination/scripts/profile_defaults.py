#!/usr/bin/env python3
"""Separate requested role defaults, catalogue tier translation and configured evidence."""
import datetime,hashlib,json
class ProfileError(ValueError):pass
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def role_request(policy,role):
 value=policy['roles'][role];return {key:value[key]for key in ('model','reasoning_effort','service_tier')if key in value}
def resolve_service_tier(catalog,model,label):
 if label is None:return {'requested_label':None,'wire_id':None,'status':'not_requested','at':now()}
 if label not in ('normal','fast'):raise ProfileError('Unsupported requested tier label; never conflate reasoning/tier or infer aliases')
 entry=next((m for m in catalog if m.get('model')==model),None)
 if entry is None:raise ProfileError('Exact model absent from catalogue')
 tiers=entry.get('serviceTiers')
 if not isinstance(tiers,list):raise ProfileError('Explicit current serviceTiers required; null/default/deprecated labels do not establish a tier')
 options=[x for x in tiers if isinstance(x,dict)and isinstance(x.get('name'),str)and x['name'].casefold()==label]
 if len(options)!=1 or not isinstance(options[0].get('id'),str)or not options[0]['id']:raise ProfileError(label+' tier absent/ambiguous in current serviceTiers; no fallback or inherited tier')
 return {'requested_label':label,'wire_id':options[0]['id'],'catalog_label':options[0]['name'],'catalog_entry_sha256':digest(entry),'source':'official model/list.serviceTiers','status':'resolved_from_catalogue','at':now()}
def start_parameters(catalog,requested):
 model=requested['model'];effort=requested['reasoning_effort'];entry=next((x for x in catalog if x.get('model')==model),None)
 if entry is None or effort not in [x.get('reasoningEffort')for x in entry.get('supportedReasoningEfforts',[])]:raise ProfileError('Exact model/reasoning effort unavailable; no fallback')
 resolution=resolve_service_tier(catalog,model,requested.get('service_tier'));params={'model':model,'config':{'model_reasoning_effort':effort}}
 if resolution['wire_id']is not None:params['serviceTier']=resolution['wire_id']
 return params,resolution
def configured(response,source):
 allowed=source in ('thread/start','thread/resume','thread/settings/updated');available=allowed and 'serviceTier'in response and response['serviceTier']is not None
 return {'thread_id':response.get('thread',{}).get('id'),'model':response.get('model'),'reasoning_effort':response.get('reasoningEffort'),'wire_service_tier':response.get('serviceTier')if allowed else None,'status':'observed'if available else 'unavailable','scope':'configured','source':source,'at':now(),'reason':'Configured response/notification only; never current provider execution telemetry'if available else 'Tier is missing/unset or not exposed by this method; no default inferred'}
def settings(notification,expected_thread):
 if notification.get('threadId')!=expected_thread:raise ProfileError('Settings notification identity mismatch')
 return configured(dict(notification.get('threadSettings',{}),reasoningEffort=notification.get('threadSettings',{}).get('effort'),thread={'id':expected_thread}),'thread/settings/updated')
def tier_matches(observation,resolution,model=None,effort=None):return resolution.get('wire_id')is not None and observation.get('status')=='observed'and observation.get('wire_service_tier')==resolution['wire_id']and (model is None or observation.get('model')==model)and (effort is None or observation.get('reasoning_effort')==effort)
def execution_unknown():return {'status':'unavailable','model':None,'reasoning_effort':None,'wire_service_tier':None,'source':'official Turn schema','at':now(),'reason':'Turn metadata and text responses do not attest provider/model/tier execution'}
def desired_overlay(policy):
 return {'schema':1,'requested_scope':'all_existing_and_future_projects','roles':{role:role_request(policy,role)for role in policy['roles']},'adoption':'pending_explicit_owner_safe_boundary','requested_at':now(),'source_runtime_version':policy['version'],'execution_authorized':False,'native_service_tier':'unsupported via current app MCP; configured state unverified','completed_projects_rerun':False}
