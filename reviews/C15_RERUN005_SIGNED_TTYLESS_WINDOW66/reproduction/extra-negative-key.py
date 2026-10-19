"""Live wrong-public-key and complete envelope-binding rejection test."""
from pathlib import Path
import os,json,xml.etree.ElementTree as ET
B=Path('/workspaces/window66-gate0-20261016T1509Z');ns={}
exec(compile((B/'mechanical-validation.py').read_text().split('compile(SETUP')[0],'mechanical-helper','exec'),ns)
E=B/'extra-key-negative';E.mkdir(mode=0o755)
ns['E']=E;ns['T']=Path('/var/lib/aios-window66-extra-key-negative');ns['T'].mkdir(mode=0o755);ns['GR']=Path('/var/lib/aios-window65/trust/window66-response-final-2020z')
(E/'due-operation.json').write_bytes((B/'due-operation.json').read_bytes())
s=ns['SIGNER'];s=s.replace("['resident_id','resident_key_id','request_id','operation_id','session_id','instance_id','request_sha256','context','publisher_challenge']", "['domain','version','purpose','enrollment_id','enrollment_sha256','resident_id','resident_key_id','run_id','session_id','instance_id','operation_id','request_id','request_sha256','request_kind','core_attempt_id','context','provenance','publisher_epoch','publisher_challenge','issued_at','expires_at']")
extra="""   with tempfile.TemporaryDirectory(dir='/var/lib/aios-window65/AIOS_RESIDENT_TEST/private') as td:
    p=pathlib.Path(td);(p/'message').write_bytes(canon(envelope))
    sp.run(['/usr/bin/openssl','genpkey','-algorithm','ED25519','-out',str(p/'untrusted.key')],check=True,capture_output=True)
    assert (p/'untrusted.key').stat().st_uid==996 and (p/'untrusted.key').stat().st_mode & 0o077==0
    sp.run(['/usr/bin/openssl','pkeyutl','-sign','-rawin','-inkey',str(p/'untrusted.key'),'-in',str(p/'message'),'-out',str(p/'signature')],check=True,capture_output=True)
    wrong=copy.deepcopy(command);wrong['signature']=(p/'signature').read_bytes().hex();probes['untrusted_public_key_signature']=wrong
"""
s=s.replace("   probes['register_endpoint']",extra+"   probes['register_endpoint']")
compile(s,'full-binding-and-untrusted-key-signer','exec');ns['SIGNER']=s
r=ns['run_scenario']('due');assert r['status']=='PASS' and 'untrusted_public_key_signature' in r['signer']['negative_pass']
(E/'result.json').write_text(json.dumps(r,indent=2)+chr(10))
suite=ET.Element('testsuite',name='Window66 actual Publisher signed response negative matrix',tests=str(len(r['signer']['negative_pass'])),failures='0')
for name in r['signer']['negative_pass']:ET.SubElement(suite,'testcase',name=name)
ET.ElementTree(suite).write(E/'junit.xml',encoding='utf-8',xml_declaration=True)
print('LIVE_FULL_BINDINGS_AND_UNTRUSTED_PUBLIC_KEY=PASS',len(r['signer']['negative_pass']))
