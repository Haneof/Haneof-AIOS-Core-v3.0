"""v2 additive correction: exact release hashes, chronology and due-work enumeration."""
import json,hashlib,pathlib,sys,collections,re
R=pathlib.Path(sys.argv[1]); sha=lambda b:'sha256:'+hashlib.sha256(b).hexdigest()
read=lambda p:json.loads((R/p).read_text())
D=[json.loads(x) for x in pathlib.Path(sys.argv[2]).read_text().splitlines()];d={x['check']:x['result'] for x in D}
def emit(k,v):print(json.dumps({'check':k,'result':v},ensure_ascii=False))
checks=[]
objects=d['durable_objects']; latest={o['object_id']:o for o in objects}
for a in d['acks']:
 e=a['event'];r=a['receipt'];o=latest[r['ingest_object_id']]
 checks.append({'sequence':r['sequence'],'payload':sha(e['resident_visible_payload'].encode())==r['fixture_payload_sha256'],'projection':sha(json.dumps(e,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())==r['fixture_projection_sha256'],'world_value':o['value']==e['resident_visible_payload'],'canonical_binding':r['binding_mode']!='canonical_user_turn' or (o['metadata']['session_id']==r['session_id'] and o['metadata']['turn_index']==r['turn_index']),'durable_revision':a['durable_revision_matches']})
emit('exact_release_checks',checks)
for x in D:
 if x['check']=='step':
  p=x['result'];a=p['advance'];emit('due_work',{'cursor':p['cursor'],'reviews':a['periodic_reviews'],'summaries':a['dimension_summaries'],'wake_passes':a['wake_passes'],'extra_wake_passes':p.get('extra_wake_passes',[]),'watch_receipts':p.get('attention_watch_receipts',[]),'pending':p.get('pending_wakes_after_step',[])})
emit('final_lifecycle',[{k:o.get(k) for k in ['object_id','object_type','wake_state','task_state','metadata','next_wake_at']} for o in latest.values() if o['object_type'] in ['wake','task']])
emit('meter_honesty',{'records':len(d['metering_records']),'provider_or_tokens_populated':[m for m in d['metering_records'] if any(m.get(k)!=None for k in ['provider','model','provider_request_id','input_tokens','output_tokens','total_tokens'])],'complete':[m for m in d['metering_records'] if m['usage_complete']]})
emit('decision_inventory',{'requests':len(d['decision_audit']),'kinds':dict(collections.Counter(read('decision_requests/'+x['request'])['kind'] for x in d['decision_audit'])),'missing_response_read':[x['request'] for x in d['decision_audit'] if not any(e['event']=='response_read' for e in x['chain'])]})
# Check complete later payloads and later ingested object IDs, without opening future fixture.
hits=[]
for x in d['decision_audit']:
 text=(R/'decision_requests'/x['request']).read_text()
 for a in d['acks']:
  if a['seq']<=x['cursor']:continue
  for kind,value in [('object_id',a['receipt']['ingest_object_id']),('payload',a['event']['resident_visible_payload'])]:
   if value in text: hits.append({'request':x['request'],'later_sequence':a['seq'],'kind':kind})
emit('later_payload_or_object_hits',hits)
emit('recovery1',{'first_request_attempt':read('decision_requests/req-0001-model_directive-13f2b448.json')['payload']['model_attempt_id'],'retry_request_attempt':read('decision_requests/req-0002-model_directive-983ede97.json')['payload']['model_attempt_id'],'first_response_has_semantic_directive':'directive' in read('decision_responses/req-0001-model_directive-13f2b448.json'),'first_response_has_request_id':'request_id' in read('decision_responses/req-0001-model_directive-13f2b448.json')})
emit('tracked_file_count',len(list(R.rglob('*'))))
