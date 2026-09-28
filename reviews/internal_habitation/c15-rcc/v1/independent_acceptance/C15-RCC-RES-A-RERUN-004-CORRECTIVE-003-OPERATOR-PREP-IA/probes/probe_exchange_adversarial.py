import json, tempfile
from pathlib import Path
from aios_exchange.bridge import ExchangeBridge, ExchangeContractError, CLASSIFICATION_DISPATCHED_AWAITING_RESPONSE
from aios_exchange.canonical import canonical_json_bytes

def env(b,r,txt='SYNTHETIC'):
 return {'response_version':1,'request_id':r,'request_sha256':b.request_sha256(r),'authored_by':'EXTERNAL_CURRENT_RESIDENT_SESSION','directive':{'capability_calls':[],'response':txt,'silence':False}}
results={}
with tempfile.TemporaryDirectory() as d:
 b=ExchangeBridge(d); p=b.publish_request(kind='model_directive',body={'probe':'synthetic'}); r=p['request_id']; data=canonical_json_bytes(env(b,r))+b'\n'; b.responses.publish_bytes(request_id=r,response_bytes=data)
 path=b.responses.path_for(r); path.write_bytes(data+b' tamper')
 try: b.responses.publish_bytes(request_id=r,response_bytes=data); results['published-overwrite']='FAIL: accepted idempotent replay over tampered file'
 except Exception as e: results['published-overwrite']='PASS: '+type(e).__name__
 try: b.consume_response(r); results['tampered-consume']='FAIL'
 except Exception as e: results['tampered-consume']='PASS: '+type(e).__name__
 # orphan request file with no ledger identity
 orphan=Path(d)/'requests'/'req-9999-model_directive-deadbeef.json'; orphan.write_bytes(b'{}')
 integ=b.integrity(); results['orphan-request-integrity']=integ['ok'] is False and any('orphan request' in x for x in integ['problems'])
 # response record removed, must not be not-submitted
 lines=Path(d,'ledger.jsonl').read_bytes().splitlines(keepends=True); Path(d,'ledger.jsonl').write_bytes(lines[:1][0])
 b2=ExchangeBridge(d); results['tail-truncation-classification']=b2.recovery_state(r)['classification']==CLASSIFICATION_DISPATCHED_AWAITING_RESPONSE
print(json.dumps(results,indent=2)); assert all(v is True or (isinstance(v,str) and v.startswith('PASS')) for v in results.values())
