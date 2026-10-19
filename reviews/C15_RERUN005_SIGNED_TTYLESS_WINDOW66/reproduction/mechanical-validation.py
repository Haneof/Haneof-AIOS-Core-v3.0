"""Disposable mechanical verification; no real Resident or sealed event inputs."""
import os,sys,json,time,hashlib,pathlib,subprocess as sp,sqlite3,copy
E=pathlib.Path('/workspaces/window66-gate0-20261016T1509Z'); S=E/'candidate'
H=S/'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness'
PY='/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python'
T=pathlib.Path('/var/lib/aios-window66-tests-retry3'); GR=pathlib.Path('/var/lib/aios-window65/trust/window66-response-retry3')
assert os.getuid()==0
os.umask(0o022)
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def prefix(uid,gid):return ['/usr/bin/setpriv','--reuid',str(uid),'--regid',str(gid),'--init-groups','--inh-caps=-all','--ambient-caps=-all','--bounding-set=-all','--no-new-privs']
def spawn(uid,gid,args,env):return sp.Popen(prefix(uid,gid)+args,env=env,stdin=sp.DEVNULL,stdout=sp.PIPE,stderr=sp.PIPE,close_fds=True,start_new_session=True)
def env(t):return {'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(t),'C15_PERSISTED_WORKSPACE':str(t),'PYTHONDONTWRITEBYTECODE':'1'}
SETUP=r'''
import sys,os,json,pathlib,subprocess as sp
from datetime import datetime,timezone,timedelta
S,H,t,scenario,grant_path=sys.argv[1:]; S=pathlib.Path(S);t=pathlib.Path(t)
sys.path[:0]=[str(S/'src'),str(S),H]
from tools.c15_persistence import backend
backend.WORKSPACE=t
from r005.safe_runner import init,barrier
from tools.c15_persistence.backend import RunBackend
from aios_core.headless.core import HeadlessConfig,HeadlessCore
from aios_core.contracts.enums import WakeSource
from aios_core.wake.service import WakeSignalRequest
g=json.loads(pathlib.Path(grant_path).read_text()); repo=t/'git';repo.mkdir();remote=t/'remote.git'
for c in [['git','init','--bare',str(remote)],['git','init',str(repo)],['git','-C',str(repo),'config','user.name','W66 Mechanical Test'],['git','-C',str(repo),'config','user.email','mechanical@example.invalid'],['git','-C',str(repo),'remote','add','origin',str(remote)]]:sp.run(c,check=True,capture_output=True)
root=t/'synthetic-root';init(root,g['run_id'],g['session_id'],'user_1',repo)
core=HeadlessCore(config=HeadlessConfig(world_path=root/'state/runtime/world.sqlite',index_path=root/'state/runtime/index.sqlite'),model_handler=lambda _:(_ for _ in ()).throw(RuntimeError('no model during setup'))).start()
moment=datetime(2026,10,13,tzinfo=timezone.utc)
if scenario=='due':core.runtime.wake_bus.emit(WakeSignalRequest(wake_source=WakeSource.SAFETY,rule_id='synthetic-boundary',observed_at=moment,priority=100,dedupe_key='synthetic-boundary'))
if scenario=='summary':
 for i in range(1,21):core.runtime.ingestor.commit_turn(session_id=g['session_id'],turn_index=i,user_text='synthetic history '+str(i),assistant_text='synthetic setup bytes',occurred_at=moment+timedelta(seconds=i))
 assert core.runtime.continuity.prepare_next_round_summary(session_id=g['session_id'],before_turn=21,recent_turn_limit=8,summary_chunk_turns=12) is not None
core.stop();b=RunBackend.open(root,run_id=g['run_id'],session_id=g['session_id']);barrier(b,repo,'synthetic-w66-setup');b.release()
'''
SIGNER=r'''
import os,sys,json,time,hashlib,pathlib,subprocess as sp,socket,struct,tempfile,base64,copy
endpoint,scenario=sys.argv[1:]
assert os.getuid()==996
statraw=pathlib.Path('/proc/self/stat').read_text(); assert statraw[statraw.rfind(')')+1:].split()[4]=='0'
try:os.open('/dev/tty',os.O_RDONLY)
except OSError:pass
else:raise AssertionError('unexpected controlling terminal')
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def rpc(command):
 with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
  s.settimeout(10);s.connect(endpoint)
  peer=struct.unpack('3i',s.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12));assert peer[1:]==(999,984)
  s.sendall(canon(command)+bytes([10]));s.shutdown(socket.SHUT_WR);b=b''
  while True:
   chunk=s.recv(65536)
   if not chunk:break
   b+=chunk;assert len(b)<2097152
  return json.loads(b)
answered=set();negative=[];deadline=time.monotonic()+80;steps=[]
while time.monotonic()<deadline:
 try:r=rpc({'command':'pending'})
 except (ConnectionError,FileNotFoundError):break
 assert r['ok'],r
 for item in r['result']['pending']:
  req=item['request'];rid=req['request_id']
  if rid in answered:continue
  directive=({'silence':True,'provenance':req['body']['provenance_binding']} if scenario=='due' else {'response':'synthetic USER return','provenance':req['body']['provenance_binding']}) if req['kind']=='model_directive' else {'text':'synthetic Summary transport bytes'}
  response={'response_version':1,'request_id':rid,'request_sha256':item['envelope']['request_sha256'],'authored_by':'EXTERNAL_CURRENT_RESIDENT_SESSION','directive':directive}
  raw=canon(response); envelope={**item['envelope'],'response_sha256':hashlib.sha256(raw).hexdigest()}
  with tempfile.TemporaryDirectory(dir='/var/lib/aios-window65/AIOS_RESIDENT_TEST/private') as td:
   p=pathlib.Path(td);(p/'message').write_bytes(canon(envelope))
   sp.run(['/usr/bin/openssl','pkeyutl','-sign','-rawin','-inkey','/var/lib/aios-window65/AIOS_RESIDENT_TEST/private/resident.key','-in',str(p/'message'),'-out',str(p/'signature')],check=True,capture_output=True)
   signature=(p/'signature').read_bytes().hex()
  command={'command':'publish-signed','envelope':envelope,'signature':signature,'raw':base64.b64encode(raw).decode()}
  if not answered:
   probes={}
   for field in ['resident_id','resident_key_id','request_id','operation_id','session_id','instance_id','request_sha256','context','publisher_challenge']:
    wrong=copy.deepcopy(command);wrong['envelope'][field]='wrong';probes[field]=wrong
   wrong=copy.deepcopy(command);wrong['raw']=base64.b64encode(raw+b' ').decode();probes['response_bytes']=wrong
   wrong=copy.deepcopy(command);wrong['signature']='00'*64;probes['signature']=wrong
   probes['register_endpoint']={'command':'register'}
   for label,wrong in probes.items():
    reply=rpc(wrong);assert reply['ok'] is False,(label,reply);negative.append(label)
  result=rpc(command); assert result['ok'],result
  replay=rpc(command);assert replay['ok'] is False;negative.append('replay')
  answered.add(rid);steps.append({'request_id':rid,'kind':req['kind'],'response_sha256':hashlib.sha256(raw).hexdigest(),'authorization_sha256':result['result']['resident_authorization_sha256']})
 time.sleep(.03)
print(json.dumps({'uid':os.getuid(),'tty':False,'signed_steps':steps,'negative_pass':negative}))
assert answered
'''
def run_scenario(scenario):
 t=T/scenario;t.mkdir(mode=0o700);os.chown(t,999,984)
 grant_path=GR/(scenario+'.json');g=json.loads(grant_path.read_text());v=env(t)
 setup=spawn(999,984,[PY,'-B','-I','-c',SETUP,str(S),str(H),str(t),scenario,str(grant_path)],v)
 out,err=setup.communicate(timeout=60);(E/(scenario+'-setup.stderr')).write_bytes(err);assert setup.returncode==0,'setup failed'
 spec=E/(scenario+'-operation.json'); (t/'operation.json').write_bytes(spec.read_bytes());os.chown(t/'operation.json',999,984)
 h=H
 if scenario=='delivered':
  packet=json.loads((H.parent/'RESIDENT_SAFE_LAUNCH_PACKET.json').read_text()); vv=env(t);vv['ARTIFACT']=str(H.parent/'artifacts/resident-harness.tar.gz');vv['DELIVERY_DIR']=str(t/'delivery')
  p=spawn(999,984,['bash','-c',packet['cross_sandbox_harness_materialization']['materialization_command']],vv)
  out,err=p.communicate(timeout=30);(E/'delivered-materialize.stderr').write_bytes(err);assert p.returncode==0,'materialize failed';h=t/'delivery/harness'
 pin=hashlib.sha256((h/'IDENTITY.json').read_bytes()).hexdigest();v['AIOS66_TEST_ENROLLMENT']=str(grant_path)
 runner=spawn(999,984,[PY,'-B','-I',str(h/'launch.py'),'--source-repo',str(S),'--identity-sha256',pin,'run','--root',str(t/'synthetic-root'),'--run-id',g['run_id'],'--session-id',g['session_id'],'--operation',str(t/'operation.json'),'--persistence-repo',str(t/'git')],v)
 signer=None
 try:
  deadline=time.monotonic()+35;endpoint_file=t/'synthetic-root/mailbox/operations'/g['operation_ids'][0]/'signed-endpoint.json'
  while not endpoint_file.exists() and runner.poll() is None and time.monotonic()<deadline:time.sleep(.05)
  assert endpoint_file.exists(),'Publisher did not become ready'
  endpoint=json.loads(endpoint_file.read_text())['socket']
  signer=spawn(996,983,[PY,'-B','-I','-c',SIGNER,endpoint,scenario],env(t))
  out,err=runner.communicate(timeout=90);(E/(scenario+'-runner.stdout')).write_bytes(out);(E/(scenario+'-runner.stderr')).write_bytes(err);assert runner.returncode==0,'Runner failed'
  sout,serr=signer.communicate(timeout=12);(E/(scenario+'-signer.stderr')).write_bytes(serr);assert signer.returncode==0,'Signer failed'
  signed=json.loads(sout);assert signed['signed_steps']
  exchange=endpoint_file.parent;proofs=[json.loads(p.read_text()) for p in (exchange/'proofs').glob('*.json')]
  assert all(p['resident_authorization_sha256'] for p in proofs)
  db=sqlite3.connect(t/'synthetic-root/state/runtime/world.sqlite');receipts=db.execute('SELECT COUNT(*) FROM background_model_response_receipts').fetchone()[0];db.close()
  core_proofs=sum(p['core_proof'] is not None for p in proofs);assert core_proofs>0 and receipts==core_proofs
  marker=json.loads((exchange/'operation.json').read_text());assert marker['state']=='completed';remote_commit=marker['remote_commit']
  ref=sp.check_output(['git','--git-dir',str(t/'remote.git'),'rev-parse','refs/heads/persistence/'+g['run_id']],text=True).strip();assert ref==remote_commit
  if scenario=='summary':assert any(p['kind']=='round_summary' for p in signed['signed_steps'])
  return {'scenario':scenario,'status':'PASS','no_controlling_tty':True,'core_receipts':receipts,'core_proofs':core_proofs,'remote_commit':remote_commit,'signer':signed}
 finally:
  if runner.poll() is None:runner.terminate()
  out,err=runner.communicate(timeout=8);(E/(scenario+'-runner.stderr')).write_bytes(err);(E/(scenario+'-runner.stdout')).write_bytes(out)
  if signer is not None:
   if signer.poll() is None:signer.terminate()
   sout,serr=signer.communicate(timeout=8);(E/(scenario+'-signer.stderr')).write_bytes(serr);(E/(scenario+'-signer.stdout')).write_bytes(sout)
compile(SETUP,'setup','exec');compile(SIGNER,'signer','exec')
T.mkdir(mode=0o755);T.chmod(0o755)
results=[]
for scenario in ['user','due','summary','delivered']:
 try:result=run_scenario(scenario)
 except Exception as exc:result={'scenario':scenario,'status':'FAIL','error_type':type(exc).__name__,'reason':str(exc)}
 results.append(result);(E/'mechanical-results.json').write_text(json.dumps(results,indent=2));print(scenario,result['status'],result.get('reason',''),flush=True)
sys.exit(0 if all(r['status']=='PASS' for r in results) else 1)
