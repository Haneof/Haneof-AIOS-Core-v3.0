"""CA2-001 .. CA2-015: reviewer-oriented Corrective-002 attack matrix.

Frozen expectations (Corrective-002 scope `C2-1` .. `C2-9`):

* no object reachable from a post-crash recovery runtime can create a trusted
  receipt, exact handoff or staged trusted response without a genuine externally
  verified RSA late-return proof over a verifier that was durably bound before the
  provider boundary;
* the historical live provider-return window is decommissioned (Route B): it arms
  nothing, is non-persisted, is absent after process death and is absent from the
  runtime/store object graph, and a genuine live local return mints no trusted row;
* verifier-less / anonymous interrupted dispatches stay strictly ``in_doubt``;
* legacy keyed-authenticator migration is verify-before-convert and atomic: any
  unauthenticated, inconsistent, transplanted or malformed legacy record fails
  closed with no partial rewrite and no secret purge;
* the frozen Window 16/17 positive properties (Route-B truthfulness, verifier
  substitution fail-closed, exactly-once effects, race first-writer, real process
  loss recovery) remain intact.
"""

from __future__ import annotations

import collections
import hashlib
import hmac
import inspect
import multiprocessing
import os
import signal
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    BackgroundModelAttemptBlocked,
    BackgroundModelExecutionInDoubt,
    BackgroundModelResponseConflict,
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
    TurnExecutionInDoubt,
)
from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptStore,
    LegacyTrustMigrationError,
    decode_model_directive,
    encode_model_directive,
)
from aios_core.runtime.late_return import (
    LateReturnSigningContext,
    LateReturnVerifier,
    late_return_message,
)
from aios_core.runtime.live_return import (
    LiveProviderReturnWindow,
    LiveReturnAuthorityError,
    live_return_authority_snapshot,
    open_live_provider_return_window,
    register_handler_return,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 10, 3, 9, 0, tzinfo=timezone.utc)
TURN_INPUT = "corrective-002 adversarial matrix input"

_RSA_E = 65537
_RSA_N = int(
    "88e3b1105b0c593e52f0ef365db4d6c0d93f6d53d59b361c0dd3a8539a343734"
    "d3b782c1dff188225d3308fbb514f6790b9175431f18bed22773bb5b0d14a220"
    "c8756976babd2ea0cf6335267151735378d1a6062376a28d1f5a65dcfb16404d"
    "eb9680397abc70c1393456adf8ce0e16fcc661236aee7f9fe0aefc651d60fb11"
    "d787ee0f512b21bc88c1975c9812d0bbb415e2956ed267c961b1bfad451f2378"
    "738c323626e0461a319ca3c0ab8d21cb535905d1eb0a2ba55595974bf1ae96dc"
    "1e0424dca706714c890b27aae6492720d90841e76a2825610bc027f676b73981"
    "8fa5e762fcfba20d1606bd172e8bf4842a6d5007b7d0e0f519cd2366c13153f5",
    16,
)
_RSA_D = int(
    "4f65a141974da6459bdddb2171607e5f04a2e14a8acea7a7c5ed49e893bc4d78"
    "fa83a9f7c1685a49743d31acacef27b6359b7ca41dd94074ac25583a0b703849"
    "437bb65c031bcf7bbe4e1079e7a812780bcfadb849c179aed8cc99e07e51fda2"
    "344eeab86c13f8625a479d2ef2ecb1076c3db401d2f7da5664ff99ad1c492fd5"
    "de8b9b604849dc3e3eeaf84939f171cc95c73a7ecf05479c722f1037ee1e029e"
    "f2bffec168a14e2e3b344c3cb0d0f210c2619eb39fc4a43c2b10046b1b59f5dc"
    "4eff617acc02628c7a1433d2e37486a6d8a51a21d8713da54a866c57fb2320d4"
    "1b7e3e5347f3cb83e6df0514314dc9adc34ba4618fd67db8e717f061016ec651",
    16,
)
_SHA256_DER = bytes.fromhex("3031300d060960864801650304020105000420")

TRUST_TABLES = (
    "background_model_response_receipts",
    "background_model_return_handoffs",
    "background_model_responses",
)


class SimulatedProcessLoss(BaseException):
    """Stands in for a SIGKILL that happens after the dispatch boundary."""


class ExternalSigner:
    """Stands in for the trusted external side; keeps the private key outside Core."""

    def __init__(self) -> None:
        self.contexts: dict[str, LateReturnSigningContext] = {}

    def accept_return_context(self, snapshot, context) -> None:
        self.contexts[context.attempt_id] = context

    def sign(self, attempt_id: str, directive: ModelDirective, **overrides) -> str:
        context = self.contexts[attempt_id]
        payload = encode_model_directive(directive)
        fields: dict[str, object] = {
            **context.scope_fields(),
            "provider": directive.provenance.provider,
            "model": directive.provenance.model,
            "provider_request_id": directive.provenance.request_id,
            "response_fingerprint": BackgroundModelAttemptStore._response_fingerprint(
                directive
            ),
            "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        }
        fields.update(overrides)
        return rsa_sign(
            late_return_message(**fields), context.verifier_key_id
        )


def make_verifier(key_id: str = "ca2-external-key") -> LateReturnVerifier:
    return LateReturnVerifier(
        key_id=key_id,
        algorithm="rsa-pkcs1v15-sha256",
        modulus_hex=f"{_RSA_N:x}",
        public_exponent=_RSA_E,
    )


def rsa_sign(message: bytes, key_id: str) -> str:
    digest_info = _SHA256_DER + hashlib.sha256(message).digest()
    size = (_RSA_N.bit_length() + 7) // 8
    encoded = (
        b"\x00\x01"
        + (b"\xff" * (size - len(digest_info) - 3))
        + b"\x00"
        + digest_info
    )
    signature = pow(int.from_bytes(encoded, "big"), _RSA_D, _RSA_N)
    return (
        f"bglate_rsa_v1:{key_id}:"
        + signature.to_bytes(size, "big").hex()
    )


def make_directive(
    *,
    response: str = "genuine external response",
    provider: str = "provider-ca2",
    model: str = "model-ca2",
    request_id: str = "request-ca2",
) -> ModelDirective:
    return ModelDirective(
        response=response,
        usage=ModelUsage(
            input_tokens=4,
            output_tokens=6,
            total_tokens=10,
            provider=provider,
            model=model,
            request_id=request_id,
        ),
        provenance=ModelCallProvenance(
            provider=provider, model=model, request_id=request_id
        ),
    )


def open_world(db: Path) -> tuple[SQLiteWorldStore, WorldSearchIndex]:
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def dispatch_and_crash(
    db: Path,
    *,
    session_id: str,
    verifier: LateReturnVerifier | None = None,
    signer: ExternalSigner | None = None,
):
    store, index = open_world(db)

    def crashing_handler(_snapshot):
        raise SimulatedProcessLoss("simulated process death after mark_dispatching")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=crashing_handler,
        subject_id="user_1",
        late_return_verifier=verifier,
        external_return_observer=signer,
    )
    try:
        runtime.run_turn(
            session_id=session_id, turn_index=1, user_input=TURN_INPUT, occurred_at=NOW
        )
    except SimulatedProcessLoss:
        pass
    execution_id = runtime.turn_executions.execution_id_for(
        subject_id="user_1", session_id=session_id, turn_index=1
    )
    attempt = runtime.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind="user_turn", work_id=execution_id
    )[-1]
    return runtime, attempt


def fresh_recovery_runtime(
    db: Path, *, verifier: LateReturnVerifier | None = None
) -> FusedTurnRuntime:
    store, index = open_world(db)

    def forbidden_provider(_snapshot):
        raise AssertionError("provider redispatch is forbidden during recovery")

    return FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=forbidden_provider,
        subject_id="user_1",
        late_return_verifier=verifier,
    )


def move_to_in_doubt(runtime: FusedTurnRuntime, attempt) -> None:
    try:
        runtime.background_model_attempts.admit(
            subject_id=attempt.subject_id,
            work_kind=attempt.work_kind,
            work_id=attempt.work_id,
            wake_reason=attempt.wake_reason,
            model_round_index=attempt.model_round_index,
            world_revision=int(runtime.store.current_world_revision()),
            admitted_at=NOW + timedelta(seconds=1),
        )
    except BackgroundModelExecutionInDoubt:
        pass


def trust_rows(db: Path) -> tuple[int, int, int]:
    with sqlite3.connect(db) as conn:
        return tuple(
            conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in TRUST_TABLES
        )


def raw_runtime_bytes(db: Path) -> bytes:
    pieces = [db.read_bytes()]
    for suffix in ("-wal", "-shm"):
        candidate = db.with_name(db.name + suffix)
        if candidate.exists():
            pieces.append(candidate.read_bytes())
    return b"".join(pieces)


# ===========================================================================
# CA2-001 / CA2-002 — recovery object graph and direct mint attacks
# ===========================================================================
_FORBIDDEN_NAMES = (
    "_capture_trusted_response_return",
    "_authenticate_background_model_response",
    "_issue_external_return_capability",
    "late_return_proof",
    "_authority_key",
)
_MINTISH = ("receipt", "handoff", "trusted", "return", "capture", "stage", "proof")
# Pydantic 2.11+ warns on instance access to these; they hold no trust state.
_PYDANTIC_INTERNALS = frozenset({"model_fields", "model_computed_fields"})


def _reachable(root, *, max_depth: int = 3):
    seen: set[int] = set()
    queue: collections.deque = collections.deque([("runtime", root, 0)])
    found: list[tuple[str, object]] = []
    while queue:
        path, obj, depth = queue.popleft()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        try:
            names = dir(obj)
        except Exception:  # pragma: no cover - defensive
            continue
        for name in names:
            if name.startswith("__") and name.endswith("__"):
                continue
            if name in _PYDANTIC_INTERNALS:
                continue
            try:
                value = getattr(obj, name)
            except Exception:
                continue
            found.append((f"{path}.{name}", value))
            if (
                depth < max_depth
                and not inspect.ismodule(value)
                and hasattr(value, "__dict__")
            ):
                queue.append((f"{path}.{name}", value, depth + 1))
    return found


def test_ca2_001_recovery_object_graph_exposes_no_trust_mint_api(tmp_path):
    db = tmp_path / "ca2-001.sqlite"
    signer = ExternalSigner()
    _, attempt = dispatch_and_crash(
        db, session_id="ca2-001", verifier=make_verifier(), signer=signer
    )
    recovery = fresh_recovery_runtime(db)
    move_to_in_doubt(recovery, attempt)

    reachable = _reachable(recovery)
    names = {path.rsplit(".", 1)[-1] for path, _ in reachable}
    exposed = sorted(set(names) & set(_FORBIDDEN_NAMES))
    assert exposed == [], f"trust-minting names reachable: {exposed}"

    # And the store no longer offers any standalone mint writer at all.
    assert not hasattr(
        recovery.background_model_attempts, "_capture_trusted_response_return"
    )
    assert not hasattr(recovery, "_authenticate_background_model_response")

    # Mechanical sweep: every reachable callable whose name suggests trust state
    # is invoked with attacker-controlled arguments; the trust tables must stay
    # empty throughout.
    forged = make_directive(
        response="FORGED_BY_RECOVERY_OBJECT_GRAPH",
        provider="forged-provider",
        model="forged-model",
        request_id="forged-request",
    )
    payload = encode_model_directive(forged)
    before = trust_rows(db)
    candidates = [
        (path, value)
        for path, value in reachable
        if callable(value)
        and not inspect.isclass(value)
        and any(token in path.rsplit(".", 1)[-1].lower() for token in _MINTISH)
    ]
    assert candidates, "the sweep must actually find trust-suggesting callables"
    argument_sets = (
        (attempt.attempt_id,),
        (attempt.attempt_id, forged),
        (attempt.attempt_id, NOW),
        (),
        ("subject-f",),
        (payload,),
        ("bglate_rsa_v1:ca2-external-key:" + "00" * 256,),
    )
    for _path, value in candidates:
        for arguments in argument_sets:
            try:
                value(*arguments)
            except BaseException:
                continue
        assert trust_rows(db) == before, (
            "a reachable recovery callable created trusted trust state"
        )
    assert trust_rows(db) == (0, 0, 0)


def test_ca2_002_direct_mint_attempts_fail_closed(tmp_path):
    """Route B: no local mint writer exists, so every direct mint attempt fails closed.

    TIGHTEN_ONLY history (Corrective-003 / Window 22-RERUN-001).

    Old expectation: the five numbered cases below asserted that
    ``record_live_provider_return`` and ``LiveProviderReturnWindow._issue`` refused
    with ``LiveReturnAuthorityError`` when handed no window, a fabricated window, a
    closed window, another thread's window, or bytes the handler did not return.
    Those refusals were the *only* thing standing between a recovery caller and a
    durable trusted receipt.

    Old authority mechanism: the ephemeral live provider-return window
    (``open_live_provider_return_window`` + ``register_handler_return`` +
    ``record_live_provider_return``).

    Why unsafe (BLK-W20-001):
    ``RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW``,
    root cause ``TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE`` -- window
    issuance was itself an ordinary public function, so the caller could simply issue
    its own window and satisfy every one of those refusals legitimately.

    Replacement route / equal-or-stronger: Route B removes the writer and the issuance
    classmethod entirely.  Each case is now asserted *structurally* (the attribute does
    not exist on the instance or on the class, so ``__globals__`` reflection over the
    store class exposes no live-return symbol) rather than behaviourally (a refusal that
    a self-issued window could bypass).  Structural absence is strictly stronger than a
    bypassable refusal.  Case 5 is strengthened from "bytes the handler did not return
    are refused" to "no self-asserted bytes are accepted at all, whether or not the
    handler returned them", and the file still asserts that zero trusted rows are
    created and that the verifier-less attempt stays ``in_doubt``.
    """

    db = tmp_path / "ca2-002.sqlite"
    signer = ExternalSigner()
    _, attempt = dispatch_and_crash(
        db, session_id="ca2-002", verifier=make_verifier(), signer=signer
    )
    recovery = fresh_recovery_runtime(db)
    move_to_in_doubt(recovery, attempt)
    attempts_store = recovery.background_model_attempts
    forged = make_directive(response="FORGED_DIRECT_MINT")
    before = trust_rows(db)

    # 1. The historical recovery-reachable private helper does not exist.
    with pytest.raises(AttributeError):
        attempts_store._capture_trusted_response_return(  # type: ignore[attr-defined]
            attempt.attempt_id, captured_at=NOW, directive=forged
        )

    # 2. Route B: the Corrective-002 public live writer does not exist either --
    #    neither on the instance nor on the class, so reflecting over
    #    ``type(store).__dict__`` or over any store method's ``__globals__`` yields
    #    no live-return writer to call.
    for target in (attempts_store, type(attempts_store)):
        assert not hasattr(target, "record_live_provider_return")
        assert not hasattr(target, "_capture_trusted_response_return")
    with pytest.raises(AttributeError):
        attempts_store.record_live_provider_return(  # type: ignore[attr-defined]
            attempt.attempt_id,
            captured_at=NOW,
            directive=forged,
            live_window=None,
        )
    assert not hasattr(LiveProviderReturnWindow, "_issue")
    with pytest.raises(AttributeError):
        LiveProviderReturnWindow._issue(  # type: ignore[attr-defined]
            sentinel=object(),
            attempt_id=attempt.attempt_id,
            window_id="forged-window",
            seal=b"0" * 32,
        )
    # ``object.__new__`` fabrication yields an inert marker that no Core code reads.
    fabricated = object.__new__(LiveProviderReturnWindow)
    object.__setattr__(fabricated, "_attempt_id", attempt.attempt_id)
    object.__setattr__(fabricated, "_window_id", "forged-window")
    object.__setattr__(fabricated, "_seal", b"0" * 32)
    object.__setattr__(fabricated, "_state", "open")
    assert isinstance(fabricated, LiveProviderReturnWindow)
    with pytest.raises(AttributeError):
        attempts_store.record_live_provider_return(  # type: ignore[attr-defined]
            attempt.attempt_id,
            captured_at=NOW,
            directive=forged,
            live_window=fabricated,
        )
    with pytest.raises(TypeError):
        LiveProviderReturnWindow()

    # 3. A legitimately opened window arms nothing at all, and stays inert after the
    #    frame that opened it returns.
    with open_live_provider_return_window(attempt_id=attempt.attempt_id) as window:
        register_handler_return(window, forged)
        armed = live_return_authority_snapshot()
        assert armed["trust_conferred"] is False
        assert armed["armed_on_this_stack"] is False
        assert armed["decommissioned"] is True
    after_frame = live_return_authority_snapshot()
    assert after_frame["open_windows"] == 0
    assert after_frame["pending_handler_returns"] == 0
    assert after_frame["inert_marker_on_this_stack"] is False
    with pytest.raises(AttributeError):
        attempts_store.record_live_provider_return(  # type: ignore[attr-defined]
            attempt.attempt_id,
            captured_at=NOW,
            directive=forged,
            live_window=window,
        )

    # 4. A window armed on another call stack (thread) carries no authority either.
    leaked: dict[str, object] = {}

    def worker() -> None:
        with open_live_provider_return_window(
            attempt_id=attempt.attempt_id
        ) as other:
            leaked["window"] = other
            register_handler_return(other, forged)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    assert isinstance(leaked["window"], LiveProviderReturnWindow)
    with pytest.raises(AttributeError):
        attempts_store.record_live_provider_return(  # type: ignore[attr-defined]
            attempt.attempt_id,
            captured_at=NOW,
            directive=forged,
            live_window=leaked["window"],
        )

    # 5. Route B strengthening: "the in-process handler returned exactly these bytes"
    #    can never be self-asserted, so nothing is accepted inside a live window --
    #    not different bytes, and not the very bytes the window was told about.
    with open_live_provider_return_window(attempt_id=attempt.attempt_id) as window:
        register_handler_return(window, forged)
        for candidate in (forged, make_directive(response="DIFFERENT_OBJECT")):
            with pytest.raises(AttributeError):
                attempts_store.record_live_provider_return(  # type: ignore[attr-defined]
                    attempt.attempt_id,
                    captured_at=NOW,
                    directive=candidate,
                    live_window=window,
                )
        # The only remaining route is genuine external proof, and a bogus signature
        # over the durable bound verifier is refused.
        with pytest.raises(BackgroundModelResponseConflict):
            attempts_store.attach_late_trusted_return(
                attempt.attempt_id,
                attached_at=NOW + timedelta(seconds=1),
                directive_payload=encode_model_directive(forged),
                late_return_proof="bglate_rsa_v1:ca2-external-key:" + "00" * 256,
                evidence="forged signature must never mint trusted state",
            )

    assert trust_rows(db) == before == (0, 0, 0)
    assert recovery.background_model_attempts.get(attempt.attempt_id).state == "in_doubt"


def test_ca2_003_verifier_less_forged_recovery_stays_in_doubt(tmp_path):
    db = tmp_path / "ca2-003.sqlite"
    _, attempt = dispatch_and_crash(db, session_id="ca2-003", verifier=None)
    recovery = fresh_recovery_runtime(db)
    move_to_in_doubt(recovery, attempt)

    assert (
        recovery.background_model_attempts.late_return_verifier(attempt.attempt_id)
        is None
    )
    forged = make_directive(response="FORGED_ON_ANONYMOUS_DISPATCH")
    with pytest.raises((AttributeError, LiveReturnAuthorityError)):
        recovery.background_model_attempts.record_live_provider_return(
            attempt.attempt_id,
            captured_at=NOW + timedelta(seconds=5),
            directive=forged,
            live_window=None,  # type: ignore[arg-type]
        )
    with pytest.raises(BackgroundModelResponseConflict):
        recovery.background_model_attempts.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(seconds=6),
            directive_payload=encode_model_directive(forged),
            late_return_proof="bglate_rsa_v1:ca2-external-key:" + "00" * 256,
            evidence="anonymous forged recovery",
        )
    with pytest.raises(
        (
            BackgroundModelResponseConflict,
            BackgroundModelExecutionInDoubt,
            BackgroundModelAttemptBlocked,
            TurnExecutionInDoubt,
        )
    ):
        recovery.run_turn(
            session_id="ca2-003", turn_index=1, user_input=TURN_INPUT, occurred_at=NOW
        )
    final = recovery.background_model_attempts.get(attempt.attempt_id)
    assert final is not None and final.state == "in_doubt"
    assert trust_rows(db) == (0, 0, 0)
    assert (
        recovery.metering.list_model_calls(
            subject_id="user_1", execution_classes=("user_interaction",)
        )
        == ()
    )


# ===========================================================================
# CA2-004 — genuine live provider return still works, and is ephemeral
# ===========================================================================
def test_ca2_004_genuine_live_return_captures_and_is_ephemeral(tmp_path):
    """Route B: a genuine live return captures NOTHING and confers no authority.

    TIGHTEN_ONLY history (Corrective-003 / Window 22-RERUN-001).

    Old expectation: after one ordinary live turn, a durable trusted receipt existed
    (``receipt.provider == "provider-ca2"``) together with an exact handoff
    (``trust_rows(db) == (1, 1, 0)`` or ``(1, 1, 1)``), produced by the live
    provider-return window; the test then asserted that this authority was
    stack-scoped and vanished with the frame.

    Old authority mechanism: ``open_live_provider_return_window`` +
    ``register_handler_return`` + ``record_live_provider_return``.

    Why unsafe (BLK-W20-001):
    ``RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW``,
    root cause ``TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE`` -- the
    "ephemeral, stack-scoped, non-persisted" properties this test used to verify were
    all satisfiable by a recovery caller that simply issued its own window, so they
    never established authenticity.

    Replacement route / equal-or-stronger: Route B.  The ephemerality assertions are
    kept in full (no window open, nothing armed, nothing pending, no
    ``LiveProviderReturnWindow`` reachable from the runtime/store object graph, no
    window schema bytes in the raw database) and are now preceded by the strictly
    stronger invariant that a genuine live local return creates ZERO trusted rows:
    no receipt, no handoff, no staged exact response.  A live turn therefore cannot
    make its own bytes recovery-eligible; only a durable external verifier bound
    before dispatch plus a genuine external proof can, which is what CA2-001 and the
    frozen Window 17 / Window 20 reviewer probes exercise.
    """

    db = tmp_path / "ca2-004.sqlite"
    store, index = open_world(db)

    def live_handler(_snapshot):
        return make_directive(response="live provider reply")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=live_handler,
        subject_id="user_1",
    )
    result = runtime.run_turn(
        session_id="ca2-004", turn_index=1, user_input=TURN_INPUT, occurred_at=NOW
    )
    assert result.runtime.response == "live provider reply"

    execution_id = runtime.turn_executions.execution_id_for(
        subject_id="user_1", session_id="ca2-004", turn_index=1
    )
    attempt = runtime.background_model_attempts.list_for_work(
        subject_id="user_1", work_kind="user_turn", work_id=execution_id
    )[-1]

    # Route B: the live local return authenticated itself and minted nothing.
    assert (
        runtime.background_model_attempts.response_authenticity_receipt(
            attempt.attempt_id
        )
        is None
    )
    assert runtime.background_model_attempts.staged_response(attempt.attempt_id) is None
    assert trust_rows(db) == (0, 0, 0)
    # The attempt did complete live, and its durable provenance is the provider
    # identity it reported -- but that provenance carries no authenticity and makes
    # the round permanently not recovery-eligible.
    completed = runtime.background_model_attempts.get(attempt.attempt_id)
    assert completed.state in {"response_returned", "metered"}
    assert completed.provider == "provider-ca2"
    assert completed.provider_request_id == "request-ca2"
    assert (
        runtime.background_model_attempts.late_return_verifier(attempt.attempt_id)
        is None
    )

    # The decommissioned authority is absent everywhere it used to be observable: no
    # window remains open, none is reachable from the recovery graph, and nothing
    # about it is persisted.
    snapshot = live_return_authority_snapshot()
    assert snapshot["open_windows"] == 0
    assert snapshot["armed_on_this_stack"] is False
    assert snapshot["pending_handler_returns"] == 0
    assert snapshot["inert_marker_on_this_stack"] is False
    assert snapshot["trust_conferred"] is False
    assert snapshot["decommissioned"] is True
    reachable = _reachable(runtime)
    assert not any(
        isinstance(value, LiveProviderReturnWindow) for _path, value in reachable
    )
    assert b"aios_live_provider_return_window" not in raw_runtime_bytes(db)

    # Fresh process: the same attempt cannot be minted at all, and no local writer
    # exists to consume.
    restarted = fresh_recovery_runtime(db)
    assert live_return_authority_snapshot()["open_windows"] == 0
    assert (
        restarted.background_model_attempts.late_return_verifier(attempt.attempt_id)
        is None
    )
    assert not hasattr(
        restarted.background_model_attempts, "record_live_provider_return"
    )
    with pytest.raises(AttributeError):
        restarted.background_model_attempts._capture_trusted_response_return(  # type: ignore[attr-defined]
            attempt.attempt_id, captured_at=NOW, directive=make_directive()
        )
    # And a verifier-less attempt can never be given trusted bytes after the fact.
    with pytest.raises(BackgroundModelResponseConflict):
        restarted.background_model_attempts.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(seconds=1),
            directive_payload=encode_model_directive(make_directive()),
            late_return_proof="bglate_rsa_v1:ca2-external-key:" + "00" * 256,
            evidence="no external verifier was ever bound for this attempt",
        )
    assert trust_rows(db) == (0, 0, 0)


# ===========================================================================
# CA2-005 .. CA2-009 — legacy keyed-authenticator migration
# ===========================================================================
def _create_pre_upgrade_db(
    db: Path,
    *,
    session_id: str,
    directive: ModelDirective,
    secret: bytes = b"\x5a" * 32,
    tamper=None,
) -> tuple[str, str, dict[str, object], str]:
    """Build a genuine pre-upgrade DB (legacy HMAC receipt + handoff + staged row)."""

    _, attempt = dispatch_and_crash(db, session_id=session_id, verifier=None)
    store = SQLiteWorldStore(db)
    attempts = BackgroundModelAttemptStore(store)
    binding = attempts.outbound_request_binding(attempt.attempt_id)
    assert binding is not None

    payload = encode_model_directive(directive)
    payload_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    response_fingerprint = BackgroundModelAttemptStore._response_fingerprint(directive)
    provider, model, request_id = BackgroundModelAttemptStore._provider_identity(
        directive
    )
    fields: dict[str, object] = {
        "attempt_id": attempt.attempt_id,
        "subject_id": attempt.subject_id,
        "work_kind": attempt.work_kind,
        "work_id": attempt.work_id,
        "model_round_index": int(attempt.model_round_index),
        "outbound_request_fingerprint": binding.outbound_request_fingerprint,
        "relay_id": binding.relay_id,
        "provider": provider,
        "model": model,
        "provider_request_id": request_id,
        "response_fingerprint": response_fingerprint,
        "payload_sha256": payload_sha256,
    }
    legacy_hmac = "bgresponse_v1_" + hmac.new(
        secret, BackgroundModelAttemptStore._receipt_message(**fields), hashlib.sha256
    ).hexdigest()

    with sqlite3.connect(db) as conn:
        conn.execute(
            """
            CREATE TABLE background_model_authenticity_authority (
                authority_id TEXT PRIMARY KEY,
                secret_hex TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO background_model_authenticity_authority(
                authority_id, secret_hex
            ) VALUES ('trusted-return-v1', ?)
            """,
            (secret.hex(),),
        )
        conn.execute(
            """
            INSERT INTO background_model_response_receipts(
                attempt_id, subject_id, work_kind, work_id, model_round_index,
                outbound_request_fingerprint, relay_id, provider, model,
                provider_request_id, response_fingerprint, payload_sha256,
                authenticity_proof, captured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*fields.values(), legacy_hmac, "2026-10-03T09:00:00Z"),
        )
        conn.execute(
            """
            INSERT INTO background_model_return_handoffs(
                attempt_id, directive_payload, payload_sha256, authenticity_proof
            ) VALUES (?, ?, ?, ?)
            """,
            (attempt.attempt_id, payload, payload_sha256, legacy_hmac),
        )
        if tamper is not None:
            tamper(conn, fields, legacy_hmac, payload)
        conn.commit()
    return attempt.attempt_id, legacy_hmac, fields, payload


def test_ca2_005_valid_legacy_migration_recovers_exactly_once(tmp_path):
    db = tmp_path / "ca2-005.sqlite"
    directive = make_directive(response="valid legacy pre-upgrade reply")
    attempt_id, legacy_hmac, fields, _payload = _create_pre_upgrade_db(
        db, session_id="ca2-005", directive=directive
    )

    recovery = fresh_recovery_runtime(db)
    result = recovery.run_turn(
        session_id="ca2-005", turn_index=1, user_input=TURN_INPUT, occurred_at=NOW
    )
    assert result.runtime.response == "valid legacy pre-upgrade reply"
    attempt = recovery.background_model_attempts.get(attempt_id)
    assert attempt is not None and attempt.state == "metered"

    receipt = recovery.background_model_attempts.response_authenticity_receipt(
        attempt_id
    )
    assert receipt is not None
    assert receipt.authenticity_proof == BackgroundModelAttemptStore._receipt_proof(
        **fields
    )
    assert receipt.authenticity_proof != legacy_hmac
    with sqlite3.connect(db) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert "background_model_authenticity_authority" not in tables
    assert b"5a" * 32 not in raw_runtime_bytes(db)


@pytest.mark.parametrize("tamper_kind", ("invalid_hmac", "wrong_secret"))
def test_ca2_006_invalid_legacy_hmac_fails_closed_atomically(
    tmp_path, tamper_kind
):
    db = tmp_path / f"ca2-006-{tamper_kind}.sqlite"
    directive = make_directive(response=f"legacy {tamper_kind}")

    def tamper(conn, fields, legacy_hmac, payload):
        if tamper_kind == "invalid_hmac":
            broken = "bgresponse_v1_" + ("00" * 32)
            conn.execute(
                "UPDATE background_model_response_receipts SET authenticity_proof=?",
                (broken,),
            )
            conn.execute(
                "UPDATE background_model_return_handoffs SET authenticity_proof=?",
                (broken,),
            )
        else:
            other_key = b"\x11" * 32
            forged = "bgresponse_v1_" + hmac.new(
                other_key,
                BackgroundModelAttemptStore._receipt_message(**fields),
                hashlib.sha256,
            ).hexdigest()
            conn.execute(
                "UPDATE background_model_response_receipts SET authenticity_proof=?",
                (forged,),
            )
            conn.execute(
                "UPDATE background_model_return_handoffs SET authenticity_proof=?",
                (forged,),
            )

    attempt_id, _legacy_hmac, _fields, _payload = _create_pre_upgrade_db(
        db, session_id=f"ca2-006-{tamper_kind}", directive=directive, tamper=tamper
    )
    with pytest.raises(LegacyTrustMigrationError):
        fresh_recovery_runtime(db)
    assert trust_rows(db) == (1, 1, 0)


def test_ca2_007_tampered_legacy_payload_fails_closed(tmp_path):
    db = tmp_path / "ca2-007.sqlite"
    directive = make_directive(response="legacy payload tamper")

    def tamper(conn, fields, legacy_hmac, payload):
        tampered = payload.replace("legacy payload tamper", "TAMPERED PAYLOAD")
        conn.execute(
            "UPDATE background_model_return_handoffs SET directive_payload=?",
            (tampered,),
        )

    _attempt_id, _legacy_hmac, _fields, _payload = _create_pre_upgrade_db(
        db, session_id="ca2-007", directive=directive, tamper=tamper
    )
    with pytest.raises(LegacyTrustMigrationError):
        fresh_recovery_runtime(db)
    assert trust_rows(db) == (1, 1, 0)


@pytest.mark.parametrize(
    "tamper_kind",
    (
        "handoff_proof_mismatch",
        "handoff_digest_mismatch",
        "staged_response_mismatch",
        "receipt_payload_digest_mismatch",
        "cross_attempt_transplant",
        "relay_binding_mismatch",
        "missing_handoff",
        "missing_binding",
    ),
)
def test_ca2_008_legacy_cross_table_inconsistency_fails_closed(
    tmp_path, tamper_kind
):
    db = tmp_path / f"ca2-008-{tamper_kind}.sqlite"
    directive = make_directive(response=f"legacy {tamper_kind}")

    def tamper(conn, fields, legacy_hmac, payload):
        attempt_id = fields["attempt_id"]
        if tamper_kind == "handoff_proof_mismatch":
            conn.execute(
                "UPDATE background_model_return_handoffs "
                "SET authenticity_proof='bgresponse_v1_corrupted'"
            )
        elif tamper_kind == "handoff_digest_mismatch":
            conn.execute(
                "UPDATE background_model_return_handoffs SET payload_sha256=?",
                ("0" * 64,),
            )
        elif tamper_kind == "staged_response_mismatch":
            conn.execute(
                """
                INSERT INTO background_model_responses(
                    attempt_id, provider, model, provider_request_id,
                    response_fingerprint, directive_payload, payload_sha256,
                    authenticity_proof, staged_at, evidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    fields["provider"],
                    fields["model"],
                    fields["provider_request_id"],
                    fields["response_fingerprint"],
                    payload.replace("legacy", "STAGED-MISMATCH"),
                    fields["payload_sha256"],
                    legacy_hmac,
                    "2026-10-03T09:00:01Z",
                    "tampered staged response",
                ),
            )
        elif tamper_kind == "receipt_payload_digest_mismatch":
            # The handoff stays self-consistent, the receipt digest does not.
            conn.execute(
                "UPDATE background_model_response_receipts SET payload_sha256=?",
                ("1" * 64,),
            )
        elif tamper_kind == "cross_attempt_transplant":
            conn.execute(
                "UPDATE background_model_response_receipts SET attempt_id=?",
                ("bgattempt_someone_else",),
            )
        elif tamper_kind == "relay_binding_mismatch":
            conn.execute(
                "UPDATE background_model_request_bindings SET relay_id=?",
                ("relay_bgattack_transplanted000000000000",),
            )
        elif tamper_kind == "missing_handoff":
            conn.execute("DELETE FROM background_model_return_handoffs")
        elif tamper_kind == "missing_binding":
            conn.execute("DELETE FROM background_model_request_bindings")

    _attempt_id, _legacy_hmac, _fields, _payload = _create_pre_upgrade_db(
        db, session_id=f"ca2-008-{tamper_kind}", directive=directive, tamper=tamper
    )
    with pytest.raises((LegacyTrustMigrationError, sqlite3.IntegrityError)):
        fresh_recovery_runtime(db)


def test_ca2_009_failed_migration_leaves_no_partial_v2_state(tmp_path):
    db = tmp_path / "ca2-009.sqlite"
    directive = make_directive(response="legacy rollback case")
    secret = b"\x33" * 32

    def tamper(conn, fields, legacy_hmac, payload):
        conn.execute(
            "UPDATE background_model_return_handoffs SET payload_sha256=?",
            ("9" * 64,),
        )

    attempt_id, legacy_hmac, _fields, _payload = _create_pre_upgrade_db(
        db,
        session_id="ca2-009",
        directive=directive,
        secret=secret,
        tamper=tamper,
    )
    before_receipt = None
    with sqlite3.connect(db) as conn:
        before_receipt = conn.execute(
            "SELECT authenticity_proof FROM background_model_response_receipts"
        ).fetchone()[0]
        before_handoff = conn.execute(
            "SELECT authenticity_proof FROM background_model_return_handoffs"
        ).fetchone()[0]
    assert before_receipt == before_handoff == legacy_hmac

    with pytest.raises(LegacyTrustMigrationError):
        fresh_recovery_runtime(db)

    with sqlite3.connect(db) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        receipt_proof = conn.execute(
            "SELECT authenticity_proof FROM background_model_response_receipts"
        ).fetchone()[0]
        handoff_proof = conn.execute(
            "SELECT authenticity_proof FROM background_model_return_handoffs"
        ).fetchone()[0]
        authority = conn.execute(
            "SELECT authority_id, secret_hex FROM background_model_authenticity_authority"
        ).fetchall()
    assert "background_model_authenticity_authority" in tables
    assert authority == [("trusted-return-v1", secret.hex())]
    assert receipt_proof == handoff_proof == legacy_hmac
    assert not receipt_proof.startswith("bgresponse_v2_")
    assert not handoff_proof.startswith("bgresponse_v2_")

    # A retried startup after the failed migration must still fail closed, and a
    # repaired database must migrate and recover exactly once.
    with pytest.raises(LegacyTrustMigrationError):
        fresh_recovery_runtime(db, verifier=make_verifier())
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE background_model_return_handoffs SET payload_sha256=? WHERE attempt_id=?",
            (
                hashlib.sha256(
                    conn.execute(
                        "SELECT directive_payload FROM background_model_return_handoffs"
                    ).fetchone()[0].encode("utf-8")
                ).hexdigest(),
                attempt_id,
            ),
        )
        conn.commit()
    recovery = fresh_recovery_runtime(db)
    result = recovery.run_turn(
        session_id="ca2-009", turn_index=1, user_input=TURN_INPUT, occurred_at=NOW
    )
    assert result.runtime.response == "legacy rollback case"
    attempt = recovery.background_model_attempts.get(attempt_id)
    assert attempt is not None and attempt.state == "metered"
    meters = recovery.metering.list_model_calls(
        subject_id="user_1", execution_classes=("user_interaction",)
    )
    assert len(meters) == 1


# ===========================================================================
# CA2-014 / CA2-015 — transplant and concurrent consumption
# ===========================================================================
def test_ca2_014_proof_from_another_attempt_cannot_be_attached(tmp_path):
    db_a = tmp_path / "ca2-014-a.sqlite"
    db_b = tmp_path / "ca2-014-b.sqlite"
    signer = ExternalSigner()
    _, attempt_a = dispatch_and_crash(
        db_a, session_id="ca2-014-a", verifier=make_verifier(key_id="key-a"), signer=signer
    )
    _, attempt_b = dispatch_and_crash(
        db_b, session_id="ca2-014-b", verifier=make_verifier(key_id="key-b"), signer=signer
    )
    genuine = make_directive(response="attempt A genuine")
    proof_a = signer.sign(attempt_a.attempt_id, genuine)

    recovery_b = fresh_recovery_runtime(db_b)
    with pytest.raises(BackgroundModelResponseConflict):
        recovery_b.background_model_attempts.attach_late_trusted_return(
            attempt_b.attempt_id,
            attached_at=NOW + timedelta(seconds=10),
            directive_payload=encode_model_directive(genuine),
            late_return_proof=proof_a,
            evidence="cross-attempt transplant",
        )
    assert trust_rows(db_b) == (0, 0, 0)


def test_ca2_015_concurrent_attach_yields_one_canonical_winner(tmp_path):
    db = tmp_path / "ca2-015.sqlite"
    signer = ExternalSigner()
    _, attempt = dispatch_and_crash(
        db, session_id="ca2-015", verifier=make_verifier(), signer=signer
    )
    candidate_a = make_directive(response="race candidate A", request_id="req-A")
    candidate_b = make_directive(response="race candidate B", request_id="req-B")
    proof_a = signer.sign(attempt.attempt_id, candidate_a)
    proof_b = signer.sign(attempt.attempt_id, candidate_b)

    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def worker(directive, proof):
        runtime = fresh_recovery_runtime(db)
        barrier.wait()
        try:
            runtime.background_model_attempts.attach_late_trusted_return(
                attempt.attempt_id,
                attached_at=NOW + timedelta(seconds=20),
                directive_payload=encode_model_directive(directive),
                late_return_proof=proof,
                evidence="concurrent attach",
            )
            with lock:
                outcomes.append("accepted")
        except BackgroundModelResponseConflict:
            with lock:
                outcomes.append("refused")

    threads = [
        threading.Thread(target=worker, args=(candidate_a, proof_a)),
        threading.Thread(target=worker, args=(candidate_b, proof_b)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["accepted", "refused"]
    assert trust_rows(db) == (1, 1, 1)
    with sqlite3.connect(db) as conn:
        payoffs = conn.execute(
            "SELECT count(*) FROM background_model_response_receipts"
        ).fetchone()[0]
        consumed = conn.execute(
            "SELECT consumed_at FROM background_model_return_verifiers "
            "WHERE attempt_id=?",
            (attempt.attempt_id,),
        ).fetchone()[0]
    assert payoffs == 1
    assert consumed is not None


# ===========================================================================
# Real process loss: the live authority does not survive it
# ===========================================================================
def _sigkill_child(db_str: str, pipe) -> None:
    db = Path(db_str)
    store, index = open_world(db)

    class PipeSigner:
        def accept_return_context(self, _snapshot, context) -> None:
            pipe.send(context.model_dump(mode="json"))
            pipe.close()

    def kill_self(_snapshot):
        os.kill(os.getpid(), signal.SIGKILL)
        raise RuntimeError("unreachable")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=kill_self,
        subject_id="user_1",
        late_return_verifier=make_verifier(),
        external_return_observer=PipeSigner(),
    )
    runtime.run_turn(
        session_id="ca2-sigkill",
        turn_index=1,
        user_input=TURN_INPUT,
        occurred_at=NOW,
    )


def test_ca2_004_real_sigkill_leaves_no_live_authority_in_the_fresh_process(tmp_path):
    db = tmp_path / "ca2-sigkill.sqlite"
    SQLiteWorldStore(db)
    context = multiprocessing.get_context("fork")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_sigkill_child, args=(str(db), child))
    process.start()
    process.join(timeout=60)
    assert process.exitcode == -signal.SIGKILL
    assert parent.poll(30)
    signing_context = LateReturnSigningContext(**parent.recv())

    signer = ExternalSigner()
    signer.contexts[signing_context.attempt_id] = signing_context
    genuine = make_directive(response="recovered after real SIGKILL")
    proof = signer.sign(signing_context.attempt_id, genuine)

    recovery = fresh_recovery_runtime(db)
    snapshot = live_return_authority_snapshot()
    assert snapshot["open_windows"] == 0
    assert snapshot["pending_handler_returns"] == 0

    forged = make_directive(response="FORGED_AFTER_REAL_SIGKILL")
    with pytest.raises(AttributeError):
        recovery.background_model_attempts._capture_trusted_response_return(  # type: ignore[attr-defined]
            signing_context.attempt_id, captured_at=NOW, directive=forged
        )
    assert trust_rows(db) == (0, 0, 0)

    recovery.background_model_attempts.attach_late_trusted_return(
        signing_context.attempt_id,
        attached_at=NOW + timedelta(seconds=30),
        directive_payload=encode_model_directive(genuine),
        late_return_proof=proof,
        evidence="genuine external RSA return after real SIGKILL",
    )
    result = recovery.run_turn(
        session_id="ca2-sigkill",
        turn_index=1,
        user_input=TURN_INPUT,
        occurred_at=NOW,
    )
    assert result.runtime.response == "recovered after real SIGKILL"
    attempt = recovery.background_model_attempts.get(signing_context.attempt_id)
    assert attempt is not None and attempt.state == "metered"
    assert trust_rows(db) == (1, 1, 1)
