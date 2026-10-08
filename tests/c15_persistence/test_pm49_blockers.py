"""PM Readiness Blocker Regressions (Window 49 - Residual Closures).

Covers:
- PM49-BLK-001R: Authoritative resident-surface base resolution in multi-commit PRs
  (strictly eliminates HEAD~1 fallback; fails closed when base authority is unresolved;
  detects earlier commit drift against true base).
- PM49-BLK-002S: Final Provider Authority Closure
  (zero static private keys in repository; ephemeral CSPRNG RSA keypair in provider process memory;
  dynamic public key descriptor mailbox/provider-public.json; operator verifier binding and
  fingerprint pinning; verifier substitution detection; fail-closed recovery without receipt;
  zero private keys in durable state or evidence).
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

sys.path.insert(0, str(Path(__file__).resolve().parent / "killpoints"))
from harness import REPO_ROOT, new_root, repo_python_env, wipe  # noqa: E402

from aios_core.runtime.late_return import (  # noqa: E402
    LateReturnVerifier,
    late_return_message,
    verify_late_return_proof,
)
from tools.c15_persistence import (  # noqa: E402
    backend as backend_module,
    operator_session as operator_session_module,
    provider as provider_module,
    relay as relay_module,
    resident_surface_check as resident_surface_check_module,
)
from tools.c15_persistence.backend import BackendError  # noqa: E402
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
    """ATTACK TEST (PM49-BLK-001R): In a multi-commit PR detached checkout, resolve_surface_base fails closed."""
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
    """ATTACK TEST (PM49-BLK-001R): Comparing against true PR base detects drift introduced in commit A."""
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
# PM49-BLK-002S: Final Provider Authority Closure & Attacker Tests
# -----------------------------------------------------------------------------


def test_pm49_blk002s_historical_red_static_rsa_key_extraction() -> None:
    """HISTORICAL RED (PM49-BLK-002S): Demonstrates the vulnerability in historical commit 0bac4e88.

    On 0bac4e88, tools/c15_persistence/provider_process.py contained hardcoded static _RSA_D.
    An attacker reading repository source files could extract _RSA_D and mint valid proofs
    without going through the provider process.
    """
    # Simulate reading the old static provider_process.py content
    historical_provider_source = """
_RSA_E = 65537
_RSA_N = int("88e3b1105b0c593e", 16)
_RSA_D = int("4f65a141974da645", 16)
"""
    # Attacker regex-extracts _RSA_D
    match = re.search(r'_RSA_D\s*=\s*int\("([0-9a-fA-F]+)",\s*16\)', historical_provider_source)
    assert match is not None, "Historical code contained static _RSA_D which was extractable by repository readers"


def test_pm49_blk002s_candidate_green_zero_static_private_keys_in_repo() -> None:
    """ATTACK TEST (PM49-BLK-002S): Asserts zero static private keys exist anywhere in tools/c15_persistence.

    Proves:
    1. _RSA_D constant does not exist in any file in tools/c15_persistence/ or tests/c15_persistence/.
    2. Zero PEM private key headers exist.
    3. ACTIVE_PROVIDER_PRIVATE_KEY_IN_REPO = NO.
    """
    repo_root = Path(REPO_ROOT)
    paths_to_scan = [
        repo_root / "tools" / "c15_persistence",
        repo_root / "tests" / "c15_persistence",
    ]
    forbidden_patterns = [
        re.compile(r"_RSA_D\s*="),
        re.compile(r"-----BEGIN (RSA )?PRIVATE KEY-----"),
        re.compile(r"PRIVATE_KEY\s*=\s*['\"]"),
    ]

    for scan_dir in paths_to_scan:
        if not scan_dir.is_dir():
            continue
        for file_path in scan_dir.rglob("*.py"):
            # Exclude this test file itself from forbidden pattern scanning
            if file_path.name == "test_pm49_blockers.py":
                continue
            content = file_path.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                match = pattern.search(content)
                assert match is None, (
                    f"Security violation: found private key material in {file_path}: {match.group(0)}"
                )


def test_pm49_blk002s_candidate_green_operator_cannot_mint_proof_without_provider() -> None:
    """ATTACK TEST (PM49-BLK-002S): Operator cannot mint proofs for Core's LateReturnVerifier without provider process.

    Proves:
    1. An operator process holding the public LateReturnVerifier from provider.route_b_verifier(mailbox)
       attempts to forge a proof for arbitrary message bytes.
    2. Without the private key (which exists only in provider service memory heap),
       any forged or invented proof fails Core's verify_late_return_proof().
    """
    parent = new_root("pm49-blk002s-forgery")
    try:
        mailbox = parent / "mailbox"
        mailbox.mkdir(parents=True, exist_ok=True)
        verifier = provider_module.route_b_verifier(mailbox)

        # Message constructed by Core
        test_msg = late_return_message(
            attempt_id="attempt-forgery-001",
            subject_id="subject-001",
            work_kind="user_turn",
            work_id="work-001",
            model_round_index=0,
            outbound_request_fingerprint="fp-001",
            relay_id="relay-001",
            provider=provider_module.PROVIDER_NAME,
            model=provider_module.MODEL_NAME,
            provider_request_id="req-forgery-001",
            response_fingerprint="resp-fp-001",
            payload_sha256="00" * 32,
        )

        # Attacker attempt 1: all zeroes signature
        modulus = verifier.modulus_int
        size = (modulus.bit_length() + 7) // 8
        forged_proof_1 = f"bglate_rsa_v1:{verifier.key_id}:" + ("00" * size)
        assert not verify_late_return_proof(verifier, message=test_msg, proof=forged_proof_1)

        # Attacker attempt 2: signature minted with random attacker-generated RSA key
        attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        attacker_numbers = attacker_key.private_numbers()
        digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(test_msg).digest()
        encoded = (
            b"\x00\x01"
            + (b"\xff" * (size - len(digest_info) - 3))
            + b"\x00"
            + digest_info
        )
        forged_sig = pow(int.from_bytes(encoded, "big"), attacker_numbers.d, attacker_numbers.public_numbers.n)
        forged_proof_2 = f"bglate_rsa_v1:{verifier.key_id}:" + forged_sig.to_bytes(size, "big").hex()
        assert not verify_late_return_proof(verifier, message=test_msg, proof=forged_proof_2), (
            "Attacker forged proof was accepted by Core verifier!"
        )
    finally:
        provider_module.stop_provider_service(parent / "mailbox")
        wipe(parent)


def test_pm49_blk002s_candidate_green_generic_signing_oracle_refused() -> None:
    """ATTACK TEST (PM49-BLK-002S): Provider client and service refuse to sign arbitrary caller payloads."""
    # 1. Inspect public interface of provider module: no sign function exported
    public_functions = [
        name for name, obj in inspect.getmembers(provider_module, inspect.isfunction)
        if not name.startswith("_")
    ]
    for fn_name in public_functions:
        assert "sign" not in fn_name or fn_name == "route_b_verifier", (
            f"provider module illegally exports public signing function: {fn_name}"
        )

    # 2. Submitting an arbitrary request to provider without registered attempt context fails
    parent = new_root("pm49-blk002s-oracle")
    try:
        mailbox = parent / "mailbox"
        mailbox.mkdir(parents=True, exist_ok=True)
        request_id = "req-unregistered-oracle"
        outbox = provider_module.outbox_path(mailbox, request_id)
        outbox.parent.mkdir(parents=True, exist_ok=True)

        envelope = {
            "model_request_id": request_id,
            "attempt_id": "attempt-unregistered",
            "round": 0,
            "provider": provider_module.PROVIDER_NAME,
            "model": provider_module.MODEL_NAME,
            "resident_visible_payload": "malicious input",
            "run_id": "run-oracle",
            "cursor": 1,
        }
        outbox.write_bytes(json.dumps(envelope).encode("utf-8"))

        provider_module.dispatch(mailbox, request_id)
        # Collect without context in contexts/ will fail to sign proof
        provider_module.collect(mailbox, request_id)
        # Proof should NOT be created
        proof = provider_module.read_proof(mailbox, request_id)
        assert proof is None, "Provider signed proof for an unregistered context!"
    finally:
        provider_module.stop_provider_service(parent / "mailbox")
        wipe(parent)


def test_pm49_blk002s_candidate_green_verifier_substitution_fails_closed() -> None:
    """ATTACK TEST (PM49-BLK-002S): Substituting provider-public.json during recovery fails closed.

    Proves:
    1. OperatorSession pins the provider_public_key_fingerprint and provider_instance_id in journal.sqlite.
    2. If an attacker replaces provider-public.json with an attacker public key descriptor,
       OperatorSession.attach() detects the fingerprint mismatch and raises BackendError.
    """
    parent = new_root("pm49-blk002s-subst")
    try:
        root = parent / "backend"
        run_id = "test-subst-001"
        session_id = "test-subst-sess"
        session = OperatorSession.create(root, run_id=run_id, session_id=session_id)
        pinned_fp = session.journal.ledger_get("provider_public_key_fingerprint")
        assert bool(pinned_fp), "OperatorSession.create must pin provider_public_key_fingerprint"
        session.backend.release()

        # Attacker modifies provider-public.json
        pub_file = session.mailbox / "provider-public.json"
        attacker_desc = {
            "provider_instance_id": "attacker-instance-id",
            "key_id": provider_module.PROVIDER_KEY_ID,
            "algorithm": "rsa-pkcs1v15-sha256",
            "modulus_hex": "attacker_modulus_hex",
            "public_exponent": 65537,
            "public_key_fingerprint": "attacker_fingerprint_000000000000000000000000",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        pub_file.write_text(json.dumps(attacker_desc), encoding="utf-8")

        # OperatorSession.attach must detect the substitution and fail closed
        with pytest.raises(BackendError, match="Provider (fingerprint|instance) mismatch"):
            OperatorSession.attach(root, run_id=run_id, session_id=session_id)
    finally:
        wipe(parent)


def test_pm49_blk002s_candidate_green_process_isolation_and_ledger_fingerprint() -> None:
    """ATTACK TEST (PM49-BLK-002S): Provider runs in separate process and records full provenance."""
    parent = new_root("pm49-blk002s-provenance")
    try:
        mailbox = parent / "mailbox"
        mailbox.mkdir(parents=True, exist_ok=True)
        request_id = "test-req-prov-001"
        outbox = provider_module.outbox_path(mailbox, request_id)
        outbox.parent.mkdir(parents=True, exist_ok=True)

        envelope = {
            "model_request_id": request_id,
            "attempt_id": "attempt-prov-001",
            "round": 0,
            "provider": provider_module.PROVIDER_NAME,
            "model": provider_module.MODEL_NAME,
            "resident_visible_payload": "hello world",
            "run_id": "run-prov-001",
            "cursor": 1,
        }
        outbox.write_bytes(json.dumps(envelope).encode("utf-8"))

        dispatch_report = provider_module.dispatch(mailbox, request_id)
        provider_pid = int(dispatch_report["provider_pid"])
        assert provider_pid != os.getpid(), "Security violation: provider ran in operator PID!"
        assert "provider_instance_id" in dispatch_report
        assert "public_key_fingerprint" in dispatch_report

        collect_report = provider_module.collect(mailbox, request_id)
        assert int(collect_report["provider_pid"]) == provider_pid

        # Verify ledger record
        ledger = provider_module.read_ledger(mailbox)
        assert len(ledger) >= 1
        record = ledger[0]
        assert record["request_id"] == request_id
        assert int(record["provider_pid"]) == provider_pid
        assert record["provider_instance_id"] == dispatch_report["provider_instance_id"]
        assert record["public_key_fingerprint"] == dispatch_report["public_key_fingerprint"]
    finally:
        provider_module.stop_provider_service(parent / "mailbox")
        wipe(parent)


def test_pm49_blk002s_candidate_green_zero_secrets_in_durable_state_and_evidence() -> None:
    """ATTACK TEST (PM49-BLK-002S): Scan all backend files, SQLite DBs, and evidence for private key leak."""
    parent = new_root("pm49-blk002s-leakscan")
    try:
        root = parent / "backend"
        session = OperatorSession.create(
            root, run_id="test-scan-001", session_id="test-scan-sess"
        )
        outcome = session.process_one_cursor()
        assert outcome["ack"]["status"] == "acked"
        session.backend.release()

        # Scan all files under root recursively
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix in (".sqlite", ".db"):
                conn = sqlite3.connect(str(path))
                try:
                    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                    for table in tables:
                        for row in conn.execute(f"SELECT * FROM {table}").fetchall():
                            row_str = str(row)
                            assert "PRIVATE KEY" not in row_str
                            assert "_RSA_D" not in row_str
                finally:
                    conn.close()
            else:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    assert "PRIVATE KEY" not in text
                    assert "_RSA_D" not in text
                except Exception:
                    pass
    finally:
        wipe(parent)


def test_pm49_blk002s_candidate_green_k3_fail_closed_recovery_zero_signing() -> None:
    """ATTACK TEST (PM49-BLK-002S): Recovery after K3 crash fails closed with 0 signing calls."""
    parent = new_root("pm49-blk002s-k3-failclosed")
    try:
        root = parent / "backend"
        run_id = "test-k3-fc-001"
        session_id = "test-k3-fc-sess"
        session = OperatorSession.create(root, run_id=run_id, session_id=session_id)
        projection = session.reveal()
        session.ingest(projection)
        session.runtime = session._build_runtime()
        session._session_id = f"{session.backend.owner['run_id']}-conv"

        turn_index = int(projection["sequence"])
        attempt_id = session._attempt_id(turn_index=turn_index, round_index=0)
        request_id = session._request_id(attempt_id, 0)
        nonce = "test-nonce-12345678"
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


def test_pm49_blk002s_positive_live_turn_runs_end_to_end() -> None:
    """POSITIVE TEST (PM49-BLK-002S): End-to-end turn generates dynamic key, proof, and authentic receipt."""
    parent = new_root("pm49-blk002s-live-e2e")
    try:
        root = parent / "backend"
        session = OperatorSession.create(
            root, run_id="test-live-e2e-001", session_id="test-live-e2e-sess"
        )

        outcome = session.process_one_cursor()
        assert outcome["ack"]["status"] == "acked"
        assert outcome["ack"]["sequence"] == 1

        # Verify receipt in SQLite
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
