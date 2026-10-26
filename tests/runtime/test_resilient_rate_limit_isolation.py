"""Rate-limiter bucket isolation for ``resilient_handler`` (Window: RPM fix).

The paced budget used to be one global bucket for every endpoint/key/model, so
a burst against one model delayed unrelated models and independent endpoints.
These tests pin the new scope: one bucket per (endpoint, API key), optionally
per model, with hashed names and survivable lock failures.

All tests inject a tiny ``interval`` (test-only constructor argument); the
production pace stays ``60 / AIOS_RPM_LIMIT``.
"""

from __future__ import annotations

import threading
import time

import pytest

from aios_core.runtime import resilient_handler as rh

URL_A = "https://api.provider-a.example/v1"
URL_B = "https://api.provider-b.example/v1"
KEY_A = "sk-PROVIDER-A-SECRET-0001"
KEY_B = "sk-PROVIDER-B-SECRET-0002"

# Small enough to keep the suite fast, large enough to measure above noise.
TICK = 0.05


def _limiter(tmp_path, url: str, key: str, model: str | None = None, **kw):
    return rh.rate_limiter_for(url, key, model, state_dir=tmp_path, interval=TICK, **kw)


def test_different_endpoints_are_isolated(tmp_path):
    """A burst on one endpoint must not delay the first call on another."""
    a = _limiter(tmp_path, URL_A, KEY_A, "model-a")
    b = _limiter(tmp_path, URL_B, KEY_B, "model-b")
    assert a is not b and a.path != b.path

    for _ in range(4):  # ~3 ticks of waiting on A
        a.acquire()
    assert a.acquire() >= TICK * 0.5  # A is genuinely pacing

    started = time.perf_counter()
    waited = b.acquire()
    elapsed = time.perf_counter() - started
    assert waited < TICK * 0.2, waited
    assert elapsed < TICK * 0.5, elapsed


def test_same_endpoint_different_keys_are_isolated(tmp_path):
    a = _limiter(tmp_path, URL_A, KEY_A)
    b = _limiter(tmp_path, URL_A, KEY_B)
    assert a.path != b.path
    a.acquire()
    assert b.acquire() < TICK * 0.2


def test_same_endpoint_and_key_share_one_budget(tmp_path):
    """Model switches on one key+endpoint draw on the same quota -> shared."""
    a = _limiter(tmp_path, URL_A, KEY_A, "model-a")
    b = _limiter(tmp_path, URL_A, KEY_A, "model-b")
    assert a is b and a.path == b.path

    assert a.acquire() < TICK * 0.2  # first call is free
    waited = b.acquire()  # second call shares the tick
    assert waited >= TICK * 0.5, waited


def test_model_scope_is_opt_in(tmp_path):
    split_a = rh.rate_limiter_for(
        URL_A, KEY_A, "model-a", state_dir=tmp_path, interval=TICK, scope_by_model=True
    )
    split_b = rh.rate_limiter_for(
        URL_A, KEY_A, "model-b", state_dir=tmp_path, interval=TICK, scope_by_model=True
    )
    assert split_a is not split_b and split_a.path != split_b.path


def test_state_files_never_contain_the_api_key(tmp_path):
    secret = "sk-PLAINTEXT-MUST-NOT-LEAK-9f3c2a"
    limiter = rh.rate_limiter_for(
        URL_A, secret, "model-a", state_dir=tmp_path, interval=0.01
    )
    limiter.acquire()
    limiter.penalize(0)
    limiter.reward()
    snapshot = limiter.snapshot()

    written = list(tmp_path.iterdir())
    assert written, "expected a state file to be created"
    for path in written:
        assert secret not in path.name
        assert secret not in path.read_text("utf-8", errors="replace")
    assert secret not in str(limiter.path)
    assert secret not in str(snapshot)
    assert rh._fingerprint(secret) in limiter.path.name  # hashed, still stable


def test_unwritable_state_dir_degrades_without_crashing(tmp_path):
    blocked = tmp_path / "blocked"
    blocked.write_text("regular file, not a directory")

    limiter = rh.rate_limiter_for(
        URL_A, KEY_A, "model-a", state_dir=blocked / "state", interval=TICK
    )
    assert limiter.degraded is True
    assert limiter.acquire() == pytest.approx(0.0, abs=0.05)  # no raise
    assert limiter.acquire() >= TICK * 0.5  # still paces, in memory

    snapshot = limiter.snapshot()
    assert snapshot["degraded"] is True
    assert snapshot["degrade_reason"]


def test_flock_failure_degrades_without_crashing(tmp_path, monkeypatch):
    limiter = _limiter(tmp_path, URL_A, KEY_A, "model-a")

    def _boom(fd: int, op: int) -> None:
        raise OSError("ENOLCK: advisory locking unavailable")

    monkeypatch.setattr(rh.fcntl, "flock", _boom)

    assert limiter.acquire() < TICK * 0.2  # must not raise
    assert limiter.acquire() >= TICK * 0.5  # pacing survives, no cross-process lock
    snapshot = limiter.snapshot()
    assert snapshot["degraded"] is True
    assert "lock_unavailable" in snapshot["degrade_reason"]


def test_concurrent_acquires_serialize_without_deadlock(tmp_path):
    limiter = _limiter(tmp_path, URL_A, KEY_A, "model-a")
    waited: list[float] = []
    guard = threading.Lock()
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            for _ in range(3):
                value = limiter.acquire()
                with guard:
                    waited.append(value)
        except BaseException as exc:  # noqa: BLE001
            with guard:
                errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    started = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)
    elapsed = time.perf_counter() - started

    assert not errors, errors
    assert all(not t.is_alive() for t in threads), "deadlock: thread still running"
    assert len(waited) == 12
    # 12 slots on one bucket: 11 of them must have waited about one tick.
    assert elapsed >= TICK * 8
    assert sum(1 for w in waited if w >= TICK * 0.5) >= 10


def test_primary_limiter_still_backs_resilient_text():
    """``resilient_text`` imports ``_LIMITER``: keep it, bound to the primary."""
    assert rh._LIMITER is rh.rate_limiter_for(
        rh.PRIMARY_BASE_URL, rh.PRIMARY_API_KEY, rh.PRIMARY_MODEL
    )
    assert rh._LIMITER.interval == pytest.approx(60.0 / rh.RPM_LIMIT)


def test_p0_safety_path_is_never_queued_by_the_limiter():
    """Iron Rule 3: P0 goes straight to the edge SLM, no limiter in the path."""
    from aios_core.contracts.enums import WakePriority
    from aios_core.runtime.edge_model_scheduler import MultiModelEdgeScheduler

    cloud_calls: list[float] = []

    def _cloud(prompt: str, context: dict) -> str:
        cloud_calls.append(time.perf_counter())
        return "cloud"

    scheduler = MultiModelEdgeScheduler(cloud_llm_executor=_cloud)
    result = scheduler.dispatch("severe fall", priority=WakePriority.P0_CRITICAL_SAFETY)

    assert result.emergency_bypassed is True
    assert not cloud_calls
    assert result.latency_ms < 50.0, result.latency_ms
