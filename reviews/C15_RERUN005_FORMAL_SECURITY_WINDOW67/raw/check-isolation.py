import os,pwd,pathlib,subprocess as sp,json,hashlib,stat
E=pathlib.Path('/workspaces/window67-evidence-20261016T2053Z');R=[]
assert os.getuid()==0
for uid in (999,996):
 p=pwd.getpwuid(uid)
 code="import os,json; r={'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups()}; paths="+repr(['/var/lib/aios-window65/operator','/var/lib/aios-window65/'+('AIOS_RESIDENT_TEST' if uid==999 else 'AIOS_RUNNER_TEST')])+";\nfor p in paths:\n try:f=os.open(p,os.O_RDONLY|os.O_DIRECTORY);os.close(f);r[p]='ACCESSIBLE'\n except PermissionError:r[p]='DENIED'\nprint(json.dumps(r))"
 def drop(p=p):os.setgroups([]);os.setgid(p.pw_gid);os.setuid(p.pw_uid)
 q=sp.run([os.environ.get('PY67','/usr/bin/python3'),'-c',code],capture_output=True,text=True,preexec_fn=drop);r={'uid_requested':uid,'argv_code':code,'returncode':q.returncode,'stdout':q.stdout,'stderr':q.stderr}
 q=sp.run(['sudo','-n','true'],capture_output=True,text=True,preexec_fn=drop);r['sudo_returncode']=q.returncode;r['sudo_stderr']=q.stderr;R.append(r)
# Metadata only for protected paths. No private bytes are opened.
M=[]
for root in ['operator','AIOS_RUNNER_TEST','AIOS_RESIDENT_TEST']:
 for p in (pathlib.Path('/var/lib/aios-window65')/root).rglob('*'):
  st=p.lstat();M.append({'path':str(p),'uid':st.st_uid,'gid':st.st_gid,'mode':oct(stat.S_IMODE(st.st_mode)),'type':'dir' if p.is_dir() else 'file'})
(E/'isolation-current.json').write_text(json.dumps({'probes':R,'protected_metadata_only':M},indent=2));print(json.dumps(R,indent=2))
