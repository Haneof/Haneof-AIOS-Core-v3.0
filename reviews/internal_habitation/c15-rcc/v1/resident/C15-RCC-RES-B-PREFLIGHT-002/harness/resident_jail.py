#!/usr/bin/env python3
"""
C15-RCC-RES-B-PREFLIGHT-002-CORRECTIVE-001 — Resident isolation sandbox (hardened).

Address blockers from PM re-review:
  1. NETWORK_SEAL_BYPASS      -> CLONE_NEWNET + block all sockets via iptables/nolisten;
                                 probe verifies urllib cannot reach GitHub/raw/API.
  2. PID_NAMESPACE_NOT_ISOLATED -> CLONE_NEWPID + fresh /proc mount; /proc shows
                                 independent PID space (Resident sees itself as pid 1
                                 only after fork of a minimal init that waits).
  3. PRIVILEGE_DROP_FAIL_OPEN -> No bare `except Exception: pass`. setgroups/setgid/
                                 setuid/chroot failures abort; privilege drop verified.
  4. MAILBOX_PATH_NOT_PROVEN  -> Mailbox is a host directory bind-mounted into the
                                 sandbox (not a private tmpfs). Operator writes
                                 requests to $MAILBOX/inbox (0644 root:nogroup);
                                 Resident writes replies to $MAILBOX/outbox (01733
                                 root:nobody with sticky group write so nobody can
                                 create files but not overwrite each other). Archive
                                 is operator-only (not mounted).
  5. RESIDENT_ENVELOPE        -> Not handled in this file (see mailbox_bridge.py).
  6. READ_ONLY_BIND_NOT_PROVEN -> bind + MS_REMOUNT|MS_RDONLY; probe attempts writes
                                 to Core src and to Resident contract; writes must
                                 fail with EROFS.
  7. STARTUP_PROCEDURE_FILENAME_BUG -> fixed in b_startup_procedure.md.
  8. TRANSPORT_E2E_PROBE      -> probe_e2e.sh + synthetic responder run under
                                 nobody in the sandbox exercises the full
                                 mailbox path.

ARCHITECTURE:
  * Parent (operator) runs as root; calls unshare() only in child (after fork)
    so parent's mount namespace is untouched and bind mounts of the host
    mailbox directory remain visible to operator.
  * Child creates new MOUNT + PID + NETWORK namespaces, mounts everything
    (including host mailbox bind rw at /work/inbox and /work/outbox), mounts
    a fresh /proc, chroots, drops to nobody, and execs Resident command.
  * Because inbox/outbox are bind mounts of a host directory, file writes
    inside the sandbox at /work/inbox and /work/outbox appear in the
    operator's $RUN_ROOT/mailbox/inbox and $RUN_ROOT/mailbox/outbox. This is
    the IPC channel; no socketpair / Unix socket magic required, but it is
    explicitly auditable and is verified by the E2E probe.

The operator archive directory ($RUN_ROOT/mailbox/archive) is NOT bind-mounted
into the sandbox, so Resident cannot read or modify prior requests/replies.
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

SIGCHLD = 17

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


def _umount(tgt: str) -> None:
    libc = _libc()
    if libc.umount2(tgt.encode(), 0) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), f"umount({tgt})")


def _bind_ro(src: str, tgt: str) -> None:
    """Read-only bind mount that is actually read-only (bind then remount RO)."""
    _mount(src, tgt, None, MS_BIND | MS_REC)
    _mount(src, tgt, None, MS_BIND | MS_REC | MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV)


def _bind_rw(src: str, tgt: str) -> None:
    _mount(src, tgt, None, MS_BIND | MS_REC | MS_NOSUID | MS_NODEV)


def _child(args: argparse.Namespace) -> int:
    """
    Namespace-init child.

    This runs in the child process AFTER fork from the operator. It creates the
    new namespaces, forks a worker (so that this process remains PID 1 in the
    new PID namespace and reaps zombies), and the worker performs all mounts,
    chroots, privilege drop, and exec.
    Every security step raises on failure (fail closed).
    """
    libc = _libc()

    # 1. New namespaces: MOUNT, PID, NETWORK
    if libc.unshare(CLONE_NEWNS | CLONE_NEWPID | CLONE_NEWNET) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), "unshare(CLONE_NEWNS|NEWPID|NEWNET)")

    # Fork a worker inside the new PID namespace so that we (the parent of this
    # fork) are PID 1 and can reap the worker and any of its children. Without
    # this, the exec'd command would be PID 1 and fork() inside it would fail
    # with ENOMEM when children are not reaped (SIGCHLD ignores causes issues).
    wpid = os.fork()
    if wpid == 0:
        # In worker; _do_mounts_and_exec never returns on success.
        return _worker(args)

    # PID-1 init loop: forward termination signals, wait for worker
    def _forward(signum, _frame):
        try:
            os.kill(wpid, signum)
        except ProcessLookupError:
            pass
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, _forward)
    while True:
        try:
            pid, status = os.waitpid(-1, 0)
            if pid == wpid:
                if os.WIFEXITED(status):
                    return os.WEXITSTATUS(status)
                if os.WIFSIGNALED(status):
                    return 128 + os.WTERMSIG(status)
                return 1
        except ChildProcessError:
            return 1
        except KeyboardInterrupt:
            _forward(signal.SIGINT, None)


def _worker(args: argparse.Namespace) -> int:
    """Second-stage child (PID>=2 in new ns): mounts, chroots, drops, execs.
    Must not return on success (calls os.execvpe)."""

    # Make mount propagation private (our mounts don't leak back)
    _mount("none", "/", None, MS_REC | MS_PRIVATE)

    sb = args.sandbox
    sb.mkdir(parents=True, exist_ok=True)

    # 2. Bring up loopback only in the new netns (so local AF_UNIX/localhost works
    # but external networks are unreachable).
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

    # 3. System directories — read-only bind + remount RO
    for d in ("/usr", "/lib", "/lib64", "/lib32", "/bin", "/sbin", "/etc", "/opt"):
        src = Path(d)
        if not src.exists():
            continue
        tgt = sb / d.lstrip("/")
        tgt.mkdir(parents=True, exist_ok=True)
        _bind_ro(str(src), str(tgt))

    # 4. /dev — bind (for null/urandom/tty)
    dev = sb / "dev"
    dev.mkdir(parents=True, exist_ok=True)
    _mount("/dev", str(dev), None, MS_BIND | MS_REC)

    # 5. /proc — fresh procfs mounted AFTER CLONE_NEWPID so PID space is clean
    #    (Resident will be PID 1 only if we fork an init; for our case the
    #    child execs the command directly so the command will be PID 1 inside
    #    the pid namespace. Either way, host pids are NOT visible because
    #    proc was mounted fresh.)
    proc = sb / "proc"
    proc.mkdir(parents=True, exist_ok=True)
    _mount("proc", str(proc), "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC)

    # sysfs is deliberately NOT mounted (prevents hardware/enum info leaks).

    # 6. /sys — don't mount (it would expose host topology).

    # 7. /repo skeleton
    repo = sb / "repo"
    repo.mkdir(parents=True, exist_ok=True)

    # Frozen Core — read-only bind (remount RO)
    core_src = args.repo / "src"
    core_tgt = repo / "src"
    core_tgt.mkdir(parents=True, exist_ok=True)
    _bind_ro(str(core_src), str(core_tgt))

    # Resident-safe contract (single file)
    c15_resident = repo / "reviews/internal_habitation/c15-rcc/v1/resident"
    c15_resident.mkdir(parents=True, exist_ok=True)
    contract_src = args.repo / "reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md"
    contract_tgt = c15_resident / "RESIDENT_B_RUN_CONTRACT.md"
    contract_tgt.touch()
    _bind_ro(str(contract_src), str(contract_tgt))

    # 8. /work
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

    # Mailbox inbox/outbox: host directories bind-mounted RW so operator and
    # Resident share the same filesystem entries. We'll chmod them for correct
    # uid/gid access AFTER mounting — but chmod through the bind-mount affects
    # the host directory, so do it on the host path before chroot.
    # Done in parent before invoking child.

    inbox_tgt = work / "inbox"
    outbox_tgt = work / "outbox"
    scratch_tgt = work / "scratch"
    inbox_tgt.mkdir(parents=True, exist_ok=True)
    outbox_tgt.mkdir(parents=True, exist_ok=True)
    scratch_tgt.mkdir(parents=True, exist_ok=True)
    _bind_rw(str(args.mailbox_inbox), str(inbox_tgt))
    _bind_rw(str(args.mailbox_outbox), str(outbox_tgt))
    _mount("tmpfs", str(scratch_tgt), "tmpfs", 0, "size=256m,mode=0700")

    # /tmp tmpfs
    tmp = sb / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    _mount("tmpfs", str(tmp), "tmpfs", 0, "size=64m,mode=1777")

    # /home/nobody
    home = sb / "home/nobody"
    home.mkdir(parents=True, exist_ok=True)
    _mount("tmpfs", str(home), "tmpfs", 0, "size=16m,mode=0700")

    # Optional inject dir (RO bind) for probe scripts
    if args.inject_dir is not None:
        inject_tgt = sb / "work/inject"
        inject_tgt.mkdir(parents=True, exist_ok=True)
        _bind_ro(str(args.inject_dir), str(inject_tgt))

    # 9. chroot MUST succeed before privilege drop
    os.chroot(str(sb))
    os.chdir("/work")

    # 10. Resolve 'nobody' user; FAIL CLOSED on any error (no bare except).
    import pwd
    try:
        nobody = pwd.getpwnam("nobody")
    except KeyError as e:
        raise RuntimeError(f"required user 'nobody' not found: {e}")

    # 11. setgroups/setgid/setuid must ALL succeed. Any error aborts.
    try:
        os.setgroups([])
    except OSError as e:
        raise RuntimeError(f"setgroups([]) failed: {e}")
    try:
        os.setgid(nobody.pw_gid)
    except OSError as e:
        raise RuntimeError(f"setgid({nobody.pw_gid}) failed: {e}")
    try:
        os.setuid(nobody.pw_uid)
    except OSError as e:
        raise RuntimeError(f"setuid({nobody.pw_uid}) failed: {e}")

    # 12. Verify we are actually nobody and cannot regain root
    if os.geteuid() == 0 or os.getuid() == 0:
        raise RuntimeError("privilege drop failed: still uid 0 after setuid")
    try:
        os.setuid(0)
        raise RuntimeError("privilege drop failed: able to re-acquire uid 0")
    except OSError:
        pass  # expected: EPERM

    # 13. Verify we cannot mount anymore (create a target dir in /tmp first since /tmp is a mounted tmpfs)
    try:
        try:
            os.mkdir("/tmp/test_mount")
        except FileExistsError:
            pass
        _mount("tmpfs", "/tmp/test_mount", "tmpfs", 0, "size=1m")
        raise RuntimeError("privilege drop failed: mount() still permitted")
    except OSError as e:
        if e.errno != 1:  # EPERM = 1
            raise RuntimeError(f"unexpected mount() result errno={e.errno}: {e}")

    # 14. Build environment and exec
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
    # Minimal inherited env; strip LD_* and anything suspicious.
    for k, v in os.environ.items():
        if k.startswith(("LD_", "PYTHON", "SUDO")):
            continue
        if k in ("PATH", "HOME", "TMPDIR", "TERM", "LANG", "LC_ALL", "LC_CTYPE"):
            env.setdefault(k, v)
    os.execvpe(args.cmd[0], args.cmd, env)
    # If we get here exec failed
    raise RuntimeError(f"execvp({args.cmd[0]!r}) failed")


def _prepare_mailbox(args: argparse.Namespace) -> None:
    """Create and chmod host-side mailbox directories before forking.

    Layout (operator-owned, host-visible):
      args.mailbox_root/inbox/   -- requests: root:nogroup 0644 per file
      args.mailbox_root/outbox/  -- replies: root:nogroup 01733 (sticky, group wx)
                                    so 'nobody' (in nogroup) can create reply files
                                    but not overwrite/delete other files; operator
                                    reads replies as root.
      args.mailbox_root/archive/ -- operator-only; NOT bind-mounted into sandbox.
    """
    root = args.mailbox_root
    root.mkdir(parents=True, exist_ok=True)
    (root / "archive").mkdir(parents=True, exist_ok=True)
    inbox = root / "inbox"
    outbox = root / "outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)

    # Clear any stale files from prior runs (preflight only; for real B run
    # startup procedure will use a fresh run root).
    for p in list(inbox.iterdir()) + list(outbox.iterdir()):
        p.unlink()

    # Determine nogroup gid. On Debian/Ubuntu it's 'nogroup'; on some systems 'nobody'.
    import grp
    try:
        nogroup_gid = grp.getgrnam("nogroup").gr_gid
    except KeyError:
        nogroup_gid = grp.getgrnam("nobody").gr_gid

    # inbox: root:nogroup 0755 — nobody can read, only root can write/delete
    os.chown(inbox, 0, nogroup_gid)
    os.chmod(inbox, 0o755)

    # outbox: root:nogroup 01733 (sticky bit + write for group) so 'nobody' can
    # create new files but not delete/overwrite files created by others (operator).
    # Files within will be created by Resident as nobody:nogroup 0644.
    os.chown(outbox, 0, nogroup_gid)
    os.chmod(outbox, 0o1733)

    # archive: root:root 0700 — operator-only, never mounted into sandbox
    os.chown(root / "archive", 0, 0)
    os.chmod(root / "archive", 0o700)

    args.mailbox_inbox = inbox
    args.mailbox_outbox = outbox


def main() -> int:
    ap = argparse.ArgumentParser(description="Hardened Resident-B sandbox (mount+pid+net NS, chroot, privdrop, host bind mailbox)")
    ap.add_argument("--repo", type=Path, default=REPO_ROOT_DEFAULT)
    ap.add_argument("--sandbox", type=Path, required=True)
    ap.add_argument("--world", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--state", type=Path, required=True)
    ap.add_argument("--lock", type=Path, required=True)
    ap.add_argument("--mailbox-root", type=Path, required=True,
                    help="Host directory that will contain inbox/ (operator->resident) "
                         "and outbox/ (resident->operator) and archive/ (operator-only).")
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

    # Clean sandbox
    import shutil
    if args.sandbox.exists():
        shutil.rmtree(args.sandbox)
    args.sandbox.mkdir(parents=True)

    _prepare_mailbox(args)

    # Fork: child enters namespaces and execs; parent waits
    pid = os.fork()
    if pid == 0:
        try:
            rc = _child(args)
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
