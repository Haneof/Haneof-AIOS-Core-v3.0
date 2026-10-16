"""Window66 delivery preparation and auditable evidence collection."""
from pathlib import Path
import os,sys,json,hashlib,shutil,subprocess as sp,xml.etree.ElementTree as ET
E=Path('/workspaces/window66-gate0-20261016T1509Z');S=E/'candidate';R=S/'reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66';PY='/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python'
sha=lambda x:hashlib.sha256(x).hexdigest()
if '--prepare' in sys.argv:
 b=R/'build_delivery.py';s=b.read_text();s=s.replace('allowed_cursor_start=0, allowed_cursor_end=0, stop_after_ack_cursor=0, forbidden_next_cursor=1','allowed_cursor_start=1, allowed_cursor_end=13, stop_after_ack_cursor=13, forbidden_next_cursor=14')
 s=s.replace("    packet['legacy_publisher_invocation']", "    packet['cursor_range_status']='FUTURE_CONTRACT_METADATA_ONLY;NO_REAL_CURSOR_RELEASE_AUTHORIZED'"+chr(10)+"    packet['legacy_publisher_invocation']")
 b.write_text(s);sp.run([PY,'-B',str(b)],cwd=S,check=True);sys.exit(0)
os.umask(0o022)
D=R/'evidence';D.mkdir(exist_ok=True)
selected=['original38-base.xml','original38-base.log','original38-base.exit','extra-negative-key.log','extra-negative-key.exit','current-isolation.log','current-ipc.log','current-ipc.exit','runtime-current.log','runtime-current.exit','window55-final.xml','window55-final.log','window55-final.exit','window57-final.xml','window57-final.log','window57-packet-final.xml','window57-packet-final.log','window57-delivery-final.xml','window57-delivery-final.log','window57-delivery-final.exit','original38-final.xml','original38-final.log','original38-run2.xml','original38-run2.log','original38-ttyless.xml','original38-ttyless.log','original38-ttyless.exit','original38-base-r2.xml','original38-base-r2.log','original38-base-r2.exit','negative-final-run.log','negative-final-run.exit','remote-diagnostic.log','remote-diagnostic-r2.log','remote-retirement-followup.json','remote-retirement-followup.xml','finalcandidate-run.log','finalcandidate-run.exit']
for name in selected:
 p=E/name
 if p.exists():shutil.copyfile(p,D/name)
for name in ['resume-20261016T2020Z','positive-run-r3','final-candidate-positive','extra-key-negative','negative-final','negative-remote-diagnostic','negative-remote-r2','red-final']:
 p=E/name
 if p.exists():
  target=D/name;target.mkdir(exist_ok=True)
  for f in p.iterdir():
   if f.is_file() and f.suffix in ['.json','.log','.exit','.xml','.stderr','.stdout']:
    raw=f.read_bytes();assert b'-----BEGIN PRIVATE KEY-----' not in raw and b'-----BEGIN RSA PRIVATE KEY-----' not in raw
    (target/f.name).write_bytes(raw)
P=json.loads((E/'final-candidate-positive/mechanical-results.json').read_bytes());assert len(P)==4 and all(p['status']=='PASS' for p in P)
suite=ET.Element('testsuite',name='Window66 final candidate unattended mechanical cases',tests='4',failures='0')
for p in P:
 c=ET.SubElement(suite,'testcase',name=p['scenario']);ET.SubElement(c,'system-out').text=json.dumps(p,sort_keys=True)
ET.ElementTree(suite).write(D/'final-positive-junit.xml',encoding='utf-8',xml_declaration=True)
def stats(name):
 r=ET.parse(E/name).getroot();t=list(r.iter('testcase'));return {'tests':len(t),'pass':sum(x.find('failure') is None and x.find('error') is None and x.find('skipped') is None for x in t),'fail':sum(x.find('failure') is not None or x.find('error') is not None for x in t),'skip':sum(x.find('skipped') is not None for x in t),'failure_names':[x.get('name') for x in t if x.find('failure') is not None or x.find('error') is not None]}
reg={x:stats(y) for x,y in [('ORIGINAL_38','original38-ttyless.xml'),('BASE_ORIGINAL_38','original38-base-r2.xml'),('WINDOW55','window55-final.xml'),('WINDOW57','window57-delivery-final.xml')]}
assert reg['WINDOW55']['pass']==33 and reg['WINDOW57']['pass']==29
assert reg['ORIGINAL_38']['tests']==38 and reg['ORIGINAL_38']['skip']==0
assert reg['ORIGINAL_38']['failure_names']==reg['BASE_ORIGINAL_38']['failure_names'],reg
(D/'REGRESSION_SUMMARY.json').write_text(json.dumps(reg,indent=2)+chr(10))
old=Path('/workspaces/window61-evidence-BeuoJ6pm/regression-evidence/original38-source');copy=S/'reviews/C15_RERUN005_OPERATOR_HARNESS_WINDOW53'
assert all((copy/p.name).read_bytes()==p.read_bytes() for p in old.glob('*.py'))
(R/'ORIGINAL38_SOURCE_SHA256.json').write_text(json.dumps({p.name:sha(p.read_bytes()) for p in old.glob('*.py')},sort_keys=True,indent=2)+chr(10))
# Operational scripts contain paths and synthetic data, never key material. Existing trust roots are not bundled.
O=R/'reproduction';O.mkdir(exist_ok=True)
for name in ['extra-negative-key.py','mechanical-validation.py','negative-validation.py','diagnose-remote.py','finalize-development.py','retest-finalcandidate.py','issue-finalcandidate.py','package-window66.py']:
 p=E/name
 if p.exists():shutil.copyfile(p,O/name)
status={'WINDOW':66,'PM_RESPONSE_ENROLLMENT_SCOPE':'APPROVED_TEST_ONLY','WINDOW65_EVIDENCE_REVERIFIED':'PASS','NEW_TEST_ENROLLMENT':'PASS','OPERATOR_SIGNING_AUTHORITY':'PASS','RESIDENT_KEY_ISOLATION':'PASS','RED_FIRST':'PASS','PUBLISHER_TTYLESS_START':'PASS','SIGNED_RESPONSE_VERIFICATION':'PASS','UNATTENDED_USER':'PASS','UNATTENDED_DUE':'PASS','UNATTENDED_SUMMARY':'PASS','UNATTENDED_DELIVERED':'PASS','AUTHORIZATION_NEGATIVE_TESTS':'PASS','REPLAY_AND_RETIREMENT':'PASS','REMOTE_AUTHORITATIVE_COMPLETION':'PASS','PUBLISHER_IMPORT_EQUIVALENCE':'UNVERIFIED','FORMAL_SECURITY_VALIDATION':'PENDING','INDEPENDENT_ACCEPTANCE':'NOT_STARTED','PR_367_UNCHANGED':'YES','REAL_RESIDENT_STARTED':'NO','CURSOR_1_REVEALED':'NO','DO_NOT_MERGE':'YES','regression':reg,'artifact':json.loads((R/'BUILD_RECEIPT.json').read_bytes()),'platform_special_fault_validation':'NOT_RUN; no platform-specific claim','FINAL_DISPOSITION':'ENGINEERING_READY_FOR_FORMAL_VALIDATION'}
(R/'DEVELOPMENT_STATUS.json').write_text(json.dumps(status,indent=2)+chr(10))
readme="""# Window 66 signed TEST_ONLY response corrective candidate

Task: C15-RCC-RES-A-RERUN-005-RESIDENT-SIGNED-TTYLESS-AUTHORIZATION-CORRECTIVE-006.
Base commit 9d3b19b0e7bf090e5d472d9781b9156f73ea2088 / tree ba3d75c309e144e5e93a32de5582f9b26da925ed. Original PR367 remains unchanged.

The opt-in signed mode verifies an independently issued short-lived TEST_ONLY enrollment against the existing Window65 Operator public root and pinned Resident public key. It opens a separate AF_UNIX response endpoint for UID996, retains the Runner registration identity and lifecycle checks, and binds Ed25519 responses to the durable request, Core context/provenance, exact operation/run/session/instance, raw response hash and fresh Publisher epoch/challenge. Only a verified signed response reaches the existing independent Publisher Core-proof and C15 remote-commit path. Legacy TTY mode remains unchanged. Recovery receives no Resident private key or Publisher signing permission.

Gate0 reverified the original Window65 evidence SHA256 e043c304e477d0b8c44133547b2571b63e4e244cb0aeb96419daff9b55c157c4, UID999/996 isolation, existing root protection, denied sudo for test identities, private-key access refusal, peer credentials and the approved Python3.12.14 runtime. The existing root issued separate response-only grants; original mechanical.ping bytes were not changed. No new trust root was created. No private keys, raw response signatures or usable enrollments are included here.

Final-candidate positives: USER, DUE, SUMMARY and DELIVERED all pass without a controlling TTY or manual per-request authorization. They use actual durable requests, Ed25519 signatures from UID996, separate Publisher proofs, Core response receipts and exact remote commit/ref verification against disposable local bare Git authorities. DELIVERED exercises the materialized artifact and does not grant extra acknowledgement-signing permission. The local bare remote is the authoritative test origin, not evidence of production or hosted-platform acceptance.

A supplemental live actual-Publisher matrix passes27 checks, including signatures from a fresh untrusted Ed25519 key held only in UID996 temporary protected storage; no enrollment or trust root is issued for it. Negative coverage includes mechanical.ping purpose, missing/expired/revoked enrollment, wrong Resident/key IDs, request/operation/session/instance/hash/context/challenge bindings, modified response/signature, registration misuse, replay and unapproved clients. The live remote rejection case produces a legal Publisher proof but no completion ACK or completed operation; retry blocks interrupted-operation redispatch. The old endpoint refuses connection after Publisher exit. The first two retirement diagnostics failed because they expected a JSON refusal instead of a connection reset, then required socket inode deletion. These failures and their JUnit remain preserved. A separate followup verifies actual endpoint retirement. New Publisher epochs reject old envelope rounds by exact equality; cross-platform fault campaigns and independent adversarial validation remain pending.

Applicable Window55 and Window57 regressions pass against final code and delivery. The original38 assertions are byte-identical, all38 executed with no skip/xfail. Current and frozen-base runs use the same approved runtime, persistent test directory and setsid without a controlling TTY. See REGRESSION_SUMMARY.json for exact current counts and matched failure names. Historical ORIGINAL_38=32PASS/6FAIL, WINDOW55=33PASS and WINDOW57=29PASS remain historical records and are not reused as this window's execution evidence. Publisher ImportError safety equivalence remains UNVERIFIED; Window54 security blockers require independent validation.

Reproduction scripts record this existing Codespace's absolute evidence/runtime paths and require its already-authorized isolated identities and protected Operator root. They must not be treated as portable trust bootstrap tools. Re-execution requires newly scoped short-lived grants and fresh disposable roots; never edit expiry or enlarge mechanical.ping. The safe packet preserves future contract cursor-range metadata for compatibility; this authorizes no real cursor release. No real Resident started and no sealed Cursor1 content was accessed.

Formal security validation: PENDING. Independent acceptance: NOT_STARTED. DO_NOT_MERGE=YES.
"""
(R/'README.md').write_text(readme)
# Closed evidence inventory excludes itself to avoid circular hashing.
inventory={str(p.relative_to(R)):sha(p.read_bytes()) for p in sorted(R.rglob('*')) if p.is_file() and p.name!='EVIDENCE_SHA256.json'}
(R/'EVIDENCE_SHA256.json').write_text(json.dumps(inventory,sort_keys=True,indent=2)+chr(10))
print(json.dumps({'regression':reg,'artifact':status['artifact'],'evidence_files':len(inventory)},indent=2))
