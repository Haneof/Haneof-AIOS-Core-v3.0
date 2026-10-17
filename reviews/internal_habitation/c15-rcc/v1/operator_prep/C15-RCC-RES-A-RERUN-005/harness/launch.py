"""Pinned isolated-mode bootstrap. Use only after independent approval."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import importlib.util
import types

root=Path(__file__).resolve().parent
sys.pycache_prefix=tempfile.mkdtemp(prefix='aios53-import-')
sys.dont_write_bytecode=True
parser=argparse.ArgumentParser(add_help=False)
parser.add_argument('--source-repo',type=Path,required=True)
parser.add_argument('--identity-sha256',required=True)
args,remaining=parser.parse_known_args()
if not remaining:raise SystemExit('command required')
# The launch packet pins this digest; never infer the expected hash from disk.
if hashlib.sha256((root/'IDENTITY.json').read_bytes()).hexdigest()!=args.identity_sha256:
    raise SystemExit('BLOCKED / IDENTITY_MANIFEST_SUBSTITUTION')
manifest=json.loads((root/'IDENTITY.json').read_bytes())
for relative,digest in manifest['harness_files'].items():
    p=root/relative
    if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:
        raise SystemExit('BLOCKED / HARNESS_SUBSTITUTION')
sys.path.extend([str(root),str(args.source_repo.resolve()/'src'),str(args.source_repo.resolve())])
def load_package(name,path):
    spec=importlib.util.spec_from_file_location(name,path,submodule_search_locations=[str(path.parent)])
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
load_package('r005',root/'r005/__init__.py')
from r005.checks import verify,loaded_modules
try:
    verify(root,args.source_repo,args.identity_sha256)
except Exception as exc:
    raise SystemExit('BLOCKED / STARTUP_VERIFICATION_FAILED: '+str(exc))
load_package('aios_core',args.source_repo.resolve()/'src/aios_core/__init__.py')
tools_namespace=types.ModuleType('tools');tools_namespace.__path__=[str(args.source_repo.resolve()/'tools')]
sys.modules['tools']=tools_namespace
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['AIOS53_LAUNCH']=str(root/'launch.py')
os.environ['AIOS53_SOURCE_REPO']=str(args.source_repo.resolve())
os.environ['AIOS53_IDENTITY_SHA']=args.identity_sha256
os.environ['PYTHONPATH']=os.pathsep.join([str(root),str(args.source_repo.resolve()/'src'),str(args.source_repo.resolve())])
if remaining[0]=='service':
    service_parser=argparse.ArgumentParser()
    service_parser.add_argument('--exchange',required=True);service_parser.add_argument('--channel',required=True)
    service_parser.add_argument('--runner-pid',required=True);service_parser.add_argument('--parent-fd',required=True)
    service=service_parser.parse_args(remaining[1:])
    sys.argv=['publisher_service',service.exchange,service.channel,service.runner_pid,service.parent_fd]
    runpy.run_module('r005.publisher_service',run_name='__main__')
else:
    from r005.cli import main
    sys.argv=[str(root/'launch.py'),*remaining]
    main()
