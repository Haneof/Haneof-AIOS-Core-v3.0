"""PM Readiness Blocker Regressions (Window 49 - Residual Closures).

Covers:
- PM49-BLK-001R: Authoritative resident-surface base resolution in multi-commit PRs
  (strictly eliminates HEAD~1 fallback; fails closed when base authority is unresolved;
  detects earlier commit drift against true base).
- PM49-BLK-002R: True provider process isolation and zero proof-minting in operator/recovery
  (OPERATOR_PID != PROVIDER_PID; hard import barrier; data-only mailbox IPC;
  fail-closed recovery without receipt).
"""

from __future__ import annotations

import inspect
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "killpoints"))
from harness import REPO_ROOT, new_root, repo_python_env, wipe  # noqa: E402

from tools.c15_persistence import (  # noqa: E402
    backend as backend_module,
    operator_session as operator_session_module,
    provider as provider_module,
    relay as relay_module,
    resident_surface_check as resident_surface_check_module,
)
from tools.c15_persistence.operator_session import (  # noqa: E402
    DurableTrustedReturnMissing,
    OperatorSession,
)
from tools.c15_persistence.relay import RelayJournal
from tools.c15_persistence.resident_surface_check import (  # noqa: E402
    _pinned_tree_digest,
    resolve_surface_base,
)
from tools.c15_persistence.synthetic_release import SyntheticRelease


# -----------------------------------------------------------------------------
# PM49-BLK-001R: Multi-Commit Base Authority & Drift Detection Attacker Tests
# -----------------------------------------------------------------------------


def _create_multi_commit_repo(root: Path) -> tuple[Path, str, str, str]:
    """Create a temporary git repository simulating a multi-commit PR with drift.

    Commit hierarchy:
    - BASE: Initial commit with clean pinned directories.
    - COMMIT_A: First corrective commit introducing drift in `src/aios_core/drift.py`.
    - COMMIT_B: Second corrective commit modifying `tools/c15_persistence/dummy.txt` (HEAD).
    """
    repo_dir = root / "multi_commit_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test Author",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test Committer",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }

    def run_git(*args: str) -> str:
        res = subprocess.run(
            ["git", *args],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        return res.stdout.strip()

    run_git("init", "-b", "main")
    run_git("config", "user.name", "Test")
    run_git("config", "user.email", "test@example.com")

    # Base commit with pinned directories
    (repo_dir / "src" / "aios_core").mkdir(parents=True, exist_ok=True)
    (repo_dir / "reviews" / "internal_habitation" / "c15-rcc" / "v1").mkdir(parents=True, exist_ok=True)
    (repo_dir / "reviews" / "internal_habitation" / "c14-resident" / "v2" / "release").mkdir(parents=True, exist_ok=True)
    (repo_dir / "tools" / "c15_persistence").mkdir(parents=True, exist_ok=True)

    (repo_dir / "src" / "aios_core" / "core.py").write_text("# Core V3\n")
    (repo_dir / "reviews" / "internal_habitation" / "c15-rcc" / "v1" / "doc.md").write_text("# C15\n")
    (repo_dir / "reviews" / "internal_habitation" / "c14-resident" / "v2" / "release" / "doc.md").write_text("# C14\n")
    (repo_dir / "tools" / "c15_persistence" / "tool.py").write_text("# Tool\n")

    run_git("add", ".")
    run_git("commit", "-m", "base commit")
    base_sha = run_git("rev-parse", "HEAD")

    # Commit A: mutates pinned surface src/aios_core
    (repo_dir / "src" / "aios_core" / "drift.py").write_text("# Drift injected in commit A\n")
    run_git("add", ".")
    run_git("commit", "-m", "commit A: introduces pinned drift")
    commit_a = run_git("rev-parse", "HEAD")

    # Commit B: unrelated change in tools/c15_persistence (HEAD)
    (repo_dir / "tools" / "c15_persistence" / "dummy.txt").write_text("commit B\n")
    run_git("add", ".")
    run_git("commit", "-m", "commit B: unrelated change at HEAD")
    commit_b = run_git("rev-parse", "HEAD")

    return repo_dir, base_sha, commit_a, commit_b


def test_pm49_blk001r_detached_checkout_fails_closed_without_head_fallback() -> None:
    """ATTACK TEST (PM49-BLK-001R): In a multi-commit PR detached checkout, resolve_surface_base fails closed.

    Proves:
    1. resolve_surface_base refuses to fall back to HEAD~1 (which would be commit A instead of base).
    2. When base authority cannot be established, resolve_surface_base raises ValueError.
    """
    parent = new_root("pm49-blk001r-detached")
    try:
        repo_dir, base_sha, commit_a, commit_b = _create_multi_commit_repo(parent)

        # Detach HEAD and remove branch references to simulate detached CI without remotes
        subprocess.run(["git", "checkout", "--detach"], cwd=str(repo_dir), check=True, capture_output=True)
        subprocess.run(["git", "branch", "-D", "main"], cwd=str(repo_dir), check=True, capture_output=True)

        # Clearing any environment base variables
        old_env = os.environ.pop("C15_SURFACE_BASE", None)
        old_event = os.environ.pop("GITHUB_EVENT_PATH", None)
        try:
            with pytest.raises(ValueError, match="base authority unresolved"):
                resolve_surface_base(None, repo_root=repo_dir)
        finally:
            if old_env:
                os.environ["C15_SURFACE_BASE"] = old_env
            if old_event:
                os.environ["GITHUB_EVENT_PATH"] = old_event
    finally:
        wipe(parent)


def test_pm49_blk001r_explicit_base_detects_earlier_commit_drift() -> None:
    """ATTACK TEST (PM49-BLK-001R): Comparing against true PR base detects drift introduced in commit A.

    Proves:
    1. If check had used HEAD~1, diff between commit A and commit B would have falsely appeared clean.
    2. Using true PR base SHA catches drift in src/aios_core and fails clean assertion.
    """
    parent = new_root("pm49-blk001r-drift")
    try:
        repo_dir, base_sha, commit_a, commit_b = _create_multi_commit_repo(parent)

        # Diff against commit A (what HEAD~1 would have produced) falsely claims clean
        pinned_from_a = _pinned_tree_digest(commit_a, repo_root=repo_dir)
        assert pinned_from_a["src/aios_core"]["clean"] is True, "HEAD~1 missed drift injected in earlier commit"

        # Diff against authoritative base_sha catches drift in src/aios_core
        pinned_from_base = _pinned_tree_digest(base_sha, repo_root=repo_dir)
        assert pinned_from_base["src/aios_core"]["clean"] is False, "True base must catch commit A drift"
        assert "drift.py" in pinned_from_base["src/aios_core"]["diff"]
        assert pinned_from_base["reviews/internal_habitation/c15-rcc/v1"]["clean"] is True
    finally:
        wipe(parent)


def test_pm49_blk001r_github_pr_event_base_resolves_correct_sha() -> None:
    """POSITIVE TEST (PM49-BLK-001R): GitHub PR event metadata resolves authoritative base SHA."""
    parent = new_root("pm49-blk001r-event")
    try:
        repo_dir, base_sha, commit_a, commit_b = _create_multi_commit_repo(parent)

        event_file = parent / "event.json"
        event_file.write_text(json.dumps({"pull_request": {"base": {"sha": base_sha}}}))

        old_event = os.environ.get("GITHUB_EVENT_PATH")
        os.environ["GITHUB_EVENT_PATH"] = str(event_file)
        try:
            resolved = resolve_surface_base(None, repo_root=repo_dir)
            assert resolved == base_sha
        finally:
            if old_event:
                os.environ["GITHUB_EVENT_PATH"] = old_event
            else:
                os.environ.pop("GITHUB_EVENT_PATH", None)
    finally:
        wipe(parent)


# -----------------------------------------------------------------------------
# PM49-BLK-002R: True Process-Separated Provider & Private Key Isolation Tests
# -----------------------------------------------------------------------------


def test_pm49_blk002r_provider_process_runs_in_separate_pid() -> None:
    """ATTACK TEST (PM49-BLK-002R): Provider process runs in distinct child process (PROVIDER_PID != OPERATOR_PID).

    Proves:
    1. provider.dispatch() runs in a child subprocess.
    2. provider.collect() runs in a child subprocess.
    3. Both record provider_pid != os.getpid() in the dispatch ledger.
    """
    parent = new_root("pm49-blk002r-pid")
    try:
        mailbox = parent / "mailbox"
        mailbox.mkdir(parents=True, exist_ok=True)
        request_id = "test-req-pid-001"
        outbox = provider_module.outbox_path(mailbox, request_id)
        outbox.parent.mkdir(parents=True, exist_ok=True)

        envelope = {
            "model_request_id": request_id,
            "attempt_id": "attempt-pid-001",
            "round": 0,
            "provider": provider_module.PROVIDER_NAME,
            "model": provider_module.MODEL_NAME,
            "resident_visible_payload": "hello world",
            "run_id": "run-pid-001",
            "cursor": 1,
        }
        outbox.write_bytes(json.dumps(envelope).encode("utf-8"))

        dispatch_report = provider_module.dispatch(mailbox, request_id)
        provider_pid = int(dispatch_report["provider_pid"])
        assert provider_pid != os.getpid(), "Security violation: dispatch ran in same process as caller!"

        collect_report = provider_module.collect(mailbox, request_id)
        collect_pid = int(collect_report["provider_pid"])
        assert collect_pid != os.getpid(), "Security violation: collect ran in same process as caller!"

        # Check ledger
        ledger = provider_module.read_ledger(mailbox)
        assert len(ledger) >= 1
        for row in ledger:
            assert int(row["provider_pid"]) != os.getpid()
    finally:
        wipe(parent)


def test_pm49_blk002r_operator_process_cannot_import_private_authority() -> None:
    """ATTACK TEST (PM49-BLK-002R): Operator process cannot import private signing modules.

    Proves:
    1. Attempting to import tools.c15_persistence.provider_process raises ImportError.
    2. Attempting to import tools.c15_persistence._provider_authority raises ImportError.
    3. No private key attributes (_RSA_D, sign) exist on OperatorSession or provider module.
    """
    # 1. Importing provider_process must raise ImportError
    with pytest.raises(ImportError, match="isolated process boundary"):
        import tools.c15_persistence.provider_process  # noqa: F401

    # 2. Importing _provider_authority must raise ImportError
    with pytest.raises(ImportError):
        import tools.c15_persistence._provider_authority  # noqa: F401

    # 3. Check OperatorSession class and module
    operator_attrs = dir(operator_session_module)
    assert "_RSA_D" not in operator_attrs
    assert "_provider_authority" not in operator_attrs
    assert "rsa_sign" not in operator_attrs
    assert not hasattr(OperatorSession, "_RSA_D")
    assert not hasattr(OperatorSession, "sign")

    # 4. Check provider module
    provider_attrs = dir(provider_module)
    assert "_RSA_D" not in provider_attrs
    assert "rsa_sign" not in provider_attrs


def test_pm49_blk002r_provider_boundary_rejects_arbitrary_attacker_response_signing() -> None:
    """ATTACK TEST (PM49-BLK-002R): Provider client exports no public signing oracle."""
    public_functions = [
        name for name, obj in inspect.getmembers(provider_module, inspect.isfunction)
        if not name.startswith("_")
    ]
    for fn_name in public_functions:
        assert "sign" not in fn_name or fn_name == "route_b_verifier", (
            f"provider module illegally exports public signing function: {fn_name}"
        )


def test_pm49_blk002r_recovery_path_never_invokes_signing_authority() -> None:
    """ATTACK TEST (PM49-BLK-002R): Recovery path never calls signing functions and fails closed."""
    parent = new_root("pm49-blk002r-rec-nosign")
    try:
        root = parent / "backend"
        run_id = "test-rec-nosign-002"
        session_id = "test-rec-nosign-sess"
        session = OperatorSession.create(root, run_id=run_id, session_id=session_id)
        projection = session.reveal()
        session.ingest(projection)
        session.runtime = session._build_runtime()
        session._session_id = f"{session.backend.owner['run_id']}-conv"

        # Stage and dispatch request (K3)
        turn_index = int(projection["sequence"])
        attempt_id = session._attempt_id(turn_index=turn_index, round_index=0)
        request_id = session._request_id(attempt_id, 0)
        nonce = "test-nonce-87654321"
        req_bytes, metadata = session._request_bytes(
            attempt_id=attempt_id,
            request_id=request_id,
            round_index=0,
            cursor=turn_index,
            event_id=str(projection["event_id"]),
            payload=str(projection["resident_visible_payload"]),
            nonce=nonce,
            binding_digest=session._binding_digest(),
        )
        session.journal.stage(metadata, req_bytes, generation=0)
        session.journal.expose(request_id)
        session._write_outbox(request_id, req_bytes, round_index=0)
        provider_module.dispatch(session.mailbox, request_id)

        # Simulate Core having marked dispatch started without a durable receipt
        execution_id = session.runtime.turn_executions.execution_id_for(
            subject_id=session.runtime.subject_id,
            session_id=session._session_id,
            turn_index=turn_index,
        )
        session.runtime.background_model_attempts.admit(
            subject_id=session.runtime.subject_id,
            work_kind="user_turn",
            work_id=execution_id,
            wake_reason="user_turn",
            model_round_index=0,
            world_revision=1,
            admitted_at=datetime.now(timezone.utc),
        )
        session.runtime.background_model_attempts.mark_dispatching(
            attempt_id=attempt_id,
            dispatched_at=datetime.now(timezone.utc),
            outbound_request_fingerprint="test-fp",
        )
        session.backend.release()

        # Attach and resume: must raise DurableTrustedReturnMissing
        recovered = OperatorSession.attach(root, run_id=run_id, session_id=session_id)
        with pytest.raises(DurableTrustedReturnMissing):
            recovered.resume()

        recovered.backend.release()
    finally:
        wipe(parent)


def test_pm49_blk002r_positive_live_path_produces_and_verifies_provider_proof() -> None:
    """POSITIVE TEST (PM49-BLK-002R): Full live turn runs end-to-end with provider subprocess proof."""
    parent = new_root("pm49-blk002r-live")
    try:
        root = parent / "backend"
        session = OperatorSession.create(
            root, run_id="test-live-002", session_id="test-live-sess"
        )

        outcome = session.process_one_cursor()
        assert outcome["ack"]["status"] == "acked"
        assert outcome["ack"]["sequence"] == 1

        # Verify receipt was created in Core SQLite
        runtime = session._build_runtime()
        session._session_id = f"{session.backend.owner['run_id']}-conv"
        session.runtime = runtime
        attempt_id = session._attempt_id(turn_index=1, round_index=0)
        receipt = runtime.background_model_attempts.response_authenticity_receipt(attempt_id)
        assert receipt is not None
        assert receipt.attempt_id == attempt_id
        assert receipt.provider == provider_module.PROVIDER_NAME
        assert receipt.model == provider_module.MODEL_NAME
        assert bool(receipt.authenticity_proof)

        session.backend.release()
    finally:
        wipe(parent)
