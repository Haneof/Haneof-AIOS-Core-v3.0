"""Retained (non-binding) Corrective-003 regression probes.

The three PM-ruled release-binding blockers (C002-001 / C002-002 / C002-004) are
probed in ``test_corrective_003_binding_blockers.py`` against accepted Core
semantics.  This file keeps the historical Independent-Acceptance findings that
the PM classified as NON-BLOCKING HARDENING for C15 release:

* ``C002-003`` coordinated/history tampering - the ordinary corruption checks
  (seal content, exact artifact set, immutable history head, authoritative
  remote short history) must stay effective and must not be weakened;
* ``C002-005`` cross-run remote config/ref transplantation stays rejected by the
  low-risk identity assertion (no new security architecture);
* ``C002-006`` the atomic expected-old-value lease stays in force for the single
  controlled-writer model (no general distributed CAS subsystem).

None of these is a C15 release gate; they are preserved so the corrective cannot
silently regress previously detected problems.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "killpoints"))

from harness import REPO_ROOT, new_root, repo_python_env, wipe  # noqa: E402

from tools.c15_persistence import remote_backend  # noqa: E402
from tools.c15_persistence.backend import (  # noqa: E402
    BackendError,
    GenerationStore,
    RunBackend,
    canonical_json,
    digest,
)
from tools.c15_persistence.operator_session import OperatorSession  # noqa: E402


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
    """PROBE: C002-003-A (retained NON-BLOCKING hardening probe)."""
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
    """PROBE: C002-003-B (retained NON-BLOCKING hardening probe)."""
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
    """PROBE: C002-003-C (retained NON-BLOCKING hardening probe)."""
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


def test_cross_run_remote_config_and_ref_transplant_is_rejected(tmp_path: Path) -> None:
    """PROBE: C002-005-A (retained NON-BLOCKING hardening probe)."""
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
    """PROBE: C002-003-D (retained NON-BLOCKING hardening probe)."""
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


def test_atomic_lease_rejects_ref_delete_between_check_and_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PROBE: C002-006-A (retained NON-BLOCKING hardening probe)."""
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
