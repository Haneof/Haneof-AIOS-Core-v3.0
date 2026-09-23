"""Round3 permanent regressions for six findings. Synthetic only, no real B/C, no private A."""
import io
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.c15_preflight.transport import Trace, StreamBridge, TransportError, JournalPoisoned, directive, encode
from tools.c15_preflight.driver import Driver, DriverBlocked
from tools.c15_preflight.freeze import freeze
from tools.c15_preflight.restart import restore_frozen
from tools.c15_preflight.audit import digest
from tools.c15_preflight.isolation_probe import create_canaries, outside_checks, assess, probe

# reuse helpers from existing driver tests
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tests/preflight'))
from test_driver import setup, NOW
from aios_core.ingest.conversation import ConversationIngestor
from aios_core.contracts.refs import ObjectRef
from aios_core.contracts.enums import WakeSource, BudgetScope, BudgetOnExceed
from aios_core.wake import WakeSignalRequest
from aios_core.runtime.cognitive_runtime import ModelDirective
from aios_core.runtime.capabilities import CapabilityCall
from aios_core.contracts.models import BudgetPolicy
from aios_core.contracts.time import TemporalExtent
from aios_core.contracts.enums import SourceClass
from datetime import timedelta, timezone, datetime

# ---- 1 journal I/O failure ----

def test_journal_write_failure_latches_and_blocks(tmp_path):
    trace = Trace(tmp_path / "trace", lambda: 0)
    # inject write failure
    orig_write = trace.file.write
    def failing_write(_):
        raise OSError("synthetic write failure")
    trace.file.write = failing_write
    with pytest.raises(OSError):
        trace.append("first", {})
    assert trace.io_failure is not None and trace.failure is not None
    with pytest.raises(JournalPoisoned):
        trace.append("second", {})
    trace.close()

def test_journal_flush_failure_latches(tmp_path):
    trace = Trace(tmp_path / "trace", lambda: 0)
    trace.file.flush = lambda: (_ for _ in ()).throw(OSError("flush fail"))
    with pytest.raises(OSError):
        trace.append("first", {})
    assert trace.io_failure is not None
    with pytest.raises(JournalPoisoned):
        trace.append("after", {})
    trace.close()

def test_journal_fsync_failure_latches(tmp_path):
    trace = Trace(tmp_path / "trace", lambda: 0)
    with patch("os.fsync", side_effect=OSError("fsync fail")):
        with pytest.raises(OSError):
            trace.append("first", {})
    assert trace.io_failure is not None
    with pytest.raises(JournalPoisoned):
        trace.append("after", {})
    trace.close()

def test_bridge_stops_after_first_request_log_failure_and_retains_file(tmp_path):
    trace = Trace(tmp_path / "trace", lambda: 0)
    # make first model_request append fail via fsync
    with patch("os.fsync", side_effect=OSError("fsync fail")):
        out = io.StringIO()
        class In:
            def readline(self,_): return ""
        bridge = StreamBridge(In(), out, trace)
        with pytest.raises(TransportError):
            bridge._request("runtime", {"a":1}, directive)
    # file retained, not truncated, not repaired
    assert (tmp_path / "trace").exists()
    # second bridge call blocked
    out2 = io.StringIO()
    class In2:
        def readline(self,_): return ""
    bridge2 = StreamBridge(In2(), out2, trace)
    with pytest.raises(TransportError):
        bridge2._request("runtime", {"a":1}, directive)
    trace.close()

# ---- 2 short write handling ----

def test_short_writes_success(tmp_path):
    trace = Trace(tmp_path / "trace", lambda: 0)
    class ShortOut:
        def __init__(self):
            self.buf=""
        def write(self,s):
            # return 1 each time
            if not s:
                return 0
            chunk=s[:1]
            self.buf+=chunk
            return 1
        def flush(self): pass
    class Reply:
        def __init__(self, out):
            self.out=out
            self.calls=0
        def readline(self,_):
            self.calls+=1
            req=json.loads(self.out.buf)
            return json.dumps({**{k:req[k] for k in ("request_id","kind","input_sha256")},"output":{"silence":True}})+"\n"
    out=ShortOut()
    reply=Reply(out)
    bridge=StreamBridge(reply,out,trace)
    val=bridge._request("runtime", {"synthetic":True}, directive)
    assert val.silence is True
    assert reply.calls==1
    assert out.buf.endswith("\n")
    trace.close()

def test_zero_progress_fails_without_reply_read(tmp_path):
    trace = Trace(tmp_path / "trace", lambda: 0)
    class ZeroOut:
        def write(self,s): return 0
        def flush(self): pass
    class Reply:
        def __init__(self): self.calls=0
        def readline(self,_):
            self.calls+=1
            return ""
    r=Reply()
    with pytest.raises(TransportError):
        StreamBridge(r,ZeroOut(),trace)._request("runtime", {"a":1}, directive)
    assert r.calls==0
    trace.close()

def test_partial_send_then_exception_fails_without_reply(tmp_path):
    trace = Trace(tmp_path / "trace", lambda: 0)
    class PartialOut:
        def __init__(self): self.n=0
        def write(self,s):
            self.n+=1
            if self.n==2:
                raise OSError("send exception")
            return min(2,len(s))
        def flush(self): pass
    class Reply:
        def __init__(self): self.calls=0
        def readline(self,_):
            self.calls+=1
            return ""
    r=Reply()
    with pytest.raises(TransportError):
        StreamBridge(r,PartialOut(),trace)._request("runtime", {"a":1}, directive)
    assert r.calls==0
    trace.close()

def test_flush_failure_fails_without_reply(tmp_path):
    trace = Trace(tmp_path / "trace", lambda: 0)
    class FlushFailOut:
        def write(self,s): return len(s)
        def flush(self): raise OSError("flush fail")
    class Reply:
        def __init__(self): self.calls=0
        def readline(self,_):
            self.calls+=1
            return ""
    r=Reply()
    with pytest.raises(TransportError):
        StreamBridge(r,FlushFailOut(),trace)._request("runtime", {"a":1}, directive)
    assert r.calls==0
    trace.close()

# ---- 3 old BACKGROUND wake cannot see future input ----

def test_old_wake_cannot_see_future_input(tmp_path):
    d,_,_=setup(tmp_path)
    old=ConversationIngestor(d.runtime.store).commit_user_input(session_id="old",turn_index=1,user_text="PAST_ONLY",occurred_at=NOW)
    sig=d.runtime.wake_bus.emit(WakeSignalRequest(wake_source=WakeSource.NO_UPDATE,rule_id="synthetic_old_background",observed_at=NOW,evidence_refs=(ObjectRef(object_id=old.observation_id,revision=1),),dedupe_key="synthetic-old"))
    seen=[]
    def model(s):
        if s.wake_reason=="no_update":
            if not s.capability_history:
                return ModelDirective(capability_calls=(CapabilityCall(name="search_world",arguments={"query":"SYNTHETIC"}),))
            seen.extend(x["excerpt"] for x in s.capability_history[-1].data)
        return ModelDirective(silence=True)
    d.runtime.cognitive_runtime.model_handler=model
    d.runtime.index.catch_up()
    d.checkpoint()
    d.step()
    assert not any("SYNTHETIC event 1" in v for v in seen), f"old wake saw future: {seen}"
    d.close();d.trace.close()

def test_budget_deferral_not_forced(tmp_path):
    d,_,_=setup(tmp_path)
    # create budget that denies background
    store=d.runtime.store
    from aios_core.contracts.operations import OperationRequest
    policy=BudgetPolicy(object_id="budget_test",subject_id="user_1",occurred=TemporalExtent.point(NOW),learned_at=NOW,recorded_at=NOW,created_by="test",scope=BudgetScope.BACKGROUND_DAY,max_wakes=0,on_exceed=BudgetOnExceed.HARD_DENY)
    store.commit([policy],OperationRequest(operation_name="test.budget",expected_world_revision=int(store.current_world_revision()),reason="test",idempotency_key="budget_test",source_class=SourceClass.PLATFORM))
    old=ConversationIngestor(store).commit_user_input(session_id="old",turn_index=1,user_text="PAST",occurred_at=NOW)
    sig=d.runtime.wake_bus.emit(WakeSignalRequest(wake_source=WakeSource.NO_UPDATE,rule_id="synthetic_budget",observed_at=NOW,evidence_refs=(ObjectRef(object_id=old.observation_id,revision=1),),dedupe_key="budget-old"))
    d.runtime.index.catch_up()
    d.checkpoint()
    # clock advance should dispatch but get queued due to budget
    result=d.clock.advance_to(NOW+timedelta(hours=1))
    # pre_ingest_wakes should contain a queued wake, not completed
    pre=result.get("pre_ingest_wakes",[])
    assert len(pre)>=1
    assert any(r["state"]!="completed" for r in pre)  # budget blocked
    # ensure future event not ingested yet
    assert d.port.read_state()["last_acked_sequence"]==0
    d.close();d.trace.close()

# ---- 4 checkpoint missing inference ----

def test_checkpoint_missing_with_ack_blocks(tmp_path):
    d,_,_=setup(tmp_path)
    d.step()
    assert d.port.read_state()["last_acked_sequence"]==1
    d.state_path.unlink()
    d.close();d.trace.close()
    t=Trace(d.directory / "new-trace", d.runtime.store.current_world_revision)
    with pytest.raises(DriverBlocked, match="missing checkpoint|fresh synthetic genesis"):
        Driver(d.runtime,t,d.port,d.directory,session="synthetic-session",clock=NOW,stop_sequence=3)
    t.close()

def test_checkpoint_corrupt_blocks(tmp_path):
    d,_,_=setup(tmp_path)
    d.step()
    d.state_path.write_text("corrupt {")
    d.close();d.trace.close()
    t=Trace(d.directory / "new-trace2", d.runtime.store.current_world_revision)
    with pytest.raises(DriverBlocked, match="unreadable/corrupt"):
        Driver(d.runtime,t,d.port,d.directory,session="synthetic-session",clock=NOW,stop_sequence=3)
    t.close()

def test_explicit_legal_first_init(tmp_path):
    d,_,_=setup(tmp_path)
    # first init should succeed (already done in setup)
    assert d.state["completed_sequence"]==0
    d.close();d.trace.close()

def test_normal_restore_with_complete_checkpoint(tmp_path):
    d,_,modules=setup(tmp_path)
    d.step()
    final=tmp_path/"frozen"
    published=freeze(d,final)
    d.close();d.trace.close()
    other=tmp_path/"other"
    other.mkdir()
    resumed,_,_=setup(other,modules=modules,restore=final,confirmation=published.confirmation)
    assert resumed.state["completed_sequence"]==1
    resumed.close();resumed.trace.close()

# ---- 5 freeze publication fsync failure ----

def test_freeze_post_publication_fsync_failure_blocks_restore(tmp_path):
    d,_,_=setup(tmp_path)
    d.step()
    dest=tmp_path/"frozen"
    real_sync=os.fsync
    def fail_after_rename(fd):
        if dest.exists():
            raise OSError("synthetic post-publication fsync failure")
        return real_sync(fd)
    with patch("os.fsync", side_effect=fail_after_rename):
        with pytest.raises(OSError):
            freeze(d,dest)
    assert dest.exists()
    # ordinary restore without confirmation must be blocked
    with pytest.raises(Exception, match="publication unconfirmed|confirmation"):
        restore_frozen(dest,tmp_path/"restored",manifest_sha256=digest(dest/"manifest.json"))
    # fake confirmation also blocked
    with pytest.raises(Exception):
        restore_frozen(dest,tmp_path/"restored2",manifest_sha256=digest(dest/"manifest.json"),confirmation=object())
    # source state should be FAILED and preserve uncertain package path
    assert d.state["stage"]=="FAILED"
    assert "publication_id" in d.state
    d.close();d.trace.close()

# ---- 6 isolation canary preconditions ----

def test_isolation_canary_preconditions_and_positive_control():
    try:
        result=probe()
    except Exception as e:
        pytest.skip(f"isolation probe host facility unavailable: {e}")
    assert result["synthetic_boundary_status"]=="PASS"
    assert all(v["status"]=="PASS" for v in result["canaries"].values())
    assert result["controls"]["allowed_readable"] is True
    assert all(v=="NOT_TESTED" for v in result["real_resources"].values())

def test_isolation_outside_checks_not_tested_when_missing(tmp_path):
    # simulate missing canary file
    base=tmp_path/"base"
    base.mkdir()
    paths, hashes = create_canaries(base)
    # delete one canary
    list(paths.values())[0].unlink()
    before=outside_checks(paths, hashes)
    assert any(v=="NOT_TESTED" for v in before.values())
    # assess should be INCONCLUSIVE not PASS
    child={"denied":{k:True for k in paths},"controls":{"allowed_readable":True,"no_host_proc":True,"no_git_or_gh":True,"clean_environment":True,"chroot_capability_removed":True,"external_network_denied":True,"packet_readonly":True}}
    after=outside_checks(paths, hashes)
    report=assess(before, child, after)
    assert report["synthetic_boundary_status"] in ("INCONCLUSIVE","FAIL")
    # check that missing resource is NOT_TESTED not PASS
    assert any(v["status"]=="NOT_TESTED" for v in report["canaries"].values())
