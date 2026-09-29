"""Independent wheel/enumeration and durable-publication fault probes."""
import unittest,tempfile,pathlib,shutil,subprocess,sys,os
from unittest.mock import patch
P=pathlib.Path(os.environ.get('IA_PACKAGE','/nonexistent'))
W=pathlib.Path('/home/user/.cache/ia288/runtime/runtime/3.12.14/wheelhouse')
class Additional(unittest.TestCase):
    def test_locked_wheelhouse(self):
        for mode in ('intact','wrong_bytes','missing','extra'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                target=pathlib.Path(tmp)/'wheels'; shutil.copytree(W,target)
                wheel=sorted(target.glob('*.whl'))[0]
                if mode=='wrong_bytes': wheel.write_bytes(b'wrong synthetic bytes')
                if mode=='missing': wheel.unlink()
                if mode=='extra': (target/'unexpected-1-py3-none-any.whl').write_bytes(b'synthetic')
                result=subprocess.run([sys.executable,str(P/'bootstrap/wheel_lock.py'),'verify','--lock',str(P/'bootstrap/PYTHON_WHEEL_LOCK.json'),'--wheelhouse',str(target)],capture_output=True,text=True)
                print(mode,result.returncode,result.stdout,result.stderr)
                self.assertEqual(result.returncode==0,mode=='intact')
    def test_collection_fail_closed(self):
        from operator_tools.gate_runner import parse_collection_output, GateEnumerationError
        for text,code in (('',0),('0 tests collected in 0.1s',0),('x::test_a\n2 tests collected in 0.1s',0),('x::test_a\n1 test collected in 0.1s',1)):
            with self.subTest(text=text,code=code),self.assertRaises(GateEnumerationError): parse_collection_output(text,'',code)
        self.assertEqual(parse_collection_output('x::test_a\n1 test collected in 0.1s','',0),['x::test_a'])
    def test_directory_fsync_error_blocks_publication(self):
        import stat
        from aios_exchange.bridge import ExchangeBridge
        from aios_exchange import atomic
        with tempfile.TemporaryDirectory() as tmp:
            b=ExchangeBridge(pathlib.Path(tmp)); real=atomic.os.fsync
            def fail_directory(fd):
                if stat.S_ISDIR(os.fstat(fd).st_mode): raise OSError('synthetic directory durability failure')
                return real(fd)
            with patch.object(atomic.os,'fsync',side_effect=fail_directory):
                with self.assertRaises(Exception): b.publish_request(kind='model_directive',body={'synthetic':True})

if __name__=='__main__':
    if '--collect-only' in sys.argv:
        for name in unittest.defaultTestLoader.getTestCaseNames(Additional):print('Additional.'+name)
    else:unittest.main(verbosity=2)
