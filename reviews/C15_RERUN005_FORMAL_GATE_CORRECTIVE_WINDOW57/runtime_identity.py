"""Verify reused approved archive bytes, every materialized regular file and versions."""
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import ssl
import sys
import tarfile
import pydantic
import pytest

sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
zip_path,tar_path = map(Path,sys.argv[1:3])
assert sha(zip_path) == 'cc6b72631e000fa161f027c3daf946805d41022a25725ead040d26c5509d155a'
assert sha(tar_path) == 'ecfe4b4b6e9dee1a08342974e816f739dcd77fcd3f25f3ad7626cc7102e5673e'
base = Path('/home/user/.cache/c002/final-runtime-003')
count = 0
with tarfile.open(tar_path,'r:gz') as archive:
    for member in archive.getmembers():
        if member.isfile():
            assert (base/member.name).read_bytes() == archive.extractfile(member).read(),member.name
            assert (base/member.name).stat().st_mode & 0o777 == member.mode & 0o777,member.name
            count += 1
binary = Path(sys.executable).resolve()
assert sha(binary) == '09605fdfbe88ca0d45a575ab8179cecd2a7167d95555b7bb8e6f29f29e82d42b'
versions = [platform.python_version(),pydantic.__version__,pytest.__version__,sqlite3.sqlite_version,ssl.OPENSSL_VERSION.split()[1]]
assert versions == ['3.12.14','2.13.5','8.4.2','3.45.1','3.0.13'],versions
print(json.dumps({'status':'PASS','runtime_zip_sha256':sha(zip_path),'runtime_tar_sha256':sha(tar_path),
    'materialized_regular_files_verified':count,'python':sys.executable,'real_binary':str(binary),
    'binary_sha256':sha(binary),'versions':versions},sort_keys=True,indent=2))
