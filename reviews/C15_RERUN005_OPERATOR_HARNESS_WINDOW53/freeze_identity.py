"""Operator only: freeze identity; never invoked by the Resident."""
import hashlib
import json
from pathlib import Path
import sys

repo=Path(sys.argv[1]).resolve()
root=repo/'reviews/internal_habitation/c15-rcc/v1/operator_prep/C15-RCC-RES-A-RERUN-005/harness'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'schema':'resident-rerun005-harness-identity-v1',
    'harness_files':{str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*.py'))},
    'source_files':{str(p.relative_to(repo)):sha(p) for folder in ('src/aios_core','tools/c15_persistence')
        for p in sorted((repo/folder).rglob('*.py'))},
    'python_sha256':sha(Path('/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python').resolve()),
    'core_tree':'16f1487e291b009c55bee402abfd79fdacbae960',
    'c15_tree':'b8a62370e6ffe80730b2ef4c17d625fab50446d4',
    'accepted_baseline':'703a8967878d8eaee70a8a8fce9df068204f5f76'}
p=root/'IDENTITY.json';p.write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
print(sha(p))
