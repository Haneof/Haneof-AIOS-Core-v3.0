#!/usr/bin/env python3
"""P16 Arena Resident harness — mechanical world runner (NOT a mind).

Owner: arena-cy-p16-001 (independent Arena resident reviewer session).

This program is deliberately mindless. It may:
  - deliver external life events (conversation text, app/payment/calendar/sensor
    records) from a per-segment events file into the real AIOS Core public surfaces
    (ConversationIngestor via FusedTurnRuntime, RealityIngestService, WorldSearchIndex,
    WakeBus, PeriodicReview, dimension-summary scheduler) using the same adapter
    (`tests.habitation.current_core.CurrentCoreHabitationTarget`) that provider-backed
    P16 runs use;
  - advance a monotonic virtual clock and drain due Task/Wake/Review/summary work;
  - mechanically execute already-authorized external Action outcomes when and only
    when an explicit `_world_exec` director event commands it;
  - persist the same private World sqlite across segments;
  - STOP at every model invocation (turn directive rounds, round summaries,
    dimension summaries) by writing the exact RuntimeSnapshot to disk and blocking
    until the Arena-session Resident model personally writes the matching decision
    file. No decision within the timeout aborts the run fail-closed.
  - record a hash-chained mechanical trace + segment checkpoint manifest with
    counters, revisions, watermarks, digests and a previous-segment digest chain.

It may NOT and does NOT:
  - produce any response, retrieval selection, summary text, claim, revision,
    goal/task/action/decision, policy change, or interpretation on its own;
  - precompute or auto-fill decisions;
  - modify src/aios_core/**.

The Resident model in the Arena chat session is the only source of semantic
decisions. Every snapshot/decision pair is preserved verbatim as evidence under
the segment `io/` directory.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve()
HARNESS_DIR = HERE.parent
REVIEW_ROOT = HARNESS_DIR.parent
REPO_ROOT = REVIEW_ROOT.parents[2]
for _p in (str(REPO_ROOT / "src"), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from aios_core.contracts.enums import SourceClass  # noqa: E402
from aios_core.contracts.refs import ObjectRef  # noqa: E402
from aios_core.contracts.time import as_utc  # noqa: E402
from aios_core.context.continuity import RoundSummaryRequest  # noqa: E402
from aios_core.execution.service import ActionOutcomeRequest  # noqa: E402
from aios_core.ingest import RealityIngestService, RealityRecord, SourceAdapterSpec  # noqa: E402
from aios_core.review import ReviewSchedulePolicy  # noqa: E402
from aios_core.runtime.capabilities import CapabilityCall  # noqa: E402
from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot  # noqa: E402
from aios_core.runtime.turn_runtime import FusedTurnRuntime  # noqa: E402
from aios_core.summaries.dimension_summary import DimensionSummaryInput  # noqa: E402
from aios_core.summaries import SummaryScale  # noqa: E402
from aios_core.wake import ObservationTriggerService  # noqa: E402

from tests.habitation.current_core import CurrentCoreHabitationTarget  # noqa: E402
from tests.habitation.harness import ResidentEvent  # noqa: E402


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str) -> datetime:
    return as_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")), "sim_time")


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_safe(value):
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))


class TraceLog:
    """Append-only hash-chained mechanical trace (integrity evidence)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.prev_sha = ""
        if path.exists():
            with open(path, "rb") as handle:
                last = b""
                for line in handle:
                    if line.strip():
                        last = line
                if last:
                    try:
                        self.prev_sha = str(json.loads(last)["sha"])
                    except Exception:
                        self.prev_sha = ""

    def log(self, obj: dict) -> None:
        body = dict(obj)
        body["ts_real"] = _utc_now_iso()
        body["prev_sha"] = self.prev_sha
        encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, default=str)
        sha = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        body["sha"] = sha
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(body, ensure_ascii=False, sort_keys=True, default=str) + "\n"
            )
        self.prev_sha = sha

    def count_model_calls(self) -> int:
        if not self.path.exists():
            return 0
        count = 0
        with open(self.path, "r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    if json.loads(line).get("t") == "model_call":
                        count += 1
                except Exception:
                    continue
        return count


class CognitionTimeout(RuntimeError):
    """No Resident decision arrived in time: fail closed, never auto-decide."""


class ArenaResidentMind:
    """Rendezvous bridge: the actual Arena-session model answers every call.

    This class contains zero cognition. Every invocation serializes the exact
    RuntimeSnapshot / summary request that Core produced, blocks until the
    Resident model's decision file appears, and replays that decision back into
    Core untouched.
    """

    model_id = "arena-session-resident-model-01"

    def __init__(
        self,
        *,
        io_dir: Path,
        trace: TraceLog,
        timeout_s: float = 5400.0,
    ) -> None:
        self.io_dir = io_dir
        self.io_dir.mkdir(parents=True, exist_ok=True)
        self.trace = trace
        self.timeout_s = float(timeout_s)
        self.seq = 0
        self.sim_time: datetime | None = None
        self.event_id: str | None = None
        self.segment_id: str | None = None
        self.call_count = 0
        # plumbing-only mode: strictly for harness self-tests in a throwaway
        # directory; never used for evidence-bearing habitation runs.
        self._smoke = bool(__import__("os").environ.get("ARENA_SMOKE_AUTOPLUMB"))

    def provenance_snapshot(self) -> dict:
        return {
            "resident_provider": "Arena.ai session model (exact underlying model identity not disclosed per platform policy)",
            "resident_role": "the Arena chat-session large model personally answering every Core model invocation",
            "automation": "none — deterministic auto-decisions are structurally absent outside ARENA_SMOKE_AUTOPLUMB plumbing tests",
            "model_invocations_this_segment": self.call_count,
        }

    # ---------------- Core-facing callables ----------------

    def __call__(self, payload):
        if isinstance(payload, RuntimeSnapshot):
            return self._turn(payload)
        if isinstance(payload, RoundSummaryRequest):
            return self._summary_round(payload)
        if isinstance(payload, DimensionSummaryInput):
            return self._summary_dimension(payload)
        raise TypeError(f"unsupported model invocation payload: {type(payload)!r}")

    def _turn(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        if self._smoke:
            self.call_count += 1
            return ModelDirective(response="[smoke-plumbing auto reply — not Resident cognition]")
        record = self._emit(
            kind="turn",
            payload={
                "wake_reason": snapshot.wake_reason,
                "round_index": snapshot.round_index,
                "remaining_tool_rounds": snapshot.remaining_tool_rounds,
                "user_input": snapshot.user_input,
                "cockpit": snapshot.cockpit,
                "capability_catalog": [dict(item) for item in snapshot.capability_catalog],
                "capability_history": [
                    asdict(item) for item in snapshot.capability_history
                ],
            },
        )
        decision = record["decision"]
        self._log_decision(record, decision)
        if decision.get("capability_calls"):
            calls = tuple(
                CapabilityCall(
                    name=str(item["name"]),
                    arguments=dict(item.get("arguments") or {}),
                    call_id=item.get("call_id"),
                )
                for item in decision["capability_calls"]
            )
            return ModelDirective(capability_calls=calls)
        if decision.get("silence"):
            return ModelDirective(silence=True)
        response = decision.get("response")
        if not isinstance(response, str) or not response.strip():
            raise ValueError(
                "Resident decision must contain non-blank response, silence, or capability_calls"
            )
        return ModelDirective(response=response)

    def _summary_round(self, request: RoundSummaryRequest) -> str:
        if self._smoke:
            self.call_count += 1
            return "[smoke-plumbing auto summary — not Resident cognition]"
        record = self._emit(kind="round_summary", payload=request.as_model_input())
        decision = record["decision"]
        self._log_decision(record, decision)
        text = str(decision.get("summary") or "").strip()
        if not text:
            raise ValueError("Resident round-summary decision must contain non-blank summary text")
        return text

    def _summary_dimension(self, inputs: DimensionSummaryInput) -> str:
        if self._smoke:
            self.call_count += 1
            return "[smoke-plumbing auto summary — not Resident cognition]"
        record = self._emit(kind="dimension_summary", payload=inputs.model_dump(mode="json"))
        decision = record["decision"]
        self._log_decision(record, decision)
        text = str(decision.get("summary") or "").strip()
        if not text:
            raise ValueError("Resident dimension-summary decision must contain non-blank summary text")
        return text

    # ---------------- rendezvous mechanics (no cognition here) ----------------

    def _emit(self, *, kind: str, payload: dict) -> dict:
        self.seq += 1
        self.call_count += 1
        seq = self.seq
        snapshot_path = self.io_dir / f"snapshot_{seq:04d}.json"
        compact_path = self.io_dir / f"snapshot_{seq:04d}.compact.txt"
        pending_path = self.io_dir / "pending.json"
        decision_path = self.io_dir / f"decision_{seq:04d}.json"
        record_body = {
            "seq": seq,
            "kind": kind,
            "segment_id": self.segment_id,
            "event_id": self.event_id,
            "sim_time": None if self.sim_time is None else self.sim_time.isoformat(),
            "resident_model_id": self.model_id,
            "payload": payload,
        }
        encoded = json.dumps(record_body, ensure_ascii=False, indent=1, default=str)
        snapshot_path.write_text(encoded, encoding="utf-8")
        compact = dict(record_body)
        catalog_note = ""
        if kind == "turn":
            catalog = compact["payload"].pop("capability_catalog", [])
            catalog_note = (
                f"[capability_catalog omitted: {len(catalog)} entries; identical to "
                "snapshot_0001.json and Core registry; full text in snapshot file]"
            )
        compact_text = json.dumps(compact, ensure_ascii=False, indent=1, default=str)
        compact_path.write_text(catalog_note + "\n" + compact_text, encoding="utf-8")
        pending_path.write_text(
            json.dumps(
                {
                    "seq": seq,
                    "kind": kind,
                    "snapshot": str(snapshot_path),
                    "compact": str(compact_path),
                    "decision_expected_at": str(decision_path),
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        self.trace.log(
            {
                "t": "model_call",
                "seq": seq,
                "kind": kind,
                "event_id": self.event_id,
                "sim_time": None if self.sim_time is None else self.sim_time.isoformat(),
                "snapshot_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
            }
        )
        deadline = time.time() + self.timeout_s
        while not decision_path.exists():
            if time.time() > deadline:
                raise CognitionTimeout(
                    f"Resident decision {decision_path.name} did not arrive within "
                    f"{self.timeout_s}s; aborting fail-closed instead of auto-deciding"
                )
            time.sleep(0.4)
        raw = decision_path.read_bytes()
        decision = json.loads(raw)
        try:
            pending_path.unlink()
        except FileNotFoundError:
            pass
        return {
            "seq": seq,
            "kind": kind,
            "decision_sha256": hashlib.sha256(raw).hexdigest(),
            "decision": decision,
        }

    def _log_decision(self, record: dict, decision: dict) -> None:
        if self._smoke:
            self.trace.log({"t": "model_decision", "seq": record["seq"], "smoke_plumbing": True})
            return
        calls = [str(item.get("name")) for item in decision.get("capability_calls") or []]
        self.trace.log(
            {
                "t": "model_decision",
                "seq": record["seq"],
                "kind": record["kind"],
                "directive": (
                    "capabilities" if calls
                    else "silence" if decision.get("silence")
                    else "summary" if record["kind"] != "turn"
                    else "respond"
                ),
                "capability_calls": calls,
                "response_chars": len(str(decision.get("response") or decision.get("summary") or "")),
                "decision_sha256": record["decision_sha256"],
                "resident_note": str(decision.get("resident_note") or ""),
            }
        )


class ArenaResidentTarget(CurrentCoreHabitationTarget):
    """Same private-world wiring as the provider-backed P16 target, with
    mechanically tuned session/summary configuration (no semantic change)."""

    def __init__(
        self,
        *,
        dim_summary_scales: tuple[str, ...] | None = None,
        dim_summary_dimensions: tuple[str, ...] | None = None,
        dim_summary_max_jobs: int = 16,
        summary_chunk_turns: int = 4,
        recent_turn_limit: int = 3,
        max_round_summaries_per_turn: int = 3,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        # Rebuild the runtime with the same public constructor surfaces the Core
        # adapter uses, changing only mechanical scheduling/context-window knobs.
        self.runtime = FusedTurnRuntime(
            store=self.store,
            index=self.index,
            model_handler=self._model_handler,
            subject_id=self.subject_id,
            round_summary_handler=self._round_summary_handler,
            dimension_summary_handler=self._dimension_summary_handler,
            max_tool_rounds=8,
            recent_turn_limit=recent_turn_limit,
            summary_chunk_turns=summary_chunk_turns,
            max_round_summaries_per_turn=max_round_summaries_per_turn,
        )
        self.observation_triggers = ObservationTriggerService(
            store=self.store,
            wake_bus=self.runtime.wake_bus,
            subject_id=self.subject_id,
        )
        self._arena_dim_scales = (
            None if dim_summary_scales is None
            else tuple(SummaryScale(item) for item in dim_summary_scales)
        )
        self._arena_dim_dimensions = dim_summary_dimensions
        self._arena_dim_max_jobs = dim_summary_max_jobs

    def _run_dimension_summaries(self, now: datetime) -> dict:
        if self.runtime.dimension_summary_scheduler is None or self._arena_dim_scales is None:
            return {"at": now.isoformat(), "invoked": False, "reason": "arena_config_disabled"}
        result = self.runtime.run_due_dimension_summaries(
            now=now,
            scales=self._arena_dim_scales,
            max_jobs=self._arena_dim_max_jobs,
            dimensions=self._arena_dim_dimensions,
        )
        return {
            "at": now.isoformat(),
            "invoked": True,
            "attempted_jobs": len(result.attempted_jobs),
            "commits": [asdict(item) for item in result.commits],
            "skipped_unchanged": len(result.skipped_unchanged),
            "skipped_empty": len(result.skipped_empty),
            "truncated": result.truncated,
        }


class SegmentRunner:
    def __init__(self, *, reviewer_root: Path, segment_id: str) -> None:
        self.root = reviewer_root
        self.segment_id = segment_id
        self.seg_dir = reviewer_root / "segments" / segment_id
        self.io_dir = self.seg_dir / "io"
        self.world_db = reviewer_root / "world" / "world.sqlite"
        self.cfg = json.loads((self.seg_dir / "segment.json").read_text(encoding="utf-8"))
        self.state_path = self.seg_dir / "run_state.json"
        if self.state_path.exists():
            self.state = json.loads(self.state_path.read_text(encoding="utf-8"))
        else:
            self.state = {"next_event_index": 0, "event_refs": {}}

    # ---------------- helpers ----------------

    def _save_state(self) -> None:
        self.state_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=1, default=str),
            encoding="utf-8",
        )

    def _events(self) -> list[dict]:
        events_path = self.seg_dir / str(self.cfg.get("events_file", "events.jsonl"))
        items = []
        with open(events_path, "r", encoding="utf-8") as handle:
            for raw in handle:
                raw = raw.strip()
                if raw:
                    items.append(json.loads(raw))
        return items

    def _build_target(self, *, fresh: bool, trace: TraceLog, mind: ArenaResidentMind):
        review_cfg = dict(self.cfg.get("review_policy") or {})
        return ArenaResidentTarget(
            model_id=mind.model_id,
            subject_id=str(self.cfg["subject_id"]),
            db_path=self.world_db,
            model_handler=mind,
            round_summary_handler=mind,
            dimension_summary_handler=mind,
            review_policy=ReviewSchedulePolicy(
                interval_hours=float(review_cfg.get("interval_hours", 72.0)),
                lookback_hours=float(review_cfg.get("lookback_hours", 72.0)),
                max_candidates=int(review_cfg.get("max_candidates", 80)),
                max_per_object_type=int(review_cfg.get("max_per_object_type", 20)),
            ),
            require_fresh=fresh,
            token_budget=self.cfg.get("token_budget"),
            dim_summary_scales=tuple(self.cfg["dimension_summaries"]["scales"])
            if self.cfg.get("dimension_summaries") else None,
            dim_summary_dimensions=tuple(self.cfg["dimension_summaries"]["dimensions"])
            if self.cfg.get("dimension_summaries") else None,
            dim_summary_max_jobs=int(self.cfg.get("dimension_summaries", {}).get("max_jobs", 16)),
            summary_chunk_turns=int(self.cfg.get("summary_chunk_turns", 4)),
            recent_turn_limit=int(self.cfg.get("recent_turn_limit", 3)),
            max_round_summaries_per_turn=int(self.cfg.get("max_round_summaries_per_turn", 3)),
        )

    def _resolve_event_ref(self, event_id: str):
        refs = self.state.get("event_refs", {}).get(event_id)
        if isinstance(refs, list) and refs:
            return ObjectRef(object_id=str(refs[0]["object_id"]), revision=int(refs[0]["revision"]))
        conv = self.state.get("conv_refs", {}).get(event_id)
        if isinstance(conv, dict):
            return self._resolve_user_turn_ref(
                str(conv["session_id"]), int(conv["turn_index"])
            )
        return None

    def _resolve_user_turn_ref(self, session_id: str, turn_index: int):
        for payload in self.store_like_list():
            if payload.get("object_type") != "observation":
                continue
            if payload.get("source_kind") != "user_ai_interaction":
                continue
            metadata = payload.get("metadata") or {}
            if (
                str(metadata.get("session_id") or "") == session_id
                and int(metadata.get("turn_index") or -1) == int(turn_index)
                and str(metadata.get("role") or "") == "user"
            ):
                return ObjectRef(
                    object_id=str(payload["object_id"]),
                    revision=int(payload.get("revision") or 1),
                )
        return None

    def store_like_list(self):
        return self._target.store.list_payloads(subject_id=self._target.subject_id)

    # ---------------- world-side mechanical action closure ----------------

    def _execute_world_action_event(self, ev: dict, now: datetime, trace: TraceLog) -> dict:
        """Explicit director instruction to the external world to authorize and
        complete a Resident-proposed Action. Mechanical only: which action, what
        outcome, and what authorization evidence are all pre-specified by the
        director event itself; nothing is inferred here."""
        payload = dict(ev["payload"])
        op = payload.get("op")
        if op != "authorize_and_record_outcome":
            raise ValueError(f"unsupported _world_exec op: {op!r}")
        action_id = str(payload.get("action_id") or "")
        outcome_state = str(payload["outcome_state"])
        service = self._target.runtime.execution_world
        action = None
        wanted_type = payload.get("action_lookup", {}).get("action_type") if isinstance(payload.get("action_lookup"), dict) else payload.get("action_type")
        require_status = str(payload.get("require_status") or "proposed")
        for item in service.current_actions():
            if action_id and item.object_id != action_id:
                continue
            if wanted_type and str(item.action_type) != str(wanted_type):
                continue
            if require_status and str(item.action_status) != require_status:
                continue
            action = item  # keep scanning: take the latest matching mechanical candidate
        if action is None:
            raise ValueError(
                f"_world_exec could not mechanically resolve a {wanted_type or ''!r} action with status "
                f"{require_status!r} (action_id={action_id or 'lookup'}); fail closed instead of guessing"
            )
        auth_refs = []
        evidence = payload.get("authorization_evidence") or {}
        if evidence.get("event_id"):
            ref = self._resolve_event_ref(str(evidence["event_id"]))
        elif evidence.get("session_id") and evidence.get("turn_index"):
            ref = self._resolve_user_turn_ref(
                str(evidence["session_id"]), int(evidence["turn_index"])
            )
        else:
            ref = None
        if ref is None:
            raise ValueError("_world_exec authorization evidence could not be resolved to a pinned ref")
        auth_refs.append(ref)
        envelope = service.authorize_action(
            action_ref=ObjectRef(object_id=action.object_id, revision=int(action.revision)),
            authorization_refs=tuple(auth_refs),
            authorized_by=str(payload.get("authorized_by", "world-user-channel")),
            authorized_at=now,
            authorizer=lambda action, refs: True,
        )
        receipt = service.record_outcome(
            ActionOutcomeRequest(
                action_ref=ObjectRef(object_id=envelope.action_id, revision=int(envelope.revision)),
                outcome_state=outcome_state,
                payload=dict(payload.get("outcome_payload") or {}),
                evidence_refs=tuple(auth_refs),
            ),
            recorded_at=now,
        )
        trace.log(
            {
                "t": "world_exec",
                "event_id": ev["event_id"],
                "action_id": receipt.action_id,
                "action_revision": receipt.action_revision,
                "outcome_id": receipt.outcome_id,
                "outcome_state": receipt.outcome_state,
                "world_revision": receipt.world_revision,
            }
        )
        return {
            "outcome_id": receipt.outcome_id,
            "action_revision": receipt.action_revision,
            "world_revision": receipt.world_revision,
        }

    # ---------------- main run ----------------

    def run(self) -> dict:
        self.io_dir.mkdir(parents=True, exist_ok=True)
        trace = TraceLog(self.seg_dir / "trace.jsonl")
        mind = ArenaResidentMind(
            io_dir=self.io_dir,
            trace=trace,
            timeout_s=float(self.cfg.get("decision_timeout_s", 5400)),
        )
        mind.segment_id = self.segment_id
        start_index = int(self.state["next_event_index"])
        # fresh = no events delivered yet AND no durable world artifact present
        fresh = bool(self.cfg.get("fresh", False)) and start_index == 0 and not self.world_db.exists()
        if bool(self.cfg.get("allow_resume", True)) and not fresh:
            fresh = False
        if fresh and self.world_db.exists():
            raise RuntimeError("segment configured fresh but a world db already exists")
        self._target = self._build_target(fresh=fresh, trace=trace, mind=mind)
        trace.log(
            {
                "t": "segment_start",
                "segment_id": self.segment_id,
                "fresh_world": fresh,
                "resumed_from_index": start_index,
                "world_revision": int(self._target.store.current_world_revision()),
                "index_watermark": int(self._target.index.watermark()),
                "restored_clock": None if self._target.clock is None else self._target.clock.isoformat(),
            }
        )
        events = self._events()
        for index, ev in enumerate(events):
            if index < start_index:
                continue
            now = _parse_iso(ev["sim_time"])
            if self._target.clock is not None and now < self._target.clock:
                raise ValueError(
                    f"event {ev['event_id']} sim_time is before the restored virtual clock "
                    f"({now} < {self._target.clock}); the segment timeline must be monotonic"
                )
            # stamp the mind before advancing so review/wake/summary model calls that
            # fire inside advance_to carry the correct event/time provenance
            mind.sim_time = now
            mind.event_id = str(ev["event_id"])
            self._target.advance_to(now)
            if ev["channel"] == "_world_exec":
                result = self._execute_world_action_event(ev, now, trace)
            else:
                result = self._target.handle_event(
                    ResidentEvent(
                        event_id=str(ev["event_id"]),
                        occurred_at=now,
                        channel=str(ev["channel"]),
                        payload=ev["payload"],
                        metadata=dict(ev.get("metadata") or {}),
                    )
                )
                result = _json_safe(dict(result))
                obs_refs = result.get("observation_refs")
                if isinstance(obs_refs, list) and obs_refs:
                    self.state.setdefault("event_refs", {})[str(ev["event_id"])] = obs_refs
                if (
                    result.get("kind") == "conversation"
                    and result.get("session_id") is not None
                    and result.get("turn_index") is not None
                ):
                    self.state.setdefault("conv_refs", {})[str(ev["event_id"])] = {
                        "session_id": result["session_id"],
                        "turn_index": int(result["turn_index"]),
                    }
            self.state["next_event_index"] = index + 1
            self.state["last_sim_time"] = now.isoformat()
            self._save_state()
            trace.log(
                {
                    "t": "event_result",
                    "event_id": ev["event_id"],
                    "index": index,
                    "channel": ev["channel"],
                    "world_revision": int(self._target.store.current_world_revision()),
                    "result_keys": sorted(result.keys()),
                }
            )
        tail = self.cfg.get("tail_advance_to")
        if tail:
            tail_time = _parse_iso(tail)
            mind.sim_time = tail_time
            mind.event_id = f"{self.segment_id}:tail"
            tail_result = self._target.advance_to(tail_time)
            trace.log(
                {
                    "t": "segment_tail_advance",
                    "to": tail_result.get("to"),
                    "task_cycles": len(tail_result.get("task_cycles") or []),
                    "periodic_reviews": len(tail_result.get("periodic_reviews") or []),
                    "world_revision": tail_result.get("world_revision"),
                }
            )
        checkpoint = self._write_checkpoint(mind, trace)
        (self.io_dir / "done.json").write_text(
            json.dumps({"status": "segment_complete", "checkpoint": checkpoint}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        trace.log({"t": "segment_end", "checkpoint_sha256": checkpoint["checkpoint_sha256"]})
        return checkpoint

    def _write_checkpoint(self, mind: ArenaResidentMind, trace: TraceLog) -> dict:
        target = self._target
        store = target.store
        subject = target.subject_id
        payloads = store.list_payloads(subject_id=subject)
        counts: dict[str, int] = {}
        reality_sources: dict[str, int] = {}
        wake_states: dict[str, int] = {}
        for payload in payloads:
            object_type = str(payload.get("object_type") or "")
            counts[object_type] = counts.get(object_type, 0) + 1
            if object_type == "observation":
                source_kind = str(payload.get("source_kind") or "")
                reality_sources[source_kind] = reality_sources.get(source_kind, 0) + 1
            if object_type == "wake":
                state = str(payload.get("wake_state") or "")
                wake_states[state] = wake_states.get(state, 0) + 1
        events = self._events()
        conversation_events = sum(1 for item in events if item["channel"] == "conversation")
        reality_events = sum(1 for item in events if item["channel"] not in {"conversation", "_world_exec"})
        git = {}
        for key, cmd in (
            ("head", ["git", "rev-parse", "HEAD"]),
            ("main", ["git", "rev-parse", "main"]),
            ("branch", ["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        ):
            try:
                git[key] = subprocess.run(
                    cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=10
                ).stdout.strip()
            except Exception:
                git[key] = None
        # immutable segment copy of the durable world
        world_copy = self.seg_dir / "world.sqlite"
        with sqlite3.connect(self.world_db) as source, sqlite3.connect(world_copy) as dest:
            source.backup(dest)
        pending_wakes = [
            wake.model_dump(mode="json") for wake in target.runtime.wake_bus.pending_wakes()
        ]
        goals = [
            {
                "object_id": item.object_id,
                "revision": item.revision,
                "title": item.title,
                "status": item.status,
            }
            for item in target.runtime.execution_world.current_goals()
        ]
        tasks = [
            {
                "object_id": item.object_id,
                "revision": item.revision,
                "title": item.title,
                "task_state": item.task_state.value if hasattr(item.task_state, "value") else str(item.task_state),
                "next_wake_at": None if item.next_wake_at is None else item.next_wake_at.isoformat(),
                "deadline": None if item.deadline is None else item.deadline.isoformat(),
            }
            for item in target.runtime.execution_world.current_tasks()
        ]
        actions = [
            {
                "object_id": item.object_id,
                "revision": item.revision,
                "action_type": item.action_type,
                "action_status": str(item.action_status),
            }
            for item in target.runtime.execution_world.current_actions()
        ]
        decision_files = sorted(self.io_dir.glob("decision_*.json"))
        decisions_digest = hashlib.sha256()
        for path in decision_files:
            decisions_digest.update(path.read_bytes())
        previous_root_checkpoint = self.root / "checkpoint.json"
        previous_digest = (
            _sha_file(previous_root_checkpoint) if previous_root_checkpoint.exists() else None
        )
        cumulative = {
            "segments_completed": 0,
            "cumulative_sim_days": 0,
            "cumulative_events": 0,
            "cumulative_interactions": 0,
            "cumulative_reality_inputs": 0,
            "cumulative_resident_model_calls": 0,
            "history": [],
        }
        cumulative_path = self.root / "cumulative.json"
        if cumulative_path.exists():
            cumulative = json.loads(cumulative_path.read_text(encoding="utf-8"))
        segment_days = int(self.cfg.get("segment_sim_days", 0))
        manifest = {
            "habitation_run_id": str(self.cfg.get("habitation_run_id", "arena-cy-p16-001-r1")),
            "reviewer_id": "arena-cy-p16-001",
            "logical_resident_id": "resident-阿潮@subject_cy01",
            "segment_id": self.segment_id,
            "segment_ordinal": int(self.cfg.get("segment_ordinal", 1)),
            "tested_repo_head_sha": git.get("head"),
            "tested_main_sha": git.get("main"),
            "review_branch": git.get("branch"),
            "segment_sim_start": str(self.cfg.get("segment_sim_start")),
            "segment_sim_end": str(self.cfg.get("segment_sim_end")),
            "segment_sim_days": segment_days,
            "cumulative_sim_days": cumulative["cumulative_sim_days"] + segment_days,
            "next_life_event_cursor": {
                "next_segment_id": str(self.cfg.get("next_segment_id", f"{self.segment_id}-NEXT")),
                "events_consumed_in_segment": len(events),
                "run_state_next_event_index": int(self.state["next_event_index"]),
            },
            "resident_cognition_checkpoint_count_segment": trace.count_model_calls(),
            "resident_cognition_checkpoint_count_cumulative": cumulative["cumulative_resident_model_calls"] + trace.count_model_calls(),
            "subject_id": subject,
            "world_db_path": str(self.world_db),
            "world_db_copy_segment_path": str(world_copy),
            "world_revision": int(store.current_world_revision()),
            "index_watermark": int(target.index.watermark()),
            "sim_clock_cursor": None if target.clock is None else target.clock.isoformat(),
            "object_counts": dict(sorted(counts.items())),
            "reality_source_kind_counts": dict(sorted(reality_sources.items())),
            "wake_state_counts": dict(sorted(wake_states.items())),
            "pending_wakes": pending_wakes,
            "active_goals": goals,
            "active_tasks": tasks,
            "actions": actions,
            "events_total_segment": len(events),
            "conversation_turns_segment": conversation_events,
            "reality_input_events_segment": reality_events,
            "session_turns": dict(sorted(target._session_turns.items())),
            "model_identity": mind.model_id,
            "provider_provenance": mind.provenance_snapshot(),
            "digests": {
                "world_db_copy_sha256": _sha_file(world_copy),
                "events_jsonl_sha256": _sha_file(self.seg_dir / str(self.cfg.get("events_file", "events.jsonl"))),
                "trace_jsonl_sha256": _sha_file(self.seg_dir / "trace.jsonl"),
                "segment_json_sha256": _sha_file(self.seg_dir / "segment.json"),
                "decisions_concat_sha256": decisions_digest.hexdigest(),
                "decision_file_count": len(decision_files),
            },
            "previous_segment_checkpoint_sha256": previous_digest,
            "written_at_real": _utc_now_iso(),
        }
        segment_checkpoint_path = self.seg_dir / "checkpoint.json"
        encoded = json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True)
        segment_checkpoint_path.write_text(encoded, encoding="utf-8")
        manifest["checkpoint_sha256"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        cumulative["segments_completed"] += 1
        cumulative["cumulative_sim_days"] += segment_days
        cumulative["cumulative_events"] += len(events)
        cumulative["cumulative_interactions"] += conversation_events
        cumulative["cumulative_reality_inputs"] += reality_events
        cumulative["cumulative_resident_model_calls"] += trace.count_model_calls()
        cumulative["history"].append(
            {
                "segment_id": self.segment_id,
                "checkpoint_sha256": manifest["checkpoint_sha256"],
                "sim_days": segment_days,
                "world_revision": manifest["world_revision"],
                "cognition": manifest["resident_cognition_checkpoint_count_segment"],
            }
        )
        cumulative_path.write_text(
            json.dumps(cumulative, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
        )
        (self.root / "checkpoint.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
        )
        return manifest


def cmd_run(args) -> int:
    runner = SegmentRunner(reviewer_root=Path(args.root).resolve(), segment_id=args.segment)
    checkpoint = runner.run()
    print(json.dumps({"status": "complete", "checkpoint": {k: checkpoint[k] for k in (
        "segment_id", "cumulative_sim_days", "resident_cognition_checkpoint_count_segment",
        "world_revision", "index_watermark", "sim_clock_cursor", "checkpoint_sha256")}}, ensure_ascii=False, indent=1))
    return 0


def cmd_verify(args) -> int:
    root = Path(args.root).resolve()
    seg_dir = root / "segments" / args.segment
    cfg = json.loads((seg_dir / "segment.json").read_text(encoding="utf-8"))
    trace = TraceLog(seg_dir / "trace.jsonl")
    mind = ArenaResidentMind(io_dir=seg_dir / "io", trace=trace)
    runner = SegmentRunner(reviewer_root=root, segment_id=args.segment)
    runner.cfg = cfg
    runner.state = {"next_event_index": int(cfg.get("events_consumed_at_verify", 0)), "event_refs": {}}
    target = runner._build_target(fresh=False, trace=trace, mind=mind)
    payloads = target.store.list_payloads(subject_id=cfg["subject_id"])
    counts: dict[str, int] = {}
    for payload in payloads:
        key = str(payload.get("object_type") or "")
        counts[key] = counts.get(key, 0) + 1
    result = {
        "status": "verify",
        "segment_id": args.segment,
        "reopened_existing_world": True,
        "world_revision": int(target.store.current_world_revision()),
        "index_watermark": int(target.index.watermark()),
        "restored_sim_clock": None if target.clock is None else target.clock.isoformat(),
        "restored_session_turns": dict(sorted(target._session_turns.items())),
        "object_counts": dict(sorted(counts.items())),
        "pending_wakes": [
            {
                "object_id": wake.object_id,
                "wake_source": wake.wake_source.value,
                "wake_state": str(getattr(wake, "wake_state", "")),
            }
            for wake in target.runtime.wake_bus.pending_wakes()
        ],
        "verified_at_real": _utc_now_iso(),
    }
    probes = root / "probes"
    probes.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (probes / f"verify_{stamp}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


def cmd_decoy_probe(args) -> int:
    """Mechanical subject-isolation probe with a decoy subject in the same world.

    Writes decoy observations through the public RealityIngestService for the decoy
    subject, then verifies the primary subject's scoped index queries and the
    resident-facing inspect capability cannot see them. No Resident cognition is
    involved or required; this checks enforcement, not judgment.
    """
    root = Path(args.root).resolve()
    seg_dir = root / "segments" / args.segment
    cfg = json.loads((seg_dir / "segment.json").read_text(encoding="utf-8"))
    probe_cfg = json.loads((root / "probes" / "decoy_probe_texts.json").read_text(encoding="utf-8"))
    target = SegmentRunner(reviewer_root=root, segment_id=args.segment)
    target.cfg = cfg
    target.state = {"next_event_index": 0, "event_refs": {}}
    trace = TraceLog(seg_dir / "trace.jsonl")
    mind = ArenaResidentMind(io_dir=seg_dir / "io", trace=trace)
    built = target._build_target(fresh=False, trace=trace, mind=mind)
    decoy_id = str(probe_cfg["decoy_subject_id"])
    spec = SourceAdapterSpec(
        adapter_id="probe.decoy.v1",
        source_kind=probe_cfg["source_kind"],
        dimension=probe_cfg["dimension"],
        source_class=SourceClass.USER,
        default_modality="structured_record",
    )
    service = RealityIngestService(store=built.store, index=built.index, subject_id=decoy_id)
    wrote = []
    for item in probe_cfg["records"]:
        receipt = service.ingest_record(
            spec,
            RealityRecord(
                external_record_id=str(item["external_record_id"]),
                occurred_at=_parse_iso(item["occurred_at"]),
                received_at=_parse_iso(item["occurred_at"]),
                value=item["text"],
                modality="structured_record",
                source_locator=f"probe://{decoy_id}/{item['external_record_id']}",
                provenance={"probe": "arena-cy-p16-001 subject isolation"},
            ),
        )
        wrote.append({"observation_id": receipt.observation_id, "world_revision": receipt.world_revision})
    built.index.catch_up()
    scoped = built.index.recall_candidates(
        probe_cfg["query"], subject=str(cfg["subject_id"]), limit=60
    )
    scoped_ids = [(hit.object_id, hit.revision) for hit in scoped.hits]
    leaked = []
    for object_id, _revision in scoped_ids:
        payload = built.store.get_payload(object_id)
        if str(payload.get("subject_id") or "") == decoy_id:
            leaked.append(object_id)
    inspect = built.runtime.registry.invoke(
        CapabilityCall(
            name="inspect_world_object",
            arguments={"object_id": wrote[0]["observation_id"], "revision": 1},
        )
    )
    result = {
        "probe": "decoy_subject_isolation",
        "primary_subject": cfg["subject_id"],
        "decoy_subject": decoy_id,
        "decoy_observation_ids": [item["observation_id"] for item in wrote],
        "query": probe_cfg["query"],
        "primary_scoped_hit_count": len(scoped_ids),
        "leaked_decoy_hits_in_primary_scope": leaked,
        "resident_inspect_of_decoy_ok": bool(inspect.ok),
        "resident_inspect_error": inspect.error_message,
        "expected": {
            "leaked_decoy_hits_in_primary_scope": [],
            "resident_inspect_of_decoy_ok": False,
        },
        "verdict": (
            "PASS"
            if (not leaked and not inspect.ok)
            else "FAIL"
        ),
        "world_revision_after_probe": int(built.store.current_world_revision()),
        "probe_records_are_foreign_to_life": True,
        "at_real": _utc_now_iso(),
    }
    probes = root / "probes"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = probes / f"decoy_isolation_probe_{stamp}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({**result, "evidence_path": str(path)}, ensure_ascii=False, indent=1))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="resident_runner")
    parser.add_argument("--root", default=str(REVIEW_ROOT))
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="run one resumable segment")
    run_p.add_argument("--segment", required=True)
    ver_p = sub.add_parser("verify", help="reopen the durable world read-only and report cursors")
    ver_p.add_argument("--segment", required=True)
    dec_p = sub.add_parser("decoy-probe", help="mechanical subject isolation probe")
    dec_p.add_argument("--segment", required=True)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "run":
            return cmd_run(args)
        if args.cmd == "verify":
            return cmd_verify(args)
        if args.cmd == "decoy-probe":
            return cmd_decoy_probe(args)
        raise ValueError(args.cmd)
    except Exception:
        error_text = traceback.format_exc()
        print(error_text, file=sys.stderr)
        try:
            io_dir = Path(args.root) / "segments" / args.segment / "io"
            io_dir.mkdir(parents=True, exist_ok=True)
            (io_dir / "error.json").write_text(
                json.dumps(
                    {
                        "status": "aborted_fail_closed",
                        "error": error_text[-4000:],
                        "note": "runner never auto-decides; a stalled model invocation aborts the segment",
                        "at_real": _utc_now_iso(),
                    },
                    ensure_ascii=False,
                    indent=1,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
