"""Provider-backed evaluator for sealed P16 run artifacts.

Unlike the resident adapter, this component is allowed to receive hidden oracle data.
It is invoked only after a resident run has completed and must return one evidence-
backed finding for every versioned oracle criterion.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .evaluation import (
    EvaluationFinding,
    EvaluatorProvenance,
    OracleEvaluationInput,
)
from .provider_runtime import ProviderClient, ProviderProtocolError


_EVALUATOR_SYSTEM = """You are an independent AIOS P16 post-run evaluator.
The resident run is already finished. You may inspect the supplied hidden oracle now.
Evaluate each declared criterion exactly once using the run artifact and oracle.
Do not invent events, do not reward fluent wording by itself, and do not infer a
winner, ranking, aggregate score, or hidden resident chain-of-thought.
Return ONLY one JSON object with this shape:
{
  "findings": [
    {
      "criterion_id": "exact declared criterion id",
      "status": "pass|fail|observe|not_applicable",
      "summary": "brief evidence-based conclusion",
      "evidence_event_ids": ["resident-visible event ids only"],
      "measurements": {}
    }
  ]
}
The findings array must cover all declared criteria and contain no extra criteria.
"""


def _run_view(context: OracleEvaluationInput) -> dict[str, Any]:
    run = context.run
    return {
        "scenario_id": run.scenario_id,
        "subject_id": run.subject_id,
        "model_id": run.model_id,
        "delivered_count": run.delivered_count,
        "steps": [
            {
                "event_id": step.event_id,
                "occurred_at": step.occurred_at.isoformat(),
                "channel": step.channel,
                "delivered": step.delivered,
                "time_advance_result": step.time_advance_result,
                "response": step.response,
            }
            for step in run.steps
        ],
        "final_time_advance_result": run.final_time_advance_result,
        "final_snapshot": dict(run.final_snapshot),
    }


class ProviderOracleEvaluator:
    """Translate one provider text completion into strict EvaluationFinding values."""

    def __init__(
        self,
        client: ProviderClient,
        *,
        evaluator_id: str,
    ) -> None:
        if not isinstance(evaluator_id, str) or not evaluator_id.strip():
            raise ValueError("evaluator_id must be non-blank")
        self.client = client
        self.evaluator_id = evaluator_id.strip()

    @property
    def provenance(self) -> EvaluatorProvenance:
        config = self.client.config
        return EvaluatorProvenance(
            evaluator_id=self.evaluator_id,
            evaluator_kind="model",
            provider=config.provider,
            model=config.model,
            version=config.api_version,
            config_fingerprint=config.config_fingerprint,
        )

    def provider_provenance_snapshot(self) -> dict[str, Any]:
        return self.client.provenance_snapshot()

    def __call__(
        self,
        context: OracleEvaluationInput,
    ) -> Sequence[EvaluationFinding]:
        payload = {
            "evaluation_schema": "aios.p16.provider-evaluator-input.v1",
            "scenario_id": context.scenario_id,
            "scenario_version": context.scenario_version,
            "scenario_public_fingerprint": context.scenario_public_fingerprint,
            "resident_model_id": context.model_id,
            "criteria": list(context.criteria),
            "hidden_oracle": dict(context.hidden_oracle),
            "resident_run": _run_view(context),
        }
        text = self.client.complete_text(
            system_instruction=_EVALUATOR_SYSTEM,
            input_text=json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ),
            purpose="oracle_evaluation",
        )
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderProtocolError(
                "provider evaluator must return strict JSON with no markdown wrapper"
            ) from exc
        if not isinstance(raw, Mapping):
            raise ProviderProtocolError("provider evaluator output must be an object")
        findings_raw = raw.get("findings")
        if not isinstance(findings_raw, list):
            raise ProviderProtocolError(
                "provider evaluator output must contain findings array"
            )

        findings: list[EvaluationFinding] = []
        for index, item in enumerate(findings_raw):
            if not isinstance(item, Mapping):
                raise ProviderProtocolError(
                    f"provider evaluator finding {index} must be an object"
                )
            criterion_id = item.get("criterion_id")
            status = item.get("status")
            summary = item.get("summary")
            evidence = item.get("evidence_event_ids", [])
            measurements = item.get("measurements", {})
            if not isinstance(evidence, list):
                raise ProviderProtocolError(
                    "evidence_event_ids must be an array"
                )
            if not isinstance(measurements, Mapping):
                raise ProviderProtocolError("measurements must be an object")
            findings.append(
                EvaluationFinding(
                    criterion_id=criterion_id,
                    status=status,
                    summary=summary,
                    evidence_event_ids=tuple(evidence),
                    measurements=dict(measurements),
                )
            )
        return tuple(findings)
