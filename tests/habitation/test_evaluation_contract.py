from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from .evaluation import (
    ORACLE_SCHEMA_V1,
    EvaluationFinding,
    EvaluatorProvenance,
    build_model_report,
    comparison_matrix,
    evaluate_with_oracle,
)
from .harness import HabitationRunner, HabitationScenario, LifeEvent, ResidentEvent


BASE = datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc)


class Target:
    def __init__(self, model: str) -> None:
        self.model = model
        self.isolation_key = f"world:{model}:{id(self)}"
        self.clock: list[datetime] = []

    def advance_to(self, instant: datetime):
        self.clock.append(instant)
        return None

    def handle_event(self, event: ResidentEvent):
        return {"model": self.model, "event_id": event.event_id}

    def audit_snapshot(self):
        return {"clock_count": len(self.clock)}


def _scenario() -> HabitationScenario:
    return HabitationScenario(
        scenario_id="eval-life",
        subject_id="u1",
        events=(
            LifeEvent(
                event_id="e1",
                occurred_at=BASE,
                channel="conversation",
                payload="first",
            ),
            LifeEvent(
                event_id="e2",
                occurred_at=BASE + timedelta(days=1),
                channel="conversation",
                payload="second",
            ),
        ),
    )


def _report(model_id: str, status: str):
    scenario = _scenario()
    run = HabitationRunner().run(
        scenario=scenario,
        model_id=model_id,
        target=Target(model_id),
    )
    return build_model_report(
        scenario=scenario,
        run=run,
        evaluator_id="judge-v1",
        findings=(
            EvaluationFinding(
                criterion_id="cross_session_continuity",
                status=status,
                summary="evaluator observation",
                evidence_event_ids=("e1", "e2"),
                measurements={"sessions_connected": 2},
            ),
        ),
    )


def test_report_keeps_findings_evidence_backed_without_overall_score() -> None:
    report = _report("provider/model-a", "observe")

    assert report.model_id == "provider/model-a"
    assert report.failure_count == 0
    assert report.findings[0].evidence_event_ids == ("e1", "e2")
    assert not hasattr(report, "score")
    assert not hasattr(report, "winner")


def test_report_rejects_evidence_not_seen_by_resident() -> None:
    scenario = _scenario()
    run = HabitationRunner().run(
        scenario=scenario,
        model_id="provider/model-a",
        target=Target("a"),
    )

    with pytest.raises(ValueError, match="not delivered"):
        build_model_report(
            scenario=scenario,
            run=run,
            evaluator_id="judge-v1",
            findings=(
                EvaluationFinding(
                    criterion_id="bad-reference",
                    status="fail",
                    summary="references hidden/nonexistent event",
                    evidence_event_ids=("oracle-only",),
                ),
            ),
        )


def test_comparison_matrix_aligns_models_but_does_not_choose_winner() -> None:
    a = _report("provider/model-a", "pass")
    b = _report("provider/model-b", "fail")

    matrix = comparison_matrix((b, a))

    assert list(matrix["models"]) == ["provider/model-a", "provider/model-b"]
    assert matrix["criteria"] == ["cross_session_continuity"]
    assert matrix["models"]["provider/model-a"]["cross_session_continuity"]["status"] == "pass"
    assert matrix["models"]["provider/model-b"]["cross_session_continuity"]["status"] == "fail"
    assert "winner" not in matrix
    assert "ranking" not in matrix
    assert "score" not in matrix


def test_comparison_rejects_duplicate_model_reports() -> None:
    a = _report("provider/model-a", "pass")
    duplicate = _report("provider/model-a", "observe")

    with pytest.raises(ValueError, match="model_id values must be unique"):
        comparison_matrix((a, duplicate))


def test_comparison_requires_same_evaluator_version() -> None:
    scenario = _scenario()
    runner = HabitationRunner()
    run_a = runner.run(
        scenario=scenario,
        model_id="provider/model-a",
        target=Target("a"),
    )
    run_b = runner.run(
        scenario=scenario,
        model_id="provider/model-b",
        target=Target("b"),
    )
    finding = EvaluationFinding(
        criterion_id="continuity",
        status="observe",
        summary="same criterion",
    )
    report_a = build_model_report(
        scenario=scenario,
        run=run_a,
        evaluator_id="judge-v1",
        findings=(finding,),
    )
    report_b = build_model_report(
        scenario=scenario,
        run=run_b,
        evaluator_id="judge-v2",
        findings=(finding,),
    )

    with pytest.raises(ValueError, match="same evaluator_id"):
        comparison_matrix((report_a, report_b))


def test_finding_rejects_invalid_runtime_types() -> None:
    with pytest.raises(ValueError, match="criterion_id must be a non-empty string"):
        EvaluationFinding(
            criterion_id=123,  # type: ignore[arg-type]
            status="pass",
            summary="x",
        )

    with pytest.raises(ValueError, match="unsupported finding status"):
        EvaluationFinding(
            criterion_id="x",
            status=["pass"],  # type: ignore[arg-type]
            summary="x",
        )

    with pytest.raises(ValueError, match="measurements must be a mapping"):
        EvaluationFinding(
            criterion_id="x",
            status="observe",
            summary="x",
            measurements=[],  # type: ignore[arg-type]
        )


def test_oracle_evaluator_requires_exact_criteria_and_records_provenance() -> None:
    scenario = HabitationScenario(
        scenario_id="oracle-eval-life",
        scenario_version="3",
        subject_id="u1",
        hidden_oracle={
            "evaluation_schema": ORACLE_SCHEMA_V1,
            "criteria": [
                "cross_session_continuity",
                "epistemic_restraint",
            ],
            "latent_truth": {"evaluation_only": True},
        },
        events=(
            LifeEvent(
                event_id="e1",
                occurred_at=BASE,
                channel="conversation",
                payload="first",
            ),
            LifeEvent(
                event_id="e2",
                occurred_at=BASE + timedelta(days=1),
                channel="conversation",
                payload="second",
            ),
        ),
    )
    run = HabitationRunner().run(
        scenario=scenario,
        model_id="provider/model-a",
        target=Target("a"),
    )
    provenance = EvaluatorProvenance(
        evaluator_id="judge-model-v2",
        evaluator_kind="model",
        provider="provider-x",
        model="judge-x",
        version="2026-09-20",
        config_fingerprint="sha256:test-config",
    )

    def handler(context):
        assert context.criteria == (
            "cross_session_continuity",
            "epistemic_restraint",
        )
        assert context.hidden_oracle["latent_truth"]["evaluation_only"] is True
        assert context.run is run
        return (
            EvaluationFinding(
                criterion_id="cross_session_continuity",
                status="observe",
                summary="The evaluator inspected continuity after the run.",
                evidence_event_ids=("e1", "e2"),
            ),
            EvaluationFinding(
                criterion_id="epistemic_restraint",
                status="pass",
                summary="No unsupported durable conclusion was observed.",
                evidence_event_ids=("e2",),
            ),
        )

    report = evaluate_with_oracle(
        scenario=scenario,
        run=run,
        evaluator_provenance=provenance,
        handler=handler,
    )

    assert report.artifact_schema == "aios.p16.model-evaluation.v2"
    assert report.evaluator_provenance == provenance
    assert [item.criterion_id for item in report.findings] == [
        "cross_session_continuity",
        "epistemic_restraint",
    ]


def test_oracle_evaluator_cannot_omit_or_invent_criteria() -> None:
    scenario = HabitationScenario(
        scenario_id="oracle-coverage",
        subject_id="u1",
        hidden_oracle={
            "evaluation_schema": ORACLE_SCHEMA_V1,
            "criteria": ["required-a", "required-b"],
        },
        events=(
            LifeEvent(
                event_id="e1",
                occurred_at=BASE,
                channel="conversation",
                payload="visible",
            ),
        ),
    )
    run = HabitationRunner().run(
        scenario=scenario,
        model_id="provider/model-a",
        target=Target("a"),
    )
    provenance = EvaluatorProvenance(
        evaluator_id="human-review-v1",
        evaluator_kind="human",
        version="1",
    )

    with pytest.raises(ValueError, match="exactly cover declared criteria"):
        evaluate_with_oracle(
            scenario=scenario,
            run=run,
            evaluator_provenance=provenance,
            handler=lambda context: (
                EvaluationFinding(
                    criterion_id="required-a",
                    status="observe",
                    summary="Only one required criterion was returned.",
                    evidence_event_ids=("e1",),
                ),
                EvaluationFinding(
                    criterion_id="invented-c",
                    status="observe",
                    summary="This criterion does not exist in the oracle contract.",
                    evidence_event_ids=("e1",),
                ),
            ),
        )


def test_model_evaluator_provenance_requires_provider_and_model() -> None:
    with pytest.raises(ValueError, match="requires provider and model"):
        EvaluatorProvenance(
            evaluator_id="bad-judge",
            evaluator_kind="model",
            version="1",
        )
