"""真实端点验证：CROSS_LINK 是否只做归属、不越界、不编造。

为什么单独验证这一件事。契约测试能证明"提示词里写了不许造维度"，但证明不了
模型真的照做。跨维归属最危险的失败不是报错，而是安静地写出一条像事实的判断，
所以这里用真实模型输出对 ground truth 核一遍。

评分口径：
- out_of_catalogue 必须为 0（越界即失败：它意味着落库层会整批拒绝）
- forbidden_hits 必须为 0（玩笑/噪声被归到任何维度即失败）
- recall 允许不满：宁缺毋滥是提示词里明确鼓励的行为
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "experiments" / "cleaning_ab"))
sys.path.insert(0, str(_ROOT / "experiments" / "prompt_separation"))

from aios_core.prompts import (  # noqa: E402
    DimensionProfile,
    PromptRenderParams,
    TaskKind,
    render_task_prompt,
    task_runtime,
)
from aios_core.query.search import derive_dimensions  # noqa: E402

from verify_task_prompts import call_model  # noqa: E402

# (id, 文本, 预期可归入的维度集合；空集 = 不该归到任何维度)
SAMPLES = [
    ("m01", "阿杰邀请我下周六去参加他的婚礼", {"dim:social"}),
    ("m02", "今天菜市场买排骨花了八十块", {"dim:expense"}),
    ("m03", "我妈打电话说我爸体检结果出来了，血糖偏高", {"dim:health", "dim:family"}),
    ("m04", "明天世界末日了哈哈哈", set()),
    ("m05", "电视里在放综艺，笑声很大", set()),
    ("m06", "下周三要去杭州拍一组旅拍，客户是家民宿", {"dim:work"}),
    ("m07", "膝盖有点疼，贴了膏药", {"dim:health"}),
    ("m08", "跟小林约了周末去看她爸妈", {"dim:social", "dim:family"}),
]

CATALOGUE = (
    DimensionProfile(dimension_key="dim:social", name="社交关系"),
    DimensionProfile(dimension_key="dim:expense", name="生活开支"),
    DimensionProfile(dimension_key="dim:health", name="健康"),
    DimensionProfile(dimension_key="dim:family", name="家庭"),
    DimensionProfile(dimension_key="dim:work", name="工作"),
)


def main() -> int:
    records = tuple(
        {"id": rid, "t": "2026-11-03 09:00", "dimension": "dim:user_ai_interaction", "text": text}
        for rid, text, _ in SAMPLES
    )
    prompt = render_task_prompt(
        TaskKind.CROSS_LINK,
        params=PromptRenderParams(
            records=records,
            dimensions=CATALOGUE,
            window_start="2026-11-03",
            window_end="2026-11-03",
            extra={"max_links": 20},
        ),
    )
    print(f"prompt_chars={len(prompt)} est_in_tokens={round(len(prompt)/1.6)}")

    runtime = task_runtime(TaskKind.CROSS_LINK)
    result = call_model(
        [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "只输出 JSON 数组。"},
        ],
        runtime.max_output_tokens,
        "cross-link",
        TaskKind.CROSS_LINK,
    )
    print(
        f"ok={result['ok']} rounds={result.get('rounds')} "
        f"max_tokens={result.get('max_tokens')} out_chars={result.get('output_chars')} "
        f"est_out={result.get('est_output_tokens')}"
    )
    text = result.get("text") or ""
    if not result["ok"]:
        print("FAILED: no usable response")
        print(text[:500])
        return 1

    payload = _extract_json(text)
    if payload is None:
        print("FAILED: response is not JSON")
        print(text[:800])
        return 1
    if isinstance(payload, dict):
        payload = payload.get("links") or []

    allowed = {profile.dimension_key for profile in CATALOGUE}
    expected = {rid: dims for rid, _, dims in SAMPLES}
    forbidden = {rid for rid, _, dims in SAMPLES if not dims}

    out_of_catalogue: list[dict] = []
    forbidden_hits: list[dict] = []
    hits: dict[str, set[str]] = {}
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        target = str(entry.get("target_dimension") or "")
        rid = str(entry.get("id") or "")
        if target not in allowed:
            out_of_catalogue.append(entry)
            continue
        if rid in forbidden:
            forbidden_hits.append(entry)
            continue
        hits.setdefault(rid, set()).add(target)

    matched = sum(1 for rid, got in hits.items() if got & expected.get(rid, set()))
    wrong_axis = {rid: sorted(got) for rid, got in hits.items() if not (got & expected.get(rid, set()))}
    total_expected = sum(1 for _, _, dims in SAMPLES if dims)

    print("\n=== 输出 ===")
    print(json.dumps(payload, ensure_ascii=False, indent=1)[:2000])
    print("\n=== 评分 ===")
    print(f"links={len(payload)} 命中={matched}/{total_expected} 归错轴={len(wrong_axis)}")
    print(f"越界维度={len(out_of_catalogue)} 禁归命中={len(forbidden_hits)}")
    if wrong_axis:
        print("归错轴明细:", json.dumps(wrong_axis, ensure_ascii=False))
    if forbidden_hits:
        print("禁归明细:", json.dumps(forbidden_hits, ensure_ascii=False))

    # 归属必须是"事实复述"，不能变成评价或推断
    judgement_marks = ("说明他", "可能是因为", "表明他", "意味着", "反映出", "可见他")
    judged = [
        entry for entry in payload
        if isinstance(entry, dict)
        and any(mark in str(entry.get("statement") or "") for mark in judgement_marks)
    ]
    print(f"写成结论的条数={len(judged)}")
    if judged:
        print(json.dumps(judged, ensure_ascii=False, indent=1)[:600])

    verdict = (
        not out_of_catalogue
        and not forbidden_hits
        and not judged
        and matched >= max(1, total_expected // 2)
    )
    print("\nVERDICT:", "PASS" if verdict else "FAIL")
    return 0 if verdict else 1


def _extract_json(text: str):
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except ValueError:
        pass
    start, end = stripped.find("["), stripped.rfind("]")
    if 0 <= start < end:
        try:
            return json.loads(stripped[start : end + 1])
        except ValueError:
            pass
    start, end = stripped.find("{"), stripped.rfind("}")
    if 0 <= start < end:
        try:
            return json.loads(stripped[start : end + 1])
        except ValueError:
            pass
    return None


if __name__ == "__main__":
    raise SystemExit(main())
