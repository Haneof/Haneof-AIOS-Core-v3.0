"""Post-run evaluator contracts for independent P16 model habitation runs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Mapping, Sequence

from .harness import HabitationRun, HabitationScenario
from .io import scenario_public_fingerprint


FindingStatus = Literal["pass", "fail", "observe", "not_applicable"]
EvaluatorKind = Literal["human", "model", "hybrid", "deterministic", "unspecified"]
_VALID_STATUSES = frozenset({"pass", "fail", "observe", "not_applicable"})
_VALID_EVALUATOR_KINDS = frozenset(
    {"human", "model", "hybrid", "deterministic", "unspecified"}
)
ORACLE_SCHEMA_V1 = "aios.p16.oracle.v1"


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
class EvaluatorProvenance:
    """Auditable identity of the post-run evaluator, never resident-visible."""

    evaluator_id: str
    evaluator_kind: EvaluatorKind = "unspecified"
    provider: str | None = None
    model: str | None = None
    version: str | None = None
    config_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.evaluator_id, str) or not self.evaluator_id.strip():
            raise ValueError("evaluator_id must be a non-empty string")
        if (
            not isinstance(self.evaluator_kind, str)
            or self.evaluator_kind not in _VALID_EVALUATOR_KINDS
        ):
            raise ValueError("unsupported evaluator_kind")
        for field_name in ("provider", "model", "version", "config_fingerprint"):
            value = getattr(self, field_name)
            if value is not None and (
                not isinstance(value, str) or not value.strip()
            ):
                raise ValueError(f"{field_name} must be non-blank when provided")
        if self.evaluator_kind in {"model", "hybrid"}:
            if self.provider is None or self.model is None:
                raise ValueError(
                    "model/hybrid evaluator provenance requires provider and model"
                )

    def as_dict(self) -> dict[str, Any]:
        return {
            "evaluator_id": self.evaluator_id,
            "evaluator_kind": self.evaluator_kind,
            "provider": self.provider,
            "model": self.model,
            "version": self.version,
            "config_fingerprint": self.config_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class OracleEvaluationInput:
    """Evaluator-only input constructed after a resident run has finished."""

    scenario_id: str
    scenario_version: str
    scenario_public_fingerprint: str
    model_id: str
    criteria: tuple[str, ...]
    hidden_oracle: Mapping[str, Any]
    run: HabitationRun


OracleEvaluatorHandler = Callable[
    [OracleEvaluationInput],
    Sequence[EvaluationFinding],
]


@dataclass(frozen=True, slots=True)
class ModelEvaluationReport:
    artifact_schema: str
    scenario_id: str
    scenario_version: str
    scenario_public_fingerprint: str
    model_id: str
    evaluator_id: str
    evaluator_provenance: EvaluatorProvenance
    findings: tuple[EvaluationFinding, ...]

    @property
    def failure_count(self) -> int:
        return sum(1 for finding in self.findings if finding.status == "fail")


def _validate_run_matches_scenario(
    *,
    scenario: HabitationScenario,
    run: HabitationRun,
) -> None:
    if run.scenario_id != scenario.scenario_id:
        raise ValueError("run and scenario do not match")
    if run.subject_id != scenario.subject_id:
        raise ValueError("run subject and scenario subject do not match")


def oracle_criteria(scenario: HabitationScenario) -> tuple[str, ...]:
    """Read the versioned evaluator criteria from sealed oracle data."""

    oracle = scenario.hidden_oracle
    if oracle.get("evaluation_schema") != ORACLE_SCHEMA_V1:
        raise ValueError(
            f"hidden oracle must declare evaluation_schema={ORACLE_SCHEMA_V1}"
        )
    raw = oracle.get("criteria")
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError("hidden oracle criteria must be a non-empty array")
    criteria = tuple(raw)
    if not all(isinstance(item, str) and item.strip() for item in criteria):
        raise ValueError("hidden oracle criteria must contain non-empty strings")
    normalized = tuple(item.strip() for item in criteria)
    if len(normalized) != len(set(normalized)):
        raise ValueError("hidden oracle criteria must be unique")
    return normalized


def build_model_report(
    *,
    scenario: HabitationScenario,
    run: HabitationRun,
    evaluator_id: str,
    findings: Sequence[EvaluationFinding],
    evaluator_provenance: EvaluatorProvenance | None = None,
) -> ModelEvaluationReport:
    """Build a post-run report without inventing an overall model score."""

    _validate_run_matches_scenario(scenario=scenario, run=run)
    if not isinstance(evaluator_id, str) or not evaluator_id.strip():
        raise ValueError("evaluator_id must be a non-empty string")

    provenance = evaluator_provenance or EvaluatorProvenance(
        evaluator_id=evaluator_id.strip(),
    )
    if provenance.evaluator_id != evaluator_id.strip():
        raise ValueError(
            "evaluator_provenance evaluator_id must match evaluator_id"
        )

    finding_tuple = tuple(findings)
    if not all(isinstance(item, EvaluationFinding) for item in finding_tuple):
        raise TypeError("findings must contain EvaluationFinding values")
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
        artifact_schema="aios.p16.model-evaluation.v2",
        scenario_id=scenario.scenario_id,
        scenario_version=scenario.scenario_version,
        scenario_public_fingerprint=scenario_public_fingerprint(scenario),
        model_id=run.model_id,
        evaluator_id=evaluator_id.strip(),
        evaluator_provenance=provenance,
        findings=finding_tuple,
    )


def evaluate_with_oracle(
    *,
    scenario: HabitationScenario,
    run: HabitationRun,
    evaluator_provenance: EvaluatorProvenance,
    handler: OracleEvaluatorHandler,
) -> ModelEvaluationReport:
    """Evaluate only after residence, requiring one finding per oracle criterion."""

    _validate_run_matches_scenario(scenario=scenario, run=run)
    criteria = oracle_criteria(scenario)
    evaluator_input = OracleEvaluationInput(
        scenario_id=scenario.scenario_id,
        scenario_version=scenario.scenario_version,
        scenario_public_fingerprint=scenario_public_fingerprint(scenario),
        model_id=run.model_id,
        criteria=criteria,
        hidden_oracle=deepcopy(dict(scenario.hidden_oracle)),
        run=run,
    )
    findings = tuple(handler(evaluator_input))
    if not all(isinstance(item, EvaluationFinding) for item in findings):
        raise TypeError("oracle evaluator must return EvaluationFinding values")

    actual = {item.criterion_id for item in findings}
    expected = set(criteria)
    if actual != expected or len(findings) != len(criteria):
        missing = sorted(expected.difference(actual))
        extra = sorted(actual.difference(expected))
        raise ValueError(
            "oracle evaluator findings must exactly cover declared criteria; "
            f"missing={missing}, extra={extra}"
        )

    return build_model_report(
        scenario=scenario,
        run=run,
        evaluator_id=evaluator_provenance.evaluator_id,
        evaluator_provenance=evaluator_provenance,
        findings=findings,
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
    first_provenance = report_tuple[0].evaluator_provenance
    if any(
        report.evaluator_provenance != first_provenance
        for report in report_tuple[1:]
    ):
        raise ValueError(
            "all reports in one comparison must use identical evaluator provenance"
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
        "artifact_schema": "aios.p16.comparison-matrix.v2",
        "scenario_id": first.scenario_id,
        "scenario_version": first.scenario_version,
        "scenario_public_fingerprint": first.scenario_public_fingerprint,
        "evaluator_id": first.evaluator_id,
        "evaluator_provenance": first.evaluator_provenance.as_dict(),
        "criteria": criteria,
        "models": by_model,
    }
