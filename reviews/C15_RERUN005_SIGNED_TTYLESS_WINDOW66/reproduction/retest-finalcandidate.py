"""Fresh short-lived grants and four-scenario rerun of the exact final candidate."""
from pathlib import Path
import os,json,subprocess as sp
E=Path('/workspaces/window66-gate0-20261016T1509Z');OUT=E/'final-candidate-positive';OUT.mkdir(mode=0o755);os.umask(0o022)
assert json.loads((E/'resume-20261016T2020Z/runtime.log').read_text())['status']=='PASS'
assert 'PASS' in (E/'resume-20261016T2020Z/isolation.log').read_text()
assert 'PASS' in (E/'resume-20261016T2020Z/ipc.log').read_text()
s=(E/'issue-final.py').read_text().replace('window66-response-final-2020z','window66-response-finalcandidate').replace('synthetic-w66-final-','synthetic-w66-candidate-')
s=s.replace("(E/(scenario+'-operation.json'))","(OUT/(scenario+'-operation.json'))").replace("(E/'operator-issuance-audit.json')","(OUT/'operator-issuance-audit.json')")
(E/'issue-finalcandidate.py').write_text(s)
exec(compile(s,'existing-operator-finalcandidate-issuance','exec'),{'OUT':OUT})
GR=Path('/var/lib/aios-window65/trust/window66-response-finalcandidate')
for n in ['user','due','summary','delivered']:
 g=json.loads((GR/(n+'.json')).read_bytes());p=Path('/run/aios-w66-responses')/g['enrollment_id'];p.mkdir(mode=0o2750);os.chown(p,999,985);p.chmod(0o2750)
s=(E/'mechanical-validation.py').read_text().replace("E=pathlib.Path('/workspaces/window66-gate0-20261016T1509Z'); S=E/'candidate'", "E=pathlib.Path('/workspaces/window66-gate0-20261016T1509Z/final-candidate-positive'); S=E.parent/'candidate'")
s=s.replace('aios-window66-tests-retry3','aios-window66-tests-finalcandidate').replace('window66-response-retry3','window66-response-finalcandidate')
(OUT/'mechanical-validation.py').write_text(s)
sp.run(['/home/user/.cache/c002/final-runtime-003/runtime/3.12.14/venv/bin/python','-B',str(OUT/'mechanical-validation.py')],check=True)
