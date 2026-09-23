"""Synthetic canary boundary probe, NOT Resident/Arena isolation attestation.

Every negative file check requires an independently readable, content-verified
synthetic canary outside the boundary, checked before AND after the child. Real
credentials, private A and sealed future files are never inspected. Their status
is NOT_TESTED. A readable allowed packet is an explicit positive control.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

LABELS = ("pm", "operator", "git_metadata", "private_a", "sealed_future",
          "git_credentials", "gh_credentials")
CONTROL_NAMES = ("allowed_readable", "no_host_proc", "no_git_or_gh", "clean_environment",
                 "chroot_capability_removed", "external_network_denied", "packet_readonly")

PROBE = r'''
import hashlib,json,os,socket,sys
request=json.loads(sys.stdin.read())
denied={};controls={}
try:
 data=open('/packet/request.json','rb').read()
 controls['allowed_readable']=hashlib.sha256(data).hexdigest()==request['allowed_sha256']
except OSError: controls['allowed_readable']=False
for label,path in request['canaries'].items():
 try:
  fd=os.open(path,os.O_RDONLY);os.close(fd)
 except (FileNotFoundError,PermissionError,NotADirectoryError): denied[label]=True
 else: denied[label]=False
controls['no_host_proc']=not os.path.exists('/proc/1/root')
controls['no_git_or_gh']=not any(os.path.exists(p) for p in ['/usr/bin/git','/usr/bin/gh','/bin/sh'])
controls['clean_environment']=not any('TOKEN' in k or 'KEY' in k or 'GITHUB' in k for k in os.environ)
try: os.chroot('/')
except PermissionError: controls['chroot_capability_removed']=True
else: controls['chroot_capability_removed']=False
try:
 with socket.create_connection(('192.0.2.1',443),timeout=1): pass
except OSError: controls['external_network_denied']=True
else: controls['external_network_denied']=False
try: open('/packet/request.json','w')
except OSError: controls['packet_readonly']=True
else: controls['packet_readonly']=False
print(json.dumps({'denied':denied,'controls':controls}))
'''


def create_canaries(base: Path):
    """Generate only disposable synthetic bytes, never read a protected real file."""
    directory = base / "protected-canaries"
    directory.mkdir(mode=0o700)
    paths, hashes = {}, {}
    for label in LABELS:
        path = directory / label
        data = b"SYNTHETIC CANARY ONLY\n" + os.urandom(32).hex().encode()
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        paths[label] = path
        hashes[label] = hashlib.sha256(data).hexdigest()
    return paths, hashes


def outside_checks(paths, expected_hashes):
    """A missing, unreadable, symlinked or changed canary is NOT a proven premise."""
    result = {}
    for label in LABELS:
        try:
            path = paths[label]
            ok = (not path.is_symlink() and path.is_file()
                  and hashlib.sha256(path.read_bytes()).hexdigest() == expected_hashes[label])
        except (OSError, KeyError):
            ok = False
        result[label] = "VERIFIED" if ok else "NOT_TESTED"
    return result


def assess(before, child, after):
    """Denial is evidence only WITH both host premises and positive control."""
    controls = child.get("controls", {})
    denied = child.get("denied", {})
    checks = {}
    for label in LABELS:
        if before.get(label) != "VERIFIED" or after.get(label) != "VERIFIED":
            status = "NOT_TESTED"
        elif controls.get("allowed_readable") is not True or type(denied.get(label)) is not bool:
            status = "INCONCLUSIVE"
        else:
            status = "PASS" if denied[label] else "FAIL"
        checks[label] = {"outside_before": before.get(label, "NOT_TESTED"),
                         "outside_after": after.get(label, "NOT_TESTED"), "status": status}
    if any(v["status"] == "FAIL" for v in checks.values()) or any(controls.get(k) is False for k in CONTROL_NAMES):
        overall = "FAIL"
    elif all(v["status"] == "PASS" for v in checks.values()) and all(controls.get(k) is True for k in CONTROL_NAMES):
        overall = "PASS"
    else:
        overall = "INCONCLUSIVE"
    return {"synthetic_boundary_status": overall, "canaries": checks, "controls": controls,
            "real_resources": {label: "NOT_TESTED" for label in LABELS},
            "resident_arena_isolation": "BLOCKED", "launchable": False}


def probe(repo: Path | None = None, private_a: Path | None = None) -> dict:
    # Deprecated positional arguments are deliberately NOT dereferenced. All
    # resources used for this proof are generated in this private temporary dir.
    with tempfile.TemporaryDirectory(prefix="c15-isolation-") as tmp:
        base = Path(tmp); root = base / "root"; root.mkdir()
        paths, hashes = create_canaries(base)
        before = outside_checks(paths, hashes)
        if any(v != "VERIFIED" for v in before.values()):
            return assess(before, {}, outside_checks(paths, hashes))
        packet = base / "packet"; packet.mkdir()
        allowed = packet / "request.json"
        allowed.write_text(json.dumps({"synthetic": True, "nonce": os.urandom(16).hex()}))
        allowed_sha256 = hashlib.sha256(allowed.read_bytes()).hexdigest()
        script = base / "probe.py"; script.write_text(PROBE)
        # Try to find a suitable interpreter: prefer python3.11 if exists, else python3, else current
        interpreter_candidates = [Path('/usr/bin/python3.11'), Path('/usr/bin/python3'), Path('/usr/bin/python3.12'), Path('/usr/bin/python3.10')]
        interpreter = None
        for cand in interpreter_candidates:
            if cand.is_file() and not cand.is_symlink():
                interpreter = cand
                break
        if interpreter is None:
            # No interpreter found, treat as env unsupported -> INCONCLUSIVE via RuntimeError
            raise RuntimeError("isolation probe INCONCLUSIVE: no suitable python interpreter found")
        setpriv = Path('/usr/bin/setpriv')
        if not setpriv.is_file():
            raise RuntimeError("isolation probe INCONCLUSIVE: setpriv not found")
        # Build mount list, handling ldd failures gracefully
        mounts = {str(interpreter): str(interpreter), str(setpriv): str(setpriv),
                  str(packet): '/packet', str(script): '/probe.py'}
        # Try to include lib dir for interpreter if exists
        for lib_dir in [f'/usr/lib/{interpreter.name}', '/usr/lib/python3.11', '/usr/lib/python3.12', '/usr/lib/python3.10', '/usr/lib/python3']:
            if Path(lib_dir).is_dir():
                mounts[lib_dir] = lib_dir
        for binary in (interpreter, setpriv):
            try:
                output = subprocess.check_output(['ldd', str(binary)], text=True, stderr=subprocess.DEVNULL)
            except (FileNotFoundError, PermissionError, OSError, subprocess.SubprocessError) as e:
                # ldd not available or binary not found -> env unsupported
                raise RuntimeError(f"isolation probe INCONCLUSIVE: ldd failed for {binary}: {e}") from e
            for token in output.split():
                if token.startswith('/'):
                    # Only include if file exists
                    if Path(token).exists():
                        mounts[token] = token
        import shlex
        q = shlex.quote
        script_lines = ['set -eu', 'mount --make-rprivate /']
        for source, target in mounts.items():
            dst = root / target.lstrip('/')
            try:
                if Path(source).is_dir():
                    dst.mkdir(parents=True, exist_ok=True)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True); dst.touch()
                script_lines += [f'mount --bind {q(source)} {q(str(dst))}',
                                 f'mount -o remount,bind,ro,nosuid,nodev {q(str(dst))}']
            except OSError as e:
                raise RuntimeError(f"isolation probe INCONCLUSIVE: mount setup failed {source}: {e}") from e
        script_lines += [f'cd {q(str(root))}',
            f'exec /usr/sbin/chroot {q(str(root))} /usr/bin/setpriv --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all {q(str(interpreter))} -I -B /probe.py']
        request = {"canaries": {k: str(v) for k, v in paths.items()}, "allowed_sha256": allowed_sha256}
        try:
            result = subprocess.run(['unshare', '--user', '--map-root-user', '--mount', '--net', '--pid', '--fork',
                                     '/bin/sh', '-c', '\n'.join(script_lines)], input=json.dumps(request),
                                    text=True, capture_output=True, timeout=20, close_fds=True,
                                    env={'PATH': '/usr/sbin:/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        except (FileNotFoundError, PermissionError, OSError) as e:
            raise RuntimeError(f"isolation probe INCONCLUSIVE: unshare failed: {e}") from e
        if result.returncode:
            raise RuntimeError(f"isolation probe INCONCLUSIVE ({result.returncode}): {result.stderr.strip()}")
        try:
            report = assess(before, json.loads(result.stdout), outside_checks(paths, hashes))
        except Exception as e:
            raise RuntimeError(f"isolation probe INCONCLUSIVE: output parse failed: {e}") from e
        return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, help='deprecated; no real repository file is opened')
    parser.add_argument('--private-a', type=Path, help='deprecated; no private A file is opened')
    args = parser.parse_args()
    result = probe(args.repo, args.private_a)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['synthetic_boundary_status'] == 'PASS' else 2)
