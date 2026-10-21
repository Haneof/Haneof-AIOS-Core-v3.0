"""P16 召回基准防护栏 —— hermetic（无网络、无 API key）回归测试。

背景（本文件锁定的历史事故）：
2026-10-20 发现结构性盲区：项目自身 C15 测试全部使用脚本化 provider（假模型），
没有任何人真正读过拼出来的系统提示词，导致「模型看不到 recent_turns」这个致命
bug 在所有绿灯下潜伏很久。直接诱因是 grok_provider.as_model_handler 曾用
``isinstance(v, (str, int, float, bool))`` 过滤 cockpit，recent_turns（列表）
被静默丢弃，模型从头到尾没见过对话。修复后渲染 RECENT CONVERSATION 段
（见 tests/runtime/test_live_multimodel_habitation.py:531 的范例测试）。

本文件把以下契约固化为离线可复现的回归测试：
1. 提示词渲染锁：as_model_handler 实际发出的系统提示词必须逐字包含
   最近对话（RECENT CONVERSATION 段），经 loopback SSE stub 走真实 HTTP
   请求路径验证（不走猴子补丁）。
2. recent_turns 挤出锁：recent_turn_limit=3、anchor 后灌 4 轮 filler 后，
   anchor 文本必须被挤出 context.recent_turns —— 否则 P16 exhaustion
   场景的「上下文耗尽」是假阳性。
3. 判据函数三分支：_evaluate_constitutional_compliance 的
   PASS / FAIL / NOT_MEASURED 必须严格由观测数据决定。
4. 主题继承探针（观测断言，非通过要求）：上下文耗尽后的指代型追问当前
   丢失主题继承（topic_inherited=False, history_not_needed）——
   这是真实缺口，测试把它固化为可见信号，行为一变即报警。
5. NOT_MEASURED 不许伪装 PASS：观测失败（observation_error）的轮次
   不得让判据变绿灯、退出码不得为 0。

全部 hermetic：loopback 127.0.0.1 stub 或进程内假 ModelHandler，
无外部网络、无 API key、不依赖 AIOS_* 环境变量。
"""

from __future__ import annotations

import json
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator

import pytest

# 与 tools/p16_recall_bench.py 顶部同一手法：把 tools/ 加入导入路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import p16_recall_bench as bench  # noqa: E402

from aios_core.query.search import WorldSearchIndex  # noqa: E402
from aios_core.runtime.cognitive_runtime import (  # noqa: E402
    ModelDirective,
    ModelHandler,
    RuntimeSnapshot,
)
from aios_core.runtime.grok_provider import (  # noqa: E402
    GrokProviderConfig,
    GrokStreamingProvider,
)
from aios_core.runtime.turn_runtime import FusedTurnRuntime  # noqa: E402
from aios_core.storage.sqlite_store import SQLiteWorldStore  # noqa: E402

# 所有 exhaustion 相关测试共用的固定时刻（与 p16 工具一致：同会话共用 occurred_at）。
_FIXED_NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)

# anchor 文本中的独特标记：p16 的 filler 轮次严禁出现该词（否则 exhaustion 命中
# 是假阳性，见 tools/p16_recall_bench.py FILLER_QUESTIONS 注释），因此它出现在
# recent_turns 里当且仅当 anchor 轮本身还在窗口内。
_ANCHOR_MARKER = "23cm 柔性屏手环"

# 第 1 项测试用的「上一轮用户输入原文」：独特字符串，不会在提示词别处偶然出现。
_PRIOR_TURN_TEXT = "请记住：我在杭州做 23cm 柔性屏手环项目，续航 14 天。"


# ---------------------------------------------------------------------------
# hermetic 基础设施：假 ModelHandler / 带 anchor 的真实运行时
# ---------------------------------------------------------------------------


def _fake_model_handler(reply: str = "（假模型）收到。") -> ModelHandler:
    """进程内假 ModelHandler：直接返回 response directive，无任何网络。"""

    def _handler(snapshot: RuntimeSnapshot) -> ModelDirective:
        return ModelDirective(response=reply)

    return _handler


def _build_hermetic_world(tmp_path: Path, *, recent_turn_limit: int = 3) -> FusedTurnRuntime:
    """写 anchor Observation，构造真实 FusedTurnRuntime（假 handler 驱动）。"""
    db_path = str(tmp_path / "guardrail_world.sqlite")
    index_path = str(tmp_path / "guardrail_index.sqlite")
    store = SQLiteWorldStore(db_path)
    bench._write_anchor(store, bench._make_anchor_observation(_FIXED_NOW))
    index = WorldSearchIndex(index_path, store=store)
    index.rebuild()
    return FusedTurnRuntime(
        store=store,
        index=index,
        model_handler=_fake_model_handler(),
        subject_id="user_1",
        recent_turn_limit=recent_turn_limit,
    )


def _run_exhaustion_flow(
    runtime: FusedTurnRuntime, *, session_id: str, filler_rounds: int = 4
) -> tuple[Any, Any, Any]:
    """anchor T1 -> filler N 轮 -> 指代型追问探针，返回 (t1_result, probe_result, probe_index)。

    filler 轮数必须大于 recent_turn_limit，anchor 才会被挤出 RECENT CONVERSATION。
    """
    t1 = runtime.run_turn(
        session_id=session_id,
        turn_index=1,
        user_input=f"请记住这句话：{bench.ANCHOR_FACT}",
        occurred_at=_FIXED_NOW,
    )
    for i in range(filler_rounds):
        runtime.run_turn(
            session_id=session_id,
            turn_index=i + 2,
            user_input=bench.FILLER_QUESTIONS[i % len(bench.FILLER_QUESTIONS)],
            occurred_at=_FIXED_NOW,
        )
    probe_index = filler_rounds + 2
    probe = runtime.run_turn(
        session_id=session_id,
        turn_index=probe_index,
        user_input=bench.RECALL_QUESTION,
        occurred_at=_FIXED_NOW,
    )
    return t1, probe, probe_index


# ---------------------------------------------------------------------------
# 第 1 项：提示词渲染锁（loopback SSE stub，真实 HTTP 请求路径）
# ---------------------------------------------------------------------------


class _PromptCaptureSSEStubHandler(BaseHTTPRequestHandler):
    """OpenAI 兼容 SSE stub：记录完整请求体（含系统提示词），返回最小流。"""

    protocol_version = "HTTP/1.0"

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            payload = {}

        self.server.last_request = payload  # type: ignore[attr-defined]

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        chunks = [
            {"id": "chatcmpl-guard-001", "choices": [{"delta": {"content": "STUB_OK"}}]},
            {
                "id": "chatcmpl-guard-001",
                "choices": [],
                "usage": {"prompt_tokens": 8, "completion_tokens": 2, "total_tokens": 10},
            },
        ]
        for chunk in chunks:
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, *args: Any) -> None:  # 静默测试输出
        return


@pytest.fixture
def prompt_capture_stub_server() -> Iterator[ThreadingHTTPServer]:
    """loopback SSE stub：零外部网络，确定性返回。"""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _PromptCaptureSSEStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_as_model_handler_prompt_carries_verbatim_previous_user_turn(
    prompt_capture_stub_server: ThreadingHTTPServer,
) -> None:
    """提示词渲染锁 —— 防 2026-10-20 recent_turns 召回 bug 复发。

    历史事故：as_model_handler 曾用 isinstance(v, (str, int, float, bool))
    过滤 cockpit，recent_turns 是列表、被静默丢弃，模型从未见过对话，
    于是对用户说「不记得你刚说过的话」，还白烧工具轮重新检索。项目 C15
    测试全用脚本化 provider，没有任何人真读过拼出来的提示词，bug 在全部
    绿灯下潜伏。

    本测试不走猴子补丁：经 loopback SSE stub 走真实 HTTP 请求路径，断言
    as_model_handler 实际发出的 system prompt 逐字包含上一轮用户输入。
    """
    port = prompt_capture_stub_server.server_address[1]
    provider = GrokStreamingProvider(
        GrokProviderConfig(
            base_url=f"http://127.0.0.1:{port}/v1",
            api_key="stub-key-for-tests",
            timeout_seconds=10.0,
        )
    )
    snapshot = RuntimeSnapshot(
        user_input="我刚才让你记住的那句话里，我在哪个城市？",
        wake_reason="user_explicit",
        cockpit={
            "current_topic": "recall",
            "token_budget": 3400,
            "recent_turns": [
                {
                    "turn_index": 1,
                    "user": {"text": _PRIOR_TURN_TEXT},
                    "assistant": {"text": "已记录。"},
                }
            ],
            "memory_cards": [],
        },
        capability_catalog=(),
        capability_history=(),
        round_index=0,
        remaining_tool_rounds=2,
    )

    directive = provider.as_model_handler(model="guard-model")(snapshot)

    # stub 回复被聚合为 response directive，证明请求真的打通了 stub 端点。
    assert isinstance(directive, ModelDirective)
    assert directive.response == "STUB_OK"

    request = prompt_capture_stub_server.last_request
    messages = request["messages"]
    system_prompt = messages[0]["content"]

    assert messages[0]["role"] == "system"
    assert "RECENT CONVERSATION" in system_prompt
    # 核心锁：上一轮用户原文必须逐字出现在系统提示词里。
    assert _PRIOR_TURN_TEXT in system_prompt, (
        "上一轮用户输入被丢弃出系统提示词（recent_turns 召回 bug 复发）"
    )
    assert "[turn 1] user:" in system_prompt
    assert "[turn 1] assistant: 已记录。" in system_prompt
    # 当前轮用户输入作为 user message 发出。
    assert messages[-1]["role"] == "user"
    assert "我在哪个城市" in messages[-1]["content"]


# ---------------------------------------------------------------------------
# 第 2 项：recent_turns 挤出锁
# ---------------------------------------------------------------------------


def test_recent_turns_evict_anchor_after_filler_rounds(tmp_path: Path) -> None:
    """recent_turns 挤出锁 —— 保 P16 exhaustion 场景不是假阳性。

    P16 exhaustion 场景靠「灌 N 轮 filler 把 anchor 挤出 RECENT CONVERSATION」
    来验证系统能改从 WorldSearchIndex 恢复记忆。若挤出没有真实发生（窗口没
    裁对、continuity 一直保留 anchor 轮），追问命中只是复读上下文，整个
    exhaustion 评测都是假阳性。

    用假 handler 驱动真实 FusedTurnRuntime：recent_turn_limit=3、anchor T1
    之后灌 4 轮 filler，断言最后一轮 context.recent_turns 只含最近 3 轮
    filler、完全不含 anchor 文本。
    """
    runtime = _build_hermetic_world(tmp_path, recent_turn_limit=3)
    session_id = "p16_guardrail_exhaustion"

    t1, probe, probe_index = _run_exhaustion_flow(runtime, session_id=session_id, filler_rounds=4)
    assert t1.runtime.termination_reason == "responded"
    assert probe_index == 6

    recent = probe.context.recent_turns
    assert len(recent) == 3, f"recent_turn_limit=3 必须把窗口裁到 3 轮，实际 {len(recent)}"
    indices = [turn["turn_index"] for turn in recent]
    assert indices == [3, 4, 5], f"窗口应只含最近 3 轮 filler，实际 {indices}"

    window_text = json.dumps([dict(turn) for turn in recent], ensure_ascii=False)
    # 窗口必须真的装着最近对话（非空窗口），否则下面的「不含」断言无意义。
    assert "天空为什么呈现蓝色" in window_text, "窗口必须包含最近一轮 filler"
    # 核心锁：anchor 文本必须已被挤出。
    assert _ANCHOR_MARKER not in window_text, (
        "anchor 文本仍留在 recent_turns 内，exhaustion 场景是假阳性"
    )
    assert "杭州" not in window_text
    assert "续航 14 天" not in window_text
    assert 1 not in indices, "anchor 轮（turn 1）不应还在 recent_turns 窗口内"


# ---------------------------------------------------------------------------
# 第 3 项：判据函数三分支（纯函数，直接构造数据，不跑 runtime）
# ---------------------------------------------------------------------------


def _round(**overrides: Any) -> bench.RoundResult:
    """直接构造 RoundResult（判据函数是纯函数，无需真跑 runtime）。"""
    base: dict[str, Any] = dict(
        turn_index=1,
        model="guard-fake",
        latency_sec=0.0,
        model_rounds=1,
        response_text="（构造用回复）",
        recalled=False,
        error=None,
        recall_check=False,
        current_topic=None,
        topic_gate_open=True,
        memory_cards_count=2,
        recommendation_reason=None,
        observation_error=None,
    )
    base.update(overrides)
    return bench.RoundResult(**base)


def _session(rounds: list[bench.RoundResult]) -> bench.SessionResult:
    return bench.SessionResult(
        session_id="guardrail_session",
        db_path="guardrail-memory",
        rounds=rounds,
        scenario="recall",
    )


def test_compliance_verdict_fails_when_gate_closed_but_cards_present() -> None:
    """判据 FAIL 分支 A：主题门关闭却推荐了卡片 = 强行补充无关历史。

    宪法 2.2（无主题不推荐）+ 十四-7（禁止强行补充无关历史）。这是 P16
    评测最核心的失败信号：宁可 0 推荐，也不能无主题硬推历史。
    """
    compliance = bench._evaluate_constitutional_compliance(
        [_session([_round(topic_gate_open=False, memory_cards_count=2)])],
        recent_turn_limit=bench.DEFAULT_RECENT_TURN_LIMIT,
    )
    assert compliance["status"] == "FAIL"
    assert compliance["measured_rounds"] == 1
    assert compliance["unmeasured_rounds"] == 0
    violations = compliance["violations"]
    assert len(violations) == 1
    assert violations[0]["check"] == "no_forced_history_injection"
    assert violations[0]["clause"] == "十四-1 / 2.2 / 十四-7"
    checks = {check["id"]: check for check in compliance["checks"]}
    assert checks["no_forced_history_injection"]["status"] == "FAIL"
    assert checks["no_full_load_every_turn"]["status"] == "PASS"


def test_compliance_verdict_fails_when_cards_exceed_recommendation_limit() -> None:
    """判据 FAIL 分支 B：单轮卡片数超过推荐上限/recent_turn_limit = 每轮全量加载。

    宪法 十四-3 / 十四-4 / 十四-8。构造卡片数 6，同时超过
    DEFAULT_RECOMMENDATION_LIMIT(5) 与 recent_turn_limit(3)。
    """
    compliance = bench._evaluate_constitutional_compliance(
        [_session([_round(topic_gate_open=True, memory_cards_count=6)])],
        recent_turn_limit=3,
    )
    assert compliance["status"] == "FAIL"
    assert compliance["measured_rounds"] == 1
    violations = compliance["violations"]
    assert len(violations) == 1
    assert violations[0]["check"] == "no_full_load_every_turn"
    assert violations[0]["clause"] == "十四-3 / 十四-4 / 十四-8"
    assert "6" in violations[0]["detail"]


def test_compliance_verdict_not_measured_without_any_observation() -> None:
    """判据 NOT_MEASURED 分支：所有观测字段为 None 时必须拒绝判决。

    运行时未暴露 memory_cards / topic_gate_open 的轮次不计入判定；全部
    轮次都拿不到时整体 NOT_MEASURED —— 宁可没有判决，也不伪造 PASS。
    """
    rounds = [
        _round(turn_index=1, memory_cards_count=None, topic_gate_open=None),
        _round(turn_index=2, memory_cards_count=None, topic_gate_open=None),
    ]
    compliance = bench._evaluate_constitutional_compliance(
        [_session(rounds)],
        recent_turn_limit=bench.DEFAULT_RECENT_TURN_LIMIT,
    )
    assert compliance["status"] == "NOT_MEASURED"
    assert compliance["measured_rounds"] == 0
    assert compliance["unmeasured_rounds"] == 2
    assert compliance["violations"] == []
    assert all(check["status"] == "NOT_MEASURED" for check in compliance["checks"])
    assert compliance["unmeasured_note"] is not None


def test_compliance_verdict_pass_when_gate_open_within_limits() -> None:
    """判据 PASS 分支：全轮主题门打开且卡片数在预算内 -> 合法绿灯。"""
    rounds = [
        _round(turn_index=1, topic_gate_open=True, memory_cards_count=3),
        _round(turn_index=2, topic_gate_open=True, memory_cards_count=0),
    ]
    compliance = bench._evaluate_constitutional_compliance(
        [_session(rounds)],
        recent_turn_limit=bench.DEFAULT_RECENT_TURN_LIMIT,
    )
    assert compliance["status"] == "PASS"
    assert compliance["measured_rounds"] == 2
    assert compliance["unmeasured_rounds"] == 0
    assert compliance["violations"] == []
    assert all(check["status"] == "PASS" for check in compliance["checks"])
    assert compliance["unmeasured_note"] is None


# ---------------------------------------------------------------------------
# 第 4 项：主题继承探针（观测断言，不是通过要求）
# ---------------------------------------------------------------------------


def test_exhaustion_probe_loses_topic_inheritance_after_eviction(tmp_path: Path) -> None:
    """主题继承探针 —— 把「上下文耗尽后指代型追问丢失主题继承」固化为可见信号。

    宪法 3.2（主题来源）：上一轮讨论某话题、下一轮用户只说指代型追问时，
    只要会话连续性仍然明确，当前主题仍应保持。P16 exhaustion 场景把 anchor
    挤出上下文后用指代型追问（RECALL_QUESTION）探测主题是否仍然继承。

    真实观测（2026-10-20 hermetic 复跑）：anchor 被挤出后，指代型追问解析出的
    current_topic 就是追问本身，与 anchor 话题无关 ——
    topic_inherited=False、topic_state_reason="current_utterance_topic:
    history_not_needed"、continued_from_recent_turn=False、本轮 0 张记忆卡片。
    即「上下文耗尽后指代型追问丢失主题继承」是真实缺口。

    本测试是观测断言、不是要求它通过：一旦被测行为改变（无论修好还是回归），
    这里会红，从而逼出人工复核 —— 这正是固化成测试的目的。
    """
    runtime = _build_hermetic_world(tmp_path, recent_turn_limit=3)
    session_id = "p16_guardrail_topic_probe"

    t1, probe, probe_index = _run_exhaustion_flow(runtime, session_id=session_id, filler_rounds=4)
    t1_obs = bench._extract_turn_observation(t1)
    probe_obs = bench._extract_turn_observation(probe)

    topic_probe = bench._build_topic_probe(
        anchor_topic=t1_obs.current_topic,
        probe_obs=probe_obs,
        probe_index=probe_index,
    )

    # 前提：anchor 话题确实在 T1 被解析出来，探针结构不是 NOT_MEASURED 分支。
    assert t1_obs.current_topic is not None
    assert topic_probe["anchor_topic"] == t1_obs.current_topic
    assert topic_probe["probe_topic"] == probe_obs.current_topic
    assert topic_probe["reason"] is None
    assert probe_obs.observation_error is None

    # 观测断言（真实缺口，详见 docstring）。
    assert topic_probe["topic_inherited"] is False
    assert topic_probe["continued_from_recent_turn"] is False
    assert probe_obs.topic_state_reason is not None
    assert "history_not_needed" in probe_obs.topic_state_reason
    assert probe_obs.memory_cards_count == 0
    assert probe_obs.topic_gate_open is True


# ---------------------------------------------------------------------------
# 第 5 项：NOT_MEASURED 不许伪装 PASS
# ---------------------------------------------------------------------------


def test_observation_error_round_never_disguises_as_pass() -> None:
    """观测失败的轮次不得把判据洗成绿灯（含退出码逻辑）。

    教训模式：观测提取失败（observation_error）时若把轮次当成 0 卡片/通过，
    一次工具侧的抽取 bug 就会把失败评测静默洗成绿灯。构造与真实失败形状
    一致的 RoundResult（observation_error 非空、观测字段留 None —— 见
    _extract_turn_observation 的 except 分支），判据必须 NOT_MEASURED，
    且沿工具 main() 的退出码逻辑（PASS 才返回 0）不得返回 0。
    """
    broken_round = _round(
        turn_index=2,
        memory_cards_count=None,
        topic_gate_open=None,
        observation_error="KeyError: 'topic_state'",
    )
    compliance = bench._evaluate_constitutional_compliance(
        [_session([broken_round])],
        recent_turn_limit=bench.DEFAULT_RECENT_TURN_LIMIT,
    )
    assert compliance["status"] == "NOT_MEASURED"
    assert compliance["measured_rounds"] == 0
    assert compliance["unmeasured_rounds"] == 1
    assert compliance["violations"] == []

    # 镜像 tools/p16_recall_bench.py main() 的退出码逻辑：
    # return 0 if verdict == "PASS" else 1
    exit_code = 0 if compliance["status"] == "PASS" else 1
    assert exit_code != 0, "观测失败不得退出码 0（不许静默伪装成绿灯）"


# ---------------------------------------------------------------------------
# 第 6 项：观测部分失败不得洗成绿灯（observation_error 必须与字段缺失同等对待）
# ---------------------------------------------------------------------------


def test_partially_failed_observation_is_not_treated_as_measured() -> None:
    """观测提取失败但残留部分非 None 字段时，该轮不得计入 measured。

    这是第 5 项的理论补洞：第 5 项构造的是「字段全 None + observation_error」，
    那种形状即使不检查 observation_error 也会因为字段缺失而被判 unmeasured。
    但 ``_extract_turn_observation`` 是先填字段、出错后才置 observation_error
    （见其 try/except 结构），所以真实失败形状可能是：``observation_error`` 非空、
    而部分字段已残留非 None 值。

    若判据只查字段是否为 None，这一轮会被当成「已测量」——于是一次抽取 bug
    就能把该轮洗成合规绿灯。必须让 observation_error 与字段缺失同等对待。
    """
    # 形状：提取过程中途失败，memory_cards / topic_gate 已残留，但 observation_error 非空。
    partially_failed = _round(
        turn_index=2,
        memory_cards_count=0,
        topic_gate_open=True,
        current_topic="某个话题",
        observation_error="KeyError: 'topic_state'",
    )
    compliance = bench._evaluate_constitutional_compliance(
        [_session([partially_failed])],
        recent_turn_limit=bench.DEFAULT_RECENT_TURN_LIMIT,
    )
    assert compliance["status"] == "NOT_MEASURED"
    assert compliance["measured_rounds"] == 0
    assert compliance["unmeasured_rounds"] == 1

    # 与 main() 退出码逻辑镜像一致：只有 PASS 才返回 0。
    assert (0 if compliance["status"] == "PASS" else 1) != 0


def test_measured_rounds_still_judge_when_one_observation_failed() -> None:
    """一轮观测失败不应连带废掉其他可测轮次的判定能力。

    与上一项互为边界：observation_error 只让**该轮** 退出判定，不是一刀切
    把整个 session 废成 NOT_MEASURED。否则一次抽取抖动就会让评测永久失去
    判定能力， equally 是对证据的浪费。
    """
    failed = _round(
        turn_index=2,
        memory_cards_count=3,
        topic_gate_open=True,
        observation_error="TypeError: unsupported operand",
    )
    healthy = _round(
        turn_index=3,
        memory_cards_count=0,
        topic_gate_open=True,
        current_topic="无关话题",
    )
    compliance = bench._evaluate_constitutional_compliance(
        [_session([failed, healthy])],
        recent_turn_limit=bench.DEFAULT_RECENT_TURN_LIMIT,
    )
    assert compliance["status"] == "PASS"
    assert compliance["measured_rounds"] == 1
    assert compliance["unmeasured_rounds"] == 1
    assert compliance["violations"] == []
