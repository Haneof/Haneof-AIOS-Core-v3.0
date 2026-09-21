"""Resident file-bridge: stop at every semantic checkpoint and wait for the model.

Hard boundary enforced by this module
-------------------------------------
This bridge NEVER decides anything. It is the mechanical counterpart of the rule
"a program may simulate the outside world, it may not simulate the Resident mind".

Its only jobs are:

1. render the *exact* object the real Core handed to the Resident
   (``RuntimeSnapshot`` / ``RoundSummaryRequest`` / ``DimensionSummaryInput``)
   into a JSON file plus a SHA-256 input fingerprint;
2. announce that a semantic checkpoint is open (write ``run/pending.json``);
3. hand back a decision that the Resident model authored into the append-only
   decision journal.

There is no keyword table, no expected answer, no pseudo-model, no template and
no heuristic in this file. If no authored decision exists, the bridge either
raises :class:`ResidentPending` (step mode) or blocks until one appears
(daemon mode). It never invents one.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective, RuntimeSnapshot

KIND_TURN = "turn_directive"
KIND_ROUND_SUMMARY = "round_summary"
KIND_DIMENSION_SUMMARY = "dimension_summary"

VALID_KINDS = (KIND_TURN, KIND_ROUND_SUMMARY, KIND_DIMENSION_SUMMARY)


class ResidentPending(Exception):
    """Raised when a new semantic checkpoint requires the Resident model itself."""

    def __init__(self, checkpoint: Mapping[str, Any]) -> None:
        super().__init__(checkpoint["checkpoint_id"])
        self.checkpoint = dict(checkpoint)


def jsonable(value: Any) -> Any:
    """Best-effort structural JSON conversion; never summarizes, never drops text."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {key: jsonable(item) for key, item in dataclasses.asdict(value).items()}
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return jsonable(dump(mode="json"))
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [jsonable(item) for item in value]
    if isinstance(value, (bytes, bytearray)):
        return repr(bytes(value))
    return str(value)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def render_turn_snapshot(snapshot: RuntimeSnapshot) -> dict[str, Any]:
    return {
        "user_input": snapshot.user_input,
        "wake_reason": snapshot.wake_reason,
        "round_index": snapshot.round_index,
        "remaining_tool_rounds": snapshot.remaining_tool_rounds,
        "cockpit": jsonable(snapshot.cockpit),
        "capability_catalog_full": jsonable(snapshot.capability_catalog),
        "capability_history": [jsonable(item) for item in snapshot.capability_history],
    }


def read_journal(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            # A partially flushed append is not a decision yet; ignore the tail.
            break
    return entries


class JournalDecisionSource:
    """Step mode: stop the process, let the operator come back later."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def peek(self, index: int) -> Mapping[str, Any] | None:
        entries = read_journal(self.path)
        return entries[index] if index < len(entries) else None

    def announce(self, record: Mapping[str, Any]) -> None:
        raise ResidentPending(record)


class BlockingDecisionSource:
    """Daemon mode: keep the live runtime in memory while the Resident thinks.

    Object ids Core mints during the active turn stay valid, so the Resident can
    pin the current utterance as evidence without the harness changing semantics.
    """

    def __init__(
        self,
        path: Path,
        pending_path: Path,
        poll_seconds: float = 0.5,
        on_announce: Any = None,
    ) -> None:
        self.path = Path(path)
        self.pending_path = Path(pending_path)
        self.poll_seconds = poll_seconds
        self.on_announce = on_announce

    def peek(self, index: int) -> Mapping[str, Any] | None:
        entries = read_journal(self.path)
        return entries[index] if index < len(entries) else None

    def announce(self, record: Mapping[str, Any]) -> None:
        self.pending_path.parent.mkdir(parents=True, exist_ok=True)
        self.pending_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        index = int(record["checkpoint_index"])
        if self.on_announce is not None:
            self.on_announce(dict(record))
        print(
            f"PENDING {record['checkpoint_id']} kind={record['kind']} "
            f"simulated_at={record['simulated_at']}",
            flush=True,
        )
        while self.peek(index) is None:
            time.sleep(self.poll_seconds)
        print(f"DECISION_RECEIVED {record['checkpoint_id']}", flush=True)


class ResidentBridge:
    """Serves authored Resident decisions and announces every new checkpoint."""

    def __init__(
        self,
        *,
        model_id: str,
        step_key: str,
        source: Any,
        snapshots_dir: Path,
        segment_id: str,
        simulated_at: str,
        world_revision_reader: Any,
        run_id: str,
    ) -> None:
        self.model_id = model_id
        self.step_key = step_key
        self.segment_id = segment_id
        self.simulated_at = simulated_at
        self.run_id = run_id
        self._source = source
        self._snapshots_dir = Path(snapshots_dir)
        self._world_revision_reader = world_revision_reader
        self._served: list[dict[str, Any]] = []

    @property
    def served(self) -> list[dict[str, Any]]:
        return list(self._served)

    def _world_revision(self) -> int | None:
        try:
            return int(self._world_revision_reader())
        except Exception:  # audit must never break a live turn
            return None

    def turn_directive(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        return self._serve(KIND_TURN, render_turn_snapshot(snapshot))

    def round_summary(self, request: Any) -> str:
        return self._serve(KIND_ROUND_SUMMARY, jsonable(request))

    def dimension_summary(self, request: Any) -> str:
        return self._serve(KIND_DIMENSION_SUMMARY, jsonable(request))

    def _serve(self, kind: str, payload: Mapping[str, Any]) -> Any:
        index = len(self._served)
        checkpoint_id = f"{self.step_key}#cp{index:02d}"
        world_revision_before = self._world_revision()
        input_fingerprint = fingerprint(payload)

        entry = self._source.peek(index)
        if entry is None:
            self._snapshots_dir.mkdir(parents=True, exist_ok=True)
            snapshot_path = self._snapshots_dir / f"{checkpoint_id}.snapshot.json"
            snapshot_path.write_text(
                json.dumps(
                    {
                        "checkpoint_id": checkpoint_id,
                        "run_id": self.run_id,
                        "segment_id": self.segment_id,
                        "step_key": self.step_key,
                        "checkpoint_index": index,
                        "kind": kind,
                        "model_id": self.model_id,
                        "simulated_at": self.simulated_at,
                        "world_revision_before": world_revision_before,
                        "input_fingerprint": input_fingerprint,
                        "payload": payload,
                    },
                    ensure_ascii=False,
                    indent=1,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            # announce() either raises (step mode) or blocks until I answer.
            self._source.announce(
                {
                    "checkpoint_id": checkpoint_id,
                    "step_key": self.step_key,
                    "checkpoint_index": index,
                    "kind": kind,
                    "simulated_at": self.simulated_at,
                    "world_revision_before": world_revision_before,
                    "input_fingerprint": input_fingerprint,
                    "snapshot_path": str(snapshot_path),
                }
            )
            entry = self._source.peek(index)
            if entry is None:  # pragma: no cover - announce guarantees an entry
                raise RuntimeError("decision source returned no entry after announce")

        if entry.get("kind") != kind:
            raise RuntimeError(
                f"authored decision {index} for {self.step_key} is "
                f"{entry.get('kind')!r} but the runtime asked for {kind!r}"
            )
        decision = entry["decision"]
        self._served.append(
            {
                "checkpoint_id": checkpoint_id,
                "kind": kind,
                "decision": decision,
                "world_revision_before": world_revision_before,
                "input_fingerprint": input_fingerprint,
            }
        )
        return _materialize(kind, decision)


def _materialize(kind: str, decision: Mapping[str, Any]) -> Any:
    if kind == KIND_TURN:
        calls_raw = decision.get("capability_calls")
        response = decision.get("response")
        silence = bool(decision.get("silence", False))
        calls: tuple[CapabilityCall, ...] = ()
        if calls_raw:
            calls = tuple(
                CapabilityCall(
                    name=str(item["name"]),
                    arguments=dict(item.get("arguments") or {}),
                    call_id=item.get("call_id"),
                )
                for item in calls_raw
            )
        return ModelDirective(
            capability_calls=calls,
            response=None if response is None else str(response),
            silence=silence,
        )
    if kind in (KIND_ROUND_SUMMARY, KIND_DIMENSION_SUMMARY):
        content = decision.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"{kind} decision must carry non-blank 'content'")
        return content
    raise ValueError(f"unknown decision kind: {kind}")
