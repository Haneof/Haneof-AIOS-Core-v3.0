#!/usr/bin/env python3
"""CORE-SCALE-001 deterministic scale benchmark harness.

This harness is intentionally mechanical:
- no Resident/model execution;
- disposable SQLite World/index files only;
- frozen S10K/S100K/S1M budgets;
- JSON + CSV evidence;
- exact SQL/RSS/latency measurements.

The S10K/S100K index is built through the production WorldSearchIndex rebuild path.
S1M uses a schema-identical mechanical projection loader to keep fixture construction
practical while exercising the same production recall query path over one million
current Claim payloads. The World remains the only truth source.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import gc
import json
import math
import os
import platform
import resource
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

import pydantic

from aios_core.ai_world.cognition import AIWorldCognitionService
from aios_core.context.controller import ContextController, estimate_tokens
from aios_core.query.search import WorldSearchIndex
from aios_core.recommendation.proactive import RecommendationBundle
from aios_core.runtime.turn_runtime import _KnowledgeCutoffStoreView
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.wake.service import WakeBus
from aios_core.contracts.enums import (
    MaintenanceClass,
    SourceClass,
    WakeSource,
    WakeState,
)
from aios_core.contracts.models import Wake
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.time import TemporalExtent

GIB = 1024 ** 3
MIB = 1024 ** 2
CONSTRUCTION_MAIN = os.environ.get(
    "CORE_SCALE_CONSTRUCTION_MAIN",
    "3fe3c924fd855251e8fe195486a072ddf5d86169",
)
CUTOFF = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
DOMAINS = (
    "user_understanding",
    "relationship",
    "self",
    "intent",
    "strategy",
    "cognitive_boundary",
    "personality",
    "calibration",
)
DIMENSIONS = {
    "user_understanding": "dim:ai_user_understanding",
    "relationship": "dim:ai_relationship",
    "self": "dim:ai_self",
    "intent": "dim:ai_intent",
    "strategy": "dim:ai_strategy",
    "cognitive_boundary": "dim:ai_cognitive_boundary",
    "personality": "dim:ai_personality",
    "calibration": "dim:ai_calibration",
}
USER_DOMAINS = {"user_understanding", "relationship", "strategy"}
CORE_DOMAINS = {"user_understanding", "relationship", "self"}
COMMON_STRIDE = 100
REVISION_STRIDE = 50
INACTIVE_STRIDE = 500
PADDING = "-" * 320

TIERS: dict[str, dict[str, Any]] = {
    "S10K": {
        "claims": 10_000,
        "evidence": 500,
        "dependencies": 200,
        "runs": 5,
        "real_index": True,
        "budgets": {
            "core_context_p95_s": 0.75,
            "snapshot_p95_s": 1.5,
            "recall_p95_s": 1.0,
            "rss_delta_bytes": 512 * MIB,
            "recall_sql": 200,
        },
    },
    "S100K": {
        "claims": 100_000,
        "evidence": 5_000,
        "dependencies": 2_000,
        "runs": 5,
        "real_index": True,
        "budgets": {
            "core_context_p95_s": 2.0,
            "snapshot_p95_s": 5.0,
            "recall_p95_s": 2.5,
            "rss_delta_bytes": int(1.5 * GIB),
            "recall_sql": 500,
        },
    },
    "S1M": {
        "claims": 1_000_000,
        "evidence": 0,
        "dependencies": 0,
        "runs": 3,
        "real_index": False,
        "budgets": {
            "core_context_p95_s": 10.0,
            "snapshot_p95_s": 20.0,
            "recall_p95_s": 10.0,
            "rss_peak_bytes": 3 * GIB,
            "recall_sql": 1_000,
            "process_envelope_bytes": 4 * GIB,
        },
    },
}

FROZEN_BUDGET_TEXT = {
    "S10K": [
        "core_context p95 <= 0.75 s",
        "snapshot p95 <= 1.5 s",
        "broad recall_candidates(limit=20) p95 <= 1.0 s",
        "no operation peak-RSS delta > 512 MiB",
        "no fixed top-k search may issue > 200 SQL statements",
    ],
    "S100K": [
        "core_context p95 <= 2.0 s",
        "snapshot p95 <= 5.0 s",
        "broad recall_candidates(limit=20) p95 <= 2.5 s",
        "peak RSS for each measured retrieval <= 1.5 GiB above steady baseline",
        "broad top-k recall SQL statements <= 500",
        "SQL count must not grow linearly with candidate hit count in an N+1 pattern",
    ],
    "S1M": [
        "must complete construction and required retrieval probes under a 4 GiB process/cgroup memory envelope without OOM",
        "core_context p95 <= 10 s",
        "snapshot p95 <= 20 s",
        "broad recall_candidates(limit=20) p95 <= 10 s",
        "retrieval peak RSS <= 3.0 GiB",
        "fixed top-k recall SQL statements <= 1,000",
    ],
}


def rss_bytes() -> int:
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        pass
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


class RSSSampler:
    def __init__(self, interval: float = 0.01) -> None:
        self.interval = interval
        self.start = rss_bytes()
        self.peak = self.start
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            self.peak = max(self.peak, rss_bytes())

    def __enter__(self) -> "RSSSampler":
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.peak = max(self.peak, rss_bytes())
        self._stop.set()
        self._thread.join(timeout=1.0)

    @property
    def delta(self) -> int:
        return max(0, self.peak - self.start)


class SQLCounter:
    def __init__(self) -> None:
        self.count = 0

    def trace(self, statement: str) -> None:
        normalized = statement.lstrip().upper()
        if normalized.startswith(("PRAGMA ", "BEGIN", "COMMIT", "ROLLBACK")):
            return
        self.count += 1


@contextlib.contextmanager
def count_sql(
    store: SQLiteWorldStore,
    index: WorldSearchIndex,
) -> Iterator[SQLCounter]:
    counter = SQLCounter()
    original_store_connection = store._connection
    original_index_connect = index._connect

    @contextlib.contextmanager
    def store_connection() -> Iterator[sqlite3.Connection]:
        with original_store_connection() as conn:
            conn.set_trace_callback(counter.trace)
            yield conn

    def index_connect() -> sqlite3.Connection:
        conn = original_index_connect()
        conn.set_trace_callback(counter.trace)
        return conn

    store._connection = store_connection  # type: ignore[method-assign]
    index._connect = index_connect  # type: ignore[method-assign]
    try:
        yield counter
    finally:
        store._connection = original_store_connection  # type: ignore[method-assign]
        index._connect = original_index_connect  # type: ignore[method-assign]


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(len(ordered) * fraction))
    return float(ordered[rank - 1])


def output_cardinality(value: Any) -> int | None:
    if value is None:
        return None
    hits = getattr(value, "hits", None)
    if isinstance(hits, list):
        return len(hits)
    if isinstance(value, dict):
        return sum(len(v) for v in value.values() if isinstance(v, list))
    if isinstance(value, (list, tuple)):
        return len(value)
    return None


def measure_operation(
    *,
    name: str,
    runs: int,
    store: SQLiteWorldStore,
    index: WorldSearchIndex,
    function: Callable[[], Any],
) -> tuple[dict[str, Any], Any | None]:
    latencies: list[float] = []
    sql_counts: list[int] = []
    rss_deltas: list[int] = []
    rss_peaks: list[int] = []
    cardinalities: list[int | None] = []
    errors: list[str] = []
    sample: Any | None = None

    for _ in range(runs):
        gc.collect()
        try:
            with count_sql(store, index) as sql_counter:
                with RSSSampler() as memory:
                    started = time.monotonic()
                    value = function()
                    elapsed = time.monotonic() - started
            latencies.append(elapsed)
            sql_counts.append(sql_counter.count)
            rss_deltas.append(memory.delta)
            rss_peaks.append(memory.peak)
            cardinalities.append(output_cardinality(value))
            if sample is None:
                sample = value
        except MemoryError:
            errors.append("MemoryError")
            break
        except Exception as exc:  # benchmark must preserve unexpected failures as evidence
            errors.append(f"{type(exc).__name__}: {exc}")
            break

    result = {
        "name": name,
        "requested_runs": runs,
        "successful_runs": len(latencies),
        "errors": errors,
        "latency_seconds": latencies,
        "p50_seconds": percentile(latencies, 0.50),
        "p95_seconds": percentile(latencies, 0.95),
        "sql_counts": sql_counts,
        "sql_max": max(sql_counts) if sql_counts else None,
        "rss_delta_bytes": rss_deltas,
        "rss_delta_max_bytes": max(rss_deltas) if rss_deltas else None,
        "rss_peak_bytes": rss_peaks,
        "rss_peak_max_bytes": max(rss_peaks) if rss_peaks else None,
        "output_cardinality": cardinalities,
    }
    return result, sample


def _cpu_model() -> str | None:
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        return None
    return None


def _read_text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def environment() -> dict[str, Any]:
    memory_limit = _read_text("/sys/fs/cgroup/memory.max")
    swap_limit = _read_text("/sys/fs/cgroup/memory.swap.max")
    if memory_limit is None:
        memory_limit = _read_text("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    if swap_limit is None:
        swap_limit = _read_text("/sys/fs/cgroup/memory/memory.memsw.limit_in_bytes")
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    return {
        "platform": platform.platform(),
        "kernel": platform.release(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "cpu_model": _cpu_model(),
        "cgroup_memory_limit": memory_limit,
        "cgroup_swap_limit": swap_limit,
        "rlimit_as_soft": soft,
        "rlimit_as_hard": hard,
        "python": sys.version.replace("\n", " "),
        "sqlite": sqlite3.sqlite_version,
        "pydantic": pydantic.__version__,
        "pytest": _package_version("pytest"),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_job": os.environ.get("GITHUB_JOB"),
    }


def _package_version(name: str) -> str | None:
    try:
        from importlib.metadata import version

        return version(name)
    except Exception:
        return None


def ensure_s1m_envelope() -> tuple[bool, str | None]:
    target = 4 * GIB
    try:
        _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        new_hard = target if hard in (-1, resource.RLIM_INFINITY) or hard >= target else hard
        if new_hard < target:
            return False, f"existing RLIMIT_AS hard limit {new_hard} is below 4 GiB"
        resource.setrlimit(resource.RLIMIT_AS, (target, new_hard))
        soft_after, _ = resource.getrlimit(resource.RLIMIT_AS)
        if soft_after != target:
            return False, f"RLIMIT_AS soft limit is {soft_after}, expected {target}"
        return True, None
    except (OSError, ValueError) as exc:
        return False, f"could not establish 4 GiB process envelope: {exc}"


def _payload_for_claim(index: int, revision: int) -> dict[str, Any]:
    domain = DOMAINS[index % len(DOMAINS)]
    subject = "user_1" if domain in USER_DOMAINS else "ai_agent_self"
    tags: list[str] = []
    if domain in CORE_DOMAINS and (index // len(DOMAINS)) % 64 == 0:
        tags.append("core_context")
    if index % 7 == 0:
        tags.append("stable")
    common = index % COMMON_STRIDE == 0
    status = "retracted" if revision >= 2 and index % INACTIVE_STRIDE == 0 else "active"
    learned = "2026-02-01T00:00:00+00:00" if revision >= 2 else "2026-01-01T00:00:00+00:00"
    content = (
        f"benchmark {'common ' if common else ''}claim {index} domain {domain} {PADDING}"
    )
    metadata: dict[str, Any] = {
        "ai_world": True,
        "ai_domain": domain,
        "scope_key": f"scope-{index % 11}",
    }
    if tags:
        metadata["tags"] = tags
    return {
        "object_id": f"scale_claim_{index:07d}",
        "revision": revision,
        "object_type": "claim",
        "subject_id": subject,
        "learned_at": learned,
        "recorded_at": learned,
        "created_by": "core-scale-001-fixture",
        "status": status,
        "metadata": metadata,
        "content": content,
        "confidence": 0.75,
        "knowledge_state": "inferred",
        "claim_type": "inference",
        "dimension": DIMENSIONS[domain],
        "unknown_items": [],
        "counter_evidence_set_refs": [],
    }


def _other_payload(kind: str, index: int, claim_count: int) -> dict[str, Any]:
    learned = "2026-01-15T00:00:00+00:00"
    if kind == "evidence_set":
        return {
            "object_id": f"scale_evidence_{index:07d}",
            "revision": 1,
            "object_type": "evidence_set",
            "subject_id": "user_1",
            "learned_at": learned,
            "recorded_at": learned,
            "created_by": "core-scale-001-fixture",
            "status": "active",
            "metadata": {"scale_fixture": True},
            "member_refs": [
                {"object_id": f"scale_claim_{index % claim_count:07d}", "revision": 1}
            ],
        }
    target = index % claim_count
    dependency = (index + 1) % claim_count
    return {
        "object_id": f"scale_dependency_{index:07d}",
        "revision": 1,
        "object_type": "dependency",
        "subject_id": "user_1",
        "learned_at": learned,
        "recorded_at": learned,
        "created_by": "core-scale-001-fixture",
        "status": "active",
        "metadata": {"scale_fixture": True},
        "dependent_ref": {"object_id": f"scale_claim_{target:07d}", "revision": 1},
        "dependency_ref": {"object_id": f"scale_claim_{dependency:07d}", "revision": 1},
        "dependency_type": "scale_fixture_link",
    }


def _insert_world_rows(
    conn: sqlite3.Connection,
    *,
    world_revision: int,
    rows: list[tuple[str, int, str, str, str, str, str]],
    reason: str,
) -> None:
    conn.execute(
        """
        INSERT INTO world_commits(
            world_revision, committed_at, operation_id, session_id, reason, source_class
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            world_revision,
            "2026-09-24T00:00:00+00:00",
            f"core-scale-fixture-{world_revision}",
            None,
            reason,
            SourceClass.AI_COGNITION.value,
        ),
    )
    conn.executemany(
        """
        INSERT INTO object_revisions(
            object_id, revision, object_type, subject_id, world_revision,
            learned_at, recorded_at, payload_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        [
            (object_id, revision, object_type, subject_id, world_revision, learned, recorded, payload)
            for object_id, revision, object_type, subject_id, learned, recorded, payload in rows
        ],
    )


def _row_from_payload(payload: dict[str, Any]) -> tuple[str, int, str, str, str, str, str]:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        str(payload["object_id"]),
        int(payload["revision"]),
        str(payload["object_type"]),
        str(payload["subject_id"]),
        str(payload["learned_at"]),
        str(payload["recorded_at"]),
        raw,
    )


def build_world(
    root: Path,
    *,
    claims: int,
    evidence: int,
    dependencies: int,
) -> tuple[SQLiteWorldStore, dict[str, Any]]:
    world_path = root / "world.sqlite"
    store = SQLiteWorldStore(world_path)
    world_revision = 0
    batch_size = 10_000

    with sqlite3.connect(world_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")

        for start in range(0, claims, batch_size):
            rows = [
                _row_from_payload(_payload_for_claim(i, 1))
                for i in range(start, min(start + batch_size, claims))
            ]
            world_revision += 1
            _insert_world_rows(
                conn,
                world_revision=world_revision,
                rows=rows,
                reason="CORE-SCALE-001 synthetic Claim corpus",
            )
            conn.execute(
                "UPDATE world_meta SET value=? WHERE key='world_revision'",
                (str(world_revision),),
            )
            conn.commit()

        revised = [i for i in range(claims) if i % REVISION_STRIDE == 0]
        for start in range(0, len(revised), batch_size):
            rows = [
                _row_from_payload(_payload_for_claim(i, 2))
                for i in revised[start : start + batch_size]
            ]
            world_revision += 1
            _insert_world_rows(
                conn,
                world_revision=world_revision,
                rows=rows,
                reason="CORE-SCALE-001 representative Claim revisions",
            )
            conn.execute(
                "UPDATE world_meta SET value=? WHERE key='world_revision'",
                (str(world_revision),),
            )
            conn.commit()

        for kind, count in (("evidence_set", evidence), ("dependency", dependencies)):
            for start in range(0, count, batch_size):
                rows = [
                    _row_from_payload(_other_payload(kind, i, claims))
                    for i in range(start, min(start + batch_size, count))
                ]
                if not rows:
                    continue
                world_revision += 1
                _insert_world_rows(
                    conn,
                    world_revision=world_revision,
                    rows=rows,
                    reason=f"CORE-SCALE-001 representative {kind} corpus",
                )
                conn.execute(
                    "UPDATE world_meta SET value=? WHERE key='world_revision'",
                    (str(world_revision),),
                )
                conn.commit()

        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    return store, {
        "world_revision": world_revision,
        "current_claims": claims,
        "claim_revision_rows": claims + math.ceil(claims / REVISION_STRIDE),
        "evidence_objects": evidence,
        "dependency_objects": dependencies,
        "common_current_claims": math.ceil(claims / COMMON_STRIDE),
        "revision_stride": REVISION_STRIDE,
        "inactive_stride_on_revised_claims": INACTIVE_STRIDE,
        "common_stride": COMMON_STRIDE,
        "domain_distribution": "round-robin across 8 AIWorldDomain values",
        "subject_distribution": "user_1 for user_understanding/relationship/strategy; ai_agent_self otherwise",
        "core_context_tags": "eligible domain and floor(index/8) % 64 == 0",
    }


def append_late_revisions(store: SQLiteWorldStore, count: int = 100) -> int:
    world_revision = int(store.current_world_revision()) + 1
    rows: list[tuple[str, int, str, str, str, str, str]] = []
    for i in range(count):
        revision = 3 if i % REVISION_STRIDE == 0 else 2
        payload = _payload_for_claim(i, revision)
        payload["learned_at"] = "2026-03-01T00:00:00+00:00"
        payload["recorded_at"] = "2026-03-01T00:00:00+00:00"
        payload["metadata"] = {**payload["metadata"], "late_revision": True}
        rows.append(_row_from_payload(payload))

    with sqlite3.connect(store.db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        _insert_world_rows(
            conn,
            world_revision=world_revision,
            rows=rows,
            reason="CORE-SCALE-001 stale-index catch-up delta",
        )
        conn.execute(
            "UPDATE world_meta SET value=? WHERE key='world_revision'",
            (str(world_revision),),
        )
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return world_revision


def build_real_index(root: Path, store: SQLiteWorldStore) -> WorldSearchIndex:
    index = WorldSearchIndex(root / "index.sqlite", store=store)
    index.rebuild()
    checkpoint_db(Path(index.db_path))
    return index


def build_s1m_mechanical_index(
    root: Path,
    store: SQLiteWorldStore,
    *,
    claims: int,
) -> WorldSearchIndex:
    index = WorldSearchIndex(root / "index.sqlite", store=store)
    batch_size = 10_000
    with sqlite3.connect(index.db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("DELETE FROM search_postings")
        conn.execute("DELETE FROM search_occurred")
        conn.execute("DELETE FROM search_doc")
        conn.execute("DELETE FROM search_tombstones")
        conn.execute("DELETE FROM search_meta")

        for start in range(0, claims, batch_size):
            occurred_rows: list[tuple[Any, ...]] = []
            doc_rows: list[tuple[Any, ...]] = []
            posting_rows: list[tuple[Any, ...]] = []
            for i in range(start, min(start + batch_size, claims)):
                payload = _payload_for_claim(i, 2 if i % REVISION_STRIDE == 0 else 1)
                oid = str(payload["object_id"])
                rev = int(payload["revision"])
                domain = str(payload["metadata"]["ai_domain"])
                excerpt = str(payload["content"])[:200].lower()
                occurred_rows.append(
                    (oid, rev, payload["subject_id"], "claim", 1767225600000000, 1767225600000000, DIMENSIONS[domain])
                )
                doc_rows.append((oid, rev, excerpt, excerpt))
                posting_rows.append(("benchmark", oid, rev))
                if i % COMMON_STRIDE == 0:
                    posting_rows.append(("common", oid, rev))

                if rev == 2:
                    old = _payload_for_claim(i, 1)
                    old_excerpt = str(old["content"])[:200].lower()
                    occurred_rows.append(
                        (oid, 1, old["subject_id"], "claim", 1767225600000000, 1767225600000000, DIMENSIONS[domain])
                    )
                    doc_rows.append((oid, 1, old_excerpt, old_excerpt))
                    posting_rows.append(("benchmark", oid, 1))
                    if i % COMMON_STRIDE == 0:
                        posting_rows.append(("common", oid, 1))

            conn.executemany(
                """
                INSERT OR REPLACE INTO search_occurred(
                    object_id, revision, subject_id, object_type,
                    occurred_start_us, occurred_end_us, dimension
                ) VALUES(?,?,?,?,?,?,?)
                """,
                occurred_rows,
            )
            conn.executemany(
                "INSERT OR REPLACE INTO search_doc(object_id, revision, haystack, excerpt) VALUES(?,?,?,?)",
                doc_rows,
            )
            conn.executemany(
                "INSERT OR IGNORE INTO search_postings(token, object_id, revision) VALUES(?,?,?)",
                posting_rows,
            )
            conn.commit()

        conn.execute(
            "INSERT OR REPLACE INTO search_meta(key,value) VALUES(?,?)",
            ("search_watermark_world_revision", str(store.current_world_revision())),
        )
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    return index


def checkpoint_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def db_size(path: Path) -> int:
    return sum(
        candidate.stat().st_size
        for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm"))
        if candidate.exists()
    )


def _run_open_probe(world: str, index: str, catch_up: bool) -> int:
    gc.collect()
    with RSSSampler() as memory:
        started = time.monotonic()
        store = SQLiteWorldStore(world)
        projection = WorldSearchIndex(index, store=store)
        if catch_up:
            while projection.catch_up() > 0:
                pass
        elapsed = time.monotonic() - started
    print(
        json.dumps(
            {
                "seconds": elapsed,
                "rss_peak_bytes": memory.peak,
                "rss_delta_bytes": memory.delta,
                "world_revision": store.current_world_revision(),
                "index_watermark": projection.watermark(),
            },
            sort_keys=True,
        )
    )
    return 0


def subprocess_open_probe(
    script: Path,
    world: Path,
    index: Path,
    *,
    catch_up: bool,
    timeout: float,
) -> dict[str, Any]:
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--open-probe-world",
            str(world),
            "--open-probe-index",
            str(index),
            *(["--open-probe-catch-up"] if catch_up else []),
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "error": "open probe failed",
        }
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "error": f"invalid probe JSON: {exc}",
        }


def measure_cold_open(
    *,
    script: Path,
    world: Path,
    index: Path,
    runs: int,
    timeout: float,
) -> dict[str, Any]:
    rows = [
        subprocess_open_probe(script, world, index, catch_up=False, timeout=timeout)
        for _ in range(runs)
    ]
    seconds = [float(row["seconds"]) for row in rows if "seconds" in row]
    return {
        "runs": rows,
        "p50_seconds": percentile(seconds, 0.50),
        "p95_seconds": percentile(seconds, 0.95),
        "max_rss_peak_bytes": max(
            (int(row.get("rss_peak_bytes", 0)) for row in rows), default=0
        ),
        "errors": [row for row in rows if "error" in row],
    }


def measure_stale_catchup(
    *,
    script: Path,
    world: Path,
    stale_template: Path,
    root: Path,
    runs: int,
    timeout: float,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for i in range(runs):
        target = root / f"stale-copy-{i}.sqlite"
        shutil.copy2(stale_template, target)
        rows.append(
            subprocess_open_probe(
                script,
                world,
                target,
                catch_up=True,
                timeout=timeout,
            )
        )
        for suffix in ("", "-wal", "-shm"):
            Path(str(target) + suffix).unlink(missing_ok=True)
    seconds = [float(row["seconds"]) for row in rows if "seconds" in row]
    return {
        "runs": rows,
        "p50_seconds": percentile(seconds, 0.50),
        "p95_seconds": percentile(seconds, 0.95),
        "max_rss_peak_bytes": max(
            (int(row.get("rss_peak_bytes", 0)) for row in rows), default=0
        ),
        "errors": [row for row in rows if "error" in row],
    }


def context_bound(core_context: Any, world_revision: int, index_watermark: int) -> dict[str, Any]:
    if not isinstance(core_context, dict):
        return {"available": False}
    empty_recommendation = RecommendationBundle(
        current_topic=None,
        topic_gate_open=False,
        world_revision=world_revision,
        index_watermark=index_watermark,
        cards=(),
        reason="CORE-SCALE-001 mechanical context bound probe",
    )
    bundle = ContextController().assemble(
        user_input="CORE-SCALE-001 bounded mechanical context probe",
        current_topic=None,
        recommendation=empty_recommendation,
        ai_identity=core_context,
        world_map={},
        recent_turns=(),
        conversation_summaries=(),
        task_context={},
        capability_catalog=(),
    )
    return {
        "available": True,
        "core_context_estimated_tokens": estimate_tokens(core_context),
        "normal_runtime_bundle_estimated_tokens": bundle.estimated_tokens,
        "token_budget": bundle.token_budget,
        "truncated": bundle.truncated,
        "output_cardinality": output_cardinality(core_context),
    }


def save_result(result: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    tmp.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(output)

    csv_path = output.with_suffix(".csv")
    rows: list[dict[str, Any]] = []
    for name, metric in (result.get("measurements") or {}).items():
        if not isinstance(metric, dict):
            continue
        rows.append(
            {
                "name": name,
                "p50_seconds": metric.get("p50_seconds"),
                "p95_seconds": metric.get("p95_seconds"),
                "sql_max": metric.get("sql_max"),
                "rss_delta_max_bytes": metric.get("rss_delta_max_bytes"),
                "rss_peak_max_bytes": metric.get("rss_peak_max_bytes"),
                "successful_runs": metric.get("successful_runs"),
                "requested_runs": metric.get("requested_runs"),
                "errors": " | ".join(metric.get("errors") or []),
            }
        )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "name",
                "p50_seconds",
                "p95_seconds",
                "sql_max",
                "rss_delta_max_bytes",
                "rss_peak_max_bytes",
                "successful_runs",
                "requested_runs",
                "errors",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def _metric_failure(
    failures: list[str],
    metric: dict[str, Any],
    *,
    label: str,
    latency_budget: float,
    rss_delta_budget: int | None = None,
    rss_peak_budget: int | None = None,
    sql_budget: int | None = None,
) -> None:
    if metric.get("successful_runs") != metric.get("requested_runs") or metric.get("errors"):
        failures.append(f"{label}: operation did not complete all requested runs")
        return
    p95 = metric.get("p95_seconds")
    if p95 is None or float(p95) > latency_budget:
        failures.append(f"{label}: p95 {p95!r}s exceeds {latency_budget}s")
    if rss_delta_budget is not None:
        delta = metric.get("rss_delta_max_bytes")
        if delta is None or int(delta) > rss_delta_budget:
            failures.append(
                f"{label}: peak RSS delta {delta!r} exceeds {rss_delta_budget} bytes"
            )
    if rss_peak_budget is not None:
        peak = metric.get("rss_peak_max_bytes")
        if peak is None or int(peak) > rss_peak_budget:
            failures.append(
                f"{label}: peak RSS {peak!r} exceeds {rss_peak_budget} bytes"
            )
    if sql_budget is not None:
        sql_max = metric.get("sql_max")
        if sql_max is None or int(sql_max) > sql_budget:
            failures.append(
                f"{label}: SQL max {sql_max!r} exceeds {sql_budget} statements"
            )


def run_tier(tier: str, output: Path) -> int:
    config = TIERS[tier]
    result: dict[str, Any] = {
        "task": "CORE-SCALE-001",
        "tier": tier,
        "construction_main": CONSTRUCTION_MAIN,
        "tested_commit": os.environ.get("GITHUB_SHA"),
        "frozen_budgets": FROZEN_BUDGET_TEXT[tier],
        "environment": environment(),
        "fixture": {},
        "construction": {},
        "measurements": {},
        "cold_start": {},
        "context_bound": {},
        "hard_failures": [],
        "provider_tokens_cost": "UNKNOWN",
    }
    save_result(result, output)

    if tier == "S1M":
        ok, error = ensure_s1m_envelope()
        result["environment"] = environment()
        result["construction"]["process_4gib_envelope_established"] = ok
        result["construction"]["process_4gib_envelope_error"] = error
        save_result(result, output)
        if not ok:
            result["hard_failures"].append(error or "4 GiB envelope unavailable")
            save_result(result, output)
            return 2

    root = output.parent / f"{tier.lower()}-workspace"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    try:
        with RSSSampler() as construction_memory:
            started = time.monotonic()
            store, fixture = build_world(
                root,
                claims=int(config["claims"]),
                evidence=int(config["evidence"]),
                dependencies=int(config["dependencies"]),
            )
            if bool(config["real_index"]):
                index = build_real_index(root, store)
            else:
                index = build_s1m_mechanical_index(
                    root,
                    store,
                    claims=int(config["claims"]),
                )
            construction_seconds = time.monotonic() - started
    except MemoryError:
        result["construction"].update(
            {
                "completed": False,
                "error": "MemoryError",
                "rss_peak_bytes": rss_bytes(),
            }
        )
        result["hard_failures"].append("fixture construction failed under memory envelope")
        save_result(result, output)
        return 2

    fixture["index_build_mode"] = (
        "production WorldSearchIndex.rebuild/catch_up"
        if bool(config["real_index"])
        else "schema-identical mechanical S1M projection loader; World remains sole truth"
    )
    result["fixture"] = fixture
    result["construction"].update(
        {
            "completed": True,
            "seconds": construction_seconds,
            "rss_start_bytes": construction_memory.start,
            "rss_peak_bytes": construction_memory.peak,
            "rss_delta_bytes": construction_memory.delta,
            "world_db_bytes": db_size(Path(store.db_path)),
            "index_db_bytes": db_size(Path(index.db_path)),
            "world_revision_before_late_delta": store.current_world_revision(),
            "index_watermark_before_late_delta": index.watermark(),
        }
    )
    save_result(result, output)

    script = Path(__file__).resolve()
    if tier == "S100K":
        append_late_revisions(store, 100)
        checkpoint_db(Path(store.db_path))
        checkpoint_db(Path(index.db_path))
        stale_template = root / "index-stale-template.sqlite"
        shutil.copy2(index.db_path, stale_template)
        result["cold_start"]["stale_valid_catchup"] = measure_stale_catchup(
            script=script,
            world=Path(store.db_path),
            stale_template=stale_template,
            root=root,
            runs=5,
            timeout=30.0,
        )
        while index.catch_up() > 0:
            pass
        checkpoint_db(Path(index.db_path))
        result["cold_start"]["current_open"] = measure_cold_open(
            script=script,
            world=Path(store.db_path),
            index=Path(index.db_path),
            runs=5,
            timeout=15.0,
        )
        stale_p95 = result["cold_start"]["stale_valid_catchup"].get("p95_seconds")
        current_p95 = result["cold_start"]["current_open"].get("p95_seconds")
        if stale_p95 is None or float(stale_p95) > 10.0:
            result["hard_failures"].append(
                f"S100K stale valid index catch-up p95 {stale_p95!r}s exceeds 10s"
            )
        if current_p95 is None or float(current_p95) > 3.0:
            result["hard_failures"].append(
                f"S100K current World+index cold open p95 {current_p95!r}s exceeds 3s"
            )
        for group in ("stale_valid_catchup", "current_open"):
            if result["cold_start"][group].get("errors"):
                result["hard_failures"].append(f"S100K {group} had process errors")
        if int(index.watermark()) != int(store.current_world_revision()):
            result["hard_failures"].append("S100K post-catch-up index watermark mismatch")
        save_result(result, output)
    elif tier == "S1M":
        checkpoint_db(Path(store.db_path))
        checkpoint_db(Path(index.db_path))
        result["cold_start"]["current_open"] = measure_cold_open(
            script=script,
            world=Path(store.db_path),
            index=Path(index.db_path),
            runs=3,
            timeout=30.0,
        )
        if result["cold_start"]["current_open"].get("errors"):
            result["hard_failures"].append("S1M current World+index cold open failed")
        cold_p95 = result["cold_start"]["current_open"].get("p95_seconds")
        if cold_p95 is None or float(cold_p95) > 20.0:
            result["hard_failures"].append(
                f"S1M current World+index cold open p95 {cold_p95!r}s exceeds 20s safety window"
            )
        save_result(result, output)

    runs = int(config["runs"])
    runtime_store = _KnowledgeCutoffStoreView(store, CUTOFF)
    cutoff_service = AIWorldCognitionService(
        store=runtime_store,
        index=index,
        user_id="user_1",
    )

    core_metric, core_sample = measure_operation(
        name="core_context_runtime_as_of",
        runs=runs,
        store=store,
        index=index,
        function=lambda: cutoff_service.core_context(per_domain=3),
    )
    result["measurements"]["core_context"] = core_metric
    save_result(result, output)

    snapshot_metric, _snapshot_sample = measure_operation(
        name="snapshot_runtime_as_of",
        runs=runs,
        store=store,
        index=index,
        function=lambda: cutoff_service.snapshot(per_domain=10),
    )
    result["measurements"]["snapshot"] = snapshot_metric
    save_result(result, output)

    recall_metric, _recall_sample = measure_operation(
        name="recall_candidates_runtime_as_of_limit20",
        runs=runs,
        store=store,
        index=index,
        function=lambda: index.recall_candidates(
            "common",
            subject="user_1",
            as_of=CUTOFF,
            limit=20,
        ),
    )
    result["measurements"]["recall_candidates"] = recall_metric
    save_result(result, output)

    # One current-view diagnostic keeps the historical #112 risk class honest
    # without using the historical #112 numbers as present evidence.
    current_service = AIWorldCognitionService(store=store, index=index, user_id="user_1")
    current_core_metric, _ = measure_operation(
        name="core_context_current_view_diagnostic",
        runs=1,
        store=store,
        index=index,
        function=lambda: current_service.core_context(per_domain=3),
    )
    current_recall_metric, _ = measure_operation(
        name="recall_candidates_current_view_diagnostic",
        runs=1,
        store=store,
        index=index,
        function=lambda: index.recall_candidates(
            "common",
            subject="user_1",
            limit=20,
        ),
    )
    result["measurements"]["diagnostic_current_core_context"] = current_core_metric
    result["measurements"]["diagnostic_current_recall"] = current_recall_metric

    result["context_bound"] = context_bound(
        core_sample,
        int(store.current_world_revision()),
        int(index.watermark()),
    )
    save_result(result, output)

    budgets = config["budgets"]
    rss_delta_budget = budgets.get("rss_delta_bytes")
    rss_peak_budget = budgets.get("rss_peak_bytes")
    _metric_failure(
        result["hard_failures"],
        core_metric,
        label=f"{tier} core_context",
        latency_budget=float(budgets["core_context_p95_s"]),
        rss_delta_budget=rss_delta_budget,
        rss_peak_budget=rss_peak_budget,
    )
    _metric_failure(
        result["hard_failures"],
        snapshot_metric,
        label=f"{tier} snapshot",
        latency_budget=float(budgets["snapshot_p95_s"]),
        rss_delta_budget=rss_delta_budget,
        rss_peak_budget=rss_peak_budget,
    )
    _metric_failure(
        result["hard_failures"],
        recall_metric,
        label=f"{tier} recall_candidates",
        latency_budget=float(budgets["recall_p95_s"]),
        rss_delta_budget=rss_delta_budget,
        rss_peak_budget=rss_peak_budget,
        sql_budget=int(budgets["recall_sql"]),
    )

    context = result["context_bound"]
    if context.get("available"):
        if int(context["normal_runtime_bundle_estimated_tokens"]) > int(context["token_budget"]):
            result["hard_failures"].append(
                f"{tier} model-visible context exceeds existing token budget"
            )
    else:
        result["hard_failures"].append(
            f"{tier} context bound could not be measured because core_context failed"
        )

    if tier == "S1M":
        envelope = int(budgets["process_envelope_bytes"])
        if int(resource.getrlimit(resource.RLIMIT_AS)[0]) != envelope:
            result["hard_failures"].append("S1M 4 GiB process envelope drifted during run")
        if not result["construction"].get("completed"):
            result["hard_failures"].append("S1M construction did not complete")

    result["world_revision_after_measurement"] = store.current_world_revision()
    result["index_watermark_after_measurement"] = index.watermark()
    result["status"] = "PASS" if not result["hard_failures"] else "FAIL"
    save_result(result, output)

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not result["hard_failures"] else 2


def make_wake(index: int, first_hit: datetime) -> Wake:
    priority = index % 101
    return Wake(
        object_id=f"scale_wake_{index:04d}",
        subject_id="user_1",
        revision=1,
        learned_at=first_hit,
        recorded_at=first_hit,
        created_by="core-scale-001-backlog",
        status=WakeState.NEW.value,
        metadata={"scale_fixture": True},
        wake_source=WakeSource.TASK_DUE,
        wake_state=WakeState.NEW,
        rule_id="core-scale-001-due",
        first_hit_at=first_hit,
        last_hit_at=first_hit,
        hit_count=1,
        evidence_refs=[],
        priority=priority,
        dedupe_key=f"scale-backlog-{index:04d}",
        occurred=TemporalExtent.point(first_hit),
    )


def run_backlog(output: Path) -> int:
    result: dict[str, Any] = {
        "task": "CORE-SCALE-001",
        "kind": "due_backlog",
        "construction_main": CONSTRUCTION_MAIN,
        "tested_commit": os.environ.get("GITHUB_SHA"),
        "environment": environment(),
        "hard_budgets": [
            "due discovery p95 <= 2 s at 1,000 due items",
            "bounded 100-item mechanical batch orchestration overhead <= 5 s excluding intentional model-handler sleep",
            "no loss, duplication, or starvation caused by pagination/batching",
            "backlog must remain durable across restart",
        ],
        "hard_failures": [],
        "provider_tokens_cost": "UNKNOWN",
    }
    root = output.parent / "backlog-workspace"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    store = SQLiteWorldStore(root / "world.sqlite")
    base = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)
    wakes = [make_wake(i, base) for i in range(1000)]
    store.commit(
        wakes,
        OperationRequest(
            operation_name="core_scale.backlog_fixture",
            arguments={"count": len(wakes)},
            expected_world_revision=0,
            reason="CORE-SCALE-001 deterministic due backlog",
            idempotency_key="core-scale-backlog-fixture-v1",
            source_class=SourceClass.MAINTENANCE,
            maintenance_class=MaintenanceClass.WAKE_SCHEDULER,
        ),
    )
    bus = WakeBus(store=store, index=None, subject_id="user_1")

    # A tiny empty projection exists only so the common measurement helper can count
    # World SQL uniformly. It is not a second truth store.
    measurement_index = WorldSearchIndex(root / "empty-index.sqlite", store=store)
    discovery, discovery_sample = measure_operation(
        name="pending_wakes_discovery",
        runs=5,
        store=store,
        index=measurement_index,
        function=bus.pending_wakes,
    )
    result["discovery"] = discovery
    if discovery.get("p95_seconds") is None or float(discovery["p95_seconds"]) > 2.0:
        result["hard_failures"].append(
            f"due discovery p95 {discovery.get('p95_seconds')!r}s exceeds 2s"
        )
    if discovery.get("successful_runs") != 5:
        result["hard_failures"].append("due discovery did not complete all runs")
    if not isinstance(discovery_sample, tuple) or len(discovery_sample) != 1000:
        result["hard_failures"].append("due discovery did not return exactly 1,000 Wakes")

    expected_order = tuple(
        wake.object_id
        for wake in sorted(
            wakes,
            key=lambda wake: (-wake.priority, wake.first_hit_at, wake.object_id),
        )
    )
    actual_order = tuple(wake.object_id for wake in (discovery_sample or ()))
    result["initial_order_matches_contract"] = actual_order == expected_order
    if actual_order != expected_order:
        result["hard_failures"].append("due backlog ordering mismatch")

    first_hundred = list((discovery_sample or ())[:100])
    with RSSSampler() as memory:
        started = time.monotonic()
        for wake in first_hundred:
            claimed = bus.claim(
                wake.object_id,
                started_at=base,
            )
            bus.complete(
                wake.object_id,
                completed_at=base,
                termination_reason="mechanical_scale_probe",
                model_rounds=0,
                capability_names=(),
                delivery_allowed=False,
                step0_state="background",
            )
            if claimed.state != WakeState.RUNNING.value:
                result["hard_failures"].append(
                    f"Wake {wake.object_id} did not enter RUNNING"
                )
        batch_seconds = time.monotonic() - started
    result["batch_100"] = {
        "seconds": batch_seconds,
        "rss_peak_bytes": memory.peak,
        "rss_delta_bytes": memory.delta,
        "processed_ids": [wake.object_id for wake in first_hundred],
    }
    if batch_seconds > 5.0:
        result["hard_failures"].append(
            f"100-item mechanical batch {batch_seconds:.6f}s exceeds 5s"
        )

    remaining = bus.pending_wakes()
    result["remaining_after_batch"] = len(remaining)
    if len(remaining) != 900:
        result["hard_failures"].append(
            f"remaining backlog {len(remaining)} != expected 900"
        )
    if len({wake.object_id for wake in remaining}) != len(remaining):
        result["hard_failures"].append("remaining backlog contains duplicate Wake ids")

    restarted_store = SQLiteWorldStore(store.db_path)
    restarted_bus = WakeBus(store=restarted_store, index=None, subject_id="user_1")
    restarted = restarted_bus.pending_wakes()
    result["remaining_after_restart"] = len(restarted)
    result["restart_order_matches"] = (
        tuple(w.object_id for w in restarted)
        == tuple(w.object_id for w in remaining)
    )
    if len(restarted) != 900 or not result["restart_order_matches"]:
        result["hard_failures"].append("backlog was not durably preserved across restart")

    result["status"] = "PASS" if not result["hard_failures"] else "FAIL"
    save_result(result, output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not result["hard_failures"] else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", choices=sorted(TIERS))
    parser.add_argument("--backlog", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--open-probe-world")
    parser.add_argument("--open-probe-index")
    parser.add_argument("--open-probe-catch-up", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.open_probe_world or args.open_probe_index:
        if not args.open_probe_world or not args.open_probe_index:
            raise SystemExit("both --open-probe-world and --open-probe-index are required")
        return _run_open_probe(
            args.open_probe_world,
            args.open_probe_index,
            bool(args.open_probe_catch_up),
        )

    if args.output is None:
        raise SystemExit("--output is required")
    if args.backlog:
        return run_backlog(args.output)
    if args.tier is None:
        raise SystemExit("--tier is required unless --backlog is used")
    return run_tier(args.tier, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
