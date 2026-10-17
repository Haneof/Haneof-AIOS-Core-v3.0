import os,socket,struct,json,platform,hashlib,pathlib,subprocess,time
r={'host':platform.node(),'uid':os.getuid(),'pid':os.getpid(),'sid':os.getsid(0),'stdin_isatty':os.isatty(0),'utc_epoch':int(time.time())}
try:fd=os.open('/dev/tty',os.O_RDWR);os.close(fd);r['controlling_tty']=True
except OSError as x:r['controlling_tty']=False;r['tty_errno']=x.errno
a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM);r['peercred']=struct.unpack('3i',b.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12));a.sendall(b'probe');r['AF_UNIX']=b.recv(5)==b'probe';a.close();b.close()
fd=os.pidfd_open(os.getpid());r['pidfd']=fd>=0;os.close(fd)
t=pathlib.Path('/var/lib/aios-window65/trust');r['trust_public']={}
for n in ['issuer.pub','resident.pub']:
 p=t/n;s=p.stat();q=subprocess.run(['/usr/bin/openssl','pkey','-pubin','-outform','DER','-in',str(p)],capture_output=True);r['trust_public'][n]={'uid':s.st_uid,'gid':s.st_gid,'mode':oct(s.st_mode&0o777),'der_sha256':hashlib.sha256(q.stdout).hexdigest(),'openssl_exit':q.returncode}
print(json.dumps(r,indent=2))
assert r['AF_UNIX'] and r['pidfd'] and not r['controlling_tty']
assert r['trust_public']['issuer.pub']['der_sha256']=='1124f54a497c9dfa5fcc6e16fb9fc570816fadba6f32016a8b53d5f0243090dd'
assert r['trust_public']['resident.pub']['der_sha256']=='838a1a7d168ac6dd8441c0c8a2deab439a7b775d6583c40618a51f627e6e3b7f'
