"""Positive regressions for audit A01-A10. Synthetic Worlds/models ONLY."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event as ThreadEvent

from aios_core.ai_world import AIWorldClaimRequest, AIWorldDomain
from aios_core.contracts.enums import ErrorCode, EventStatus, ObjectType
from aios_core.dependency.graph import find_dependency_cycle
from aios_core.events.service import EventDimensionService, EventWriteRequest, EventTransitionRequest
from aios_core.policy.service import CognitivePolicyUpdateRequest
from aios_core.runtime import TurnAlreadyCompleted, TurnExecutionInDoubt, TurnInputConflict
from aios_core.summaries.dimension_summary import _stable_id

from datetime import datetime, timedelta, timezone
import pytest
from aios_core.contracts.enums import SourceClass, PolicyClass, UserReaction
from aios_core.contracts.models import Observation, Dependency
from aios_core.contracts.operations import OperationRequest
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.time import TemporalExtent
from aios_core.storage.sqlite_store import SQLiteWorldStore, StoreError
from aios_core.query.search import WorldSearchIndex
from aios_core.writeback.cognition import CognitionWritebackService, ClaimWriteRequest
from aios_core.revision.service import CognitionRevisionService, ClaimRevisionRequest
from aios_core.communication.service import CommunicationExperienceService, CommunicationExperienceRequest
from aios_core.policy.service import CognitivePolicyRegistry, CognitivePolicyCreateRequest
from aios_core.summaries.dimension_summary import DimensionSummaryService
from aios_core.runtime.turn_runtime import FusedTurnRuntime
from aios_core.runtime.cognitive_runtime import ModelDirective
NOW = datetime(2030, 1, 2, tzinfo=timezone.utc)
DAY = NOW - timedelta(days=1)

def obs(oid, value, subject='user_1'):
    return Observation(
        object_id=oid, subject_id=subject, occurred=TemporalExtent.point(DAY),
        learned_at=DAY, recorded_at=DAY, created_by='synthetic-audit',
        source_kind='synthetic_sensor', modality='text', value=value,
        metadata={'dimension': 'dim:synthetic'},
    )


def commit(store, objects, key):
    return store.commit(objects, OperationRequest(
        operation_name='audit.synthetic',
        expected_world_revision=store.current_world_revision(),
        reason='SYNTHETIC only', idempotency_key=key, source_class=SourceClass.USER,
    ))


def world(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    store = SQLiteWorldStore(tmp_path / 'world.sqlite')
    return store, WorldSearchIndex(tmp_path / 'index.sqlite', store=store)


def grounded_experience(tmp_path):
    store, index = world(tmp_path)
    commit(store, [obs('old', 'SYNTHETIC old feedback'),
                   obs('correction', 'SYNTHETIC correction')], 'seed')
    index.catch_up()
    claim = CognitionWritebackService(store=store, index=index).commit_claim(
        ClaimWriteRequest(
            content='SYNTHETIC old interpretation',
            evidence_refs=(ObjectRef(object_id='old', revision=1),),
            confidence=0.8, dimension='dim:ai_user_understanding',
        ), learned_at=NOW,
    )
    experience = CommunicationExperienceService(store=store, index=index).record(
        CommunicationExperienceRequest(
            scenario='SYNTHETIC', style='SYNTHETIC concise',
            user_reaction=next(iter(UserReaction)),
            evidence_refs=(ObjectRef(object_id='old', revision=1),
                           ObjectRef(object_id=claim.claim_id, revision=1)),
        ), recorded_at=NOW + timedelta(seconds=1),
    )
    return store, index, claim, experience


def new_policy(registry, ref):
    return registry.register(CognitivePolicyCreateRequest(
        policy_id='communication.response_style', scope='user',
        policy_class=PolicyClass.COGNITIVE_POLICY, default_value='normal',
        current_value='SYNTHETIC learned value', mutable_by_ai=True,
        reason='SYNTHETIC feedback case', evidence_refs=(ref,),
        changed_by='resident_ai', evaluation_window='24h',
    ), changed_at=NOW + timedelta(seconds=2), actor_is_ai=True)


def revise(store, index, claim):
    return CognitionRevisionService(store=store, index=index).apply(
        ClaimRevisionRequest(
            target_ref=ObjectRef(object_id=claim.claim_id, revision=1), mode='revise',
            reason='SYNTHETIC correction',
            evidence_refs=(ObjectRef(object_id='correction', revision=1),),
            replacement_content='SYNTHETIC corrected interpretation',
        ), changed_at=NOW + timedelta(seconds=3),
    )


def prepare(service):
    return service.prepare(
        dimension='dim:synthetic', granularity='day', window_start=DAY,
        window_end=NOW - timedelta(microseconds=1),
    )


def test_a01_policy_invalidation_is_atomic_and_preserves_version_history(tmp_path):
    s, i, claim, exp = grounded_experience(tmp_path)
    registry = CognitivePolicyRegistry(store=s, index=i)
    receipt = new_policy(registry, ObjectRef(object_id=exp.experience_id, revision=1))
    before = s.current_world_revision()
    old = s.get_payload(receipt.object_id, revision=1)
    revise(s, i, claim)
    assert s.current_world_revision() == before + 1
    policy = registry.latest('communication.response_style')
    assert policy.status == 'stale_review_required'
    assert policy.revision == policy.version == 2
    assert policy.previous_version == policy.rollback_pointer == 1
    assert s.get_payload(receipt.object_id, revision=1) == old
    assert s.get_payload(claim.claim_id)['revision'] == 2
    assert s.get_payload(exp.experience_id)['status'] == 'stale_review_required'
    assert registry.effective_value(policy.policy_id, 'fallback') == 'fallback'
    runtime = FusedTurnRuntime(store=s, index=i, model_handler=lambda _: ModelDirective(silence=True))
    assert policy.policy_id not in runtime._cognitive_policy_context()
    # Reviewing with fresh reality evidence creates the next coherent version.
    restored = registry.update(CognitivePolicyUpdateRequest(
        policy_id=policy.policy_id, current_value='reviewed', reason='SYNTHETIC review',
        evidence_refs=(ObjectRef(object_id='correction', revision=1),)), changed_at=NOW)
    assert restored.revision == 3
    assert registry.effective_value(policy.policy_id) == 'reviewed'


def test_a02_runtime_invalidates_paired_ai_self_but_not_other_user(tmp_path):
    s, i = world(tmp_path)
    commit(s, [obs('old', 'old reality'), obs('correction', 'corrected')], 'seed')
    runtime = FusedTurnRuntime(store=s, index=i, model_handler=lambda _: ModelDirective(silence=True))
    a = runtime.writeback.commit_claim(ClaimWriteRequest(
        content='SYNTHETIC base', evidence_refs=(ObjectRef(object_id='old', revision=1),),
        confidence=.8, dimension='dim:synthetic'), learned_at=NOW)
    b = runtime.ai_world.commit(AIWorldClaimRequest(
        domain=AIWorldDomain.SELF, statement='SYNTHETIC self', confidence=.8,
        evidence_refs=(ObjectRef(object_id=a.claim_id, revision=1), ObjectRef(object_id='old', revision=1))), learned_at=NOW)
    from aios_core.contracts.models import Claim
    other = Claim.model_validate(s.get_payload(a.claim_id)).model_copy(update={'object_id': 'other', 'subject_id': 'user_2'})
    # An in-scope edge does NOT authorize a cross-user dependent endpoint.
    edge = Dependency(object_id='cross', subject_id='user_1', learned_at=NOW, recorded_at=NOW, created_by='synthetic',
        dependent_ref=ObjectRef(object_id='other', revision=1),
        dependency_ref=ObjectRef(object_id=a.claim_id, revision=1), dependency_type='synthetic')
    commit(s, [other, edge], 'other')
    runtime.revision.apply(ClaimRevisionRequest(target_ref=ObjectRef(object_id=a.claim_id, revision=1),
        mode='revise', reason='SYNTHETIC correction', replacement_content='corrected',
        evidence_refs=(ObjectRef(object_id='correction', revision=1),)), changed_at=NOW)
    assert s.get_payload(b.claim.claim_id)['status'] == 'stale_review_required'
    assert b.claim.claim_id not in {x.object_id for x in runtime.ai_world.current()}
    assert s.get_payload('other')['revision'] == 1


def test_a03_rejected_event_invalidates_claim_summary_and_search(tmp_path):
    s, i = world(tmp_path)
    commit(s, [obs('old', 'old'), obs('correction', 'corrected')], 'seed')
    events = EventDimensionService(store=s, index=i)
    event = events.form_event(EventWriteRequest(title='SYNTHETIC event', interpretation='initial',
        event_time=TemporalExtent.point(DAY), evidence_refs=(ObjectRef(object_id='old', revision=1),),
        confidence=.8), learned_at=DAY)
    claim = CognitionWritebackService(store=s, index=i).commit_claim(ClaimWriteRequest(
        content='SYNTHETIC from event', evidence_refs=(ObjectRef(object_id=event.event_id, revision=1),),
        confidence=.8, dimension='dim:synthetic'), learned_at=DAY)
    svc = DimensionSummaryService(store=s, index=i)
    prepared = svc.prepare(dimension='dim:events', granularity='day', window_start=DAY,
                           window_end=NOW-timedelta(microseconds=1))
    summary = svc.commit(prepared, content='SYNTHETIC event summary', generated_at=NOW)
    before = s.current_world_revision()
    events.transition(EventTransitionRequest(event_ref=ObjectRef(object_id=event.event_id, revision=1),
        new_status=EventStatus.REJECTED, reason='SYNTHETIC rejection',
        evidence_refs=(ObjectRef(object_id='correction', revision=1),)), changed_at=NOW)
    assert s.current_world_revision() == before + 1
    assert s.get_payload(claim.claim_id)['status'] == 'stale_review_required'
    assert s.get_payload(summary.object_id)['summary_status'] == 'stale'
    ids = {x.object_id for x in i.recall_candidates('SYNTHETIC', limit=50).hits}
    assert claim.claim_id not in ids and summary.object_id not in ids
    assert s.get_payload(summary.object_id, revision=1)['summary_status'] == 'current'


@pytest.mark.parametrize('operation', ['register', 'update', 'rollback'])
@pytest.mark.parametrize('ref_version', [1, 2])
def test_a04_policy_rejects_stale_and_superseded_evidence(tmp_path, operation, ref_version):
    s, i, claim, exp = grounded_experience(tmp_path)
    registry = CognitivePolicyRegistry(store=s, index=i)
    if operation != 'register':
        new_policy(registry, ObjectRef(object_id='old', revision=1))
        registry.update(CognitivePolicyUpdateRequest(policy_id='communication.response_style',
            current_value='new', reason='SYNTHETIC', evidence_refs=(ObjectRef(object_id='old', revision=1),)), changed_at=NOW)
    revise(s, i, claim)
    ref = ObjectRef(object_id=exp.experience_id, revision=ref_version)
    before = s.current_world_revision()
    with pytest.raises(ValueError, match='current, active'):
        if operation == 'register':
            new_policy(registry, ref)
        elif operation == 'update':
            registry.update(CognitivePolicyUpdateRequest(policy_id='communication.response_style',
                current_value='invalid', reason='SYNTHETIC', evidence_refs=(ref,)), changed_at=NOW)
        else:
            registry.rollback('communication.response_style', 1, reason='SYNTHETIC',
                evidence_refs=(ref,), changed_by='resident_ai', changed_at=NOW)
    assert s.current_world_revision() == before


@pytest.mark.parametrize('size,limit', [(4, 2), (50001, 50000)])
def test_a05_whole_commit_indexing_and_rebuild(tmp_path, size, limit):
    s, i = world(tmp_path)
    commit(s, [obs(f'o{k:05d}', 'SYNTHETIC sentinel') for k in range(size)], 'batch')
    assert len(s.revisions_after(0, limit=2)) == 2  # old bounded default retained
    assert i.catch_up(max_rows=limit) == size
    assert i.catch_up() == 0
    assert i.watermark() == s.current_world_revision() == 1
    with sqlite3.connect(i.db_path) as conn:
        assert conn.execute('select count(*) from search_occurred').fetchone()[0] == size
        # Simulate an old damaged projection with a falsely current watermark.
        conn.execute('delete from search_occurred where object_id=?', ('o00000',))
    assert i.rebuild() == size
    with sqlite3.connect(i.db_path) as conn:
        assert conn.execute('select count(*) from search_occurred').fetchone()[0] == size


def test_a05_concurrent_catchup_and_mixed_commit_boundary(tmp_path):
    s, i = world(tmp_path)
    commit(s, [obs('a', 'first')], 'a')
    commit(s, [obs(f'b{x}', 'second') for x in range(4)], 'b')
    with ThreadPoolExecutor(2) as pool:
        counts = list(pool.map(lambda _: i.catch_up(max_rows=2), range(2)))
    assert sorted(counts) == [0, 5]
    assert i.watermark() == 2


def test_a06_runtime_schedules_ai_self_and_c14_without_other_user(tmp_path):
    s, i = world(tmp_path)
    commit(s, [obs('old', 'SYNTHETIC reality'), obs('private_other', 'OTHER USER', 'user_2')], 'seed')
    inputs = []
    def handler(request):
        inputs.append(request)
        return 'SYNTHETIC summary'
    runtime = FusedTurnRuntime(store=s, index=i, model_handler=lambda _: ModelDirective(silence=True),
                              dimension_summary_handler=handler)
    ai = runtime.ai_world.commit(AIWorldClaimRequest(domain=AIWorldDomain.SELF,
        statement='SYNTHETIC self', confidence=.8, evidence_refs=(ObjectRef(object_id='old', revision=1),)),
        learned_at=DAY+timedelta(hours=1))
    assert 'dim:ai_self' in runtime.dimension_summary_scheduler.active_dimensions()
    result = runtime.run_due_dimension_summaries(now=NOW, scales=('day',), dimensions=('dim:ai_self',))
    assert len(result.commits) == 1
    assert inputs[0].subject_id == 'user_1'
    assert ai.claim.claim_id in {x.object_id for x in inputs[0].sources}
    assert 'private_other' not in {x.object_id for x in inputs[0].sources}
    assert s.get_payload(result.commits[0].object_id)['subject_id'] == 'user_1'
    assert s.list_payloads(object_type=ObjectType.WAKE, subject_id='user_1')
    assert not runtime.run_due_dimension_summaries(now=NOW, scales=('day',),
                                                  dimensions=('dim:ai_self',)).commits


def test_a07_truncated_summary_rejected_at_service_boundary(tmp_path):
    s, i = world(tmp_path)
    commit(s, [obs('a', 'one'), obs('b', 'two')], 'seed')
    service = DimensionSummaryService(store=s, index=i, max_source_objects=1)
    request = prepare(service)
    assert request.truncated
    before = s.current_world_revision()
    with pytest.raises(ValueError, match='truncated'):
        service.commit(request, content='SYNTHETIC incomplete', generated_at=NOW)
    assert s.current_world_revision() == before


def test_a07_prepared_summary_rejects_changed_source_and_foreign_owner(tmp_path):
    s, i = world(tmp_path)
    original = obs('a', 'one')
    commit(s, [original], 'seed')
    service = DimensionSummaryService(store=s, index=i)
    request = prepare(service)
    other = DimensionSummaryService(store=s, index=i, subject_id='user_2')
    with pytest.raises(ValueError, match='bound'):
        other.commit(request, content='SYNTHETIC foreign', generated_at=NOW)
    with pytest.raises(ValueError, match='bound'):
        other.mark_stale_if_present(request, changed_at=NOW, reason='foreign')
    commit(s, [original.model_copy(update={'revision': 2, 'status': 'stale_review_required'})], 'advance')
    with pytest.raises(ValueError, match='current'):
        service.commit(request, content='SYNTHETIC outdated', generated_at=NOW)


def test_a08_subject_ids_are_distinct_and_legacy_owned_id_is_preserved(tmp_path):
    s, i = world(tmp_path)
    commit(s, [obs('u1', 'one'), obs('u2', 'two', 'user_2')], 'seed')
    one = DimensionSummaryService(store=s, index=i)
    two = DimensionSummaryService(store=s, index=i, subject_id='user_2')
    first = one.commit(prepare(one), content='SYNTHETIC one', generated_at=NOW)
    second = two.commit(prepare(two), content='SYNTHETIC two', generated_at=NOW)
    assert first.object_id != second.object_id
    assert first.revision == second.revision == 1
    legacy_id = 'sum_' + _stable_id('dim:synthetic', 'day', DAY.isoformat(),
                                  (NOW-timedelta(microseconds=1)).isoformat())
    # Separate World models upgrade from the original subject-less identifier.
    old_world, old_index = world(tmp_path / 'legacy')
    commit(old_world, [obs('u1', 'one'), obs('u2', 'two', 'user_2')], 'seed')
    from aios_core.contracts.models import Summary
    legacy = Summary.model_validate(s.get_payload(first.object_id)).model_copy(update={'object_id': legacy_id})
    commit(old_world, [legacy], 'legacy')
    old_one = DimensionSummaryService(store=old_world, index=old_index)
    old_two = DimensionSummaryService(store=old_world, index=old_index, subject_id='user_2')
    updated = old_one.commit(prepare(old_one), content='SYNTHETIC upgraded', generated_at=NOW)
    foreign = old_two.commit(prepare(old_two), content='SYNTHETIC two', generated_at=NOW)
    assert updated.object_id == legacy_id and updated.revision == 2
    assert foreign.object_id != legacy_id and foreign.revision == 1
    old_two.mark_stale_if_present(prepare(old_two), changed_at=NOW, reason='SYNTHETIC incomplete')
    assert old_world.get_payload(legacy_id)['summary_status'] == 'current'


def turn_args():
    return dict(session_id='synthetic-session', turn_index=1, user_input='SYNTHETIC request', occurred_at=NOW)


def test_a09_completed_retry_restart_and_changed_input_never_call_model(tmp_path):
    s, i = world(tmp_path)
    calls = []
    def model(_):
        calls.append(1)
        return ModelDirective(response='SYNTHETIC response')
    runtime = FusedTurnRuntime(store=s, index=i, model_handler=model)
    first = runtime.run_turn(**turn_args())
    before = s.current_world_revision()
    for instance in (runtime, FusedTurnRuntime(store=s, index=i, model_handler=model)):
        with pytest.raises(TurnAlreadyCompleted) as error:
            instance.run_turn(**{**turn_args(), 'session_id': ' synthetic-session '})
        assert error.value.assistant_ref.object_id == first.conversation_commit.assistant_observation_id
        with pytest.raises(TurnInputConflict):
            instance.run_turn(**{**turn_args(), 'user_input': 'DIFFERENT'})
    assert len(calls) == len(runtime.metering.list_model_calls(subject_id='user_1')) == 1
    assert s.current_world_revision() == before


def test_a09_in_progress_concurrent_retry_is_refused(tmp_path):
    s, i = world(tmp_path)
    entered, release = ThreadEvent(), ThreadEvent()
    calls = []
    def model(_):
        calls.append(1)
        entered.set()
        assert release.wait(10)
        return ModelDirective(response='SYNTHETIC response')
    one = FusedTurnRuntime(store=s, index=i, model_handler=model)
    two = FusedTurnRuntime(store=s, index=i, model_handler=model)
    with ThreadPoolExecutor(2) as pool:
        pending = pool.submit(one.run_turn, **turn_args())
        try:
            assert entered.wait(10)
            with pytest.raises(TurnExecutionInDoubt):
                two.run_turn(**turn_args())
        finally:
            release.set()
        pending.result()
    assert len(calls) == 1


def test_a09_exception_keeps_uncertain_claim_but_preingested_user_is_allowed(tmp_path):
    s, i = world(tmp_path)
    calls = []
    def failing(_):
        calls.append(1)
        raise RuntimeError('SYNTHETIC provider interruption')
    runtime = FusedTurnRuntime(store=s, index=i, model_handler=failing)
    runtime.ingestor.commit_user_input(session_id='synthetic-session', turn_index=1,
        user_text='SYNTHETIC request', occurred_at=NOW)
    with pytest.raises(RuntimeError, match='provider interruption'):
        runtime.run_turn(**turn_args())
    restarted = FusedTurnRuntime(store=s, index=i, model_handler=failing)
    with pytest.raises(TurnExecutionInDoubt):
        restarted.run_turn(**turn_args())
    assert len(calls) == 1


def test_a09_legacy_assistant_output_prevents_inference(tmp_path):
    s, i = world(tmp_path)
    runtime = FusedTurnRuntime(store=s, index=i,
        model_handler=lambda _: pytest.fail('legacy retry must not call model'))
    runtime.ingestor.commit_assistant_output(session_id='synthetic-session', turn_index=1,
        assistant_text='SYNTHETIC old response', occurred_at=NOW)
    with pytest.raises(TurnAlreadyCompleted) as error:
        runtime.run_turn(**turn_args())
    assert error.value.state == 'legacy_output_present'


def test_a10_long_dag_commits_and_long_cycle_rejects_atomically(tmp_path):
    s, _ = world(tmp_path)
    n = 1100
    objects = [obs(f'node{j:04d}', 'SYNTHETIC chain') for j in range(n)]
    edges = [Dependency(object_id=f'dep{j:04d}', subject_id='user_1', learned_at=DAY, recorded_at=DAY, created_by='synthetic',
        dependent_ref=ObjectRef(object_id=f'node{j:04d}', revision=1),
        dependency_ref=ObjectRef(object_id=f'node{j+1:04d}', revision=1), dependency_type='synthetic')
        for j in range(n-1)]
    assert find_dependency_cycle(edges) is None
    commit(s, [*objects, *edges], 'long-dag')
    cycle_edge = edges[0].model_copy(update={'object_id': 'cycle',
        'dependent_ref': ObjectRef(object_id=f'node{n-1:04d}', revision=1),
        'dependency_ref': ObjectRef(object_id='node0000', revision=1)})
    cycle = find_dependency_cycle([*edges, cycle_edge])
    assert len(cycle) == n + 1 and cycle[0] == cycle[-1]
    with pytest.raises(StoreError):
        commit(s, [cycle_edge], 'cycle')
    assert s.current_world_revision() == 1


def test_a01_invalidation_commit_failure_leaves_every_revision_intact(tmp_path):
    s, i, claim, exp = grounded_experience(tmp_path)
    registry = CognitivePolicyRegistry(store=s, index=i)
    policy = new_policy(registry, ObjectRef(object_id=exp.experience_id, revision=1))
    before = s.current_world_revision()
    # SQLite aborts while inserting the planned stale Policy; earlier inserts
    # in the SAME transaction must not become durable.
    with sqlite3.connect(s.db_path) as conn:
        conn.execute(f"""CREATE TRIGGER synthetic_fail BEFORE INSERT ON object_revisions
            WHEN NEW.object_id='{policy.object_id}' AND NEW.revision=2
            BEGIN SELECT RAISE(ABORT, 'synthetic fault'); END""")
    with pytest.raises(StoreError):
        revise(s, i, claim)
    assert s.current_world_revision() == before
    for oid in (claim.claim_id, exp.experience_id, policy.object_id):
        assert s.get_payload(oid)['revision'] == 1


def test_a04_policy_validation_and_commit_share_cas(tmp_path, monkeypatch):
    s, i, _, _ = grounded_experience(tmp_path)
    registry = CognitivePolicyRegistry(store=s, index=i)
    validate = registry._validate_refs
    def racing(refs, **kwargs):
        validate(refs, **kwargs)
        commit(s, [obs('race', 'SYNTHETIC concurrent change')], 'race')
    monkeypatch.setattr(registry, '_validate_refs', racing)
    with pytest.raises(StoreError) as error:
        new_policy(registry, ObjectRef(object_id='old', revision=1))
    assert error.value.code == ErrorCode.VERSION_CONFLICT
    assert registry.latest('communication.response_style') is None


@pytest.mark.parametrize('policy_class', [PolicyClass.HARD_BOUNDARY, PolicyClass.ENGINEERING_PARAMETER])
def test_a04_invalidated_hard_limits_fail_closed_in_access_and_cockpit(tmp_path, policy_class):
    s, i = world(tmp_path)
    runtime = FusedTurnRuntime(store=s, index=i, model_handler=lambda _: ModelDirective(silence=True))
    receipt = runtime.policies.register(CognitivePolicyCreateRequest(
        policy_id='synthetic.limit', scope='user', policy_class=policy_class,
        default_value=False, current_value=False, mutable_by_ai=False, reason='SYNTHETIC',
        changed_by='operator', evaluation_window='24h'), changed_at=NOW)
    from aios_core.contracts.models import CognitivePolicy
    stale = CognitivePolicy.model_validate(s.get_payload(receipt.object_id)).model_copy(update={
        'revision': 2, 'version': 2, 'previous_version': 1, 'rollback_pointer': 1,
        'status': 'stale_review_required'})
    commit(s, [stale], 'stale-limit')
    with pytest.raises(PermissionError):
        runtime.policies.effective_value('synthetic.limit', True)
    with pytest.raises(PermissionError):
        runtime._cognitive_policy_context()


def test_a05_index_failure_does_not_publish_partial_watermark(tmp_path, monkeypatch):
    s, i = world(tmp_path)
    commit(s, [obs('a', 'one'), obs('b', 'two')], 'seed')
    original = i._index_row
    def failing(conn, row):
        original(conn, row)
        if row['object_id'] == 'b':
            raise RuntimeError('SYNTHETIC indexing fault')
    monkeypatch.setattr(i, '_index_row', failing)
    with pytest.raises(RuntimeError, match='indexing fault'):
        i.catch_up(max_rows=1)
    assert i.watermark() == 0
    with sqlite3.connect(i.db_path) as conn:
        assert conn.execute('select count(*) from search_occurred').fetchone()[0] == 0
    monkeypatch.setattr(i, '_index_row', original)
    assert i.catch_up(max_rows=1) == 2


def test_a06_default_summary_scope_is_still_owner_only(tmp_path):
    s, i = world(tmp_path)
    commit(s, [obs('user', 'one'), obs('self', 'two', 'ai_agent_self'),
               obs('other', 'three', 'user_2')], 'seed')
    prepared = prepare(DimensionSummaryService(store=s, index=i))
    assert {x.object_id for x in prepared.sources} == {'user'}


def test_a07_summary_new_source_after_prepare_cannot_publish_incomplete_current(tmp_path):
    s, i = world(tmp_path)
    commit(s, [obs('a', 'one')], 'seed')
    service = DimensionSummaryService(store=s, index=i)
    request = prepare(service)
    commit(s, [obs('b', 'late arrival')], 'late')
    before = s.current_world_revision()
    with pytest.raises(ValueError, match='window changed'):
        service.commit(request, content='SYNTHETIC missing late fact', generated_at=NOW)
    assert s.current_world_revision() == before


def test_a07_summary_validation_and_commit_share_cas(tmp_path, monkeypatch):
    s, i = world(tmp_path)
    commit(s, [obs('a', 'one')], 'seed')
    service = DimensionSummaryService(store=s, index=i)
    request = prepare(service)
    validate = service._validate_sources
    def racing(prepared):
        validate(prepared)
        commit(s, [obs('b', 'late arrival')], 'late')
    monkeypatch.setattr(service, '_validate_sources', racing)
    with pytest.raises(StoreError) as error:
        service.commit(request, content='SYNTHETIC race', generated_at=NOW)
    assert error.value.code == ErrorCode.VERSION_CONFLICT
    assert not s.list_payloads(object_type=ObjectType.SUMMARY)


def test_a07_saturated_filtered_scan_is_not_certified_complete(tmp_path):
    s, i = world(tmp_path)
    commit(s, [obs('a', 'one')], 'seed')
    service = DimensionSummaryService(store=s, index=i, max_source_objects=1)
    receipt = service.commit(prepare(service), content='SYNTHETIC', generated_at=NOW)
    from aios_core.contracts.models import Summary
    base = Summary.model_validate(s.get_payload(receipt.object_id))
    # 72 is the scan cap for max_source_objects=1. Same-scale summaries are
    # deliberately filtered out, but a full scan cannot prove nothing lies beyond it.
    commit(s, [base.model_copy(update={'object_id': f'filtered{x}'}) for x in range(80)], 'filtered')
    prepared = prepare(service)
    assert prepared.truncated
    with pytest.raises(ValueError, match='truncated'):
        service.commit(prepared, content='SYNTHETIC incomplete', generated_at=NOW)


def test_a09_assistant_write_crash_blocks_retry_without_second_model_call(tmp_path, monkeypatch):
    s, i = world(tmp_path)
    calls = []
    def model(_):
        calls.append(1)
        return ModelDirective(response='SYNTHETIC')
    runtime = FusedTurnRuntime(store=s, index=i, model_handler=model)
    def failing(**kwargs):
        raise RuntimeError('SYNTHETIC assistant write failure')
    monkeypatch.setattr(runtime.ingestor, 'commit_assistant_output', failing)
    with pytest.raises(RuntimeError, match='assistant write failure'):
        runtime.run_turn(**turn_args())
    with pytest.raises(TurnExecutionInDoubt):
        FusedTurnRuntime(store=s, index=i, model_handler=model).run_turn(**turn_args())
    assert len(calls) == 1


def test_a10_cycle_detector_does_not_collapse_exact_versions():
    a = Dependency(object_id='a', subject_id='user_1', learned_at=DAY, recorded_at=DAY,
        created_by='SYNTHETIC', dependent_ref=ObjectRef(object_id='x', revision=2),
        dependency_ref=ObjectRef(object_id='y', revision=1), dependency_type='synthetic')
    b = a.model_copy(update={'object_id': 'b', 'dependent_ref': ObjectRef(object_id='y', revision=1),
                            'dependency_ref': ObjectRef(object_id='x', revision=1)})
    assert find_dependency_cycle([a, b]) is None


@pytest.mark.parametrize('service_type', ['claim', 'event'])
def test_a01_a03_invalidation_plan_and_root_commit_share_cas(tmp_path, monkeypatch, service_type):
    import importlib
    module = importlib.import_module(f'aios_core.{"revision" if service_type == "claim" else "events"}.service')
    s, i, claim, _ = grounded_experience(tmp_path)
    if service_type == 'event':
        service = EventDimensionService(store=s, index=i)
        event = service.form_event(EventWriteRequest(title='SYNTHETIC', interpretation='initial',
            event_time=TemporalExtent.point(DAY), evidence_refs=(ObjectRef(object_id='old', revision=1),),
            confidence=.8), learned_at=DAY)
    original = module.plan_invalidation
    def racing(*args, **kwargs):
        plan = original(*args, **kwargs)
        commit(s, [obs('race', 'SYNTHETIC concurrent change')], 'race')
        return plan
    monkeypatch.setattr(module, 'plan_invalidation', racing)
    with pytest.raises(StoreError) as error:
        if service_type == 'claim':
            revise(s, i, claim)
        else:
            service.transition(EventTransitionRequest(event_ref=ObjectRef(object_id=event.event_id, revision=1),
                new_status=EventStatus.REJECTED, reason='SYNTHETIC rejection',
                evidence_refs=(ObjectRef(object_id='correction', revision=1),)), changed_at=NOW)
    assert error.value.code == ErrorCode.VERSION_CONFLICT
    target = claim.claim_id if service_type == 'claim' else event.event_id
    assert s.get_payload(target)['revision'] == 1


@pytest.mark.parametrize('tampering', ['type', 'subject', 'text', 'metadata', 'omitted', 'unbound', 'false_cut'])
def test_a07_untrusted_prepared_input_cannot_forge_provenance(tmp_path, tampering):
    s, i = world(tmp_path)
    commit(s, [obs('a', 'one'), obs('b', 'other', 'user_2')], 'seed')
    service = DimensionSummaryService(store=s, index=i)
    request = prepare(service)
    source = request.sources[0]
    if tampering == 'unbound':
        request = request.model_copy(update={'subject_id': ''})
    elif tampering == 'false_cut':
        request = request.model_copy(update={'source_world_revision': 0})
    elif tampering == 'omitted':
        request = request.model_copy(update={'sources': ()})
    else:
        updates = {'type': {'object_type': 'claim'}, 'subject': {'object_id': 'b'},
                   'text': {'text': 'forged'}, 'metadata': {'metadata': {'dimension': 'forged'}}}
        request = request.model_copy(update={'sources': (source.model_copy(update=updates[tampering]),)})
    with pytest.raises((ValueError, StoreError)):
        service.commit(request, content='SYNTHETIC forged', generated_at=NOW)
    assert not s.list_payloads(object_type=ObjectType.SUMMARY)


def test_a07_resolved_event_remains_eligible_summary_material(tmp_path):
    s, i = world(tmp_path)
    commit(s, [obs('a', 'one')], 'seed')
    events = EventDimensionService(store=s, index=i)
    ev = events.form_event(EventWriteRequest(title='SYNTHETIC', interpretation='initial',
        event_time=TemporalExtent.point(DAY), evidence_refs=(ObjectRef(object_id='a', revision=1),),
        confidence=.8), learned_at=DAY)
    # Build a valid resolved historical event; unlike rejected/stale it is still
    # descriptive source material in the current World projection.
    from aios_core.contracts.models import EventAnchor
    resolved = EventAnchor.model_validate(s.get_payload(ev.event_id)).model_copy(update={
        'revision': 2, 'status': 'resolved', 'event_status': EventStatus.RESOLVED})
    commit(s, [resolved], 'resolved')
    service = DimensionSummaryService(store=s, index=i)
    request = service.prepare(dimension='dim:events', granularity='day', window_start=DAY,
                              window_end=NOW-timedelta(microseconds=1))
    assert ev.event_id in {x.object_id for x in request.sources}
    result = service.commit(request, content='SYNTHETIC resolved event', generated_at=NOW)
    assert s.get_payload(result.object_id)['summary_status'] == 'current'
