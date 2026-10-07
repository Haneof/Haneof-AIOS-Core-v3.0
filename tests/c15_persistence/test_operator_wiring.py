"""Production-wiring tests for the C15 persistence corrective.

The historical 13 synthetic journal tests only cover the synthetic library.  This
file covers what §21 of the task requires: the real operator integration path,
durable backend reopen, lock ownership, path rejection, exact bytes, crash
barriers, Core receipt revalidation, interrupted-transaction rollback, tamper
detection, identity-mismatch rejection, no-second-semantic-engine and no
duplicate side effects.

Every test uses disposable synthetic state under the authoritative backend path.
No real Resident, no real fixture, no real cursor, no Core source modification.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "killpoints"))

from harness import REPO_ROOT, new_root, repo_python_env, run_clip, wipe  # noqa: E402

from tools.c15_persistence.backend import (  # noqa: E402
    BackendError,
    GenerationStore,
    RunBackend,
    canonical_json,
    digest,
    durable_root,
    runs_root,
)
from tools.c15_persistence.journal import WORKSPACE  # noqa: E402
from tools.c15_persistence.operator_session import OperatorSession  # noqa: E402
from tools.c15_persistence.relay import RelayJournal  # noqa: E402
from tools.c15_persistence.runstate import (  # noqa: E402
    capture_manifest,
    verify_reattach,
    write_manifest,
)


def _ids(prefix: str = "wiring") -> tuple[str, str]:
    token = uuid.uuid4().hex[:8]
    return f"synthetic-run-{prefix}-{token}", f"synthetic-session-{prefix}-{token}"


# --------------------------------------------------------------- path policy


def test_authoritative_path_rejects_every_ephemeral_location() -> None:
    # Corrective-003 portability correction: workspace-relative cases are derived
    # from the resolved workspace, so the probe keeps testing the workspace root
    # itself and the excluded locations (.cache/.venv/node_modules/build/dist/
    # out/target/.git) on every account, instead of silently degrading to
    # "outside the workspace" on the formal CI account.
    for bad in (
        "/tmp/x",
        "/var/tmp/x",
        "/dev/shm/x",
        "/run/user/1000/x",
        str(WORKSPACE),
        str(WORKSPACE / ".cache" / "x"),
        str(WORKSPACE / ".venv" / "x"),
        str(WORKSPACE / "node_modules" / "x"),
        str(WORKSPACE / "build" / "x"),
        str(WORKSPACE / "dist" / "x"),
        str(WORKSPACE / "out" / "x"),
        str(WORKSPACE / "target" / "x"),
        str(WORKSPACE / ".git" / "x"),
    ):
        with pytest.raises(BackendError):
            durable_root(bad)


def test_authoritative_path_rejects_symlink_alias_to_tmp() -> None:
    root = new_root("symlink")
    try:
        link = root / "alias"
        link.symlink_to("/tmp", target_is_directory=True)
        with pytest.raises(BackendError):
            durable_root(link / "backend")
    finally:
        wipe(root)


def test_default_runs_root_is_under_the_persisted_workspace() -> None:
    root = runs_root()
    workspace = Path(
        os.environ.get("C15_PERSISTED_WORKSPACE") or Path.home()
    ).expanduser().resolve()
    assert root == workspace / "c15-persistence-runs"
    assert root != workspace


# ------------------------------------------------------- create / reopen / lock


def test_creation_is_exclusive_and_reopen_never_rebuilds() -> None:
    root = new_root("exclusive")
    run_id, session_id = _ids()
    try:
        backend = RunBackend.create(
            root / "backend", run_id=run_id, session_id=session_id,
            subject_id="user_1", phase="A",
        )
        assert (root / "backend" / "owner.json").is_file()
        backend.release()
        with pytest.raises(BackendError):
            RunBackend.create(
                root / "backend", run_id=run_id, session_id=session_id,
                subject_id="user_1", phase="A",
            )
        reopened = RunBackend.open(root / "backend", run_id=run_id, session_id=session_id)
        assert reopened.owner["run_id"] == run_id
        reopened.release()
    finally:
        wipe(root)


def test_reopen_rejects_identity_mismatch_and_missing_state() -> None:
    root = new_root("identity")
    run_id, session_id = _ids()
    try:
        backend = RunBackend.create(
            root / "backend", run_id=run_id, session_id=session_id,
            subject_id="user_1", phase="A",
        )
        backend.release()
        with pytest.raises(BackendError, match="session identity mismatch"):
            RunBackend.open(root / "backend", run_id=run_id, session_id="synthetic-other")
        with pytest.raises(BackendError, match="run identity mismatch"):
            RunBackend.open(root / "backend", run_id="synthetic-other", session_id=session_id)
        missing = root / "absent"
        with pytest.raises(BackendError, match="does not exist"):
            RunBackend.open(missing, run_id=run_id, session_id=session_id)
        assert not missing.exists()
    finally:
        wipe(root)


def test_retired_rerun002_identities_are_permanently_forbidden() -> None:
    root = new_root("retired")
    try:
        with pytest.raises(BackendError, match="retired"):
            RunBackend.create(
                root / "backend",
                run_id="c15-rcc-res-b-rerun-002-65e6e826",
                session_id="synthetic-session-x",
                subject_id="user_1",
                phase="B",
            )
        with pytest.raises(BackendError, match="retired"):
            RunBackend.create(
                root / "backend2",
                run_id="synthetic-run-x",
                session_id="c15-rcc-res-b-session-002-65e6e826",
                subject_id="user_1",
                phase="B",
            )
    finally:
        wipe(root)


def test_lock_is_exclusive_across_live_processes() -> None:
    root = new_root("lock")
    run_id, session_id = _ids()
    try:
        RunBackend.create(
            root / "backend", run_id=run_id, session_id=session_id,
            subject_id="user_1", phase="A",
        )
        script = (
            "import sys; sys.path.insert(0, %r);"
            "from tools.c15_persistence.backend import RunBackend;"
            "RunBackend.open(%r, run_id=%r, session_id=%r, adopt_stale_owner=False)"
            % (str(REPO_ROOT), str(root / "backend"), run_id, session_id)
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=repo_python_env(),
            timeout=120,
            cwd=str(REPO_ROOT),
        )
        assert completed.returncode != 0
        assert "refusing concurrent ownership" in (completed.stderr or "")
    finally:
        subprocess.run(["pkill", "-f", "c15-persistence-runs/probe-lock"], check=False)
        wipe(root)


# ------------------------------------------------------------ exact bytes


def test_relay_journal_preserves_exact_bytes_and_detects_tampering() -> None:
    root = new_root("bytes")
    run_id, session_id = _ids()
    try:
        backend = RunBackend.create(
            root / "backend", run_id=run_id, session_id=session_id,
            subject_id="user_1", phase="A",
        )
        journal = RelayJournal(backend, create=True)
        request = b'{ "synthetic": true, "unicode": "\xe4\xbd\xa0" }\r\n'
        reply = b' {"reply": true}\n'
        metadata = {
            "run_id": run_id,
            "session_id": session_id,
            "provider": "synthetic-provider",
            "model": "synthetic-model",
            "model_request_id": f"synthetic-request-{uuid.uuid4().hex[:8]}",
            "attempt_id": f"synthetic-attempt-{uuid.uuid4().hex[:8]}",
            "nonce": "synthetic-nonce",
            "event_id": "synthetic-evt-0001",
            "cursor": 1,
            "round": 0,
            "request_fingerprint": digest(request),
            "binding_digest": digest(b"{}"),
        }
        journal.stage(metadata, request, generation=0)
        request_id = metadata["model_request_id"]
        assert journal.expose(request_id) == request
        journal.stage_reply(request_id, reply)
        backend.release()
        reopened = RunBackend.open(root / "backend", run_id=run_id, session_id=session_id,
                                   adopt_stale_owner=True)
        recovered = RelayJournal(reopened).recovery(request_id)
        assert recovered["request"] == request
        assert recovered["reply"] == reply
        assert recovered["state"] == "reply-staged"
        assert recovered["request_sha256"] == digest(request)
        assert recovered["reply_sha256"] == digest(reply)
        reopened.release()

        # Tampering with the durable bytes is detected, never silently accepted.
        db = sqlite3.connect(backend.journal_path)
        db.execute("UPDATE relay SET request=? WHERE request_id=?", (b"tampered", request_id))
        db.commit()
        db.close()
        reopened2 = RunBackend.open(root / "backend", run_id=run_id, session_id=session_id,
                                    adopt_stale_owner=True)
        with pytest.raises(BackendError, match="request corruption"):
            RelayJournal(reopened2).recovery(request_id)
    finally:
        wipe(root)


def test_conflicting_reply_bytes_are_refused_not_rewritten() -> None:
    root = new_root("conflict")
    run_id, session_id = _ids()
    try:
        backend = RunBackend.create(
            root / "backend", run_id=run_id, session_id=session_id,
            subject_id="user_1", phase="A",
        )
        journal = RelayJournal(backend, create=True)
        backend.release()
        metadata = {
            "run_id": run_id,
            "session_id": session_id,
            "provider": "p",
            "model": "m",
            "model_request_id": f"synthetic-request-{uuid.uuid4().hex[:8]}",
            "attempt_id": f"synthetic-attempt-{uuid.uuid4().hex[:8]}",
            "nonce": "n",
            "event_id": "synthetic-evt-0001",
            "cursor": 1,
            "round": 0,
            "request_fingerprint": digest(b"x"),
            "binding_digest": digest(b"{}"),
        }
        journal.stage(metadata, b"exact-request", generation=0)
        rid = metadata["model_request_id"]
        journal.expose(rid)
        journal.stage_reply(rid, b"exact-reply")
        journal.stage_reply(rid, b"exact-reply")  # identical redelivery: idempotent
        with pytest.raises(BackendError, match="conflicting reply"):
            journal.stage_reply(rid, b"different-reply")
        assert journal.recovery(rid)["reply"] == b"exact-reply"
    finally:
        wipe(root)


def test_interrupted_transaction_rolls_back() -> None:
    root = new_root("rollback")
    run_id, session_id = _ids()
    try:
        created = run_clip(
            root, run_id, session_id, ["--mode", "create"]
        )
        assert created.returncode == 0
        script = (
            "import os, signal, sqlite3, sys\n"
            "c = sqlite3.connect(sys.argv[1])\n"
            "c.execute('BEGIN IMMEDIATE')\n"
            "c.execute('DELETE FROM relay')\n"
            "os.kill(os.getpid(), signal.SIGKILL)\n"
        )
        killed = subprocess.run(
            [sys.executable, "-c", script, str(root / "backend" / "journal.sqlite")],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert killed.returncode == -signal.SIGKILL
        report = run_clip(root, run_id, session_id, ["--mode", "report"])
        assert report.returncode == 0
        # The pre-crash rows survived the uncommitted delete.
        payload = json.loads(report.stdout)
        assert payload["generations"], "sealed generations were destroyed"
    finally:
        wipe(root)


# ---------------------------------------------- operator integration / Core


def test_real_operator_integration_path_reaches_ack() -> None:
    root = new_root("integration")
    run_id, session_id = _ids()
    try:
        completed = run_clip(root, run_id, session_id, ["--mode", "create"])
        assert completed.returncode == 0
        outcome = json.loads(completed.stdout)
        assert outcome["ack"]["status"] == "acked"
        assert outcome["ack"]["next_sequence"] == 2
        assert outcome["observed"]["counters"]["reveals"] == 1
        assert outcome["observed"]["counters"]["ingests"] == 1
        assert outcome["observed"]["counters"]["acks"] == 1
        assert outcome["observed"]["metering_rows"] >= 1
        assert len(outcome["observed"]["dispatch_ledger"]) >= 1
        # Sealed generations all re-verify byte-for-byte.
        assert outcome["observed"]["generations"]
    finally:
        wipe(root)


def test_core_receipt_revalidation_rejects_an_operator_invented_receipt() -> None:
    """The journal stores receipts; only Core validates them.

    Corrective-003 probe correction: the historical probe relied on Core never
    holding a staged response after an ordinary run, which is no longer true -
    accepted Core legitimately stages its own trusted-return handoff while the
    turn advances to the next round.  The probe now stores the invented receipt
    in the journal (the actual operator-side attack) and proves Core refuses it,
    while a genuine Core receipt still cross-checks cleanly.
    """
    root = new_root("receipt")
    run_id, session_id = _ids()
    try:
        created = run_clip(root, run_id, session_id, ["--mode", "create"])
        assert created.returncode == 0
        session = OperatorSession.attach(root / "backend", run_id=run_id, session_id=session_id)
        session.runtime = session._build_runtime()
        session._session_id = f"{run_id}-conv"
        attempts = session.runtime.background_model_attempts
        request_id = session.journal.request_ids()[0]
        record = session.journal.recovery(request_id)
        attempt_id = str(record["metadata"]["attempt_id"])
        payload = bytes(record["reply"]).decode("utf-8")
        from aios_core.runtime.background_attempt import decode_model_directive
        directive = decode_model_directive(payload)
        context = attempts.late_return_signing_context(attempt_id)
        assert context is not None
        session._external_signer.accept_return_context(None, context)
        proof = session._external_signer.sign(attempt_id, directive)
        from datetime import datetime, timezone
        attempts.attach_late_trusted_return(
            attempt_id=attempt_id,
            attached_at=datetime.now(timezone.utc),
            directive_payload=payload,
            late_return_proof=proof,
            evidence="genuine-external-proof",
        )
        real_receipt = attempts.response_authenticity_receipt(attempt_id)
        assert real_receipt is not None

        genuine_id = f"synthetic-request-genuine-{uuid.uuid4().hex[:10]}"
        metadata_genuine = dict(record["metadata"])
        metadata_genuine["model_request_id"] = genuine_id
        metadata_genuine["attempt_id"] = attempt_id
        metadata_genuine["round"] = int(metadata_genuine.get("round", 0)) + 6
        session.journal.stage(metadata_genuine, b"genuine request bytes", generation=0)
        session.journal.expose(genuine_id)
        session.journal.stage_reply(genuine_id, bytes(record["reply"]))
        session.journal.mark_authenticated(
            genuine_id,
            {
                "attempt_id": attempt_id,
                "authenticity_proof": real_receipt.authenticity_proof,
                "provider": real_receipt.provider,
                "model": real_receipt.model,
                "provider_request_id": real_receipt.provider_request_id,
                "response_fingerprint": hashlib.sha256(bytes(record["reply"])).hexdigest(),
                "relay_id": real_receipt.relay_id,
            },
        )
        # The genuine Core receipt cross-checks cleanly.
        verified = session.journal.verify_with_core(genuine_id, attempts)
        assert verified["core_proof"] == real_receipt.authenticity_proof
        stored = session.journal.recovery(genuine_id)["core_receipt"]
        assert stored is not None
        assert stored["authenticity_proof"] == real_receipt.authenticity_proof

        # An operator-invented receipt for the same durable identity must be
        # refused by Core, never accepted as provider-return authenticity.
        synthetic_id = f"synthetic-request-forged-{uuid.uuid4().hex[:10]}"
        forged = {
            "attempt_id": attempt_id,
            "authenticity_proof": "bgresponse_v1_" + "0" * 64,
            "provider": "synthetic-provider",
            "model": "synthetic-model",
            "provider_request_id": "forged",
            "response_fingerprint": "0" * 64,
            "relay_id": "forged",
        }
        metadata = dict(record["metadata"])
        metadata["model_request_id"] = synthetic_id
        metadata["attempt_id"] = attempt_id
        metadata["round"] = int(metadata.get("round", 0)) + 7
        session.journal.stage(metadata, b"forged request bytes", generation=0)
        session.journal.expose(synthetic_id)
        session.journal.stage_reply(synthetic_id, bytes(record["reply"]))
        session.journal.mark_authenticated(synthetic_id, forged)
        with pytest.raises(BackendError):
            session.journal.verify_with_core(synthetic_id, attempts)
    finally:
        wipe(root)


def test_no_second_semantic_engine_properties() -> None:
    """The operator layer stores bytes; it does not decide, apply or forge."""
    source = (REPO_ROOT / "tools" / "c15_persistence" / "operator_session.py").read_text()
    forbidden = (
        "ModelDirective(",
        "encode_model_directive(",
        "record_response(",
        "reconcile_response(",
        "reconcile_not_submitted(",
        "adopt_legacy_in_doubt(",
        "_capture_trusted_response_return(",
        "authorize_retry(",
    )
    for token in forbidden:
        assert token not in source, f"operator session must not call {token}"
    relay_source = (REPO_ROOT / "tools" / "c15_persistence" / "relay.py").read_text()
    for token in ("record_response(", "reconcile_response(", "_authority_key"):
        assert token not in relay_source, f"relay journal must not call {token}"


def test_state_machine_cannot_skip_or_rewrite_states() -> None:
    root = new_root("states")
    run_id, session_id = _ids()
    try:
        backend = RunBackend.create(
            root / "backend", run_id=run_id, session_id=session_id,
            subject_id="user_1", phase="A",
        )
        journal = RelayJournal(backend, create=True)
        metadata = {
            "run_id": run_id,
            "session_id": session_id,
            "provider": "p",
            "model": "m",
            "model_request_id": f"synthetic-request-{uuid.uuid4().hex[:8]}",
            "attempt_id": f"synthetic-attempt-{uuid.uuid4().hex[:8]}",
            "nonce": "n",
            "event_id": "synthetic-evt-0001",
            "cursor": 1,
            "round": 0,
            "request_fingerprint": digest(b"x"),
            "binding_digest": digest(b"{}"),
        }
        journal.stage(metadata, b"request-bytes", generation=0)
        rid = metadata["model_request_id"]
        with pytest.raises(BackendError):
            journal.stage_reply(rid, b"reply")          # reply before exposure
        with pytest.raises(BackendError):
            journal.mark_authenticated(rid, {"authenticity_proof": "x"})
        with pytest.raises(BackendError):
            journal.begin_applying(rid)
        with pytest.raises(BackendError):
            journal.mark_applied(rid)
        with pytest.raises(BackendError):
            journal.mark_acked(rid, {"sequence": 1})
        raw = journal.expose(rid)
        assert raw == b"request-bytes"
        with pytest.raises(BackendError):
            journal.expose(rid)                          # no second exposure
        journal.stage_reply(rid, b"reply-bytes")
        journal.mark_authenticated(rid, {"authenticity_proof": "core-proof"})
        assert journal.begin_applying(rid) == b"reply-bytes"
        assert journal.recovery(rid)["disposition"] == "IN_DOUBT_STOP"
        with pytest.raises(BackendError):
            journal.begin_applying(rid)                  # in-doubt stays in-doubt
    finally:
        wipe(root)


# --------------------------------------------------------- generation sealing


def test_sealed_generations_are_immutable_and_reverify() -> None:
    root = new_root("generations")
    run_id, session_id = _ids()
    try:
        backend = RunBackend.create(
            root / "backend", run_id=run_id, session_id=session_id,
            subject_id="user_1", phase="A",
        )
        store = GenerationStore(backend)
        generation = store.seal({"a/one.bin": b"exact-bytes", "b/two.bin": b"\x00\x01"}, label="test")
        assert store.verify(generation)["artifacts"]["a/one.bin"] == digest(b"exact-bytes")
        target = backend.generations_dir / f"{generation:06d}"
        assert (target.stat().st_mode & 0o777) == 0o500
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            assert (target.stat().st_mode & 0o222) == 0
        else:
            with pytest.raises(OSError):
                (target / "sneaky.bin").write_bytes(b"x")
        tampered = target / "a" / "one.bin"
        os.chmod(tampered, 0o600)
        tampered.write_bytes(b"tampered")
        os.chmod(tampered, 0o400)
        with pytest.raises(BackendError, match="generation artifact corruption"):
            store.verify(generation)
    finally:
        wipe(root)


def test_run_state_manifest_detects_a_vanished_slot() -> None:
    root = new_root("runstate")
    run_id, session_id = _ids()
    try:
        backend = RunBackend.create(
            root / "backend", run_id=run_id, session_id=session_id,
            subject_id="user_1", phase="A",
        )
        journal = RelayJournal(backend, create=True)
        backend.release()
        from tools.c15_persistence.synthetic_release import SyntheticRelease

        release = SyntheticRelease(backend.state_dir / "synthetic-release")
        session = OperatorSession(backend, journal, release)
        session.prepare_world()
        session.ensure_release_initialized()
        projection = session.reveal()
        session.ingest(projection)
        manifest = capture_manifest(
            backend, cursor=1, event_id="synthetic-evt-0001", phase="A"
        )
        path = write_manifest(backend, manifest)
        report = verify_reattach(backend, manifest)
        assert report["reattached"] is True
        (backend.state_dir / "current-event.json").write_bytes(b'{"synthetic": false}\n')
        with pytest.raises(BackendError, match="slot changed"):
            verify_reattach(backend, manifest)
        (backend.state_dir / "current-event.json").unlink()
        with pytest.raises(BackendError, match="slot vanished"):
            verify_reattach(backend, manifest)
        assert path.is_file()
    finally:
        wipe(root)
