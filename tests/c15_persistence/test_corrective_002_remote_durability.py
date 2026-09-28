"""Corrective-002 regression gates for cross-Arena remote durability.

These tests target the two independently accepted blockers from the failed
63ca5923 candidate:

* IA-BLK-PERSIST-001: K1-K5 existed only in local state; remote Git persistence
  happened after a completed cursor in the Stage A/B wrapper.
* IA-BLK-PERSIST-002: backend reopen / reattach did not admit on the complete
  sealed-generation chain.

No real Resident is used.  Every run/ref is synthetic and disposable.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "killpoints"))

from harness import REPO_ROOT, new_root, repo_python_env, wipe  # noqa: E402

from tools.c15_persistence.backend import BackendError, RunBackend  # noqa: E402
from tools.c15_persistence.operator_session import KILL_POINTS, OperatorSession  # noqa: E402


def _bare_remote(tmp_path: Path, label: str) -> Path:
    bare = tmp_path / f"{label}-{uuid.uuid4().hex[:8]}.git"
    subprocess.run(
        ["git", "init", "--bare", "-q", str(bare)],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    return bare


def _remote_head(remote: Path, ref: str) -> str:
    completed = subprocess.run(
        ["git", "ls-remote", str(remote), ref],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout.strip(), f"remote ref missing: {ref}"
    return completed.stdout.strip().split()[0]


def _remote_json(remote: Path, commit_sha: str, path: str) -> dict:
    raw = subprocess.check_output(
        ["git", f"--git-dir={remote}", "show", f"{commit_sha}:{path}"],
        text=True,
    )
    return json.loads(raw)


def _run_cli(
    *,
    root: Path,
    run_id: str,
    session_id: str,
    mode: str,
    remote: Path,
    remote_ref: str,
    kill_at: str | None = None,
) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        "-m",
        "tools.c15_persistence.probe_cli",
        "--root",
        str(root),
        "--run-id",
        run_id,
        "--session-id",
        session_id,
        "--mode",
        mode,
        "--remote-ref",
        remote_ref,
        "--remote",
        str(remote),
        "--repo-dir",
        str(REPO_ROOT),
        "--require-remote-durability",
    ]
    if kill_at is not None:
        cmd.extend(["--kill-at", kill_at])
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=repo_python_env(),
        capture_output=True,
        text=True,
        timeout=1200,
    )


@pytest.mark.parametrize("kill_point", KILL_POINTS)
def test_k1_k5_survive_total_local_cache_loss_from_remote_only(
    tmp_path: Path, kill_point: str
) -> None:
    """Every frozen K barrier must already be authoritative on the remote ref."""

    remote = _bare_remote(tmp_path, kill_point.lower())
    token = uuid.uuid4().hex[:10]
    run_id = f"synthetic-run-c002-{kill_point.lower()}-{token}"
    session_id = f"synthetic-session-c002-{kill_point.lower()}-{token}"
    remote_ref = f"refs/heads/persistence/{run_id}"

    first_root = new_root(f"c002-{kill_point.lower()}-first") / "backend"
    fresh_parent: Path | None = None
    try:
        killed = _run_cli(
            root=first_root,
            run_id=run_id,
            session_id=session_id,
            mode="create",
            remote=remote,
            remote_ref=remote_ref,
            kill_at=kill_point,
        )
        assert killed.returncode == -signal.SIGKILL, (
            f"{kill_point}: expected SIGKILL, got {killed.returncode}\n"
            f"stdout={killed.stdout}\nstderr={killed.stderr}"
        )

        barrier_head = _remote_head(remote, remote_ref)
        marker = _remote_json(remote, barrier_head, "state/remote-barrier.json")
        assert marker["point"] == kill_point
        assert marker["cursor"] == 1

        # The entire execution environment's run cache is gone.  Recovery may
        # use only the remote commit/ref, never files left by the killed process.
        first_parent = first_root.parent
        wipe(first_parent)
        assert not first_root.exists()

        fresh_parent = new_root(f"c002-{kill_point.lower()}-fresh")
        fresh_root = fresh_parent / "backend"
        resumed = _run_cli(
            root=fresh_root,
            run_id=run_id,
            session_id=session_id,
            mode="materialize-resume",
            remote=remote,
            remote_ref=remote_ref,
        )
        assert resumed.returncode == 0, (
            f"{kill_point}: remote-only recovery failed\n"
            f"stdout={resumed.stdout}\nstderr={resumed.stderr}"
        )
        outcome = json.loads(resumed.stdout)
        assert outcome["projection"]["sequence"] == 1
        assert outcome["ack"]["status"] == "acked"
        assert outcome["ack"]["sequence"] == 1
        assert outcome["ack"]["next_sequence"] == 2

        observed = outcome["observed"]
        counters = observed["counters"]
        assert counters["reveals"] == 1
        assert counters["ingests"] == 1
        assert counters["acks"] == 1
        assert counters["turns_completed"] == 1
        assert counters["capability_side_effects"] == 1
        assert len(observed["dispatch_ledger"]) == 2
        assert observed["metering_rows"] == 2
        assert observed["observation_counts"]["observations_for_event"] == 1
        assert observed["observation_counts"]["assistant_outputs"] == 1

        final_head = _remote_head(remote, remote_ref)
        assert final_head != barrier_head
        final_marker = _remote_json(remote, final_head, "state/remote-barrier.json")
        assert final_marker["point"] == "ACKED"
        assert final_marker["cursor"] == 1
    finally:
        if first_root.parent.exists():
            wipe(first_root.parent)
        if fresh_parent is not None:
            wipe(fresh_parent)


def test_remote_compare_and_swap_rejects_stale_writer(tmp_path: Path) -> None:
    """A stale tree may not be fast-forwarded on top of somebody else's head."""

    remote = _bare_remote(tmp_path, "cas")
    token = uuid.uuid4().hex[:10]
    run_id = f"synthetic-run-c002-cas-{token}"
    session_id = f"synthetic-session-c002-cas-{token}"
    remote_ref = f"refs/heads/persistence/{run_id}"

    origin_parent = new_root("c002-cas-origin")
    a_parent = new_root("c002-cas-a")
    b_parent = new_root("c002-cas-b")
    try:
        origin = OperatorSession.create(
            origin_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            remote_ref=remote_ref,
            remote=str(remote),
            repo_dir=REPO_ROOT,
            require_remote_durability=True,
        )
        head0 = _remote_head(remote, remote_ref)
        origin.backend.release()

        a = OperatorSession.materialize_and_attach(
            a_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            remote_ref=remote_ref,
            commit_sha=head0,
            remote=str(remote),
            repo_dir=REPO_ROOT,
        )
        b = OperatorSession.materialize_and_attach(
            b_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            remote_ref=remote_ref,
            commit_sha=head0,
            remote=str(remote),
            repo_dir=REPO_ROOT,
        )

        a.bump("cas_writer_a")
        _ref, head_a = a.push_to_remote(message="IA corrective-002 CAS writer A")
        assert _remote_head(remote, remote_ref) == head_a

        b.bump("cas_writer_b")
        with pytest.raises(BackendError, match="remote CAS conflict"):
            b.push_to_remote(message="IA corrective-002 stale writer B")
        assert _remote_head(remote, remote_ref) == head_a
        a.backend.release()
        b.backend.release()
    finally:
        wipe(origin_parent)
        wipe(a_parent)
        wipe(b_parent)


def _completed_local_run(label: str) -> tuple[Path, str, str]:
    parent = new_root(label)
    token = uuid.uuid4().hex[:10]
    run_id = f"synthetic-run-{label}-{token}"
    session_id = f"synthetic-session-{label}-{token}"
    session = OperatorSession.create(
        parent / "backend", run_id=run_id, session_id=session_id
    )
    outcome = session.process_one_cursor()
    assert outcome["ack"]["status"] == "acked"
    session.backend.release()
    return parent, run_id, session_id


def test_reopen_rejects_deleted_middle_sealed_generation() -> None:
    parent, run_id, session_id = _completed_local_run("c002-gen-gap")
    try:
        victim = parent / "backend" / "generations" / "000002"
        assert victim.is_dir()
        os.chmod(victim, 0o700)
        shutil.rmtree(victim)
        with pytest.raises(BackendError, match="generation chain"):
            RunBackend.open(
                parent / "backend", run_id=run_id, session_id=session_id,
                adopt_stale_owner=True,
            )
    finally:
        wipe(parent)


def test_reopen_rejects_modified_sealed_generation_artifact() -> None:
    parent, run_id, session_id = _completed_local_run("c002-gen-tamper")
    try:
        target = parent / "backend" / "generations" / "000001" / "journal.sqlite"
        assert target.is_file()
        os.chmod(target, 0o600)
        target.write_bytes(target.read_bytes() + b"tamper")
        os.chmod(target, 0o400)
        with pytest.raises(BackendError, match="generation artifact corruption"):
            RunBackend.open(
                parent / "backend", run_id=run_id, session_id=session_id,
                adopt_stale_owner=True,
            )
    finally:
        wipe(parent)


def test_reopen_rejects_incomplete_unsealed_generation() -> None:
    parent, run_id, session_id = _completed_local_run("c002-gen-incomplete")
    try:
        generations = parent / "backend" / "generations"
        existing = sorted(int(p.name) for p in generations.iterdir() if p.is_dir())
        incomplete = generations / f"{max(existing) + 1:06d}"
        incomplete.mkdir(mode=0o700)
        (incomplete / "partial.bin").write_bytes(b"partial")
        with pytest.raises(BackendError, match="generation chain"):
            RunBackend.open(
                parent / "backend", run_id=run_id, session_id=session_id,
                adopt_stale_owner=True,
            )
    finally:
        wipe(parent)
