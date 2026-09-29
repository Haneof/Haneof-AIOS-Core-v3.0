"""Additional independent synthetic attacks; retains v2 as immutable import."""
import unittest, pathlib, tempfile, datetime as dt, threading, time, json, hashlib, sys
from probes_v2 import Probes

class Extra(unittest.TestCase):
    def test_due_wake_external_roundtrip(self):
        from aios_exchange.runner import run_due_work
        from aios_exchange.bridge import ExchangeBridge
        from aios_core.headless import HeadlessCore, HeadlessConfig
        from aios_core.contracts.enums import WakeSource
        from aios_core.wake.service import WakeSignalRequest
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp); world=root/'world.sqlite'; index=root/'index.sqlite'; exchange=root/'exchange'
            now=dt.datetime(2026,9,29,10,tzinfo=dt.timezone.utc)
            def forbidden(snapshot): raise AssertionError('setup called model')
            with HeadlessCore(config=HeadlessConfig(world_path=world,index_path=index,subject_id='ia-synthetic'),model_handler=forbidden) as c:
                c.runtime.wake_bus.emit(WakeSignalRequest(wake_source=WakeSource.SAFETY,rule_id='ia-synthetic',observed_at=now,priority=100,dedupe_key='ia-synthetic'))
            errors=[]; done=threading.Event()
            def external():
                try:
                    b=ExchangeBridge(exchange)
                    while not done.wait(.01):
                        for rid in b.recovery_state()['open_dispatched']:
                            b.responses.publish_object(request_id=rid,response={'response_version':1,'request_id':rid,
                                'request_sha256':b.request_sha256(rid),'authored_by':'EXTERNAL_CURRENT_RESIDENT_SESSION',
                                'directive':{'response':'independent synthetic completion'}})
                except Exception as exc: errors.append(repr(exc))
            worker=threading.Thread(target=external); worker.start()
            try:
                result=run_due_work(world_path=world,index_path=index,subject_id='ia-synthetic',exchange_root=exchange,
                    now=now,max_wakes=1,include_periodic_review=False,response_timeout_s=10,poll_interval_s=.01)
            finally: done.set(); worker.join(15)
            print('independent due result:',json.dumps(result,default=str),flush=True)
            self.assertFalse(errors); self.assertFalse(worker.is_alive())
            self.assertEqual(len(result['handoffs']),1)
            self.assertEqual(result['due_work_result']['wakes'][0]['wake']['state'],'completed')
            self.assertEqual([r['event'] for r in ExchangeBridge(exchange).ledger.read_records()],
                ['request_published','response_published','response_consumed'])
    def test_ledger_fault_matrix(self):
        from aios_exchange.bridge import ExchangeBridge
        from aios_exchange.canonical import canonical_json_bytes, sha256_hex
        for fault in ('mutation','deletion','duplicate_request','duplicate_response','duplicate_consume','order','seq','prev','digest','request_digest','response_digest'):
            for operation in ('append','recovery','consume','lookup'):
                with self.subTest(fault=fault,operation=operation), tempfile.TemporaryDirectory() as tmp:
                    b=ExchangeBridge(pathlib.Path(tmp)); r=b.publish_request(kind='model_directive',body={'synthetic':True}); rid=r['request_id']
                    b.responses.publish_object(request_id=rid,response={'response_version':1,'request_id':rid,
                        'request_sha256':r['request_sha256'],'authored_by':'EXTERNAL_CURRENT_RESIDENT_SESSION','directive':{'response':'synthetic'}})
                    b.consume_response(rid); rows=b.ledger.read_records()
                    rehash=False
                    if fault=='mutation': rows[0]['wall_clock']='changed'
                    elif fault=='deletion': del rows[1]
                    elif fault.startswith('duplicate_'):
                        pos={'duplicate_request':0,'duplicate_response':1,'duplicate_consume':2}[fault]
                        rows.insert(pos+1,dict(rows[pos])); rehash=True
                    elif fault=='order': rows[0]['event']='response_published'; rehash=True
                    elif fault=='seq': rows[1]['seq']=90
                    elif fault=='prev': rows[1]['prev_sha256']='f'*64
                    elif fault=='digest': rows[1]['record_sha256']='f'*64
                    elif fault=='request_digest': rows[1]['request_sha256']='f'*64; rehash=True
                    elif fault=='response_digest': rows[2]['response_sha256']='f'*64; rehash=True
                    if rehash:
                        prev='0'*64
                        for i,row in enumerate(rows,1):
                            row.update(seq=i,prev_sha256=prev); row.pop('record_sha256',None)
                            row['record_sha256']=sha256_hex(canonical_json_bytes(row)); prev=row['record_sha256']
                    b.ledger.path.write_bytes(b''.join(canonical_json_bytes(row)+b'\n' for row in rows))
                    with self.assertRaises(Exception):
                        if operation=='append': b.ledger.append('request_published',request_id='other',request_sha256='a'*64)
                        elif operation=='recovery': b.recovery_state()
                        elif operation=='consume': b.consume_response(rid)
                        else: b.ledger.latest_event(rid,'request_published')

if __name__=='__main__':
    if '--collect-only' in sys.argv:
        for cls in (Probes,Extra):
            for name in unittest.defaultTestLoader.getTestCaseNames(cls): print(cls.__name__+'.'+name)
    else: unittest.main(verbosity=2)
