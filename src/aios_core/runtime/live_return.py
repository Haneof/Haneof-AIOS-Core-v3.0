"""Ephemeral, call-stack-scoped authority for the live provider-return boundary.

`BLK-W17-001` proved that Python underscore naming is not an authorization
boundary: a post-crash recovery caller holding ``FusedTurnRuntime`` /
``BackgroundModelAttemptStore`` could invoke the receipt writer directly and mint
a durable trusted receipt + exact handoff for bytes it fabricated, with no
external RSA proof and no live provider call.

Corrective-002 therefore removes every receipt/handoff writer that accepts only
caller-supplied arguments and replaces the live fast path with a genuine
ephemeral authority:

``LiveProviderReturnWindow``
    A one-shot, attempt-bound token issued **only** while Core's own model-call
    frame is between the provider handler returning and the receipt being
    captured.  It is not persisted, not written to SQLite, never attached to any
    runtime/store object, not serializable, not copyable, not re-issuable after
    process death, and it is removed from the process-local registry when the
    window closes.

Authorization therefore requires all of the following simultaneously:

1. the exact window object that Core's live frame issued (process-local registry
   identity check, not equality),
2. that window still being the one armed on the *current* call stack
   (:data:`_ACTIVE_WINDOW` context variable identity check),
3. the window still open (one-shot consumption),
4. the window's attempt id equal to the attempt being captured, and
5. the directive being captured being the exact object the in-process provider
   handler returned for that window (identity check against the live-capture
   registry).

A post-crash recovery process has none of these: the registry, the context
variable and the handler-returned object all died with the process, and nothing
about them exists in the runtime database.

Trust boundary (explicit and honest): this authority separates the *live
provider-return call stack* from the *recovery object graph* and from the
durable database.  It is not a defence against arbitrary Python code that
already executes inside the Core process and deliberately drives this module's
issuing helpers to fake a live provider boundary; that is the same in-process
limitation disclosed for the accepted Window 12/14/16 trust rulings, where any
in-process caller could reach the previous authority helpers directly.
"""

from __future__ import annotations

import contextvars
import secrets
import threading
from contextlib import contextmanager
from typing import Iterator, Mapping

LIVE_RETURN_WINDOW_SCHEMA = "aios.background-model-live-return-window.v1"


class LiveReturnAuthorityError(RuntimeError):
    """The live provider-return authority was not satisfied; fail closed."""


# Module-private issuance sentinel.  A window can only be built by :func:`issue`
# below, which itself is only reachable from the live model-call frame.
_ISSUE_SENTINEL = object()

# Process-local registry of currently open windows.  Never persisted.  Removal on
# window close is what makes the token non-reissuable after process death: a
# fresh process starts with this mapping empty.
_OPEN_WINDOWS: dict[str, "LiveProviderReturnWindow"] = {}
# Directive identities returned by the in-process provider handler, per window.
_HANDLER_RETURNS: dict[str, int] = {}
_REGISTRY_LOCK = threading.RLock()

# The window armed on the current call stack/context.  A window object is only
# usable while it is both registered and currently armed, so a reference leaked
# out of the ``with`` block can never be replayed.
_ACTIVE_WINDOW: contextvars.ContextVar["LiveProviderReturnWindow | None"] = (
    contextvars.ContextVar("aios_live_provider_return_window", default=None)
)


class LiveProviderReturnWindow:
    """One-shot ephemeral grant issued by the live provider-return boundary."""

    __slots__ = ("_attempt_id", "_window_id", "_seal", "_state")

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError(
            "LiveProviderReturnWindow is issued by the live provider-return "
            "boundary and cannot be constructed directly"
        )

    @classmethod
    def _issue(
        cls,
        *,
        sentinel: object,
        attempt_id: str,
        window_id: str,
        seal: bytes,
    ) -> "LiveProviderReturnWindow":
        if sentinel is not _ISSUE_SENTINEL:
            raise LiveReturnAuthorityError(
                "live provider-return windows may only be issued by the live "
                "provider-return boundary"
            )
        if not isinstance(attempt_id, str) or not attempt_id:
            raise ValueError("live provider-return window requires an attempt id")
        window = object.__new__(cls)
        object.__setattr__(window, "_attempt_id", attempt_id)
        object.__setattr__(window, "_window_id", window_id)
        object.__setattr__(window, "_seal", seal)
        object.__setattr__(window, "_state", "open")
        return window

    # -- public, non-secret identity -------------------------------------
    @property
    def attempt_id(self) -> str:
        return self._attempt_id

    @property
    def window_id(self) -> str:
        return self._window_id

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_open(self) -> bool:
        return self._state == "open"

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return (
            f"LiveProviderReturnWindow(window_id={self._window_id!r}, "
            f"attempt_id={self._attempt_id!r}, state={self._state!r})"
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


@contextmanager
def open_live_provider_return_window(
    *,
    attempt_id: str,
) -> Iterator[LiveProviderReturnWindow]:
    """Arm the live provider-return authority for one in-process provider call.

    Only the live model-call frame (:mod:`aios_core.runtime.cognitive_runtime`)
    opens this window, and it does so strictly around the in-process provider
    handler invocation plus the immediately following trusted-return capture.
    """

    if _ACTIVE_WINDOW.get() is not None:
        raise LiveReturnAuthorityError(
            "a live provider-return window is already open on this call stack"
        )
    window = LiveProviderReturnWindow._issue(
        sentinel=_ISSUE_SENTINEL,
        attempt_id=attempt_id,
        window_id=secrets.token_hex(16),
        seal=secrets.token_bytes(32),
    )
    with _REGISTRY_LOCK:
        _OPEN_WINDOWS[window.window_id] = window
        _HANDLER_RETURNS.pop(window.window_id, None)
    token = _ACTIVE_WINDOW.set(window)
    try:
        yield window
    finally:
        _ACTIVE_WINDOW.reset(token)
        with _REGISTRY_LOCK:
            _OPEN_WINDOWS.pop(window.window_id, None)
            _HANDLER_RETURNS.pop(window.window_id, None)
        object.__setattr__(window, "_state", "closed")


def register_handler_return(
    window: "LiveProviderReturnWindow",
    directive: object,
) -> None:
    """Record the exact object the in-process provider handler returned.

    Called by :mod:`aios_core.runtime.cognitive_runtime` in the same frame that
    invokes the provider handler, so the live capture can mechanically require
    that the captured bytes are the bytes the provider actually returned.
    """

    _require_open_window(window)
    with _REGISTRY_LOCK:
        _HANDLER_RETURNS[window.window_id] = id(directive)


def _require_open_window(window: object) -> "LiveProviderReturnWindow":
    if not isinstance(window, LiveProviderReturnWindow):
        raise LiveReturnAuthorityError(
            "a live provider-return window is required to authorize trusted "
            "provider-return capture"
        )
    with _REGISTRY_LOCK:
        registered = _OPEN_WINDOWS.get(window.window_id)
    if registered is not window:
        raise LiveReturnAuthorityError(
            "live provider-return window was not issued by the live "
            "provider-return boundary of this process"
        )
    if _ACTIVE_WINDOW.get() is not window:
        raise LiveReturnAuthorityError(
            "live provider-return window is not armed on the current call stack"
        )
    if window._state != "open":
        raise LiveReturnAuthorityError(
            "live provider-return window is already closed or consumed"
        )
    return window


def consume_live_provider_return_window(
    window: object,
    *,
    attempt_id: str,
    directive: object,
) -> "LiveProviderReturnWindow":
    """Validate and one-shot consume the live authority for one exact return."""

    bound = _require_open_window(window)
    if bound.attempt_id != attempt_id:
        raise LiveReturnAuthorityError(
            "live provider-return window is bound to a different attempt"
        )
    with _REGISTRY_LOCK:
        handler_return = _HANDLER_RETURNS.get(bound.window_id)
        if handler_return is None:
            raise LiveReturnAuthorityError(
                "the in-process provider handler returned no bytes for this "
                "live provider-return window"
            )
        if handler_return != id(directive):
            raise LiveReturnAuthorityError(
                "captured bytes are not the object the in-process provider "
                "handler returned for this live provider-return window"
            )
        _HANDLER_RETURNS.pop(bound.window_id, None)
    object.__setattr__(bound, "_state", "consumed")
    return bound


def live_return_authority_snapshot() -> Mapping[str, object]:
    """Read-only diagnostics: no window contents, no seals, no directives."""

    with _REGISTRY_LOCK:
        return {
            "schema": LIVE_RETURN_WINDOW_SCHEMA,
            "open_windows": len(_OPEN_WINDOWS),
            "armed_on_this_stack": _ACTIVE_WINDOW.get() is not None,
            "pending_handler_returns": len(_HANDLER_RETURNS),
        }


__all__ = [
    "LIVE_RETURN_WINDOW_SCHEMA",
    "LiveProviderReturnWindow",
    "LiveReturnAuthorityError",
    "consume_live_provider_return_window",
    "live_return_authority_snapshot",
    "open_live_provider_return_window",
    "register_handler_return",
]
