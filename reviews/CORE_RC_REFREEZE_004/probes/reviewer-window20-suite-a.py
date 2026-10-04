#!/usr/bin/env python3
"""WINDOW 20 Fresh Independent Acceptance — reviewer-owned adversarial probes.

Task: CORE-BACKGROUND-LATE-TRUSTED-RETURN-001-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE
Reviewed exact candidate: fec30bd1495017bf13f08b0ef5b1e241dfb0e247 (PR #310)
Frozen historical RED anchor: cb8a6b3cdaa697a5ede81cbe9fafc3ac9891e9dd (PR #308)
Canonical W17 review: e4161dd0ad0a2f825461311a1c8c5ff8234a07f8

These probes are authored by the Window 20 reviewer.  They deliberately do NOT
reuse any Window 19 author test, helper or expectation, and they do NOT use any
candidate-side signing helper to produce "attacking" proofs: the only RSA material
used here is the reviewer-owned key generated in the reviewer workspace.

Frozen BEFORE first execution against the candidate (see PROBE_FREEZE_MANIFEST.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import contextvars
import copy
import hashlib
from pathlib import Path
import pickle
import sqlite3
import sys
import tempfile
import threading

from aios_core.query.search import WorldSearchIndex
from aios_core.runtime import (
    BackgroundModelExecutionInDoubt,
    BackgroundModelResponseConflict,
    ExternalReturnObserver,
    LateReturnSigningContext,
    LateReturnVerifier,
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
)
from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptStore,
    encode_model_directive,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
TURN_INPUT = "window20 independent acceptance probe input"

# Reviewer-owned external RSA-2048 public modulus (private half stays in the
# reviewer workspace, `reviewer_w20_key.pem`, SHA-256
# 1d0c0b40fa6f865287c6132fd365f7967e11141bdf93fe73bfc58c030fa53636).
# Generated with `openssl genrsa 2048` inside the reviewer sandbox.
REVIEWER_MODULUS_HEX = (
    "d5adea8a26837ebc4db1815f1553b860045602d65656764198d262907674b454"
    "fd3dc2095d7f0bdc02a281a9e2fd1d33b52f4bf568900afd62d6ffe962e7f1bc"
    "69eae4596fdd9e76ee14b5b92084af432e1102a36981e34a5acdc6808683238b"
    "66ea89fac4712f84520ef0e20c163a8d0a395e978bc15bb0d1ab454d09ecfba3"
    "33e5ef65f693a9c44f910a475ad08bb8855ebe8dc75c168023b58359da08eedf"
    "0d7fad8dbaf2daaa5cf6d8c7bfbcfbe2e20cd962eb5c05ebe00c4d34db9684b3"
    "c9f0bf94c4ece3562c19731eebf66576c93982d9046174138e137dd0dcb3be0b"
    "18e4f7b65acc7757e52727c3c5339876b741e1ae20a557ecc00ee363c5b42087"
)
_SHA256_DER = bytes.fromhex("3031300d060960864801650304020105000420")


class SimulatedCrash(BaseException):
    pass


@dataclass(frozen=True)
class ProbeResult:
    probe_id: str
    expected: str
    actual: str
    passed: bool


def make_verifier(key_id: str = "w20-reviewer-ext-key") -> LateReturnVerifier:
    return LateReturnVerifier(
        key_id=key_id,
        algorithm="rsa-pkcs1v15-sha256",
        modulus_hex=REVIEWER_MODULUS_HEX,
        public_exponent=65537,
    )


def make_directive(
    *,
    response: str,
    provider: str = "provider-W20",
    model: str = "model-W20",
    request_id: str = "req-W20-1",
) -> ModelDirective:
    return ModelDirective(
        response=response,
        capability_calls=(),
        usage=ModelUsage(
            input_tokens=4,
            output_tokens=6,
            total_tokens=10,
            provider=provider,
            model=model,
            request_id=request_id,
        ),
        provenance=ModelCallProvenance(
            provider=provider,
            model=model,
            request_id=request_id,
        ),
    )


class ReviewerObserver:
    """Reviewer-owned external return authority: holds the signing context only."""

    def __init__(self) -> None:
        self.contexts: dict[str, LateReturnSigningContext] = {}

    def accept_return_context(self, snapshot: object, context: LateReturnSigningContext) -> None:
        self.contexts[context.attempt_id] = context


def open_world(db: Path) -> tuple[SQLiteWorldStore, WorldSearchIndex]:
    store = SQLiteWorldStore(db)
    index = WorldSearchIndex(db, store=store)
    index.rebuild()
    return store, index


def dispatch_and_crash(
    db: Path,
    *,
    session_id: str,
    verifier: LateReturnVerifier | None,
    observer: ExternalReturnObserver | None = None,
) -> tuple[FusedTurnRuntime, object]:
    store, index = open_world(db)

    def crashing_handler(_snapshot: object) -> ModelDirective:
        raise SimulatedCrash("simulated process death after durable dispatch boundary")

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=crashing_handler,
        subject_id="user_1",
        late_return_verifier=verifier,
        external_return_observer=observer,
    )
    try:
        runtime.run_turn(
            session_id=session_id,
            turn_index=1,
            user_input=TURN_INPUT,
            occurred_at=NOW,
        )
    except SimulatedCrash:
        pass
    exec_id = runtime.turn_executions.execution_id_for(
        subject_id="user_1",
        session_id=session_id,
        turn_index=1,
    )
    attempt = runtime.background_model_attempts.list_for_work(
        subject_id="user_1",
        work_kind="user_turn",
        work_id=exec_id,
    )[-1]
    return runtime, attempt


def fresh_recovery_runtime(db: Path, *, verifier: LateReturnVerifier | None = None) -> FusedTurnRuntime:
    store, index = open_world(db)

    def forbidden_provider(_snapshot: object) -> ModelDirective:
        raise AssertionError("provider redispatch is forbidden during recovery")

    return FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=forbidden_provider,
        subject_id="user_1",
        late_return_verifier=verifier,
    )


def drive_to_in_doubt(recovery: FusedTurnRuntime, attempt: object) -> object:
    try:
        recovery.background_model_attempts.admit(
            subject_id=attempt.subject_id,
            work_kind=attempt.work_kind,
            work_id=attempt.work_id,
            wake_reason=attempt.wake_reason,
            model_round_index=attempt.model_round_index,
            world_revision=int(recovery.store.current_world_revision()),
            admitted_at=NOW + timedelta(seconds=1),
        )
    except BackgroundModelExecutionInDoubt:
        pass
    return recovery.background_model_attempts.get(attempt.attempt_id)


def read_binding_identity(db: Path, attempt_id: str) -> dict[str, str]:
    """Public/readable Core state: the durable outbound request binding row.

    The binding row persists scope fields only (relay id, outbound request
    fingerprint, work identity); it deliberately does not carry provider/model
    identity.  Attacker-chosen provider/model/request_id below are therefore
    supplied by the probe itself, exactly as the frozen Window 17 IA17-MINT-001
    attack did.
    """
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM background_model_request_bindings WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()
    if row is None:
        raise AssertionError("expected a durable request binding row")
    return {k: row[k] for k in row.keys()}


def forged_identity() -> dict[str, str]:
    return {
        "provider": "forged-provider-w20",
        "model": "forged-model-w20",
        "request_id": "forged-req-w20",
    }


def store_state(db: Path, attempt_id: str) -> tuple[str, int, int, int]:
    with sqlite3.connect(db) as conn:
        state = conn.execute(
            "SELECT state FROM background_model_attempts WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()[0]
        receipts = conn.execute(
            "SELECT COUNT(*) FROM background_model_response_receipts WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()[0]
        handoffs = conn.execute(
            "SELECT COUNT(*) FROM background_model_return_handoffs WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()[0]
        responses = conn.execute(
            "SELECT COUNT(*) FROM background_model_responses WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()[0]
    return state, receipts, handoffs, responses


def meters_for(recovery: FusedTurnRuntime) -> int:
    return len(
        recovery.metering.list_model_calls(
            subject_id="user_1", execution_classes=("user_interaction",)
        )
    )


# ---------------------------------------------------------------------------
# IA20-MINT-003 — public-API ephemeral-window forgery (CRITICAL)
# ---------------------------------------------------------------------------
def probe_ia20_mint_003_public_window_api_forge(root: Path) -> ProbeResult:
    """A caller that is NOT inside a genuine live provider frame must not mint.

    Attack: an ordinary post-crash recovery caller (no RSA key, no live provider
    call) uses the *public, exported* issuance helpers of the new ephemeral
    authority to satisfy every precondition of
    ``BackgroundModelAttemptStore.record_live_provider_return`` and completes the
    in_doubt turn with attacker-authored bytes.
    """
    from aios_core.runtime.live_return import (
        open_live_provider_return_window,
        register_handler_return,
    )

    db = root / "ia20-mint-003.sqlite"
    observer = ReviewerObserver()
    _, attempt = dispatch_and_crash(
        db, session_id="sess-mint-003", verifier=make_verifier(), observer=observer
    )
    recovery = fresh_recovery_runtime(db)
    in_doubt = drive_to_in_doubt(recovery, attempt)
    assert in_doubt is not None and in_doubt.state == "in_doubt"

    identity = forged_identity()
    forged = make_directive(
        response="FORGED_VIA_PUBLIC_LIVE_WINDOW_API_NO_PROVIDER_CALL",
        provider=identity["provider"],
        model=identity["model"],
        request_id=identity["request_id"],
    )

    minted = False
    completed_response: object = None
    try:
        with open_live_provider_return_window(attempt_id=attempt.attempt_id) as window:
            register_handler_return(window, forged)
            recovery.background_model_attempts.record_live_provider_return(
                attempt.attempt_id,
                captured_at=NOW + timedelta(seconds=10),
                directive=forged,
                live_window=window,
            )
            minted = True
        completed = recovery.run_turn(
            session_id="sess-mint-003",
            turn_index=1,
            user_input=TURN_INPUT,
            occurred_at=NOW,
        )
        completed_response = completed.runtime.response
    except BaseException as exc:  # noqa: BLE001 - probe records the refusal
        if not minted:
            return ProbeResult(
                "IA20-MINT-003",
                "caller outside the genuine live provider frame cannot mint receipt/handoff nor complete the in_doubt turn",
                f"refused before mint: {type(exc).__name__}: {exc}",
                True,
            )

    state, receipts, handoffs, responses = store_state(db, attempt.attempt_id)
    meters = meters_for(recovery)

    # Genuine external RSA return (reviewer authority) must still be able to win.
    genuine_poisoned = False
    try:
        recovery.background_model_attempts.attach_late_trusted_return(
            attempt.attempt_id,
            attached_at=NOW + timedelta(seconds=30),
            directive_payload=encode_model_directive(make_directive(response="genuine")),
            late_return_proof="bglate_rsa_v1:w20-reviewer-ext-key:" + "00" * 256,
            evidence="genuine external signer return after forged capture",
        )
    except BackgroundModelResponseConflict:
        genuine_poisoned = True
    except BaseException:
        pass

    forged_visible = minted and receipts >= 1 and handoffs >= 1
    return ProbeResult(
        "IA20-MINT-003",
        "caller outside the genuine live provider frame cannot mint receipt/handoff nor complete the in_doubt turn",
        (
            f"FORGED MINT VIA PUBLIC LIVE-WINDOW API: minted={minted}, "
            f"state={state}, receipts={receipts}, handoffs={handoffs}, responses={responses}, "
            f"meters={meters}, turn_response={completed_response!r}, "
            f"genuine_rsa_return_conflicted={genuine_poisoned}"
        ),
        not forged_visible,
    )


# ---------------------------------------------------------------------------
# IA20-MINT-004 — verifier-less attempt must stay permanently in_doubt (CRITICAL)
# ---------------------------------------------------------------------------
def probe_ia20_mint_004_verifierless_forge(root: Path) -> ProbeResult:
    """Attempt dispatched with late_return_verifier=None must never complete (T6/C8)."""
    from aios_core.runtime.live_return import (
        open_live_provider_return_window,
        register_handler_return,
    )

    db = root / "ia20-mint-004.sqlite"
    _, attempt = dispatch_and_crash(db, session_id="sess-mint-004", verifier=None)
    recovery = fresh_recovery_runtime(db)
    in_doubt = drive_to_in_doubt(recovery, attempt)
    assert in_doubt is not None and in_doubt.state == "in_doubt"
    with sqlite3.connect(db) as conn:
        bound_verifier_rows = conn.execute(
            "SELECT COUNT(*) FROM background_model_return_verifiers WHERE attempt_id=?",
            (attempt.attempt_id,),
        ).fetchone()[0]
    assert bound_verifier_rows == 0, (
        f"expected anonymous (no-verifier) dispatch, found {bound_verifier_rows} verifier rows"
    )

    identity = forged_identity()
    forged = make_directive(
        response="FORGED_ON_VERIFIERLESS_ATTEMPT_VIA_PUBLIC_WINDOW",
        provider=identity["provider"],
        model=identity["model"],
        request_id=identity["request_id"],
    )

    completed_response: object = None
    refused: str | None = None
    try:
        with open_live_provider_return_window(attempt_id=attempt.attempt_id) as window:
            register_handler_return(window, forged)
            recovery.background_model_attempts.record_live_provider_return(
                attempt.attempt_id,
                captured_at=NOW + timedelta(seconds=10),
                directive=forged,
                live_window=window,
            )
        completed = recovery.run_turn(
            session_id="sess-mint-004",
            turn_index=1,
            user_input=TURN_INPUT,
            occurred_at=NOW,
        )
        completed_response = completed.runtime.response
    except BaseException as exc:  # noqa: BLE001
        refused = f"{type(exc).__name__}: {exc}"

    state, receipts, handoffs, responses = store_state(db, attempt.attempt_id)
    meters = meters_for(recovery)
    honest = (
        state == "in_doubt"
        and receipts == 0
        and handoffs == 0
        and responses == 0
        and meters == 0
    )
    return ProbeResult(
        "IA20-MINT-004",
        "anonymous / no-verifier attempt remains permanently in_doubt FAIL_CLOSED (no receipt, no handoff, no meter, no completion)",
        (
            f"state={state}, receipts={receipts}, handoffs={handoffs}, responses={responses}, "
            f"meters={meters}, turn_response={completed_response!r}, refusal={refused}"
        ),
        honest,
    )


# ---------------------------------------------------------------------------
# IA20-OBJGRAPH-002 — recovery object graph -> mint authority (CRITICAL)
# ---------------------------------------------------------------------------
def probe_ia20_objgraph_002_reflection_reachability(root: Path) -> ProbeResult:
    """Reflection-only walk (no `import aios_core.runtime.live_return` statement).

    Starting from the post-crash recovery runtime object, follow only attribute
    access (`type(store).record_live_provider_return.__globals__` and
    `LiveProviderReturnWindow._issue.__func__.__globals__`) and try to re-derive a
    usable minting authority.  This is the W17 `IA17-OBJGRAPH-001` framing
    ("reachable from the recovery object graph") applied to the new design.
    """
    db = root / "ia20-objgraph-002.sqlite"
    observer = ReviewerObserver()
    _, attempt = dispatch_and_crash(
        db, session_id="sess-objgraph-002", verifier=make_verifier(), observer=observer
    )
    recovery = fresh_recovery_runtime(db)
    in_doubt = drive_to_in_doubt(recovery, attempt)
    assert in_doubt is not None and in_doubt.state == "in_doubt"

    reached: list[str] = []
    minted = False
    detail = ""
    try:
        store = recovery.background_model_attempts
        writer = type(store).record_live_provider_return
        bg_globals = writer.__globals__
        reached.append("store.__class__.record_live_provider_return.__globals__")
        window_cls = bg_globals["LiveProviderReturnWindow"]
        live_globals = window_cls._issue.__func__.__globals__
        reached.append("LiveProviderReturnWindow._issue.__func__.__globals__")
        sentinel = live_globals["_ISSUE_SENTINEL"]
        open_windows = live_globals["_OPEN_WINDOWS"]
        handler_returns = live_globals["_HANDLER_RETURNS"]
        active_window = live_globals["_ACTIVE_WINDOW"]

        identity = forged_identity()
        forged = make_directive(
            response="FORGED_BY_OBJECT_GRAPH_REFLECTION_ONLY",
            provider=identity["provider"],
            model=identity["model"],
            request_id=identity["request_id"],
        )
        forged_window = window_cls._issue(
            sentinel=sentinel,
            attempt_id=attempt.attempt_id,
            window_id="w20-forged-window",
            seal=b"\x00" * 32,
        )
        open_windows["w20-forged-window"] = forged_window
        handler_returns["w20-forged-window"] = id(forged)
        token = active_window.set(forged_window)
        try:
            store.record_live_provider_return(
                attempt.attempt_id,
                captured_at=NOW + timedelta(seconds=11),
                directive=forged,
                live_window=forged_window,
            )
            minted = True
        finally:
            # Harness isolation only: do not leave the process ContextVar armed
            # for later probes in this process.
            active_window.reset(token)
    except BaseException as exc:  # noqa: BLE001
        detail = f"{type(exc).__name__}: {exc}"

    state, receipts, handoffs, responses = store_state(db, attempt.attempt_id)
    return ProbeResult(
        "IA20-OBJGRAPH-002",
        "recovery object graph yields no reachable callable/state able to mint trusted receipts or handoffs",
        (
            f"reachable_via=[{', '.join(reached)}], minted={minted}, state={state}, "
            f"receipts={receipts}, handoffs={handoffs}, responses={responses}"
            + (f", refusal={detail}" if detail else "")
        ),
        not (minted and receipts >= 1 and handoffs >= 1),
    )


# ---------------------------------------------------------------------------
# IA20-WINDOW-001 — ephemeral-window negative matrix (design properties)
# ---------------------------------------------------------------------------
def probe_ia20_window_001_negative_matrix(root: Path) -> ProbeResult:
    """All non-live-window satisfactions must fail closed.

    Sub-cases (each must be refused):
      a) live_window=None
      b) window bound to a different attempt id
      c) window whose `with` block already exited (closed)
      d) already-consumed window
      e) copy.copy / copy.deepcopy / pickle of a window
      f) window used from a thread where the ContextVar is not armed
      g) window object obtained after process-scoped context (simulated by a copy
         of the runtime DB: same attempt id, different durable world)
    """
    from aios_core.runtime.live_return import (
        open_live_provider_return_window,
        register_handler_return,
    )
    from aios_core.runtime.live_return import LiveProviderReturnWindow

    subcases: dict[str, str] = {}

    def clear_stray_armed_window() -> None:
        """Harness isolation: clear a ContextVar left armed by an earlier probe."""
        from aios_core.runtime.live_return import _ACTIVE_WINDOW as _active

        if _active.get() is not None:
            _active.set(None)

    def fresh_case(name: str) -> tuple[Path, object, FusedTurnRuntime]:
        clear_stray_armed_window()
        db = root / f"ia20-window-001-{name}.sqlite"
        _, attempt = dispatch_and_crash(
            db, session_id=f"sess-window-{name}", verifier=make_verifier()
        )
        recovery = fresh_recovery_runtime(db)
        in_doubt = drive_to_in_doubt(recovery, attempt)
        assert in_doubt is not None and in_doubt.state == "in_doubt"
        return db, attempt, recovery

    def forged_directive(db: Path, attempt_id: str, tag: str) -> ModelDirective:
        identity = forged_identity()
        return make_directive(
            response=f"FORGED_WINDOW_SUBCASE_{tag}",
            provider=identity["provider"],
            model=identity["model"],
            request_id=identity["request_id"],
        )

    def attempt_mint(recovery: FusedTurnRuntime, attempt_id: str, directive: object, window: object) -> str:
        try:
            recovery.background_model_attempts.record_live_provider_return(
                attempt_id,
                captured_at=NOW + timedelta(seconds=5),
                directive=directive,
                live_window=window,
            )
            return "MINTED"
        except BaseException as exc:  # noqa: BLE001
            return f"refused:{type(exc).__name__}"

    # (a) no window
    db, attempt, recovery = fresh_case("a")
    subcases["a_none"] = attempt_mint(
        recovery, attempt.attempt_id, forged_directive(db, attempt.attempt_id, "A"), None
    )

    # (b) wrong attempt id
    db, attempt, recovery = fresh_case("b")
    with open_live_provider_return_window(attempt_id="bgattempt_some_other_attempt") as w:
        register_handler_return(w, forged_directive(db, "bgattempt_some_other_attempt", "B"))
        subcases["b_wrong_attempt"] = attempt_mint(
            recovery, attempt.attempt_id, forged_directive(db, attempt.attempt_id, "B"), w
        )

    # (c) closed window (handle kept after context exit)
    db, attempt, recovery = fresh_case("c")
    directive = forged_directive(db, attempt.attempt_id, "C")
    with open_live_provider_return_window(attempt_id=attempt.attempt_id) as w:
        register_handler_return(w, directive)
    subcases["c_closed"] = attempt_mint(recovery, attempt.attempt_id, directive, w)

    # (d) already-consumed window
    db, attempt, recovery = fresh_case("d")
    directive = forged_directive(db, attempt.attempt_id, "D")
    with open_live_provider_return_window(attempt_id=attempt.attempt_id) as w:
        register_handler_return(w, directive)
        first = attempt_mint(recovery, attempt.attempt_id, directive, w)
        second = attempt_mint(recovery, attempt.attempt_id, directive, w)
    subcases["d_replay"] = f"first={first}, second={second}"

    # (e) copy / deepcopy / pickle
    db, attempt, recovery = fresh_case("e")
    with open_live_provider_return_window(attempt_id=attempt.attempt_id) as w:
        outcomes = []
        for label, fn in (
            ("copy", lambda: copy.copy(w)),
            ("deepcopy", lambda: copy.deepcopy(w)),
            ("pickle", lambda: pickle.dumps(w)),
        ):
            try:
                fn()
                outcomes.append(f"{label}=COPIED")
            except BaseException as exc:  # noqa: BLE001
                outcomes.append(f"{label}=refused:{type(exc).__name__}")
        subcases["e_copy"] = ",".join(outcomes)

    # (f) window used from a thread where the ContextVar is not armed
    db, attempt, recovery = fresh_case("f")
    directive = forged_directive(db, attempt.attempt_id, "F")
    result_holder: dict[str, str] = {}

    def worker(window: object) -> None:
        result_holder["result"] = attempt_mint(recovery, attempt.attempt_id, directive, window)

    with open_live_provider_return_window(attempt_id=attempt.attempt_id) as w:
        register_handler_return(w, directive)
        t = threading.Thread(target=worker, args=(w,))
        t.start()
        t.join()
    subcases["f_other_thread"] = result_holder.get("result", "no-result")
    clear_stray_armed_window()

    # (g) same attempt id, different durable world (cloned DB)
    db, attempt, recovery = fresh_case("g")
    clone = root / "ia20-window-001-g-clone.sqlite"
    with sqlite3.connect(db) as src, sqlite3.connect(clone) as dst:
        src.backup(dst)
    clone_recovery = fresh_recovery_runtime(clone)
    directive = forged_directive(db, attempt.attempt_id, "G")
    with open_live_provider_return_window(attempt_id=attempt.attempt_id) as w:
        register_handler_return(w, directive)
        subcases["g_other_world"] = attempt_mint(
            clone_recovery, attempt.attempt_id, directive, w
        )

    # (h) forged window object with equal-looking public fields (no real issue)
    db, attempt, recovery = fresh_case("h")
    directive = forged_directive(db, attempt.attempt_id, "H")
    try:
        fake = object.__new__(LiveProviderReturnWindow)
        object.__setattr__(fake, "_attempt_id", attempt.attempt_id)
        object.__setattr__(fake, "_window_id", "w20-fake")
        object.__setattr__(fake, "_seal", b"")
        object.__setattr__(fake, "_state", "open")
        subcases["h_unregistered"] = attempt_mint(recovery, attempt.attempt_id, directive, fake)
    except BaseException as exc:  # noqa: BLE001
        subcases["h_unregistered"] = f"construction-refused:{type(exc).__name__}"

    # (i) direct construction via the documented public constructor
    try:
        LiveProviderReturnWindow()
        subcases["i_direct_ctor"] = "CONSTRUCTED"
    except BaseException as exc:  # noqa: BLE001
        subcases["i_direct_ctor"] = f"refused:{type(exc).__name__}"

    # (j) fresh ContextVar context where the window is not armed
    db, attempt, recovery = fresh_case("j")
    directive = forged_directive(db, attempt.attempt_id, "J")
    with open_live_provider_return_window(attempt_id=attempt.attempt_id) as w:
        register_handler_return(w, directive)
        ctx = contextvars.copy_context()
        holder: dict[str, str] = {}

        def detached() -> None:
            holder["result"] = attempt_mint(recovery, attempt.attempt_id, directive, w)

        ctx.run(detached)
        subcases["j_detached_context"] = holder.get("result", "no-result")

    bad = {k: v for k, v in subcases.items() if "MINTED" in v or "COPIED" in v or "CONSTRUCTED" in v}
    return ProbeResult(
        "IA20-WINDOW-001",
        "all non-live-window satisfactions (none/wrong-attempt/closed/consumed/copied/pickle/other-thread/other-world/unregistered/ctor/detached-context) are refused",
        f"subcases={subcases}",
        not bad,
    )


PROBES = (
    probe_ia20_mint_003_public_window_api_forge,
    probe_ia20_mint_004_verifierless_forge,
    probe_ia20_objgraph_002_reflection_reachability,
    probe_ia20_window_001_negative_matrix,
)


def _isolation_reset() -> None:
    """Harness isolation between probes (never affects a probe's verdict)."""
    try:
        from aios_core.runtime.live_return import _ACTIVE_WINDOW as _active

        if _active.get() is not None:
            _active.set(None)
    except BaseException:  # noqa: BLE001
        pass


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory(prefix="w20-ia-probes-") as tmp:
        root = Path(tmp)
        for probe_fn in PROBES:
            _isolation_reset()
            res = probe_fn(root)
            status = "PASS" if res.passed else "FAIL"
            if not res.passed:
                failures += 1
            print(f"{status} | {res.probe_id}")
            print(f"  expected: {res.expected}")
            print(f"  actual:   {res.actual}")
    print(f"SUMMARY | probes={len(PROBES)} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
