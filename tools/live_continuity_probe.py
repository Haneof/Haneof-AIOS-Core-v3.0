"""Live continuity probe — run a real conversation against a real model.

``p16_recall_bench`` measures recall with a scripted provider. That is the right
tool for regression, and the wrong tool for one question: does a *real* model
actually use the continuity machinery it is given? A scripted provider always
does what the script says, so it cannot answer that.

This probe drives a real OpenAI-compatible endpoint through the full turn
runtime and reports three things per turn:

  * what the model was given (anchor present? anchor content? grounding?)
  * what the model decided to do (capability calls, or a reply, or silence)
  * what actually became durable (claims / goals / tasks / summaries)

and at the end, whether the final answer still knows facts disclosed in turn 1
after they have left the verbatim window.

    python tools/live_continuity_probe.py \\
        --base-url http://127.0.0.1:8081/v1 \\
        --model qwen3.8-27b-coder390-q3lynnstyle16g-mtp \\
        --expect "老王,东莞,23cm"

Exit code is 0 when the probe ran, 1 when the endpoint could not be reached.
The probe never asserts a verdict: a model that forgets is a finding, not a
test failure.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aios_core.contracts.enums import ObjectType  # noqa: E402
from aios_core.query.search import WorldSearchIndex  # noqa: E402
from aios_core.runtime.grok_provider import (  # noqa: E402
    GrokProviderConfig,
    GrokStreamingProvider,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime  # noqa: E402
from aios_core.storage.sqlite_store import SQLiteWorldStore  # noqa: E402

# The disclosure turn, then filler that pushes it out of the verbatim window,
# then the same question the product must be able to answer.
DEFAULT_TURNS: tuple[str, ...] = (
    "我叫老王，在东莞做23cm柔性屏手环，跟我说话别用敬语。",
    "今天天气一般。",
    "你平时喜欢看纪录片吗？",
    "我早上喝了杯咖啡。",
    "珠峰有多高来着？",
    "随便聊两句吧。",
    "我刚才跟你说我是做什么的？在哪个城市？",
)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8081/v1")
    parser.add_argument("--model", default="qwen3.8-27b-coder390-q3lynnstyle16g-mtp")
    parser.add_argument("--api-key", default=None, help="Omit for loopback endpoints.")
    parser.add_argument("--recent-turn-limit", type=int, default=3)
    parser.add_argument("--max-output-tokens", type=int, default=220)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--expect", default="", help="Comma-separated facts the last answer must still know.")
    parser.add_argument("--turns-file", default=None, help="JSON list of user turns, overriding the default script.")
    parser.add_argument("--report", default=None, help="Write the full JSON report here.")
    return parser.parse_args(argv)


def _load_turns(path: str | None) -> tuple[str, ...]:
    if not path:
        return DEFAULT_TURNS
    loaded = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(loaded, list) or not all(isinstance(x, str) for x in loaded):
        raise SystemExit("--turns-file must contain a JSON list of strings")
    return tuple(loaded)


def _section(text: str, header: str, *, limit: int = 900) -> str:
    """Return one rendered prompt section, for the report."""

    index = text.find(header)
    if index < 0:
        return ""
    return text[index : index + limit]


def _attribute_failures(outcomes: Sequence[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Split capability failures by who has to fix them.

    A model that cannot fill in a schema is not a kernel bug, and treating it as
    one means loosening evidence semantics for every caller. Keeping the two
    buckets separate is what stops the test rig from shaping the product.
    """

    model_side = [o for o in outcomes if not o["ok"] and o["error_code"] == "CAPABILITY_ARGUMENT_ERROR"]
    kernel_side = [
        o for o in outcomes if not o["ok"] and o["error_code"] not in {"CAPABILITY_ARGUMENT_ERROR", None}
    ]
    succeeded = [o for o in outcomes if o["ok"]]
    return {"succeeded": succeeded, "model_side": model_side, "kernel_side": kernel_side}


def run(args: argparse.Namespace) -> int:
    tmp = Path(tempfile.mkdtemp(prefix="aios-live-"))
    store = SQLiteWorldStore(str(tmp / "world.sqlite"))
    index = WorldSearchIndex(str(tmp / "index.sqlite"), store=store)
    index.rebuild()

    provider = GrokStreamingProvider(
        GrokProviderConfig(
            base_url=args.base_url,
            api_key=args.api_key or "loopback-no-auth",
            default_model=args.model,
            timeout_seconds=args.timeout,
            max_output_tokens=args.max_output_tokens,
        )
    )

    sent: list[dict[str, Any]] = []
    call_seconds: list[float] = []
    original_stream_chat = provider.stream_chat

    def spy(messages, **kwargs):  # type: ignore[no-untyped-def]
        sent.clear()
        sent.extend(messages)
        started = time.perf_counter()
        try:
            return original_stream_chat(messages, **kwargs)
        finally:
            # A single turn can issue several model calls (capability round
            # trips). Recording each one is what separates "the model is slow"
            # from "the provider retried a hung stream".
            call_seconds.append(round(time.perf_counter() - started, 2))

    provider.stream_chat = spy  # type: ignore[method-assign]

    inner = provider.as_model_handler(model=args.model)
    calls_by_turn: list[list[dict[str, Any]]] = []
    replies: list[str] = []
    prompts: list[str] = []
    labels: list[str] = []
    outcomes: list[dict[str, Any]] = []

    def handler(snapshot):  # type: ignore[no-untyped-def]
        # Results of the previous round's capability calls arrive here. Recording
        # them is what separates "this model cannot fill in the schema" from "the
        # kernel broke" — a distinction that decides whether anything in src/ should
        # be touched at all.
        for result in getattr(snapshot, "capability_history", ()) or ():
            outcomes.append(
                {
                    "name": getattr(result, "name", ""),
                    "ok": bool(getattr(result, "ok", False)),
                    "error_code": getattr(result, "error_code", None),
                    "error_message": str(getattr(result, "error_message", "") or "")[:200],
                }
            )

        directive = inner(snapshot)
        system = sent[0]["content"] if sent else ""
        prompts.append(system)
        # A turn can issue more than one model call (capability round trips). Label
        # each call by the turn it belongs to, otherwise the report silently
        # attributes round 2 of turn 3 to turn 4.
        current_turn["round"] += 1
        labels.append(f"T{current_turn['index']}.{current_turn['round']}")
        calls_by_turn.append(
            [
                {"name": call.name, "arguments": {k: str(v)[:120] for k, v in call.arguments.items()}}
                for call in directive.capability_calls
            ]
        )
        replies.append(str(directive.response or ""))
        return directive

    runtime = FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=handler,
        subject_id="user_1",
        recent_turn_limit=args.recent_turn_limit,
    )

    turns = _load_turns(args.turns_file)
    base = datetime.now(timezone.utc).replace(microsecond=0)
    latencies: list[float] = []
    failures: list[str] = []
    current_turn = {"index": 0, "round": 0}

    for i, text in enumerate(turns, start=1):
        current_turn["index"] = i
        current_turn["round"] = 0
        started = time.perf_counter()
        error = ""
        try:
            runtime.run_turn(
                session_id="live",
                turn_index=i,
                user_input=text,
                occurred_at=base + timedelta(minutes=i),
            )
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            failures.append(f"T{i}: {error}")
        latencies.append(time.perf_counter() - started)
        print(f"T{i} [{latencies[-1]:5.1f}s] user: {text}", flush=True)
        if error:
            print(f"    !! turn aborted: {error}", flush=True)

    print("\n=== what the model was given ===", flush=True)
    for label, prompt in zip(labels, prompts):
        anchor = _section(prompt, "CONTINUITY ANCHOR", limit=400)
        anchor_body = [
            line for line in anchor.splitlines()[1:] if line.strip().startswith("-")
        ]
        print(
            f"{label}: prompt={len(prompt)}ch anchor_section={'yes' if anchor else 'no'} "
            f"anchor_items={len(anchor_body)} grounding={'yes' if 'THIS TURN — GROUNDING' in prompt else 'no'}",
            flush=True,
        )
        for line in anchor_body[:6]:
            print(f"     {line.strip()[:160]}", flush=True)

    print("\n=== what the model decided ===", flush=True)
    for label, calls, reply in zip(labels, calls_by_turn, replies):
        if calls:
            print(f"{label}: {len(calls)} capability call(s)", flush=True)
            for call in calls:
                print(f"     -> {call['name']}({json.dumps(call['arguments'], ensure_ascii=False)[:180]})", flush=True)
        elif reply.strip():
            print(f"{label}: reply  {reply.strip()[:220]}", flush=True)
        else:
            print(f"{label}: silence", flush=True)

    print("\n=== what became durable ===", flush=True)
    counts: dict[str, int] = {}
    for kind in (ObjectType.CLAIM, ObjectType.GOAL, ObjectType.TASK, ObjectType.SUMMARY):
        rows = store.list_payloads(object_type=kind, subject_id="user_1")
        counts[kind.value] = len(rows)
        print(f"{kind.value:10s} = {len(rows)}", flush=True)
        for row in rows[:5]:
            statement = row.get("statement") or row.get("title") or row.get("summary") or ""
            print(f"     - {str(statement)[:150]}", flush=True)

    print("\n=== failure attribution ===", flush=True)
    buckets = _attribute_failures(outcomes)
    model_side = buckets["model_side"]
    kernel_side = buckets["kernel_side"]
    succeeded = buckets["succeeded"]
    print(f"capability calls executed : {len(outcomes)} (ok={len(succeeded)})", flush=True)
    print(f"model-side (bad arguments): {len(model_side)}", flush=True)
    print(f"kernel-side (raised)      : {len(kernel_side)}", flush=True)
    if model_side:
        print(
            "  -> the schema was not followed. Fixing this in the kernel means accepting\n"
            "     shapes the model should not be producing; that is a tolerance decision,\n"
            "     not a bug fix. A stronger model usually needs no such tolerance.",
            flush=True,
        )
        for outcome in model_side[:3]:
            print(f"     {outcome['name']}: {outcome['error_message'][:160]}", flush=True)
    if kernel_side:
        print("  -> these are real defects in src/, not model weakness:", flush=True)
        for outcome in kernel_side[:3]:
            print(f"     {outcome['name']}: {outcome['error_code']} {outcome['error_message'][:160]}", flush=True)

    # The last call of the last turn is not always a reply: a turn can end on a
    # capability round trip. The user-visible answer is the last non-empty one.
    final_reply = next((text for text in reversed(replies) if text.strip()), "")
    expected = [token.strip() for token in args.expect.split(",") if token.strip()]
    recalled = [token for token in expected if token in final_reply]
    missed = [token for token in expected if token not in final_reply]

    print("\n=== continuity verdict ===", flush=True)
    print(f"final question: {turns[-1]}", flush=True)
    print(f"final answer  : {final_reply.strip()[:400] or '(none)'}", flush=True)
    if expected:
        print(f"still knows   : {recalled or '(none)'}", flush=True)
        print(f"forgot        : {missed or '(none)'}", flush=True)
    print(f"latency       : min {min(latencies):.1f}s / median {sorted(latencies)[len(latencies)//2]:.1f}s / max {max(latencies):.1f}s", flush=True)
    if call_seconds:
        print(f"model calls   : {len(call_seconds)} total, durations {call_seconds}", flush=True)

    report = {
        "base_url": args.base_url,
        "model": args.model,
        "recent_turn_limit": args.recent_turn_limit,
        "turns": list(turns),
        "latencies_seconds": [round(x, 2) for x in latencies],
        "model_call_seconds": call_seconds,
        "turn_failures": failures,
        "capability_calls": calls_by_turn,
        "capability_outcomes": outcomes,
        "replies": replies,
        "prompt_chars": [len(p) for p in prompts],
        "durable_counts": counts,
        "expected_facts": expected,
        "recalled_facts": recalled,
        "missed_facts": missed,
    }
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nreport written: {args.report}", flush=True)

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run(_parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
