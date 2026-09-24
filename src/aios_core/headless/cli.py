"""Command-line entrypoint for one writable AIOS Core headless process."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

from aios_core.runtime.background_attempt import (
    BackgroundModelAttemptBlocked,
    BackgroundModelExecutionInDoubt,
    BackgroundModelResponsePending,
)
from aios_core.runtime.turn_execution import (
    TurnAlreadyCompleted,
    TurnExecutionInDoubt,
    TurnInputConflict,
)
from aios_core.storage.sqlite_store import StoreError

from .core import (
    HeadlessConfig,
    HeadlessConfigurationError,
    HeadlessCore,
    HeadlessWriterBusy,
    load_model_handler,
)
from .recovery import (
    RecoveryError,
    backup_world,
    rebuild_index,
    recovery_status,
    restore_world,
)


def _iso_time(raw: str | None) -> datetime:
    if raw is None:
        return datetime.now(timezone.utc)
    text = raw.strip()
    if not text:
        raise ValueError("timestamp must not be blank")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def _json_value(raw: str) -> Any:
    if raw.startswith("@"):
        return json.loads(Path(raw[1:]).read_text(encoding="utf-8"))
    return json.loads(raw)


def _emit(value: Any, *, stream: Any = sys.stdout) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str), file=stream)


def _global_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aios-core-headless",
        description="Minimal installable headless wrapper around AIOS FusedTurnRuntime.",
    )
    parser.add_argument(
        "--world",
        default=os.getenv("AIOS_WORLD_PATH"),
        help="Persistent SQLite World path (or AIOS_WORLD_PATH).",
    )
    parser.add_argument(
        "--index",
        default=os.getenv("AIOS_INDEX_PATH"),
        help="Rebuildable search-index SQLite path; defaults beside World.",
    )
    parser.add_argument(
        "--lock",
        default=os.getenv("AIOS_LOCK_PATH"),
        help=(
            "Validation-only writer lease path; if supplied it must equal "
            "<canonical-world>.writer.lock (or AIOS_LOCK_PATH)."
        ),
    )
    parser.add_argument(
        "--subject",
        default=os.getenv("AIOS_SUBJECT_ID", "user_1"),
        help="Runtime subject id.",
    )
    parser.add_argument(
        "--model-handler",
        default=os.getenv("AIOS_MODEL_HANDLER"),
        help="Existing ModelHandler as module:attribute (or AIOS_MODEL_HANDLER).",
    )
    parser.add_argument(
        "--round-summary-handler",
        default=os.getenv("AIOS_ROUND_SUMMARY_HANDLER"),
        help="Optional existing round-summary callable as module:attribute.",
    )
    parser.add_argument(
        "--dimension-summary-handler",
        default=os.getenv("AIOS_DIMENSION_SUMMARY_HANDLER"),
        help="Optional existing dimension-summary callable as module:attribute.",
    )

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Open the configured World and report operational status.")
    sub.add_parser(
        "recovery-status",
        help="Inspect World/schema/index recovery state without invoking a model provider.",
    )
    sub.add_parser(
        "rebuild-index",
        help="Rebuild the non-authoritative search projection atomically from World truth.",
    )
    backup = sub.add_parser(
        "backup",
        help="Create a coherent SQLite online-backup snapshot of the World.",
    )
    backup.add_argument("--to", required=True, dest="backup_to")
    restore = sub.add_parser(
        "restore",
        help="Restore a backup into the new --world path; existing Worlds are never overwritten.",
    )
    restore.add_argument("--from-backup", required=True, dest="restore_from")

    turn = sub.add_parser("turn", help="Submit one ordinary user turn.")
    turn.add_argument("--session", required=True)
    turn.add_argument("--turn-index", required=True, type=int)
    turn.add_argument("--text", required=True)
    turn.add_argument("--at", help="Aware ISO-8601 occurrence time; defaults to now.")
    turn.add_argument("--token-budget", type=int)

    ingest = sub.add_parser("ingest", help="Ingest one external reality fact.")
    ingest.add_argument(
        "--adapter-json",
        required=True,
        help="SourceAdapterSpec JSON, or @path to a JSON file.",
    )
    ingest.add_argument(
        "--record-json",
        required=True,
        help="RealityRecord JSON, or @path to a JSON file.",
    )

    due = sub.add_parser("due", help="Process bounded existing Wake/Review due work.")
    due.add_argument("--at", help="Aware ISO-8601 processing time; defaults to now.")
    due.add_argument("--max-wakes", type=int, default=8)
    due.add_argument("--skip-periodic-review", action="store_true")
    due.add_argument("--token-budget", type=int)

    inspect_turn = sub.add_parser(
        "inspect-turn",
        help="Inspect durable user-turn recovery state without provider invocation.",
    )
    inspect_turn.add_argument("--session", required=True)
    inspect_turn.add_argument("--turn-index", required=True, type=int)
    inspect_turn.add_argument("--text", required=True)
    inspect_turn.add_argument("--at", required=True)

    return parser


def _build_recovery_config(args: argparse.Namespace) -> HeadlessConfig:
    if not args.world:
        raise HeadlessConfigurationError(
            "persistent World path is required via --world or AIOS_WORLD_PATH"
        )
    return HeadlessConfig(
        world_path=Path(args.world),
        index_path=None if not args.index else Path(args.index),
        lock_path=None if not args.lock else Path(args.lock),
        subject_id=args.subject,
    )


def _build_core(args: argparse.Namespace) -> HeadlessCore:
    if not args.world:
        raise HeadlessConfigurationError(
            "persistent World path is required via --world or AIOS_WORLD_PATH"
        )
    if not args.model_handler:
        raise HeadlessConfigurationError(
            "model adapter is required via --model-handler or AIOS_MODEL_HANDLER"
        )
    model_handler = load_model_handler(args.model_handler)
    round_summary = (
        None
        if not args.round_summary_handler
        else load_model_handler(args.round_summary_handler)
    )
    dimension_summary = (
        None
        if not args.dimension_summary_handler
        else load_model_handler(args.dimension_summary_handler)
    )
    return HeadlessCore(
        config=HeadlessConfig(
            world_path=Path(args.world),
            index_path=None if not args.index else Path(args.index),
            lock_path=None if not args.lock else Path(args.lock),
            subject_id=args.subject,
        ),
        model_handler=model_handler,
        round_summary_handler=round_summary,
        dimension_summary_handler=dimension_summary,
    )


def _run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command in {"recovery-status", "rebuild-index", "backup", "restore"}:
        config = _build_recovery_config(args)
        if args.command == "recovery-status":
            return recovery_status(config)
        if args.command == "rebuild-index":
            return rebuild_index(config)
        if args.command == "backup":
            return backup_world(config, args.backup_to)
        if args.command == "restore":
            return restore_world(config, args.restore_from)
        raise RuntimeError(f"unsupported recovery command: {args.command}")

    core = _build_core(args)
    with core:
        if args.command == "status":
            return core.status()

        if args.command == "turn":
            result = core.submit_user_turn(
                session_id=args.session,
                turn_index=args.turn_index,
                user_input=args.text,
                occurred_at=_iso_time(args.at),
                token_budget=args.token_budget,
            )
            return {
                "status": "turn_completed",
                "response": result.runtime.response,
                "silenced": result.runtime.silenced,
                "termination_reason": result.runtime.termination_reason,
                "model_rounds": result.runtime.model_rounds,
                "world_revision": result.conversation_commit.world_revision,
                "user_observation_id": result.conversation_commit.user_observation_id,
                "assistant_observation_id": result.conversation_commit.assistant_observation_id,
                "idempotent_replay": result.conversation_commit.idempotent_replay,
                "summary_error": result.continuity_summary_error,
                "summary_commits": len(result.continuity_summary_commits),
            }

        if args.command == "ingest":
            adapter = _json_value(args.adapter_json)
            record = _json_value(args.record_json)
            if not isinstance(adapter, dict) or not isinstance(record, dict):
                raise ValueError("adapter-json and record-json must decode to JSON objects")
            receipt = core.ingest_external_fact(adapter=adapter, record=record)
            return {
                "status": "fact_ingested",
                "receipt_type": type(receipt).__name__,
                **asdict(receipt),
            }

        if args.command == "due":
            result = core.process_due_work(
                now=_iso_time(args.at),
                max_wakes=args.max_wakes,
                include_periodic_review=not args.skip_periodic_review,
                token_budget=args.token_budget,
            )
            wakes = [
                {
                    "wake_id": item.wake.wake_id,
                    "revision": item.wake.revision,
                    "state": item.wake.state,
                    "delivery_response": item.delivery_response,
                    "delivery_suppressed": item.delivery_suppressed,
                    "termination_reason": (
                        None
                        if item.runtime is None
                        else item.runtime.termination_reason
                    ),
                }
                for item in result.wakes
            ]
            review = None
            if result.periodic_review is not None:
                item = result.periodic_review
                review = {
                    "review_id": item.request.review_id,
                    "wake_id": item.wake.wake_id,
                    "revision": item.wake.revision,
                    "state": item.wake.state,
                    "termination_reason": (
                        None
                        if item.runtime is None
                        else item.runtime.termination_reason
                    ),
                }
            status = core.status()
            return {
                "status": "due_processed",
                "wakes": wakes,
                "periodic_review": review,
                "world_revision": status["world_revision"],
                "index_watermark": status["index_watermark"],
            }

        if args.command == "inspect-turn":
            runtime = core.runtime
            if runtime is None:
                raise RuntimeError("headless Core is not started")
            inspection = runtime.inspect_turn_execution(
                session_id=args.session,
                turn_index=args.turn_index,
                user_input=args.text,
                occurred_at=_iso_time(args.at),
            )
            return {
                "status": "turn_inspected",
                "execution_id": inspection.execution_id,
                "state": inspection.state,
                "recovery_disposition": inspection.recovery_disposition,
                "retry_authorized": inspection.retry_authorized,
                "retry_count": inspection.retry_count,
                "reconciliation_evidence": inspection.reconciliation_evidence,
                "assistant_ref": (
                    None
                    if inspection.assistant_ref is None
                    else inspection.assistant_ref.model_dump(mode="json")
                ),
                "model_attempts": [
                    {
                        "attempt_id": attempt.attempt_id,
                        "state": attempt.state,
                        "work_kind": attempt.work_kind,
                        "model_round_index": attempt.model_round_index,
                        "provider": attempt.provider,
                        "model": attempt.model,
                        "provider_request_id": attempt.provider_request_id,
                        "recovery_disposition": attempt.recovery_disposition,
                    }
                    for attempt in inspection.model_attempts
                ],
            }

    raise RuntimeError(f"unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = _global_parser()
    args = parser.parse_args(argv)
    try:
        _emit(_run(args))
        return 0
    except HeadlessConfigurationError as exc:
        _emit(
            {"status": "configuration_error", "error": str(exc)},
            stream=sys.stderr,
        )
        return 2
    except HeadlessWriterBusy as exc:
        _emit({"status": "writer_busy", "error": str(exc)}, stream=sys.stderr)
        return 3
    except (
        TurnExecutionInDoubt,
        BackgroundModelAttemptBlocked,
        BackgroundModelExecutionInDoubt,
        BackgroundModelResponsePending,
        TimeoutError,
    ) as exc:
        _emit(
            {
                "status": "reconciliation_required",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
            stream=sys.stderr,
        )
        return 4
    except TurnAlreadyCompleted as exc:
        _emit(
            {
                "status": "turn_already_completed",
                "state": exc.state,
                "assistant_ref": (
                    None
                    if exc.assistant_ref is None
                    else exc.assistant_ref.model_dump(mode="json")
                ),
            },
            stream=sys.stderr,
        )
        return 5
    except TurnInputConflict as exc:
        _emit(
            {
                "status": "turn_input_conflict",
                "error": str(exc),
            },
            stream=sys.stderr,
        )
        return 6
    except StoreError as exc:
        _emit(
            {
                "status": "storage_error",
                "error_code": str(exc.code),
                "error": str(exc),
                "context": getattr(exc, "context", None),
            },
            stream=sys.stderr,
        )
        return 7
    except RecoveryError as exc:
        _emit(
            {
                "status": "recovery_error",
                "error": str(exc),
            },
            stream=sys.stderr,
        )
        return 9
    except (ValueError, TypeError, OSError) as exc:
        _emit(
            {
                "status": "operation_error",
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
            stream=sys.stderr,
        )
        return 8


if __name__ == "__main__":
    raise SystemExit(main())
