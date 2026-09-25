#!/usr/bin/env python3
"""
C15-RCC-RES-B-PREFLIGHT-002 — Resident filesystem isolation sandbox.

ARCHITECTURE (matches release_contract.md §2):

  * OUTSIDE the sandbox (operator/transport, runs as the operator user):
      - release_operator.py (reads sealed fixture, validates boundary,
        reveals/acks, writes ONLY the 8-field resident-visible projection)
      - mailbox bridge (transports RuntimeSnapshot+projection in,
        transports Resident directive out; performs ZERO semantic
        judgment — validates only JSON structure)
      - freeze/evidence hashing
      - Core headless CLI for `ingest`, `due`, etc. (operates on the
        same private World via RW bind mount, but only on the operator
        side of the boundary; never injects semantics)

  * INSIDE the sandbox (Resident model process only):
      - Python + frozen Core code (read-only)
      - /work/world.sqlite          RW — durable private World (bind-mounted)
      - /work/world_index.sqlite    RW — synchronized index
      - /work/release_state.json    RW — phase-boundary receipt state
      - /work/world.writer.lock     RW — writer lease
      - /work/inbox/                tmpfs — Resident-visible event JSON
      - /work/outbox/               tmpfs — Resident directive JSON
      - /work/scratch/              tmpfs — mailbox round-trip temp
      - RESIDENT_B_RUN_CONTRACT.md  RO — the safe run contract (single file)
      - NO fixture/, evaluator/, governance/, .git/, task board,
        checkpoint, PM reports, prior A-002 evidence, transcripts, or
        other Resident contracts — these paths simply do not exist
        inside the mount namespace.

The Resident process cannot reach sealed material by any filesystem
path; it cannot exec `mount`, cannot read /proc/<pid>/root of host
processes (runs as user `nobody`), and chroots into a minimal tree.

This is NOT a prompt-based "don't read" barrier. It is an OS-level
enforcement: the paths are not mounted.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import os
import subprocess
import sys
from pathlib import Path

CLONE_NEWNS = 0x00020000
MS_BIND = 4096
MS_REC = 16384
MS_RDONLY = 1
MS_PRIVATE = 1 << 18

REPO_ROOT_DEFAULT = Path("/home/user/Haneof-AIOS-Core-v3.0")


def _mount(src: str, tgt: str, fstype: str | None, flags: int, data: str = "") -> None:
    libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    if libc.mount(src.encode(), tgt.encode(), fstype.encode() if fstype else None, flags, data.encode()) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), f"mount({src} -> {tgt})")


def _unshare_mountns() -> None:
    libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    if libc.unshare(CLONE_NEWNS) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), "unshare(CLONE_NEWNS)")
    _mount("none", "/", None, MS_REC | MS_PRIVATE)


def build_sandbox(repo_root: Path, sandbox_root: Path, runtime_world: Path,
                  runtime_index: Path, runtime_state: Path, runtime_lock: Path,
                  writable_scratch: Path, inject_dir: Path | None = None) -> None:
    sandbox_root.mkdir(parents=True, exist_ok=True)

    # System roots (read-only bind mounts of the host OS)
    for d in ("/usr", "/lib", "/lib64", "/lib32", "/bin", "/sbin", "/etc", "/opt"):
        src = Path(d)
        if not src.exists():
            continue
        tgt = sandbox_root / d.lstrip("/")
        tgt.mkdir(parents=True, exist_ok=True)
        _mount(str(src), str(tgt), None, MS_BIND | MS_REC | MS_RDONLY)

    # /proc and /dev (proc read-write so Python sees its own pid; dev for null/urandom)
    proc = sandbox_root / "proc"
    proc.mkdir(parents=True, exist_ok=True)
    _mount("proc", str(proc), "proc", 0)
    dev = sandbox_root / "dev"
    dev.mkdir(parents=True, exist_ok=True)
    _mount("/dev", str(dev), None, MS_BIND | MS_REC)

    # /repo skeleton (read-only)
    repo = sandbox_root / "repo"
    repo.mkdir(parents=True, exist_ok=True)

    # Frozen Core tree
    core_src = repo_root / "src"
    core_tgt = repo / "src"
    core_tgt.mkdir(parents=True, exist_ok=True)
    _mount(str(core_src), str(core_tgt), None, MS_BIND | MS_REC | MS_RDONLY)

    # Resident-safe B run contract ONLY (single file).
    # release_contract.md (OPERATOR-only) is deliberately NOT mounted.
    c15_resident = repo / "reviews/internal_habitation/c15-rcc/v1/resident"
    c15_resident.mkdir(parents=True, exist_ok=True)
    contract_src = repo_root / "reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_B_RUN_CONTRACT.md"
    contract_tgt = c15_resident / "RESIDENT_B_RUN_CONTRACT.md"
    contract_tgt.touch()
    _mount(str(contract_src), str(contract_tgt), None, MS_BIND | MS_RDONLY)

    # NOTE: we intentionally DO NOT mount:
    #   - reviews/internal_habitation/c15-rcc/v1/fixture/
    #   - reviews/internal_habitation/c15-rcc/v1/evaluator/
    #   - reviews/internal_habitation/c15-rcc/v1/release/
    #   - reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002/
    #   - reviews/internal_habitation/c14-resident/** (except what's needed for Core import)
    #   - governance/, prompts/, .github/, docs/
    #   - AIOS_SINGLE_WINDOW_TASK_BOARD.md, AIOS_v3.0_CURRENT_CHECKPOINT.md, PROJECT_MASTER_MAP.md
    #   - .git/
    # These paths simply do not exist in the sandbox.

    # /work — durable state (RW bind mounts from operator-side runtime dir)
    #        and tmpfs scratch (mailbox in/out, tmp).
    work = sandbox_root / "work"
    work.mkdir(parents=True, exist_ok=True)

    def _mount_work_rw(src_path: Path, name: str) -> None:
        tgt = work / name
        tgt.parent.mkdir(parents=True, exist_ok=True)
        if src_path.is_dir():
            tgt.mkdir(parents=True, exist_ok=True)
        else:
            tgt.parent.mkdir(parents=True, exist_ok=True)
            tgt.touch()
        _mount(str(src_path), str(tgt), None, MS_BIND)

    _mount_work_rw(runtime_world, "world.sqlite")
    _mount_work_rw(runtime_index, "world_index.sqlite")
    _mount_work_rw(runtime_state, "release_state.json")
    _mount_work_rw(runtime_lock, "world.writer.lock")

    # Inbox/outbox: tmpfs so Resident cannot see prior mailbox content
    for sub in ("inbox", "outbox", "scratch"):
        p = work / sub
        p.mkdir(parents=True, exist_ok=True)
        _mount("tmpfs", str(p), "tmpfs", 0, "size=256m,mode=0700")

    # /tmp
    tmp = sandbox_root / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    _mount("tmpfs", str(tmp), "tmpfs", 0, "size=64m,mode=1777")

    # /home (for the nobody user)
    home = sandbox_root / "home/nobody"
    home.mkdir(parents=True, exist_ok=True)
    _mount("tmpfs", str(home), "tmpfs", 0, "size=16m,mode=0700")

    # Optional read-only injection directory for test probes
    if inject_dir is not None:
        inject_tgt = sandbox_root / "work/inject"
        inject_tgt.mkdir(parents=True, exist_ok=True)
        _mount(str(inject_dir), str(inject_tgt), None, MS_BIND | MS_REC | MS_RDONLY)


def enter_sandbox(sandbox_root: Path, cmd: list[str], cwd: str = "/work", env: dict | None = None) -> int:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    for k in list(full_env):
        if k.startswith("LD_"):
            del full_env[k]
    pid = os.fork()
    if pid == 0:
        try:
            os.chroot(str(sandbox_root))
            os.chdir(cwd)
            # Drop privileges to 'nobody' so Resident cannot remount or read host proc
            try:
                import pwd
                nobody = pwd.getpwnam("nobody")
                os.setgroups([])
                os.setgid(nobody.pw_gid)
                os.setuid(nobody.pw_uid)
            except Exception:
                pass
            os.execvpe(cmd[0], cmd, full_env)
        except Exception as e:
            print(f"child exec failed: {e}", file=sys.stderr)
            os._exit(127)
    else:
        _, status = os.waitpid(pid, 0)
        if os.WIFEXITED(status):
            return os.WEXITSTATUS(status)
        return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Build and enter Resident-B isolation sandbox (Resident model side only)")
    ap.add_argument("--repo", type=Path, default=REPO_ROOT_DEFAULT)
    ap.add_argument("--sandbox", type=Path, required=True)
    ap.add_argument("--world", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--state", type=Path, required=True)
    ap.add_argument("--lock", type=Path, required=True)
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--inject-dir", type=Path, help="Optional directory to bind RO at /work/inject inside the sandbox (for test/probe scripts)")
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args()

    if os.geteuid() != 0:
        print("error: resident_jail.py must run as root (sudo)", file=sys.stderr)
        return 99

    _unshare_mountns()
    build_sandbox(args.repo, args.sandbox, args.world, args.index, args.state, args.lock, args.scratch, args.inject_dir)

    if args.verify_only:
        probe = ["/bin/sh", "-c",
                 "echo PROBE_OK; "
                 "echo '=== /repo layout ==='; ls /repo; echo; ls /repo/reviews/internal_habitation/c15-rcc/v1/resident/; "
                 "echo '=== checking Core import ==='; "
                 "PYTHONPATH=/repo/src /usr/bin/python3 -c \"import pydantic; from aios_core.contracts.base import WorldObject; print('core_import_ok')\"; "
                 "echo '=== sealed-path leak probe ==='; "
                 "leak=0; "
                 "for p in /repo/fixture /repo/evaluator /repo/governance /repo/.git "
                 "/repo/reviews/internal_habitation/c15-rcc/v1/fixture "
                 "/repo/reviews/internal_habitation/c15-rcc/v1/evaluator "
                 "/repo/reviews/internal_habitation/c15-rcc/v1/release "
                 "/repo/reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-A-RERUN-002 "
                 "/repo/reviews/internal_habitation/c14-resident "
                 "/repo/prompts /repo/AIOS_SINGLE_WINDOW_TASK_BOARD.md "
                 "/repo/AIOS_v3.0_CURRENT_CHECKPOINT.md /repo/PROJECT_MASTER_MAP.md; "
                 "do if [ -e \\$p ]; then echo LEAK:\\$p; leak=1; else echo sealed:\\$p absent; fi; done; "
                 "echo '=== capability audit: can we read /proc/1/root? ==='; "
                 "ls -la /proc/1/root 2>&1 | head -1; "
                 "if [ \\$leak -eq 0 ]; then echo ISOLATION_PASS; else echo ISOLATION_FAIL; fi"]
        return enter_sandbox(args.sandbox, probe, cwd="/work")

    if not args.cmd:
        print("error: provide a command to run inside the sandbox", file=sys.stderr)
        return 2
    cmd = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    return enter_sandbox(args.sandbox, cmd, cwd="/work", env={
        "AIOS_WORLD_PATH": "/work/world.sqlite",
        "AIOS_INDEX_PATH": "/work/world_index.sqlite",
        "AIOS_LOCK_PATH": "/work/world.writer.lock",
        "AIOS_SUBJECT_ID": "user_1",
        "PYTHONPATH": "/repo/src",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/home/nobody",
        "TMPDIR": "/tmp",
    })


if __name__ == "__main__":
    raise SystemExit(main())
