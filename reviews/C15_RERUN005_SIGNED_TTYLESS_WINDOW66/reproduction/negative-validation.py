"""Window66 isolated rejection, remote failure and exact-restart checks."""
import os,sys,json,time,pathlib,subprocess as sp,hashlib,copy,ast,xml.etree.ElementTree as ET
BASE=pathlib.Path('/workspaces/window66-gate0-20261016T1509Z')
namespace={}; source=(BASE/'mechanical-validation.py').read_text().split('compile(SETUP')[0]
exec(compile(source,'approved-mechanical-helper','exec'),namespace)
E=BASE/'negative-final';E.mkdir(mode=0o755)
S=namespace['S'];H=namespace['H'];PY=namespace['PY'];SETUP=namespace['SETUP'];SIGNER=namespace['SIGNER']
spawn=namespace['spawn'];env=namespace['env'];canon=namespace['canon']
GR=pathlib.Path('/var/lib/aios-window65/trust/window66-response-final-2020z')
T=pathlib.Path('/var/lib/aios-window66-negative-final');T.mkdir(mode=0o755)
results=[]
def record(name,fn):
 try:detail=fn();r={'case':name,'status':'PASS','detail':detail}
 except Exception as exc:r={'case':name,'status':'FAIL','error':type(exc).__name__+': '+str(exc)}
 results.append(r);(E/'results.json').write_text(json.dumps(results,indent=2));print(name,r['status'],flush=True)
 return r

def verifier_reject(path,reason):
 code="import sys;sys.path.insert(0,"+repr(str(H))+");from r005.response_authorization import load_grant;load_grant("+repr(str(path))+")"
 p=spawn(999,984,[PY,'-B','-I','-c',code],env(T));out,err=p.communicate(timeout=10)
 assert p.returncode!=0 and reason.encode() in err
 return {'exit':p.returncode,'expected_reason':reason,'no_publish_invoked':True}
record('expired_response_enrollment',lambda:verifier_reject(pathlib.Path('/var/lib/aios-window65/trust/window66-response-retry3/user.json'),'expired or invalid enrollment'))
record('mechanical_ping_purpose_rejected',lambda:verifier_reject(pathlib.Path('/var/lib/aios-window65/trust/enrollment.json'),'response-purpose TEST_ONLY enrollment required'))
record('missing_enrollment',lambda:verifier_reject(GR/'not-issued.json','FileNotFoundError'))

# Operator-only revocation, retained permanently. No expired record is edited.
def revoke():
 p=GR/'delivered.revocation.json';g=json.loads((GR/'delivered.json').read_text())
 p.write_bytes(canon({'epoch':1,'revoked_enrollment_ids':[g['enrollment_id']]}));p.chmod(0o444)
 return verifier_reject(GR/'delivered.json','revoked enrollment')
record('revoked_enrollment',revoke)

RPC=r'''
import socket,json,sys
s=socket.socket(socket.AF_UNIX);s.settimeout(5);s.connect(sys.argv[1]);s.sendall(json.dumps({'command':'pending'}).encode()+bytes([10]));s.shutdown(socket.SHUT_WR);b=b''
while True:
 c=s.recv(65536)
 if not c:break
 b+=c
print(b.decode())
'''
def case_setup(tag,scenario):
 t=T/tag;t.mkdir(mode=0o700);os.chown(t,999,984);gp=GR/(scenario+'.json');g=json.loads(gp.read_text())
 p=spawn(999,984,[PY,'-B','-I','-c',SETUP,str(S),str(H),str(t),scenario,str(gp)],env(t));out,err=p.communicate(timeout=60)
 (E/(tag+'-setup.stderr')).write_bytes(err);assert p.returncode==0
 spec=(BASE/(scenario+'-operation.json')).read_bytes();(t/'operation.json').write_bytes(spec);os.chown(t/'operation.json',999,984)
 return t,g,gp

def runner_args(t,g):
 return [PY,'-B','-I',str(H/'launch.py'),'--source-repo',str(S),'--identity-sha256',hashlib.sha256((H/'IDENTITY.json').read_bytes()).hexdigest(),'run','--root',str(t/'synthetic-root'),'--run-id',g['run_id'],'--session-id',g['session_id'],'--operation',str(t/'operation.json'),'--persistence-repo',str(t/'git')]

def invalid_start(tag,grant_path,reason):
 t,g,gp=case_setup(tag,'user');v=env(t);v['AIOS66_TEST_ENROLLMENT']=str(grant_path)
 p=spawn(999,984,runner_args(t,g),v);out,err=p.communicate(timeout=40)
 (E/(tag+'-runner.stderr')).write_bytes(err);assert p.returncode!=0 and reason.encode() in err
 assert not list((t/'synthetic-root/mailbox').rglob('publisher-public.json'))
 assert not list((t/'synthetic-root/mailbox').glob('operations/*/proofs/*.json'))
 return {'runner_exit':p.returncode,'proof_count':0,'publisher_ready':False}
record('actual_runner_missing_enrollment',lambda:invalid_start('missing',GR/'not-issued.json','FileNotFoundError'))
record('actual_runner_ping_grant',lambda:invalid_start('ping','/var/lib/aios-window65/trust/enrollment.json','response-purpose TEST_ONLY enrollment required'))
record('actual_runner_expired_grant',lambda:invalid_start('expired','/var/lib/aios-window65/trust/window66-response-retry3/user.json','expired or invalid enrollment'))

def remote_failure():
 t,g,gp=case_setup('remote-reject','user');v=env(t);v['AIOS66_TEST_ENROLLMENT']=str(gp)
 p=spawn(999,984,runner_args(t,g),v);signer=None
 try:
  exchange=t/'synthetic-root/mailbox/operations'/g['operation_ids'][0];metadata=exchange/'signed-endpoint.json'
  deadline=time.monotonic()+40
  while not metadata.exists() and p.poll() is None and time.monotonic()<deadline:time.sleep(.03)
  assert metadata.exists(),'signed Publisher unavailable';endpoint=json.loads(metadata.read_text())['socket']
  # Filesystem refusal for an unapproved principal on the real response endpoint.
  bad=spawn(995,982,[PY,'-B','-I','-c',RPC,endpoint],env(t));out,err=bad.communicate(timeout=8)
  assert bad.returncode!=0 and b'PermissionError' in err
  # Runner UID cannot use the response-only endpoint even though it owns the socket.
  bad=spawn(999,984,[PY,'-B','-I','-c',RPC,endpoint],env(t));out,err=bad.communicate(timeout=8)
  assert bad.returncode==0 and json.loads(out)['ok'] is False
  deadline=time.monotonic()+20
  while not list((exchange/'ready').glob('*.json')) and p.poll() is None and time.monotonic()<deadline:time.sleep(.03)
  assert list((exchange/'ready').glob('*.json')),'durable request missing'
  service=json.loads((exchange/'service.json').read_text())
  bad=spawn(996,983,[PY,'-B','-I','-c',RPC,service['socket']],env(t));out,err=bad.communicate(timeout=8)
  assert bad.returncode!=0 and b'PermissionError' in err
  before=sp.check_output(['git','--git-dir',str(t/'remote.git'),'rev-parse','refs/heads/persistence/'+g['run_id']],text=True).strip()
  hook=t/'remote.git/hooks/pre-receive';hook.write_text('#!/bin/sh'+chr(10)+'exit 1'+chr(10));os.chown(hook,0,0);hook.chmod(0o755)
  signer=spawn(996,983,[PY,'-B','-I','-c',SIGNER,endpoint,'user'],env(t))
  out,err=p.communicate(timeout=70);(E/'remote-runner.stderr').write_bytes(err);assert p.returncode!=0
  sout,serr=signer.communicate(timeout=12);(E/'remote-signer.stderr').write_bytes(serr);assert signer.returncode==0
  signed=json.loads(sout);assert signed['signed_steps'];(E/'remote-signer-summary.json').write_text(json.dumps(signed,indent=2))
  assert list((exchange/'proofs').glob('*.json')),'legal signature did not reach Publisher proof'
  assert not list((exchange/'committed').glob('*.json')),'remote failure produced a completion ACK'
  state=json.loads((exchange/'operation.json').read_text());assert state['state']!='completed'
  after=sp.check_output(['git','--git-dir',str(t/'remote.git'),'rev-parse','refs/heads/persistence/'+g['run_id']],text=True).strip();assert before==after
  requests=len(list((exchange/'requests').glob('*.json')))
  retry=spawn(999,984,runner_args(t,g),v);rout,rerr=retry.communicate(timeout=30);(E/'exact-restart.stderr').write_bytes(rerr)
  assert retry.returncode!=0 and b'interrupted operation' in rerr
  assert len(list((exchange/'requests').glob('*.json')))==requests
  assert not pathlib.Path(endpoint).exists(),'retired Publisher endpoint survived'
  return {'unauthorized_uid_rejected':True,'runner_cannot_publish':True,'resident_cannot_register':True,'legal_signature_and_publisher_proof':True,'remote_head_unchanged':True,'completed':False,'ack_count':0,'exact_restart_rejected':True,'no_redispatch':True,'old_endpoint_retired':True}
 finally:
  if p.poll() is None:p.terminate();p.communicate(timeout=8)
  if signer is not None and signer.poll() is None:signer.terminate();signer.communicate(timeout=8)
record('real_remote_rejection_and_exact_restart',remote_failure)
suite=ET.Element('testsuite',name='Window66 negative mechanical validation',tests=str(len(results)),failures=str(sum(x['status']!='PASS' for x in results)))
for r in results:
 case=ET.SubElement(suite,'testcase',name=r['case'])
 if r['status']!='PASS':ET.SubElement(case,'failure').text=r.get('error','failed')
ET.ElementTree(suite).write(E/'junit.xml',encoding='utf-8',xml_declaration=True)
sys.exit(0 if all(r['status']=='PASS' for r in results) else 1)
