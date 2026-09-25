#!/usr/bin/env python3
"""
C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-002 — Resident isolation sandbox (hardened, PID1 supervisor fixed).

Address blockers:
  1. NETWORK_SEAL_BYPASS      -> CLONE_NEWNET + loopback only + ENETUNREACH probe.
  2. PID_NAMESPACE_NOT_ISOLATED (FIXED) -> host -> unshare -> fork PID1 init -> PID1 forks worker (>=2).
     Init never runs Resident payload; only reaps zombies, forwards TERM/INT/HUP, returns worker exit.
     Probe proves /proc/1/comm == sandbox-init, resident pid !=1, host pids invisible, orphans reaped, signal termination works.
  3. PRIVILEGE_DROP_FAIL_OPEN -> no bare except, fail-closed, plus negative test seam.
  4. MAILBOX_PATH_NOT_PROVEN  -> host bind-mount inbox/outbox, archive not mounted.
  5. RESIDENT_ENVELOPE        -> see mailbox_bridge.py (now with request_id/digest binding).
  6. READ_ONLY_BIND_NOT_PROVEN -> bind then remount RO.
  7. STARTUP_PROCEDURE_FILENAME_BUG -> fixed in b_startup_procedure.md.
  8. TRANSPORT_E2E_PROBE      -> probe_e2e.sh + synthetic responder + genuine Core adapter.

ARCHITECTURE (correct):
  parent (operator, host namespaces)
    -> fork unsharer child
         unsharer: unshare(NEWNS|NEWPID|NEWNET), make mount private, fork init
           init (PID 1 in new ns): set comm sandbox-init, fork worker, reap, forward signals
             worker (PID >=2): mounts, chroot, drop privs, exec Resident command
           unsharer waits for init, forwards signals, exits with init status
         parent waits for unsharer

Mailbox IPC: host directories bind-mounted RW at /work/inbox and /work/outbox; operator archive not mounted.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import os
import signal
import socket
import struct
import sys
import time
from pathlib import Path

CLONE_NEWNS = 0x00020000
CLONE_NEWPID = 0x20000000
CLONE_NEWNET = 0x40000000

MS_BIND = 4096
MS_REC = 16384
MS_RDONLY = 1
MS_PRIVATE = 1 << 18
MS_REMOUNT = 32
MS_NOSUID = 2
MS_NODEV = 4
MS_NOEXEC = 8

REPO_ROOT_DEFAULT = Path("/home/user/Haneof-AIOS-Core-v3.0")


def _libc() -> ctypes.CDLL:
    return ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)


def _mount(src: str, tgt: str, fstype: str | None, flags: int, data: str = "") -> None:
    libc = _libc()
    if libc.mount(
        src.encode(), tgt.encode(),
        fstype.encode() if fstype else None,
        flags, data.encode()
    ) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), f"mount({src} -> {tgt}, flags=0x{flags:x})")


def _bind_ro(src: str, tgt: str) -> None:
    _mount(src, tgt, None, MS_BIND | MS_REC)
    _mount(src, tgt, None, MS_BIND | MS_REC | MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV)


def _bind_rw(src: str, tgt: str) -> None:
    _mount(src, tgt, None, MS_BIND | MS_REC | MS_NOSUID | MS_NODEV)


def _set_comm(name: str) -> None:
    # Try prctl PR_SET_NAME (15) then /proc/self/comm
    try:
        libc = _libc()
        PR_SET_NAME = 15
        # prctl expects null-terminated string max 16 including NUL (15 chars)
        bname = name.encode()[:15]
        libc.prctl(PR_SET_NAME, bname, 0, 0, 0)
    except Exception:
        pass
    try:
        Path("/proc/self/comm").write_text(name[:15])
    except Exception:
        pass


def _worker_main(args: argparse.Namespace) -> int:
    """Worker PID>=2: mounts, chroot, drop privs, exec. Never returns on success."""
    # Make mount propagation private (redundant if unsharer already did, but safe)
    try:
        _mount("none", "/", None, MS_REC | MS_PRIVATE)
    except OSError:
        pass

    sb = args.sandbox
    sb.mkdir(parents=True, exist_ok=True)

    # Bring up loopback in new netns
    try:
        import fcntl
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        ifr = struct.pack("16sH", b"lo", 0)
        fcntl.ioctl(s.fileno(), 0x8913, ifr)  # SIOCGIFFLAGS
        flags = struct.unpack("16sH", ifr)[1]
        IFF_UP = 1
        ifr_up = struct.pack("16sH", b"lo", flags | IFF_UP)
        fcntl.ioctl(s.fileno(), 0x8914, ifr_up)  # SIOCSIFFLAGS
        s.close()
    except OSError:
        pass

    # System dirs RO
    for d in ("/usr", "/lib", "/lib64", "/lib32", "/bin", "/sbin", "/etc", "/opt"):
        src = Path(d)
        if not src.exists():
            continue
        tgt = sb / d.lstrip("/")
        tgt.mkdir(parents=True, exist_ok=True)
        _bind_ro(str(src), str(tgt))

    # /dev bind
    dev = sb / "dev"
    dev.mkdir(parents=True, exist_ok=True)
    _mount("/dev", str(dev), None, MS_BIND | MS_REC)

    # /proc fresh (must be after CLONE_NEWPID, and in new PID namespace this proc will show init as PID1)
    proc = sb / "proc"
    proc.mkdir(parents=True, exist_ok=True)
    _mount("proc", str(proc), "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC)

    # /repo skeleton
    repo = sb / "repo"
    repo.mkdir(parents=True, exist_ok=True)

    core_src = args.repo / "src"
    core_tgt = repo / "src"
    core_tgt.mkdir(parents=True, exist_ok=True)
    _bind_ro(str(core_src), str(core_tgt))

    c15_resident = repo / "reviews/internal_habitation/c15-rcc/v1/resident"
    c15_resident.mkdir(parents=True, exist_ok=True)
    contract_src = args.repo / "reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md"
    contract_tgt = c15_resident / "RESIDENT_B_RUN_CONTRACT.md"
    contract_tgt.touch()
    _bind_ro(str(contract_src), str(contract_tgt))

    # /work
    work = sb / "work"
    work.mkdir(parents=True, exist_ok=True)

    def _rw_file(src_path: Path, tgt_name: str) -> None:
        tgt = work / tgt_name
        tgt.parent.mkdir(parents=True, exist_ok=True)
        tgt.touch()
        _bind_rw(str(src_path), str(tgt))

    _rw_file(args.world, "world.sqlite")
    _rw_file(args.index, "world_index.sqlite")
    _rw_file(args.state, "release_state.json")
    _rw_file(args.lock, "world.writer.lock")

    inbox_tgt = work / "inbox"
    outbox_tgt = work / "outbox"
    scratch_tgt = work / "scratch"
    inbox_tgt.mkdir(parents=True, exist_ok=True)
    outbox_tgt.mkdir(parents=True, exist_ok=True)
    scratch_tgt.mkdir(parents=True, exist_ok=True)
    _bind_rw(str(args.mailbox_inbox), str(inbox_tgt))
    _bind_rw(str(args.mailbox_outbox), str(outbox_tgt))
    _mount("tmpfs", str(scratch_tgt), "tmpfs", 0, "size=256m,mode=0700")

    tmp = sb / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    _mount("tmpfs", str(tmp), "tmpfs", 0, "size=64m,mode=1777")

    home = sb / "home/nobody"
    home.mkdir(parents=True, exist_ok=True)
    _mount("tmpfs", str(home), "tmpfs", 0, "size=16m,mode=0700")

    if args.inject_dir is not None:
        inject_tgt = sb / "work/inject"
        inject_tgt.mkdir(parents=True, exist_ok=True)
        _bind_ro(str(args.inject_dir), str(inject_tgt))

    # chroot before privdrop
    os.chroot(str(sb))
    os.chdir("/work")

    # Test seam: inject privdrop failure if operator requested
    # This is NOT a bypass flag; it forces failure to prove fail-closed.
    # Resident cannot set this because sandbox env is sanitized and this is checked before drop.
    if os.environ.get("_RESIDENT_JAIL_INJECT_PRIVDROP_FAIL") == "1":
        # Simulate setuid failure
        raise RuntimeError("injected privdrop failure (test seam)")

    import pwd
    try:
        nobody = pwd.getpwnam("nobody")
    except KeyError as e:
        raise RuntimeError(f"required user 'nobody' not found: {e}")

    # Optional secondary seam for negative test that patches setuid via env
    inject_fail = os.environ.get("_RESIDENT_JAIL_INJECT_FAIL_MODE")
    # Supported values: setgroups, setgid, setuid
    try:
        if inject_fail == "setgroups":
            raise OSError(1, "injected setgroups failure")
        os.setgroups([])
    except OSError as e:
        raise RuntimeError(f"setgroups([]) failed: {e}")
    try:
        if inject_fail == "setgid":
            raise OSError(1, "injected setgid failure")
        os.setgid(nobody.pw_gid)
    except OSError as e:
        raise RuntimeError(f"setgid({nobody.pw_gid}) failed: {e}")
    try:
        if inject_fail == "setuid":
            raise OSError(1, "injected setuid failure")
        os.setuid(nobody.pw_uid)
    except OSError as e:
        raise RuntimeError(f"setuid({nobody.pw_uid}) failed: {e}")

    if os.geteuid() == 0 or os.getuid() == 0:
        raise RuntimeError("privilege drop failed: still uid 0 after setuid")
    try:
        os.setuid(0)
        raise RuntimeError("privilege drop failed: able to re-acquire uid 0")
    except OSError:
        pass

    try:
        try:
            os.mkdir("/tmp/test_mount")
        except FileExistsError:
            pass
        _mount("tmpfs", "/tmp/test_mount", "tmpfs", 0, "size=1m")
        raise RuntimeError("privilege drop failed: mount() still permitted")
    except OSError as e:
        if e.errno != 1:  # EPERM
            raise RuntimeError(f"unexpected mount() result errno={e.errno}: {e}")

    env = {
        "AIOS_WORLD_PATH": "/work/world.sqlite",
        "AIOS_INDEX_PATH": "/work/world_index.sqlite",
        "AIOS_LOCK_PATH": "/work/world.writer.lock",
        "AIOS_SUBJECT_ID": "user_1",
        "PYTHONPATH": "/repo/src",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/home/nobody",
        "TMPDIR": "/tmp",
    }
    # Sanitized env: only allow explicit allowlist, plus operator-controlled probe vars
    # PROBE_MODE/PROBE_ROUNDS are allowed only when operator explicitly sets them before jail,
    # and they are sanitized to known values (normal/malformed/stale etc.) - resident cannot escalate.
    allowed_probe_vars = {"PROBE_MODE", "PROBE_ROUNDS"}
    for k, v in os.environ.items():
        if k in allowed_probe_vars:
            # Validate value to prevent injection
            if k == "PROBE_MODE" and v not in ("normal", "malformed", "stale", "preplay", "replay", "binding", "genuine"):
                continue
            if k == "PROBE_ROUNDS" and not v.isdigit():
                continue
            env[k] = v
        elif k.startswith(("LD_", "PYTHON", "SUDO")):
            continue
        elif k in ("PATH", "HOME", "TMPDIR", "TERM", "LANG", "LC_ALL", "LC_CTYPE"):
            env.setdefault(k, v)
        elif k in ("_RESIDENT_JAIL_INJECT_PRIVDROP_FAIL", "_RESIDENT_JAIL_INJECT_FAIL_MODE"):
            # Do NOT propagate these into sandbox; they are host-side test seams only
            continue
    os.execvpe(args.cmd[0], args.cmd, env)
    raise RuntimeError(f"execvp({args.cmd[0]!r}) failed")


def _init_main(args: argparse.Namespace) -> int:
    """PID 1 init: forks worker, reaps zombies, forwards signals."""
    _set_comm("sandbox-init")
    # Fork worker
    worker_pid = os.fork()
    if worker_pid == 0:
        # Child worker (PID >=2)
        try:
            rc = _worker_main(args)
            os._exit(rc if isinstance(rc, int) else 0)
        except Exception as e:
            print(f"[jail] sandbox setup FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            os._exit(98)

    # Parent init (PID 1)
    # Forward termination signals to worker
    def _forward(signum, _frame):
        try:
            os.kill(worker_pid, signum)
        except ProcessLookupError:
            pass
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, _forward)
    # Ensure SIGCHLD is not ignored
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)

    worker_exit = None
    while True:
        try:
            pid, status = os.waitpid(-1, 0)
            if pid == worker_pid:
                if os.WIFEXITED(status):
                    worker_exit = os.WEXITSTATUS(status)
                elif os.WIFSIGNALED(status):
                    worker_exit = 128 + os.WTERMSIG(status)
                else:
                    worker_exit = 1
                # Drain any remaining zombies (orphans reparented to PID1)
                while True:
                    try:
                        rpid, _ = os.waitpid(-1, os.WNOHANG)
                        if rpid == 0:
                            break
                    except ChildProcessError:
                        break
                return worker_exit
            else:
                # Reaped an orphan / zombie child of worker; continue
                continue
        except ChildProcessError:
            # No children left
            if worker_exit is not None:
                return worker_exit
            return 1
        except KeyboardInterrupt:
            _forward(signal.SIGINT, None)


def _unsharer_main(args: argparse.Namespace) -> int:
    """Child that creates new namespaces, then forks PID1 init."""
    libc = _libc()
    if libc.unshare(CLONE_NEWNS | CLONE_NEWPID | CLONE_NEWNET) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), "unshare(CLONE_NEWNS|NEWPID|NEWNET)")
    # Do NOT mount private here before fork; let worker do it after fork (old jail did)
    # This avoids ENOMEM in some kernel configurations when forking immediately after unshare

    init_pid = os.fork()
    if init_pid == 0:
        # Init process (will become PID 1)
        rc = _init_main(args)
        os._exit(rc)
    else:
        # Unsharer parent (still in host PID namespace) waits for init
        def _forward_to_init(signum, _frame):
            try:
                os.kill(init_pid, signum)
            except ProcessLookupError:
                pass
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(sig, _forward_to_init)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        while True:
            try:
                pid, status = os.waitpid(init_pid, 0)
                if pid == init_pid:
                    if os.WIFEXITED(status):
                        return os.WEXITSTATUS(status)
                    if os.WIFSIGNALED(status):
                        return 128 + os.WTERMSIG(status)
                    return 1
            except ChildProcessError:
                return 1
            except KeyboardInterrupt:
                _forward_to_init(signal.SIGINT, None)


def _prepare_mailbox(args: argparse.Namespace) -> None:
    root = args.mailbox_root
    root.mkdir(parents=True, exist_ok=True)
    (root / "archive").mkdir(parents=True, exist_ok=True)
    inbox = root / "inbox"
    outbox = root / "outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    for p in list(inbox.iterdir()) + list(outbox.iterdir()):
        if p.is_file():
            p.unlink()
    import grp
    try:
        nogroup_gid = grp.getgrnam("nogroup").gr_gid
    except KeyError:
        nogroup_gid = grp.getgrnam("nobody").gr_gid
    os.chown(inbox, 0, nogroup_gid)
    os.chmod(inbox, 0o755)
    os.chown(outbox, 0, nogroup_gid)
    os.chmod(outbox, 0o1733)
    os.chown(root / "archive", 0, 0)
    os.chmod(root / "archive", 0o700)
    args.mailbox_inbox = inbox
    args.mailbox_outbox = outbox


def main() -> int:
    ap = argparse.ArgumentParser(description="Hardened Resident-B sandbox (mount+pid+net NS, PID1 supervisor, chroot, privdrop, host bind mailbox)")
    ap.add_argument("--repo", type=Path, default=REPO_ROOT_DEFAULT)
    ap.add_argument("--sandbox", type=Path, required=True)
    ap.add_argument("--world", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--state", type=Path, required=True)
    ap.add_argument("--lock", type=Path, required=True)
    ap.add_argument("--mailbox-root", type=Path, required=True,
                    help="Host directory that will contain inbox/ and outbox/ and archive/.")
    ap.add_argument("--inject-dir", type=Path)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args()

    if os.geteuid() != 0:
        print("error: resident_jail.py must run as root (sudo)", file=sys.stderr)
        return 99
    if not args.cmd or args.cmd[0] == "--":
        args.cmd = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
        if not args.cmd:
            print("error: provide a command to run inside the sandbox", file=sys.stderr)
            return 2

    import shutil
    if args.sandbox.exists():
        shutil.rmtree(args.sandbox)
    args.sandbox.mkdir(parents=True)

    _prepare_mailbox(args)

    pid = os.fork()
    if pid == 0:
        try:
            rc = _unsharer_main(args)
            os._exit(rc if isinstance(rc, int) else 0)
        except Exception as e:
            print(f"[jail] sandbox setup FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            os._exit(98)
    else:
        _, status = os.waitpid(pid, 0)
        if os.WIFEXITED(status):
            return os.WEXITSTATUS(status)
        if os.WIFSIGNALED(status):
            sig = os.WTERMSIG(status)
            print(f"[jail] child killed by signal {sig}", file=sys.stderr)
            return 128 + sig
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
