"""Required Linux facilities only. Exit 78 means ENVIRONMENT_GATE_PENDING."""
import json
import os
from pathlib import Path
import select
import socket
import struct
import subprocess
import sys

results = {}
try:
    listener = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    listener.close()
    results['AF_UNIX_LISTENER_CREATION'] = {'status':'PASS'}
except Exception as error:
    results['AF_UNIX_LISTENER_CREATION'] = {'status':'ENVIRONMENT_BLOCKED','error':repr(error)}
try:
    left,right = socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
    try:
        peer = struct.unpack('3i',left.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        assert peer == (os.getpid(),os.getuid(),os.getgid()),peer
        results['AF_UNIX_SO_PEERCRED'] = {'status':'PASS','peer':list(peer)}
    finally:left.close();right.close()
except Exception as error:
    results['AF_UNIX_SO_PEERCRED'] = {'status':'ENVIRONMENT_BLOCKED','error':repr(error)}

child = subprocess.Popen([sys.executable,'-I','-c','import sys;print("ready",flush=True);sys.stdin.read()'],
                         stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
try:
    assert child.stdout.readline().strip() == 'ready'
    raw = Path(f'/proc/{child.pid}/stat').read_text()
    assert raw.split(' ',1)[0] == str(child.pid),raw
    assert raw[raw.rfind(')')+1:].split()[1] == str(os.getpid()),raw
    pidfd = os.pidfd_open(child.pid)
    try:
        poll = select.poll();poll.register(pidfd,select.POLLIN)
        assert not poll.poll(0)
        child.kill();child.wait(timeout=5)
        assert poll.poll(1000)
        results['PROC_PID_START_AND_PIDFD'] = {'status':'PASS','child_pid':child.pid}
    finally:os.close(pidfd)
except Exception as error:
    results['PROC_PID_START_AND_PIDFD'] = {'status':'ENVIRONMENT_BLOCKED','error':repr(error)}
finally:
    if child.poll() is None:child.kill()
    child.wait(timeout=5)
print(json.dumps(results,sort_keys=True,indent=2))
raise SystemExit(0 if all(v['status']=='PASS' for v in results.values()) else 78)
