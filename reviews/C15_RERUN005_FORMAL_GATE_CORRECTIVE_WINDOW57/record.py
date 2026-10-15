"""Record actual command, source identity, exit code and unmodified byte streams."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    command = sys.argv[2:]
    source_identity = {}
    for argument in command:
        path = Path(argument.split('::',1)[0])
        if path.is_file() and path.suffix == '.py':
            source_identity[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif path.is_dir():
            for item in path.rglob('*.py'):
                source_identity[str(item.resolve())] = hashlib.sha256(item.read_bytes()).hexdigest()
    base = Path('reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005')
    for path in (base/'harness/IDENTITY.json',base/'RESIDENT_SAFE_LAUNCH_PACKET.json',base/'artifacts/resident-harness.tar.gz'):
        if path.is_file():source_identity[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    start = datetime.now(timezone.utc).isoformat()
    with (out/'stdout').open('wb') as stdout, (out/'stderr').open('wb') as stderr:
        result = subprocess.run(command, stdout=stdout, stderr=stderr)
    record = {'command': command, 'cwd': str(Path.cwd()), 'started': start,
              'finished': datetime.now(timezone.utc).isoformat(), 'exit_code': result.returncode,
              'classification': 'DEVELOPMENT_ONLY_NOT_FORMAL_ACCEPTANCE',
              'git_head': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              'tested_source_sha256': source_identity,
              'environment': {k: os.environ[k] for k in ('PYTHONPATH','APPROVED53_PYTHON','TMPDIR','PYTHONDONTWRITEBYTECODE') if k in os.environ},
              'logs': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()}}
    (out/'record.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'log_directory': str(out), 'exit_code': result.returncode}))
    return result.returncode

if __name__ == '__main__':
    raise SystemExit(main())
