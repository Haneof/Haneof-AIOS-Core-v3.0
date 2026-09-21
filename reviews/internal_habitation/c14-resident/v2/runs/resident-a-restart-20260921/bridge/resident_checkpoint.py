#!/usr/bin/env python3
"""C14 Resident A — thin synchronous checkpoint bridge (test-side, NON-SEMANTIC).

Contract basis: reviews/internal_habitation/c14-resident/v2/release/RESIDENT_A_RUN_CONTRACT.md §11.

This bridge may ONLY:
  * instantiate the real AIOS SQLiteWorldStore / WorldSearchIndex / FusedTurnRuntime;
  * serialize the exact RuntimeSnapshot or DimensionSummaryInput it is handed;
  * pause;
  * accept the decision the Resident model personally writes to a file;
  * feed that exact decision back into the real runtime;
  * execute exactly the capability calls the Resident chose;
  * persist capability results and audit receipts.

It contains NO semantic rule: no keyword mapping, no importance scoring, no search-target
selection, no Claim text, no Summary text, no revise/retract/silence decision. Every value
that is not a mechanical AIOS fact in the output below was written by the Resident model.

Usage
-----
  resident_checkpoint.py init-world   --world-db DB --session-dir DIR
  resident_checkpoint.py ingest-hooks --world-db DB --session-dir DIR --ingest-ref OBJ@REV
  resident_checkpoint.py status       --world-db DB --session-dir DIR [--release-state S]
  resident_checkpoint.py process-due  --world-db DB --session-dir DIR --now ISO
                                      [--timeout 1800] [--max-wakes 12] [--background-advance 61]
  resident_checkpoint.py handoff      --world-db DB --session-dir DIR --release-state S
                                      [--out DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

UTC = timezone.utc


def _bootstrap_repo_src() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "src"
        if (candidate / "aios_core").is_dir():
            sys.path.insert(0, str(candidate))
            return candidate.parent
    raise RuntimeError("repository src/aios_core not found")


REPO_ROOT = _bootstrap_repo_src()

from aios_core.ai_world import AI_SELF_SUBJECT_ID  # noqa: E402
from aios_core.contracts.enums import ObjectType  # noqa: E402
from aios_core.contracts.refs import ObjectRef  # noqa: E402
from aios_core.query.search import WorldSearchIndex  # noqa: E402
from aios_core.runtime.capabilities import CapabilityCall  # noqa: E402
from aios_core.runtime.cognitive_runtime import (  # noqa: E402
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime  # noqa: E402
from aios_core.storage.sqlite_store import SQLiteWorldStore  # noqa: E402
from aios_core.summaries.dimension_summary import DimensionSummaryInput  # noqa: E402
from aios_core.wake import Step0GateInput  # noqa: E402

SUBJECT_ID = "user_1"
DEFAULT_TIMEOUT = 1800.0


# --------------------------------------------------------------------------------------
# mechanical helpers (no semantics)
# --------------------------------------------------------------------------------------


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def _slug(key: str) -> str:
    cleaned = "".join(char if (char.isalnum() or char in "-_.") else "_" for char in key)
    cleaned = cleaned.strip("_")[:96]
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:8]
    return f"{cleaned or 'unit'}-{digest}"


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: _jsonable(getattr(value, name))
            for name in value.__dataclass_fields__  # type: ignore[attr-defined]
        }
    return value


class Audit:
    def __init__(self, session_dir: Path) -> None:
        self.path = session_dir / "audit" / "session.log"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, event: str, **fields: Any) -> None:
        payload = {
            "at_utc": datetime.now(UTC).isoformat(),
            "event": event,
            **_jsonable(fields),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        printable = dict(fields)
        stdout_summary = printable.pop("stdout_summary", None)
        if stdout_summary is not None:
            printable = {"summary": stdout_summary}
        readable = " ".join(
            f"{key}={json.dumps(value, ensure_ascii=False)}"
            for key, value in printable.items()
            if key not in {"cockpit", "capability_history"}
        )
        print(f"[bridge] {event} {readable}".rstrip(), flush=True)


class CheckpointAbort(RuntimeError):
    """Raised when the Resident model did not answer a checkpoint in time."""


# --------------------------------------------------------------------------------------
# checkpoint rendezvous (transports decisions; decides nothing)
# --------------------------------------------------------------------------------------


class RendezvousModelHandler:
    """ModelHandler that publishes a snapshot and waits for a Resident-written decision."""

    def __init__(self, session_dir: Path, audit: Audit, timeout: float) -> None:
        self.session_dir = session_dir
        self.audit = audit
        self.timeout = float(timeout)
        self.unit_key: str | None = None
        self.rounds_seen: dict[str, int] = {}

    def begin_unit(self, unit_key: str) -> None:
        self.unit_key = unit_key

    def _paths(self, round_index: int) -> tuple[Path, Path, Path]:
        unit = _slug(self.unit_key or "unscoped")
        self.rounds_seen[unit] = max(self.rounds_seen.get(unit, -1), round_index)
        snapshot_dir = self.session_dir / "checkpoints" / "snapshots" / unit
        decision = (
            self.session_dir
            / "checkpoints"
            / "decisions"
            / unit
            / f"round-{round_index}.json"
        )
        return snapshot_dir, decision, self.session_dir / "checkpoints" / "results" / unit

    def _render_markdown(self, unit_key: str, snapshot_payload: Mapping[str, Any]) -> str:
        lines = [
            f"# RuntimeSnapshot — {unit_key}",
            "",
            f"- round_index: {snapshot_payload['round_index']}",
            f"- remaining_tool_rounds: {snapshot_payload['remaining_tool_rounds']}",
            f"- wake_reason: {snapshot_payload['wake_reason']}",
            "",
            "## wake_input",
            "",
            "```text",
            str(snapshot_payload["user_input"]),
            "```",
            "",
            "## cockpit",
            "",
            "```json",
            json.dumps(snapshot_payload["cockpit"], ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
            "## capability_history",
            "",
            "```json",
            json.dumps(
                snapshot_payload["capability_history"],
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            "```",
            "",
            "## capability_catalog",
            "",
            "```json",
            json.dumps(
                snapshot_payload["capability_catalog"],
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            "```",
            "",
        ]
        return "\n".join(lines)

    def __call__(self, snapshot: Any) -> ModelDirective:
        unit_key = self.unit_key or f"unscoped-{snapshot.wake_reason}"
        round_index = int(snapshot.round_index)
        snapshot_dir, decision_path, results_dir = self._paths(round_index)
        payload = {
            "unit_key": unit_key,
            "wake_reason": snapshot.wake_reason,
            "user_input": snapshot.user_input,
            "round_index": round_index,
            "remaining_tool_rounds": int(snapshot.remaining_tool_rounds),
            "cockpit": _jsonable(dict(snapshot.cockpit)),
            "capability_catalog": _jsonable(snapshot.capability_catalog),
            "capability_history": _jsonable(snapshot.capability_history),
        }
        _atomic_text(
            snapshot_dir / f"round-{round_index}.json",
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        _atomic_text(
            snapshot_dir / f"round-{round_index}.md",
            self._render_markdown(unit_key, payload),
        )
        self.audit(
            "AWAITING_DECISION",
            unit=unit_key,
            round=round_index,
            snapshot=str(snapshot_dir / f"round-{round_index}.json"),
            expected_decision=str(decision_path),
        )
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if decision_path.exists():
                break
            time.sleep(1.0)
        else:
            raise CheckpointAbort(
                f"no Resident decision for unit={unit_key} round={round_index} "
                f"within {self.timeout}s"
            )

        raw = json.loads(decision_path.read_text(encoding="utf-8"))
        self.audit(
            "DECISION_RECEIVED",
            unit=unit_key,
            round=round_index,
            decision_kind=(
                "capability_calls"
                if raw.get("capability_calls")
                else ("response" if raw.get("response") is not None else "silence")
            ),
            decision_path=str(decision_path),
        )
        directive = self._directive(raw)
        if snapshot.capability_history:
            _atomic_text(
                results_dir / f"round-{round_index}.json",
                json.dumps(
                    {
                        "unit_key": unit_key,
                        "round_index": round_index,
                        "directive": raw,
                        "capability_history": _jsonable(snapshot.capability_history),
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
            )
        return directive

    @staticmethod
    def _directive(raw: Mapping[str, Any]) -> ModelDirective:
        if not isinstance(raw, Mapping):
            raise ValueError("decision file must contain a JSON object")
        calls = tuple(
            CapabilityCall(
                name=str(item["name"]),
                arguments=dict(item.get("arguments") or {}),
                call_id=(None if item.get("call_id") is None else str(item["call_id"])),
            )
            for item in (raw.get("capability_calls") or ())
        )
        usage = None
        if raw.get("usage") is not None:
            usage = ModelUsage(**dict(raw["usage"]))
        provenance = None
        if raw.get("provenance") is not None:
            provenance = ModelCallProvenance(**dict(raw["provenance"]))
        return ModelDirective(
            capability_calls=calls,
            response=(None if raw.get("response") is None else str(raw["response"])),
            silence=bool(raw.get("silence", False)),
            usage=usage,
            provenance=provenance,
        )


class RendezvousSummaryHandler:
    """DimensionSummary handler that publishes the exact input and waits for Resident text."""

    def __init__(self, session_dir: Path, audit: Audit, timeout: float) -> None:
        self.session_dir = session_dir
        self.audit = audit
        self.timeout = float(timeout)

    @staticmethod
    def _key(prepared: DimensionSummaryInput) -> str:
        return (
            f"{prepared.dimension}__{prepared.granularity}"
            f"__{prepared.window_start.isoformat()}__{prepared.window_end.isoformat()}"
        )

    def __call__(self, prepared: DimensionSummaryInput) -> str:
        key = self._key(prepared)
        slug = _slug(key)
        target = self.session_dir / "checkpoints" / "summaries" / slug
        text_path = target / "summary.txt"
        input_path = target / "INPUT.json"
        payload = {
            "summary_key": key,
            "dimension": prepared.dimension,
            "granularity": prepared.granularity,
            "window_start": prepared.window_start.isoformat(),
            "window_end": prepared.window_end.isoformat(),
            "source_world_revision": prepared.source_world_revision,
            "truncated": prepared.truncated,
            "sources": _jsonable(prepared.sources),
        }
        _atomic_text(
            input_path,
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        lines = [
            f"# DimensionSummaryInput — {key}",
            "",
            f"- dimension: {prepared.dimension}",
            f"- granularity: {prepared.granularity}",
            f"- window: {prepared.window_start.isoformat()} .. {prepared.window_end.isoformat()}",
            f"- source_world_revision: {prepared.source_world_revision}",
            f"- source_count: {len(prepared.sources)}",
            f"- truncated: {prepared.truncated}",
            "",
            "## sources (exact pinned material)",
            "",
        ]
        for index, source in enumerate(payload["sources"], start=1):
            lines.extend(
                [
                    f"### {index}. {source['object_id']}@{source['revision']} "
                    f"({source['object_type']})",
                    "",
                    f"- occurred_at: {source.get('occurred_at')}",
                    f"- metadata: {json.dumps(source.get('metadata') or {}, ensure_ascii=False, sort_keys=True)}",
                    "",
                    "```text",
                    str(source.get("text") or ""),
                    "```",
                    "",
                ]
            )
        _atomic_text(target / "INPUT.md", "\n".join(lines))
        self.audit(
            "AWAITING_SUMMARY_TEXT",
            summary_key=key,
            dimension=prepared.dimension,
            granularity=prepared.granularity,
            window=f"{prepared.window_start.isoformat()}..{prepared.window_end.isoformat()}",
            source_count=len(prepared.sources),
            input=str(input_path),
            expected_text=str(text_path),
        )
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if text_path.exists():
                break
            time.sleep(1.0)
        else:
            raise CheckpointAbort(f"no Resident summary text for {key} within {self.timeout}s")
        text = text_path.read_text(encoding="utf-8").strip()
        if not text:
            raise CheckpointAbort(f"Resident summary text for {key} is blank")
        self.audit(
            "SUMMARY_TEXT_RECEIVED",
            summary_key=key,
            chars=len(text),
            text_path=str(text_path),
        )
        return text


# --------------------------------------------------------------------------------------
# runtime assembly
# --------------------------------------------------------------------------------------


class Session:
    def __init__(self, world_db: Path, session_dir: Path, timeout: float) -> None:
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.world_db = Path(world_db)
        self.audit = Audit(self.session_dir)
        self.store = SQLiteWorldStore(self.world_db)
        self.index = WorldSearchIndex(self.world_db, store=self.store)
        self.handler = RendezvousModelHandler(self.session_dir, self.audit, timeout)
        self.summary_handler = RendezvousSummaryHandler(self.session_dir, self.audit, timeout)
        self.runtime = FusedTurnRuntime(
            store=self.store,
            index=self.index,
            model_handler=self.handler,
            subject_id=SUBJECT_ID,
            dimension_summary_handler=self.summary_handler,
        )


def _refs_of(store: SQLiteWorldStore, object_type: ObjectType, subject_id: str | None) -> list[dict]:
    out: list[dict] = []
    for payload in store.list_payloads(
        object_type=object_type,
        subject_id=subject_id,
    ):
        out.append(
            {
                "object_id": payload.get("object_id"),
                "revision": payload.get("revision"),
                "status": payload.get("summary_status")
                or payload.get("claim_status")
                or payload.get("lifecycle")
                or payload.get("wake_state"),
                "recorded_at": payload.get("recorded_at"),
                "content": (
                    str(payload.get("content"))[:400]
                    if payload.get("content") is not None
                    else None
                ),
            }
        )
    out.sort(key=lambda item: (str(item.get("recorded_at") or ""), str(item.get("object_id"))))
    return out


def _status_payload(session: Session) -> dict[str, Any]:
    store = session.store
    runtime = session.runtime
    wakes = []
    for payload in store.list_payloads(object_type=ObjectType.WAKE, subject_id=SUBJECT_ID):
        metadata = payload.get("metadata") or {}
        wakes.append(
            {
                "wake_id": payload.get("object_id"),
                "revision": payload.get("revision"),
                "state": payload.get("wake_state"),
                "wake_source": payload.get("wake_source"),
                "priority": payload.get("priority"),
                "first_hit_at": payload.get("first_hit_at"),
                "last_hit_at": payload.get("last_hit_at"),
                "hit_count": payload.get("hit_count"),
                "dedupe_key": payload.get("dedupe_key"),
                "summary_ref": metadata.get("summary_ref"),
                "attention_bundle": metadata.get("attention_bundle"),
                "termination_reason": metadata.get("termination_reason"),
                "runtime_incomplete_attempts": metadata.get("runtime_incomplete_attempts"),
            }
        )
    wakes.sort(key=lambda item: str(item.get("first_hit_at") or ""))
    return {
        "world_db": str(session.world_db),
        "world_revision": int(store.current_world_revision()),
        "index_watermark": int(session.index.watermark()),
        "index_lag": int(session.index.lag()),
        "pending_wakes": len(runtime.wake_bus.pending_wakes()),
        "wakes": wakes,
        "summaries": _refs_of(store, ObjectType.SUMMARY, SUBJECT_ID),
        "claims_user": _refs_of(store, ObjectType.CLAIM, SUBJECT_ID),
        "claims_ai_self": _refs_of(store, ObjectType.CLAIM, AI_SELF_SUBJECT_ID),
        "observations": _refs_of(store, ObjectType.OBSERVATION, SUBJECT_ID),
        "tasks": _refs_of(store, ObjectType.TASK, SUBJECT_ID),
        "goals": _refs_of(store, ObjectType.GOAL, SUBJECT_ID),
        "events": _refs_of(store, ObjectType.EVENT, SUBJECT_ID),
        "entities": _refs_of(store, ObjectType.ENTITY, SUBJECT_ID),
        "dimensions": _refs_of(store, ObjectType.DIMENSION_DEFINITION, SUBJECT_ID),
        "policies": _refs_of(store, ObjectType.COGNITIVE_POLICY, SUBJECT_ID),
        "operation_experiences": _refs_of(store, ObjectType.OPERATION_EXPERIENCE, SUBJECT_ID),
    }


# --------------------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------------------


def cmd_init_world(args: argparse.Namespace) -> None:
    session = Session(Path(args.world_db), Path(args.session_dir), DEFAULT_TIMEOUT)
    session.index.catch_up()
    payload = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "world_db": str(session.world_db),
        "world_revision": int(session.store.current_world_revision()),
        "index_watermark": int(session.index.watermark()),
        "subject_id": SUBJECT_ID,
        "repository_root": str(REPO_ROOT),
    }
    _atomic_text(
        Path(args.session_dir) / "receipts" / "world-init.json",
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    session.audit("WORLD_INITIALIZED", **payload)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def cmd_ingest_hooks(args: argparse.Namespace) -> None:
    session = Session(Path(args.world_db), Path(args.session_dir), DEFAULT_TIMEOUT)
    object_id, _, revision_text = str(args.ingest_ref).partition("@")
    ref = ObjectRef(object_id=object_id, revision=int(revision_text))
    receipts = session.runtime.attention_watches.evaluate_observation(ref)
    session.index.catch_up()
    payload = {
        "ingest_ref": f"{object_id}@{revision_text}",
        "watch_receipts": _jsonable(receipts),
        "world_revision": int(session.store.current_world_revision()),
        "index_watermark": int(session.index.watermark()),
    }
    session.audit("INGEST_HOOKS", **payload)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def cmd_status(args: argparse.Namespace) -> None:
    session = Session(Path(args.world_db), Path(args.session_dir), DEFAULT_TIMEOUT)
    payload = _status_payload(session)
    if args.release_state:
        state_path = Path(args.release_state)
        payload["release_state"] = json.loads(state_path.read_text(encoding="utf-8"))
    out = Path(args.session_dir) / "receipts" / f"status-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    _atomic_text(out, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def cmd_process_due(args: argparse.Namespace) -> None:
    session = Session(Path(args.world_db), Path(args.session_dir), float(args.timeout))
    runtime = session.runtime
    moment = _utc(args.now)
    background_moment = moment + timedelta(seconds=float(args.background_advance))
    audit = session.audit
    audit(
        "PROCESS_DUE_START",
        now=moment.isoformat(),
        background_now=background_moment.isoformat(),
        world_revision=int(session.store.current_world_revision()),
        index_watermark=int(session.index.watermark()),
    )
    session.index.catch_up()

    summary_result = runtime.run_due_dimension_summaries(now=moment)
    audit(
        "SUMMARIES_DONE",
        attempted=len(summary_result.attempted_jobs),
        commits=[
            {
                "object_id": commit.object_id,
                "revision": commit.revision,
                "reused_existing": commit.reused_existing,
            }
            for commit in summary_result.commits
        ],
        skipped_unchanged=len(summary_result.skipped_unchanged),
        skipped_empty=len(summary_result.skipped_empty),
        truncated=bool(summary_result.truncated),
    )

    reconcile = runtime.dimension_summary_scheduler.reconcile_cognitive_derivation()
    audit(
        "C14_RECONCILE",
        result=_jsonable(reconcile),
        stdout_summary={
            "examined": reconcile.get("examined"),
            "scheduled": len(reconcile.get("scheduled") or ()),
        },
    )

    dispatches: list[dict[str, Any]] = []
    for _ in range(int(args.max_wakes)):
        runtime.attention_watches.expire_due(now=background_moment)
        runtime.execution_world.wake_due_tasks(now=background_moment)
        wake = runtime.attention_router.next_dispatchable(
            now=background_moment,
            background_batch_window_seconds=(
                runtime.attention_scheduling_policy.background_batch_window_seconds
            ),
        )
        if wake is None:
            break
        unit = f"wake-{wake.wake_source.value}-{wake.object_id}-rev{wake.revision}"
        session.handler.begin_unit(unit)
        audit(
            "WAKE_DISPATCH_BEGIN",
            unit=unit,
            wake_id=wake.object_id,
            wake_revision=wake.revision,
            wake_source=wake.wake_source.value,
            attention_class=runtime.wake_bus.attention_class_for_wake(wake).value,
        )
        try:
            result = runtime.dispatch_next_pending_wake(now=background_moment)
        except CheckpointAbort as exc:
            audit("WAKE_DISPATCH_ABORT", unit=unit, error=str(exc))
            print(
                json.dumps(
                    {
                        "status": "awaiting_decision",
                        "unit": unit,
                        "world_revision": int(session.store.current_world_revision()),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            raise SystemExit(3)
        if result is None:
            break
        runtime_result = result.runtime
        record = {
            "unit": unit,
            "dispatched_wake_ref": f"{result.wake_ref.object_id}@{result.wake_ref.revision}",
            "wake_state": result.wake.state,
            "step0_state": result.step0.state,
            "termination_reason": (
                None if runtime_result is None else runtime_result.termination_reason
            ),
            "model_rounds": None if runtime_result is None else runtime_result.model_rounds,
            "silenced": None if runtime_result is None else runtime_result.silenced,
            "response": None if runtime_result is None else runtime_result.response,
            "delivery_suppressed": result.delivery_suppressed,
            "capability_calls": (
                []
                if runtime_result is None
                else [
                    {"name": item.name, "ok": item.ok, "error_code": item.error_code}
                    for item in runtime_result.capability_history
                ]
            ),
        }
        dispatches.append(record)
        audit("WAKE_DISPATCH_DONE", **record)

    session.handler.begin_unit(
        f"periodic-review-{background_moment.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    )
    review_result = runtime.run_periodic_review(now=background_moment)
    audit(
        "PERIODIC_REVIEW_DONE",
        invoked=review_result is not None,
        request=(
            None
            if review_result is None
            else {
                "review_id": review_result.request.review_id,
                "wake_ref": f"{review_result.request.wake_ref.object_id}@"
                f"{review_result.request.wake_ref.revision}",
                "anchor_count": len(review_result.request.anchors),
            }
        ),
        wake_state=None if review_result is None else review_result.wake.state,
    )

    payload = {
        "status": "processed",
        "now": moment.isoformat(),
        "background_now": background_moment.isoformat(),
        "summary_commits": [
            {"object_id": commit.object_id, "revision": commit.revision}
            for commit in summary_result.commits
        ],
        "dispatches": dispatches,
        "periodic_review": (
            None
            if review_result is None
            else {
                "review_id": review_result.request.review_id,
                "wake_state": review_result.wake.state,
                "anchors": len(review_result.request.anchors),
            }
        ),
        "world_revision": int(session.store.current_world_revision()),
        "index_watermark": int(session.index.watermark()),
    }
    _atomic_text(
        Path(args.session_dir)
        / "receipts"
        / f"process-due-{moment.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}.json",
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    audit("PROCESS_DUE_DONE", **{k: v for k, v in payload.items() if k != "dispatches"})
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def cmd_handoff(args: argparse.Namespace) -> None:
    session = Session(Path(args.world_db), Path(args.session_dir), DEFAULT_TIMEOUT)
    out_dir = Path(args.out) if args.out else Path(args.session_dir) / "handoff"
    out_dir.mkdir(parents=True, exist_ok=True)
    with session.store._connection() as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.commit()
    status = _status_payload(session)
    world_sha = "sha256:" + hashlib.sha256(Path(args.world_db).read_bytes()).hexdigest()
    release_sha = (
        "sha256:" + hashlib.sha256(Path(args.release_state).read_bytes()).hexdigest()
        if args.release_state
        else None
    )
    handoff = {
        "run_id": "resident-a-restart-20260921",
        "task": "C14-RES-A-001",
        "evaluated_main_sha": args.main_sha,
        "model_identity_as_declared": "GPT-5.6 Sol",
        "provider_session_id": "unknown/not exposed",
        "world_db": str(args.world_db),
        "world_sha256": world_sha,
        "release_state_path": args.release_state,
        "release_state_sha256": release_sha,
        "world_revision": status["world_revision"],
        "index_watermark": status["index_watermark"],
        "summary_refs": [
            f"{item['object_id']}@{item['revision']}" for item in status["summaries"]
        ],
        "claim_refs_user": [
            f"{item['object_id']}@{item['revision']}" for item in status["claims_user"]
        ],
        "claim_refs_ai_self": [
            f"{item['object_id']}@{item['revision']}" for item in status["claims_ai_self"]
        ],
        "wake_refs": [
            f"{item['wake_id']}@{item['revision']}" for item in status["wakes"]
        ],
        "counts": {
            key: len(status[key])
            for key in (
                "wakes",
                "summaries",
                "claims_user",
                "claims_ai_self",
                "observations",
                "tasks",
                "goals",
                "events",
                "entities",
                "dimensions",
                "policies",
                "operation_experiences",
            )
        },
    }
    if args.release_state:
        handoff["release_state"] = json.loads(
            Path(args.release_state).read_text(encoding="utf-8")
        )
    _atomic_text(
        out_dir / "handoff.json",
        json.dumps(handoff, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    _atomic_text(
        out_dir / "world-status.json",
        json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    session.audit("HANDOFF_FROZEN", world_sha256=world_sha, release_state_sha256=release_sha)
    print(json.dumps(handoff, ensure_ascii=False, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init-world")
    init_p.add_argument("--world-db", required=True)
    init_p.add_argument("--session-dir", required=True)
    init_p.set_defaults(func=cmd_init_world)

    hooks_p = sub.add_parser("ingest-hooks")
    hooks_p.add_argument("--world-db", required=True)
    hooks_p.add_argument("--session-dir", required=True)
    hooks_p.add_argument("--ingest-ref", required=True)
    hooks_p.set_defaults(func=cmd_ingest_hooks)

    status_p = sub.add_parser("status")
    status_p.add_argument("--world-db", required=True)
    status_p.add_argument("--session-dir", required=True)
    status_p.add_argument("--release-state")
    status_p.set_defaults(func=cmd_status)

    due_p = sub.add_parser("process-due")
    due_p.add_argument("--world-db", required=True)
    due_p.add_argument("--session-dir", required=True)
    due_p.add_argument("--now", required=True)
    due_p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    due_p.add_argument("--max-wakes", type=int, default=12)
    due_p.add_argument("--background-advance", type=float, default=61.0)
    due_p.set_defaults(func=cmd_process_due)

    handoff_p = sub.add_parser("handoff")
    handoff_p.add_argument("--world-db", required=True)
    handoff_p.add_argument("--session-dir", required=True)
    handoff_p.add_argument("--release-state")
    handoff_p.add_argument("--main-sha", default="")
    handoff_p.add_argument("--out")
    handoff_p.set_defaults(func=cmd_handoff)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
