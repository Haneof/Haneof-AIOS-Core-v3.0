"""Collection imports no candidate code. All binding executions require exact runtime."""
import os
import pathlib
import sys
import pytest

@pytest.fixture(scope='session')
def package():
    path = pathlib.Path(os.environ['C002_PACKAGE']).resolve()
    sys.path.insert(0, str(path / 'harness'))
    sys.path.insert(0, str(pathlib.Path(os.environ['C002_REPO']).resolve() / 'src'))
    sys.path.insert(0, str(path / 'harness/tests'))
    import platform, pydantic, sqlite3, ssl
    assert platform.python_version() == '3.12.14'
    assert pydantic.__version__ == '2.13.5'
    assert pytest.__version__ == '8.4.2'
    assert sqlite3.sqlite_version == '3.45.1'
    assert ssl.OPENSSL_VERSION.split()[1] == '3.0.13'
    return path
