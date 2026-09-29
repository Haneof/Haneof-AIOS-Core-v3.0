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
        response={'response_version':1,'request_id':rid,'request_sha256':req['request_sha256'],'directive':{'finish':True}}
        b.responses.publish_object(request_id=rid,response=response)
        p=pathlib.Path(req['path']); p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaises(Exception): b.consume_response(rid)

if __name__=='__main__':
    if '--collect-only' in sys.argv:
        for name in unittest.defaultTestLoader.getTestCaseNames(Probes): print('Probes.'+name)
    else: unittest.main(verbosity=2)
