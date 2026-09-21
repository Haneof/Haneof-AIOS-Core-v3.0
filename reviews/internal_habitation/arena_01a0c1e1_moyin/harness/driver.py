"""P16 Arena Resident driver (reviewer-only, non-Core).

Mechanical responsibilities ONLY (governance/P16 section 5):

* advance the simulated clock;
* deliver Life-Director-authored external observations through real Core surfaces;
* execute capability calls the Resident already chose;
* persist / restore the durable World;
* stop at the next semantic checkpoint and print it verbatim;
* freeze auditable segment checkpoints.

It never interprets an observation, never writes a Summary, never forms a Claim,
never chooses a reply. Those are authored by the Resident model itself and stored
under ``decisions/`` as an append-only journal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.habitation.current_core import CurrentCoreHabitationTarget  # noqa: E402

from .bridge import (  # noqa: E402
    KIND_DIMENSION_SUMMARY,
    KIND_ROUND_SUMMARY,
    KIND_TURN,
    JournalDecisionSource,
    ResidentBridge,
    ResidentPending,
    canonical_json,
    fingerprint,
)

LOCAL = timezone(timedelta(hours=8), name="Asia/Shanghai")
RUN_ID = "hab_arena_01a0c1e1_moyin_v1"
REVIEWER_ID = "arena_01a0c1e1_moyin"
RESIDENT_ID = "resident_moyin_shenyanqiu"
SUBJECT_ID = "subj_shen_yanqiu"
DECOY_SUBJECT_ID = "subj_lintong_apprentice"
MODEL_ID = "arena-agent-mode-resident/unknown-provider-model"
BASE_DIR = Path(
    os.environ.get("MOYIN_BASE") or Path(__file__).resolve().parents[1]
).resolve()


# --------------------------------------------------------------------------- io
def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(value) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ------------------------------------------------------------------- db safety
def backup_db(db_path: Path, backup_path: Path) -> None:
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if backup_path.exists():
        backup_path.unlink()
    source = sqlite3.connect(str(db_path))
    try:
        target = sqlite3.connect(str(backup_path))
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()


def restore_db(db_path: Path, backup_path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        stale = Path(str(db_path) + suffix)
        if stale.exists():
            stale.unlink()
    source = sqlite3.connect(str(backup_path))
    try:
        target = sqlite3.connect(str(db_path))
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()


# --------------------------------------------------------------- handler shell
class _HandlerShell:
    """Exposes model_id/provenance so Core-side provenance checks stay honest."""

    def __init__(self, holder: "BridgeHolder", kind: str) -> None:
        self.holder = holder
        self.kind = kind
        self.model_id = MODEL_ID

    def provenance_snapshot(self) -> dict[str, Any]:
        return {
            "model_id": MODEL_ID,
            "provider": "arena.ai-agent-mode",
            "provider_note": (
                "Arena.ai Agent Mode does not expose the concrete provider/model "
                "identity to the session. Decisions were authored by the Arena "
                "session model itself through the file bridge."
            ),
            "decision_journal": "reviews/internal_habitation/"
            f"{REVIEWER_ID}/decisions",
            "bridge": "file-bridge; no pseudo-model, no keyword table",
        }


class TurnHandlerShell(_HandlerShell):
    def __init__(self, holder: "BridgeHolder") -> None:
        super().__init__(holder, KIND_TURN)

    def __call__(self, snapshot: Any) -> Any:
        return self.holder.current.turn_directive(snapshot)


class RoundSummaryHandlerShell(_HandlerShell):
    def __init__(self, holder: "BridgeHolder") -> None:
        super().__init__(holder, KIND_ROUND_SUMMARY)

    def __call__(self, request: Any) -> str:
        return self.holder.current.round_summary(request)


class DimensionSummaryHandlerShell(_HandlerShell):
    def __init__(self, holder: "BridgeHolder") -> None:
        super().__init__(holder, KIND_DIMENSION_SUMMARY)

    def __call__(self, request: Any) -> str:
        return self.holder.current.dimension_summary(request)


class BridgeHolder:
    def __init__(self) -> None:
        self.current: ResidentBridge | None = None


# ------------------------------------------------------------------ life input
def parse_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class LifeEvent:
    event_id: str
    occurred_at: datetime
    channel: str
    payload: Any
    metadata: dict[str, Any]


def load_life(segment_dir: Path) -> list[LifeEvent]:
    events: list[LifeEvent] = []
    for path in sorted(segment_dir.glob("*.jsonl")):
        if path.name == "decoy.jsonl":
            # The decoy subject's facts are an isolation probe, not this Resident's life.
            continue
        for raw in _read_jsonl(path):
            events.append(
                LifeEvent(
                    event_id=str(raw["event_id"]),
                    occurred_at=parse_instant(str(raw["occurred_at"])),
                    channel=str(raw["channel"]),
                    payload=raw["payload"],
                    metadata=dict(raw.get("metadata") or {}),
                )
            )
    events.sort(key=lambda item: (item.occurred_at, item.event_id))
    return events


def day_rolls(start: datetime, end: datetime, hour: int, minute: int) -> list[datetime]:
    """Deterministic background ticks so scheduler work never sleeps across days."""
    rolls: list[datetime] = []
    local_start = start.astimezone(LOCAL)
    day = local_start.replace(hour=hour, minute=minute, second=0, microsecond=0)
    while day.astimezone(timezone.utc) < start:
        day = day + timedelta(days=1)
    while day.astimezone(timezone.utc) <= end:
        rolls.append(day.astimezone(timezone.utc))
        day = day + timedelta(days=1)
    return rolls


# ----------------------------------------------------------------------- steps
def build_steps(events: Sequence[LifeEvent], roll_hour: int, roll_minute: int) -> list[dict[str, Any]]:
    if not events:
        return []
    start = events[0].occurred_at
    end = events[-1].occurred_at
    instants = {event.occurred_at for event in events}
    instants.update(day_rolls(start, end, roll_hour, roll_minute))
    ordered = sorted(instants)

    by_time: dict[datetime, list[LifeEvent]] = {}
    for event in events:
        by_time.setdefault(event.occurred_at, []).append(event)

    steps: list[dict[str, Any]] = []
    for index, instant in enumerate(ordered):
        steps.append({"index": len(steps), "kind": "advance", "at": instant.isoformat()})
        for event in by_time.get(instant, []):
            steps.append(
                {
                    "index": len(steps),
                    "kind": "event",
                    "at": instant.isoformat(),
                    "event_id": event.event_id,
                    "channel": event.channel,
                }
            )
    return steps


def step_key(segment_id: str, step: Mapping[str, Any]) -> str:
    if step["kind"] == "advance":
        return f"{segment_id}-s{step['index']:04d}-advance"
    return f"{segment_id}-s{step['index']:04d}-ev-{step['event_id']}"


# --------------------------------------------------------------------- run state
class RunState:
    def __init__(self, base: Path) -> None:
        self.base = base
        self.run_dir = base / "run"
        self.decisions_dir = base / "decisions"
        self.snapshots_dir = base / "snapshots"
        self.trace_path = base / "trace" / "trace.jsonl"
        self.state_path = self.run_dir / "state.json"
        self.db_path = self.run_dir / "world.sqlite"
        self.backup_path = self.run_dir / "world.step-backup.sqlite"
        self.pending_path = self.run_dir / "pending.json"
        for directory in (
            self.run_dir,
            self.decisions_dir,
            self.snapshots_dir,
            self.trace_path.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if self.state_path.exists():
            return _read_json(self.state_path)
        return {}

    def save(self, state: Mapping[str, Any]) -> None:
        _write_json(self.state_path, state)


def decisions_path(state: RunState, key: str) -> Path:
    return state.decisions_dir / f"{key}.decisions.jsonl"


# ------------------------------------------------------------------ target build
def observation_rules():
    from aios_core.contracts.enums import WakeSource
    from aios_core.wake import ObservationWakeRule

    return (
        ObservationWakeRule(
            rule_id="rule.studio_climate_change",
            wake_source=WakeSource.MECHANICAL_CHANGE,
            source_kind="sensor_studio_climate",
            modality="numeric_change",
            dedupe_metadata_keys=("series_id",),
            priority=60,
            cooldown_seconds=6 * 3600,
        ),
        ObservationWakeRule(
            rule_id="rule.father_care_note",
            wake_source=WakeSource.WATCH_MATCH,
            source_kind="care_note",
            dedupe_metadata_keys=("external_record_id",),
            priority=70,
            cooldown_seconds=0,
        ),
    )


def source_specs():
    from aios_core.contracts.enums import SourceClass
    from aios_core.ingest import SourceAdapterSpec

    def spec(kind: str, dimension: str, modality: str, cls=SourceClass.USER):
        return SourceAdapterSpec(
            adapter_id=f"moyin.{kind}.v1",
            source_kind=kind,
            dimension=dimension,
            source_class=cls,
            default_modality=modality,
        )

    return {
        "calendar": spec("calendar", "dim:schedule", "structured_record"),
        "order": spec("order", "dim:money", "structured_record"),
        "group_message": spec("group_message", "dim:social", "text"),
        "call_log": spec("call_log", "dim:social", "structured_record"),
        "care_note": spec("care_note", "dim:family", "text"),
        "delivery": spec("delivery", "dim:logistics", "structured_record"),
        "bank": spec("bank", "dim:money", "structured_record"),
        "lab_report": spec("lab_report", "dim:craft", "text"),
        "news_push": spec("news_push", "dim:noise", "text"),
        "photo_description": spec("photo_description", "dim:craft", "image_caption"),
    }


def build_target(
    state: RunState, *, require_fresh: bool
) -> tuple[CurrentCoreHabitationTarget, BridgeHolder]:
    from aios_core.review import ReviewSchedulePolicy

    holder = BridgeHolder()
    target = CurrentCoreHabitationTarget(
        model_id=MODEL_ID,
        subject_id=SUBJECT_ID,
        db_path=state.db_path,
        model_handler=TurnHandlerShell(holder),
        round_summary_handler=RoundSummaryHandlerShell(holder),
        dimension_summary_handler=DimensionSummaryHandlerShell(holder),
        source_specs=source_specs(),
        observation_wake_rules=observation_rules(),
        review_policy=ReviewSchedulePolicy(interval_hours=24.0, lookback_hours=72.0),
        require_fresh=require_fresh,
    )
    return target, holder


# ------------------------------------------------------------------------ driver
def ingest_decoy(state: RunState, events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Subject-isolation probe: another subject's facts live in the SAME World."""
    from aios_core.ingest import RealityIngestService, RealityRecord
    from aios_core.query.search import WorldSearchIndex
    from aios_core.storage.sqlite_store import SQLiteWorldStore

    store = SQLiteWorldStore(state.db_path)
    index = WorldSearchIndex(state.db_path, store=store)
    index.rebuild()
    service = RealityIngestService(store=store, index=index, subject_id=DECOY_SUBJECT_ID)
    spec = source_specs()["group_message"]
    receipts = []
    for raw in events:
        at = parse_instant(str(raw["occurred_at"]))
        receipt = service.ingest_record(
            spec,
            RealityRecord(
                external_record_id=str(raw["event_id"]),
                occurred_at=at,
                received_at=at,
                value=raw["payload"],
                modality="text",
                source_locator=f"habitation://{DECOY_SUBJECT_ID}/group_message/{raw['event_id']}",
                provenance={"decoy_subject_isolation_probe": True},
            ),
        )
        receipts.append(
            {
                "event_id": raw["event_id"],
                "subject_id": DECOY_SUBJECT_ID,
                "observation_id": receipt.observation_id,
                "world_revision": receipt.world_revision,
            }
        )
    return receipts


def run_segment(args: argparse.Namespace) -> int:
    state = RunState(BASE_DIR)
    existing = state.load()
    segment_id = args.segment
    segment_dir = BASE_DIR / "life" / segment_id

    events = load_life(segment_dir)
    steps = build_steps(events, args.roll_hour, args.roll_minute)
    decoy_events = _read_jsonl(segment_dir / "decoy.jsonl") if (
        segment_dir / "decoy.jsonl"
    ).exists() else []

    fresh = not state.db_path.exists()
    target, holder = build_target(state, require_fresh=fresh)

    if existing.get("segment_id") != segment_id:
        cursor_step = 0
    elif existing.get("next_step_key") is None and "next_step_key" in existing:
        cursor_step = len(steps)
    else:
        wanted = existing.get("next_step_key")
        cursor_step = 0
        for candidate in steps:
            if step_key(segment_id, candidate) == wanted:
                cursor_step = candidate["index"]
                break
        else:
            if wanted:
                raise RuntimeError(
                    f"durable cursor {wanted!r} is absent from the regenerated step "
                    "list; refuse to guess a resume position"
                )
    if existing.get("segment_id") == segment_id and existing.get("clock"):
        cursor_time = parse_instant(existing["clock"])
    elif existing.get("clock"):
        cursor_time = parse_instant(existing["clock"])
    else:
        cursor_time = None

    log: list[dict[str, Any]] = []
    if decoy_events and cursor_step == 0:
        log.append({"kind": "decoy_ingest", "receipts": ingest_decoy(state, decoy_events)})
        target, holder = build_target(state, require_fresh=False)

    # Re-anchor the virtual clock from durable state (never move it backwards).
    if cursor_time is not None:
        current = target.clock
        if current is None:
            target.advance_to(cursor_time)
        elif current < cursor_time:
            log.append(
                {
                    "kind": "clock_regap",
                    "restored_clock": current.isoformat(),
                    "cursor": cursor_time.isoformat(),
                }
            )
            target.advance_to(cursor_time)

    while cursor_step < len(steps):
        step = steps[cursor_step]
        key = step_key(segment_id, step)
        stale_pending = existing.get("pending")
        if isinstance(stale_pending, Mapping) and stale_pending.get("step_key") == key:
            # A previous attempt stopped mid-step: its partial writes are discarded
            # and the step is re-executed with the decisions already authored.
            restore_db(state.db_path, state.backup_path)
            log.append({"kind": "restored_step_backup", "step_key": key})
        else:
            backup_db(state.db_path, state.backup_path)

        bridge = ResidentBridge(
            model_id=MODEL_ID,
            step_key=key,
            source=JournalDecisionSource(decisions_path(state, key)),
            snapshots_dir=state.snapshots_dir,
            segment_id=segment_id,
            simulated_at=step["at"],
            world_revision_reader=target.store.current_world_revision,
            run_id=RUN_ID,
        )
        holder.current = bridge

        try:
            if step["kind"] == "advance":
                result = target.advance_to(parse_instant(step["at"]))
                record = {"kind": "advance", "at": step["at"], "result": _shrink_advance(result)}
            else:
                life_event = _find_event(events, step["event_id"])
                from tests.habitation.harness import ResidentEvent

                result = target.handle_event(
                    ResidentEvent(
                        event_id=life_event.event_id,
                        occurred_at=life_event.occurred_at,
                        channel=life_event.channel,
                        payload=life_event.payload,
                        metadata=life_event.metadata,
                    )
                )
                record = {"kind": "event", "event_id": life_event.event_id, "channel": life_event.channel, "result": result}
        except ResidentPending as pending:
            state.save(
                {
                    **existing,
                    "run_id": RUN_ID,
                    "segment_id": segment_id,
                    "cursor_step": cursor_step,
                    "next_step_key": key,
                    "clock": existing.get("clock") or step["at"],
                    "pending": pending.checkpoint,
                    "world_revision": int(target.store.current_world_revision()),
                }
            )
            _write_json(state.pending_path, pending.checkpoint)
            print("=== RESIDENT CHECKPOINT REQUIRED ===")
            print(canonical_json(pending.checkpoint))
            print("--- snapshot payload ---")
            print(
                json.dumps(
                    _read_json(Path(pending.checkpoint["snapshot_path"]))["payload"],
                    ensure_ascii=False,
                    indent=1,
                    sort_keys=True,
                )
            )
            return 2
        finally:
            holder.current = None

        for entry in bridge.served:
            _append_jsonl(
                state.trace_path,
                {
                    "run_id": RUN_ID,
                    "segment_id": segment_id,
                    "step_key": key,
                    "checkpoint_id": entry["checkpoint_id"],
                    "kind": entry["kind"],
                    "simulated_at": step["at"],
                    "model_id": MODEL_ID,
                    "reviewer_id": REVIEWER_ID,
                    "resident_id": RESIDENT_ID,
                    "replayed_authored_decision": entry["replayed"],
                    "input_fingerprint": entry["input_fingerprint"],
                    "input_fingerprint_at_pending": _pending_fingerprint(
                        state, entry["checkpoint_id"]
                    ),
                    "world_revision_before": entry["world_revision_before"],
                    "world_revision_after": int(target.store.current_world_revision()),
                    "decision": entry["decision"],
                },
            )

        record["world_revision"] = int(target.store.current_world_revision())
        record["checkpoints"] = len(bridge.served)
        log.append(record)
        cursor_step += 1
        existing = {
            **existing,
            "run_id": RUN_ID,
            "segment_id": segment_id,
            "cursor_step": cursor_step,
            "next_step_key": (
                step_key(segment_id, steps[cursor_step])
                if cursor_step < len(steps)
                else None
            ),
            "clock": step["at"],
            "pending": None,
            "world_revision": int(target.store.current_world_revision()),
            "index_watermark": int(target.index.watermark()),
        }
        state.save(existing)

    print("=== SEGMENT STEPS EXHAUSTED ===")
    print(json.dumps(log, ensure_ascii=False, indent=1, sort_keys=True))
    return 0


def _pending_fingerprint(state: RunState, checkpoint_id: str) -> str | None:
    """Fingerprint rendered at the moment the runtime first stopped for the Resident.

    A replayed step re-renders the snapshot; Core mints a fresh opaque Observation
    id for the current utterance, so the replay fingerprint can differ in that one
    field. Both digests are preserved so the evidence stays auditable.
    """
    path = state.snapshots_dir / f"{checkpoint_id}.snapshot.json"
    if not path.exists():
        return None
    return str(_read_json(path).get("input_fingerprint"))


def _find_event(events: Sequence[LifeEvent], event_id: str) -> LifeEvent:
    for event in events:
        if event.event_id == event_id:
            return event
    raise KeyError(event_id)


def _shrink_advance(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "from": result.get("from"),
        "to": result.get("to"),
        "background_cycles": result.get("background_cycles"),
        "world_revision": result.get("world_revision"),
        "periodic_reviews": result.get("periodic_reviews"),
        "task_cycles": result.get("task_cycles"),
        "dimension_summaries": result.get("dimension_summaries"),
    }


# ---------------------------------------------------------------------- reports
def status(args: argparse.Namespace) -> int:
    state = RunState(BASE_DIR)
    if not state.db_path.exists():
        print("no world yet")
        return 0
    target, _holder = build_target(state, require_fresh=False)
    snapshot = target.audit_snapshot()
    counts = snapshot["object_counts"]
    trace = _read_jsonl(state.trace_path)
    print(
        json.dumps(
            {
                "state": state.load(),
                "world_revision": snapshot["world_revision"],
                "index_watermark": snapshot["index_watermark"],
                "clock": snapshot["clock"],
                "object_counts": counts,
                "session_turns": snapshot["session_turns"],
                "event_count": len(snapshot["event_log"]),
                "trace_checkpoints": len(trace),
                "trace_by_kind": _count_by(trace, "kind"),
                "decisions_files": len(list(state.decisions_dir.glob("*.jsonl"))),
            },
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        )
    )
    return 0


def _count_by(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        out[str(row.get(key))] = out.get(str(row.get(key)), 0) + 1
    return dict(sorted(out.items()))


def checkpoint(args: argparse.Namespace) -> int:
    state = RunState(BASE_DIR)
    st = state.load()
    target, _holder = build_target(state, require_fresh=False)
    snapshot = target.audit_snapshot()
    trace = _read_jsonl(state.trace_path)

    seg_dir = BASE_DIR / "segments" / args.segment
    seg_dir.mkdir(parents=True, exist_ok=True)
    world_copy = seg_dir / "world.sqlite"
    backup_db(state.db_path, world_copy)
    import gzip

    world_gz = seg_dir / "world.sqlite.gz"
    with world_copy.open("rb") as src, gzip.open(world_gz, "wb", compresslevel=9) as dst:
        shutil.copyfileobj(src, dst)
    world_copy.unlink()

    manifest = {
        "habitation_run_id": RUN_ID,
        "reviewer_id": REVIEWER_ID,
        "resident_id": RESIDENT_ID,
        "subject_id": SUBJECT_ID,
        "decoy_subject_id": DECOY_SUBJECT_ID,
        "segment_id": args.segment,
        "segment_ordinal": args.ordinal,
        "tested_main_sha": args.main_sha,
        "review_branch": args.branch,
        "segment_simulated_start": args.start,
        "segment_simulated_end": args.end,
        "cumulative_simulated_days": args.days,
        "next_event_cursor": st.get("cursor_step"),
        "next_life_event": args.next_event,
        "cumulative_resident_cognition_checkpoints": len(trace),
        "trace_checkpoints_by_kind": _count_by(trace, "kind"),
        "world_artifact": f"segments/{args.segment}/world.sqlite.gz",
        "world_artifact_sha256": sha256_file(world_gz),
        "world_revision": int(snapshot["world_revision"]),
        "index_watermark": int(snapshot["index_watermark"]),
        "simulated_time_cursor": snapshot["clock"],
        "object_counts": snapshot["object_counts"],
        "session_turns": snapshot["session_turns"],
        "observable_events_delivered": len(snapshot["event_log"]),
        "background_cycles": sum(
            int(item.get("background_cycles") or 0) for item in snapshot["background_log"]
        ),
        "periodic_reviews_run": sum(
            len(item.get("periodic_reviews") or []) for item in snapshot["background_log"]
        ),
        "model_id": MODEL_ID,
        "provider_provenance": snapshot["provider_provenance"],
        "previous_checkpoint_sha256": args.previous,
        "notes": args.notes,
    }
    manifest_path = seg_dir / "checkpoint.json"
    _write_json(manifest_path, manifest)
    manifest["checkpoint_manifest_sha256"] = sha256_file(manifest_path)
    _write_json(BASE_DIR / "checkpoint.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="advance the life until a Resident checkpoint")
    run_parser.add_argument("--segment", required=True)
    run_parser.add_argument("--roll-hour", type=int, default=4)
    run_parser.add_argument("--roll-minute", type=int, default=0)
    run_parser.set_defaults(func=run_segment)

    status_parser = sub.add_parser("status", help="print World + trace counters")
    status_parser.set_defaults(func=status)

    cp = sub.add_parser("checkpoint", help="freeze a durable segment checkpoint")
    cp.add_argument("--segment", required=True)
    cp.add_argument("--ordinal", type=int, required=True)
    cp.add_argument("--main-sha", required=True)
    cp.add_argument("--branch", required=True)
    cp.add_argument("--start", required=True)
    cp.add_argument("--end", required=True)
    cp.add_argument("--days", required=True)
    cp.add_argument("--next-event", default="")
    cp.add_argument("--previous", default="")
    cp.add_argument("--notes", default="")
    cp.set_defaults(func=checkpoint)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
