"""Export only synthetic completed-run public proof and receipt evidence."""
from pathlib import Path
import os,json,sqlite3,subprocess as sp,hashlib,re,shutil
assert os.getuid()==0
os.umask(0o022)
E=Path('/workspaces/window66-gate0-20261016T1509Z');R=E/'candidate/reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66';D=R/'evidence/authoritative-cases';D.mkdir(mode=0o755)
results=json.loads((E/'final-candidate-positive/mechanical-results.json').read_bytes())
for result in results:
 n=result['scenario'];t=Path('/var/lib/aios-window66-tests-finalcandidate')/n;g=json.loads((Path('/var/lib/aios-window65/trust/window66-response-finalcandidate')/(n+'.json')).read_bytes());x=t/'synthetic-root/mailbox/operations'/g['operation_ids'][0];out=D/n;out.mkdir(mode=0o755)
 def save(name,raw):
  assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',raw)
  p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(0o644)
 save('operation.json',(x/'operation.json').read_bytes())
 for part in ['requests','responses','proofs','committed','ready']:
  for p in (x/part).glob('*.json'):save(part+'/'+p.name,p.read_bytes())
 db=sqlite3.connect('file:'+str(t/'synthetic-root/state/runtime/world.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 rows=[dict(row) for row in db.execute('SELECT * FROM background_model_response_receipts')];db.close()
 assert len(rows)==result['core_receipts'] and len(rows)>0
 save('core-response-receipts.json',(json.dumps(rows,sort_keys=True,indent=2,default=lambda v:v.hex())+chr(10)).encode())
 ref='refs/heads/persistence/'+g['run_id'];commit=sp.check_output(['git','--git-dir',str(t/'remote.git'),'rev-parse',ref],text=True).strip();assert commit==result['remote_commit']
 save('authoritative-remote.json',(json.dumps({'authority':'ISOLATED_LOCAL_BARE_GIT_TEST_ORIGIN','ref':ref,'commit':commit,'operation_remote_commit':json.loads((x/'operation.json').read_bytes())['remote_commit'],'source_root':str(t),'test_only':True},sort_keys=True,indent=2)+chr(10)).encode())
 save('authoritative-commit.txt',sp.check_output(['git','--git-dir',str(t/'remote.git'),'show','--format=fuller','--no-patch',commit]))
 save('authoritative-tree.txt',sp.check_output(['git','--git-dir',str(t/'remote.git'),'ls-tree','-r',commit]))
 print(n,'PUBLIC_PROOF_RECEIPT_REMOTE_EVIDENCE_EXPORTED',len(rows))
shutil.copyfile(E/'export-authoritative-evidence.py',R/'reproduction/export-authoritative-evidence.py')
# Preserve raw logs exactly; whitespace warnings in raw stderr/stdout are expected.
p=R/'README.md';p.write_text(p.read_text()+chr(10)+'Evidence/authoritative-cases includes the actual synthetic durable requests/responses, Publisher proofs, Core receipt rows and authoritative commit/tree records. Raw logs retain their original whitespace; source-code diff checks exclude these immutable log bytes.'+chr(10))
inv={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.rglob('*')) if p.is_file() and p.name!='EVIDENCE_SHA256.json'}
(R/'EVIDENCE_SHA256.json').write_text(json.dumps(inv,sort_keys=True,indent=2)+chr(10))
