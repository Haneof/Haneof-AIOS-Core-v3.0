"""Synthetic Linux boundary probe, NOT a Resident runner or isolation attestation.

Build an allowlisted minimal root in a disposable private directory. Child has a
new user/mount/network/PID namespace, no capabilities, no-new-privileges, no proc,
no Git/gh/shell, no credentials/environment, read-only interpreter/packet mounts.
Only a synthetic probe is executed. Actual Arena tool permissions remain BLOCKED.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

PROBE = r'''
import json,os,socket,sys
paths=json.loads(sys.stdin.read())
checks={}
assert json.load(open('/packet/request.json'))=={'synthetic':True}
for label,path in paths.items():
 try:
  fd=os.open(path,os.O_RDONLY);os.close(fd)
 except (FileNotFoundError,PermissionError,NotADirectoryError): checks[label]=True
 else: checks[label]=False
checks['no_host_proc']=not os.path.exists('/proc/1/root')
checks['no_git_or_gh']=not any(os.path.exists(p) for p in ['/usr/bin/git','/usr/bin/gh','/bin/sh'])
checks['clean_environment']=not any('TOKEN' in k or 'KEY' in k or 'GITHUB' in k for k in os.environ)
try: os.chroot('/')
except PermissionError: checks['chroot_capability_removed']=True
else: checks['chroot_capability_removed']=False
try:
 with socket.create_connection(('192.0.2.1',443),timeout=1): pass
except OSError: checks['external_network_denied']=True
else: checks['external_network_denied']=False
try:
 open('/packet/request.json','w')
except OSError: checks['packet_readonly']=True
else: checks['packet_readonly']=False
print(json.dumps({'synthetic_probe_only':True,'checks':checks,'all_denied':all(checks.values())}))
sys.exit(0 if all(checks.values()) else 1)
'''


def probe(repo: Path, private_a: Path) -> dict:
    repo = repo.resolve()
    protected = {
        "pm": str(repo / "governance/C15_RCC_RES_B_CORRECTIVE_DECISION_2026-09-23.md"),
        "operator": str(repo / "tools/c15_preflight/driver.py"),
        "git_metadata": str(repo / ".git/HEAD"),
        "private_a": str(private_a / "private_world.sqlite"),
        "sealed_future": str(repo / "reviews/internal_habitation/c15-rcc/v1/fixture/sealed_fixture.json"),
        # Only attempt open/close inside the minimal root; never read credential bytes.
        "git_credentials": "/home/user/.git-credentials",
        "gh_credentials": "/home/user/.config/gh/hosts.yml",
    }
    with tempfile.TemporaryDirectory(prefix="c15-isolation-") as tmp:
        base=Path(tmp);root=base/'root';root.mkdir()
        packet=base/'packet';packet.mkdir();(packet/'request.json').write_text('{"synthetic":true}')
        script=base/'probe.py';script.write_text(PROBE)
        interpreter=Path('/usr/bin/python3.11')
        setpriv=Path('/usr/bin/setpriv')
        mounts={str(interpreter):str(interpreter),str(setpriv):str(setpriv),
                '/usr/lib/python3.11':'/usr/lib/python3.11',str(packet):'/packet',str(script):'/probe.py'}
        # Resolve ELF dependencies mechanically, never mount all of /usr or /home.
        for binary in (interpreter,setpriv):
            output=subprocess.check_output(['ldd',str(binary)],text=True)
            for token in output.split():
                if token.startswith('/'):
                    mounts[token]=token
        script_lines=['set -eu','mount --make-rprivate /']
        import shlex
        q=shlex.quote
        for source,target in mounts.items():
            dst=root/target.lstrip('/')
            if Path(source).is_dir():dst.mkdir(parents=True,exist_ok=True)
            else:dst.parent.mkdir(parents=True,exist_ok=True);dst.touch()
            script_lines += [f'mount --bind {q(source)} {q(str(dst))}',
                             f'mount -o remount,bind,ro,nosuid,nodev {q(str(dst))}']
        # No proc mount or cwd/fd from the host survives the exec/chroot boundary.
        script_lines += [f'cd {q(str(root))}',
            f'exec /usr/sbin/chroot {q(str(root))} /usr/bin/setpriv --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all /usr/bin/python3.11 -I -B /probe.py']
        result=subprocess.run(['unshare','--user','--map-root-user','--mount','--net','--pid','--fork',
                               '/bin/sh','-c','\n'.join(script_lines)],input=json.dumps(protected),
                              text=True,capture_output=True,timeout=20,close_fds=True,
                              env={'PATH':'/usr/sbin:/usr/bin:/bin','LANG':'C.UTF-8'})
        if result.returncode:
            raise RuntimeError(f"isolation probe failed ({result.returncode}): {result.stderr.strip()} {result.stdout.strip()}")
        return json.loads(result.stdout)


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--private-a',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(probe(args.repo,args.private_a),indent=2))
