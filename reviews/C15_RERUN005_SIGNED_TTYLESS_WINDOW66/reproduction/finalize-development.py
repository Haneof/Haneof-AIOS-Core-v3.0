"""Finalize Window66 development evidence without editing prior test assertions."""
from pathlib import Path
import os,json,hashlib,subprocess as sp,xml.etree.ElementTree as ET
E=Path('/workspaces/window66-gate0-20261016T1509Z');S=E/'candidate';R=S/'reviews/C15_RERUN005_SIGNED_TTYLESS_WINDOW66'
ns={};exec(compile((E/'mechanical-validation.py').read_text().split('compile(SETUP')[0],'mechanical-helper','exec'),ns)
# Supplement the preserved failed diagnostic: test transport retirement, rather than require removal of the socket inode.
t=Path('/var/lib/aios-window66-negative-remote-r2/remote-reject');g=json.loads(Path('/var/lib/aios-window65/trust/window66-response-final-2020z/user.json').read_bytes())
x=t/'synthetic-root/mailbox/operations'/g['operation_ids'][0];endpoint=json.loads((x/'signed-endpoint.json').read_text())['socket']
code="import socket,sys;s=socket.socket(socket.AF_UNIX);s.settimeout(3);s.connect(sys.argv[1])"
p=ns['spawn'](996,983,[ns['PY'],'-B','-I','-c',code,endpoint],ns['env'](t));out,err=p.communicate(timeout=6)
assert p.returncode!=0 and b'ConnectionRefusedError' in err,err
assert list((x/'proofs').glob('*.json')) and not list((x/'committed').glob('*.json'))
assert json.loads((x/'operation.json').read_bytes())['state']!='completed'
assert b'interrupted operation' in (E/'negative-remote-r2/exact-restart.stderr').read_bytes()
r={'case':'remote_rejection_and_retirement_followup','status':'PASS','detail':{'remote_rejection':True,'publisher_proof_present':True,'completion_ack_count':0,'exact_restart_rejected':True,'retired_endpoint_connect_refused':True,'stale_socket_inode_preserved':True,'original_failure_preserved':'negative-remote-r2/results.json','limitation':'Local isolated bare Git authority. No platform-specific remote fault injection or independent security acceptance.'}}
(E/'remote-retirement-followup.json').write_text(json.dumps(r,indent=2)+chr(10))
suite=ET.Element('testsuite',name='Window66 remote retirement followup',tests='1',failures='0');ET.SubElement(suite,'testcase',name=r['case']);ET.ElementTree(suite).write(E/'remote-retirement-followup.xml',encoding='utf-8',xml_declaration=True)
# Make the new copied builder describe its actual TEST_ONLY signed workflow.
b=R/'build_delivery.py';s=b.read_text().replace('Deterministic closed delivery from unchanged exact Window55 Harness bytes.','Deterministic closed delivery for Window66 TEST_ONLY signed response candidate.')
anchor='    packet_bytes = '
assert s.count(anchor)==1
extra="""    packet.update(packet_version='c15-r005-window66-test-signed-candidate', role='ISOLATED_TEST_ONLY_RESIDENT', access_class='TEST_ONLY/MECHANICAL', phase='TEST_ONLY', allowed_cursor_start=0, allowed_cursor_end=0, stop_after_ack_cursor=0, forbidden_next_cursor=1, startup_inputs={}, approval_state='PM_RESPONSE_SCOPE_APPROVED_TEST_ONLY;INDEPENDENT_ACCEPTANCE_NOT_STARTED', real_resident_use_authorized=False)
    packet['start_preconditions']=['Window65 isolation and existing Operator root reverified', 'Separate short-lived Operator-signed response enrollment for each exact test run/session/instance/operation', 'No real Resident or sealed cursor is authorized', 'Qualified Linux with the unchanged Runner registration identity controls', 'Exact approved runtime and closed executable manifest']
    packet['cross_sandbox_harness_materialization']['transport']='Exact TEST_ONLY candidate artifact and this packet; never transmit private keys or reusable credentials'
    packet['resident_response_handoff']['authorization']='TEST_ONLY Ed25519 signature on canonical aios.r005.test.response.v1 envelope; protected independent AF_UNIX channel. No controlling TTY or stdout token in signed mode. Original legacy TTY path remains separate.'
    packet['signed_test_response']={'purpose':'aios.r005.test.response.sign.v1','enrollment_env':'AIOS66_TEST_ENROLLMENT: absolute protected Operator-issued JSON path','issuer_fingerprint':'1124f54a497c9dfa5fcc6e16fb9fc570816fadba6f32016a8b53d5f0243090dd','resident_fingerprint':'838a1a7d168ac6dd8441c0c8a2deab439a7b775d6583c40618a51f627e6e3b7f','runner_uid':999,'resident_uid':996,'response_channel':'Root-provisioned /run/aios-w66-responses/<enrollment-id>/<fresh-publisher-epoch>.sock; peer UID996/GID983 only','framing':'Bounded canonical JSON followed by newline and shutdown(SHUT_WR)','commands':['pending','publish-signed'],'publish_exact_keys':['command','envelope','signature','raw'],'signature_encoding':'Ed25519 signature hex; raw response base64','envelope':'Publisher-issued exact current envelope plus response_sha256. Canonical UTF-8 sorted-key compact JSON, ensure_ascii=False, allow_nan=False. Every issued binding must be retained.','ttl':'Challenge at most 120 seconds and never beyond enrollment expiry','scope_mapping':{'USER':['model_directive'],'DUE':['model_directive'],'SUMMARY':['model_directive','round_summary','dimension_summary'],'DELIVERED':['model_directive: materialized delivery case; no extra acknowledgement signing scope']},'retirement':'Consumed response cannot authorize different bytes. Fresh Publisher epoch invalidates prior rounds. Interrupted operation blocks redispatch; stale filesystem socket may remain but is not a live service.','private_key':'Held only by existing UID996 protected account; no key is contained in this packet','evidence_scope':'Mechanical local isolated Git authority only; formal and independent validation pending'}
    packet['legacy_publisher_invocation']=packet.pop('publisher_invocation')
    packet['publisher_invocation']='UID996 signed-response AF_UNIX protocol described in signed_test_response; do not invoke legacy token publish for signed mode'
    packet['run_state_binding']['variables']['OPERATION_JSON']='Exact synthetic TEST_ONLY operation covered by current Operator enrollment; no real cursor release'
"""
s=s.replace(anchor,extra+anchor);b.write_text(s)
sp.run([ns['PY'],'-B',str(b)],cwd=S,check=True)
print('REMOTE_RETIREMENT_FOLLOWUP=PASS TEST_ONLY_PACKET_REBUILT=YES')
