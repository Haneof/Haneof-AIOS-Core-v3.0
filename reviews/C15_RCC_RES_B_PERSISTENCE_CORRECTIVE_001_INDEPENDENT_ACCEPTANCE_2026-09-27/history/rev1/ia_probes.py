"""Independent Acceptance adversarial probes -- C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001.

Reviewer-authored.  Authored and frozen BEFORE first execution.

Tested exact candidate: 63ca592359c7e3fd71d6cc4ba349949e4f0b80e3
Canonical Stage B commit: 15c75ac3e97c57a5fa1f3085c282a852994d9acf

These probes exist to try to make the candidate RED.  They are not a
re-run of the author's suite.  Every expected outcome below is the
*contract* the candidate itself declares, not a number copied from the
author's logs:

  * ``tools/c15_persistence/backend.py`` declares the Git remote ref
    ``refs/heads/persistence/<run_id>`` to be the AUTHORITATIVE backend and
    ``/home/user`` to be a "disposable local cache" that "is ephemeral across
    session boundaries".
  * ``tools/c15_persistence/operator_session.py`` declares kill points
    K1..K5 as durability barriers of the operator loop.
  * ``backend.py`` states "A process restart inside the same environment is
    therefore NOT the same boundary" -- the RERUN-002 incident was an
    ENVIRONMENT loss, not a process restart.

Therefore the contract tested here is: if the execution environment is lost at
any of K1..K5, a brand new environment that can see only the remote
authoritative backend must recover to that exact barrier and continue
convergence without duplicating already-durable work.

Groups:
  A  cross-environment durability at K1..K5 (highest priority)
  B  remote backend fail-closed on tampered / missing / conflicting state
  C  concurrent writer / remote CAS (no force, no silent fork)
  D  Stage A / Stage B exact byte fidelity (independent materialization)
  E  exactly-once / no duplicate under retry
  F  Git-as-authoritative-store semantics
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
CANDIDATE_REPO = Path(os.environ.get("IA_CANDIDATE_REPO", Path.cwd())).resolve()
RUN_ID = "ia-probe-synthetic-run"
SESSION_ID = "ia-probe-synthetic-session"
STAGE_A_COMMIT = "914c960cade8830d4d0c80925bcfe03f803c3ceb"
STAGE_B_COMMIT = "15c75ac3e97c57a5fa1f3085c282a852994d9acf"
CANONICAL_REF = "refs/heads/persistence/c15-persistence-synthetic-run-ae5c57221c83"
CANONICAL_RUN = "c15-persistence-synthetic-run-ae5c57221c83"
CANONICAL_SESSION = "c15-persistence-synthetic-session-ae5c57221c83"

KILL_POINTS = [
    "K1_AFTER_REVEAL",
    "K2_AFTER_INGEST",
    "K3_AFTER_REQUEST_DISPATCH",
    "K4_AFTER_REPLY_AUTHENTICATED",
    "K5_AFTER_APPLIED_BEFORE_ACK",
]

# The persisted workspace must be a legal (non-ephemeral) backend root.
_WS = Path(os.environ.get("IA_WORKSPACE") or (Path.home() / "ia-workspace"))
os.environ.setdefault("C15_PERSISTED_WORKSPACE", str(_WS))
os.environ.setdefault("C15_PERSISTENCE_RUNS_ROOT", str(_WS / "runs"))
_WS.mkdir(parents=True, exist_ok=True)
(_WS / "runs").mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(CANDIDATE_REPO / "src"))
sys.path.insert(0, str(CANDIDATE_REPO))

from tools.c15_persistence.backend import BackendError, RunBackend  # noqa: E402
from tools.c15_persistence.operator_session import OperatorSession  # noqa: E402
from tools.c15_persistence import remote_backend  # noqa: E402


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _child_env() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(CANDIDATE_REPO / "src"), str(CANDIDATE_REPO), env.get("PYTHONPATH", "")]
    )
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return env


def run_child(args: list[str], *, expect_sigkill: bool = False):
    cmd = [sys.executable, str(HERE / "ia_child.py"), *args]
    p = subprocess.run(cmd, cwd=str(CANDIDATE_REPO), env=_child_env(),
                       capture_output=True, text=True, timeout=900)
    if expect_sigkill:
        assert p.returncode == -signal.SIGKILL, (
            f"expected SIGKILL, got {p.returncode}\n{p.stdout}\n{p.stderr}"
        )
        return p
    assert p.returncode == 0, f"child failed rc={p.returncode}\n{p.stdout}\n{p.stderr}"
    return json.loads(p.stdout)


def run_probe_cli(args: list[str], *, expect_sigkill: bool = False):
    cmd = [sys.executable, "-m", "tools.c15_persistence.probe_cli", *args]
    p = subprocess.run(cmd, cwd=str(CANDIDATE_REPO), env=_child_env(),
                       capture_output=True, text=True, timeout=900)
    if expect_sigkill:
        assert p.returncode == -signal.SIGKILL, (
            f"expected SIGKILL, got {p.returncode}\n{p.stdout}\n{p.stderr}"
        )
        return p
    assert p.returncode == 0, f"probe_cli failed rc={p.returncode}\n{p.stdout}\n{p.stderr}"
    return json.loads(p.stdout)


def git(args: list[str], cwd: Path, *, check: bool = True):
    p = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if check:
        assert p.returncode == 0, f"git {args} failed:\n{p.stdout}\n{p.stderr}"
    return p


def make_bare_remote() -> Path:
    bare = _WS / f"remote-{uuid.uuid4().hex[:10]}.git"
    bare.mkdir(parents=True, exist_ok=True)
    git(["init", "--bare", "-q", str(bare)], cwd=_WS)
    return bare


def remote_head(bare: Path, ref: str) -> str | None:
    p = subprocess.run(["git", "ls-remote", str(bare), ref],
                       capture_output=True, text=True)
    if p.returncode != 0 or not p.stdout.strip():
        return None
    return p.stdout.split()[0]


def new_identity(tag: str) -> tuple[str, str]:
    u = uuid.uuid4().hex[:10]
    return f"ia-{tag}-run-{u}", f"ia-{tag}-session-{u}"


def destroy_environment(root: Path) -> None:
    """Simulate total loss of the execution environment's local filesystem."""
    for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        try:
            if path.is_dir() and not path.is_symlink():
                path.chmod(0o700)
            elif path.is_file() and not path.is_symlink():
                path.chmod(0o600)
        except OSError:
            pass
    shutil.rmtree(root, ignore_errors=True)


def assert_no_force_push() -> None:
    """No force-push may exist anywhere in the persistence durability layer."""
    bad = []
    for f in sorted((CANDIDATE_REPO / "tools" / "c15_persistence").glob("*.py")):
        src = f.read_text(encoding="utf-8")
        for token in ("--force", "-f ", "push --force", "+refs/heads"):
            if token in src:
                bad.append(f"{f.name}:{token}")
    assert not bad, f"force-push primitive present in durability layer: {bad}"


# ==========================================================================
# GROUP A -- cross-environment durability at K1..K5  (highest priority)
# ==========================================================================
@pytest.mark.parametrize("kill_point", KILL_POINTS)
def test_groupA_cross_environment_durability_at_barrier(kill_point, tmp_path):
    """The remote authoritative backend must already hold the K-barrier state.

    Contract under test (declared by the candidate itself): the Git remote ref
    is the authoritative backend, local is a disposable cache, and the original
    incident was an ENVIRONMENT loss rather than a process restart.

    Steps:
      1. checkpoint cursor 1 to a disposable remote;
      2. a fresh process resumes and is SIGKILLed at the barrier mid-cursor-2;
      3. the remote authoritative state must already contain the barrier work;
      4. the whole local environment is destroyed;
      5. a brand new environment recovers from the remote only, and must land
         on cursor 2 having lost nothing.
    """
    run_id, session_id = new_identity("A" + kill_point[1])
    bare = make_bare_remote()
    ref = f"refs/heads/persistence/{run_id}"
    runs = _WS / "runs"
    local = runs / run_id

    # --- 1. durable checkpoint of cursor 1 (a completed cursor) -----------
    session = OperatorSession.create(local, run_id=run_id, session_id=session_id,
                                     event_count=30)
    out1 = session.process_one_cursor()
    assert out1["ack"]["status"] == "acked"
    session.backend.release()
    ref_pushed, checkpoint_sha = remote_backend.push_run_state(
        session.backend, remote_ref=ref, remote=str(bare),
        repo_dir=CANDIDATE_REPO, message="IA checkpoint cursor 1")
    assert remote_head(bare, ref) == checkpoint_sha

    # --- 2. fresh process: resume and die at the barrier during cursor 2 ---
    killed = run_probe_cli(
        ["--root", str(local), "--run-id", run_id, "--session-id", session_id,
         "--mode", "resume", "--kill-at", kill_point],
        expect_sigkill=True)
    assert killed.returncode == -signal.SIGKILL

    problems = []
    # --- 3. was the barrier already durable on the REMOTE? -----------------
    after_barrier_sha = remote_head(bare, ref)
    if after_barrier_sha == checkpoint_sha:
        problems.append(
            f"{kill_point}: remote authoritative ref is UNCHANGED at the durability "
            f"barrier (still {checkpoint_sha[:12]}, the pre-barrier cursor-1 commit). "
            f"The K-barrier work existed only in local /home/user cache bytes."
        )
    # the local (doomed) environment did have the work -- prove the loss is real
    local_cur = None
    ce = local / "state" / "current-event.json"
    if ce.is_file():
        local_cur = json.loads(ce.read_text()).get("sequence")

    # --- 4. the environment disappears entirely ---------------------------
    destroy_environment(local)

    # --- 5. a brand new environment recovers from the remote only ----------
    fresh = runs / f"{run_id}-fresh"
    try:
        snap = run_child(["--mode", "materialize-report", "--root", str(fresh),
                          "--run-id", run_id, "--session-id", session_id,
                          "--remote", str(bare), "--remote-ref", ref,
                          "--repo-dir", str(CANDIDATE_REPO)])
    except AssertionError as exc:
        problems.append(f"{kill_point}: new environment could not recover from "
                        f"remote at all: {exc}")
        snap = {"cursor": None, "last_acked_sequence": None}

    if snap.get("cursor") != 2:
        problems.append(
            f"{kill_point}: after environment loss, remote-authoritative recovery "
            f"yields cursor {snap.get('cursor')} (last_acked="
            f"{snap.get('last_acked_sequence')}), not the in-flight cursor 2 "
            f"(local cache at the barrier held cursor {local_cur}). "
            f"Work already durably staged/applied at the barrier is LOST and will "
            f"be re-executed from scratch."
        )

    try:
        destroy_environment(fresh)
    except Exception:
        pass

    assert not problems, "CROSS-ENVIRONMENT DURABILITY CONTRACT VIOLATED:\n  - " + \
        "\n  - ".join(problems)


def test_groupA_production_loop_never_reaches_the_remote_backend():
    """The normal operator loop must make the remote authoritative backend
    part of its durability path.  If the loop never touches it, then no K1-K5
    barrier can ever be remotely durable."""
    session_calls = []
    real_push = remote_backend.push_run_state

    def spy(*a, **k):
        session_calls.append(k.get("remote_ref") or (a[1] if len(a) > 1 else None))
        return real_push(*a, **k)

    remote_backend.push_run_state = spy
    run_id, session_id = new_identity("Aloop")
    local = _WS / "runs" / run_id
    try:
        session = OperatorSession.create(local, run_id=run_id,
                                         session_id=session_id, event_count=30)
        session.process_one_cursor()
        session.backend.release()
    finally:
        remote_backend.push_run_state = real_push

    assert session_calls, (
        "PRODUCTION PATH GAP: OperatorSession.process_one_cursor() completed a "
        "full cursor (reveal->ingest->dispatch->apply->ack) without ever calling "
        "push_run_state(). The remote Git backend is therefore NOT on the normal "
        "production operator durability path; it is reachable only by explicitly "
        "calling OperatorSession.push_to_remote() or by running the dedicated "
        "tools/c15_persistence/platform_reattach.py Stage A/B runner."
    )


# ==========================================================================
# GROUP B -- remote backend must fail closed
# ==========================================================================
def _stage_remote(tag: str):
    run_id, session_id = new_identity(tag)
    bare = make_bare_remote()
    ref = f"refs/heads/persistence/{run_id}"
    local = _WS / "runs" / run_id
    session = OperatorSession.create(local, run_id=run_id, session_id=session_id,
                                     event_count=30)
    session.process_one_cursor()
    session.backend.release()
    from tools.c15_persistence.runstate import capture_manifest, write_manifest
    cur = json.loads((local / "state" / "current-event.json").read_text())
    man = capture_manifest(session.backend, cursor=cur["sequence"],
                           event_id=cur["event_id"], phase="A")
    write_manifest(session.backend, man, name="run-state-manifest.json")
    session.backend.release()
    _, sha = remote_backend.push_run_state(session.backend, remote_ref=ref,
                                           remote=str(bare),
                                           repo_dir=CANDIDATE_REPO,
                                           message="IA group B stage")
    return dict(run_id=run_id, session_id=session_id, bare=bare, ref=ref,
                local=local, sha=sha, manifest=man)


def _tamper_and_recover(ctx, mutate, *, commit_sha=None, target=None):
    """Clone the bare remote, mutate one byte in the commit tree, push it to a
    new ref, and try to open it.  Must fail closed."""
    work = _WS / f"tamper-{uuid.uuid4().hex[:8]}"
    work.mkdir(parents=True)
    subprocess.run(["git", "clone", "-q", str(ctx["bare"]), str(work)],
                   capture_output=True, text=True, check=True)
    git(["checkout", "-q", ctx["sha"]], cwd=work)
    mutate(work)
    git(["add", "-A"], cwd=work)
    git(["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
         "-m", "tampered"], cwd=work)
    new_sha = git(["rev-parse", "HEAD"], cwd=work).stdout.strip()
    new_ref = ctx["ref"] + "-tampered"
    p = subprocess.run(["git", "push", str(ctx["bare"]), f"{new_sha}:{new_ref}"],
                       cwd=work, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    out = {}
    fresh = _WS / "runs" / f"{ctx['run_id']}-t{uuid.uuid4().hex[:6]}"
    try:
        snap = run_child(["--mode", "materialize-report", "--root", str(fresh),
                          "--run-id", ctx["run_id"], "--session-id", ctx["session_id"],
                          "--remote", str(ctx["bare"]), "--remote-ref", new_ref,
                          "--commit-sha", commit_sha or new_sha,
                          "--repo-dir", str(CANDIDATE_REPO)])
        out["opened"] = True
        out["snap"] = snap
    except AssertionError as exc:
        out["opened"] = False
        out["err"] = str(exc)
    finally:
        try:
            destroy_environment(fresh)
        except Exception:
            pass
        shutil.rmtree(work, ignore_errors=True)
    return out


@pytest.mark.parametrize("label,mutate", [
    ("owner_tamper", lambda w: (w / "owner.json").write_text(
        json.dumps({"run_id": "attacker-run", "session_id": "attacker-session",
                    "subject_id": "u", "phase": "A", "creator_pid": 1,
                    "boot_id": "x", "backend_version": "c15-persistence-backend-v1"}))),
    ("manifest_tamper", lambda w: (w / "run-state-manifest.json").write_text(
        json.dumps({"manifest_version": "c15-run-state-manifest-v1",
                    "run_id": "x", "session_id": "y", "artifacts": {},
                    "manifest_sha256": "0" * 64}))),
    ("manifest_missing", lambda w: (w / "run-state-manifest.json").unlink()),
    ("owner_missing", lambda w: (w / "owner.json").unlink()),
    ("world_byte_tamper", lambda w: (w / "state" / "runtime" / "world.sqlite")
     .write_bytes(b"CORRUPTED-WORLD-BYTES")),
    ("journal_tamper", lambda w: (w / "journal.sqlite").write_bytes(b"CORRUPTED-JOURNAL")),
    ("mailbox_tamper", lambda w: (w / "mailbox" / "archive.jsonl")
     .write_bytes(b'{"forged": true}\n')),
    ("sealed_generation_deletion", lambda w: shutil.rmtree(
        w / "generations" / "000004")),
    ("sealed_generation_modification", lambda w: (w / "generations" / "000004"
                                                   / "current-event.json")
     .write_text("{}")),
    ("index_tamper", lambda w: (w / "state" / "runtime" / "index.sqlite")
     .write_bytes(b"CORRUPTED-INDEX")),
    ("release_state_tamper", lambda w: (w / "state" / "runtime" / "release_state.json")
     .write_text(json.dumps({"last_acked_sequence": 99, "next_sequence": 100}))),
])
def test_groupB_tampered_remote_state_fails_closed(label, mutate):
    ctx = _stage_remote("B" + label)
    res = _tamper_and_recover(ctx, mutate)
    assert not res["opened"], (
        f"FAIL-OPEN: remote state tampered ({label}) was ACCEPTED and opened. "
        f"snapshot={res.get('snap')}"
    )


def test_groupB_missing_remote_ref_fails_closed():
    run_id, session_id = new_identity("Bmissing")
    bare = make_bare_remote()
    fresh = _WS / "runs" / f"{run_id}-m"
    failed = False
    try:
        run_child(["--mode", "materialize-report", "--root", str(fresh),
                   "--run-id", run_id, "--session-id", session_id,
                   "--remote", str(bare),
                   "--remote-ref", f"refs/heads/persistence/{run_id}",
                   "--repo-dir", str(CANDIDATE_REPO)])
    except AssertionError:
        failed = True
    finally:
        shutil.rmtree(fresh, ignore_errors=True)
    assert failed, "FAIL-OPEN: missing remote ref was silently reconstructed"


def test_groupB_wrong_run_id_fails_closed():
    ctx = _stage_remote("Brun")
    wrong_run, _ = new_identity("Brun-wrong")
    fresh = _WS / "runs" / f"{wrong_run}-w"
    failed = False
    try:
        run_child(["--mode", "materialize-report", "--root", str(fresh),
                   "--run-id", wrong_run, "--session-id", ctx["session_id"],
                   "--remote", str(ctx["bare"]), "--remote-ref", ctx["ref"],
                   "--commit-sha", ctx["sha"], "--repo-dir", str(CANDIDATE_REPO)])
    except AssertionError:
        failed = True
    finally:
        shutil.rmtree(fresh, ignore_errors=True)
    assert failed, "FAIL-OPEN: a remote backend was opened under a foreign run_id"


def test_groupB_wrong_session_id_fails_closed():
    ctx = _stage_remote("Bsess")
    _, wrong_ses = new_identity("Bsess-wrong")
    fresh = _WS / "runs" / f"{ctx['run_id']}-s"
    failed = False
    try:
        run_child(["--mode", "materialize-report", "--root", str(fresh),
                   "--run-id", ctx["run_id"], "--session-id", wrong_ses,
                   "--remote", str(ctx["bare"]), "--remote-ref", ctx["ref"],
                   "--commit-sha", ctx["sha"], "--repo-dir", str(CANDIDATE_REPO)])
    except AssertionError:
        failed = True
    finally:
        shutil.rmtree(fresh, ignore_errors=True)
    assert failed, "FAIL-OPEN: a remote backend was opened under a foreign session_id"


def test_groupB_manifest_sha_mismatch_fails_closed():
    ctx = _stage_remote("Bsha")
    with pytest.raises(Exception):
        remote_backend.verify_remote_state(
            remote_ref=ctx["ref"], commit_sha=ctx["sha"],
            expected_manifest_sha256="0" * 64, remote=str(ctx["bare"]),
            repo_dir=CANDIDATE_REPO)


def test_groupB_newer_remote_generation_beats_stale_local_cache():
    """A stale local cache must never be silently preferred over a newer
    authoritative remote generation."""
    ctx = _stage_remote("Bstale")
    run_id, session_id = ctx["run_id"], ctx["session_id"]
    bare, ref, sha = ctx["bare"], ctx["ref"], ctx["sha"]
    # advance the REMOTE by one full cursor
    work = _WS / f"adv-{uuid.uuid4().hex[:8]}"
    work.mkdir(parents=True)
    subprocess.run(["git", "clone", "-q", str(bare), str(work)],
                   capture_output=True, text=True, check=True)
    git(["checkout", "-q", sha], cwd=work)
    session = OperatorSession.attach(work / "backend", run_id=run_id,
                                     session_id=session_id)
    session.resume()
    session.backend.release()
    _, sha2 = remote_backend.push_run_state(
        session.backend, remote_ref=ref, remote=str(bare),
        repo_dir=CANDIDATE_REPO, message="IA advance to cursor 2")
    assert remote_head(bare, ref) == sha2 and sha2 != sha
    # a fresh environment must see cursor 2, not cursor 1
    fresh = _WS / "runs" / f"{run_id}-adv"
    try:
        snap = run_child(["--mode", "materialize-report", "--root", str(fresh),
                          "--run-id", run_id, "--session-id", session_id,
                          "--remote", str(bare), "--remote-ref", ref,
                          "--repo-dir", str(CANDIDATE_REPO)])
        assert snap["cursor"] == 2, (
            f"stale-cache failure: fresh environment recovered cursor "
            f"{snap['cursor']} instead of remote cursor 2"
        )
    finally:
        shutil.rmtree(fresh, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)


# ==========================================================================
# GROUP C -- concurrent writer / remote CAS
# ==========================================================================
def test_groupC_stale_writer_cannot_overwrite_and_never_forces():
    """Two writers read the same remote generation; the second must fail."""
    assert_no_force_push()
    run_id, session_id = new_identity("C")
    bare = make_bare_remote()
    ref = f"refs/heads/persistence/{run_id}"
    base = _WS / "runs" / f"{run_id}-base"
    session = OperatorSession.create(base, run_id=run_id, session_id=session_id,
                                     event_count=30)
    session.process_one_cursor()
    session.backend.release()
    _, gen_n = remote_backend.push_run_state(session.backend, remote_ref=ref,
                                              remote=str(bare),
                                              repo_dir=CANDIDATE_REPO,
                                              message="C base N")

    # writer A and writer B both materialize generation N
    wa = _WS / "runs" / f"{run_id}-A"
    wb = _WS / "runs" / f"{run_id}-B"
    for w in (wa, wb):
        remote_backend.materialize_run_state(
            run_id=run_id, session_id=session_id, target_dir=w,
            remote_ref=ref, commit_sha=gen_n, remote=str(bare),
            repo_dir=CANDIDATE_REPO).release()

    # writer A advances and pushes N+1
    sa = OperatorSession.attach(wa, run_id=run_id, session_id=session_id)
    sa.resume()
    sa.backend.release()
    remote_backend.push_run_state(sa.backend, remote_ref=ref, remote=str(bare),
                                  repo_dir=CANDIDATE_REPO, message="C writer A N+1")
    a_sha = remote_head(bare, ref)
    assert a_sha != gen_n, "writer A did not advance the remote"

    # writer B is still based on the stale N and must be REJECTED
    sb = OperatorSession.attach(wb, run_id=run_id, session_id=session_id)
    sb.resume()
    sb.backend.release()
    rejected = False
    try:
        remote_backend.push_run_state(sb.backend, remote_ref=ref, remote=str(bare),
                                      repo_dir=CANDIDATE_REPO, message="C writer B stale")
    except Exception:
        rejected = True
    head = remote_head(bare, ref)
    assert rejected, (
        f"CONCURRENT-WRITER VIOLATION: stale writer B pushed on top of generation N "
        f"and was accepted. remote head moved {a_sha[:12]} -> {head[:12]}"
    )
    assert head == a_sha, (
        f"SILENT FORK: remote ref no longer points at writer A's commit "
        f"({head[:12]} != {a_sha[:12]})"
    )
    for w in (wa, wb, base):
        shutil.rmtree(w, ignore_errors=True)


def test_groupC_same_generation_duplicate_commit_is_monotonic():
    run_id, session_id = new_identity("Cdup")
    bare = make_bare_remote()
    ref = f"refs/heads/persistence/{run_id}"
    local = _WS / "runs" / run_id
    session = OperatorSession.create(local, run_id=run_id, session_id=session_id,
                                     event_count=30)
    session.process_one_cursor()
    session.backend.release()
    _, s1 = remote_backend.push_run_state(session.backend, remote_ref=ref,
                                          remote=str(bare), repo_dir=CANDIDATE_REPO,
                                          message="dup 1")
    rejected = False
    try:
        session2 = RunBackend.open(local, run_id=run_id, session_id=session_id,
                                   adopt_stale_owner=True)
        remote_backend.push_run_state(session2, remote_ref=ref, remote=str(bare),
                                      repo_dir=CANDIDATE_REPO, message="dup 2")
        session2.release()
    except Exception:
        rejected = True
    head = remote_head(bare, ref)
    assert rejected and head == s1, (
        f"duplicate-generation push was accepted or forked the ref "
        f"(rejected={rejected}, head={head[:12]}, s1={s1[:12]})"
    )
    shutil.rmtree(local, ignore_errors=True)


# ==========================================================================
# GROUP D -- Stage A / Stage B exact byte fidelity (independent)
# ==========================================================================
def _materialize_commit(repo: Path, commit: str, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    p1 = subprocess.Popen(["git", "archive", commit], cwd=str(repo), stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["tar", "-x", "-C", str(dest)], stdin=p1.stdout)
    p1.stdout.close()
    p2.communicate()
    return dest


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.mark.skipif(not (Path(os.environ.get("IA_CANDIDATE_REPO", "")).exists()),
                    reason="needs candidate repo with persistence commits")
def test_groupD_stageA_stageB_byte_fidelity():
    repo = Path(os.environ["IA_CANDIDATE_REPO"])
    try:
        subprocess.run(["git", "cat-file", "-e", STAGE_A_COMMIT], cwd=str(repo),
                       capture_output=True, check=True)
        subprocess.run(["git", "cat-file", "-e", STAGE_B_COMMIT], cwd=str(repo),
                       capture_output=True, check=True)
    except subprocess.CalledProcessError:
        pytest.skip("persistence commits not present in this checkout")

    base = _WS / f"fidelity-{uuid.uuid4().hex[:8]}"
    A = _materialize_commit(repo, STAGE_A_COMMIT, base / "A")
    B = _materialize_commit(repo, STAGE_B_COMMIT, base / "B")
    problems = []

    oa = json.loads((A / "owner.json").read_text())
    ob = json.loads((B / "owner.json").read_text())
    for k, v in (("run_id", CANONICAL_RUN), ("session_id", CANONICAL_SESSION)):
        if oa.get(k) != v or ob.get(k) != v:
            problems.append(f"owner {k} mismatch: A={oa.get(k)} B={ob.get(k)}")

    ma = json.loads((A / "run-state-manifest.json").read_text())
    mb = json.loads((B / "run-state-manifest.json").read_text())
    if ma["manifest_sha256"] != "5df8378c5b94b136bff2017575db0518b9574a4b44277e42656695115ed3e542":
        problems.append(f"Stage A manifest digest drift: {ma['manifest_sha256']}")
    if mb["manifest_sha256"] != "2c9accf2221c22f00c89d9f8e40a855c3e658d11806fb3c2bb9b2ef0f7110236":
        problems.append(f"Stage B manifest digest drift: {mb['manifest_sha256']}")
    for m, cur, ev, boot in ((ma, 1, "synthetic-evt-0001", None),
                             (mb, 2, "synthetic-evt-0002", None)):
        if m["cursor"] != cur or m["event_id"] != ev:
            problems.append(f"cursor/event drift: {cur}/{ev} vs {m['cursor']}/{m['event_id']}")
    for m in (ma, mb):
        rec = hashlib.sha256(json.dumps(m["artifacts"], sort_keys=True,
                                        separators=(",", ":")).encode()).hexdigest()
        if rec != m["manifest_sha256"]:
            problems.append("manifest canonical digest does not recompute")
        for rel, want in m["artifacts"].items():
            if rel.startswith("journal.sqlite"):
                p = m and (Path("A") if m is ma else Path("B")) / rel
                p = (A if m is ma else B) / rel
            elif rel.split("/")[0] == "mailbox":
                p = (A if m is ma else B) / "mailbox" / rel[len("mailbox/"):]
            else:
                p = (A if m is ma else B) / "state" / rel
            if not p.is_file() or _sha(p) != want:
                problems.append(f"slot hash mismatch {rel} ({'A' if m is ma else 'B'})")

    if ma["boot_id"] == mb["boot_id"]:
        problems.append("Stage A and Stage B boot identity are identical")

    gensA = sorted(int(p.name) for p in (A / "generations").glob("[0-9]" * 6) if p.is_dir())
    gensB = sorted(int(p.name) for p in (B / "generations").glob("[0-9]" * 6) if p.is_dir())
    if gensA != [1, 2, 3, 4]:
        problems.append(f"Stage A sealed generations {gensA} != [1,2,3,4]")
    if gensB != [1, 2, 3, 4, 5, 6, 7]:
        problems.append(f"Stage B sealed generations {gensB} != [1..7]")
    for g in (1, 2, 3, 4):
        da, db = A / "generations" / f"{g:06d}", B / "generations" / f"{g:06d}"
        for f in sorted(da.rglob("*")):
            if f.is_file():
                rel = f.relative_to(da)
                other = db / rel
                if not other.is_file() or other.read_bytes() != f.read_bytes():
                    problems.append(f"sealed generation {g} mutated across Stage A->B: {rel}")
    for rel in ("state/runtime/world.sqlite", "state/runtime/index.sqlite", "journal.sqlite"):
        for root, lbl in ((A, "A"), (B, "B")):
            p = root / rel
            if p.is_file():
                db = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
                r = db.execute("PRAGMA quick_check").fetchone()[0]
                db.close()
                if r != "ok":
                    problems.append(f"sqlite quick_check {rel} [{lbl}] = {r}")

    cA = json.loads((A / "state" / "counters.json").read_text())
    cB = json.loads((B / "state" / "counters.json").read_text())
    for k in ("reveals", "ingests", "acks", "turns_completed", "capability_side_effects"):
        if cB.get(k) != cA.get(k, 0) + 1:
            problems.append(f"counter {k}: {cA.get(k)} -> {cB.get(k)} (expected +1)")
    dA = (A / "mailbox" / "dispatch-ledger.jsonl").read_bytes()
    dB = (B / "mailbox" / "dispatch-ledger.jsonl").read_bytes()
    if not dB.startswith(dA):
        problems.append("dispatch ledger prefix not preserved")
    if len(dB.splitlines()) != len(dA.splitlines()) + 2:
        problems.append("dispatch ledger did not advance by exactly 2 rounds")
    for rel in ("state/capability-ledger.jsonl", "mailbox/archive.jsonl"):
        pa, pb = A / rel, B / rel
        if pb.is_file() and pa.is_file() and not pb.read_bytes().startswith(pa.read_bytes()):
            problems.append(f"prefix not preserved: {rel}")

    shutil.rmtree(base, ignore_errors=True)
    assert not problems, "STAGE A/B FIDELITY VIOLATIONS:\n  - " + "\n  - ".join(problems)


# ==========================================================================
# GROUP E -- exactly-once / no duplicate under retry
# ==========================================================================
def test_groupE_repeated_ack_is_idempotent():
    run_id, session_id = new_identity("Eack")
    local = _WS / "runs" / run_id
    session = OperatorSession.create(local, run_id=run_id, session_id=session_id,
                                     event_count=30)
    session.process_one_cursor()
    before = session.counters()
    # replay the same cursor in a fresh attached session (retry semantics)
    s2 = OperatorSession.attach(local, run_id=run_id, session_id=session_id)
    s2.process_one_cursor()
    after = s2.counters()
    s2.backend.release()
    assert after["acks"] == before["acks"] + 1, (
        f"ACK not exactly-once across cursor: {before['acks']} -> {after['acks']}"
    )
    rs = json.loads((local / "state" / "runtime" / "release_state.json").read_text())
    assert rs.get("last_acked_sequence") == 2 and rs.get("next_sequence") == 3, (
        f"release receipt not monotonic: {rs}"
    )
    shutil.rmtree(local, ignore_errors=True)


def test_groupE_no_duplicate_capability_or_output_within_a_cursor():
    run_id, session_id = new_identity("Edup")
    local = _WS / "runs" / run_id
    session = OperatorSession.create(local, run_id=run_id, session_id=session_id,
                                     event_count=30)
    out = session.process_one_cursor()
    ev = out["projection"]["event_id"]
    oc = session.observation_counts(ev)
    assert oc["assistant_outputs"] == 1, (
        f"duplicate assistant output for one cursor: {oc['assistant_outputs']}"
    )
    caps = session.report()["capability_ledger"]
    keys = [c.get("key") or c.get("capability_key") for c in caps]
    assert len(keys) == len(set(keys)), f"duplicate capability side effect keys: {keys}"
    session.backend.release()
    shutil.rmtree(local, ignore_errors=True)


# ==========================================================================
# GROUP F -- Git-as-authoritative-store semantics
# ==========================================================================
def test_groupF_commit_pin_is_immutable_identity():
    run_id, session_id = new_identity("Fpin")
    bare = make_bare_remote()
    ref = f"refs/heads/persistence/{run_id}"
    local = _WS / "runs" / run_id
    session = OperatorSession.create(local, run_id=run_id, session_id=session_id,
                                     event_count=30)
    session.process_one_cursor()
    session.backend.release()
    _, sha = remote_backend.push_run_state(session.backend, remote_ref=ref,
                                           remote=str(bare), repo_dir=CANDIDATE_REPO,
                                           message="F pin")
    tree1 = git(["rev-parse", f"{sha}^{{tree}}"], cwd=CANDIDATE_REPO).stdout.strip()
    # re-reading the same commit must give the same tree
    tree2 = git(["rev-parse", f"{sha}^{{tree}}"], cwd=CANDIDATE_REPO).stdout.strip()
    assert tree1 == tree2
    # advancing the ref must not change the pinned commit's content
    s2 = OperatorSession.attach(local, run_id=run_id, session_id=session_id)
    s2.resume()
    s2.backend.release()
    _, sha2 = remote_backend.push_run_state(s2.backend, remote_ref=ref,
                                            remote=str(bare), repo_dir=CANDIDATE_REPO,
                                            message="F pin 2")
    tree3 = git(["rev-parse", f"{sha}^{{tree}}"], cwd=CANDIDATE_REPO).stdout.strip()
    assert sha2 != sha and tree1 == tree3, "pinned commit identity is not immutable"
    shutil.rmtree(local, ignore_errors=True)


def test_groupF_ref_drift_does_not_silently_open_new_state():
    """If the ref moves, an explicit commit pin must still open the pinned
    state, and an unpinned open must not silently succeed on a different
    generation without recording it."""
    run_id, session_id = new_identity("Fdrift")
    bare = make_bare_remote()
    ref = f"refs/heads/persistence/{run_id}"
    local = _WS / "runs" / run_id
    session = OperatorSession.create(local, run_id=run_id, session_id=session_id,
                                     event_count=30)
    session.process_one_cursor()
    session.backend.release()
    _, sha1 = remote_backend.push_run_state(session.backend, remote_ref=ref,
                                            remote=str(bare), repo_dir=CANDIDATE_REPO,
                                            message="F drift 1")
    s2 = OperatorSession.attach(local, run_id=run_id, session_id=session_id)
    s2.resume()
    s2.backend.release()
    _, sha2 = remote_backend.push_run_state(s2.backend, remote_ref=ref,
                                            remote=str(bare), repo_dir=CANDIDATE_REPO,
                                            message="F drift 2")
    assert remote_head(bare, ref) == sha2
    # explicit pin to the OLD commit must still yield the OLD cursor
    fresh = _WS / "runs" / f"{run_id}-pin-old"
    try:
        snap = run_child(["--mode", "materialize-report", "--root", str(fresh),
                          "--run-id", run_id, "--session-id", session_id,
                          "--remote", str(bare), "--remote-ref", ref,
                          "--commit-sha", sha1, "--repo-dir", str(CANDIDATE_REPO)])
        assert snap["cursor"] == 1, (
            f"commit pin ignored: expected pinned cursor 1, got {snap['cursor']}"
        )
    finally:
        shutil.rmtree(fresh, ignore_errors=True)
        shutil.rmtree(local, ignore_errors=True)


def test_groupF_unreachable_commit_pin_fails_closed():
    """A pin that is not in the commit tree must fail closed, not produce a
    silently empty/half materialization."""
    run_id, session_id = new_identity("Fbad")
    bare = make_bare_remote()
    ref = f"refs/heads/persistence/{run_id}"
    local = _WS / "runs" / run_id
    session = OperatorSession.create(local, run_id=run_id, session_id=session_id,
                                     event_count=30)
    session.process_one_cursor()
    session.backend.release()
    remote_backend.push_run_state(session.backend, remote_ref=ref,
                                  remote=str(bare), repo_dir=CANDIDATE_REPO,
                                  message="F bad")
    fresh = _WS / "runs" / f"{run_id}-bad"
    failed = False
    try:
        run_child(["--mode", "materialize-report", "--root", str(fresh),
                   "--run-id", run_id, "--session-id", session_id,
                   "--remote", str(bare), "--remote-ref", ref,
                   "--commit-sha", "0" * 40, "--repo-dir", str(CANDIDATE_REPO)])
    except AssertionError:
        failed = True
    finally:
        shutil.rmtree(fresh, ignore_errors=True)
        shutil.rmtree(local, ignore_errors=True)
    assert failed, (
        "FAIL-OPEN: an unreachable commit pin produced a successful "
        "materialization instead of failing closed"
    )
