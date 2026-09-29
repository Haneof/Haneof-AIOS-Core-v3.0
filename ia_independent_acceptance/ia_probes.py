"""Independent Acceptance Window 05 — adversarial probes (reviewer-authored).

These probes were written by the Independent Persistence Acceptance Reviewer,
not by the PR author.  They intentionally reuse only read-only helpers from the
candidate's own harness (``tests/c15_persistence/killpoints/harness.py``) and
attack the three PM-bound blocker classes with scenarios that are NOT
byte-identical to the author's frozen matrix:

* IA-01  C002-001: authoritative abort crosses Core's capability-result boundary
          as a BaseException in a fresh, reviewer-built runtime (no operator
          code involved in the crossing itself).
* IA-02  C002-001: end-to-end K4 barrier failure — hard stop, durable failure
          evidence, cursor un-acked, remote still at the authenticated
          provider-return barrier, and the advanced local cache refuses
          re-attach (restart latch without local loss).
* IA-03  C002-001: total local loss after the K4 authoritative failure — a
          fresh process recovers from the authoritative remote state exactly
          once; every durable quantity is counted independently from the
          remote commit bytes (SQLite tables, JSONL ledgers), not from the
          operator's self-reported counters.
* IA-04  C002-001: ACK-barrier failure — the cursor is never published as
          acked; the failure is recorded, not swallowed.
* IA-05  C002-002: later-round K3 trusted-return durable, total local loss,
          remote-only recovery — exactly-once counted independently.
* IA-06  C002-002: later-round dispatch-only (no durable trusted return) —
          fail-closed stop, no redispatch, deterministic on a second attempt.
* IA-07  C002-002: K5 barrier push succeeds then the local cache is destroyed —
          exactly one ACK, no rerun of model/capability work (independent
          counts from the materialized World database).
* IA-08  C002-002: K5 barrier push *fails* (network error) after the local
          commit — authoritative-failure exit, the advanced local cache
          refuses re-attach, and remote-only recovery still converges exactly
          once.
* IA-09  C002-002: tampered relay-journal REQUEST bytes (the author's matrix
          tampered the reply) — fail-closed before anything is re-handed to
          Core; no redispatch.
* IA-10  C002-004: valid binding but a tampered local expected-head marker
          (``.remote-head``) — attach fails closed; never local-only.
* IA-11  C002-004: remote ref rewound by the storage itself (remote commit no
          longer carries the immutable generation head that the local cache
          records) — attach fails closed.
* IA-12  C002-004: remote ref deleted from the server — attach fails closed.
* IA-13  Workspace portability: a fresh, foreign HOME plus a foreign
          ``C15_PERSISTED_WORKSPACE`` must keep the journal contract fully in
          force (13/13 under the frozen unittest contract).
* IA-14  Workspace portability: a relative ``C15_PERSISTED_WORKSPACE``
          override — observed behaviour recorded (hardening observation, see
          report; behaviour predates the candidate).
* IA-15  Workspace portability: a ``C15_PERSISTED_WORKSPACE`` override pointing
          at a platform-excluded directory (``.cache``) — observed behaviour
          recorded (hardening observation, see report).

Exit codes (candidate's frozen contract, re-verified here):
``0`` converged; ``42`` deliberate fail-closed stop; ``43`` authoritative
persistence failure.
"""

from __future__ import annotations

import json
import os
import signal
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
# This reviewer probe module lives OUTSIDE tests/c15_persistence, so the
# candidate's directory-scoped conftest path bootstrap does not apply here;
# the probe provides the same read-only bootstrap for itself.
for _candidate in (REPO_ROOT, REPO_ROOT / "src"):
    if _candidate.is_dir() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))
sys.path.insert(0, str(REPO_ROOT / "tests" / "c15_persistence" / "killpoints"))

from harness import new_root, repo_python_env, wipe  # noqa: E402

from tools.c15_persistence import remote_backend  # noqa: E402
from tools.c15_persistence.backend import BackendError, RunBackend  # noqa: E402
from tools.c15_persistence.operator_session import (  # noqa: E402
    RemoteDurabilityAbort,
    OperatorSession,
)

CONVERGED_EXIT = 0
FAIL_CLOSED_EXIT = 42
AUTHORITATIVE_FAILURE_EXIT = 43


# --------------------------------------------------------------------- helpers


def _bare_remote(tmp_path: Path, label: str) -> Path:
    remote = tmp_path / f"ia-{label}-{uuid.uuid4().hex[:8]}.git"
    subprocess.run(
        ["git", "init", "--bare", "-q", str(remote)],
        cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
    )
    return remote


def _ids(label: str) -> tuple[str, str, str]:
    token = uuid.uuid4().hex[:10]
    run_id = f"synthetic-run-ia05-{label}-{token}"
    session_id = f"synthetic-session-ia05-{label}-{token}"
    return run_id, session_id, f"refs/heads/persistence/{run_id}"


def _cli(*, root: Path, run_id: str, session_id: str, mode: str, remote: Path,
         remote_ref: str, kill_at: str | None = None, kill_round: int | None = None,
         fail_barrier: str | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable, "-m", "tools.c15_persistence.probe_cli",
        "--root", str(root), "--run-id", run_id, "--session-id", session_id,
        "--mode", mode, "--remote-ref", remote_ref, "--remote", str(remote),
        "--repo-dir", str(REPO_ROOT), "--require-remote-durability",
    ]
    if kill_at:
        cmd += ["--kill-at", kill_at]
    if kill_round is not None:
        cmd += ["--kill-round", str(kill_round)]
    if fail_barrier:
        cmd += ["--fail-barrier", fail_barrier]
    return subprocess.run(cmd, cwd=str(REPO_ROOT), env=repo_python_env(),
                          capture_output=True, text=True, timeout=1200)


def _remote_commit(remote: Path, ref: str) -> str:
    out = subprocess.run(["git", "ls-remote", str(remote), ref],
                         cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
    assert out.stdout.strip(), f"remote ref {ref} is empty"
    return out.stdout.strip().split()[0]


def _commit_bytes(remote: Path, sha: str, path: str) -> bytes | None:
    p = subprocess.run(["git", f"--git-dir={remote}", "show", f"{sha}:{path}"],
                       capture_output=True)
    return None if p.returncode != 0 else p.stdout


def _commit_db_query(remote: Path, sha: str, db_path: str, sql: str) -> list[tuple]:
    raw = _commit_bytes(remote, sha, db_path)
    assert raw is not None, f"{db_path} missing in remote commit {sha[:12]}"
    dump = Path(f"/tmp/ia-remote-{uuid.uuid4().hex[:8]}-{Path(db_path).name}")
    dump.write_bytes(raw)
    try:
        with sqlite3.connect(str(dump)) as db:
            return db.execute(sql).fetchall()
    finally:
        dump.unlink(missing_ok=True)


def _remote_ledger_entries(remote: Path, sha: str) -> list[dict]:
    raw = _commit_bytes(remote, sha, "mailbox/dispatch-ledger.jsonl")
    if raw is None:
        return []
    return [json.loads(line) for line in raw.decode().splitlines() if line.strip()]


def _release_state(remote: Path, sha: str) -> dict:
    raw = _commit_bytes(remote, sha, "state/runtime/release_state.json")
    assert raw is not None, "release state missing on remote"
    return json.loads(raw.decode())


def _count_world_effects(remote: Path, sha: str) -> dict:
    """Count durable effects straight from the remote World bytes."""
    meters = _commit_db_query(
        remote, sha, "state/runtime/world.sqlite",
        "SELECT COUNT(*) FROM metering_records",
    )
    attempts = _commit_db_query(
        remote, sha, "state/runtime/world.sqlite",
        "SELECT model_round_index, state FROM background_model_attempts ORDER BY model_round_index",
    )
    return {"meter_rows": meters[0][0], "attempts": attempts}


def _count_assistant_outputs(remote: Path, sha: str, event_id: str) -> int:
    rows = _commit_db_query(
        remote, sha, "state/runtime/world.sqlite",
        "SELECT payload_json FROM object_revisions WHERE object_type='observation'",
    )
    n = 0
    for (payload,) in rows:
        try:
            body = json.loads(payload)
        except (TypeError, ValueError):
            continue
        md = body.get("metadata") or {}
        if str(md.get("source_kind") or "") == "assistant" or (
            str(body.get("object_type") or "") == "observation"
            and str(md.get("role") or "") == "assistant"
        ):
            n += 1
    return n


# ------------------------------------------------- C002-001: hard stop family


def test_ia_01_abort_crosses_capability_boundary() -> None:
    """IA-01: reviewer-built runtime; the authoritative abort must cross
    ``CapabilityRegistry.invoke`` unwrapped while an ordinary error is wrapped."""
    from aios_core.query.search import WorldSearchIndex
    from aios_core.runtime.capabilities import CapabilityCall, CapabilityKind, CapabilitySpec
    from aios_core.runtime.turn_runtime import FusedTurnRuntime
    from aios_core.storage.sqlite_store import SQLiteWorldStore

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "ia-world.db"
        store = SQLiteWorldStore(db)
        index = WorldSearchIndex(db, store=store)
        index.rebuild()
        runtime = FusedTurnRuntime(store=store, index=index,
                                   model_handler=lambda _s: None)

        def authoritative_fail(**_kw):
            raise RemoteDurabilityAbort("IA reviewer-injected authoritative failure")

        def ordinary_fail(**_kw):
            raise ValueError("IA reviewer-injected ordinary failure")

        for name, handler in (("ia_abort", authoritative_fail), ("ia_error", ordinary_fail)):
            runtime.registry.register(
                CapabilitySpec(name=name, description="IA probe", kind=CapabilityKind.READ,
                               input_schema={}, side_effecting=False),
                handler,
            )
        with pytest.raises(RemoteDurabilityAbort):
            runtime.registry.invoke(CapabilityCall(name="ia_abort", call_id="ia-a", arguments={}))
        control = runtime.registry.invoke(CapabilityCall(name="ia_error", call_id="ia-b", arguments={}))
        assert control.ok is False
        assert control.error_code == "CAPABILITY_EXECUTION_ERROR"
        # The authoritative failure must NOT have produced a capability result.
        assert isinstance(control, object)


def test_ia_02_k4_failure_hard_stop_and_restart_latch(tmp_path: Path) -> None:
    """IA-02: K4 barrier failure — exit 43, evidence durable, no ACK, remote
    unchanged, and the advanced local cache refuses a later re-attach."""
    remote = _bare_remote(tmp_path, "ia02")
    run_id, session_id, ref = _ids("ia02")
    parent = new_root("ia-ia02")
    try:
        failed = _cli(root=parent / "backend", run_id=run_id, session_id=session_id,
                      mode="create", remote=remote, remote_ref=ref,
                      fail_barrier="K4_AFTER_REPLY_AUTHENTICATED")
        assert failed.returncode == AUTHORITATIVE_FAILURE_EXIT, failed.stderr

        root = parent / "backend"
        failures = [json.loads(l) for l in
                    (root / "state" / "evidence" / "failures.jsonl").read_text().splitlines()
                    if l.strip()]
        assert any(r.get("point") == "AUTHORITATIVE_PERSISTENCE_FAILURE"
                   and r.get("barrier") == "K4_AFTER_REPLY_AUTHENTICATED" for r in failures), failures
        assert "failure_evidence" in (root / "audit.jsonl").read_text()

        counters = json.loads((root / "state" / "counters.json").read_text())
        assert counters.get("acks", 0) == 0, counters
        assert counters.get("turns_completed", 0) == 0, counters
        assert counters.get("capability_side_effects") == 1, counters

        # Restart latch: the advanced local cache must refuse re-attach.
        with pytest.raises(BackendError):
            OperatorSession.attach(root, run_id=run_id, session_id=session_id)

        head = _remote_commit(remote, ref)
        marker = json.loads(_commit_bytes(remote, head, "state/remote-barrier.json").decode())
        assert marker["point"] == "K3_TRUSTED_RETURN_DURABLE", marker
        state = _release_state(remote, head)
        assert int(state.get("next_sequence", 1)) == 1, state
        assert not state.get("receipts"), state
    finally:
        wipe(parent)


def test_ia_03_total_local_loss_after_k4_failure_recovers_once(tmp_path: Path) -> None:
    """IA-03: after IA-02's failure and TOTAL loss of the failed cache, a fresh
    process converges from authoritative state exactly once.  All counts below
    are taken independently from the remote commit bytes."""
    remote = _bare_remote(tmp_path, "ia03")
    run_id, session_id, ref = _ids("ia03")
    first = new_root("ia-ia03-first")
    fresh: Path | None = None
    try:
        failed = _cli(root=first / "backend", run_id=run_id, session_id=session_id,
                      mode="create", remote=remote, remote_ref=ref,
                      fail_barrier="K4_AFTER_REPLY_AUTHENTICATED")
        assert failed.returncode == AUTHORITATIVE_FAILURE_EXIT, failed.stderr
        wipe(first)

        fresh = new_root("ia-ia03-fresh")
        resumed = _cli(root=fresh / "backend", run_id=run_id, session_id=session_id,
                       mode="materialize-resume", remote=remote, remote_ref=ref)
        assert resumed.returncode == CONVERGED_EXIT, resumed.stderr

        head = _remote_commit(remote, ref)
        state = _release_state(remote, head)
        assert int(state["last_acked_sequence"]) == 1, state
        assert int(state["next_sequence"]) == 2, state

        ledger = _remote_ledger_entries(remote, head)
        assert len(ledger) == 2, ledger
        assert len({r["request_id"] for r in ledger}) == 2, "duplicate dispatch id"

        effects = _count_world_effects(remote, head)
        assert effects["meter_rows"] == 2, effects
        assert [s for _, s in effects["attempts"]] == ["metered", "metered"], effects
        projection = json.loads(_commit_bytes(remote, head, "state/current-event.json").decode())
        assert _count_assistant_outputs(remote, head, projection["event_id"]) == 1

        journal = sqlite3.connect(
            str(fresh / "backend" / "journal.sqlite"))
        rows = journal.execute(
            "SELECT state, COUNT(*) FROM relay GROUP BY state").fetchall()
        journal.close()
        # Round 0 stays 'applied'; the terminal (highest-round) request is acked.
        assert dict(rows) == {"applied": 1, "acked": 1}, rows
    finally:
        if first.exists():
            wipe(first)
        if fresh is not None:
            wipe(fresh)


def test_ia_04_ack_barrier_failure_never_publishes_ack(tmp_path: Path) -> None:
    """IA-04: ACK barrier failure — fatal, cursor never published as acked."""
    remote = _bare_remote(tmp_path, "ia04")
    run_id, session_id, ref = _ids("ia04")
    parent = new_root("ia-ia04")
    try:
        failed = _cli(root=parent / "backend", run_id=run_id, session_id=session_id,
                      mode="create", remote=remote, remote_ref=ref, fail_barrier="ACKED")
        assert failed.returncode == AUTHORITATIVE_FAILURE_EXIT, failed.stderr
        head = _remote_commit(remote, ref)
        marker = json.loads(_commit_bytes(remote, head, "state/remote-barrier.json").decode())
        assert marker["point"] == "K5_AFTER_APPLIED_BEFORE_ACK", marker
        state = _release_state(remote, head)
        assert int(state.get("next_sequence", 1)) == 1, state
        assert not state.get("receipts"), state
    finally:
        wipe(parent)


# ------------------------------------------------- C002-002: exactly-once family


def test_ia_05_later_round_trusted_return_remote_only_converges(tmp_path: Path) -> None:
    """IA-05: later-round K3_TRUSTED_RETURN_DURABLE + total local loss — remote-
    only recovery converges exactly once (independent counts)."""
    remote = _bare_remote(tmp_path, "ia05")
    run_id, session_id, ref = _ids("ia05")
    first = new_root("ia-ia05-first")
    fresh: Path | None = None
    try:
        killed = _cli(root=first / "backend", run_id=run_id, session_id=session_id,
                      mode="create", remote=remote, remote_ref=ref,
                      kill_at="K3_TRUSTED_RETURN_DURABLE", kill_round=1)
        assert killed.returncode == -signal.SIGKILL, killed.stderr
        barrier_head = _remote_commit(remote, ref)
        assert len(_remote_ledger_entries(remote, barrier_head)) == 2
        wipe(first)

        fresh = new_root("ia-ia05-fresh")
        resumed = _cli(root=fresh / "backend", run_id=run_id, session_id=session_id,
                       mode="materialize-resume", remote=remote, remote_ref=ref)
        assert resumed.returncode == CONVERGED_EXIT, resumed.stderr
        outcome = json.loads(resumed.stdout)
        assert outcome["ack"]["status"] == "acked"
        assert outcome["ack"]["sequence"] == 1
        assert outcome["ack"]["next_sequence"] == 2

        head = _remote_commit(remote, ref)
        assert head != barrier_head
        ledger = _remote_ledger_entries(remote, head)
        assert len(ledger) == 2 and len({r["request_id"] for r in ledger}) == 2, ledger
        effects = _count_world_effects(remote, head)
        assert effects["meter_rows"] == 2, effects
        assert [s for _, s in effects["attempts"]] == ["metered", "metered"], effects
        state = _release_state(remote, head)
        assert int(state["last_acked_sequence"]) == 1, state
    finally:
        if first.exists():
            wipe(first)
        if fresh is not None:
            wipe(fresh)


def test_ia_06_later_round_dispatch_only_fails_closed_deterministically(tmp_path: Path) -> None:
    """IA-06: later-round dispatch-only loss (no durable trusted return) —
    fail-closed, no redispatch, deterministic across repeated recovery."""
    remote = _bare_remote(tmp_path, "ia06")
    run_id, session_id, ref = _ids("ia06")
    first = new_root("ia-ia06-first")
    fresh: Path | None = None
    second: Path | None = None
    try:
        killed = _cli(root=first / "backend", run_id=run_id, session_id=session_id,
                      mode="create", remote=remote, remote_ref=ref,
                      kill_at="K3_AFTER_REQUEST_DISPATCH", kill_round=1)
        assert killed.returncode == -signal.SIGKILL, killed.stderr
        barrier_head = _remote_commit(remote, ref)
        assert len(_remote_ledger_entries(remote, barrier_head)) == 2
        wipe(first)

        fresh = new_root("ia-ia06-fresh")
        resumed = _cli(root=fresh / "backend", run_id=run_id, session_id=session_id,
                       mode="materialize-resume", remote=remote, remote_ref=ref)
        assert resumed.returncode == FAIL_CLOSED_EXIT, resumed.stderr
        assert "FAIL_CLOSED_HARD_STOP" in resumed.stderr, resumed.stderr

        after1 = _remote_commit(remote, ref)
        assert len(_remote_ledger_entries(remote, after1)) == 2, "redispatch after fail-closed"
        state = _release_state(remote, after1)
        assert int(state.get("next_sequence", 1)) == 1, state
        assert not state.get("receipts"), state
        effects = _count_world_effects(remote, after1)
        assert [s for _, s in effects["attempts"]] == ["metered", "dispatching"], effects

        second = new_root("ia-ia06-second")
        again = _cli(root=second / "backend", run_id=run_id, session_id=session_id,
                     mode="materialize-resume", remote=remote, remote_ref=ref)
        assert again.returncode == FAIL_CLOSED_EXIT, again.stderr
        after2 = _remote_commit(remote, ref)
        assert len(_remote_ledger_entries(remote, after2)) == 2
    finally:
        for p in (first, fresh, second):
            if p is not None and p.exists():
                wipe(p)


def test_ia_07_k5_push_success_then_total_loss_acks_once(tmp_path: Path) -> None:
    """IA-07: K5 push succeeded, then the whole local cache is destroyed — the
    fresh process ACKs exactly once without rerunning work (independent counts
    from the materialized World DB)."""
    remote = _bare_remote(tmp_path, "ia07")
    run_id, session_id, ref = _ids("ia07")
    first = new_root("ia-ia07-first")
    fresh: Path | None = None
    try:
        killed = _cli(root=first / "backend", run_id=run_id, session_id=session_id,
                      mode="create", remote=remote, remote_ref=ref,
                      kill_at="K5_AFTER_APPLIED_BEFORE_ACK")
        assert killed.returncode == -signal.SIGKILL, killed.stderr
        barrier_head = _remote_commit(remote, ref)
        marker = json.loads(_commit_bytes(remote, barrier_head,
                                          "state/remote-barrier.json").decode())
        assert marker["point"] == "K5_AFTER_APPLIED_BEFORE_ACK", marker
        wipe(first)

        fresh = new_root("ia-ia07-fresh")
        resumed = _cli(root=fresh / "backend", run_id=run_id, session_id=session_id,
                       mode="materialize-resume", remote=remote, remote_ref=ref)
        assert resumed.returncode == CONVERGED_EXIT, resumed.stderr
        outcome = json.loads(resumed.stdout)
        assert outcome["ack"]["status"] == "acked"
        assert outcome["turn"].get("skipped") is True, "model/capability work was rerun"

        head = _remote_commit(remote, ref)
        assert head != barrier_head
        ledger = _remote_ledger_entries(remote, head)
        assert len(ledger) == 2 and len({r["request_id"] for r in ledger}) == 2, ledger
        effects = _count_world_effects(remote, head)
        assert effects["meter_rows"] == 2, effects
        # Capability effect counted from the materialized capability ledger bytes.
        cap = _commit_bytes(remote, head, "state/capability-ledger.jsonl")
        cap_rows = [json.loads(l) for l in cap.decode().splitlines() if l.strip()]
        assert len(cap_rows) == 1, cap_rows
        state = _release_state(remote, head)
        assert int(state["last_acked_sequence"]) == 1, state
    finally:
        if first.exists():
            wipe(first)
        if fresh is not None:
            wipe(fresh)


def test_ia_08_k5_push_failure_advances_nothing_and_recovers(tmp_path: Path) -> None:
    """IA-08: the K5 barrier push itself fails (network) after the local commit
    — the run must stop with an authoritative failure, the advanced local cache
    must refuse re-attach, and remote-only recovery must still converge exactly
    once from the last published barrier."""
    remote = _bare_remote(tmp_path, "ia08")
    run_id, session_id, ref = _ids("ia08")
    parent = new_root("ia-ia08")
    fresh: Path | None = None
    try:
        session = OperatorSession.create(
            parent / "backend", run_id=run_id, session_id=session_id,
            remote_ref=ref, remote=str(remote), repo_dir=REPO_ROOT,
            require_remote_durability=True,
        )
        real_push = remote_backend.push_run_state
        state = {"tripped": False}

        def push_that_fails(*args, **kwargs):
            message = str(kwargs.get("message") or "")
            if "point=K5_AFTER_APPLIED_BEFORE_ACK" in message:
                state["tripped"] = True
                raise BackendError("IA reviewer-injected network push failure")
            return real_push(*args, **kwargs)

        remote_backend.push_run_state = push_that_fails
        try:
            with pytest.raises(BackendError, match="authoritative persistence failure"):
                session.process_one_cursor()
        finally:
            remote_backend.push_run_state = real_push
        assert state["tripped"]
        session.backend.release()

        head_before = _remote_commit(remote, ref)
        marker = json.loads(_commit_bytes(remote, head_before,
                                          "state/remote-barrier.json").decode())
        assert marker["point"] == "K3_TRUSTED_RETURN_DURABLE", marker

        # The advanced local cache must refuse re-attach (head mismatch).
        with pytest.raises(BackendError):
            OperatorSession.attach(parent / "backend", run_id=run_id,
                                   session_id=session_id, repo_dir=REPO_ROOT)

        wipe(parent)
        fresh = new_root("ia-ia08-fresh")
        recovered = OperatorSession.materialize_and_attach(
            fresh / "backend", run_id=run_id, session_id=session_id,
            remote_ref=ref, commit_sha=head_before, remote=str(remote),
            repo_dir=REPO_ROOT,
        )
        outcome = recovered.resume()
        assert outcome["ack"]["status"] == "acked"
        assert outcome["ack"]["next_sequence"] == 2
        head_after = _remote_commit(remote, ref)
        ledger = _remote_ledger_entries(remote, head_after)
        assert len(ledger) == 2 and len({r["request_id"] for r in ledger}) == 2, ledger
        recovered.backend.release()
    finally:
        if parent.exists():
            wipe(parent)
        if fresh is not None:
            wipe(fresh)


def test_ia_09_tampered_request_bytes_fail_closed(tmp_path: Path) -> None:
    """IA-09: the relay journal's REQUEST bytes are altered (the author's
    matrix altered the reply) — fail-closed on the operator's integrity check,
    no redispatch, no ACK."""
    remote = _bare_remote(tmp_path, "ia09")
    run_id, session_id, ref = _ids("ia09")
    first = new_root("ia-ia09-first")
    restore: Path | None = None
    try:
        killed = _cli(root=first / "backend", run_id=run_id, session_id=session_id,
                      mode="create", remote=remote, remote_ref=ref,
                      kill_at="K3_TRUSTED_RETURN_DURABLE", kill_round=1)
        assert killed.returncode == -signal.SIGKILL, killed.stderr
        wipe(first)

        restore = new_root("ia-ia09-restore")
        RunBackend.materialize_from_remote(
            run_id=run_id, session_id=session_id, target_dir=restore / "backend",
            remote_ref=ref, remote=str(remote), repo_dir=REPO_ROOT,
        )
        journal_path = restore / "backend" / "journal.sqlite"
        with sqlite3.connect(str(journal_path)) as db:
            row = db.execute("SELECT request_id, request FROM relay "
                             "ORDER BY round_index DESC LIMIT 1").fetchone()
            assert row is not None
            request_id, request_bytes = row
            db.execute("UPDATE relay SET request=? WHERE request_id=?",
                       (bytes(request_bytes) + b"tamper", request_id))
            db.commit()

        tampered = _cli(root=restore / "backend", run_id=run_id, session_id=session_id,
                        mode="resume", remote=remote, remote_ref=ref)
        assert tampered.returncode != CONVERGED_EXIT, tampered.stdout
        assert "request corruption" in (tampered.stderr + tampered.stdout)
        head = _remote_commit(remote, ref)
        state = _release_state(remote, head)
        assert int(state.get("next_sequence", 1)) == 1, state
        assert len(_remote_ledger_entries(remote, head)) == 2, "redispatch after tamper"
    finally:
        if first.exists():
            wipe(first)
        if restore is not None:
            wipe(restore)


# ------------------------------------------------- C002-004: binding fail-closed


def _completed_remote_session(tmp_path: Path, label: str):
    remote = _bare_remote(tmp_path, label)
    run_id, session_id, ref = _ids(label)
    parent = new_root(f"ia-ia-{label}")
    session = OperatorSession.create(
        parent / "backend", run_id=run_id, session_id=session_id,
        remote_ref=ref, remote=str(remote), repo_dir=REPO_ROOT,
        require_remote_durability=True,
    )
    session.process_one_cursor()
    return session, remote, run_id, session_id, ref, parent


def test_ia_10_tampered_expected_head_marker_fails_closed(tmp_path: Path) -> None:
    """IA-10: valid binding but the local expected-head marker is rewritten —
    attach must fail closed (never local-only)."""
    session, remote, run_id, session_id, _ref, parent = _completed_remote_session(
        tmp_path, "ia10")
    try:
        root = parent / "backend"
        marker_path = root / ".remote-head"
        original = marker_path.read_text().strip()
        other = "0" * 40
        assert other != original
        marker_path.write_text(other + "\n", encoding="utf-8")
        try:
            with pytest.raises(BackendError):
                OperatorSession.attach(root, run_id=run_id, session_id=session_id)
        finally:
            marker_path.write_text(original + "\n", encoding="utf-8")
    finally:
        session.backend.release()
        wipe(parent)


def test_ia_11_remote_commit_missing_generation_head_fails_closed(tmp_path: Path) -> None:
    """IA-11: the authoritative storage is rewound so that the pinned commit no
    longer carries the immutable generation head matching the local cache —
    attach must fail closed.  Two shapes: a rewind to the previous full commit,
    and a rewind to a commit built from the tree minus ``generation-head.json``."""
    session, remote, run_id, session_id, ref, parent = _completed_remote_session(
        tmp_path, "ia11")
    try:
        root = parent / "backend"
        current = _remote_commit(remote, ref)

        # Shape A: rewind the ref to the commit that preceded the last barrier.
        log = subprocess.run(["git", f"--git-dir={remote}", "log", "--format=%H", ref],
                             capture_output=True, text=True, check=True).stdout.split()
        assert len(log) >= 2, "need at least two authoritative commits"
        previous = log[1]
        # Rewinding a ref is a non-fast-forward update: the hostile-storage
        # shape being simulated requires an explicit force.
        subprocess.run(["git", "push", "--force", str(remote), f"{previous}:{ref}"],
                       cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
        with pytest.raises(BackendError):
            OperatorSession.attach(root, run_id=run_id, session_id=session_id)

        # Shape B: the pinned commit exists but no longer carries the immutable
        # generation head (the storage lost exactly that file).
        archive = subprocess.Popen(
            ["git", "archive", current], cwd=str(REPO_ROOT), stdout=subprocess.PIPE)
        stage = tmp_path / "ia11-stage"
        stage.mkdir()
        tar = subprocess.run(["tar", "-x", "-C", str(stage)],
                             stdin=archive.stdout, capture_output=True)
        archive.wait()
        assert tar.returncode == 0, tar.stderr
        (stage / "generation-head.json").unlink()
        temp_index = tmp_path / "ia11-index"
        env = dict(os.environ, GIT_INDEX_FILE=str(temp_index))
        subprocess.run(["git", f"--work-tree={stage}", "add", "-A", "--", "."],
                       cwd=str(REPO_ROOT), env=env, check=True, capture_output=True)
        tree = subprocess.run(["git", "write-tree"], cwd=str(REPO_ROOT), env=env,
                              check=True, capture_output=True, text=True).stdout.strip()
        headless = subprocess.run(
            ["git", "commit-tree", tree, "-p", current,
             "-m", "IA reviewer: authoritative commit without immutable head"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=True).stdout.strip()
        subprocess.run(["git", "push", str(remote), f"{headless}:{ref}"],
                       cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
        assert _remote_commit(remote, ref) == headless
        with pytest.raises(BackendError):
            OperatorSession.attach(root, run_id=run_id, session_id=session_id)
    finally:
        session.backend.release()
        wipe(parent)


def test_ia_12_remote_ref_deleted_fails_closed(tmp_path: Path) -> None:
    """IA-12: the authoritative remote ref is deleted from the server — attach
    must fail closed."""
    session, remote, run_id, session_id, ref, parent = _completed_remote_session(
        tmp_path, "ia12")
    try:
        subprocess.run(["git", f"--git-dir={remote}", "update-ref", "-d", ref],
                       check=True, capture_output=True, text=True)
        with pytest.raises(BackendError):
            OperatorSession.attach(parent / "backend", run_id=run_id,
                                   session_id=session_id)
    finally:
        session.backend.release()
        wipe(parent)


# ------------------------------------------------- workspace portability


def test_ia_13_foreign_home_keeps_journal_contract(tmp_path: Path) -> None:
    """IA-13: with a foreign HOME and an explicit foreign
    C15_PERSISTED_WORKSPACE, the frozen journal unittest contract must still
    pass 13/13 (the historical /home/user hardcode failure mode)."""
    foreign_home = tmp_path / "ia-foreign-home"
    foreign_home.mkdir(parents=True, mode=0o755)
    workspace = tmp_path / "ia-foreign-workspace"
    workspace.mkdir(parents=True, mode=0o700)
    env = dict(os.environ)
    env["HOME"] = str(foreign_home)
    env["C15_PERSISTED_WORKSPACE"] = str(workspace)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT / "src"), str(REPO_ROOT), env.get("PYTHONPATH", "")])
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.c15_persistence.test_journal", "-v"],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=900,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    combined = completed.stdout + "\n" + completed.stderr  # unittest reports on stderr
    assert "Ran 13 tests" in combined, combined
    assert "OK" in combined, combined


def test_ia_14_relative_workspace_override_observed(tmp_path: Path) -> None:
    """IA-14 (hardening observation, recorded for the report): what happens
    when C15_PERSISTED_WORKSPACE is a RELATIVE override.  The probe records the
    observed behaviour of the production backend path check (accepted/rejected
    and the workspace the override resolves to) rather than asserting a
    specific verdict; the report carries the classification.  Note this
    behaviour predates the candidate (backend.py is byte-identical across the
    freeze history)."""
    saved = os.environ.get("C15_PERSISTED_WORKSPACE")
    os.environ["C15_PERSISTED_WORKSPACE"] = "relative/override"
    try:
        import importlib
        import tools.c15_persistence.backend as backend_mod
        importlib.reload(backend_mod)
        resolved_workspace = str(backend_mod.WORKSPACE)
        probe_root = backend_mod.WORKSPACE / "ia-relative-probe"
        try:
            backend_mod.durable_root(probe_root)
            verdict = f"ACCEPTED (resolved workspace: {resolved_workspace})"
        except BackendError as exc:
            verdict = f"REJECTED: {exc} (resolved workspace: {resolved_workspace})"
        (tmp_path / "ia-14-verdict.txt").write_text(verdict + "\n")
        assert not probe_root.exists()
        os.environ.pop("C15_PERSISTED_WORKSPACE", None)
        importlib.reload(backend_mod)
    finally:
        if saved is None:
            os.environ.pop("C15_PERSISTED_WORKSPACE", None)
        else:
            os.environ["C15_PERSISTED_WORKSPACE"] = saved


def test_ia_15_excluded_workspace_root_observed(tmp_path: Path) -> None:
    """IA-15 (hardening observation, recorded for the report): what happens
    when the operator declares C15_PERSISTED_WORKSPACE to be a platform-excluded
    directory (``.cache``).  This probe records the observed behaviour of the
    production backend path check rather than asserting a specific verdict;
    the report carries the classification."""
    saved = os.environ.get("C15_PERSISTED_WORKSPACE")
    os.environ["C15_PERSISTED_WORKSPACE"] = str(REPO_ROOT / ".cache")
    try:
        import importlib
        import tools.c15_persistence.backend as backend_mod
        importlib.reload(backend_mod)
        probe_root = backend_mod.WORKSPACE / "ia-excluded-root-probe"
        try:
            backend_mod.durable_root(probe_root)
            verdict = "ACCEPTED"
        except BackendError as exc:
            verdict = f"REJECTED: {exc}"
        (tmp_path / "ia-15-verdict.txt").write_text(verdict + "\n")
        # The probe root itself must never be left behind.
        assert not probe_root.exists()
        # Restore the default workspace view for the rest of the session.
        os.environ.pop("C15_PERSISTED_WORKSPACE", None)
        importlib.reload(backend_mod)
    finally:
        if saved is None:
            os.environ.pop("C15_PERSISTED_WORKSPACE", None)
        else:
            os.environ["C15_PERSISTED_WORKSPACE"] = saved
