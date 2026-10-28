"""Resilient model handler for AIOS Core verification runs (NVIDIA-only build).

Why this exists
---------------
The NVIDIA NIM free tier enforces a per-key request rate (40 RPM on this key).
A naive handler bursts requests (one turn may make several model rounds, and the
Core's wake/summary schedulers fire immediately afterwards), slams into the
ceiling, gets 429, and — if it "degrades" to another model — gets 429 again,
because **the limit is per API key, not per model**. Switching models does not
help. What actually helps is:

1. **Pacing** — spread requests out to ``60 / limit`` seconds each, so the budget
   is never consumed as a burst.
2. **Backoff on 429** — when the provider still pushes back, wait and retry with
   exponential backoff instead of switching models.
3. **Cross-process coordination** — several agents share one key, so the budget
   and the penalty must live on disk behind a file lock.

A second endpoint is supported only for the case where the primary endpoint is
unreachable or rejects the key — never as a rate-limit escape hatch.

Bucket scope
------------
The paced budget is shared **per (endpoint, API key)** — not per model, and not
one global bucket for everything. OpenAI-compatible providers meter RPM against
the key/account on a given endpoint: switching ``model=`` on the same key and
the same ``base_url`` draws on the same quota, while a different endpoint has an
independent quota of its own. Bucketing on (endpoint, key) therefore never
under-protects a shared quota and never over-throttles an independent one.
Bucket names are fingerprints only: the key is hashed, never written out.

Environment
-----------
    AIOS_PRIMARY_BASE_URL / _API_KEY / _MODEL    (default: NVIDIA MiniMax)
    AIOS_SECONDARY_BASE_URL / _API_KEY / _MODEL  (optional independent fallback)
    AIOS_RPM_LIMIT          requests/minute, default 40
    AIOS_RPM_PACE           1 = smooth pacing on (default), 0 = window only
    AIOS_RPM_SCOPE_MODEL    1 = also split per model (default 0 = endpoint+key)
    AIOS_RETRY_ATTEMPTS     default 3
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time

from aios_core.runtime._filelock import lock as _lock_file
from aios_core.runtime._filelock import unlock as _unlock_file
import urllib.error
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from aios_core.runtime.grok_provider import (
    GrokProviderConfig,
    GrokStreamingProvider,
)

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

PRIMARY_BASE_URL = os.environ.get(
    "AIOS_PRIMARY_BASE_URL", "https://integrate.api.nvidia.com/v1"
)
PRIMARY_API_KEY = os.environ.get(
    "AIOS_PRIMARY_API_KEY",
    "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",
)
PRIMARY_MODEL = os.environ.get(
    "AIOS_PRIMARY_MODEL", "minimaxai/minimax-m3.1-flash"
)

# Second endpoint — only used when the primary endpoint itself is down or the key
# is rejected. Rate limits are per key, so this is NOT a way to escape 429.
SECONDARY_BASE_URL = os.environ.get("AIOS_SECONDARY_BASE_URL", PRIMARY_BASE_URL)
SECONDARY_API_KEY = os.environ.get("AIOS_SECONDARY_API_KEY", PRIMARY_API_KEY)
SECONDARY_MODEL = os.environ.get("AIOS_SECONDARY_MODEL", "z-ai/glm-5.3-flash")

RPM_LIMIT = int(os.environ.get("AIOS_RPM_LIMIT", "40"))
PACE = os.environ.get("AIOS_RPM_PACE", "1") not in ("0", "false", "no")
# Some providers meter per model even on one key. Off by default: the common
# OpenAI-compatible contract is per key on a given endpoint.
SCOPE_BY_MODEL = os.environ.get("AIOS_RPM_SCOPE_MODEL", "0") not in (
    "0",
    "false",
    "no",
)
RETRY_ATTEMPTS = int(os.environ.get("AIOS_RETRY_ATTEMPTS", "3"))
STATE_DIR = Path(os.environ.get("AIOS_RPM_STATE_DIR", "/tmp/aios_rpm_state"))

_LOG = logging.getLogger(__name__)


def _fingerprint(value: str) -> str:
    """Short, non-reversible fingerprint — keys must never reach disk or logs."""
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:12]


def _canonical_endpoint(base_url: str) -> str:
    """Scheme/host/port/path only: query and ``user:pass@`` are dropped."""
    raw = (base_url or "").strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw if "://" in raw else "https://" + raw)
        host = (parts.hostname or "").lower()
        netloc = f"{host}:{parts.port}" if parts.port else host
        return f"{parts.scheme.lower()}://{netloc}{parts.path.rstrip('/')}"
    except ValueError:
        return raw.lower().rstrip("/")


def _bucket_name(base_url: str, api_key: str, model: str | None = None) -> str:
    """State-file stem for one quota bucket. Contains no plaintext secret."""
    parts = [
        "rpm",
        _fingerprint(_canonical_endpoint(base_url))[:10],
        _fingerprint(api_key) if api_key else "anon",
    ]
    if model:
        parts.append(_fingerprint(model)[:8])
    return "_".join(parts)


def _is_rate_limited(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
        return True
    low = f"{type(exc).__name__}: {exc}".lower()
    return any(
        h in low
        for h in ("429", "rate limit", "too many requests", "quota", "throttl")
    )


def _is_transient(exc: BaseException) -> bool:
    if _is_rate_limited(exc):
        return True
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    name = type(exc).__name__.lower()
    return any(k in name for k in ("timeout", "socket", "connection", "http"))


# --------------------------------------------------------------------------
# Shared, paced rate limiter
# --------------------------------------------------------------------------


class _SharedRateLimiter:
    """Per-(endpoint, key) request budget, paced and shared across processes.

    State file: ``{"stamps": [...], "last": ts, "penalty": seconds}``

    Concurrency: an in-process ``RLock`` serialises threads; an OS advisory
    file lock (``_filelock``: ``fcntl.flock`` on POSIX, ``msvcrt.locking`` on
    Windows) serialises processes. Either layer failing is survivable — the
    limiter marks itself degraded (see :attr:`degraded` / :meth:`snapshot`) and
    keeps pacing in process memory instead of raising, so a read-only or
    lock-less filesystem can never stop AIOS from starting.
    """

    def __init__(
        self,
        name: str,
        limit: int,
        state_dir: Path,
        *,
        interval: float | None = None,
    ) -> None:
        self.name = name
        self.limit = max(1, limit)
        # ``interval`` exists for tests only; production pace stays 60/limit.
        self.interval = 60.0 / self.limit if not interval else float(interval)
        self.path = state_dir / f"{name}.json"
        self.degraded = False
        self.degrade_reason: str | None = None
        self._lock = threading.RLock()
        self._memory: dict[str, Any] = {"stamps": [], "last": 0.0, "penalty": 0.0}
        try:
            state_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._degrade(f"state_dir_unusable:{type(exc).__name__}")

    # -- degradation ------------------------------------------------------
    def _degrade(self, reason: str) -> None:
        if self.degraded:
            return
        self.degraded = True
        self.degrade_reason = reason
        _LOG.warning(
            "rate limiter %s degraded (%s); pacing in process memory only",
            self.name,
            reason,
        )

    def _tx_memory(self, fn: Callable[[dict, int | None], Any]) -> Any:
        self._memory.setdefault("stamps", [])
        self._memory.setdefault("last", 0.0)
        self._memory.setdefault("penalty", 0.0)
        return fn(self._memory, None)

    def _read_state(self, fd: int) -> dict[str, Any]:
        try:
            raw = os.read(fd, 65536).decode("utf-8", errors="replace")
            state = json.loads(raw) if raw.strip() else {}
        except (ValueError, OSError):
            state = {}
        if not isinstance(state, dict):
            state = {}
        state.setdefault("stamps", [])
        state.setdefault("last", 0.0)
        state.setdefault("penalty", 0.0)
        if not isinstance(state["stamps"], list):
            state["stamps"] = []
        return state

    def _write_state(self, fd: int, state: dict[str, Any]) -> None:
        try:
            os.ftruncate(fd, 0)
            os.lseek(fd, 0, os.SEEK_SET)
            state["stamps"] = state["stamps"][-300:]
            os.write(fd, json.dumps(state).encode())
        except OSError:
            pass

    # -- transaction -------------------------------------------------------
    def _tx(self, fn: Callable[[dict, int | None], Any]) -> Any:
        with self._lock:
            try:
                fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o600)
            except OSError as exc:
                self._degrade(f"state_file_unopenable:{type(exc).__name__}")
                return self._tx_memory(fn)
            lock_held = False
            try:
                try:
                    _lock_file(fd)
                    lock_held = True
                except OSError as exc:
                    # No advisory locking (some network/odd filesystems). Pace
                    # in memory rather than failing the caller.
                    self._degrade(f"lock_unavailable:{type(exc).__name__}")
                state = self._read_state(fd)
                # The callback may sleep while holding the lock. That is
                # intentional: it serialises waiters so two processes cannot
                # both decide the same slot is free. Sleeps are bounded (<= 90s).
                result = fn(state, fd)
                self._write_state(fd, state)
                return result
            finally:
                if lock_held:
                    try:
                        _unlock_file(fd)
                    except OSError:
                        pass
                try:
                    os.close(fd)
                except OSError:
                    pass

    def acquire(self) -> float:
        """Block until a slot is free under both pacing and the 60s window."""

        def _fn(state: dict, fd: int | None) -> float:
            now = time.time()
            waited = 0.0
            if PACE:
                earliest = float(state["last"]) + self.interval + float(state["penalty"])
                if earliest > now:
                    waited += earliest - now
                    time.sleep(earliest - now)
                    now = time.time()
            window = [t for t in state["stamps"] if now - t < 60.0]
            if len(window) >= self.limit:
                # Fixed-window fallback: wait for the oldest to age out.
                sleep_for = 60.0 - (now - min(window)) + 0.1
                time.sleep(sleep_for)
                waited += sleep_for
                now = time.time()
                window = [t for t in window if now - t < 60.0]
            window.append(now)
            state["stamps"] = window
            state["last"] = now
            return waited

        return self._tx(_fn)

    def penalize(self, attempt: int) -> float:
        """Record a 429 and return how long the caller should wait."""

        def _fn(state: dict, fd: int | None) -> float:
            current = float(state.get("penalty") or 0.0)
            new = min(max(5.0, current * 2 + 5.0), 90.0)
            state["penalty"] = new
            # A rejected attempt still consumed a request slot upstream.
            state["stamps"] = list(state.get("stamps") or []) + [time.time()]
            state["last"] = time.time()
            return max(5.0 * (2**attempt), min(new, 60.0))

        return self._tx(_fn)

    def reward(self) -> None:
        """Decay the penalty after a successful call."""

        def _fn(state: dict, fd: int | None) -> None:
            state["penalty"] = max(0.0, float(state.get("penalty") or 0.0) * 0.7 - 1.0)
            return None

        self._tx(_fn)

    def snapshot(self) -> dict[str, Any]:
        return self._tx(
            lambda state, fd: {
                "bucket": self.name,
                "limit": self.limit,
                "used_last_60s": len(
                    [t for t in state["stamps"] if time.time() - t < 60.0]
                ),
                "penalty_seconds": round(float(state["penalty"]), 1),
                "degraded": self.degraded,
                "degrade_reason": self.degrade_reason,
            }
        )


# --------------------------------------------------------------------------
# Bucket registry — one limiter per (endpoint, key[, model]) scope
# --------------------------------------------------------------------------

_LIMITER_REGISTRY: dict[tuple[str, str], _SharedRateLimiter] = {}
_LIMITER_REGISTRY_LOCK = threading.Lock()


def rate_limiter_for(
    base_url: str,
    api_key: str,
    model: str | None = None,
    *,
    limit: int | None = None,
    state_dir: Path | None = None,
    interval: float | None = None,
    scope_by_model: bool | None = None,
) -> _SharedRateLimiter:
    """Return the shared limiter for one quota bucket.

    Two calls with the same endpoint+key share one budget (same quota); a
    different endpoint or a different key gets its own, so independent quotas
    never throttle each other.
    """
    per_model = SCOPE_BY_MODEL if scope_by_model is None else scope_by_model
    name = _bucket_name(base_url, api_key, model if per_model else None)
    directory = state_dir if state_dir is not None else STATE_DIR
    key = (name, str(directory))
    with _LIMITER_REGISTRY_LOCK:
        limiter = _LIMITER_REGISTRY.get(key)
        if limiter is None:
            limiter = _SharedRateLimiter(
                name,
                limit if limit is not None else RPM_LIMIT,
                directory,
                interval=interval,
            )
            _LIMITER_REGISTRY[key] = limiter
        return limiter


_LIMITER = rate_limiter_for(PRIMARY_BASE_URL, PRIMARY_API_KEY, PRIMARY_MODEL)


# --------------------------------------------------------------------------
# Handler
# --------------------------------------------------------------------------


def _build(base_url: str, api_key: str, model: str) -> Callable[[Any], Any]:
    if not api_key:
        raise RuntimeError(
            "model API key is not configured; refusing to send an "
            "unauthenticated request"
        )
    config = GrokProviderConfig(
        base_url=base_url,
        api_key=api_key,
        default_model=model,
        secondary_model=model,
    )
    return GrokStreamingProvider(config).as_model_handler()


def _make_handler() -> Callable[[Any], Any]:
    primary = _build(PRIMARY_BASE_URL, PRIMARY_API_KEY, PRIMARY_MODEL)
    has_secondary = bool(SECONDARY_API_KEY) and (
        SECONDARY_BASE_URL,
        SECONDARY_MODEL,
    ) != (PRIMARY_BASE_URL, PRIMARY_MODEL)
    secondary = (
        _build(SECONDARY_BASE_URL, SECONDARY_API_KEY, SECONDARY_MODEL)
        if has_secondary
        else None
    )

    def _handler(snapshot: Any) -> Any:
        last_exc: BaseException | None = None
        for attempt in range(RETRY_ATTEMPTS + 1):
            _LIMITER.acquire()
            try:
                directive = primary(snapshot)
                _LIMITER.reward()
                return directive
            except BaseException as exc:  # noqa: BLE001
                last_exc = exc
                if _is_rate_limited(exc) and attempt < RETRY_ATTEMPTS:
                    # Same key, same limit — waiting is the only fix.
                    time.sleep(_LIMITER.penalize(attempt))
                    continue
                if _is_transient(exc) and attempt < RETRY_ATTEMPTS:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                break
        if secondary is not None and last_exc is not None:
            try:
                return secondary(snapshot)
            except BaseException:  # noqa: BLE001
                pass
        assert last_exc is not None
        raise last_exc

    _handler.primary_model = PRIMARY_MODEL  # type: ignore[attr-defined]
    _handler.secondary_model = SECONDARY_MODEL  # type: ignore[attr-defined]
    _handler.rate_state = _LIMITER.snapshot  # type: ignore[attr-defined]
    return _handler


_handler_cache: Callable[[Any], Any] | None = None


def __getattr__(name: str) -> Any:
    """Lazily build the resilient handler on first attribute access.

    Building eagerly at import time forced the module to require a live API key
    just to be importable, which breaks offline/edge use and any test that only
    needs the module constants. The handler is now constructed the first time
    ``resilient_handler.handler`` is actually accessed.
    """
    if name == "handler":
        global _handler_cache
        if _handler_cache is None:
            _handler_cache = _make_handler()
        return _handler_cache
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
