"""DECOMMISSIONED local live provider-return authority (Route B).

History
-------
``BLK-W17-001`` proved that Python underscore naming is not an authorization
boundary: a post-crash recovery caller holding ``FusedTurnRuntime`` /
``BackgroundModelAttemptStore`` could invoke the receipt writer directly and mint
a durable trusted receipt + exact handoff for bytes it fabricated.

Corrective-002 answered that with an "ephemeral live provider-return window":
a process-local registry plus a :class:`contextvars.ContextVar` plus an issuance
sentinel plus a handler-return identity map.  ``BLK-W20-001``
(``RECOVERY_CALLER_TRUSTED_RETURN_MINT_ORACLE_VIA_SELF_ISSUED_EPHEMERAL_WINDOW``,
root cause ``TRUST_AUTHORITY_ISSUANCE_REMAINS_CALLER_MANUFACTURABLE``) proved that
design was still caller-manufacturable, because the *issuance* helpers themselves
were ordinary public module functions:

    with open_live_provider_return_window(attempt_id=...) as window:
        register_handler_return(window, attacker_directive)
        store.record_live_provider_return(..., live_window=window)

Any ordinary process-local recovery caller could therefore issue its own window,
declare its own bytes "handler-returned", mint a durable receipt + handoff,
complete and meter an attempt that must have stayed ``in_doubt``, and poison a
later genuine RSA trusted return.  The same authority was reachable through
``__globals__`` of the store writer and of the issuance classmethod.

Corrective-003 / Route B
------------------------
The PM-frozen design ruling for Corrective-003 is **Route B**: the local
self-trusting provider-return authority is removed entirely.  Durable trusted
provider/late return now depends only on

    a durable external verifier bound before the provider boundary
    + a genuine external cryptographic proof over that verifier

(:meth:`BackgroundModelAttemptStore.attach_late_trusted_return`).  A normal live
local handler return mints **no** durable trusted receipt and **no** exact
handoff, and an attempt with no bound verifier stays ``in_doubt`` permanently
after the provider boundary is crossed.

What this module is now
-----------------------
This module is a **tombstone**.  It holds no authority of any kind.  Nothing in
Core reads anything defined here to make an authorization decision, and no
receipt, handoff, staged exact response, state transition or meter can be
produced through it.  The historical public names are retained *only* so that
frozen third-party reviewer probes -- which import them by name and call them
outside ``try`` blocks -- remain executable byte-for-byte; each of them is an
inert no-op that grants nothing and is documented as such.

Retained inert names (zero authority):
    ``LiveProviderReturnWindow``       never constructible, never copyable,
                                       never serializable, carries no state that
                                       any Core code reads.
    ``open_live_provider_return_window`` context manager yielding an inert
                                       marker; arms no authority.
    ``register_handler_return``        inert no-op; records nothing.
    ``_ACTIVE_WINDOW``                 inert diagnostics ContextVar; **never**
                                       consulted by any authorization decision.
    ``live_return_authority_snapshot`` read-only diagnostics that report the
                                       authority as permanently decommissioned.
    ``LiveReturnAuthorityError``       fail-closed refusal exception still raised
                                       by the Route B writers.

Removed with Route B (no longer exist anywhere in Core):
    ``_ISSUE_SENTINEL``, ``_OPEN_WINDOWS``, ``_HANDLER_RETURNS``,
    ``LiveProviderReturnWindow._issue``,
    ``consume_live_provider_return_window``,
    ``BackgroundModelAttemptStore.record_live_provider_return``.

Python object identity ruling
-----------------------------
Per the frozen Corrective-003 design ruling, Python object identity may at most
act as a consistency/sequencing guard and must never act as an authenticity
authority.  This module therefore keeps no identity-bearing state at all: there
is no registry to compare against, so object identity cannot mint a receipt,
mint a handoff, establish provider authenticity, make caller bytes trusted, make
bytes recovery-eligible, move a verifier-less attempt out of ``in_doubt``, or
replace RSA/external proof.
"""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Iterator, Mapping

LIVE_RETURN_WINDOW_SCHEMA = "aios.background-model-live-return-window.v2-decommissioned"

#: Permanent, non-negotiable marker: the local live provider-return authority is
#: decommissioned.  This is a public constant, not a secret, and it authorizes
#: nothing.  It exists so that callers and audits can mechanically assert that
#: Route B is in force instead of trusting a docstring claim.
LOCAL_LIVE_RETURN_AUTHORITY_DECOMMISSIONED = True


class LiveReturnAuthorityError(RuntimeError):
    """A local caller asked for provider-return trust that Route B never grants."""


class LiveProviderReturnWindow:
    """Inert marker for a decommissioned authority.  Grants nothing.

    This type is retained only so that frozen reviewer probes that reference it
    keep executing.  It has no secret, no registry entry, no issuance path and no
    consumer: no Core code path reads an instance of this class to decide
    anything.  It deliberately cannot be constructed, copied or serialized, so
    that no caller can mistake it for a capability object.
    """

    __slots__ = ("_attempt_id", "_window_id", "_seal", "_state")

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError(
            "the local live provider-return authority is permanently "
            "decommissioned (Route B); it issues no window and grants no trust"
        )

    # -- explicitly non-serializable / non-copyable ----------------------
    def __reduce__(self) -> object:
        raise TypeError("live provider-return windows are not serializable")

    def __reduce_ex__(self, protocol: int) -> object:
        raise TypeError("live provider-return windows are not serializable")

    def __copy__(self) -> object:
        raise TypeError("live provider-return windows are not copyable")

    def __deepcopy__(self, memo: object) -> object:
        raise TypeError("live provider-return windows are not copyable")

    def __getstate__(self) -> object:
        raise TypeError("live provider-return windows are not serializable")

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return (
            "LiveProviderReturnWindow(decommissioned=true, authority=none, "
            f"attempt_id={getattr(self, '_attempt_id', None)!r})"
        )


def _inert_marker(attempt_id: str) -> LiveProviderReturnWindow:
    """Build the inert marker yielded by the decommissioned context manager.

    This is the only construction path and it is module-private, but it is *not*
    an authority: the marker it returns is never consulted by Core.  It exists
    purely so the retained context manager can yield a correctly typed object.
    """

    marker = object.__new__(LiveProviderReturnWindow)
    object.__setattr__(marker, "_attempt_id", attempt_id)
    object.__setattr__(marker, "_window_id", None)
    object.__setattr__(marker, "_seal", None)
    object.__setattr__(marker, "_state", "decommissioned")
    return marker


#: Inert diagnostics ContextVar.  **Never** read by any authorization decision in
#: Core.  Retained because frozen reviewer probes import it by name to reset
#: harness isolation state; deleting it would crash those probes at import time
#: rather than exercising them.
_ACTIVE_WINDOW: contextvars.ContextVar["LiveProviderReturnWindow | None"] = (
    contextvars.ContextVar(
        "aios_live_provider_return_window_decommissioned", default=None
    )
)


@contextmanager
def open_live_provider_return_window(
    *,
    attempt_id: str,
) -> Iterator[LiveProviderReturnWindow]:
    """DECOMMISSIONED.  Arms nothing, authorizes nothing, records nothing.

    Retained as an inert no-op so frozen reviewer probes remain executable.  A
    caller that uses this context manager obtains an inert marker and *no*
    capability: there is no receipt writer, no handoff writer and no state
    transition anywhere in Core that consults it.
    """

    if not isinstance(attempt_id, str) or not attempt_id:
        raise ValueError("attempt_id must be a non-blank string")
    marker = _inert_marker(attempt_id)
    token = _ACTIVE_WINDOW.set(marker)
    try:
        yield marker
    finally:
        _ACTIVE_WINDOW.reset(token)


def register_handler_return(
    window: object = None,
    directive: object = None,
) -> None:
    """DECOMMISSIONED.  Inert no-op: records nothing and authorizes nothing.

    "The handler returned exactly these bytes" can never be self-asserted by a
    caller under Route B, so this function does not record such a claim
    anywhere.  It accepts and ignores its historical arguments purely so that
    frozen reviewer probes keep executing byte-for-byte.
    """

    return None


def live_return_authority_snapshot() -> Mapping[str, object]:
    """Read-only diagnostics: the local authority is permanently decommissioned.

    There is no registry, no seal, no handler-return map and no armed authority
    to report.  The counts are structurally and permanently zero.
    """

    return {
        "schema": LIVE_RETURN_WINDOW_SCHEMA,
        "decommissioned": True,
        "route": "B",
        "open_windows": 0,
        "armed_on_this_stack": False,
        "pending_handler_returns": 0,
        "trust_conferred": False,
        "durable_trusted_return_authority": "external_verifier_plus_genuine_proof_only",
    }


__all__ = [
    "LIVE_RETURN_WINDOW_SCHEMA",
    "LOCAL_LIVE_RETURN_AUTHORITY_DECOMMISSIONED",
    "LiveProviderReturnWindow",
    "LiveReturnAuthorityError",
    "live_return_authority_snapshot",
    "open_live_provider_return_window",
    "register_handler_return",
]
