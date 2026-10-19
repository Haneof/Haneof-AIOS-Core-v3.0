"""Deterministic closed delivery for Window66 TEST_ONLY signed response candidate.

Never scans arbitrary globbed Python sources into a new identity. The existing
closed manifest is the source of truth and launcher scanner verifies it first.
"""
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = Path(__file__).resolve().parent
BASE = REPO/'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005'
HARN = BASE/'harness'
ART = BASE/'artifacts/resident-harness.tar.gz'
sha = lambda data: hashlib.sha256(data).hexdigest()

def build():
    manifest_bytes = (HARN/'IDENTITY.json').read_bytes()
    pin = sha(manifest_bytes)
    manifest = json.loads(manifest_bytes)
    spec = importlib.util.spec_from_file_location('delivery_identity_scan', HARN/'launch.py')
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    state = launcher.scan_identity(HARN, REPO, pin)
    assert all(entry['mode'] == 0o644 for name,entry in state['snapshots'].items()
               if name == 'IDENTITY.json' or name in manifest['harness_files'])
    files = {'harness/'+name: entry['bytes'] for name,entry in state['snapshots'].items()
             if name == 'IDENTITY.json' or name in manifest['harness_files']}
    inventory = {name: {'sha256': sha(data), 'size': len(data), 'mode': 0o644}
                 for name,data in sorted(files.items())}
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name,data in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.mode = 0o644
            member.uid = member.gid = member.mtime = 0
            archive.addfile(member, io.BytesIO(data))
    compressed = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', compresslevel=9, mtime=0, fileobj=compressed) as stream:
        stream.write(buffer.getvalue())
    raw = compressed.getvalue()
    ART.parent.mkdir(exist_ok=True)
    ART.write_bytes(raw)
    (ART.parent/'resident-harness.tar.gz.sha256').write_text(sha(raw)+'  resident-harness.tar.gz\n')
    (ART.parent/'MEMBERS.json').write_text(json.dumps(inventory,sort_keys=True,indent=2)+'\n')
    python = '/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python'
    entry = f'{python} -I "$HARNESS/launch.py" --source-repo "$SOURCE_REPO" --identity-sha256 {pin}'
    script = (EVIDENCE/'materialize.py').read_text()
    materializer = f'{python} -I -c {shlex.quote(script)} "$ARTIFACT" "$DELIVERY_DIR" {sha(raw)} {shlex.quote(json.dumps(inventory,sort_keys=True,separators=(",",":")))}'
    # Build a minimal clean-room packet; never copy governance, fixture bindings,
    # prior reviews, release tool paths or semantic test inputs into it.
    packet = {
        'packet_version': 'c15-rcc-res-a-rerun-005-launch-v3-candidate',
        'task': 'C15-RCC-RES-A-RERUN-005',
        'role': 'Real Resident AI — Fresh Resident A',
        'access_class': 'RESIDENT_VISIBLE/CLEAN_ROOM',
        'phase': 'A', 'allowed_cursor_start': 1, 'allowed_cursor_end': 13,
        'stop_after_ack_cursor': 13, 'forbidden_next_cursor': 14,
        'startup_inputs': {
            'clean_room_contract': {'path': 'reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_CORRECTIVE_003_CLEAN_ROOM_CONTRACT.md',
                'git_blob': '430a75e0a20b0256672eb430617ae5a1d14c142f'},
            'run_contract': {'path': 'reviews/internal_habitation/c15-rcc/v1/resident/RESIDENT_A_RUN_CONTRACT.md',
                'git_blob': '1b45ca7fa441855d927b610ca2a93ef50b5eee66'}},
        'fresh_identity_requirements': ['fresh private World', 'fresh WorldSearchIndex',
            'fresh release-state', 'fresh runtime/checkpoint', 'fresh exchange ledger and request/response directories',
            'fresh Resident process identity', 'fresh Resident session identity', 'fresh run identity'],
        'approval_state': 'PENDING_INDEPENDENT_ACCEPTANCE_AND_PM_AUTHORIZATION',
        'real_resident_use_authorized': False,
        'start_preconditions': ['Independent acceptance and PM launch authorization required',
            'Qualified Linux x86_64 with AF_UNIX SO_PEERCRED, pidfd and real /proc process identity',
            'Approved runtime and closed source identity verified',
            'Current event legally released by external Operator; existing state preserved',
            'Writable authoritative persistence origin and canonical run ref'],
        'approved_runtime': {'prepared_venv_python': python, 'expected_python': '3.12.14',
            'expected_pydantic': '2.13.5', 'expected_pytest': '8.4.2',
            'expected_sqlite': '3.45.1', 'expected_openssl': '3.0.13',
            'python_sha256': manifest['python_sha256'],
            'runtime_tar_sha256': 'ecfe4b4b6e9dee1a08342974e816f739dcd77fcd3f25f3ad7626cc7102e5673e',
            'build_or_install_authorized': False},
        'current_main_harness_identity': {'approval_state': 'PENDING_INDEPENDENT_ACCEPTANCE_AND_PM',
            'identity_sha256': pin, 'all_harness_files': manifest['harness_files'],
            'core_tree': manifest['core_tree'], 'c15_tree': manifest['c15_tree'],
            'provenance': 'IDENTITY metadata describes source ancestry; exact executable bytes are pinned'},
        'runtime_module_identity': {'manifest': 'harness/IDENTITY.json', 'manifest_sha256': pin,
            'module_verification': entry+' verify',
            'isolation': 'Python -I and closed verified in-memory source importer'},
        'semantic_router_disabled_verification': {'command': entry+' verify',
            'expected_pass_marker': 'HARNESS_IDENTITY_AND_ROUTER_PASS'},
        'cross_sandbox_harness_materialization': {'artifact_repository_path': str(ART.relative_to(REPO)),
            'artifact_sha256': sha(raw), 'artifact_size': len(raw), 'closed_members': sorted(files),
            'member_identity': inventory, 'materialization_command': materializer,
            'post_materialization_command': entry+' verify',
            'destination': 'absolute absent $DELIVERY_DIR; existing parent required; no symlinks in parent path',
            'repeat_policy': 'FAIL_CLOSED for every existing destination, including empty directory or dangling symlink',
            'partial_failure_policy': 'Preserve blocked partial target; choose a new destination after Operator inspection',
            'transport': 'Exact candidate tar bytes and safe packet only after independent acceptance and PM authorization',
            'resident_may_edit_harness': False},
        'runner_invocation': entry+' run --root "$RUN_ROOT" --run-id "$RUN_ID" --session-id "$SESSION_ID" --operation "$OPERATION_JSON" --persistence-repo "$PERSISTENCE_REPO"',
        'publisher_invocation': entry+' publish --exchange "$EXCHANGE" --request-id "$REQUEST_ID" --response "$RESPONSE_JSON" --persistence-repo "$PERSISTENCE_REPO" --timeout 60',
        'run_state_binding': {'variables': {'HARNESS': '$DELIVERY_DIR/harness',
            'SOURCE_REPO': 'Independent local source checkout whose exact Core/C15 bytes and modes pass verify',
            'RUN_ROOT': 'Private durable run directory; preserve all existing state',
            'PERSISTENCE_REPO': 'Approved Git checkout with authoritative writable origin',
            'RUN_ID': 'Externally authorized run identity', 'SESSION_ID': 'Externally authorized session identity',
            'EXCHANGE': 'Current operation exchange directory', 'OPERATION_JSON': 'Current legally released mechanical operation'},
            'environment': 'export C15_PERSISTED_WORKSPACE=/home/user',
            'operation_exact_keys': ['mode','at','cursor','event_id','turn_index','user_input','timeout'],
            'operation_field_rules': {'mode': 'user for a legal USER turn; due for legal due work',
                'at': 'current released event ISO timestamp with timezone', 'cursor': 'current legally released cursor only',
                'event_id': 'current released event identity', 'turn_index': 'current legal USER turn index',
                'user_input': 'current released USER bytes; empty for due work',
                'timeout': 'positive external response wait seconds; bounded failure'},
            'init_only_when_absent': entry+' init --root "$RUN_ROOT" --run-id "$RUN_ID" --session-id "$SESSION_ID" --subject-id "$SUBJECT_ID" --persistence-repo "$PERSISTENCE_REPO"',
            'checkpoint_after_approved_mechanical_ingest': entry+' checkpoint --root "$RUN_ROOT" --run-id "$RUN_ID" --session-id "$SESSION_ID" --persistence-repo "$PERSISTENCE_REPO"'},
        'resident_response_handoff': {'read_command': entry+' read-request --exchange "$EXCHANGE" --request-id "$REQUEST_ID"',
            'authorization': 'Publisher discloses a separate one-request capability on a validated controlling TTY. Never redirect, persist, log, or expose it to Core/recovery. Publisher CLI reads token only from stdin. Bind token to matching REQUEST_ID and OPERATION_ID.',
            'response_schema': {'required_exact_envelope_keys': ['response_version','request_id','request_sha256','authored_by','directive'],
                'response_version': 1, 'authored_by': 'EXTERNAL_CURRENT_RESIDENT_SESSION',
                'model_directive': 'Resident decides from legal RuntimeSnapshot; echo exact provenance_binding as directive.provenance',
                'summary_directive': 'Resident-authored object with text'},
            'publisher_success': 'Exact response and proof in verified authoritative remote commit; later Core application may still fail'},
        'recovery_failure_behavior': {'completed_operation': 'Replay only after exact authoritative remote completion verification',
            'interrupted_or_uncertain_operation': 'BLOCKED; preserve state; no automatic redispatch, fallback or invented response',
            'reattach_exact_remote_head': entry+' reattach --root "$EMPTY_RECOVERY_ROOT" --run-id "$RUN_ID" --session-id "$SESSION_ID" --commit-sha "$REMOTE_HEAD" --persistence-repo "$PERSISTENCE_REPO"'},
        'clean_room_policy': ['Current legally released input and request/snapshot only',
            'No governance, prior reviews, test answers, sealed events, fixture/evaluator/release source or Git history'],
        'self_acceptance': False,
    }
    packet.update(packet_version='c15-r005-window66-test-signed-candidate', role='ISOLATED_TEST_ONLY_RESIDENT', access_class='TEST_ONLY/MECHANICAL', phase='TEST_ONLY', allowed_cursor_start=1, allowed_cursor_end=13, stop_after_ack_cursor=13, forbidden_next_cursor=14, startup_inputs={}, approval_state='PM_RESPONSE_SCOPE_APPROVED_TEST_ONLY;INDEPENDENT_ACCEPTANCE_NOT_STARTED', real_resident_use_authorized=False)
    packet['start_preconditions']=['Window65 isolation and existing Operator root reverified', 'Separate short-lived Operator-signed response enrollment for each exact test run/session/instance/operation', 'No real Resident or sealed cursor is authorized', 'Qualified Linux with the unchanged Runner registration identity controls', 'Exact approved runtime and closed executable manifest']
    packet['cross_sandbox_harness_materialization']['transport']='Exact TEST_ONLY candidate artifact and this packet; never transmit private keys or reusable credentials'
    packet['resident_response_handoff']['authorization']='TEST_ONLY Ed25519 signature on canonical aios.r005.test.response.v1 envelope; protected independent AF_UNIX channel. No controlling TTY or stdout token in signed mode. Original legacy TTY path remains separate.'
    packet['signed_test_response']={'purpose':'aios.r005.test.response.sign.v1','enrollment_env':'AIOS66_TEST_ENROLLMENT: absolute protected Operator-issued JSON path','issuer_fingerprint':'1124f54a497c9dfa5fcc6e16fb9fc570816fadba6f32016a8b53d5f0243090dd','resident_fingerprint':'838a1a7d168ac6dd8441c0c8a2deab439a7b775d6583c40618a51f627e6e3b7f','runner_uid':999,'resident_uid':996,'response_channel':'Root-provisioned /run/aios-w66-responses/<enrollment-id>/<fresh-publisher-epoch>.sock; peer UID996/GID983 only','framing':'Bounded canonical JSON followed by newline and shutdown(SHUT_WR)','commands':['pending','publish-signed'],'publish_exact_keys':['command','envelope','signature','raw'],'signature_encoding':'Ed25519 signature hex; raw response base64','envelope':'Publisher-issued exact current envelope plus response_sha256. Canonical UTF-8 sorted-key compact JSON, ensure_ascii=False, allow_nan=False. Every issued binding must be retained.','ttl':'Challenge at most 120 seconds and never beyond enrollment expiry','scope_mapping':{'USER':['model_directive'],'DUE':['model_directive'],'SUMMARY':['model_directive','round_summary','dimension_summary'],'DELIVERED':['model_directive: materialized delivery case; no extra acknowledgement signing scope']},'retirement':'Consumed response cannot authorize different bytes. Fresh Publisher epoch invalidates prior rounds. Interrupted operation blocks redispatch; stale filesystem socket may remain but is not a live service.','private_key':'Held only by existing UID996 protected account; no key is contained in this packet','evidence_scope':'Mechanical local isolated Git authority only; formal and independent validation pending'}
    packet['cursor_range_status']='FUTURE_CONTRACT_METADATA_ONLY;NO_REAL_CURSOR_RELEASE_AUTHORIZED'
    packet['legacy_publisher_invocation']=packet.pop('publisher_invocation')
    packet['publisher_invocation']='UID996 signed-response AF_UNIX protocol described in signed_test_response; do not invoke legacy token publish for signed mode'
    packet['run_state_binding']['variables']['OPERATION_JSON']='Exact synthetic TEST_ONLY operation covered by current Operator enrollment; no real cursor release'
    packet_bytes = (json.dumps(packet,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    (BASE/'RESIDENT_SAFE_LAUNCH_PACKET.json').write_bytes(packet_bytes)
    receipt = {'source_head_at_build': subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
               'harness_manifest_sha256': pin, 'artifact_sha256': sha(raw),
               'packet_sha256': sha(packet_bytes), 'member_count': len(files),
               'harness_python_files': len(manifest['harness_files']),
               'core_python_files': sum(p.startswith('src/') for p in manifest['source_files']),
               'c15_python_files': sum(p.startswith('tools/') for p in manifest['source_files'])}
    (EVIDENCE/'BUILD_RECEIPT.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt,sort_keys=True))

if __name__ == '__main__':
    sys.dont_write_bytecode = True
    build()
