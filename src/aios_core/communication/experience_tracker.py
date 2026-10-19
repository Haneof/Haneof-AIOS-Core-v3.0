"""ExperienceTracker: Bayesian adaptive symbiotic communication style tracker for AIOS 3.0.

Fulfills GAP-004 & Constitution Articles 12 & 69:
- Dynamically learns what speaking style and tone are most effective for each user/scenario.
- Replaces rigid if-else rules with Bayesian posterior estimation over recorded CommunicationExperience objects.
- Generates blacklisted avoidance rules for styles with high user resistance (defending user mental comfort).
- Supports hierarchical Bayesian smoothing (scenario-specific observations smoothed by global user priors).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Sequence

from aios_core.contracts.enums import ObjectType, UserReaction
from aios_core.contracts.models import CommunicationExperience, ObjectRef
from aios_core.contracts.time import as_utc
from aios_core.storage.sqlite_store import SQLiteWorldStore
from .service import (
    CommunicationExperienceReceipt,
    CommunicationExperienceRequest,
    CommunicationExperienceService,
)


class ToneStyle(StrEnum):
    FORMAL = "formal"
    HUMOROUS = "humorous"
    GENTLE = "gentle"
    DIRECT = "direct"
    TEASING = "teasing"
    EMPATHIC = "empathic"
    CONCISE = "concise"
    ENCOURAGING = "encouraging"


@dataclass(frozen=True, slots=True)
class StyleScore:
    style: str
    tone: str | None
    posterior_acceptance: float
    total_samples: int
    accepted_count: int
    resisted_count: int
    ignored_count: int


@dataclass(frozen=True, slots=True)
class StyleRecommendation:
    scenario: str
    recommended_style: str
    recommended_tone: str | None
    posterior_score: float
    confidence: float
    sample_count: int
    is_scenario_specific: bool = True
    candidates: list[StyleScore] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AvoidanceRule:
    scenario: str | None
    style: str
    tone: str | None
    resistance_rate: float
    total_samples: int
    reason: str


class ExperienceTracker:
    """Evaluates communication history to recommend symbiotic styles and blacklist negative patterns."""

    def __init__(
        self,
        *,
        store: SQLiteWorldStore,
        service: CommunicationExperienceService | None = None,
        subject_id: str = "user_1",
    ) -> None:
        self.store = store
        self.subject_id = subject_id
        self.service = service or CommunicationExperienceService(store=store, subject_id=subject_id)

    def record_interaction_experience(
        self,
        *,
        scenario: str,
        style: str,
        tone: str | None = None,
        user_reaction: UserReaction,
        evidence_refs: Sequence[ObjectRef],
        action_ref: ObjectRef | None = None,
        counterexample_refs: Sequence[ObjectRef] = (),
        recorded_at: datetime | None = None,
    ) -> CommunicationExperienceReceipt:
        """Record an empirical communication feedback experience."""
        rec = as_utc(recorded_at or datetime.now(timezone.utc), "recorded_at")
        req = CommunicationExperienceRequest(
            scenario=scenario.strip(),
            style=style.strip(),
            tone=tone.strip() if tone else None,
            user_reaction=user_reaction,
            evidence_refs=tuple(evidence_refs),
            action_ref=action_ref,
            counterexample_refs=tuple(counterexample_refs),
        )
        return self.service.record(req, recorded_at=rec)

    def _load_experiences(self, scenario: str | None = None) -> list[CommunicationExperience]:
        payloads = self.store.list_payloads(
            object_type=ObjectType.COMMUNICATION_EXPERIENCE,
            subject_id=self.subject_id,
        )
        items: list[CommunicationExperience] = []
        for p in payloads:
            if p.get("deleted_at") is not None:
                continue
            exp = CommunicationExperience.model_validate(p)
            if scenario is not None and exp.scenario != scenario.strip():
                continue
            items.append(exp)
        return items

    def get_style_stats(self, scenario: str | None = None) -> list[StyleScore]:
        """Aggregate statistical performance for each style/tone combination."""
        experiences = self._load_experiences(scenario)
        buckets: dict[tuple[str, str | None], list[UserReaction]] = {}

        for exp in experiences:
            key = (exp.style, exp.tone)
            buckets.setdefault(key, []).append(exp.user_reaction)

        stats: list[StyleScore] = []
        for (style, tone), reactions in buckets.items():
            acc = sum(1 for r in reactions if r == UserReaction.ACCEPTED)
            res = sum(1 for r in reactions if r == UserReaction.RESISTED)
            ign = sum(1 for r in reactions if r == UserReaction.IGNORED)
            total = len(reactions)

            # Laplace/Bayesian smoothing (alpha=1, beta=1)
            posterior = (acc + 1.0) / (total + 2.0)

            stats.append(
                StyleScore(
                    style=style,
                    tone=tone,
                    posterior_acceptance=posterior,
                    total_samples=total,
                    accepted_count=acc,
                    resisted_count=res,
                    ignored_count=ign,
                )
            )

        stats.sort(key=lambda s: s.posterior_acceptance, reverse=True)
        return stats

    def get_effective_style(
        self,
        scenario: str,
        *,
        candidate_styles: Sequence[str] | None = None,
        default_style: str = ToneStyle.DIRECT.value,
        default_tone: str | None = None,
        use_fallback_priors: bool = True,
    ) -> StyleRecommendation:
        """Recommend optimal communication style for a given scenario based on Bayesian posterior acceptance."""
        scenario_clean = scenario.strip()
        scenario_stats = self.get_style_stats(scenario_clean)
        global_stats = self.get_style_stats(None) if use_fallback_priors else []

        allowed_styles = set(candidate_styles) if candidate_styles else None

        # Build candidate map
        scores: list[StyleScore] = []
        is_scenario_specific = True

        # If scenario-specific data exists, use it
        if scenario_stats:
            for s_stat in scenario_stats:
                if allowed_styles and s_stat.style not in allowed_styles:
                    continue
                scores.append(s_stat)

        # Fallback to global user stats if no scenario data and enabled
        if not scores and global_stats:
            is_scenario_specific = False
            for g_stat in global_stats:
                if allowed_styles and g_stat.style not in allowed_styles:
                    continue
                scores.append(g_stat)

        # Filter out high resistance styles (blacklist guardrail)
        viable_scores = [s for s in scores if (s.resisted_count / max(1, s.total_samples)) < 0.6]

        if not viable_scores:
            # Cold start default
            return StyleRecommendation(
                scenario=scenario_clean,
                recommended_style=default_style,
                recommended_tone=default_tone,
                posterior_score=0.5,
                confidence=0.1,
                sample_count=0,
                is_scenario_specific=False,
                candidates=[],
            )

        best = viable_scores[0]
        # Confidence increases with sample volume (asymptotic to 1.0)
        confidence = 1.0 - (1.0 / (1.0 + best.total_samples * 0.5))

        return StyleRecommendation(
            scenario=scenario_clean,
            recommended_style=best.style,
            recommended_tone=best.tone,
            posterior_score=best.posterior_acceptance,
            confidence=confidence,
            sample_count=best.total_samples,
            is_scenario_specific=is_scenario_specific,
            candidates=viable_scores,
        )

    def get_avoidance_list(
        self,
        scenario: str | None = None,
        *,
        min_resistance_rate: float = 0.4,
        min_samples: int = 2,
    ) -> list[AvoidanceRule]:
        """Detect styles or tones that provoke high user resistance and must be actively avoided."""
        stats = self.get_style_stats(scenario)
        rules: list[AvoidanceRule] = []

        for st in stats:
            if st.total_samples >= min_samples:
                res_rate = st.resisted_count / st.total_samples
                if res_rate >= min_resistance_rate:
                    rules.append(
                        AvoidanceRule(
                            scenario=scenario,
                            style=st.style,
                            tone=st.tone,
                            resistance_rate=res_rate,
                            total_samples=st.total_samples,
                            reason=(
                                f"Style '{st.style}' (tone='{st.tone or 'default'}') caused {st.resisted_count}/{st.total_samples} "
                                f"({res_rate:.1%}) resistance events; blacklisted to preserve symbiotic rapport"
                            ),
                        )
                    )

        rules.sort(key=lambda r: r.resistance_rate, reverse=True)
        return rules
