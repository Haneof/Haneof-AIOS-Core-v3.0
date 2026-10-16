import os,sys,json,hashlib,pathlib,subprocess as sp,socket,struct,tempfile,signal,time,tarfile,stat
E=pathlib.Path(os.environ['W67']); S=E/'candidate'; H=S/os.environ['H67']; B=H.parent
R={}; commands=[]
def run(a,**kw):
 p=sp.run(a,capture_output=True,text=True,**kw); commands.append({'argv':a,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}); return p
def ck(n,f):
 try: R[n]={'status':'PASS','detail':f()}
 except Exception as e:R[n]={'status':'FAIL','detail':repr(e)}
def require(x):
 assert x
 return True
sha=lambda b:hashlib.sha256(b).hexdigest()
ck('python_version',lambda:require(sys.version_info[:3]==(3,12,14)))
ck('python_executable_hash',lambda:require(sha(pathlib.Path(sys.executable).resolve().read_bytes())==json.loads((H/'IDENTITY.json').read_text())['python_sha256']))
R['kernel']={'status':'PASS','detail':os.uname().release}
ck('pid_proc',lambda:require(int(pathlib.Path('/proc/self/stat').read_text().split()[0])==os.getpid()))
def pidfd():
 fd=os.pidfd_open(os.getpid());os.close(fd);return True
ck('pidfd',pidfd)
def ipc():
 with tempfile.TemporaryDirectory(prefix='w67-unix-') as d:
  with socket.socket(socket.AF_UNIX) as srv,socket.socket(socket.AF_UNIX) as cli:
   srv.bind(d+'/sock');srv.listen();cli.connect(d+'/sock');c,_=srv.accept()
   with c: peer=struct.unpack('3i',c.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12));assert peer==(os.getpid(),os.getuid(),os.getgid());return peer
ck('AF_UNIX_SO_PEERCRED',ipc)
def kill():
 p=sp.Popen([sys.executable,'-c','import time;time.sleep(600)']);os.kill(p.pid,signal.SIGKILL);return require(p.wait()==-signal.SIGKILL)
ck('disposable_SIGKILL',kill)
p=run([sys.executable,'-c',"import os,json; r={'pid':os.getpid(),'sid':os.getsid(0),'stdin_tty':os.isatty(0)};\ntry: os.open('/dev/tty',os.O_RDONLY);r['tty_open']=True\nexcept OSError:r['tty_open']=False\nprint(json.dumps(r))"],start_new_session=True)
ck('no_controlling_tty',lambda:require(p.returncode==0 and not json.loads(p.stdout)['tty_open']))
for uid in (999,996):
 p=run(['sudo','-n','-u','#'+str(uid),'id']); R['UID_'+str(uid)]={'status':'PASS' if p.returncode==0 else 'BLOCKED','detail':p.stdout.strip()}
 p=run(['sudo','-n','-u','#'+str(uid),'sudo','-n','true']);ck('UID_'+str(uid)+'_no_sudo',lambda p=p:require(p.returncode!=0))
# Inspect permissions and public anchors, never read any private key.
anchors={}
for p in [pathlib.Path('/var/lib/aios-window65/trust/issuer.pub'),pathlib.Path('/var/lib/aios-window65/trust/resident.pub')]:
 st=p.stat();anchors[str(p)]={'uid':st.st_uid,'gid':st.st_gid,'mode':oct(stat.S_IMODE(st.st_mode)),'sha256':sha(p.read_bytes())}
R['trust_anchor_metadata']={'status':'PASS','detail':anchors}
m=json.loads((H/'IDENTITY.json').read_text()); artifact=B/'artifacts/resident-harness.tar.gz'; packet=B/'RESIDENT_SAFE_LAUNCH_PACKET.json'
for n,p,expected in [('manifest',H/'IDENTITY.json','364cc03617fcd782327b3307720baf5371839185b1b07b71476308af74c5a817'),('artifact',artifact,'82aa3ff81d9492e0828934b5744adf4129fb6dc1361303a537379a603a319de3'),('packet',packet,'023c7556de1bcd4d4b0caccb90b0fa65d0b8a9b783f41f30574dfbb12e8f6b34')]:ck(n+'_sha256',lambda p=p,expected=expected:require(sha(p.read_bytes())==expected))
def members():
 expected={'harness/'+k for k in m['harness_files']}|{'harness/IDENTITY.json'}
 with tarfile.open(artifact) as tf:
  ms=tf.getmembers();assert len(ms)==len(expected) and {x.name for x in ms}==expected
  for x in ms:
   assert x.isfile() and x.mode==0o644 and tf.extractfile(x).read()==(H/pathlib.PurePosixPath(x.name).relative_to('harness')).read_bytes()
 return {'members':len(expected),'all_bytes_match_final_candidate':True}
ck('closed_archive_final_tree',members)
def source():
 bad=[]
 for k,v in m['source_files'].items():
  expected=v['sha256'] if isinstance(v,dict) else v
  if sha((S/k).read_bytes())!=expected:bad.append(k)
 assert not bad,bad
 return len(m['source_files'])
ck('core_c15_source_bytes',source)
changed=(E/'changed-paths.txt').read_text().splitlines()
ck('core_c15_unchanged',lambda:require(not any(x.startswith(('src/aios_core/','tools/c15_persistence/')) for x in changed)))
ck('approved_scope',lambda:require(all(x.startswith(('reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66/','reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/')) for x in changed)))
def evid():
 d=S/'reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66'; records=json.loads((d/'EVIDENCE_SHA256.json').read_text());bad=[]
 for k,v in records.items():
  expected=v['sha256'] if isinstance(v,dict) else v
  if sha((d/k).read_bytes())!=expected:bad.append(k)
 assert not bad,bad
 return len(records)
ck('author_evidence_hashes',evid)
(E/'preflight-results.json').write_text(json.dumps(R,indent=2));(E/'preflight-commands.json').write_text(json.dumps(commands,indent=2))
print(json.dumps({k:v['status'] for k,v in R.items()},indent=2))
