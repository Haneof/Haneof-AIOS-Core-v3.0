"""Does this endpoint actually use the tools array?

The native-tools work was justified by one run on one model. On another model the
same code produced zero tool calls in six turns, which means the whole array was
pure payload cost. "Does this model call tools" is therefore a property to
measure per endpoint, not an assumption to carry across models.

Usage:
    python tools/model_probe.py --base-url http://127.0.0.1:8080/v1 \
        --model grok-4.6 --api-key ... --turns 6

Exit code is 0 when the model called at least once, 1 when it never did — so it
can gate a decision in a script rather than requiring someone to read the output.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aios_core.query.search import WorldSearchIndex  # noqa: E402
from aios_core.runtime.cognitive_runtime import ModelDirective  # noqa: E402
from aios_core.runtime.grok_provider import (  # noqa: E402
    GrokProviderConfig,
    GrokStreamingProvider,
    select_native_tools,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime  # noqa: E402
from aios_core.storage.sqlite_store import SQLiteWorldStore  # noqa: E402

# One statement that must produce a write if the model is going to write at all.
PROBE_TEXT = "我叫老王，在东莞做23cm柔性屏手环，跟我说话别用敬语。"


def _snapshot():  # type: ignore[no-untyped-def]
    captured: dict = {}

    def handler(snap):  # type: ignore[no-untyped-def]
        captured["snap"] = snap
        return ModelDirective(response="ok")

    tmp = Path(tempfile.mkdtemp())
    store = SQLiteWorldStore(str(tmp / "w.sqlite"))
    index = WorldSearchIndex(str(tmp / "i.sqlite"), store=store)
    index.rebuild()
    FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=handler,
        subject_id="user_1",
        recent_turn_limit=2,
    ).run_turn(
        session_id="probe",
        turn_index=1,
        user_input=PROBE_TEXT,
        occurred_at=datetime.now(timezone.utc).replace(microsecond=0),
    )
    return captured["snap"]


def run(args: argparse.Namespace) -> int:
    snapshot = _snapshot()
    tools = select_native_tools(snapshot.capability_catalog)
    payload_chars = len(json.dumps(tools, ensure_ascii=False))
    print(f"tools advertised : {len(tools)} ({payload_chars} chars)")
    print(f"user text        : {PROBE_TEXT}")
    print(f"model            : {args.model} @ {args.base_url}\n", flush=True)

    provider = GrokStreamingProvider(
        GrokProviderConfig(
            base_url=args.base_url,
            api_key=args.api_key or "",
            default_model=args.model,
            timeout_seconds=args.timeout,
            max_output_tokens=args.max_output_tokens,
        )
    )

    messages = [
        {"role": "system", "content": "You are a personal assistant on a wearable band."},
        {"role": "user", "content": PROBE_TEXT},
    ]

    calls = 0
    for index in range(1, args.turns + 1):
        try:
            completion = provider.stream_chat_with_tools(
                messages, model=args.model, tools=tools
            )
        except Exception as exc:  # noqa: BLE001 - the probe reports, it does not raise
            print(f"  turn {index}: ERROR {type(exc).__name__}: {exc}", flush=True)
            continue
        names = [call.name for call in completion.tool_calls]
        calls += len(names)
        detail = ", ".join(names) if names else (completion.text or "").strip()[:80]
        print(f"  turn {index}: {'CALL' if names else 'none'}  {detail}", flush=True)

    rate = f"{calls > 0 and 1 or 0}/{args.turns}"
    print(f"\nturns with at least one tool call: {rate}")
    if calls:
        print("verdict: this model uses the tools array — keep it advertised")
    else:
        print(
            "verdict: this model ignores the tools array — set AIOS_NATIVE_TOOLS=off "
            "for this endpoint, the payload is pure cost"
        )
    return 0 if calls else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key", default=None, help="Omit for loopback endpoints.")
    parser.add_argument("--turns", type=int, default=6)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--max-output-tokens", type=int, default=900)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
