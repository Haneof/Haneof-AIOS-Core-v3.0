"""探针：今日总览调用方式试验（thinking 开关 / max_tokens）。"""
import json
import sys
import time
import urllib.request
from datetime import timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "cleaning_ab"))
sys.path.insert(0, "src")

import harness  # noqa: E402
from verify_summary import DIMENSION_SOURCE_CAPS, SUBJECT, cleaning_admission, DATES  # noqa: E402

from aios_core.query.search import WorldSearchIndex  # noqa: E402
from aios_core.storage.sqlite_store import SQLiteWorldStore  # noqa: E402
from aios_core.summaries import MultiScaleSummaryScheduler  # noqa: E402


def main() -> None:
    thinking = sys.argv[1] == "nothink" if len(sys.argv) > 1 else True
    max_tokens = int(sys.argv[2]) if len(sys.argv) > 2 else 3000

    store = SQLiteWorldStore(HERE / "_tmp_echo_0.db")
    index = WorldSearchIndex(HERE / "_tmp_echo_0.db", store=store)
    sched = MultiScaleSummaryScheduler(
        store=store, index=index, subject_id=SUBJECT,
        summary_handler=lambda p: "", source_admission=cleaning_admission,
        dimension_source_caps=DIMENSION_SOURCE_CAPS,
    )
    wins = sched._digest_candidate_windows(now=DATES[0] + timedelta(days=1))
    p = sched.digest_service.prepare(window_start=wins[0][0], window_end=wins[0][1])
    lines = [f"- ({s.metadata.get('dimension', '?')}) {s.text}" for s in p.sources]
    body = (
        "下面是用户 2026-10-28 一天里 9 个维度的 DAY 总结。请写一段中文「今日总览」，"
        "把这天跨维度发生过什么整合成一天全貌，保留关键细节，不编造，"
        "直接输出正文不超过 300 字。\n\n" + "\n".join(lines)
    )
    body_json = {
        "model": harness.PRIMARY_MODEL,
        "messages": [{"role": "user", "content": body}],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    if not thinking:
        body_json["chat_template_kwargs"] = {"thinking": False}
    req = urllib.request.Request(
        harness.PRIMARY_BASE_URL + "/chat/completions",
        data=json.dumps(body_json).encode("utf-8"),
        headers={"Authorization": f"Bearer {harness.PRIMARY_API_KEY}",
                 "Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            payload = json.load(resp)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {type(exc).__name__}: {exc} ({time.time()-t0:.0f}s)")
        return
    choice = payload["choices"][0]
    msg = choice["message"]
    print(f"finish={choice.get('finish_reason')} 用时={time.time()-t0:.0f}s "
          f"usage={payload.get('usage')}")
    rc = msg.get("reasoning_content") or ""
    if rc:
        print(f"[reasoning {len(rc)} 字] {rc[:120]}...")
    content = msg.get("content") or ""
    print(f"[content {len(content)} 字]")
    print(content[:500])


if __name__ == "__main__":
    main()
