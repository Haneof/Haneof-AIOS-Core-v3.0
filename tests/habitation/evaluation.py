"""Post-run finding schema for independent P16 model habitation runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

from .harness import HabitationRun, HabitationScenario
from .io import scenario_public_fingerprint


FindingStatus = Literal["pass", "fail", "observe", "not_applicable"]


@dataclass(frozen=True, slots=True)
class EvaluationFinding:
    """One evaluator conclusion backed by concrete run evidence.

    Findings are created after a resident run. They are never fed back into the
    resident model during the same benchmark run.
    """

    criterion_id: str
    status: FindingStatus
    summary: str
    evidence_event_ids: tuple[str, ...] = ()
    measurements: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.criterion_id.strip():
            raise ValueError("criterion_id must be non-empty")
        if self.status not in {"pass", "fail", "observe", "not_applicable"}:
            raise ValueError(f"unsupported finding status: {self.status}")
        if not self.summary.strip():
            raise ValueError("summary must be non-empty")


@dataclass(frozen=True, slots=True)
class ModelEvaluationReport:
    artifact_schema: str
    scenario_id: str
    scenario_version: str
    scenario_public_fingerprint: str
    model_id: str
    evaluator_id: str
    findings: tuple[EvaluationFinding, ...]

    @property
    def failure_count(self) -> int:
        return sum(1 for finding in self.findings if finding.status == "fail")


def build_model_report(
    *,
    scenario: HabitationScenario,
    run: HabitationRun,
    evaluator_id: str,
    findings: Sequence[EvaluationFinding],
) -> ModelEvaluationReport:
    """Build a post-run report without inventing an overall model score."""

    if run.scenario_id != scenario.scenario_id:
        raise ValueError("run and scenario do not match")
    if run.subject_id != scenario.subject_id:
        raise ValueError("run subject and scenario subject do not match")
    if not evaluator_id.strip():
        raise ValueError("evaluator_id must be non-empty")

    finding_tuple = tuple(findings)
    criterion_ids = [finding.criterion_id for finding in finding_tuple]
    if len(criterion_ids) != len(set(criterion_ids)):
        raise ValueError("criterion_id values must be unique within one report")

    delivered_ids = {
        step.event_id
        for step in run.steps
        if step.delivered
    }
    for finding in finding_tuple:
        unknown = set(finding.evidence_event_ids).difference(delivered_ids)
        if unknown:
            raise ValueError(
                "finding references events not delivered to this resident run: "
                + ", ".join(sorted(unknown))
            )

    return ModelEvaluationReport(
        artifact_schema="aios.p16.model-evaluation.v1",
        scenario_id=scenario.scenario_id,
        scenario_version=scenario.scenario_version,
        scenario_public_fingerprint=scenario_public_fingerprint(scenario),
        model_id=run.model_id,
        evaluator_id=evaluator_id,
        findings=finding_tuple,
    )


def comparison_matrix(
    reports: Sequence[ModelEvaluationReport],
) -> dict[str, Any]:
    """Align per-model findings by criterion without declaring a winner.

    The benchmark may later attach domain-specific measurements, model judges or
    human review. This deterministic layer only verifies that reports refer to the
    same visible life and exposes comparable evidence.
    """

    report_tuple = tuple(reports)
    if not report_tuple:
        raise ValueError("at least one report is required")

    fingerprints = {report.scenario_public_fingerprint for report in report_tuple}
    if len(fingerprints) != 1:
        raise ValueError("all reports must come from the same visible scenario")

    model_ids = [report.model_id for report in report_tuple]
    if len(model_ids) != len(set(model_ids)):
        raise ValueError("model_id values must be unique in one comparison")

    criteria = sorted(
        {
            finding.criterion_id
            for report in report_tuple
            for finding in report.findings
        }
    )

    by_model: dict[str, dict[str, Any]] = {}
    for report in sorted(report_tuple, key=lambda item: item.model_id):
        finding_map = {
            finding.criterion_id: {
                "status": finding.status,
                "summary": finding.summary,
                "evidence_event_ids": list(finding.evidence_event_ids),
                "measurements": dict(finding.measurements),
            }
            for finding in report.findings
        }
        by_model[report.model_id] = {
            criterion: finding_map.get(criterion)
            for criterion in criteria
        }

    first = report_tuple[0]
    return {
        "artifact_schema": "aios.p16.comparison-matrix.v1",
        "scenario_id": first.scenario_id,
        "scenario_version": first.scenario_version,
        "scenario_public_fingerprint": first.scenario_public_fingerprint,
        "criteria": criteria,
        "models": by_model,
    }
