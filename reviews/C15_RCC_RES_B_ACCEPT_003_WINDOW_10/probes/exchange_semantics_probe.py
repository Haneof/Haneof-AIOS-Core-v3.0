#!/usr/bin/env python3
"""Read-only exchange authorship, replay, response feedback, and B semantic packet probe."""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
from collections import Counter,defaultdict

def sha(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--run-root',type=Path,required=True); ap.add_argument('--fresh-a-root',type=Path,required=True); ap.add_argument('--output',type=Path); a=ap.parse_args(); r=a.run_root.resolve(); ar=a.fresh_a_root.resolve()
 ra=r/'exchange/requests'; rb=r/'exchange/responses'; aa=ar/'exchange/requests'; ab=ar/'exchange/responses'
 ledger=[json.loads(x) for x in (r/'exchange/ledger.jsonl').read_text().splitlines() if x.strip()]
 pub={(x.get('request_id'),x.get('event')):x for x in ledger}
 rows=[]; old_hashes={}; b_hashes=Counter(); b_hash_to_ids=defaultdict(list); semantic_hashes=Counter(); missing=[]
 a_hash_to_ids={sha(p.read_bytes()):p.name for p in ab.glob('*.json')}
 def compact(v):
  if isinstance(v,dict): return {k:compact(x) for k,x in v.items() if k not in ('capability_catalog','cockpit')}
  if isinstance(v,list): return [compact(x) for x in v]
  return v
 for i in range(1,44):
  req=next(iter(ra.glob(f'req-{i:04d}-*.json')),None); resp=next(iter(rb.glob(f'req-{i:04d}-*.json')),None)
  if not req or not resp: missing.append(i); continue
  q=load(req); s=load(resp); rid=q['request_id']; raw=resp.read_bytes(); dh=sha(raw); d=s.get('directive',{}); sem=sha(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
  if i<=21:
   old=next(iter(ab.glob(f'req-{i:04d}-*.json')),None)
   old_hashes[rid]={'A_response_sha256':sha(old.read_bytes()) if old else None,'B_lineage_response_sha256':dh,'byte_equal':bool(old and old.read_bytes()==raw)}
  else:
   b_hashes[dh]+=1; b_hash_to_ids[dh].append(rid); semantic_hashes[sem]+=1
  pr=pub.get((rid,'response_published'),{})
  history=q['body'].get('capability_history',[])
  rows.append({'sequence':i,'request_id':rid,'cursor_group':'A-lineage' if i<=21 else 'B-run','request_wall_clock':q.get('wall_clock'),'response_published_wall_clock':pr.get('wall_clock'),'response_sha256':dh,'semantic_directive_sha256':sem,'envelope_authored_by':s.get('authored_by'),'provenance':s.get('provenance'),'provider_identity_fields':{k:s.get(k) for k in ('provider','model') if k in s},'round_index':q['body'].get('round_index'),'wake_reason':q['body'].get('wake_reason'),'user_input':q['body'].get('user_input'),'capability_history':[{k:h.get(k) for k in ('name','call_id','ok','error_code','error_message')} for h in history],'chosen_capabilities':[c.get('name') for c in d.get('capability_calls',[])],'chosen_response':d.get('response'),'silence':d.get('silence')} )
 # exact authoredness and replay assessment is deliberately observational; a self-asserted field is not authentication.
 report={'probe':'C15-RCC-RES-B-ACCEPT-003/window10/exchange-semantics','checks':{
  'counts':{'request_files':len(list(ra.glob('*.json'))),'response_files':len(list(rb.glob('*.json'))),'ledger_records':len(ledger),'missing_sequences':missing},
  'A_lineage_exact_response_bytes':old_hashes,
  'A_lineage_all_21_exact':len(old_hashes)==21 and all(x['byte_equal'] for x in old_hashes.values()),
  'B_exchange_uniqueness':{'B_request_count':len(rows)-21,'unique_raw_response_sha256':len(b_hashes),'duplicate_raw_response_sha256':{k:v for k,v in b_hashes.items() if v>1},'unique_directive_sha256':len(semantic_hashes),'duplicate_directive_sha256':{k:v for k,v in semantic_hashes.items() if v>1},'duplicate_against_A_lineage_response_bytes':{rid:{'response_sha256':dh,'matched_A_file':a_hash_to_ids[dh]} for dh,ids in b_hash_to_ids.items() if dh in a_hash_to_ids for rid in ids},'duplicate_B_response_groups':{dh:ids for dh,ids in b_hash_to_ids.items() if len(ids)>1}},
  'B_exchanges': [x for x in rows if x['sequence']>=22],
  'req0039': next((x for x in rows if x['request_id']=='req-0039-model_directive-ed097a32'),None),
  'req0040_to_req0041_feedback':{'req0040':next((x for x in rows if x['sequence']==40),None),'req0041':next((x for x in rows if x['sequence']==41),None)},
  'provenance_summary':{'response_envelopes_with_provenance':sum(bool(x.get('provenance')) for x in [load(p) for p in sorted(rb.glob('*.json'))]),'response_envelopes_with_provider_or_model':sum(bool(load(p).get('provider') or load(p).get('model')) for p in sorted(rb.glob('*.json'))),'all_envelope_authored_by_values':dict(Counter(str(load(p).get('authored_by')) for p in sorted(rb.glob('*.json'))))},
  'chronology_req0039':{'request_published':pub.get(('req-0039-model_directive-ed097a32','request_published')),'response_published':pub.get(('req-0039-model_directive-ed097a32','response_published')),'response_consumed':pub.get(('req-0039-model_directive-ed097a32','response_consumed'))}},'limitations':['Envelope authored_by is a self-asserted protocol field, not a process signature.','UNKNOWN provider identity is not treated as an automatic failure; authorship remains a separate predicate.']}
 text=json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+'\n'
 if a.output:a.output.write_text(text,encoding='utf-8')
 else: print(text)
if __name__=='__main__':main()
