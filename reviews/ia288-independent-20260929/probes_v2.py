"""Independent synthetic probes. Candidate imports occur only during execution."""
import unittest, tempfile, pathlib, threading, json, sys, hashlib
from concurrent.futures import ThreadPoolExecutor

class Probes(unittest.TestCase):
    def setUp(self):
        from aios_exchange.ledger import ExchangeLedger, LedgerError
        self.L, self.E = ExchangeLedger, LedgerError
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.ledger = self.L(self.root/'ledger.jsonl')
    def append(self, event='request_published', rid='synthetic-1', response=None):
        return self.ledger.append(event, request_id=rid, request_sha256='a'*64, response_sha256=response)
    def test_legal_chain(self):
        self.append(); self.append('response_published', response='b'*64); self.append('response_consumed',response='b'*64)
        self.assertTrue(self.ledger.verify_chain()['ok'])
    def test_interior_mutation(self):
        self.append(); self.append(rid='synthetic-2')
        p=self.ledger.path; p.write_bytes(p.read_bytes().replace(b'synthetic-1', b'synthetic-X'))
        with self.assertRaises(self.E): self.append(rid='synthetic-3')
    def test_duplicate_rejected(self):
        self.append()
        with self.assertRaises(self.E): self.append()
    def test_valid_tail_boundary(self):
        self.append(); self.append('response_published',response='b'*64)
        p=self.ledger.path; p.write_bytes(p.read_bytes().splitlines(keepends=True)[0])
        self.assertTrue(self.ledger.verify_chain()['ok']) # permitted documented limitation
    def test_concurrent_append_preserves_validity(self):
        # Force the legal scheduling boundary after each writer's validated read.
        # No candidate bytes or ledger bytes are edited by this attack.
        barrier=threading.Barrier(2)
        def writer(rid):
            ledger=self.L(self.ledger.path)
            original=ledger.read_records
            def synchronized_read():
                records=original(); barrier.wait(timeout=10); return records
            ledger.read_records=synchronized_read
            try:
                ledger.append('request_published',request_id=rid,request_sha256='a'*64)
                return 'success'
            except self.E: return 'closed'
        with ThreadPoolExecutor(2) as pool: results=list(pool.map(writer,['synthetic-1','synthetic-2']))
        print('concurrent outcomes:',results,'chain:',self.ledger.verify_chain(),flush=True)
        self.assertTrue(self.ledger.verify_chain()['ok'], 'successful appends must not corrupt the durable ledger')
    def test_request_mutation_before_consume(self):
        from aios_exchange.bridge import ExchangeBridge
        b=ExchangeBridge(self.root/'exchange')
        req=b.publish_request(kind='model_directive',body={'synthetic':True})
        rid=req['request_id']
        response={'response_version':1,'request_id':rid,'request_sha256':req['request_sha256'],'authored_by':'EXTERNAL_CURRENT_RESIDENT_SESSION','directive':{'response':'synthetic','silence':False}}
        b.responses.publish_object(request_id=rid,response=response)
        p=pathlib.Path(req['path']); p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaises(Exception): b.consume_response(rid)

    def test_replay_integrity_matrix(self):
        from aios_exchange.bridge import ExchangeBridge
        for mode in ('intact','tamper','missing','changed','consume_tampered'):
            with self.subTest(mode=mode):
                b=ExchangeBridge(self.root/mode)
                r=b.publish_request(kind='model_directive',body={'synthetic':mode})
                rid=r['request_id']
                data=json.dumps({'response_version':1,'request_id':rid,'request_sha256':r['request_sha256'],
                    'authored_by':'EXTERNAL_CURRENT_RESIDENT_SESSION','directive':{'response':'synthetic'}}).encode()
                b.responses.publish_bytes(request_id=rid,response_bytes=data)
                p=b.responses.path_for(rid)
                if mode in ('tamper','consume_tampered'): p.write_bytes(data+b' ')
                if mode=='missing': p.unlink()
                if mode=='intact':
                    self.assertTrue(b.responses.publish_bytes(request_id=rid,response_bytes=data)['idempotent_replay'])
                else:
                    with self.assertRaises(Exception):
                        if mode=='consume_tampered': b.consume_response(rid)
                        else: b.responses.publish_bytes(request_id=rid,response_bytes=data+(b' ' if mode=='changed' else b''))
    def test_snapshot_recovery_matrix(self):
        from aios_exchange.runner import ExternalSessionConfig, ExternalSessionModelHandler
        from aios_exchange.schema import serialize_runtime_snapshot
        from aios_core.runtime.cognitive_runtime import RuntimeSnapshot
        for mode in ('legal','outstanding_mismatch','durable_mismatch','two_outstanding','two_durable','mixed'):
            with self.subTest(mode=mode):
                h=ExternalSessionModelHandler(ExternalSessionConfig(self.root/mode,response_timeout_s=.05))
                def snap(text): return RuntimeSnapshot(user_input=text,wake_reason='synthetic',cockpit={},
                    capability_catalog=(),capability_history=(),round_index=0,remaining_tool_rounds=1)
                s1,s2=snap('synthetic one'),snap('synthetic two')
                n=2 if mode in ('two_outstanding','two_durable','mixed') else 1
                for i in range(n):
                    r=h.bridge.publish_request(kind='model_directive',body=serialize_runtime_snapshot(s1))
                    if mode in ('legal','durable_mismatch','two_durable') or (mode=='mixed' and i==0):
                        h.bridge.responses.publish_object(request_id=r['request_id'],response={
                            'response_version':1,'request_id':r['request_id'],'request_sha256':r['request_sha256'],
                            'authored_by':'EXTERNAL_CURRENT_RESIDENT_SESSION','directive':{'response':'synthetic'}})
                if mode=='legal': self.assertEqual(h(s1).response,'synthetic')
                else:
                    from aios_exchange.bridge import ExchangeContractError
                    with self.assertRaises(ExchangeContractError): h(s2 if 'mismatch' in mode else s1)
    def test_manifest_symlink(self):
        from aios_exchange.content_manifest import core_content_manifest
        tree=self.root/'tree'; tree.mkdir(); (self.root/'file').write_text('synthetic')
        (tree/'link').symlink_to(self.root/'file')
        with self.assertRaises(ValueError): core_content_manifest(tree)

if __name__=='__main__':
    if '--collect-only' in sys.argv:
        for name in unittest.defaultTestLoader.getTestCaseNames(Probes): print('Probes.'+name)
    else: unittest.main(verbosity=2)
