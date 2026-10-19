import os,time,json,hashlib,pathlib,subprocess as sp,secrets,uuid,stat
assert os.getuid()==0
B=pathlib.Path('/var/lib/aios-window65'); E=pathlib.Path('/workspaces/window66-gate0-20261016T1509Z')
def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
assert (E/'runtime-current.exit').read_text().strip()=='0'
assert 'PASS' in (E/'current-isolation.log').read_text()
assert (E/'current-ipc.exit').read_text().strip()=='0'
old={p.name:sha(p.read_bytes()) for p in [B/'trust/enrollment.json',B/'trust/enrollment.sig',B/'trust/config.json']}
for p in [B,B/'operator',B/'trust']:
    s=p.lstat(); assert stat.S_ISDIR(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022
expected='1124f54a497c9dfa5fcc6e16fb9fc570816fadba6f32016a8b53d5f0243090dd'
r=sp.run(['openssl','pkey','-in',str(B/'operator/issuer.key'),'-pubout','-outform','DER'],capture_output=True,check=True); assert sha(r.stdout)==expected
D=B/'trust/window66-response-finalcandidate'; D.mkdir(mode=0o755); now=int(time.time()); audit=[]
for scenario in ['user','due','summary','delivered']:
    spec={'mode':'due' if scenario=='due' else 'user','at':'2026-10-13T00:00:21+00:00' if scenario=='summary' else '2026-10-13T00:00:00+00:00','cursor':1,'event_id':'synthetic-w66-candidate-'+scenario,'turn_index':21 if scenario=='summary' else 1,'user_input':'' if scenario=='due' else 'synthetic USER bytes','timeout':20}
    kinds=['model_directive','round_summary','dimension_summary'] if scenario=='summary' else ['model_directive']
    g={'domain':'aios.r005.test.enrollment.v1','version':1,'purpose':'aios.r005.test.response.sign.v1','test_only':True,'issuer_key_id':expected,'enrollment_id':'W66-'+str(uuid.uuid4()),'serial':secrets.token_hex(16),'issued_at':now,'not_before':now,'expires_at':now+3600,'resident_id':'AIOS_RESIDENT_TEST','resident_uid':996,'resident_key_id':'838a1a7d168ac6dd8441c0c8a2deab439a7b775d6583c40618a51f627e6e3b7f','resident_public_key_pem':(B/'trust/resident.pub').read_text(),'run_id':'synthetic-w66-candidate-'+scenario,'session_id':'synthetic-w66-candidate-session-'+scenario,'instance_id':secrets.token_hex(32),'operation_ids':[sha(canon(spec))],'request_kinds':kinds,'revocation':{'epoch':1,'file':str(D/(scenario+'.revocation.json'))},'scenario':scenario,'pm_decision':'https://github.com/Haneof/Haneof-AIOS-Core-v3.0/pull/367#issuecomment-6218239137'}
    p=D/(scenario+'.json'); p.write_bytes(canon(g)); sig=D/(scenario+'.sig')
    sp.run(['openssl','pkeyutl','-sign','-rawin','-inkey',str(B/'operator/issuer.key'),'-in',str(p),'-out',str(sig)],check=True,stdout=sp.DEVNULL)
    sp.run(['openssl','pkeyutl','-verify','-rawin','-pubin','-inkey',str(B/'trust/issuer.pub'),'-in',str(p),'-sigfile',str(sig)],check=True,stdout=sp.DEVNULL)
    rev=D/(scenario+'.revocation.json'); rev.write_bytes(canon({'epoch':1,'revoked_enrollment_ids':[]}))
    for q in [p,sig,rev]:os.chown(q,0,0);q.chmod(0o444)
    (OUT/(scenario+'-operation.json')).write_bytes(canon(spec))
    audit.append({'scenario':scenario,'enrollment_id':g['enrollment_id'],'grant_sha256':sha(p.read_bytes()),'signature_sha256':sha(sig.read_bytes()),'issued_at':now,'expires_at':now+3600,'issuer_euid':os.geteuid(),'issuer_fingerprint':expected})
assert old=={p.name:sha(p.read_bytes()) for p in [B/'trust/enrollment.json',B/'trust/enrollment.sig',B/'trust/config.json']}
(OUT/'operator-issuance-audit.json').write_text(json.dumps(audit,indent=2))
(E/'gate0-status.json').write_text(json.dumps({'WINDOW':66,'WINDOW65_EVIDENCE_REVERIFIED':'PASS','OPERATOR_SIGNING_AUTHORITY':'PASS','RESIDENT_KEY_ISOLATION':'PASS','NEW_TEST_ENROLLMENT':'PASS','old_grant_hashes':old},indent=2))
print('GATE0=PASS OPERATOR_SIGNING_AUTHORITY=PASS NEW_TEST_ENROLLMENT=PASS GRANTS=4 ORIGINAL_PING_UNCHANGED=YES')
