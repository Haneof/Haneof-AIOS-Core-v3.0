from __future__ import annotations
import argparse, json, posixpath, xml.etree.ElementTree as ET
from pathlib import Path

ap=argparse.ArgumentParser(); ap.add_argument('--pytest-exit',type=int,required=True); ap.add_argument('--junit',type=Path,required=True); ns=ap.parse_args()
print(f'pytest_exit={ns.pytest_exit}')
assert ns.pytest_exit in (0,1), f'NON_ADMISSIBLE_PYTEST_EXIT={ns.pytest_exit}'
root=ET.parse(ns.junit).getroot()
def local(tag:str)->str: return tag.rsplit('}',1)[-1]
structured=[]
for tc in root.iter():
    if local(tc.tag)!='testcase': continue
    kinds=[local(ch.tag) for ch in list(tc) if local(ch.tag) in {'failure','error'}]
    if not kinds: continue
    file_attr=(tc.attrib.get('file') or '').replace('\\','/')
    cls=tc.attrib.get('classname') or ''
    mapped=file_attr or (cls.replace('.','/') if cls else '')
    normalized=posixpath.normpath(mapped) if mapped else ''
    structured.append({'kinds':kinds,'file':file_attr,'classname':cls,'mapped':mapped,'normalized':normalized,'name':tc.attrib.get('name','')})
print('structured_count='+str(len(structured)))
for x in structured: print('case='+json.dumps(x,sort_keys=True))
if ns.pytest_exit==0:
    assert not structured, 'RC0_WITH_STRUCTURED_FAILURE_OR_ERROR'
    print('REVIEWER_C15_RC0_CLEAN=PASS')
else:
    assert structured, 'RC1_WITH_ZERO_STRUCTURED_FAILURE_OR_ERROR'
    bad=[x for x in structured if not (x['normalized']=='tests/c15_persistence' or x['normalized'].startswith('tests/c15_persistence/'))]
    assert not bad, 'NON_DOWNSTREAM_STRUCTURED='+json.dumps(bad,sort_keys=True)
    print('REVIEWER_C15_REAL_JUNIT_ALL_DOWNSTREAM=PASS')
