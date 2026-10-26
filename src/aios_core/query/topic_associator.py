"""DynamicTopicAssociator: Rapid multi-path topological associative recall for unpredictable topics.

Fulfills AIOS 3.0 Core Problem 2:
- When the AI is awakened without prior warning of what unpredictable topic the user will bring up
  (past memories, delayed events, philosophical concepts, physiological fatigue),
- In <= 30ms, executes parallel multi-path topological summoning:
  Path 1: Entity Hyperlink Graph traversal (Entity -> Event -> EvidenceSet)
  Path 2: NarrativeSegment thematic & phase matching
  Path 3: DimensionCurveTracker cognitive derivative & burnout inflection detection
  Path 4: WorldSearchIndex CJK inverted token search
- Synthesizes a compact, non-conflicting ad-hoc topic context card (<= 500 tokens)
  for direct injection into the model context bundle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
import time
from typing import Any, Sequence

from aios_core.context.budget_policy import resolve_context_budget_policy
from aios_core.context.tokenization import count_text_tokens
from aios_core.contracts.enums import ObjectType
from aios_core.contracts.models import ObjectRef
from aios_core.contracts.time import as_utc
from aios_core.query.hyperlink_traverser import EntityHyperlinkGraphTraverser
from aios_core.query.search import WorldSearchIndex
from aios_core.storage.sqlite_store import SQLiteWorldStore


def _estimate_tokens(text: str) -> int:
    """Conservative token estimate shared with the context budget machinery.

    The legacy ``(len(text) + 3) // 4`` formula undercounts Chinese text by roughly
    2.5x (measured: ~0.636 tokens/char for Chinese vs the 0.25 implied by /4), which
    let narrative cards silently exceed their stated budget. Delegate to the single
    source of truth instead of keeping a second, divergent copy here.
    """
    return count_text_tokens(text)


def _truncate_text_to_tokens(text: str, budget_tokens: int) -> str:
    """Longest prefix of `text` whose estimate fits `budget_tokens`.

    Binary search relies on `count_text_tokens` being monotonic (longer text never
    estimates cheaper), which holds for its per-character weighting.
    """
    if budget_tokens <= 0:
        return ""
    if count_text_tokens(text) <= budget_tokens:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if count_text_tokens(text[:mid]) <= budget_tokens:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo]


_STOPWORDS: set[str] = {
    "你", "我", "他", "她", "它", "我们", "你们", "他们",
    "的", "了", "和", "是", "在", "有", "个", "这", "那",
    "啊", "吗", "呢", "吧", "嘛", "呀", "着", "过", "么",
    "说", "想", "看", "去", "来", "还", "也", "就", "到",
    "让", "给", "但", "而", "又", "并且", "或者", "因为", "所以",
}


def _extract_keywords(text: str) -> list[str]:
    # Extract alphanumeric words
    latin_words = re.findall(r"[a-zA-Z0-9_]{2,20}", text)
    # Extract CJK characters
    cjk_chars = [c for c in text if '\u4e00' <= c <= '\u9fff']
    
    # Bigrams
    bigrams = [cjk_chars[i] + cjk_chars[i+1] for i in range(len(cjk_chars) - 1)]
    # Trigrams
    trigrams = [cjk_chars[i] + cjk_chars[i+1] + cjk_chars[i+2] for i in range(len(cjk_chars) - 2)]
    
    all_tokens = latin_words + trigrams + bigrams
    cleaned = [t.strip() for t in all_tokens if t.strip() and t.strip().lower() not in _STOPWORDS]
    return list(dict.fromkeys(cleaned))


@dataclass(frozen=True, slots=True)
class AdHocTopicCard:
    query: str
    detected_keywords: list[str]
    matched_entities: list[dict[str, Any]]
    matched_segments: list[dict[str, Any]]
    matched_events: list[dict[str, Any]]
    matched_claims: list[dict[str, Any]]
    cognitive_trends: list[dict[str, Any]]
    context_text: str
    estimated_tokens: int
    duration_ms: float

    def as_context_card(self) -> dict[str, Any]:
        return {
            "type": "ad_hoc_topic_memory",
            "query": self.query,
            "detected_keywords": self.detected_keywords,
            "context_text": self.context_text,
            "estimated_tokens": self.estimated_tokens,
            "duration_ms": self.duration_ms,
        }


class DynamicTopicAssociator:
    """Rapid multi-path topological memory associator for spontaneous and unpredictable topics."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        traverser: EntityHyperlinkGraphTraverser | None = None,
        index: WorldSearchIndex | None = None,
        subject_id: str = "user_1",
    ) -> None:
        self.store = store
        self.traverser = traverser
        self.index = index
        self.subject_id = subject_id

    def associate_topic(
        self,
        query: str,
        *,
        max_tokens: int | None = None,
    ) -> AdHocTopicCard:
        """Perform fast multi-path associative retrieval across unified world store in <= 30ms."""
        # Omitted / non-positive -> policy (also honours AIOS_BUDGET_* overrides);
        # an explicit argument still wins.
        max_tokens = resolve_context_budget_policy(
            narrative_context_tokens=max_tokens
        ).narrative_context_tokens
        t_start = time.perf_counter()
        clean_query = query.strip()
        keywords = _extract_keywords(clean_query)

        matched_entities: list[dict[str, Any]] = []
        matched_segments: list[dict[str, Any]] = []
        matched_events: list[dict[str, Any]] = []
        matched_claims: list[dict[str, Any]] = []
        cognitive_trends: list[dict[str, Any]] = []

        # ---------------------------------------------------------------------
        # Path 1: Entity Hyperlink Graph Traversal
        # ---------------------------------------------------------------------
        if self.traverser is not None and keywords:
            for kw in keywords[:3]:
                try:
                    res = self.traverser.traverse(kw, depth=2)
                    if res.found:
                        matched_entities.append({
                            "entity_id": res.entity_id,
                            "alias": kw,
                            "canonical_name": res.canonical_name,
                            "connected_anchors": [
                                {"object_id": a.object_id, "title": a.title}
                                for a in res.anchors[:3]
                            ],
                        })
                except Exception:
                    pass

        # ---------------------------------------------------------------------
        # Path 2: NarrativeSegment Theme & Phase Matching
        # ---------------------------------------------------------------------
        segment_payloads = self.store.list_payloads(
            object_type=ObjectType.NARRATIVE_SEGMENT,
            subject_id=self.subject_id,
        )
        for sp in segment_payloads:
            if sp.get("deleted_at") is not None:
                continue
            title = str(sp.get("title") or "")
            tags = [str(t) for t in (sp.get("theme_tags") or [])]
            desc = str(sp.get("description") or "")
            combined_text = f"{title} {' '.join(tags)} {desc}"

            # Check overlap with extracted keywords
            matched_tags = [kw for kw in keywords if kw in combined_text]
            if matched_tags or any(tag in clean_query for tag in tags):
                matched_segments.append({
                    "segment_id": sp.get("object_id"),
                    "title": title,
                    "status": sp.get("segment_status"),
                    "matched_keywords": matched_tags,
                })
                if len(matched_segments) >= 2:
                    break

        # ---------------------------------------------------------------------
        # Path 3: Cognitive Dimension Curves & Burnout Inflections
        # ---------------------------------------------------------------------
        energy_stress_terms = {"累", "疲惫", "压力", "焦虑", "心率", "精力", "失眠", "瓶颈", "耗竭", "崩溃"}
        has_stress_indicator = any(term in clean_query for term in energy_stress_terms)
        if has_stress_indicator:
            curve_payloads = self.store.list_payloads(
                object_type=ObjectType.DIMENSION_CURVE_POINT,
                subject_id=self.subject_id,
            )
            for cp in curve_payloads[-3:]:
                if cp.get("deleted_at") is not None:
                    continue
                cognitive_trends.append({
                    "point_id": cp.get("object_id"),
                    "dimension_id": (cp.get("dimension_ref") or {}).get("object_id"),
                    "value": cp.get("value"),
                    "velocity": cp.get("velocity"),
                    "acceleration": cp.get("acceleration"),
                    "anomaly_flag": cp.get("anomaly_flag"),
                    "anomaly_description": cp.get("anomaly_description"),
                })

        # ---------------------------------------------------------------------
        # Path 4: Claims and Key Events
        # ---------------------------------------------------------------------
        claim_payloads = self.store.list_payloads(
            object_type=ObjectType.CLAIM,
            subject_id=self.subject_id,
        )
        for clm in claim_payloads:
            if clm.get("deleted_at") is not None:
                continue
            content = str(clm.get("content") or "")
            if any(kw in content for kw in keywords):
                matched_claims.append({
                    "claim_id": clm.get("object_id"),
                    "content": content,
                    "confidence": clm.get("confidence"),
                })
                if len(matched_claims) >= 3:
                    break

        event_payloads = self.store.list_payloads(
            object_type=ObjectType.EVENT,
            subject_id=self.subject_id,
        )
        for ev in event_payloads:
            if ev.get("deleted_at") is not None:
                continue
            ev_title = str(ev.get("title") or "")
            ev_interp = str(ev.get("interpretation") or "")
            if any(kw in f"{ev_title} {ev_interp}" for kw in keywords):
                matched_events.append({
                    "event_id": ev.get("object_id"),
                    "title": ev_title,
                    "interpretation": ev_interp,
                })
                if len(matched_events) >= 3:
                    break

        # ---------------------------------------------------------------------
        # Synthesize Context Narrative (Bounded by max_tokens)
        # ---------------------------------------------------------------------
        lines: list[str] = [f"【突发话题拓扑联想检索看板】针对输入: \"{clean_query[:50]}\""]

        if matched_entities:
            for ent in matched_entities:
                anchors_str = ", ".join(a["title"] for a in ent.get("connected_anchors", []))
                lines.append(f"- 关联实体: {ent['canonical_name']} (别名: {ent['alias']}) -> 关联事件: {anchors_str or '无'}")

        if matched_segments:
            for seg in matched_segments:
                lines.append(f"- 关联人生叙事分段: 《{seg['title']}》(状态: {seg['status']})")

        if matched_events:
            for ev in matched_events:
                lines.append(f"- 历史事件锚点: {ev['title']} ({ev['interpretation']})")

        if matched_claims:
            for cl in matched_claims:
                lines.append(f"- 相关事实主张: {cl['content']} (置信度: {cl['confidence']})")

        if cognitive_trends:
            for ct in cognitive_trends:
                vel_str = f", 变化速率 v={ct['velocity']:.2f}" if ct.get("velocity") is not None else ""
                ano_str = f" [预警: {ct['anomaly_description']}]" if ct.get("anomaly_flag") else ""
                lines.append(f"- 身心认知负荷: 维度 {ct['dimension_id']} 当前值={ct['value']:.1f}{vel_str}{ano_str}")

        if len(lines) == 1:
            lines.append("- (未发现强相关历史陈账或异常实体，建议以当下新鲜情境流畅交流)")

        context_text = "\n".join(lines)
        est_tokens = _estimate_tokens(context_text)

        # Budget truncation if exceeds max_tokens.
        # The budget is a HARD bound: the header line alone can already exceed a very
        # small `max_tokens`, so the surviving body is additionally cut to size instead
        # of being emitted over budget. Underestimating estimators used to hide this.
        if est_tokens > max_tokens:
            suffix = "... (已依据Token预算上限紧凑裁剪)"
            line_gen = [lines[0]]
            cur_tokens = _estimate_tokens(lines[0])
            for line in lines[1:]:
                line_tokens = _estimate_tokens(line)
                if cur_tokens + line_tokens + 8 > max_tokens:
                    break
                line_gen.append(line)
                cur_tokens += line_tokens
            body_budget = max(0, max_tokens - _estimate_tokens(suffix))
            body = _truncate_text_to_tokens("\n".join(line_gen), body_budget)
            context_text = f"{body}{suffix}" if body else suffix
            est_tokens = _estimate_tokens(context_text)

        duration_ms = (time.perf_counter() - t_start) * 1000.0

        return AdHocTopicCard(
            query=clean_query,
            detected_keywords=keywords,
            matched_entities=matched_entities,
            matched_segments=matched_segments,
            matched_events=matched_events,
            matched_claims=matched_claims,
            cognitive_trends=cognitive_trends,
            context_text=context_text,
            estimated_tokens=est_tokens,
            duration_ms=duration_ms,
        )
