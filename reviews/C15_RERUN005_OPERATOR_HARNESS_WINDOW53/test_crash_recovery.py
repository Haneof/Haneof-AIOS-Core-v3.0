import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from test_current_trusted_adapter import setup,entry
from r005.bridge import ExchangeBridge
from r005.canonical import canonical_json_bytes
from tools.c15_persistence.remote_backend import materialize_run_state


def test_sigkill_after_request_never_regenerates_or_redispatches(tmp_path,monkeypatch):
    root,repo=setup(tmp_path,monkeypatch)
    spec={'mode':'user','at':'2026-10-13T00:00:00+00:00','cursor':1,
        'event_id':'synthetic-crash-event','turn_index':1,'user_input':'synthetic pending request','timeout':30}
    path=tmp_path/'operation.json';path.write_bytes(canonical_json_bytes(spec))
    command=entry()+['run','--root',str(root),'--run-id','synthetic-53-run',
        '--session-id','synthetic-53-session','--operation',str(path),'--persistence-repo',str(repo)]
    env=dict(os.environ,C15_PERSISTED_WORKSPACE=str(tmp_path))
    runner=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    line=runner.stdout.readline()
    assert line.startswith('RESIDENT_PUBLISH_AUTHORIZATION='),runner.stderr.read()
    authorization=line.strip().split('=',1)[1]
    ready=[];deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        ready=list((root/'mailbox/operations').glob('*/ready/*.json'))
        if ready:break
        time.sleep(.02)
    assert len(ready)==1
    exchange=ready[0].parent.parent;rid=ready[0].stem
    service=json.loads((exchange/'service.json').read_bytes())
    b=ExchangeBridge(exchange)
    assert b.published_response_record(rid) is None
    runner.kill();runner.wait(timeout=5)
    assert runner.returncode==-signal.SIGKILL
    before=(root/'state/runtime/world.sqlite').read_bytes()
    try:
        replay=subprocess.run(command,env=env,capture_output=True,text=True,timeout=15)
        assert replay.returncode!=0
        assert 'interrupted operation' in replay.stderr
        assert len(list((root/'mailbox/operations').glob('*/requests/*.json')))==1
        assert (root/'state/runtime/world.sqlite').read_bytes()==before
        assert b.published_response_record(rid) is None
        # Materialize the exact authoritative remote prefix into another cache.
        attached=materialize_run_state(run_id='synthetic-53-run',session_id='synthetic-53-session',
            target_dir=tmp_path/'reattached',repo_dir=repo)
        try:
            assert len(list((attached.mailbox_dir/'operations').glob('*/requests/*.json')))==1
            assert (attached.state_dir/'runtime/world.sqlite').read_bytes()==before
        finally:attached.release()
        spec['user_input']='changed spec cannot bypass an unresolved operation';path.write_bytes(canonical_json_bytes(spec))
        changed=subprocess.run(command,env=env,capture_output=True,text=True,timeout=15)
        assert changed.returncode!=0
        assert 'older operation is unresolved' in changed.stderr
    finally:
        try:os.kill(service['pid'],signal.SIGTERM)
        except ProcessLookupError:pass


def test_absent_external_response_bounded_fail_closed(tmp_path,monkeypatch):
    root,repo=setup(tmp_path,monkeypatch)
    spec={'mode':'user','at':'2026-10-13T00:00:00+00:00','cursor':1,
        'event_id':'synthetic-timeout','turn_index':1,'user_input':'synthetic pending','timeout':.2}
    path=tmp_path/'operation.json';path.write_bytes(canonical_json_bytes(spec))
    command=entry()+['run','--root',str(root),'--run-id','synthetic-53-run',
        '--session-id','synthetic-53-session','--operation',str(path),'--persistence-repo',str(repo)]
    env=dict(os.environ,C15_PERSISTED_WORKSPACE=str(tmp_path))
    runner=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    stdout,stderr=runner.communicate(timeout=40)
    assert runner.returncode!=0
    assert 'response wait expired' in stderr
    requests=list((root/'mailbox/operations').glob('*/requests/*.json'))
    assert len(requests)==1
    assert not list((root/'mailbox/operations').glob('*/responses/*.json'))
    marker=list((root/'mailbox/operations').glob('*/operation.json'))[0]
    assert json.loads(marker.read_bytes())['state']!='completed'
    replay=subprocess.run(command,env=env,capture_output=True,text=True,timeout=15)
    assert replay.returncode!=0 and 'interrupted operation' in replay.stderr
    assert len(list((root/'mailbox/operations').glob('*/requests/*.json')))==1
