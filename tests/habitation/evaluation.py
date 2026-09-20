"""Post-run finding schema for independent P16 model habitation runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

from .harness import HabitationRun, HabitationScenario
from .io import scenario_public_fingerprint


FindingStatus = Literal["pass", "fail", "observe", "not_applicable"]
_VALID_STATUSES = frozenset({"pass", "fail", "observe", "not_applicable"})


@dataclass(frozen=True, slots=True)
class EvaluationFinding:
    """One evaluator conclusion backed by concrete resident-run evidence."""

    criterion_id: str
    status: FindingStatus
    summary: str
    evidence_event_ids: tuple[str, ...] = ()
    measurements: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.criterion_id, str) or not self.criterion_id.strip():
            raise ValueError("criterion_id must be a non-empty string")
        if not isinstance(self.status, str) or self.status not in _VALID_STATUSES:
            raise ValueError(f"unsupported finding status: {self.status!r}")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if not isinstance(self.evidence_event_ids, tuple) or not all(
            isinstance(event_id, str) and event_id.strip()
            for event_id in self.evidence_event_ids
        ):
            raise ValueError(
                "evidence_event_ids must be a tuple of non-empty strings"
            )
        if not isinstance(self.measurements, Mapping):
            raise ValueError("measurements must be a mapping")


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
    if not isinstance(evaluator_id, str) or not evaluator_id.strip():
        raise ValueError("evaluator_id must be a non-empty string")

    finding_tuple = tuple(findings)
    criterion_ids = [finding.criterion_id for finding in finding_tuple]
    if len(criterion_ids) != len(set(criterion_ids)):
        raise ValueError("criterion_id values must be unique within one report")

    delivered_ids = {step.event_id for step in run.steps}
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
        evaluator_id=evaluator_id.strip(),
        findings=finding_tuple,
    )


def comparison_matrix(
    reports: Sequence[ModelEvaluationReport],
) -> dict[str, Any]:
    """Align comparable per-model findings without declaring a winner."""

    report_tuple = tuple(reports)
    if not report_tuple:
        raise ValueError("at least one report is required")

    fingerprints = {report.scenario_public_fingerprint for report in report_tuple}
    if len(fingerprints) != 1:
        raise ValueError("all reports must come from the same visible scenario")

    evaluator_ids = {report.evaluator_id for report in report_tuple}
    if len(evaluator_ids) != 1:
        raise ValueError(
            "all reports in one comparison must use the same evaluator_id"
        )

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
        "evaluator_id": first.evaluator_id,
        "criteria": criteria,
        "models": by_model,
    }
