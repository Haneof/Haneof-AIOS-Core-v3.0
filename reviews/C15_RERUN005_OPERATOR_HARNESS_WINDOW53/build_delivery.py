"""Operator-only deterministic artifact and mechanical packet supplement."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import shlex
import tarfile

REPO=Path(__file__).resolve().parents[2]
BASE=REPO/'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005'
HARN=BASE/'harness'
ART=BASE/'artifacts/resident-harness.tar.gz'
FILES=sorted([*HARN.rglob('*.py'),HARN/'IDENTITY.json'])
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w',format=tarfile.USTAR_FORMAT) as tar:
    for p in FILES:
        raw=p.read_bytes();info=tarfile.TarInfo('harness/'+str(p.relative_to(HARN)))
        info.size=len(raw);info.mode=0o644;info.mtime=0;info.uid=info.gid=0
        tar.addfile(info,io.BytesIO(raw))
ART.parent.mkdir(exist_ok=True)
ART.write_bytes(gzip.compress(buf.getvalue(),mtime=0))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
members=['harness/'+str(p.relative_to(HARN)) for p in FILES]
identity=json.loads((HARN/'IDENTITY.json').read_bytes())
pin=sha(HARN/'IDENTITY.json')
python='/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python'
entry=f'{python} -I "$HARNESS/launch.py" --source-repo "$SOURCE_REPO" --identity-sha256 {pin}'
# Hash before listing. Closed regular-file set, unique names, fresh destination.
materializer='''import hashlib,json,pathlib,sys,tarfile
a=pathlib.Path(sys.argv[1]);target=pathlib.Path(sys.argv[2]);expected=sys.argv[3];names=json.loads(sys.argv[4])
assert hashlib.sha256(a.read_bytes()).hexdigest()==expected,'artifact substitution'
assert not target.exists(),'materialization destination must be absent'
with tarfile.open(a,'r:gz') as t:
 members=t.getmembers()
 assert sorted(m.name for m in members)==sorted(names),'closed member set mismatch'
 assert len({m.name for m in members})==len(members),'duplicate archive member'
 assert all(m.isfile() and not pathlib.PurePosixPath(m.name).is_absolute() and '..' not in pathlib.PurePosixPath(m.name).parts for m in members),'unsafe member'
 target.mkdir(parents=True)
 for m in members:
  p=target/m.name;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(t.extractfile(m).read())
print('HARNESS_MATERIALIZATION_PASS')'''
materialize=f'{python} -I -c {shlex.quote(materializer)} "$ARTIFACT" "$DELIVERY_DIR" {sha(ART)} {shlex.quote(json.dumps(members))}'
packet_path=BASE/'RESIDENT_SAFE_LAUNCH_PACKET.json'
packet=json.loads(packet_path.read_bytes())
for key in ('accepted_operator_candidate','accepted_operator_tree','c15_tests_tree','habitation_tree',
            'fixture_binding','post_merge_main_gate','terminal_state'):
    packet.pop(key,None)
packet['packet_version']='c15-rcc-res-a-rerun-005-launch-v2-candidate'
packet['start_preconditions']=[
    'Fresh independent acceptance and PM launch authorization are required before actual Resident execution',
    'Verify the exact approved portable runtime and this packet-pinned harness identity',
    'Verify Core/C15 file hashes and module paths through the pinned isolated verify entry',
    'Preserve the existing cursor-zero fresh state; initialization only applies to a genuinely absent run root',
    'Remote persistence origin and canonical run ref are available; uncertain state is a startup blocker']
packet['runner_invocation']=entry+' run --root "$RUN_ROOT" --run-id "$RUN_ID" --session-id "$SESSION_ID" --operation "$OPERATION_JSON" --persistence-repo "$PERSISTENCE_REPO"'
packet['publisher_invocation']=entry+' publish --exchange "$EXCHANGE" --request-id "$REQUEST_ID" --response "$RESPONSE_JSON" --persistence-repo "$PERSISTENCE_REPO" --timeout 60'
packet['runtime_module_identity']={'core_tree':identity['core_tree'],'c15_tree':identity['c15_tree'],
    'manifest':'harness/IDENTITY.json','manifest_sha256':pin,
    'module_verification':entry+' verify','isolation':'Python -I, explicit package roots, fresh bytecode-cache prefix, no bytecode writes'}
packet['semantic_router_disabled_verification']={'command':entry+' verify',
    'expected_pass_marker':'HARNESS_IDENTITY_AND_ROUTER_PASS',
    'runtime_report':'mailbox/operations/<operation-sha256>/runtime-handler-identity.json',
    'missing_response_behavior':'wait bounded by operation timeout; fail closed; never generate a response'}
packet['current_main_harness_identity']={'approval_state':'PENDING_FRESH_INDEPENDENT_ACCEPTANCE_AND_PM',
    'identity_sha256':pin,'runner':{'entry':'launch.py run','files':{k:v for k,v in identity['harness_files'].items() if k in ('launch.py','r005/cli.py','r005/safe_runner.py')}},
    'publisher':{'entry':'launch.py publish','service':'launch.py service (Runner-owned subprocess only)',
        'files':{k:v for k,v in identity['harness_files'].items() if k in ('launch.py','r005/cli.py','r005/safe_runner.py','r005/publisher_service.py','r005/payload.py')}},
    'all_harness_files':identity['harness_files']}
packet['cross_sandbox_harness_materialization']={'artifact_repository_path':str(ART.relative_to(REPO)),
    'artifact_sha256':sha(ART),'artifact_size':ART.stat().st_size,'closed_members':members,
    'transport':'Operator transfers exact tar bytes from the independently accepted and PM-authorized candidate Git commit, or attaches those same bytes. Resident receives only the safe artifact and packet.',
    'operator_git_export':'git show "$APPROVED_HARNESS_HEAD:'+str(ART.relative_to(REPO))+'" > "$ARTIFACT"',
    'materialization_command':materialize,'destination':'fresh $DELIVERY_DIR; set HARNESS=$DELIVERY_DIR/harness after PASS',
    'post_materialization_command':entry+' verify','resident_may_edit_harness':False}
packet['run_state_binding']={'variables':{
    'SOURCE_REPO':'local checkout whose Core/C15 exact bytes pass pinned verification',
    'PERSISTENCE_REPO':'local Git checkout with approved writable origin for canonical persistence/run-id ref',
    'RUN_ROOT':'absolute private durable root under /home/user; existing Window 51 state must not be replaced',
    'RUN_ID':'fresh approved run identity','SESSION_ID':'fresh approved Resident session identity',
    'EXCHANGE':'RUN_ROOT/mailbox/operations/SHA256(canonical operation JSON)',
    'OPERATION_JSON':'mechanical operation file bound to the currently released event only'},
    'environment':'export C15_PERSISTED_WORKSPACE=/home/user',
    'world':'RUN_ROOT/state/runtime/world.sqlite','index':'RUN_ROOT/state/runtime/index.sqlite',
    'release_state':'RUN_ROOT/state/runtime/release_state.json',
    'init_only_when_absent':entry+' init --root "$RUN_ROOT" --run-id "$RUN_ID" --session-id "$SESSION_ID" --subject-id "$SUBJECT_ID" --persistence-repo "$PERSISTENCE_REPO"',
    'checkpoint_after_approved_mechanical_ingest':entry+' checkpoint --root "$RUN_ROOT" --run-id "$RUN_ID" --session-id "$SESSION_ID" --persistence-repo "$PERSISTENCE_REPO"',
    'operation_exact_keys':['mode','at','cursor','event_id','turn_index','user_input','timeout'],
    'operation_field_rules':{'mode':'user for current legal USER turn; due for current legal due work',
        'at':'ISO timestamp with timezone from current event','cursor':'current permitted released cursor',
        'event_id':'current released event identity','turn_index':'current legal USER turn index',
        'user_input':'current released USER bytes; empty for due entry','timeout':'positive external-response wait seconds; choose enough for live Resident and bounded failure'},
    'existing_binding_incompatible':'BLOCKED; do not migrate, overwrite, or start real Resident'}
packet['resident_response_handoff']={
    'read_command':entry+' read-request --exchange "$EXCHANGE" --request-id "$REQUEST_ID"',
    'authorization':'Runner emits RESIDENT_PUBLISH_AUTHORIZATION once to the external session terminal/pipe. Keep it in that session; never save it to a file, argv, environment, run state or logs. Publisher reads exactly one authorization line from stdin. Core never receives it.',
    'response_schema':{'required_exact_envelope_keys':['response_version','request_id','request_sha256','authored_by','directive'],
        'response_version':1,'request_id':'exact published request id','request_sha256':'exact published request digest',
        'authored_by':'EXTERNAL_CURRENT_RESIDENT_SESSION',
        'model_directive':'Resident chooses capability_calls OR response OR silence under the request Core schema; echo body.provenance_binding exactly as directive.provenance; optional actual usage only',
        'summary_directive':'exact object containing text, a nonempty Summary authored by Resident'},
    'publication':'Resident authors RESPONSE_JSON from legal request/snapshot. Publisher validates and durably commits the exact file bytes; it does not choose or repair a decision.',
    'trust':'Envelope integrity and authorization are separate from Core authenticity. Background returns require external process RSA proof verified by the pre-bound Core verifier and a Core trusted-return receipt before application.',
    'publisher_success':'exact response and proof included in remote durable Git commit; Runner may still fail during later semantic application'}
packet['recovery_failure_behavior']={
    'completed_operation':'identical operation returns durable recorded result; no new Core execution',
    'committed_response':'exact-byte replay verifies signed bytes against recorded immutable remote commit; conflict rejected',
    'interrupted_or_uncertain_operation':'BLOCKED; preserve exact state; no automatic redispatch, new request, invented directive or fallback',
    'reattach_exact_remote_head':entry+' reattach --root "$EMPTY_RECOVERY_ROOT" --run-id "$RUN_ID" --session-id "$SESSION_ID" --commit-sha "$REMOTE_HEAD" --persistence-repo "$PERSISTENCE_REPO"',
    'reattach_policy':'materializes authoritative prefix only; does not authorize replay or semantic recovery of an interrupted operation',
    'startup_fail_closed':['missing artifact/runtime/manifest','hash or import drift','semantic adapter reintroduction',
        'owner/run/session mismatch','remote CAS or durability failure','unresolved operation','missing/tampered/stale/conflicting response',
        'external authorization or Core proof unavailable','Summary failure']}
packet['mechanical_verification']={'approved_command_source':'this mechanical candidate packet after independent acceptance and PM authorization',
    'steps':['Verify approved runtime','Materialize exact harness artifact to an absent destination',
        'Run pinned isolated verify command','Check approved fresh run binding and remote persistence authority'],
    'success_marker':'HARNESS_IDENTITY_AND_ROUTER_PASS'}
packet_path.write_text(json.dumps(packet,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
(ART.parent/'resident-harness.tar.gz.sha256').write_text(sha(ART)+'  resident-harness.tar.gz\n')
print(json.dumps({'artifact_sha256':sha(ART),'identity_sha256':pin,'packet_sha256':sha(packet_path)}))
