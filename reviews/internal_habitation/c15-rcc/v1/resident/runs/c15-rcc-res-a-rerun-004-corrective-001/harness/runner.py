"""Corrective Resident A Runner — Phase A sequential reality habitation harness.

Enforces:
- RC f20f2edfa7af00d0286493fd15196ca9503bc315 execution baseline.
- Exchange Bridge request/response durable publication protocols.
- Sequential release operator reveal -> ingest -> ack -> index -> watches -> advance -> resident decision -> checkpoint.
- Cursor 1..13 strictly; cursor 14 NEVER revealed.
- No fixture semantics, no expected answers, no keyword branching.
- Fail closed on any exchange ambiguity or integrity break.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Sequence

from aios_core.contracts.enums import ObjectType, SourceClass, WakeSource
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import as_utc, canonical_utc_iso
from aios_core.query.search import WorldSearchIndex
from aios_core.runtime.capabilities import CapabilityCall, CapabilityResult
from aios_core.runtime.cognitive_runtime import (
    ModelCallProvenance,
    ModelDirective,
    ModelUsage,
    RuntimeSnapshot,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.storage.sqlite_store import SQLiteWorldStore
from aios_core.summaries.dimension_summary import DimensionSummaryInput
from aios_core.wake import Step0GateInput

from exchange_bridge import (
    ExchangeBlockedError,
    ExchangeBridge,
    ExchangeLedger,
    RequestIdMismatchError,
    UnpublishedRequestError,
    utc_iso_now,
)


def _canonical_json(obj: Any) -> str:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _safe_json(obj: Any) -> Any:
    return json.loads(_canonical_json(obj))


def find_repo_root(start: Path | None = None) -> Path:
    p = (start or Path(__file__)).resolve()
    while p != p.parent:
        if (p / ".git").exists() or (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("Repo root not found")


class CorrectiveResidentRunner:
    def __init__(
        self,
        *,
        run_dir: Path | str,
        repo_root: Path | str | None = None,
        subject_id: str = "user_1",
        resident_session_id: str = "resident-a-rerun-004-corr-001-session",
        conversation_session_id: str = "session-user-corr-001",
        resident_decision_callback: Callable[[str, Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> None:
        self.run_dir = Path(run_dir).resolve()
        self.repo_root = Path(repo_root).resolve() if repo_root else find_repo_root(self.run_dir)
        self.subject_id = subject_id.strip()
        self.resident_session_id = resident_session_id.strip()
        self.conversation_session_id = conversation_session_id.strip()
        self.resident_decision_callback = resident_decision_callback

        self.requests_dir = self.run_dir / "decision_requests"
        self.responses_dir = self.run_dir / "decision_responses"
        self.events_dir = self.run_dir / "events"
        self.receipts_dir = self.run_dir / "receipts"
        self.checkpoints_dir = self.run_dir / "checkpoints"
        self.logs_dir = self.run_dir / "logs"

        for d in (
            self.run_dir,
            self.requests_dir,
            self.responses_dir,
            self.events_dir,
            self.receipts_dir,
            self.checkpoints_dir,
            self.logs_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

        self.world_db_path = self.run_dir / "world.db"
        self.release_state_path = self.run_dir / "release-state.json"
        self.ledger_path = self.run_dir / "exchange_ledger.jsonl"
        self.identity_path = self.run_dir / "identity.json"
        self.runtime_state_path = self.run_dir / "runtime_state.json"

        self.ledger = ExchangeLedger(self.ledger_path)
        self.bridge = ExchangeBridge(
            requests_dir=self.requests_dir,
            responses_dir=self.responses_dir,
            ledger=self.ledger,
        )

        self.release_op_script = (
            self.repo_root / "reviews/internal_habitation/c15-rcc/v1/release/release_operator.py"
        )
        self.mech_ingest_script = (
            self.repo_root / "reviews/internal_habitation/c15-rcc/v1/release/mechanical_ingest_adapter.py"
        )
        self.canon_convo_script = (
            self.repo_root / "reviews/internal_habitation/c15-rcc/v1/release/canonical_conversation_ingest.py"
        )

        self.store = SQLiteWorldStore(self.world_db_path)
        self.index = WorldSearchIndex(self.world_db_path, store=self.store)
        self.runtime = FusedTurnRuntime(
            store=self.store,
            index=self.index,
            model_handler=self._handle_model_directive,
            subject_id=self.subject_id,
            dimension_summary_handler=self._handle_dimension_summary,
            max_tool_rounds=8,
        )

        self._request_counter = 0
        self._user_turn_counter = 0
        self._clock: datetime | None = None
        self._restore_counters()

    def _restore_counters(self) -> None:
        if self.ledger_path.exists():
            records = self.ledger.verify()
            self._request_counter = len(
                [r for r in records if r.event == "request_published"]
            )
        if self.runtime_state_path.exists():
            try:
                state = json.loads(self.runtime_state_path.read_text(encoding="utf-8"))
                self._user_turn_counter = state.get("user_turn_counter", 0)
                if state.get("clock"):
                    self._clock = as_utc(datetime.fromisoformat(state["clock"]), "clock")
            except Exception:
                pass

    def _save_runtime_state(self, cursor: int) -> None:
        state = {
            "cursor": cursor,
            "user_turn_counter": self._user_turn_counter,
            "clock": self._clock.isoformat() if self._clock else None,
            "world_revision": int(self.store.current_world_revision()),
            "index_watermark": self.index.current_watermark(),
            "updated_at": utc_iso_now(),
        }
        self.runtime_state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def init_release_state(self) -> None:
        if not self.release_state_path.exists():
            env = os.environ.copy()
            env["PYTHONPATH"] = f"{self.repo_root / 'src'}:{env.get('PYTHONPATH', '')}"
            cmd = [
                sys.executable,
                str(self.release_op_script),
                "init",
                "--phase",
                "A",
                "--state",
                str(self.release_state_path),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if proc.returncode != 0:
                raise RuntimeError(f"release_operator init failed: {proc.stderr}")

        if not self.identity_path.exists():
            identity = {
                "run_id": "c15-rcc-res-a-rerun-004-corrective-001",
                "task_id": "C15-RCC-RES-A-RERUN-004-CORRECTIVE-001",
                "role": "Real Resident AI — Fresh Corrective Resident A",
                "resident_session_id": self.resident_session_id,
                "conversation_session_id": self.conversation_session_id,
                "subject_id": self.subject_id,
                "frozen_rc_software": "f20f2edfa7af00d0286493fd15196ca9503bc315",
                "frozen_core_tree": "9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623",
                "frozen_tests_tree": "7e33b5ef8432370234965d3ccd61248c703c4019",
                "created_at": utc_iso_now(),
            }
            self.identity_path.write_text(
                json.dumps(identity, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

    def _next_request_id(self, kind: str, snippet: str) -> str:
        self._request_counter += 1
        h = hashlib.sha256(snippet.encode("utf-8")).hexdigest()[:8]
        return f"req-{self._request_counter:04d}-{kind}-{h}"

    def _exchange_roundtrip(
        self,
        request_id: str,
        request_data: Mapping[str, Any],
        poll_interval: float = 0.2,
        timeout_seconds: float = 300.0,
    ) -> dict[str, Any]:
        """Publish request through bridge, await/call resident response, then consume."""
        req_path, req_sha, req_rec = self.bridge.publish_request(
            request_id,
            request_data,
        )

        if self.resident_decision_callback is not None:
            # Resident AI decision handler produces response
            response_payload = self.resident_decision_callback(
                request_id,
                dict(request_data),
            )
            self.bridge.publish_response(
                request_id,
                req_sha,
                response_payload,
            )
        else:
            # Await external publication by Resident AI
            start_t = time.time()
            while not self.bridge.can_recover_published_response(request_id, req_sha):
                if time.time() - start_t > timeout_seconds:
                    raise ExchangeBlockedError(
                        f"Timeout waiting for resident response to {request_id}"
                    )
                time.sleep(poll_interval)

        consumed_data, consumed_rec = self.bridge.consume_response(request_id, req_sha)
        return consumed_data

    def _handle_model_directive(self, snapshot: RuntimeSnapshot) -> ModelDirective:
        kind = "model_directive"
        snippet = f"{snapshot.wake_reason}:{snapshot.round_index}:{snapshot.user_input[:20]}"
        request_id = self._next_request_id(kind, snippet)

        cap_history_json = [
            {
                "call_id": c.call_id,
                "name": c.name,
                "arguments": c.arguments,
                "result": c.result,
                "error": c.error,
                "duration_seconds": c.duration_seconds,
            }
            for c in snapshot.capability_history
        ]

        req_data = {
            "request_id": request_id,
            "kind": kind,
            "round_index": snapshot.round_index,
            "remaining_tool_rounds": snapshot.remaining_tool_rounds,
            "wake_reason": snapshot.wake_reason,
            "user_input": snapshot.user_input,
            "cockpit": _safe_json(snapshot.cockpit),
            "capability_history": cap_history_json,
            "capability_catalog": _safe_json(snapshot.capability_catalog),
            "model_attempt_id": snapshot.model_attempt_id,
            "outbound_relay_id": snapshot.outbound_relay_id,
        }

        resp_data = self._exchange_roundtrip(request_id, req_data)

        # Deserialize ModelDirective
        calls = []
        for call_dict in resp_data.get("capability_calls") or []:
            calls.append(
                CapabilityCall(
                    name=str(call_dict["name"]),
                    arguments=dict(call_dict.get("arguments") or {}),
                    call_id=(
                        str(call_dict["call_id"])
                        if call_dict.get("call_id")
                        else None
                    ),
                )
            )

        resp_text = resp_data.get("response")
        silence = bool(resp_data.get("silence", False))

        # Anonymous local handler: provider=None, model=None, usage=None
        return ModelDirective(
            capability_calls=tuple(calls),
            response=resp_text,
            silence=silence,
            usage=None,
            provenance=None,
        )

    def _handle_dimension_summary(self, input: DimensionSummaryInput) -> str:
        kind = "dimension_summary"
        snippet = f"{input.dimension}:{input.window_start.isoformat()}:{input.window_end.isoformat()}"
        request_id = self._next_request_id(kind, snippet)

        sources_json = [
            {
                "observation_id": s.observation_id,
                "revision": s.revision,
                "occurred_at": s.occurred_at.isoformat(),
                "value": s.value,
                "source_kind": s.source_kind,
                "modality": s.modality,
                "metadata": _safe_json(s.metadata),
            }
            for s in input.sources
        ]

        req_data = {
            "request_id": request_id,
            "kind": kind,
            "dimension": input.dimension,
            "granularity": input.granularity,
            "window_start": input.window_start.isoformat(),
            "window_end": input.window_end.isoformat(),
            "source_world_revision": input.source_world_revision,
            "sources": sources_json,
            "truncated": input.truncated,
        }

        resp_data = self._exchange_roundtrip(request_id, req_data)
        summary_text = resp_data.get("summary_text")
        if not summary_text or not isinstance(summary_text, str):
            raise ExchangeBlockedError(
                f"Dimension summary {request_id} returned blank or non-string summary_text"
            )
        return summary_text.strip()

    def run_cursor(self, cursor: int) -> dict[str, Any]:
        """Execute one cursor strictly (1..13). Never reveal cursor 14."""
        if cursor < 1 or cursor > 13:
            raise ValueError(f"Cursor {cursor} out of allowed Phase A bounds (1..13)")

        env = os.environ.copy()
        env["PYTHONPATH"] = f"{self.repo_root / 'src'}:{env.get('PYTHONPATH', '')}"

        # 1. Reveal event
        reveal_cmd = [
            sys.executable,
            str(self.release_op_script),
            "reveal",
            "--phase",
            "A",
            "--state",
            str(self.release_state_path),
        ]
        reveal_proc = subprocess.run(reveal_cmd, capture_output=True, text=True, env=env)
        if reveal_proc.returncode != 0:
            raise RuntimeError(f"Cursor {cursor} reveal failed: {reveal_proc.stderr}")

        event = json.loads(reveal_proc.stdout)
        if int(event["sequence"]) != cursor:
            raise ExchangeBlockedError(
                f"Revealed event sequence {event['sequence']} != expected cursor {cursor}"
            )

        event_bytes = reveal_proc.stdout.encode("utf-8")
        event_projection_sha256 = hashlib.sha256(event_bytes).hexdigest()
        event_path = self.events_dir / f"cursor_{cursor:02d}_event.json"
        event_path.write_bytes(event_bytes)

        # 2. Ingest event
        is_user_convo = (
            event.get("source_kind") == "user_ai_interaction"
            or event.get("source_class") == "USER"
        )

        turn_index = None
        if is_user_convo:
            self._user_turn_counter += 1
            turn_index = self._user_turn_counter
            ingest_cmd = [
                sys.executable,
                str(self.canon_convo_script),
                "--world-db",
                str(self.world_db_path),
                "--session-id",
                self.conversation_session_id,
                "--turn-index",
                str(turn_index),
                "--event-file",
                str(event_path),
            ]
        else:
            ingest_cmd = [
                sys.executable,
                str(self.mech_ingest_script),
                "--world-db",
                str(self.world_db_path),
                "--event-file",
                str(event_path),
            ]

        ingest_proc = subprocess.run(ingest_cmd, capture_output=True, text=True, env=env)
        if ingest_proc.returncode != 0:
            raise RuntimeError(f"Cursor {cursor} ingest failed: {ingest_proc.stderr}")

        ingest_receipt_path = self.receipts_dir / f"cursor_{cursor:02d}_ingest_stdout.json"
        ingest_receipt_path.write_text(ingest_proc.stdout, encoding="utf-8")
        ingest_data = json.loads(ingest_proc.stdout)
        ingest_ref = ingest_data["ingest_ref"]

        # 3. Acknowledge event
        ack_cmd = [
            sys.executable,
            str(self.release_op_script),
            "ack",
            "--phase",
            "A",
            "--state",
            str(self.release_state_path),
            "--world-db",
            str(self.world_db_path),
            "--sequence",
            str(cursor),
            "--event-id",
            event["event_id"],
            "--ingest-ref",
            ingest_ref,
        ]
        if is_user_convo:
            ack_cmd.extend(
                [
                    "--conversation-session-id",
                    self.conversation_session_id,
                    "--conversation-turn-index",
                    str(turn_index),
                ]
            )

        ack_proc = subprocess.run(ack_cmd, capture_output=True, text=True, env=env)
        if ack_proc.returncode != 0:
            raise RuntimeError(f"Cursor {cursor} ack failed: {ack_proc.stderr}")

        ack_receipt_path = self.receipts_dir / f"cursor_{cursor:02d}_ack_stdout.json"
        ack_receipt_path.write_text(ack_proc.stdout, encoding="utf-8")

        # 4. Catch up index
        self.index.catch_up()

        # 5. Native AttentionWatch evaluation (Section 二十)
        obs_id, rev_str = ingest_ref.split("@")
        obs_ref = ObjectRef(object_id=obs_id, revision=int(rev_str))
        watch_signals = self.runtime.attention_watches.evaluate_observation(obs_ref)
        self.index.catch_up()

        # 6. Advance virtual time and run due background work
        occurred_at = as_utc(
            datetime.fromisoformat(event["occurred_at"]),
            "occurred_at",
        )
        self._clock = occurred_at

        # Task wakes
        task_wakes = self.runtime.execution_world.wake_due_tasks(now=occurred_at)
        self.index.catch_up()

        # Pending wakes
        wake_results = []
        for wake in self.runtime.wake_bus.pending_wakes():
            if wake.wake_source in {WakeSource.USER_INTERACTION}:
                continue
            cur = self.runtime.wake_bus.current_wake(wake.object_id)
            if cur.wake_state.value in {"new", "queued"}:
                w_res = self.runtime.run_wake(
                    wake_ref=ObjectRef(object_id=cur.object_id, revision=cur.revision),
                    now=occurred_at,
                )
                wake_results.append(
                    {
                        "wake_id": cur.object_id,
                        "state": w_res.wake.state,
                    }
                )
        self.index.catch_up()

        # Periodic review
        review_result = None
        review_run = self.runtime.run_periodic_review(now=occurred_at)
        if review_run is not None:
            review_result = {
                "review_id": review_run.request.review_id,
                "wake_id": review_run.wake.wake_id,
            }
        self.index.catch_up()

        # Multi-scale dimension summaries
        dim_summary_commits = []
        if self.runtime.dimension_summary_scheduler is not None:
            sum_res = self.runtime.run_due_dimension_summaries(now=occurred_at, max_jobs=64)
            dim_summary_commits = [asdict(c) for c in sum_res.commits]
        self.index.catch_up()

        # 7. User conversation turn if applicable
        turn_result_data = None
        if is_user_convo:
            turn_res = self.runtime.run_turn(
                session_id=self.conversation_session_id,
                turn_index=turn_index,
                user_input=event["resident_visible_payload"],
                occurred_at=occurred_at,
            )
            turn_result_data = {
                "turn_index": turn_index,
                "response": turn_res.runtime.response,
                "silenced": turn_res.runtime.silenced,
                "capabilities": [c.name for c in turn_res.runtime.capability_history],
                "termination_reason": turn_res.runtime.termination_reason,
            }
        self.index.catch_up()

        self._save_runtime_state(cursor)

        checkpoint = {
            "cursor": cursor,
            "event_id": event["event_id"],
            "occurred_at": event["occurred_at"],
            "event_projection_sha256": event_projection_sha256,
            "ingest_ref": ingest_ref,
            "world_revision": int(self.store.current_world_revision()),
            "index_watermark": self.index.current_watermark(),
            "is_user_conversation": is_user_convo,
            "turn_result": turn_result_data,
            "task_wakes": [asdict(t) for t in task_wakes],
            "wake_results": wake_results,
            "periodic_review": review_result,
            "dimension_summary_commits": dim_summary_commits,
            "watch_signals_emitted": len(watch_signals),
            "timestamp": utc_iso_now(),
        }
        ckpt_path = self.checkpoints_dir / f"checkpoint_cursor_{cursor:02d}.json"
        ckpt_path.write_text(
            json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        return checkpoint


def main():
    parser = argparse.ArgumentParser(description="Corrective Resident A Runner")
    parser.add_argument("--run-dir", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--repo-root", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_p = subparsers.add_parser("init")

    cursor_p = subparsers.add_parser("run-cursor")
    cursor_p.add_argument("--cursor", type=int, required=True)
    cursor_p.add_argument("--resident-module", type=str, default=None)

    verify_p = subparsers.add_parser("verify-ledger")

    args = parser.parse_args()

    callback = None
    if getattr(args, "resident_module", None):
        spec = importlib.util.spec_from_file_location("resident_decision_module", args.resident_module)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load resident module from {args.resident_module}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        callback = getattr(mod, "resident_decide", None)

    runner = CorrectiveResidentRunner(
        run_dir=args.run_dir,
        repo_root=args.repo_root,
        resident_decision_callback=callback,
    )

    if args.command == "init":
        runner.init_release_state()
        print("Initialized fresh release state and identities.")
    elif args.command == "run-cursor":
        ckpt = runner.run_cursor(args.cursor)
        print(f"Cursor {args.cursor} completed successfully: world_rev={ckpt['world_revision']}")
    elif args.command == "verify-ledger":
        records = runner.ledger.verify()
        print(f"Ledger verified: {len(records)} records, unbroken sequence and hash chain.")


if __name__ == "__main__":
    main()
