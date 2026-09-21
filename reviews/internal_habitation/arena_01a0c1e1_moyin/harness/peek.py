"""Compact renderer for the pending Resident checkpoint (evidence-only tooling).

Prints the *complete* pending payload in a denser layout so the Resident model can
read the whole RuntimeSnapshot without paying for JSON indentation. The static
capability catalog is collapsed after its first sighting.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

BASE = Path(__file__).resolve().parents[1]
PENDING = BASE / "run" / "pending.json"
SEEN_CATALOG = BASE / "run" / ".catalog_seen"


def load_pending() -> tuple[Mapping[str, Any], Mapping[str, Any]] | None:
    if not PENDING.exists():
        return None
    meta = json.loads(PENDING.read_text(encoding="utf-8"))
    record = json.loads(Path(meta["snapshot_path"]).read_text(encoding="utf-8"))
    return meta, record


def render_pending(meta: Mapping[str, Any], record: Mapping[str, Any]) -> None:
    payload = record["payload"]
    print(f"# checkpoint {meta['checkpoint_id']} kind={meta['kind']}")
    print(f"# simulated_at={meta['simulated_at']} world_rev_before={meta['world_revision_before']}")
    print(f"# input_fingerprint={meta['input_fingerprint']}")

    if meta["kind"] != "turn_directive":
        print(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
        return

    cockpit = payload["cockpit"]
    print(f"wake={payload['wake_reason']} round={payload['round_index']} "
          f"rounds_left={payload['remaining_tool_rounds']}")
    print(f"USER_INPUT: {payload['user_input']}")
    print(f"CURRENT_TOPIC: {json.dumps(cockpit.get('current_topic'), ensure_ascii=False)}")
    print(f"AI_IDENTITY: {json.dumps(cockpit.get('ai_identity'), ensure_ascii=False)}")
    print(f"MEMORY_CARDS: {json.dumps(cockpit.get('memory_cards'), ensure_ascii=False)}")
    print(f"RECENT_TURNS: {json.dumps(cockpit.get('recent_turns'), ensure_ascii=False)}")
    print(f"CONV_SUMMARIES: {json.dumps(cockpit.get('conversation_summaries'), ensure_ascii=False)}")
    task = cockpit.get("task_context", {})
    for key in sorted(task):
        print(f"TASK.{key}: {json.dumps(task[key], ensure_ascii=False)}")
    print(f"BUDGET: {cockpit.get('token_budget')} est={cockpit.get('estimated_tokens')} "
          f"truncated={cockpit.get('truncated')}")
    history = payload.get("capability_history") or []
    print("CAPABILITY_HISTORY:")
    for item in history:
        print("  " + json.dumps(item, ensure_ascii=False))
    if not history:
        print("  (none)")
    if SEEN_CATALOG.exists():
        print("CAPABILITY_CATALOG_FULL: (unchanged since first sighting)")
    else:
        print("CAPABILITY_CATALOG_FULL:")
        for cap in payload.get("capability_catalog_full", []):
            print("  " + json.dumps(cap, ensure_ascii=False))
        SEEN_CATALOG.parent.mkdir(parents=True, exist_ok=True)
        SEEN_CATALOG.write_text("seen\n", encoding="utf-8")


def main() -> int:
    loaded = load_pending()
    if loaded is None:
        print("(no pending checkpoint)")
        return 0
    meta, record = loaded
    render_pending(meta, record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
