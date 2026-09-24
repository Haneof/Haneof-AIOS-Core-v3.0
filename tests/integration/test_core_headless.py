from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aios_core.contracts.enums import SourceClass, WakeSource
from aios_core.contracts.refs import ObjectRef
from aios_core.headless import (
    HeadlessConfig,
    HeadlessConfigurationError,
    HeadlessCore,
    HeadlessWriterBusy,
)
from aios_core.headless.testing import deterministic_model_handler
from aios_core.headless.cli import main as headless_cli_main
from aios_core.ingest.reality import RealityRecord, SourceAdapterSpec
from aios_core.runtime.background_attempt import BackgroundModelExecutionInDoubt
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.turn_execution import TurnExecutionInDoubt
from aios_core.wake.service import WakeSignalRequest


UTC = timezone.utc
T0 = datetime(2026, 9, 24, 8, 0, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
T2 = T0 + timedelta(hours=2)


class CountingHandler:
    def __init__(self, response: str = "ok") -> None:
        self.calls = 0
        self.response = response

    def __call__(self, _snapshot):
        self.calls += 1
        return ModelDirective(response=self.response)


def config(tmp_path):
    return HeadlessConfig(world_path=tmp_path / "world.sqlite")


def test_headless_start_turn_ingest_stop_restart_same_world(tmp_path):
    handler = deterministic_model_handler
    cfg = config(tmp_path)
    spec = SourceAdapterSpec(
        adapter_id="headless-test-source",
        source_kind="headless_test",
        dimension="dim:headless_test_fact",
        source_class=SourceClass.USER,
        default_modality="text",
    )
    record = RealityRecord(
        external_record_id="fact-1",
        occurred_at=T0,
        received_at=T0,
        value="durable external fact",
        modality="text",
    )

    with HeadlessCore(config=cfg, model_handler=handler) as first:
        receipt = first.ingest_external_fact(adapter=spec, record=record)
        result = first.submit_user_turn(
            session_id="headless-session",
            turn_index=1,
            user_input="hello",
            occurred_at=T1,
        )
        before = first.status()
        assert receipt.observation_id
        assert result.runtime.response == "HEADLESS_MECHANICAL_OK"
        assert before["world_revision"] == before["index_watermark"]
        assert first.runtime is not None
        meter_count = len(
            first.runtime.metering.list_model_calls(subject_id=cfg.subject_id)
        )
        assert meter_count == 1

    with HeadlessCore(config=cfg, model_handler=handler) as second:
        after = second.status()
        assert after["world_revision"] == before["world_revision"]
        assert after["index_watermark"] == before["index_watermark"]
        assert after["index_lag"] == 0
        payload = second.store.get_payload(receipt.observation_id, revision=1)
        assert payload["value"] == "durable external fact"
        assert second.runtime is not None
        assert len(
            second.runtime.metering.list_model_calls(subject_id=cfg.subject_id)
        ) == meter_count

    with HeadlessCore(config=cfg, model_handler=handler) as third:
        assert third.status()["world_revision"] == before["world_revision"]
        assert third.runtime is not None
        assert len(
            third.runtime.metering.list_model_calls(subject_id=cfg.subject_id)
        ) == meter_count


def test_headless_single_writer_fails_closed_and_releases_on_stop(tmp_path):
    cfg = config(tmp_path)
    first = HeadlessCore(config=cfg, model_handler=CountingHandler())
    second = HeadlessCore(config=cfg, model_handler=CountingHandler())
    first.start()
    try:
        before = first.status()["world_revision"]
        with pytest.raises(HeadlessWriterBusy):
            second.start()
        assert first.status()["world_revision"] == before
    finally:
        first.stop()

    try:
        second.start()
        assert second.status()["writer_lease_held"] is True
        assert second.status()["world_revision"] == before
    finally:
        second.stop()


def test_headless_writer_identity_is_canonical_and_non_overridable(tmp_path):
    world = tmp_path / "world.sqlite"
    canonical = HeadlessConfig(world_path=world)
    assert str(canonical.lock_path) == str(world.resolve()) + ".writer.lock"

    with pytest.raises(
        HeadlessConfigurationError,
        match="must equal the canonical World writer lease path",
    ):
        HeadlessConfig(
            world_path=world,
            lock_path=tmp_path / "writer-b.lock",
        )

    explicit_canonical = HeadlessConfig(
        world_path=world,
        lock_path=canonical.lock_path,
    )
    assert explicit_canonical.lock_path == canonical.lock_path


def test_headless_alternate_lock_path_cannot_bypass_live_world_writer(tmp_path):
    world = tmp_path / "world.sqlite"
    cfg_a = HeadlessConfig(world_path=world)
    writer_a = HeadlessCore(config=cfg_a, model_handler=CountingHandler()).start()
    try:
        before = writer_a.status()["world_revision"]
        with pytest.raises(
            HeadlessConfigurationError,
            match="must equal the canonical World writer lease path",
        ):
            HeadlessConfig(
                world_path=world,
                lock_path=tmp_path / "alternate-writer.lock",
            )
        assert writer_a.status()["world_revision"] == before
    finally:
        writer_a.stop()

    writer_b = HeadlessCore(
        config=HeadlessConfig(world_path=world, lock_path=cfg_a.lock_path),
        model_handler=CountingHandler(),
    ).start()
    try:
        assert writer_b.status()["writer_lease_held"] is True
        assert writer_b.status()["world_revision"] == before
    finally:
        writer_b.stop()


def test_headless_stale_canonical_lock_file_without_os_lease_reopens(tmp_path):
    cfg = config(tmp_path)
    first = HeadlessCore(config=cfg, model_handler=CountingHandler()).start()
    before = first.status()["world_revision"]
    first.stop()

    assert cfg.lock_path is not None
    cfg.lock_path.write_text(
        '{"kind":"stale-corrective-probe","pid":999999,"host":"stale"}\\n',
        encoding="utf-8",
    )

    second = HeadlessCore(config=cfg, model_handler=CountingHandler()).start()
    try:
        assert second.status()["writer_lease_held"] is True
        assert second.status()["world_revision"] == before
    finally:
        second.stop()


def test_headless_relative_and_absolute_world_share_writer_identity(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    relative = HeadlessConfig(world_path="world.sqlite")
    absolute = HeadlessConfig(world_path=(tmp_path / "world.sqlite").resolve())
    assert relative.world_path == absolute.world_path
    assert relative.lock_path == absolute.lock_path


def test_headless_symlinked_existing_world_shares_writer_identity(tmp_path):
    target = tmp_path / "world.sqlite"
    cfg = HeadlessConfig(world_path=target)
    first = HeadlessCore(config=cfg, model_handler=CountingHandler()).start()
    first.stop()

    link = tmp_path / "world-link.sqlite"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    via_link = HeadlessConfig(world_path=link)
    assert via_link.world_path == cfg.world_path
    assert via_link.lock_path == cfg.lock_path


def test_headless_cli_lock_override_is_validation_only(tmp_path):
    world = tmp_path / "world.sqlite"
    rc = headless_cli_main(
        [
            "--world",
            str(world),
            "--lock",
            str(tmp_path / "alternate.lock"),
            "--model-handler",
            "aios_core.headless.testing:deterministic_model_handler",
            "status",
        ]
    )
    assert rc == 2


def test_headless_env_lock_override_is_validation_only(tmp_path, monkeypatch):
    world = tmp_path / "world.sqlite"
    monkeypatch.setenv("AIOS_LOCK_PATH", str(tmp_path / "alternate-env.lock"))
    rc = headless_cli_main(
        [
            "--world",
            str(world),
            "--model-handler",
            "aios_core.headless.testing:deterministic_model_handler",
            "status",
        ]
    )
    assert rc == 2


def test_headless_restart_preserves_fix003_pre_admission_and_requires_authorization(
    tmp_path,
):
    cfg = config(tmp_path)
    handler = CountingHandler("recovered")
    first = HeadlessCore(config=cfg, model_handler=handler).start()
    assert first.runtime is not None
    original_admit = first.runtime.background_model_attempts.admit

    def crash_before_attempt_admission(**_kwargs):
        raise RuntimeError("simulated crash before durable model-attempt admission")

    first.runtime.background_model_attempts.admit = crash_before_attempt_admission
    with pytest.raises(RuntimeError, match="simulated crash"):
        first.submit_user_turn(
            session_id="fix003",
            turn_index=1,
            user_input="same exact input",
            occurred_at=T1,
        )
    assert handler.calls == 0
    first.runtime.background_model_attempts.admit = original_admit
    first.stop()

    second = HeadlessCore(config=cfg, model_handler=handler).start()
    try:
        assert second.runtime is not None
        inspection = second.runtime.inspect_turn_execution(
            session_id="fix003",
            turn_index=1,
            user_input="same exact input",
            occurred_at=T1,
        )
        assert inspection.recovery_disposition == "safe_to_retry"
        assert handler.calls == 0

        with pytest.raises(TurnExecutionInDoubt):
            second.submit_user_turn(
                session_id="fix003",
                turn_index=1,
                user_input="same exact input",
                occurred_at=T1,
            )
        assert handler.calls == 0

        authorized = second.runtime.authorize_turn_retry(
            session_id="fix003",
            turn_index=1,
            user_input="same exact input",
            occurred_at=T1,
            evidence="operator verified provider submission never began",
        )
        assert authorized.retry_authorized is True

        recovered = second.submit_user_turn(
            session_id="fix003",
            turn_index=1,
            user_input="same exact input",
            occurred_at=T1,
        )
        assert recovered.runtime.response == "recovered"
        assert handler.calls == 1
    finally:
        second.stop()


def test_headless_restart_keeps_pending_due_work_and_executes_after_reopen(tmp_path):
    cfg = config(tmp_path)
    handler = CountingHandler("wake-completed")
    first = HeadlessCore(config=cfg, model_handler=handler).start()
    assert first.runtime is not None
    receipt = first.runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id="headless-pending-restart",
            observed_at=T1,
            priority=100,
            dedupe_key="headless-pending-restart",
        )
    )
    assert handler.calls == 0
    first.stop()

    second = HeadlessCore(config=cfg, model_handler=handler).start()
    try:
        due = second.process_due_work(
            now=T2,
            max_wakes=1,
            include_periodic_review=False,
        )
        assert len(due.wakes) == 1
        assert due.wakes[0].wake.wake_id == receipt.wake_id
        assert due.wakes[0].wake.state == "completed"
        assert due.wakes[0].runtime is not None
        assert due.wakes[0].runtime.response == "wake-completed"
        assert handler.calls == 1
    finally:
        second.stop()

    third = HeadlessCore(config=cfg, model_handler=handler).start()
    try:
        due_again = third.process_due_work(
            now=T2 + timedelta(minutes=1),
            max_wakes=1,
            include_periodic_review=False,
        )
        assert due_again.wakes == ()
        assert handler.calls == 1
    finally:
        third.stop()


class AmbiguousHandler:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, _snapshot):
        self.calls += 1
        raise RuntimeError("provider transport became ambiguous after dispatch boundary")


def test_headless_restart_preserves_fix002_background_in_doubt_without_reinvoke(
    tmp_path,
):
    cfg = config(tmp_path)
    handler = AmbiguousHandler()
    first = HeadlessCore(config=cfg, model_handler=handler).start()
    assert first.runtime is not None
    receipt = first.runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id="headless-restart-probe",
            observed_at=T1,
            priority=100,
            dedupe_key="headless-restart-probe",
        )
    )
    with pytest.raises(RuntimeError, match="ambiguous"):
        first.runtime.run_wake(
            wake_ref=ObjectRef(object_id=receipt.wake_id, revision=receipt.revision),
            now=T1,
        )
    assert handler.calls == 1
    first.stop()

    second = HeadlessCore(config=cfg, model_handler=handler).start()
    try:
        assert second.runtime is not None
        with pytest.raises(BackgroundModelExecutionInDoubt):
            second.runtime.run_wake(
                wake_ref=ObjectRef(
                    object_id=receipt.wake_id,
                    revision=receipt.revision,
                ),
                now=T2,
            )
        assert handler.calls == 1
    finally:
        second.stop()


class TemporalProbeHandler:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, snapshot):
        self.calls += 1
        if snapshot.round_index == 0:
            return ModelDirective(
                capability_calls=(
                    CapabilityCall(
                        name="search_world",
                        arguments={"query": "future-knowledge-sentinel", "limit": 10},
                        call_id="temporal-probe",
                    ),
                )
            )
        result = snapshot.capability_history[-1]
        assert result.ok is True
        assert "future-knowledge-sentinel" not in str(result.data)
        return ModelDirective(response="historical cut preserved")


def test_headless_restart_keeps_fix001_historical_knowledge_cut(tmp_path):
    cfg = config(tmp_path)
    setup_handler = CountingHandler()
    late_spec = SourceAdapterSpec(
        adapter_id="late-import",
        source_kind="late_import",
        dimension="dim:late_import",
        source_class=SourceClass.USER,
        default_modality="text",
    )
    late_record = RealityRecord(
        external_record_id="late-1",
        occurred_at=T0,
        received_at=T2,
        value="future-knowledge-sentinel",
        modality="text",
    )

    first = HeadlessCore(config=cfg, model_handler=setup_handler).start()
    assert first.runtime is not None
    first.ingest_external_fact(adapter=late_spec, record=late_record)
    receipt = first.runtime.wake_bus.emit(
        WakeSignalRequest(
            wake_source=WakeSource.SAFETY,
            rule_id="historical-background-cut",
            observed_at=T1,
            priority=100,
            dedupe_key="historical-background-cut",
        )
    )
    first.stop()

    probe = TemporalProbeHandler()
    restarted = HeadlessCore(config=cfg, model_handler=probe).start()
    try:
        assert restarted.runtime is not None
        result = restarted.runtime.run_wake(
            wake_ref=ObjectRef(
                object_id=receipt.wake_id,
                revision=receipt.revision,
            ),
            now=T1,
        )
        assert result.runtime is not None
        assert result.runtime.response == "historical cut preserved"
        assert probe.calls == 2
    finally:
        restarted.stop()


# ---------------------------------------------------------------------------
# CORE-HEADLESS-001-CORRECTIVE-001 fresh independent acceptance probes.
# Probe branch only; do not merge.
# ---------------------------------------------------------------------------

def test_independent_corrective_probe_historical_alt_lock_is_rejected_and_world_unchanged(
    tmp_path,
):
    world = tmp_path / "world.sqlite"
    canonical = HeadlessConfig(world_path=world)
    alternate_lock = tmp_path / "historical-bypass-writer-b.lock"
    writer_a = HeadlessCore(config=canonical, model_handler=CountingHandler()).start()
    writer_b = HeadlessCore(
        config=HeadlessConfig(world_path=world),
        model_handler=CountingHandler(),
    )
    try:
        before = writer_a.status()["world_revision"]
        with pytest.raises(
            HeadlessConfigurationError,
            match="must equal the canonical World writer lease path",
        ):
            HeadlessConfig(world_path=world, lock_path=alternate_lock)
        assert not alternate_lock.exists()
        assert writer_a.status()["world_revision"] == before
        with pytest.raises(HeadlessWriterBusy):
            writer_b.start()
        assert writer_a.status()["world_revision"] == before
    finally:
        writer_b.stop()
        writer_a.stop()

    writer_b.start()
    try:
        assert writer_b.status()["writer_lease_held"] is True
        assert writer_b.status()["world_revision"] == before
    finally:
        writer_b.stop()


def test_independent_corrective_probe_textual_world_aliases_share_one_lease(
    tmp_path,
):
    alias_dir = tmp_path / "alias"
    alias_dir.mkdir()
    textual_alias = alias_dir / ".." / "world.sqlite"
    absolute = (tmp_path / "world.sqlite").resolve()
    cfg_alias = HeadlessConfig(world_path=textual_alias)
    cfg_absolute = HeadlessConfig(world_path=absolute)
    assert cfg_alias.world_path == cfg_absolute.world_path
    assert cfg_alias.lock_path == cfg_absolute.lock_path

    writer_a = HeadlessCore(config=cfg_alias, model_handler=CountingHandler()).start()
    writer_b = HeadlessCore(config=cfg_absolute, model_handler=CountingHandler())
    try:
        before = writer_a.status()["world_revision"]
        with pytest.raises(HeadlessWriterBusy):
            writer_b.start()
        assert writer_a.status()["world_revision"] == before
    finally:
        writer_b.stop()
        writer_a.stop()


def test_independent_corrective_probe_existing_world_symlink_cannot_split_lease(
    tmp_path,
):
    target = tmp_path / "world.sqlite"
    cfg_target = HeadlessConfig(world_path=target)
    writer_a = HeadlessCore(config=cfg_target, model_handler=CountingHandler()).start()
    link = tmp_path / "world-alias.sqlite"
    try:
        try:
            link.symlink_to(target)
        except OSError as exc:
            pytest.skip(f"symlink unavailable: {exc}")
        cfg_link = HeadlessConfig(world_path=link)
        assert cfg_link.world_path == cfg_target.world_path
        assert cfg_link.lock_path == cfg_target.lock_path
        writer_b = HeadlessCore(config=cfg_link, model_handler=CountingHandler())
        try:
            before = writer_a.status()["world_revision"]
            with pytest.raises(HeadlessWriterBusy):
                writer_b.start()
            assert writer_a.status()["world_revision"] == before
        finally:
            writer_b.stop()
    finally:
        writer_a.stop()


def test_independent_corrective_probe_stale_metadata_is_not_liveness_truth(
    tmp_path,
):
    cfg = HeadlessConfig(world_path=tmp_path / "world.sqlite")
    writer_a = HeadlessCore(config=cfg, model_handler=CountingHandler()).start()
    before = writer_a.status()["world_revision"]
    writer_a.stop()
    assert cfg.lock_path is not None
    cfg.lock_path.write_text(
        '{"kind":"stale-independent-corrective","pid":424242,"host":"stale"}\n',
        encoding="utf-8",
    )
    writer_b = HeadlessCore(config=cfg, model_handler=CountingHandler()).start()
    try:
        assert writer_b.status()["writer_lease_held"] is True
        assert writer_b.status()["world_revision"] == before
        assert "424242" not in cfg.lock_path.read_text(encoding="utf-8")
    finally:
        writer_b.stop()


def test_independent_corrective_probe_cli_and_env_lock_are_validation_only(
    tmp_path,
    monkeypatch,
    capsys,
):
    world = tmp_path / "world.sqlite"
    model = "aios_core.headless.testing:deterministic_model_handler"
    alternate_cli = tmp_path / "cli-alternate.lock"
    rc_cli = headless_cli_main(
        [
            "--world",
            str(world),
            "--lock",
            str(alternate_cli),
            "--model-handler",
            model,
            "status",
        ]
    )
    assert rc_cli == 2
    assert not alternate_cli.exists()
    capsys.readouterr()

    alternate_env = tmp_path / "env-alternate.lock"
    monkeypatch.setenv("AIOS_WORLD_PATH", str(world))
    monkeypatch.setenv("AIOS_MODEL_HANDLER", model)
    monkeypatch.setenv("AIOS_LOCK_PATH", str(alternate_env))
    rc_env = headless_cli_main(["status"])
    assert rc_env == 2
    assert not alternate_env.exists()
    capsys.readouterr()

    monkeypatch.delenv("AIOS_LOCK_PATH")
    canonical_lock = HeadlessConfig(world_path=world).lock_path
    assert canonical_lock is not None
    rc_canonical = headless_cli_main(
        [
            "--world",
            str(world),
            "--lock",
            str(canonical_lock),
            "--model-handler",
            model,
            "status",
        ]
    )
    assert rc_canonical == 0
