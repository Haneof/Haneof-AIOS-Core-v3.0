"""Corrective-003 regressions for the six C002 Independent Acceptance blockers."""

from __future__ import annotations

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

sys.path.insert(0, str(Path(__file__).resolve().parent / "killpoints"))

from harness import REPO_ROOT, new_root, repo_python_env, wipe  # noqa: E402

from tools.c15_persistence import provider as provider_module  # noqa: E402
from tools.c15_persistence import remote_backend  # noqa: E402
from tools.c15_persistence.backend import (  # noqa: E402
    BackendError,
    GenerationStore,
    RunBackend,
    canonical_json,
    digest,
)
from tools.c15_persistence.operator_session import (  # noqa: E402
    OperatorSession,
    RemoteDurabilityAbort,
)


def _bare_remote(tmp_path: Path, label: str) -> Path:
    remote = tmp_path / f"{label}-{uuid.uuid4().hex[:8]}.git"
    subprocess.run(
        ["git", "init", "--bare", "-q", str(remote)],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    return remote


def _remote_head(remote: Path, ref: str) -> str | None:
    completed = subprocess.run(
        ["git", "ls-remote", str(remote), ref],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    if not completed.stdout.strip():
        return None
    return completed.stdout.strip().split()[0]


def _run_cli(
    *,
    root: Path,
    run_id: str,
    session_id: str,
    mode: str,
    remote: Path,
    remote_ref: str,
    kill_at: str | None = None,
    kill_round: int | None = None,
) -> subprocess.CompletedProcess[str]:
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
    if kill_round is not None:
        cmd.extend(["--kill-round", str(kill_round)])
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=repo_python_env(),
        capture_output=True,
        text=True,
        timeout=1200,
    )


def _remote_session(tmp_path: Path, label: str) -> tuple[OperatorSession, Path, str, str, str, Path]:
    remote = _bare_remote(tmp_path, label)
    token = uuid.uuid4().hex[:10]
    run_id = f"synthetic-run-c003-{label}-{token}"
    session_id = f"synthetic-session-c003-{label}-{token}"
    remote_ref = f"refs/heads/persistence/{run_id}"
    parent = new_root(f"c003-{label}")
    session = OperatorSession.create(
        parent / "backend",
        run_id=run_id,
        session_id=session_id,
        remote_ref=remote_ref,
        remote=str(remote),
        repo_dir=REPO_ROOT,
        require_remote_durability=True,
    )
    return session, remote, run_id, session_id, remote_ref, parent


def test_k4_remote_failure_is_fatal_and_cannot_reach_ack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session, _remote, _run, _sid, _ref, parent = _remote_session(tmp_path, "k4-fatal")
    original = session.backend.push_to_remote

    def fail_only_k4(**kwargs):
        if "point=K4_AFTER_REPLY_AUTHENTICATED" in str(kwargs.get("message") or ""):
            raise BackendError("synthetic K4 remote outage")
        return original(**kwargs)

    monkeypatch.setattr(session.backend, "push_to_remote", fail_only_k4)
    try:
        with pytest.raises(RemoteDurabilityAbort, match="K4 remote-authoritative persistence failed"):
            session.process_one_cursor()

        counters = session.counters()
        assert counters.get("acks", 0) == 0
        assert counters.get("turns_completed", 0) == 0
        # K4 happens after round-0 provider return/capability but before round 1.
        dispatches = provider_module.read_ledger(session.mailbox)
        assert len(dispatches) == 1
        assert len({row["request_id"] for row in dispatches}) == 1
    finally:
        session.backend.release()
        wipe(parent)


def test_second_round_k3_survives_total_local_loss_remote_only(tmp_path: Path) -> None:
    remote = _bare_remote(tmp_path, "k3-round1")
    token = uuid.uuid4().hex[:10]
    run_id = f"synthetic-run-c003-k3r1-{token}"
    session_id = f"synthetic-session-c003-k3r1-{token}"
    remote_ref = f"refs/heads/persistence/{run_id}"
    first_parent = new_root("c003-k3r1-first")
    fresh_parent: Path | None = None
    try:
        killed = _run_cli(
            root=first_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="create",
            remote=remote,
            remote_ref=remote_ref,
            kill_at="K3_AFTER_REQUEST_DISPATCH",
            kill_round=1,
        )
        assert killed.returncode == -signal.SIGKILL, (
            f"expected round-1 K3 SIGKILL, got {killed.returncode}\n"
            f"stdout={killed.stdout}\nstderr={killed.stderr}"
        )
        barrier_head = _remote_head(remote, remote_ref)
        assert barrier_head is not None

        # Destroy every local run byte. The remote K3 snapshot is the only source.
        wipe(first_parent)
        fresh_parent = new_root("c003-k3r1-fresh")
        resumed = _run_cli(
            root=fresh_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="materialize-resume",
            remote=remote,
            remote_ref=remote_ref,
        )
        assert resumed.returncode == 0, (
            f"round-1 K3 remote recovery failed\nstdout={resumed.stdout}\nstderr={resumed.stderr}"
        )
        outcome = json.loads(resumed.stdout)
        assert outcome["ack"]["status"] == "acked"
        assert outcome["ack"]["sequence"] == 1
        assert outcome["ack"]["next_sequence"] == 2
        observed = outcome["observed"]
        assert observed["counters"]["reveals"] == 1
        assert observed["counters"]["ingests"] == 1
        assert observed["counters"]["capability_side_effects"] == 1
        assert observed["counters"]["acks"] == 1
        assert observed["metering_rows"] == 2
        dispatch_ledger = observed["dispatch_ledger"]
        assert len(dispatch_ledger) == 2
        assert len({row["request_id"] for row in dispatch_ledger}) == 2
    finally:
        if first_parent.exists():
            wipe(first_parent)
        if fresh_parent is not None:
            wipe(fresh_parent)


def _completed_local_run(label: str) -> tuple[Path, str, str]:
    parent = new_root(label)
    token = uuid.uuid4().hex[:10]
    run_id = f"synthetic-run-{label}-{token}"
    session_id = f"synthetic-session-{label}-{token}"
    session = OperatorSession.create(parent / "backend", run_id=run_id, session_id=session_id)
    outcome = session.process_one_cursor()
    assert outcome["ack"]["status"] == "acked"
    session.backend.release()
    return parent, run_id, session_id


def test_generation_admission_rejects_seal_content_tamper() -> None:
    parent, run_id, session_id = _completed_local_run("c003-seal")
    try:
        seal = parent / "backend" / "generations" / "000001" / ".sealed"
        os.chmod(seal.parent, 0o700)
        os.chmod(seal, 0o600)
        seal.write_text("999999\n", encoding="utf-8")
        with pytest.raises(BackendError, match="seal content mismatch"):
            RunBackend.open(parent / "backend", run_id=run_id, session_id=session_id, adopt_stale_owner=True)
    finally:
        wipe(parent)


def test_generation_admission_rejects_unexpected_artifact() -> None:
    parent, run_id, session_id = _completed_local_run("c003-extra")
    try:
        generation = parent / "backend" / "generations" / "000001"
        os.chmod(generation, 0o700)
        (generation / "unexpected.bin").write_bytes(b"unexpected")
        with pytest.raises(BackendError, match="artifact set mismatch"):
            RunBackend.open(parent / "backend", run_id=run_id, session_id=session_id, adopt_stale_owner=True)
    finally:
        wipe(parent)


def test_generation_history_cannot_be_shortened_by_lowering_current_ledger() -> None:
    parent, run_id, session_id = _completed_local_run("c003-history")
    try:
        root = parent / "backend"
        generations = sorted(p for p in (root / "generations").iterdir() if p.is_dir())
        assert len(generations) >= 2
        latest = int(generations[-1].name)
        victim = generations[-1]
        os.chmod(victim, 0o700)
        shutil.rmtree(victim)
        with sqlite3.connect(root / "journal.sqlite") as db:
            db.execute("UPDATE ledger SET value=? WHERE name='generation'", (str(latest - 1),))
            db.commit()
        with pytest.raises(BackendError, match="immutable history head"):
            RunBackend.open(root, run_id=run_id, session_id=session_id, adopt_stale_owner=True)
    finally:
        wipe(parent)


def test_missing_remote_config_fails_closed_instead_of_local_downgrade(tmp_path: Path) -> None:
    session, _remote, run_id, session_id, _ref, parent = _remote_session(tmp_path, "missing-config")
    try:
        session.backend.release()
        config = parent / "backend" / "remote-durability.json"
        assert config.is_file()
        config.unlink()
        with pytest.raises(BackendError, match="missing remote durability config"):
            OperatorSession.attach(parent / "backend", run_id=run_id, session_id=session_id)
    finally:
        wipe(parent)


def test_cross_run_remote_config_and_ref_transplant_is_rejected(tmp_path: Path) -> None:
    remote = _bare_remote(tmp_path, "cross-run")
    parents: list[Path] = []
    sessions: list[OperatorSession] = []
    try:
        for label in ("a", "b"):
            token = uuid.uuid4().hex[:8]
            run_id = f"synthetic-run-c003-cross-{label}-{token}"
            session_id = f"synthetic-session-c003-cross-{label}-{token}"
            remote_ref = f"refs/heads/persistence/{run_id}"
            parent = new_root(f"c003-cross-{label}")
            session = OperatorSession.create(
                parent / "backend",
                run_id=run_id,
                session_id=session_id,
                remote_ref=remote_ref,
                remote=str(remote),
                repo_dir=REPO_ROOT,
                require_remote_durability=True,
            )
            parents.append(parent)
            sessions.append(session)

        a, b = sessions
        a_root, b_root = parents[0] / "backend", parents[1] / "backend"
        a.backend.release()
        b.backend.release()

        # Copy both attacker-controlled locator files from B into A.
        shutil.copy2(b_root / "remote-durability.json", a_root / "remote-durability.json")
        shutil.copy2(b_root / ".remote-head", a_root / ".remote-head")

        with pytest.raises(BackendError, match="not canonical|remote durability config/binding mismatch|remote authority"):
            OperatorSession.attach(
                a_root,
                run_id=str(a.backend.owner["run_id"]),
                session_id=str(a.backend.owner["session_id"]),
            )

        with pytest.raises(BackendError, match="not canonical"):
            remote_backend.push_run_state(
                a.backend,
                remote_ref=f"refs/heads/persistence/{b.backend.owner['run_id']}",
                remote=str(remote),
                repo_dir=REPO_ROOT,
            )
    finally:
        for session in sessions:
            session.backend.release()
        for parent in parents:
            wipe(parent)


def test_remote_authority_rejects_coordinated_short_history_even_if_local_head_is_rehashed(
    tmp_path: Path,
) -> None:
    session, remote, run_id, session_id, remote_ref, parent = _remote_session(
        tmp_path, "coordinated-history"
    )
    try:
        outcome = session.process_one_cursor()
        assert outcome["ack"]["status"] == "acked"
        authoritative_head = _remote_head(remote, remote_ref)
        assert authoritative_head is not None
        session.backend.release()

        root = parent / "backend"
        generations = sorted(p for p in (root / "generations").iterdir() if p.is_dir())
        assert len(generations) >= 2
        victim = generations[-1]
        shortened_to = int(generations[-2].name)
        os.chmod(victim, 0o700)
        shutil.rmtree(victim)
        with sqlite3.connect(root / "journal.sqlite") as db:
            db.execute(
                "UPDATE ledger SET value=? WHERE name='generation'",
                (str(shortened_to),),
            )
            db.commit()

        # Rebuild the local self-hash so purely local checks see a coherent
        # shortened history. Remote exact-head admission must still reject it.
        manifest = root / "generations" / f"{shortened_to:06d}" / "manifest.json"
        head_path = root / GenerationStore.HEAD_NAME
        old_head = json.loads(head_path.read_text(encoding="utf-8"))
        base = {
            "generation": shortened_to,
            "manifest_file_sha256": digest(manifest.read_bytes()),
            "previous_head_sha256": old_head.get("previous_head_sha256"),
            "version": GenerationStore.HEAD_VERSION,
        }
        forged = {**base, "head_sha256": digest(canonical_json(base))}
        head_path.write_text(json.dumps(forged, sort_keys=True) + "\n", encoding="utf-8")

        with pytest.raises(
            BackendError,
            match="immutable generation head differs from authoritative remote commit",
        ):
            OperatorSession.attach(
                root,
                run_id=run_id,
                session_id=session_id,
                repo_dir=REPO_ROOT,
            )
        assert _remote_head(remote, remote_ref) == authoritative_head
    finally:
        session.backend.release()
        wipe(parent)


def test_k5_commit_tree_before_push_crash_recovers_from_prior_remote_k3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session, remote, run_id, session_id, remote_ref, parent = _remote_session(
        tmp_path, "k5-prepush"
    )
    original_commit = remote_backend.commit_backend_tree
    tripped = {"value": False}

    def crash_after_commit_tree(*args, **kwargs):
        result = original_commit(*args, **kwargs)
        message = str(kwargs.get("message") or "")
        if "point=K5_AFTER_APPLIED_BEFORE_ACK" in message:
            tripped["value"] = True
            raise BackendError("synthetic crash after commit-tree before remote push")
        return result

    monkeypatch.setattr(remote_backend, "commit_backend_tree", crash_after_commit_tree)
    fresh_parent: Path | None = None
    try:
        with pytest.raises(BackendError, match="commit-tree before remote push"):
            session.process_one_cursor()
        assert tripped["value"], "K5 pre-push crash hook was not reached"
        prior_remote = _remote_head(remote, remote_ref)
        assert prior_remote is not None
        session.backend.release()

        wipe(parent)
        fresh_parent = new_root("c003-k5-prepush-fresh")
        recovered = OperatorSession.materialize_and_attach(
            fresh_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            remote_ref=remote_ref,
            commit_sha=prior_remote,
            remote=str(remote),
            repo_dir=REPO_ROOT,
        )
        outcome = recovered.resume()
        assert outcome["ack"]["status"] == "acked"
        assert outcome["ack"]["sequence"] == 1
        observed = outcome["observed"]
        assert observed["counters"]["reveals"] == 1
        assert observed["counters"]["ingests"] == 1
        assert observed["counters"]["capability_side_effects"] == 1
        assert observed["counters"]["acks"] == 1
        assert len(observed["dispatch_ledger"]) == 2
        assert observed["metering_rows"] == 2
        recovered.backend.release()
    finally:
        session.backend.release()
        if parent.exists():
            wipe(parent)
        if fresh_parent is not None:
            wipe(fresh_parent)


def test_atomic_lease_rejects_ref_delete_between_check_and_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session, remote, _run_id, _session_id, remote_ref, parent = _remote_session(tmp_path, "lease-delete")
    original_commit = remote_backend.commit_backend_tree
    expected_before = _remote_head(remote, remote_ref)
    assert expected_before is not None

    def commit_then_delete(*args, **kwargs):
        result = original_commit(*args, **kwargs)
        deleted = subprocess.run(
            ["git", "push", str(remote), f":{remote_ref}"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert deleted.returncode == 0, deleted.stderr
        assert _remote_head(remote, remote_ref) is None
        return result

    monkeypatch.setattr(remote_backend, "commit_backend_tree", commit_then_delete)
    try:
        session.bump("lease_race_probe")
        with pytest.raises(BackendError, match="atomic CAS/lease rejected"):
            session.push_to_remote(message="C003 atomic lease delete race")
        assert _remote_head(remote, remote_ref) is None
    finally:
        session.backend.release()
        wipe(parent)
