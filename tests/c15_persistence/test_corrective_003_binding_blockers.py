"""Frozen Corrective-003 binding-blocker matrix (v2) on accepted Core semantics.

Scope
-----
Only the three PM-ruled release-binding blockers are probed here:

* ``C002-001`` authoritative checkpoint failure hard-stops the operator;
* ``C002-002`` later-round provider-return / K3 / K5 remote-only recovery;
* ``C002-004`` remote-authoritative binding can never silently downgrade.

Probe discipline
----------------
Every probe carries a stable ``PROBE:`` id and a frozen ``EXPECT:`` outcome in
its docstring.  The matrix is enumerated and hashed by
``tools/c15_persistence/freeze_corrective_003_matrix.py`` **before** any
implementation adjustment, and the same probe sources are executed for the RED
(baseline) and GREEN (candidate) runs.

Provider-return authority (why the K3 window is split)
------------------------------------------------------
Accepted Core owns provider-return authenticity: only Core's own trusted-return
callback mints the receipt/handoff, and only Core's own recovery surface may
resume a round from exact bytes.  A later round whose provider boundary was
crossed *without* a durable trusted return therefore has no legal continuation;
the harness must stop fail-closed instead of redispatching or inventing
authenticity (independently reproduced on fresh main before this matrix was
frozen).  The convergent K3 boundary is the authenticatable one:
``K3_TRUSTED_RETURN_DURABLE``.

Exit codes are part of the frozen contract:

``0``   converged;
``42``  deliberate fail-closed stop (``FAIL_CLOSED_HARD_STOP`` on stderr);
``43``  authoritative persistence failure (``AUTHORITATIVE_PERSISTENCE_FAILURE``).

No real Resident, no real C15 fixture and no release-state mutation is used:
every run/ref/identity below is synthetic and disposable.
"""

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
from tools.c15_persistence.backend import BackendError, RunBackend  # noqa: E402
from tools.c15_persistence.operator_session import OperatorSession  # noqa: E402

# Frozen contract values (declared here, not imported from the implementation).
CONVERGED_EXIT = 0
FAIL_CLOSED_EXIT = 42
AUTHORITATIVE_FAILURE_EXIT = 43
FAIL_CLOSED_MARKER = "FAIL_CLOSED_HARD_STOP"
AUTHORITATIVE_FAILURE_MARKER = "AUTHORITATIVE_PERSISTENCE_FAILURE"
K4_BARRIER = "K4_AFTER_REPLY_AUTHENTICATED"
ACK_BARRIER = "ACKED"
K3_DISPATCH_BARRIER = "K3_AFTER_REQUEST_DISPATCH"
K3_TRUSTED_RETURN_BARRIER = "K3_TRUSTED_RETURN_DURABLE"
K5_BARRIER = "K5_AFTER_APPLIED_BEFORE_ACK"


# --------------------------------------------------------------------- helpers


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


def _remote_file(remote: Path, commit_sha: str, path: str) -> bytes | None:
    completed = subprocess.run(
        ["git", f"--git-dir={remote}", "show", f"{commit_sha}:{path}"],
        capture_output=True,
        text=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def _remote_json(remote: Path, commit_sha: str, path: str) -> dict:
    raw = _remote_file(remote, commit_sha, path)
    assert raw is not None, f"remote commit {commit_sha} is missing {path}"
    return json.loads(raw.decode("utf-8"))


def _remote_ledger(remote: Path, commit_sha: str) -> list[dict]:
    raw = _remote_file(remote, commit_sha, "mailbox/dispatch-ledger.jsonl")
    if raw is None:
        return []
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


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
    fail_barrier: str | None = None,
    commit_sha: str | None = None,
    require_remote: bool = True,
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
    ]
    if require_remote:
        cmd.append("--require-remote-durability")
    if kill_at is not None:
        cmd.extend(["--kill-at", kill_at])
    if kill_round is not None:
        cmd.extend(["--kill-round", str(kill_round)])
    if fail_barrier is not None:
        cmd.extend(["--fail-barrier", fail_barrier])
    if commit_sha is not None:
        cmd.extend(["--commit-sha", commit_sha])
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=repo_python_env(),
        capture_output=True,
        text=True,
        timeout=1200,
    )


def _ids(label: str) -> tuple[str, str, str]:
    token = uuid.uuid4().hex[:10]
    run_id = f"synthetic-run-c003v2-{label}-{token}"
    session_id = f"synthetic-session-c003v2-{label}-{token}"
    remote_ref = f"refs/heads/persistence/{run_id}"
    return run_id, session_id, remote_ref


def _remote_session(tmp_path: Path, label: str):
    remote = _bare_remote(tmp_path, label)
    run_id, session_id, remote_ref = _ids(label)
    parent = new_root(f"c003v2-{label}")
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


def _release_state(remote: Path, commit_sha: str) -> dict:
    return _remote_json(remote, commit_sha, "state/runtime/release_state.json")


def _assert_not_acked(remote: Path, commit_sha: str) -> None:
    state = _release_state(remote, commit_sha)
    assert int(state.get("next_sequence", 1)) == 1, state
    assert not state.get("receipts"), state
    assert state.get("last_acked_sequence") in (None, 0), state


def _assert_converged(outcome: dict, *, dispatches: int, meters: int) -> None:
    observed = outcome["observed"]
    counters = observed["counters"]
    ack = outcome["ack"]
    assert ack["status"] == "acked", ack
    assert ack["sequence"] == outcome["projection"]["sequence"], ack
    assert ack["next_sequence"] == outcome["projection"]["sequence"] + 1, ack
    assert counters.get("reveals") == 1, counters
    assert counters.get("ingests") == 1, counters
    assert counters.get("acks") == 1, counters
    assert counters.get("turns_completed") == 1, counters
    assert counters.get("capability_side_effects") == 1, counters
    assert observed["metering_rows"] == meters, observed["metering_rows"]
    assert observed["observation_counts"]["assistant_outputs"] == 1, observed["observation_counts"]
    ledger = observed["dispatch_ledger"]
    assert len(ledger) == dispatches, ledger
    assert len({row["request_id"] for row in ledger}) == dispatches, ledger


# ------------------------------------------------------- C002-001 (hard stop)


def test_c002_001_a_capability_wrapping_cannot_swallow_authoritative_abort(
    tmp_path: Path,
) -> None:
    """PROBE: C002-001-A.

    EXPECT: an authoritative-durability abort raised inside a registered
    capability handler crosses Core's ``CapabilityRegistry.invoke`` boundary as
    a BaseException and is never converted into a ``CAPABILITY_EXECUTION_ERROR``
    capability result, while ordinary handler errors are still wrapped.
    """
    from aios_core.query.search import WorldSearchIndex
    from aios_core.runtime import ModelCallProvenance  # noqa: F401  (import parity)
    from aios_core.runtime.capabilities import (
        CapabilityCall,
        CapabilityKind,
        CapabilitySpec,
    )
    from aios_core.runtime.turn_runtime import FusedTurnRuntime
    from aios_core.storage.sqlite_store import SQLiteWorldStore

    from tools.c15_persistence.operator_session import RemoteDurabilityAbort

    db = tmp_path / "world.db"
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    runtime = FusedTurnRuntime(store=store, index=index, model_handler=lambda _snapshot: None)

    def aborting(**_kwargs):
        raise RemoteDurabilityAbort("injected authoritative durability failure")

    def failing(**_kwargs):
        raise RuntimeError("ordinary capability failure")

    for name, handler in (("probe_abort", aborting), ("probe_error", failing)):
        runtime.registry.register(
            CapabilitySpec(
                name=name,
                description="Corrective-003 probe capability",
                kind=CapabilityKind.READ,
                input_schema={},
                side_effecting=False,
            ),
            handler,
        )

    with pytest.raises(RemoteDurabilityAbort):
        runtime.registry.invoke(
            CapabilityCall(name="probe_abort", call_id="probe-abort", arguments={})
        )

    control = runtime.registry.invoke(
        CapabilityCall(name="probe_error", call_id="probe-control", arguments={})
    )
    assert control.ok is False
    assert control.error_code == "CAPABILITY_EXECUTION_ERROR", control
    assert "ordinary capability failure" in (control.error_message or ""), control


def test_c002_001_b_k4_authoritative_failure_hard_stops_before_progress(
    tmp_path: Path,
) -> None:
    """PROBE: C002-001-B.

    EXPECT: with the remote-authoritative write for the K4 capability barrier
    failing, the operator exits through the authoritative-failure path with the
    cursor un-acked, no second provider dispatch, and no round-1 model call; the
    remote ref still holds the previous (K3) authoritative barrier, so the failed
    K4 advance is never published as success.
    """
    remote = _bare_remote(tmp_path, "c001b")
    run_id, session_id, remote_ref = _ids("c001b")
    parent = new_root("c003v2-c001b")
    try:
        failed = _run_cli(
            root=parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="create",
            remote=remote,
            remote_ref=remote_ref,
            fail_barrier=K4_BARRIER,
        )
        assert failed.returncode == AUTHORITATIVE_FAILURE_EXIT, (
            f"expected authoritative-failure exit {AUTHORITATIVE_FAILURE_EXIT}, "
            f"got {failed.returncode}\nstdout={failed.stdout}\nstderr={failed.stderr}"
        )
        assert AUTHORITATIVE_FAILURE_MARKER in failed.stderr, failed.stderr

        root = parent / "backend"
        # Durable local failure evidence exists and never claims success.
        failures = [
            json.loads(line)
            for line in (root / "state" / "evidence" / "failures.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        injected = [
            row
            for row in failures
            if row.get("point") == "AUTHORITATIVE_PERSISTENCE_FAILURE"
            and row.get("barrier") == K4_BARRIER
        ]
        assert injected, failures
        counters = json.loads((root / "state" / "counters.json").read_text(encoding="utf-8"))
        assert counters.get("acks", 0) == 0, counters
        assert counters.get("turns_completed", 0) == 0, counters
        assert counters.get("capability_side_effects", 0) == 1, counters
        assert len(provider_module.read_ledger(root / "mailbox")) == 1, "round 0 only"

        # The unpublished local K4 advance must not be adopted as authoritative.
        with pytest.raises(BackendError):
            OperatorSession.attach(root, run_id=run_id, session_id=session_id)

        head = _remote_head(remote, remote_ref)
        assert head is not None
        marker = _remote_json(remote, head, "state/remote-barrier.json")
        # The failed K4 write is not published; the surviving authoritative state
        # is the authenticated provider-return barrier of round 0.
        assert marker["point"] == K3_TRUSTED_RETURN_BARRIER, marker
        _assert_not_acked(remote, head)
        ledger = _remote_ledger(remote, head)
        assert len(ledger) == 1, ledger
    finally:
        wipe(parent)


def test_c002_001_c_k4_failure_restart_recovers_from_authoritative_state_once(
    tmp_path: Path,
) -> None:
    """PROBE: C002-001-C.

    EXPECT: after the K4 authoritative failure and total loss of the failed local
    cache, a fresh process that restores only the authoritative remote state
    converges exactly once - one reveal/ingest/ACK, one capability effect, two
    metered rounds and two provider dispatches (one per round) with no duplicate.
    """
    remote = _bare_remote(tmp_path, "c001c")
    run_id, session_id, remote_ref = _ids("c001c")
    first_parent = new_root("c003v2-c001c-first")
    fresh_parent: Path | None = None
    try:
        failed = _run_cli(
            root=first_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="create",
            remote=remote,
            remote_ref=remote_ref,
            fail_barrier=K4_BARRIER,
        )
        assert failed.returncode == AUTHORITATIVE_FAILURE_EXIT, failed.stderr

        # Failure evidence must be durably recorded in the failed run itself:
        # both the evidence slot and the audit trail carry the authoritative
        # durability failure (probe correction: the assertion is made before the
        # probe deliberately destroys the whole local cache).
        failures = [
            json.loads(line)
            for line in (first_parent / "backend" / "state" / "evidence" / "failures.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        assert any(
            row.get("point") == "AUTHORITATIVE_PERSISTENCE_FAILURE"
            and row.get("barrier") == K4_BARRIER
            for row in failures
        ), failures
        audit_blob = (first_parent / "backend" / "audit.jsonl").read_text(encoding="utf-8")
        assert "failure_evidence" in audit_blob, "audit trail lost the failure"

        wipe(first_parent)
        fresh_parent = new_root("c003v2-c001c-fresh")
        resumed = _run_cli(
            root=fresh_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="materialize-resume",
            remote=remote,
            remote_ref=remote_ref,
        )
        assert resumed.returncode == CONVERGED_EXIT, (
            f"remote-only restart failed\nstdout={resumed.stdout}\nstderr={resumed.stderr}"
        )
        _assert_converged(json.loads(resumed.stdout), dispatches=2, meters=2)

        head = _remote_head(remote, remote_ref)
        assert head is not None
        state = _release_state(remote, head)
        assert int(state["last_acked_sequence"]) == 1, state
        # The recovered run supersedes the failed barrier with a published state
        # whose journal records both rounds as applied.
        journal_blob = _remote_file(remote, head, "journal.sqlite")
        assert journal_blob is not None and len(journal_blob) > 0
    finally:
        if first_parent.exists():
            wipe(first_parent)
        if fresh_parent is not None:
            wipe(fresh_parent)


def test_c002_001_d_ack_barrier_failure_never_acks_the_cursor(tmp_path: Path) -> None:
    """PROBE: C002-001-D.

    EXPECT: an authoritative ACK-barrier failure is fatal and the cursor is never
    acked; the previous authoritative barrier stays published and the failure is
    durably recorded rather than reported as a successful persistence.
    """
    remote = _bare_remote(tmp_path, "c001d")
    run_id, session_id, remote_ref = _ids("c001d")
    parent = new_root("c003v2-c001d")
    try:
        failed = _run_cli(
            root=parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="create",
            remote=remote,
            remote_ref=remote_ref,
            fail_barrier=ACK_BARRIER,
        )
        assert failed.returncode == AUTHORITATIVE_FAILURE_EXIT, (
            f"stderr={failed.stderr}\nstdout={failed.stdout}"
        )
        assert AUTHORITATIVE_FAILURE_MARKER in failed.stderr, failed.stderr

        root = parent / "backend"
        counters = json.loads((root / "state" / "counters.json").read_text(encoding="utf-8"))
        assert counters.get("acks", 0) == 1, counters  # the ack ran once locally
        local_release = json.loads(
            (root / "state" / "runtime" / "release_state.json").read_text(encoding="utf-8")
        )
        assert int(local_release["last_acked_sequence"]) == 1, local_release

        head = _remote_head(remote, remote_ref)
        assert head is not None
        marker = _remote_json(remote, head, "state/remote-barrier.json")
        assert marker["point"] == K5_BARRIER, marker
        _assert_not_acked(remote, head)
    finally:
        wipe(parent)


# ------------------------------------------------- C002-002 (later-round K3/K5)


def test_c002_002_a_k3_trusted_return_first_round_remote_only_converges(
    tmp_path: Path,
) -> None:
    """PROBE: C002-002-A.

    EXPECT: a total local loss at the first round's authenticatable provider
    return (Core receipt + exact return handoff durable) recovers from remote
    state alone, without a second dispatch and without duplicate work.
    """
    remote = _bare_remote(tmp_path, "c002a")
    run_id, session_id, remote_ref = _ids("c002a")
    first_parent = new_root("c003v2-c002a-first")
    fresh_parent: Path | None = None
    try:
        killed = _run_cli(
            root=first_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="create",
            remote=remote,
            remote_ref=remote_ref,
            kill_at=K3_TRUSTED_RETURN_BARRIER,
            kill_round=0,
        )
        assert killed.returncode == -signal.SIGKILL, (
            f"expected SIGKILL at the trusted-return barrier, got {killed.returncode}\n"
            f"stderr={killed.stderr}"
        )
        head = _remote_head(remote, remote_ref)
        assert head is not None
        assert _remote_json(remote, head, "state/remote-barrier.json")["point"] == (
            K3_TRUSTED_RETURN_BARRIER
        )

        wipe(first_parent)
        fresh_parent = new_root("c003v2-c002a-fresh")
        resumed = _run_cli(
            root=fresh_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="materialize-resume",
            remote=remote,
            remote_ref=remote_ref,
        )
        assert resumed.returncode == CONVERGED_EXIT, (
            f"remote-only recovery failed\nstdout={resumed.stdout}\nstderr={resumed.stderr}"
        )
        _assert_converged(json.loads(resumed.stdout), dispatches=2, meters=2)
    finally:
        if first_parent.exists():
            wipe(first_parent)
        if fresh_parent is not None:
            wipe(fresh_parent)


def test_c002_002_b_k3_trusted_return_later_round_remote_only_converges(
    tmp_path: Path,
) -> None:
    """PROBE: C002-002-B.

    EXPECT: the same authenticatable provider-return loss in a *later* round
    (after round 0 was metered and its capability applied) still converges from
    remote state alone: two dispatches with distinct request ids, two metered
    rounds, one capability effect, one assistant output, one ACK.
    """
    remote = _bare_remote(tmp_path, "c002b")
    run_id, session_id, remote_ref = _ids("c002b")
    first_parent = new_root("c003v2-c002b-first")
    fresh_parent: Path | None = None
    try:
        killed = _run_cli(
            root=first_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="create",
            remote=remote,
            remote_ref=remote_ref,
            kill_at=K3_TRUSTED_RETURN_BARRIER,
            kill_round=1,
        )
        assert killed.returncode == -signal.SIGKILL, (
            f"expected SIGKILL at later-round trusted return, got {killed.returncode}\n"
            f"stderr={killed.stderr}"
        )
        head = _remote_head(remote, remote_ref)
        assert head is not None
        assert _remote_json(remote, head, "state/remote-barrier.json")["point"] == (
            K3_TRUSTED_RETURN_BARRIER
        )
        ledger = _remote_ledger(remote, head)
        assert len(ledger) == 2, ledger

        wipe(first_parent)
        fresh_parent = new_root("c003v2-c002b-fresh")
        resumed = _run_cli(
            root=fresh_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="materialize-resume",
            remote=remote,
            remote_ref=remote_ref,
        )
        assert resumed.returncode == CONVERGED_EXIT, (
            f"later-round remote-only recovery failed\nstdout={resumed.stdout}\n"
            f"stderr={resumed.stderr}"
        )
        _assert_converged(json.loads(resumed.stdout), dispatches=2, meters=2)
    finally:
        if first_parent.exists():
            wipe(first_parent)
        if fresh_parent is not None:
            wipe(fresh_parent)


def test_c002_002_c_k3_dispatch_only_later_round_hard_stops_without_redispatch(
    tmp_path: Path,
) -> None:
    """PROBE: C002-002-C.

    EXPECT: a later round whose provider boundary was crossed with no durable
    trusted return has no legal continuation.  Remote-only recovery exits through
    the deliberate fail-closed stop (never a redispatch, never an invented
    receipt): the dispatch ledger stays at two entries, the cursor is not acked,
    durable failure evidence is published, and a repeated recovery makes the same
    deterministic decision.
    """
    remote = _bare_remote(tmp_path, "c002c")
    run_id, session_id, remote_ref = _ids("c002c")
    first_parent = new_root("c003v2-c002c-first")
    fresh_parent: Path | None = None
    second_parent: Path | None = None
    try:
        killed = _run_cli(
            root=first_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="create",
            remote=remote,
            remote_ref=remote_ref,
            kill_at=K3_DISPATCH_BARRIER,
            kill_round=1,
        )
        assert killed.returncode == -signal.SIGKILL, (
            f"expected SIGKILL after later-round dispatch, got {killed.returncode}\n"
            f"stderr={killed.stderr}"
        )
        head = _remote_head(remote, remote_ref)
        assert head is not None
        assert _remote_json(remote, head, "state/remote-barrier.json")["point"] == (
            K3_DISPATCH_BARRIER
        )
        assert len(_remote_ledger(remote, head)) == 2

        wipe(first_parent)
        fresh_parent = new_root("c003v2-c002c-fresh")
        resumed = _run_cli(
            root=fresh_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="materialize-resume",
            remote=remote,
            remote_ref=remote_ref,
        )
        assert resumed.returncode == FAIL_CLOSED_EXIT, (
            f"expected fail-closed exit {FAIL_CLOSED_EXIT}, got {resumed.returncode}\n"
            f"stdout={resumed.stdout}\nstderr={resumed.stderr}"
        )
        assert FAIL_CLOSED_MARKER in resumed.stderr, resumed.stderr

        # No redispatch, no ACK, durable evidence - and the attempt is untouched.
        head_after = _remote_head(remote, remote_ref)
        assert head_after is not None and head_after != head
        assert len(_remote_ledger(remote, head_after)) == 2, "no second dispatch"
        marker = _remote_json(remote, head_after, "state/remote-barrier.json")
        assert marker["point"] == "FAIL_CLOSED_NO_DURABLE_TRUSTED_RETURN", marker
        _assert_not_acked(remote, head_after)

        root = fresh_parent / "backend"
        with sqlite3.connect(root / "state" / "runtime" / "world.sqlite") as db:
            states = [
                row[0]
                for row in db.execute(
                    "SELECT state FROM background_model_attempts ORDER BY model_round_index"
                ).fetchall()
            ]
        assert states == ["metered", "dispatching"], states

        # Deterministic: a second recovery makes the identical decision.
        second_parent = new_root("c003v2-c002c-second")
        again = _run_cli(
            root=second_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="materialize-resume",
            remote=remote,
            remote_ref=remote_ref,
        )
        assert again.returncode == FAIL_CLOSED_EXIT, again.stderr
        assert FAIL_CLOSED_MARKER in again.stderr, again.stderr
        head_last = _remote_head(remote, remote_ref)
        assert len(_remote_ledger(remote, head_last)) == 2, "still no dispatch"
        _assert_not_acked(remote, head_last)
    finally:
        if first_parent.exists():
            wipe(first_parent)
        if fresh_parent is not None:
            wipe(fresh_parent)
        if second_parent is not None:
            wipe(second_parent)


def test_c002_002_d_k5_push_success_then_total_local_loss_acks_once(
    tmp_path: Path,
) -> None:
    """PROBE: C002-002-D.

    EXPECT: when the applied-before-ACK barrier is already authoritative and the
    whole local cache is destroyed, the fresh process completes the cursor
    exactly once without rerunning model/capability work (dispatch ledger and
    metering stay at their published values, one assistant output, one ACK).
    """
    remote = _bare_remote(tmp_path, "c002d")
    run_id, session_id, remote_ref = _ids("c002d")
    first_parent = new_root("c003v2-c002d-first")
    fresh_parent: Path | None = None
    try:
        killed = _run_cli(
            root=first_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="create",
            remote=remote,
            remote_ref=remote_ref,
            kill_at=K5_BARRIER,
        )
        assert killed.returncode == -signal.SIGKILL, killed.stderr
        head = _remote_head(remote, remote_ref)
        assert head is not None
        assert _remote_json(remote, head, "state/remote-barrier.json")["point"] == K5_BARRIER
        assert len(_remote_ledger(remote, head)) == 2

        wipe(first_parent)
        fresh_parent = new_root("c003v2-c002d-fresh")
        resumed = _run_cli(
            root=fresh_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="materialize-resume",
            remote=remote,
            remote_ref=remote_ref,
        )
        assert resumed.returncode == CONVERGED_EXIT, (
            f"K5 remote-only ACK failed\nstdout={resumed.stdout}\nstderr={resumed.stderr}"
        )
        outcome = json.loads(resumed.stdout)
        _assert_converged(outcome, dispatches=2, meters=2)
        assert outcome["turn"].get("skipped") is True, outcome["turn"]
    finally:
        if first_parent.exists():
            wipe(first_parent)
        if fresh_parent is not None:
            wipe(fresh_parent)


def test_c002_002_e_k5_prepush_crash_recovers_from_prior_authoritative_barrier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PROBE: C002-002-E.

    EXPECT: a crash after the local commit object is created but before the
    remote push leaves the prior barrier authoritative - and that prior barrier is
    the authenticated provider-return boundary of the last round, so restoring
    only it converges exactly once (the unpublished commit is never promoted and
    no provider is redispatched).
    """
    from tools.c15_persistence import remote_backend

    session, remote, run_id, session_id, remote_ref, parent = _remote_session(
        tmp_path, "c002e"
    )
    original_commit = remote_backend.commit_backend_tree
    tripped = {"value": False}

    def crash_after_commit_tree(*args, **kwargs):
        result = original_commit(*args, **kwargs)
        message = str(kwargs.get("message") or "")
        if f"point={K5_BARRIER}" in message:
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
        assert _remote_json(remote, prior_remote, "state/remote-barrier.json")["point"] == (
            K3_TRUSTED_RETURN_BARRIER
        ), "the last published barrier must be the authenticated provider return"
        session.backend.release()
        # The fault was a one-shot crash, not a permanent outage: the recovery
        # process runs without it (probe correction).
        monkeypatch.setattr(remote_backend, "commit_backend_tree", original_commit)

        wipe(parent)
        fresh_parent = new_root("c003v2-c002e-fresh")
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
        counters = recovered.counters()
        assert outcome["ack"]["status"] == "acked"
        assert outcome["ack"]["sequence"] == 1
        assert outcome["ack"]["next_sequence"] == 2
        assert counters["reveals"] == 1
        assert counters["ingests"] == 1
        assert counters["capability_side_effects"] == 1
        assert counters["acks"] == 1
        assert len(provider_module.read_ledger(recovered.mailbox)) == 2
        assert recovered.metering_rows() == 2
        recovered.backend.release()
    finally:
        session.backend.release()
        if parent.exists():
            wipe(parent)
        if fresh_parent is not None:
            wipe(fresh_parent)


def test_c002_002_f_changed_trusted_return_bytes_under_same_identity_fail_closed(
    tmp_path: Path,
) -> None:
    """PROBE: C002-002-F.

    EXPECT: changing the exact provider-return bytes while keeping the durable
    identity fails closed: no downstream application, no ACK and no duplicate
    work, because Core re-verifies the handoff digest before applying anything.
    """
    remote = _bare_remote(tmp_path, "c002f")
    run_id, session_id, remote_ref = _ids("c002f")
    first_parent = new_root("c003v2-c002f-first")
    restore_parent: Path | None = None
    try:
        killed = _run_cli(
            root=first_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="create",
            remote=remote,
            remote_ref=remote_ref,
            kill_at=K3_TRUSTED_RETURN_BARRIER,
            kill_round=1,
        )
        assert killed.returncode == -signal.SIGKILL, killed.stderr
        wipe(first_parent)

        restore_parent = new_root("c003v2-c002f-restore")
        RunBackend.materialize_from_remote(
            run_id=run_id,
            session_id=session_id,
            target_dir=restore_parent / "backend",
            remote_ref=remote_ref,
            remote=str(remote),
            repo_dir=REPO_ROOT,
        )
        world = restore_parent / "backend" / "state" / "runtime" / "world.sqlite"
        with sqlite3.connect(world) as db:
            row = db.execute(
                "SELECT h.attempt_id, h.directive_payload FROM background_model_return_handoffs h "
                "JOIN background_model_attempts a ON a.attempt_id = h.attempt_id "
                "ORDER BY a.model_round_index DESC LIMIT 1"
            ).fetchone()
            assert row is not None, "trusted-return handoff missing"
            attempt_id, payload = row
            tampered = payload.replace("round 1 answer", "round 1 altered", 1)
            assert tampered != payload, "tamper target text not found"
            db.execute(
                "UPDATE background_model_return_handoffs SET directive_payload=? "
                "WHERE attempt_id=?",
                (tampered, attempt_id),
            )
            db.commit()

        tampered_run = _run_cli(
            root=restore_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="resume",
            remote=remote,
            remote_ref=remote_ref,
        )
        assert tampered_run.returncode not in (CONVERGED_EXIT,), (
            f"tampered trusted return must not converge\nstdout={tampered_run.stdout}"
        )
        head = _remote_head(remote, remote_ref)
        assert head is not None
        _assert_not_acked(remote, head)
        assert len(_remote_ledger(remote, head)) == 2, "no redispatch after tamper"
    finally:
        if first_parent.exists():
            wipe(first_parent)
        if restore_parent is not None:
            wipe(restore_parent)


def test_c002_002_g_changed_relay_journal_reply_bytes_fail_closed(tmp_path: Path) -> None:
    """PROBE: C002-002-G.

    EXPECT: changing the exact relay-journal reply bytes fails closed on the
    operator's own integrity check before anything is handed back to Core: no
    ACK, no duplicate dispatch, no application.
    """
    remote = _bare_remote(tmp_path, "c002g")
    run_id, session_id, remote_ref = _ids("c002g")
    first_parent = new_root("c003v2-c002g-first")
    restore_parent: Path | None = None
    try:
        killed = _run_cli(
            root=first_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="create",
            remote=remote,
            remote_ref=remote_ref,
            kill_at=K3_TRUSTED_RETURN_BARRIER,
            kill_round=1,
        )
        assert killed.returncode == -signal.SIGKILL, killed.stderr
        wipe(first_parent)

        restore_parent = new_root("c003v2-c002g-restore")
        RunBackend.materialize_from_remote(
            run_id=run_id,
            session_id=session_id,
            target_dir=restore_parent / "backend",
            remote_ref=remote_ref,
            remote=str(remote),
            repo_dir=REPO_ROOT,
        )
        journal = restore_parent / "backend" / "journal.sqlite"
        with sqlite3.connect(journal) as db:
            row = db.execute(
                "SELECT request_id, reply FROM relay WHERE reply IS NOT NULL "
                "ORDER BY updated_at_epoch DESC LIMIT 1"
            ).fetchone()
            assert row is not None, "no staged relay reply"
            request_id, reply = row
            db.execute(
                "UPDATE relay SET reply=? WHERE request_id=?",
                (bytes(reply) + b" ", request_id),
            )
            db.commit()

        tampered_run = _run_cli(
            root=restore_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="resume",
            remote=remote,
            remote_ref=remote_ref,
        )
        assert tampered_run.returncode not in (CONVERGED_EXIT,), tampered_run.stdout
        assert "reply corruption" in (tampered_run.stderr + tampered_run.stdout), (
            tampered_run.stderr
        )
        head = _remote_head(remote, remote_ref)
        assert head is not None
        _assert_not_acked(remote, head)
        assert len(_remote_ledger(remote, head)) == 2, "no redispatch after tamper"
    finally:
        if first_parent.exists():
            wipe(first_parent)
        if restore_parent is not None:
            wipe(restore_parent)


# ------------------------------------------ C002-004 (no silent downgrade)


def test_c002_004_a_valid_remote_authoritative_binding_is_durable(tmp_path: Path) -> None:
    """PROBE: C002-004-A.

    EXPECT: a remote-authoritative run records its classification + binding
    durably; the binding survives a total local loss and re-attach still reports
    remote authority (never local-only).
    """
    session, remote, run_id, session_id, remote_ref, parent = _remote_session(
        tmp_path, "c004a"
    )
    fresh_parent: Path | None = None
    try:
        session.process_one_cursor()
        assert session.remote_durability_enabled is True
        session.backend.release()
        head = _remote_head(remote, remote_ref)
        assert head is not None
        owner = _remote_json(remote, head, "owner.json")
        assert owner["remote_authoritative"] is True, owner
        assert owner["remote_authority"]["run_id"] == run_id, owner
        assert owner["remote_authority"]["remote_ref"] == remote_ref, owner
        binding = _remote_json(remote, head, "remote-durability.json")
        assert binding["remote_ref"] == remote_ref and binding["run_id"] == run_id, binding

        wipe(parent)
        fresh_parent = new_root("c003v2-c004a-fresh")
        resumed = _run_cli(
            root=fresh_parent / "backend",
            run_id=run_id,
            session_id=session_id,
            mode="materialize-resume",
            remote=remote,
            remote_ref=remote_ref,
        )
        assert resumed.returncode == CONVERGED_EXIT, resumed.stderr
        restored = OperatorSession.attach(
            fresh_parent / "backend", run_id=run_id, session_id=session_id
        )
        assert restored.remote_durability_enabled is True
        assert str(restored.backend.owner["remote_authoritative"]) == "True"
        restored.backend.release()
    finally:
        session.backend.release()
        if parent.exists():
            wipe(parent)
        if fresh_parent is not None:
            wipe(fresh_parent)


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param("missing", id="missing"),
        pytest.param("truncated", id="truncated"),
        pytest.param("malformed-json", id="malformed-json"),
        pytest.param("extra-field", id="extra-field"),
        pytest.param("missing-field", id="missing-field"),
        pytest.param("unreadable", id="unreadable"),
        pytest.param("wrong-run", id="wrong-run"),
        pytest.param("wrong-session", id="wrong-session"),
        pytest.param("non-canonical-ref", id="non-canonical-ref"),
    ],
)
def test_c002_004_b_binding_damage_fails_closed_never_local_only(
    tmp_path: Path, mutation: str
) -> None:
    """PROBE: C002-004-B.

    EXPECT: for every damaged-binding shape on a run whose durable owner record
    declares remote authority - missing, truncated, malformed JSON, unexpected or
    missing fields, unreadable, wrong run/session identity, non-canonical ref -
    attach/resume refuses with a BackendError.  It must never fall back to
    local-only operation or make non-authoritative progress.  One probe id covers
    the nine parametrized shapes C002-004-B..J (missing, truncated,
    malformed-json, extra-field, missing-field, unreadable, wrong-run,
    wrong-session, non-canonical-ref).
    """
    session, _remote, run_id, session_id, _ref, parent = _remote_session(
        tmp_path, f"c004b-{mutation}"
    )
    try:
        session.process_one_cursor()
        session.backend.release()
        root = parent / "backend"
        config = root / "remote-durability.json"
        assert config.is_file()
        original = json.loads(config.read_text(encoding="utf-8"))

        if mutation == "missing":
            config.unlink()
        elif mutation == "truncated":
            raw = config.read_text(encoding="utf-8")
            config.write_text(raw[: len(raw) // 2], encoding="utf-8")
        elif mutation == "malformed-json":
            config.write_text('{"version": "c15-remote-durability-v2", ', encoding="utf-8")
        elif mutation == "extra-field":
            config.write_text(
                json.dumps({**original, "unexpected": "attacker"}), encoding="utf-8"
            )
        elif mutation == "missing-field":
            trimmed = {k: v for k, v in original.items() if k != "binding_sha256"}
            config.write_text(json.dumps(trimmed), encoding="utf-8")
        elif mutation == "unreadable":
            os.chmod(config, 0o000)
        elif mutation == "wrong-run":
            config.write_text(
                json.dumps({**original, "run_id": "synthetic-run-someone-else"}),
                encoding="utf-8",
            )
        elif mutation == "wrong-session":
            config.write_text(
                json.dumps({**original, "session_id": "synthetic-session-someone-else"}),
                encoding="utf-8",
            )
        elif mutation == "non-canonical-ref":
            config.write_text(
                json.dumps({**original, "remote_ref": "refs/heads/persistence/other-run"}),
                encoding="utf-8",
            )
        else:  # pragma: no cover - defensive
            raise AssertionError(mutation)

        try:
            with pytest.raises(BackendError):
                OperatorSession.attach(root, run_id=run_id, session_id=session_id)
        finally:
            if mutation == "unreadable":
                os.chmod(config, 0o600)
    finally:
        session.backend.release()
        wipe(parent)


def test_c002_004_k_unavailable_remote_state_fails_closed(tmp_path: Path) -> None:
    """PROBE: C002-004-K.

    EXPECT: a remote-authoritative cache whose authoritative remote is
    unreachable fails closed on attach; the operator never silently continues
    against a missing remote.
    """
    session, remote, run_id, session_id, _ref, parent = _remote_session(
        tmp_path, "c004k"
    )
    try:
        session.process_one_cursor()
        session.backend.release()
        shutil.rmtree(remote)
        with pytest.raises(BackendError):
            OperatorSession.attach(parent / "backend", run_id=run_id, session_id=session_id)
    finally:
        session.backend.release()
        wipe(parent)


def test_c002_004_l_local_only_run_cannot_be_silently_promoted(tmp_path: Path) -> None:
    """PROBE: C002-004-L.

    EXPECT: an intentionally local-only synthetic run has no remote
    classification, never reports remote durability, and cannot be promoted to
    remote-authoritative by attach parameters: the two run classes stay durably
    distinguishable.
    """
    parent = new_root("c003v2-c004l")
    run_id, session_id, remote_ref = _ids("c004l")
    session = OperatorSession.create(
        parent / "backend", run_id=run_id, session_id=session_id
    )
    try:
        assert session.remote_durability_enabled is False
        assert not Path(parent / "backend" / "remote-durability.json").exists()
        assert not bool(session.backend.owner.get("remote_authoritative"))
        session.process_one_cursor()
        session.backend.release()
        with pytest.raises(BackendError):
            OperatorSession.attach(
                parent / "backend",
                run_id=run_id,
                session_id=session_id,
                remote_ref=remote_ref,
                remote=str(_bare_remote(tmp_path, "c004l-remote")),
                repo_dir=REPO_ROOT,
            )
    finally:
        session.backend.release()
        wipe(parent)
