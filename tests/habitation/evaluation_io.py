"""Persistence helpers for completed P16 evaluator artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from .evaluation import (
    EvaluationFinding,
    EvaluatorProvenance,
    ModelEvaluationReport,
)


@dataclass(frozen=True, slots=True)
class LoadedEvaluationArtifact:
    resident_model_id: str
    report: ModelEvaluationReport
    provider_request_provenance: Mapping[str, Any]
    raw: Mapping[str, Any]


def _required_string(raw: Mapping[str, Any], name: str) -> str:
    value = raw.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def report_from_mapping(raw: Mapping[str, Any]) -> ModelEvaluationReport:
    if not isinstance(raw, Mapping):
        raise TypeError("evaluation report must be a mapping")
    if raw.get("artifact_schema") != "aios.p16.model-evaluation.v2":
        raise ValueError("unsupported model evaluation report schema")

    provenance_raw = raw.get("evaluator_provenance")
    if not isinstance(provenance_raw, Mapping):
        raise ValueError("evaluation report missing evaluator_provenance")
    provenance = EvaluatorProvenance(
        evaluator_id=_required_string(provenance_raw, "evaluator_id"),
        evaluator_kind=provenance_raw.get("evaluator_kind", "unspecified"),
        provider=provenance_raw.get("provider"),
        model=provenance_raw.get("model"),
        version=provenance_raw.get("version"),
        config_fingerprint=provenance_raw.get("config_fingerprint"),
    )

    evaluator_id = _required_string(raw, "evaluator_id")
    if provenance.evaluator_id != evaluator_id:
        raise ValueError(
            "evaluation report evaluator_id does not match provenance"
        )

    findings_raw = raw.get("findings")
    if not isinstance(findings_raw, list):
        raise ValueError("evaluation report findings must be an array")
    findings: list[EvaluationFinding] = []
    seen_criteria: set[str] = set()
    for index, item in enumerate(findings_raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"evaluation finding {index} must be an object")
        evidence = item.get("evidence_event_ids", [])
        if not isinstance(evidence, (list, tuple)):
            raise ValueError("evidence_event_ids must be an array")
        measurements = item.get("measurements", {})
        if not isinstance(measurements, Mapping):
            raise ValueError("measurements must be an object")
        finding = EvaluationFinding(
            criterion_id=item.get("criterion_id"),
            status=item.get("status"),
            summary=item.get("summary"),
            evidence_event_ids=tuple(evidence),
            measurements=dict(measurements),
        )
        if finding.criterion_id in seen_criteria:
            raise ValueError("duplicate criterion_id in evaluation report")
        seen_criteria.add(finding.criterion_id)
        findings.append(finding)

    return ModelEvaluationReport(
        artifact_schema="aios.p16.model-evaluation.v2",
        scenario_id=_required_string(raw, "scenario_id"),
        scenario_version=_required_string(raw, "scenario_version"),
        scenario_public_fingerprint=_required_string(
            raw,
            "scenario_public_fingerprint",
        ),
        model_id=_required_string(raw, "model_id"),
        evaluator_id=evaluator_id,
        evaluator_provenance=provenance,
        findings=tuple(findings),
    )


def load_evaluation_artifact(path: str | Path) -> LoadedEvaluationArtifact:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError("evaluation artifact must contain one JSON object")
    if raw.get("artifact_schema") != "aios.p16.provider-evaluation-launch.v1":
        raise ValueError("unsupported provider evaluation artifact wrapper")

    report_raw = raw.get("report")
    if not isinstance(report_raw, Mapping):
        raise ValueError("evaluation artifact missing report")
    report = report_from_mapping(report_raw)
    resident_model_id = _required_string(raw, "resident_model_id")
    if resident_model_id != report.model_id:
        raise ValueError(
            "evaluation artifact resident_model_id does not match report model_id"
        )

    wrapper_fingerprint = _required_string(
        raw,
        "scenario_public_fingerprint",
    )
    if wrapper_fingerprint != report.scenario_public_fingerprint:
        raise ValueError(
            "evaluation artifact fingerprint does not match report fingerprint"
        )

    provider_provenance = raw.get("provider_request_provenance", {})
    if not isinstance(provider_provenance, Mapping):
        raise ValueError("provider_request_provenance must be an object")

    return LoadedEvaluationArtifact(
        resident_model_id=resident_model_id,
        report=report,
        provider_request_provenance=dict(provider_provenance),
        raw=dict(raw),
    )
