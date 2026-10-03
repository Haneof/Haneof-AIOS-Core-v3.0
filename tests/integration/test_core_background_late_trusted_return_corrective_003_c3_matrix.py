"""C3 author attack matrix for Corrective-003 / Route B (27 enumerated cases).

Contract `C3-1` .. `C3-3` require that no caller-manufacturable trust authority
remains.  This file is the AUTHOR matrix demanded by task section 16: it
mechanically enumerates 27 attack cases and, for every one of them, asserts the
same durable *property* rather than a naming fact:

    P1  zero trusted rows exist anywhere in the World
        (``background_model_response_receipts``,
         ``background_model_return_handoffs``,
         ``background_model_responses``);
    P2  the attacked attempt is still ``in_doubt`` and owns no receipt, no
        handoff and no staged exact response;
    P3  the attack either refused with an exception or was inert -- and in the
        inert case it still produced nothing durable.

Case numbering
--------------
``C3-1`` (13 cases, `c1_01` .. `c1_13`) -- each candidate trust root that the
frozen contract declares invalid is used as the attack's trust root:
public function, exported symbol, store method, classmethod, registry,
ContextVar, sentinel, object identity, test secret, underscore naming, stack
naming, docstring, bool flag.

``C3-2`` (13 cases, `c2_01` .. `c2_13`) -- each enumerated reflection path is
used to reach for a mint authority: ``__globals__``, ``sys.modules``,
``__dict__``, bound methods, closure cells, defaults, descriptors,
``object.__new__``, ctor, import, callbacks, exception objects, store/runtime
object graph.

``C3-3`` (1 case, `c3_01`) -- an attempt with NO bound external verifier stays
permanently ``in_doubt`` across a fresh process, against every durable writer.

Design note on why these are property checks
--------------------------------------------
Window 20's ``BLK-W20-001`` was possible precisely because the previous design
satisfied "the writer refuses when the window is forged" while the *issuance*
helper stayed public.  A matrix of "function X is absent" assertions would have
passed on that candidate too.  Every case here therefore drives a real attack
against a real durable World and then asserts on durable state, so a future
re-introduction of ANY local mint route -- under any name, in any module, behind
any guard -- fails this matrix.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import sqlite3
import sys
import types
from datetime import timedelta
from pathlib import Path

import pytest

from aios_core.runtime import background_attempt as background_attempt_module
from aios_core.runtime import cognitive_runtime as cognitive_runtime_module
from aios_core.runtime import late_return as late_return_module
from aios_core.runtime import live_return as live_return_module
from aios_core.runtime import turn_runtime as turn_runtime_module
from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptStore,
    encode_model_directive,
)
from aios_core.runtime.late_return import (
    LATE_RETURN_PROOF_PREFIX,
    LateReturnSigningContext,
    LateReturnVerifier,
    late_return_message,
)
# NOTE: only names that exist on BOTH the Route B candidate and the frozen failed
# candidate are imported at module level, so this matrix COLLECTS and therefore
# genuinely fails (rather than erroring at import) when it is replayed against the
# failed candidate as RED-first evidence.  Route-B-only markers are read with
# getattr and asserted below.
from aios_core.runtime.live_return import (
    LiveProviderReturnWindow,
    live_return_authority_snapshot,
    open_live_provider_return_window,
    register_handler_return,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from test_core_background_late_trusted_return_corrective_002 import (
    NOW,
    TRUST_TABLES,
    ExternalSigner,
    dispatch_and_crash,
    fresh_recovery_runtime,
    make_directive,
    make_verifier,
    move_to_in_doubt,
    open_world,
    trust_rows,
)

#: A *different* external authority than the one durably bound below.  Its key id
#: stands in for "some other test's secret material": under Route B only the
#: verifier that Core itself bound before dispatch can authorize an attempt, so a
#: proof labelled with any other key id must be refused.
FOREIGN_EXTERNAL_KEY_ID = "c3-matrix-foreign-external-key"

CORE_MODULES = (
    live_return_module,
    background_attempt_module,
    cognitive_runtime_module,
    turn_runtime_module,
    late_return_module,
)

#: Names that historically constituted a local mint authority.  Under Route B none
#: of them may exist anywhere in Core, and no reachable ``__globals__`` may hold
#: them.  Used only as a supporting structural scan; the authoritative assertions
#: in every case are the durable properties P1/P2/P3.
FORBIDDEN_MINT_NAMES = frozenset(
    {
        "record_live_provider_return",
        "_capture_trusted_response_return",
        "_authenticate_background_model_response",
        "_issue_external_return_capability",
        "consume_live_provider_return_window",
        "_ISSUE_SENTINEL",
        "_OPEN_WINDOWS",
        "_HANDLER_RETURNS",
        "_live_provider_return_window",
        "model_response_authenticator",
        "ModelResponseAuthenticator",
    }
)


# ---------------------------------------------------------------------------
# shared attack context
# ---------------------------------------------------------------------------
class AttackContext:
    """One durable World with a crashed, verifier-bound, ``in_doubt`` attempt."""

    def __init__(
        self,
        tmp_path: Path,
        *,
        bind_verifier: bool = True,
        force_in_doubt: bool = False,
    ) -> None:
        self.db = tmp_path / "c3-matrix.sqlite"
        self.signer = ExternalSigner()
        _runtime, self.attempt = dispatch_and_crash(
            self.db,
            session_id="c3-matrix",
            verifier=make_verifier() if bind_verifier else None,
            signer=self.signer if bind_verifier else None,
        )
        self.runtime = fresh_recovery_runtime(
            self.db, verifier=make_verifier() if bind_verifier else None
        )
        self.force_in_doubt = force_in_doubt
        if force_in_doubt:
            move_to_in_doubt(self.runtime, self.attempt)
        self.attempts = self.runtime.background_model_attempts
        self.attempt_id = self.attempt.attempt_id
        self.forged = make_directive(response="C3_FORGED_BYTES")
        self.payload = encode_model_directive(self.forged)
        # The attacked attempt sits in exactly the state the frozen BLK-W20-001
        # oracle was able to abuse: durably past the provider boundary, with no
        # provider provenance and no trusted row of any kind.
        self.expected_state = "in_doubt" if force_in_doubt else "dispatching"
        assert self.attempts.get(self.attempt_id).state == self.expected_state
        assert trust_rows(self.db) == (0, 0, 0)

    # -- the durable properties every case must satisfy -------------------
    def assert_properties(self, outcome: str) -> None:
        # P1: no trusted row anywhere in the World.
        assert trust_rows(self.db) == (0, 0, 0), f"attack produced trusted rows ({outcome})"
        # P2: the attacked attempt never left the state it was in and owns nothing
        #     trusted, so caller-supplied bytes are not recovery-eligible.
        attempt = self.attempts.get(self.attempt_id)
        assert attempt.state == self.expected_state, (
            attempt.state, self.expected_state, outcome
        )
        assert attempt.provider is None
        assert attempt.model is None
        assert attempt.provider_request_id is None
        assert attempt.response_fingerprint is None
        assert self.attempts.response_authenticity_receipt(self.attempt_id) is None
        assert self.attempts.staged_response(self.attempt_id) is None
        with sqlite3.connect(self.db) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM background_model_return_handoffs "
                "WHERE attempt_id=?",
                (self.attempt_id,),
            ).fetchone()[0] == 0

    # -- attack helpers ---------------------------------------------------
    def attach(self, proof: str, *, directive=None, evidence="C3 matrix attack"):
        return self.attempts.attach_late_trusted_return(
            self.attempt_id,
            attached_at=NOW + timedelta(seconds=5),
            directive_payload=encode_model_directive(directive or self.forged),
            late_return_proof=proof,
            evidence=evidence,
        )

    def bogus_proof(self, key_id: str = "ca2-external-key") -> str:
        return f"{LATE_RETURN_PROOF_PREFIX}{key_id}:" + "00" * 256

    def stage(self, **overrides):
        arguments = {
            "staged_at": NOW + timedelta(seconds=5),
            "provider": self.forged.provenance.provider,
            "model": self.forged.provenance.model,
            "provider_request_id": self.forged.provenance.request_id,
            "response_fingerprint": BackgroundModelAttemptStore._response_fingerprint(
                self.forged
            ),
            "directive_payload": self.payload,
            "evidence": "C3 matrix attack",
        }
        arguments.update(overrides)
        return self.attempts.stage_exact_response(self.attempt_id, **arguments)

    def record_response(self):
        return self.attempts.record_response(
            self.attempt_id, returned_at=NOW + timedelta(seconds=5),
            directive=self.forged,
        )

    def signing_context(self) -> LateReturnSigningContext:
        context = self.attempts.late_return_signing_context(self.attempt_id)
        assert context is not None
        return context


def _attack_outcome(fn) -> str:
    """Drive one attack; Core refusals are data, matrix violations are failures.

    Core refuses a mint with ``AttributeError`` / ``TypeError`` /
    ``BackgroundModelResponseConflict`` / ``LiveReturnAuthorityError`` and similar;
    any of those is a *successful* defence and is recorded as the case outcome.  An
    ``AssertionError`` is different: it is this matrix detecting that a forbidden
    authority is still reachable, so it must propagate and fail the case instead of
    being swallowed.  Without that distinction a matrix could report green while a
    mint writer was still present.
    """

    try:
        fn()
    except AssertionError:
        raise
    except BaseException as exc:  # noqa: BLE001 - Core refusals are the property
        return f"refused:{type(exc).__name__}"
    return "inert:no-exception"


# ---------------------------------------------------------------------------
# C3-1: every candidate trust root declared invalid by the frozen contract
# ---------------------------------------------------------------------------
def c1_01_public_function(c: AttackContext) -> str:
    """PUBLIC FUNCTION as trust root: drive the historical public attack verbatim."""

    def attack():
        with open_live_provider_return_window(attempt_id=c.attempt_id) as window:
            register_handler_return(window, c.forged)
            c.attempts.record_live_provider_return(  # type: ignore[attr-defined]
                c.attempt_id, captured_at=NOW, directive=c.forged,
                live_window=window,
            )

    return _attack_outcome(attack)


def c1_02_exported_symbol(c: AttackContext) -> str:
    """EXPORTED SYMBOL as trust root: drive every name in ``__all__`` as authority."""

    def attack():
        for name in live_return_module.__all__:
            symbol = getattr(live_return_module, name)
            if callable(symbol):
                try:
                    symbol(attempt_id=c.attempt_id)
                except BaseException:
                    pass
                try:
                    symbol(c.attempt_id, c.forged)
                except BaseException:
                    pass
        # No exported symbol may be a mint writer for the store.
        assert not any(
            name in FORBIDDEN_MINT_NAMES for name in live_return_module.__all__
        )
        c.stage()

    return _attack_outcome(attack)


def c1_03_store_method(c: AttackContext) -> str:
    """STORE METHOD as trust root: search the whole store surface for a mint writer."""

    def attack():
        for holder in (c.attempts, type(c.attempts)):
            for name in dir(holder):
                if name in FORBIDDEN_MINT_NAMES:
                    raise AssertionError(f"mint writer reachable as {name}")
        c.attempts.record_live_provider_return(  # type: ignore[attr-defined]
            c.attempt_id, captured_at=NOW, directive=c.forged, live_window=None
        )

    return _attack_outcome(attack)


def c1_04_classmethod(c: AttackContext) -> str:
    """CLASSMETHOD as trust root: no class-level issuance path may exist."""

    def attack():
        for klass in (LiveProviderReturnWindow, BackgroundModelAttemptStore):
            for name, value in vars(klass).items():
                if isinstance(value, classmethod):
                    assert name not in FORBIDDEN_MINT_NAMES, name
                    # Driving any surviving classmethod with attacker bytes must
                    # not create trusted state.
                    try:
                        getattr(klass, name)(c.attempt_id, c.forged)
                    except BaseException:
                        pass
        assert not hasattr(LiveProviderReturnWindow, "_issue")
        LiveProviderReturnWindow._issue(  # type: ignore[attr-defined]
            sentinel=object(), attempt_id=c.attempt_id, window_id="c3", seal=b"0" * 32
        )

    return _attack_outcome(attack)


def c1_05_registry(c: AttackContext) -> str:
    """REGISTRY as trust root: no module-level mutable registry may accumulate state."""

    def attack():
        before = {}
        for module in CORE_MODULES:
            for name, value in vars(module).items():
                if isinstance(value, (dict, list, set)) and not name.startswith("__"):
                    before[(module.__name__, name)] = (
                        len(value) if hasattr(value, "__len__") else None
                    )
        for _ in range(3):
            with open_live_provider_return_window(attempt_id=c.attempt_id) as window:
                register_handler_return(window, c.forged)
        after = {}
        for module in CORE_MODULES:
            for name, value in vars(module).items():
                if isinstance(value, (dict, list, set)) and not name.startswith("__"):
                    after[(module.__name__, name)] = (
                        len(value) if hasattr(value, "__len__") else None
                    )
        assert before == after, "a module-level registry accumulated window state"
        assert not hasattr(live_return_module, "_OPEN_WINDOWS")
        assert not hasattr(live_return_module, "_HANDLER_RETURNS")

    return _attack_outcome(attack)


def c1_06_contextvar(c: AttackContext) -> str:
    """CONTEXTVAR as trust root: setting it directly from caller code confers nothing."""

    def attack():
        marker = object.__new__(LiveProviderReturnWindow)
        object.__setattr__(marker, "_attempt_id", c.attempt_id)
        object.__setattr__(marker, "_state", "open")
        token = live_return_module._ACTIVE_WINDOW.set(marker)
        try:
            assert live_return_module._ACTIVE_WINDOW.get() is marker
            assert live_return_authority_snapshot()["inert_marker_on_this_stack"] is True
            # Even with the ContextVar armed by the caller, nothing is authorized.
            assert live_return_authority_snapshot()["armed_on_this_stack"] is False
            assert live_return_authority_snapshot()["trust_conferred"] is False
            # Arming the ContextVar by hand must not unlock the historical writer.
            c.attempts.record_live_provider_return(  # type: ignore[attr-defined]
                c.attempt_id, captured_at=NOW, directive=c.forged, live_window=marker
            )
        finally:
            live_return_module._ACTIVE_WINDOW.reset(token)

    return _attack_outcome(attack)


def c1_07_sentinel(c: AttackContext) -> str:
    """SENTINEL as trust root: no identity-bearing sentinel may gate authenticity."""

    def attack():
        # The historical issuance sentinel is gone.
        assert not hasattr(live_return_module, "_ISSUE_SENTINEL")
        sentinels = {
            (module.__name__, name)
            for module in CORE_MODULES
            for name, value in vars(module).items()
            if not name.startswith("__") and type(value) is object
        }
        # The decommissioned authority module holds no identity sentinel at all:
        # there is nothing whose object identity could gate authenticity.
        assert not any(
            module_name.endswith("live_return") for module_name, _ in sentinels
        ), sorted(sentinels)
        # Any sentinel that legitimately exists elsewhere in Core (for example an
        # "auto" marker used for topic selection) must never be consulted by the
        # modules that own trusted-return authorization, so it cannot act as an
        # authenticity gate.
        authority_sources = {
            authority.__name__: inspect.getsource(authority)
            for authority in (background_attempt_module, late_return_module)
        }
        for module_name, sentinel_name in sentinels:
            for authority_name, source in authority_sources.items():
                assert sentinel_name not in source, (
                    f"{authority_name} consults sentinel {module_name}.{sentinel_name}"
                )
        # And driving the historical sentinel-shaped attack still yields nothing.
        with open_live_provider_return_window(attempt_id=c.attempt_id) as window:
            register_handler_return(window, c.forged)
            c.attempts.record_live_provider_return(  # type: ignore[attr-defined]
                c.attempt_id, captured_at=NOW, directive=c.forged, live_window=window
            )

    return _attack_outcome(attack)


def c1_08_object_identity(c: AttackContext) -> str:
    """OBJECT IDENTITY as trust root: the exact returned object authenticates nothing."""

    def attack():
        # A live turn whose handler returns exactly this object.
        db2 = c.db.with_name("c3-identity.sqlite")
        store, index = open_world(db2)
        returned = make_directive(response="C3_IDENTITY_BYTES")
        runtime = FusedTurnRuntime(
            store=store, index=index, subject_id="user_1",
            model_handler=lambda _snapshot: returned,
            late_return_verifier=make_verifier(),
        )
        runtime.run_turn(
            session_id="c3-identity", turn_index=1,
            user_input="identity is not authority", occurred_at=NOW,
        )
        execution_id = runtime.turn_executions.execution_id_for(
            subject_id="user_1", session_id="c3-identity", turn_index=1
        )
        attempt = runtime.background_model_attempts.list_for_work(
            subject_id="user_1", work_kind="user_turn", work_id=execution_id
        )[-1]
        # Object identity of the returned directive conferred no authenticity:
        # no receipt, no handoff, no staged response exist for that live round.
        assert (
            runtime.background_model_attempts.response_authenticity_receipt(
                attempt.attempt_id
            )
            is None
        )
        assert runtime.background_model_attempts.staged_response(attempt.attempt_id) is None
        with sqlite3.connect(db2) as conn:
            assert tuple(
                conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in TRUST_TABLES
            ) == (0, 0, 0)

    return _attack_outcome(attack)


def c1_09_test_secret(c: AttackContext) -> str:
    """TEST SECRET as trust root: another test's key material is not this authority."""

    def attack():
        context = c.signing_context()
        # A well-formed proof labelled with a DIFFERENT external key id must be
        # refused: only the verifier Core itself bound before dispatch can
        # authorize this attempt, so no other key material -- including any secret
        # a test happens to hold -- is a trust root.
        message = late_return_message(
            **context.scope_fields(),
            provider=c.forged.provenance.provider,
            model=c.forged.provenance.model,
            provider_request_id=c.forged.provenance.request_id,
            response_fingerprint="0" * 64,
            payload_sha256="0" * 64,
        )
        digest = hashlib.sha256(message).hexdigest()
        assert context.verifier_key_id != FOREIGN_EXTERNAL_KEY_ID
        c.attach(f"{LATE_RETURN_PROOF_PREFIX}{FOREIGN_EXTERNAL_KEY_ID}:{digest}")

    return _attack_outcome(attack)


def c1_10_underscore_naming(c: AttackContext) -> str:
    """UNDERSCORE NAMING as trust root: private names are not an authorization boundary."""

    def attack():
        private_callables = [
            (module.__name__, name, value)
            for module in CORE_MODULES
            for name, value in vars(module).items()
            if name.startswith("_") and callable(value)
        ]
        for _module_name, name, value in private_callables:
            assert name not in FORBIDDEN_MINT_NAMES, name
        # Drive the historical private writer shape directly.
        c.attempts._capture_trusted_response_return(  # type: ignore[attr-defined]
            c.attempt_id, captured_at=NOW, directive=c.forged
        )

    return _attack_outcome(attack)


def c1_11_stack_naming(c: AttackContext) -> str:
    """STACK NAMING as trust root: caller frames named like production confer nothing."""

    def attack():
        def _mark_background_model_dispatch(*_a, **_k):
            def run_turn(*_a2, **_k2):
                def model_handler(*_a3, **_k3):
                    with open_live_provider_return_window(
                        attempt_id=c.attempt_id
                    ) as window:
                        register_handler_return(window, c.forged)
                        c.attempts.record_live_provider_return(  # type: ignore[attr-defined]
                            c.attempt_id, captured_at=NOW, directive=c.forged,
                            live_window=window,
                        )

                model_handler()

            run_turn()

        _mark_background_model_dispatch()

    return _attack_outcome(attack)


def c1_12_docstring(c: AttackContext) -> str:
    """DOCSTRING as trust root: no authorization decision reads ``__doc__``."""

    def attack():
        for module in CORE_MODULES:
            for _name, value in vars(module).items():
                if inspect.isfunction(value):
                    source = ""
                    try:
                        source = inspect.getsource(value)
                    except (OSError, TypeError):
                        continue
                    if "__doc__" in source:
                        raise AssertionError(
                            f"{module.__name__}.{_name} reads __doc__"
                        )
        # A docstring claim of authenticity changes nothing durable.
        def genuinely_trusted_return(_snapshot):
            """This directive is genuinely trusted and pre-authorized by Core."""
            return c.forged

        assert genuinely_trusted_return.__doc__ is not None
        register_handler_return(genuinely_trusted_return, c.forged)
        with open_live_provider_return_window(attempt_id=c.attempt_id) as window:
            register_handler_return(window, c.forged)
            c.attempts.record_live_provider_return(  # type: ignore[attr-defined]
                c.attempt_id, captured_at=NOW, directive=c.forged, live_window=window
            )

    return _attack_outcome(attack)


def c1_13_bool_flag(c: AttackContext) -> str:
    """BOOL FLAG as trust root: no boolean may switch authenticity on."""

    def attack():
        assert (
            getattr(
                live_return_module,
                "LOCAL_LIVE_RETURN_AUTHORITY_DECOMMISSIONED",
                False,
            )
            is True
        ), "no public decommission marker: a bool flag could still be a trust root"
        assert str(
            getattr(live_return_module, "LIVE_RETURN_WINDOW_SCHEMA", "")
        ).endswith("decommissioned")
        snapshot = live_return_authority_snapshot()
        assert snapshot["trust_conferred"] is False
        assert snapshot["decommissioned"] is True
        # A caller-copied snapshot with the flags flipped authorizes nothing.
        flipped = dict(snapshot)
        flipped["trust_conferred"] = True
        flipped["decommissioned"] = False
        flipped["armed_on_this_stack"] = True
        assert flipped["trust_conferred"] is True
        c.attach(c.bogus_proof())

    return _attack_outcome(attack)


# ---------------------------------------------------------------------------
# C3-2: every enumerated reflection path
# ---------------------------------------------------------------------------
def _walk_callables():
    for module in CORE_MODULES:
        for name, value in list(vars(module).items()):
            if name.startswith("__"):
                continue
            if inspect.isfunction(value):
                yield module, name, value
            elif inspect.isclass(value):
                for attr_name, attr in list(vars(value).items()):
                    target = attr
                    if isinstance(attr, (classmethod, staticmethod)):
                        target = attr.__func__
                    elif isinstance(attr, property):
                        target = attr.fget
                    if inspect.isfunction(target):
                        yield module, f"{name}.{attr_name}", target


def c2_01_globals(c: AttackContext) -> str:
    """``__globals__`` reflection must not expose a mint authority."""

    def attack():
        for _module, qualified, function in _walk_callables():
            for name in FORBIDDEN_MINT_NAMES:
                assert name not in function.__globals__, f"{qualified}.__globals__[{name}]"
        store_globals = type(c.attempts).record_response.__globals__
        for name in FORBIDDEN_MINT_NAMES:
            assert name not in store_globals, name
        c.attach(c.bogus_proof())

    return _attack_outcome(attack)


def c2_02_sys_modules(c: AttackContext) -> str:
    """``sys.modules`` re-entry must not expose a mint authority."""

    def attack():
        module = sys.modules["aios_core.runtime.live_return"]
        assert module is live_return_module
        for name in FORBIDDEN_MINT_NAMES:
            assert not hasattr(module, name), name
        # Reaching the store class through sys.modules and minting from it.
        store_module = sys.modules["aios_core.runtime.background_attempt"]
        klass = store_module.BackgroundModelAttemptStore
        assert not hasattr(klass, "record_live_provider_return")
        klass.record_live_provider_return(  # type: ignore[attr-defined]
            c.attempts, c.attempt_id, captured_at=NOW, directive=c.forged,
            live_window=None,
        )

    return _attack_outcome(attack)


def c2_03_dict(c: AttackContext) -> str:
    """``__dict__`` walks over module, class, instance and runtime must find nothing."""

    def attack():
        holders = (
            live_return_module.__dict__,
            background_attempt_module.__dict__,
            vars(type(c.attempts)),
            vars(c.attempts),
            vars(c.runtime),
            vars(LiveProviderReturnWindow),
        )
        for holder in holders:
            for name in FORBIDDEN_MINT_NAMES:
                assert name not in holder, name
            for value in holder.values():
                assert not isinstance(value, LiveProviderReturnWindow)
        c.attach(c.bogus_proof())

    return _attack_outcome(attack)


def c2_04_bound_methods(c: AttackContext) -> str:
    """Bound methods of the store/runtime must not mint from caller bytes."""

    def attack():
        for holder in (c.attempts, c.runtime):
            for name in dir(holder):
                if name.startswith("__"):
                    continue
                try:
                    value = getattr(holder, name)
                except Exception:
                    continue
                if not inspect.ismethod(value):
                    continue
                assert name not in FORBIDDEN_MINT_NAMES, name
        # The historical bound-method mint shape, reached through the instance.
        c.attempts.record_live_provider_return(  # type: ignore[attr-defined]
            c.attempt_id, captured_at=NOW, directive=c.forged, live_window=None
        )

    return _attack_outcome(attack)


def c2_05_closure_cells(c: AttackContext) -> str:
    """Closure cells must not smuggle a mint authority."""

    def attack():
        for _module, qualified, function in _walk_callables():
            closure = function.__closure__ or ()
            for cell in closure:
                try:
                    content = cell.cell_contents
                except ValueError:
                    continue
                assert not isinstance(content, LiveProviderReturnWindow), qualified
                if inspect.isfunction(content):
                    for name in FORBIDDEN_MINT_NAMES:
                        assert name not in content.__globals__, qualified
        c.attach(c.bogus_proof())

    return _attack_outcome(attack)


def c2_06_defaults(c: AttackContext) -> str:
    """Argument defaults must not carry an authority object."""

    def attack():
        for _module, qualified, function in _walk_callables():
            for value in (function.__defaults__ or ()):
                assert not isinstance(value, LiveProviderReturnWindow), qualified
            for value in (function.__kwdefaults__ or {}).values():
                assert not isinstance(value, LiveProviderReturnWindow), qualified
        c.attach(c.bogus_proof())

    return _attack_outcome(attack)


def c2_07_descriptors(c: AttackContext) -> str:
    """Descriptors / properties must not produce authority on access."""

    def attack():
        for klass in (BackgroundModelAttemptStore, LiveProviderReturnWindow,
                      FusedTurnRuntime):
            for name, value in list(vars(klass).items()):
                if isinstance(value, property):
                    assert name not in FORBIDDEN_MINT_NAMES, name
                if hasattr(value, "__get__") and not isinstance(
                    value, (classmethod, staticmethod, property, types.FunctionType)
                ):
                    assert name not in FORBIDDEN_MINT_NAMES, name
        # Accessing every descriptor on a live instance must arm nothing.
        for name in dir(type(c.attempts)):
            if isinstance(getattr(type(c.attempts), name, None), property):
                try:
                    getattr(c.attempts, name)
                except Exception:
                    pass
        assert live_return_authority_snapshot()["open_windows"] == 0
        c.attach(c.bogus_proof())

    return _attack_outcome(attack)


def c2_08_object_new(c: AttackContext) -> str:
    """``object.__new__`` fabrication must not produce a capability object."""

    def attack():
        fabricated = object.__new__(LiveProviderReturnWindow)
        object.__setattr__(fabricated, "_attempt_id", c.attempt_id)
        object.__setattr__(fabricated, "_window_id", "c3-forged")
        object.__setattr__(fabricated, "_seal", b"0" * 32)
        object.__setattr__(fabricated, "_state", "open")
        assert isinstance(fabricated, LiveProviderReturnWindow)
        register_handler_return(fabricated, c.forged)
        live_return_module._ACTIVE_WINDOW.set(fabricated)
        c.attempts.record_live_provider_return(  # type: ignore[attr-defined]
            c.attempt_id, captured_at=NOW, directive=c.forged,
            live_window=fabricated,
        )

    return _attack_outcome(attack)


def c2_09_ctor(c: AttackContext) -> str:
    """Direct ctor invocation must not produce a window."""

    def attack():
        for arguments in (
            (),
            (c.attempt_id,),
            (c.attempt_id, "c3-window"),
        ):
            try:
                LiveProviderReturnWindow(*arguments)  # type: ignore[call-arg]
                raise AssertionError("window ctor succeeded")
            except TypeError:
                pass
        c.attach(c.bogus_proof())

    return _attack_outcome(attack)


def c2_10_import(c: AttackContext) -> str:
    """Re-import / reload must not resurrect authority."""

    def attack():
        module = importlib.import_module("aios_core.runtime.live_return")
        assert module is live_return_module
        reloaded = importlib.reload(module)
        try:
            for name in FORBIDDEN_MINT_NAMES:
                assert not hasattr(reloaded, name), name
            assert reloaded.LOCAL_LIVE_RETURN_AUTHORITY_DECOMMISSIONED is True
            with reloaded.open_live_provider_return_window(
                attempt_id=c.attempt_id
            ) as window:
                reloaded.register_handler_return(window, c.forged)
            assert reloaded.live_return_authority_snapshot()["open_windows"] == 0
        finally:
            importlib.reload(reloaded)
        c.attach(c.bogus_proof())

    return _attack_outcome(attack)


def c2_11_callbacks(c: AttackContext) -> str:
    """Caller-installed callbacks must not mint trusted state."""

    def attack():
        db2 = c.db.with_name("c3-callbacks.sqlite")
        store, index = open_world(db2)
        armed: dict[str, object] = {}

        def handler(snapshot):
            with open_live_provider_return_window(
                attempt_id=snapshot.model_attempt_id
            ) as window:
                register_handler_return(window, None)
                armed["window"] = window
                armed["globals"] = open_live_provider_return_window.__globals__
            return make_directive(response="C3_CALLBACK_BYTES")

        runtime = FusedTurnRuntime(
            store=store, index=index, subject_id="user_1", model_handler=handler,
            late_return_verifier=make_verifier(),
            model_response_recorder=lambda _s, _d: armed.setdefault("recorded", True),
        )
        runtime.run_turn(
            session_id="c3-callbacks", turn_index=1,
            user_input="callback attack", occurred_at=NOW,
        )
        assert "window" in armed
        with sqlite3.connect(db2) as conn:
            assert tuple(
                conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in TRUST_TABLES
            ) == (0, 0, 0)

    return _attack_outcome(attack)


def c2_12_exception_objects(c: AttackContext) -> str:
    """Exception objects / tracebacks must not leak a mint authority."""

    def attack():
        namespaces = []
        # The decommissioned ctor is deliberately excluded from the frame walk:
        # ``LiveProviderReturnWindow()`` raises from inside ``__init__``, whose own
        # frame necessarily holds the half-built ``self``.  That object is never
        # returned to the caller, which is asserted separately below.
        for attempt in (
            lambda: c.attempts.record_live_provider_return(  # type: ignore[attr-defined]
                c.attempt_id, captured_at=NOW, directive=c.forged, live_window=None
            ),
            lambda: c.attach(c.bogus_proof()),
            lambda: c.stage(),
            # Re-crossing the provider boundary is refused, which yields genuine
            # Core frames without changing the attacked attempt's state.
            lambda: c.attempts.mark_dispatching(
                c.attempt_id, dispatched_at=NOW + timedelta(seconds=5),
                outbound_request_fingerprint="c3-matrix-redispatch-attack",
            ),
        ):
            try:
                attempt()
            except BaseException as exc:
                traceback = exc.__traceback__
                while traceback is not None:
                    frame = traceback.tb_frame
                    namespaces.append(frame.f_globals)
                    namespaces.append(dict(frame.f_locals))
                    for value in list(frame.f_locals.values()):
                        if isinstance(value, LiveProviderReturnWindow):
                            raise AssertionError("window leaked through a frame")
                    traceback = traceback.tb_next
                for name in FORBIDDEN_MINT_NAMES:
                    assert not hasattr(exc, name), name
        # No exception path ever hands a window instance back to the caller.
        for factory in (
            lambda: LiveProviderReturnWindow(),  # type: ignore[call-arg]
            lambda: LiveProviderReturnWindow(c.attempt_id),  # type: ignore[call-arg]
        ):
            try:
                produced = factory()
            except BaseException as exc:
                assert not isinstance(exc, LiveProviderReturnWindow)
                assert getattr(exc, "args", ()) is not None
            else:
                raise AssertionError(f"ctor produced {produced!r}")
        assert namespaces, "no exception namespace was collected"
        for namespace in namespaces:
            for name in FORBIDDEN_MINT_NAMES:
                assert name not in namespace, name

    return _attack_outcome(attack)


def c2_13_store_runtime_graph(c: AttackContext) -> str:
    """A full BFS over the store/runtime graph must find no mint authority."""

    def attack():
        seen: set[int] = set()
        queue = [(c.runtime, "runtime"), (c.attempts, "store")]
        windows = []
        forbidden = []
        while queue:
            current, path = queue.pop()
            if id(current) in seen or len(seen) > 20000:
                continue
            seen.add(id(current))
            if isinstance(current, LiveProviderReturnWindow):
                windows.append(path)
                continue
            if inspect.isfunction(current) or inspect.ismethod(current):
                function = getattr(current, "__func__", current)
                for name in FORBIDDEN_MINT_NAMES:
                    if getattr(function, "__name__", "") == name:
                        forbidden.append(f"{path}:{name}")
                    if name in getattr(function, "__globals__", {}):
                        forbidden.append(f"{path}:__globals__:{name}")
            holders = []
            if isinstance(current, dict):
                holders = list(current.items())
            elif isinstance(current, (list, tuple, set, frozenset)):
                holders = list(enumerate(current))
            elif hasattr(current, "__dict__"):
                holders = list(vars(current).items())
            for key, value in holders:
                if isinstance(value, (str, int, float, bool, bytes, type(None))):
                    continue
                queue.append((value, f"{path}.{key}"))
        assert windows == [], windows
        assert forbidden == [], forbidden

    return _attack_outcome(attack)


# ---------------------------------------------------------------------------
# C3-3: verifier-less attempts stay permanently in doubt
# ---------------------------------------------------------------------------
def c3_01_verifier_less_permanently_in_doubt(c: AttackContext) -> str:
    """No bound verifier => no route out of ``in_doubt``, ever, in any process."""

    def attack():
        assert c.attempts.late_return_verifier(c.attempt_id) is None
        assert c.attempts.late_return_signing_context(c.attempt_id) is None
        # Every durable writer refuses, in sequence, in a fresh process.
        c.record_response()
        c.stage(authenticity_proof=None)
        c.stage(authenticity_proof="bgresponse_v1_" + "0" * 64)
        c.attach(c.bogus_proof())
        with open_live_provider_return_window(attempt_id=c.attempt_id) as window:
            register_handler_return(window, c.forged)
            c.attempts.record_live_provider_return(  # type: ignore[attr-defined]
                c.attempt_id, captured_at=NOW, directive=c.forged, live_window=window
            )
        reopened = fresh_recovery_runtime(c.db)
        assert reopened.background_model_attempts.get(c.attempt_id).state == "in_doubt"
        reopened.background_model_attempts.attach_late_trusted_return(
            c.attempt_id,
            attached_at=NOW + timedelta(seconds=9),
            directive_payload=c.payload,
            late_return_proof=c.bogus_proof(),
            evidence="verifier-less attempt must stay in doubt",
        )

    return _attack_outcome(attack)


CASES = (
    ("C3-1-01-public-function", c1_01_public_function, True),
    ("C3-1-02-exported-symbol", c1_02_exported_symbol, True),
    ("C3-1-03-store-method", c1_03_store_method, True),
    ("C3-1-04-classmethod", c1_04_classmethod, True),
    ("C3-1-05-registry", c1_05_registry, True),
    ("C3-1-06-contextvar", c1_06_contextvar, True),
    ("C3-1-07-sentinel", c1_07_sentinel, True),
    ("C3-1-08-object-identity", c1_08_object_identity, True),
    ("C3-1-09-test-secret", c1_09_test_secret, True),
    ("C3-1-10-underscore-naming", c1_10_underscore_naming, True),
    ("C3-1-11-stack-naming", c1_11_stack_naming, True),
    ("C3-1-12-docstring", c1_12_docstring, True),
    ("C3-1-13-bool-flag", c1_13_bool_flag, True),
    ("C3-2-01-globals", c2_01_globals, True),
    ("C3-2-02-sys-modules", c2_02_sys_modules, True),
    ("C3-2-03-dict", c2_03_dict, True),
    ("C3-2-04-bound-methods", c2_04_bound_methods, True),
    ("C3-2-05-closure-cells", c2_05_closure_cells, True),
    ("C3-2-06-defaults", c2_06_defaults, True),
    ("C3-2-07-descriptors", c2_07_descriptors, True),
    ("C3-2-08-object-new", c2_08_object_new, True),
    ("C3-2-09-ctor", c2_09_ctor, True),
    ("C3-2-10-import", c2_10_import, True),
    ("C3-2-11-callbacks", c2_11_callbacks, True),
    ("C3-2-12-exception-objects", c2_12_exception_objects, True),
    ("C3-2-13-store-runtime-graph", c2_13_store_runtime_graph, True),
    ("C3-3-01-verifier-less-in-doubt", c3_01_verifier_less_permanently_in_doubt, False),
)

#: (case id, attack, bind_verifier, force_in_doubt)
CASE_SPECS = tuple(
    (case_id, fn, bind, (not bind)) for case_id, fn, bind in CASES
)


def test_c3_matrix_covers_exactly_the_enumerated_cases():
    """The matrix is mechanically complete: 27 cases, 13 + 13 + 1."""

    assert len(CASES) == 27
    identifiers = [spec[0] for spec in CASE_SPECS]
    assert len(set(identifiers)) == 27
    assert sum(1 for i in identifiers if i.startswith("C3-1-")) == 13
    assert sum(1 for i in identifiers if i.startswith("C3-2-")) == 13
    assert sum(1 for i in identifiers if i.startswith("C3-3-")) == 1


@pytest.mark.parametrize(
    "case_id,attack,bind_verifier,force_in_doubt",
    [pytest.param(*spec, id=spec[0]) for spec in CASE_SPECS],
)
def test_c3_attack_case_leaves_no_caller_manufacturable_trust(
    tmp_path, case_id, attack, bind_verifier, force_in_doubt
):
    context = AttackContext(
        tmp_path, bind_verifier=bind_verifier, force_in_doubt=force_in_doubt
    )
    outcome = attack(context)
    assert isinstance(outcome, str) and outcome
    context.assert_properties(outcome)
    # The World is still usable afterwards: nothing was corrupted by the attack.
    assert trust_rows(context.db) == (0, 0, 0)
