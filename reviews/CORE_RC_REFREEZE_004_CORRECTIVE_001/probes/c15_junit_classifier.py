#!/usr/bin/env python3
from __future__ import annotations
import argparse, tempfile, xml.etree.ElementTree as ET
from pathlib import Path
DOWNSTREAM_PREFIX="tests/c15_persistence/"

def mapped(tc):
    f=(tc.attrib.get("file") or "").replace("\\","/")
    while f.startswith("./"): f=f[2:]
    if f: return f
    c=tc.attrib.get("classname") or ""
    return c.replace(".","/") if c else None

def adjudicate(rc:int,p:Path)->int:
    print(f"pytest_exit={rc}")
    if rc not in (0,1):
        print(f"C15_PYTEST_EXIT_NOT_ADMISSIBLE rc={rc}"); return 2
    if not p.is_file():
        print("C15_JUNIT_MISSING"); return 3
    if p.stat().st_size<=0:
        print("C15_JUNIT_EMPTY"); return 3
    try: root=ET.parse(p).getroot()
    except ET.ParseError as exc:
        print(f"C15_JUNIT_MALFORMED {exc}"); return 3
    cases=[]
    for tc in root.iter("testcase"):
        kids=list(tc); fail=any(x.tag=="failure" for x in kids); err=any(x.tag=="error" for x in kids)
        if fail or err: cases.append((tc,"failure" if fail else "error",mapped(tc)))
    sf=[]; se=[]
    for n in root.iter():
        if n.tag in {"testsuite","testsuites"}:
            try:
                if "failures" in n.attrib: sf.append(int(n.attrib["failures"]))
                if "errors" in n.attrib: se.append(int(n.attrib["errors"]))
            except ValueError:
                print("C15_JUNIT_BAD_COUNT"); return 3
    print(f"structured_failed_error_testcases={len(cases)}")
    for tc,kind,m in cases:
        print("structured_case="+repr({"kind":kind,"classname":tc.attrib.get("classname",""),"name":tc.attrib.get("name",""),"file":tc.attrib.get("file",""),"mapped":m}))
    if rc==0:
        if cases or any(sf) or any(se):
            print("C15_RC0_JUNIT_NOT_CLEAN"); return 4
        print("C15_RC0_CLEAN_ACCEPT"); return 0
    if not cases:
        print("C15_RC1_WITH_ZERO_STRUCTURED_FAILURE_OR_ERROR"); return 5
    bad=[(kind,m,tc.attrib.get("classname",""),tc.attrib.get("name","")) for tc,kind,m in cases if not m or not m.startswith(DOWNSTREAM_PREFIX)]
    if bad:
        print("ACCEPTED_CORE_REGRESSION_EXPOSED_BY_C15")
        for x in bad: print("non_downstream_structured_case="+repr(x))
        return 6
    print("CORE_FREEZE_NOT_BLOCKED_BY_DOWNSTREAM_OPERATOR_DEBT")
    print("C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT")
    return 0

def self_test()->int:
    cases=[
      ("rc0_clean",0,'<testsuite tests="1" failures="0" errors="0"><testcase classname="tests.c15_persistence.test_ok" name="test_ok"/></testsuite>',True),
      ("rc1_downstream",1,'<testsuite tests="1" failures="1" errors="0"><testcase classname="tests.c15_persistence.test_x" name="test_x"><failure>boom</failure></testcase></testsuite>',True),
      ("rc1_nondownstream",1,'<testsuite tests="1" failures="1" errors="0"><testcase classname="tests.integration.test_core" name="test_core"><failure>boom</failure></testcase></testsuite>',False),
      ("rc2",2,'<testsuite tests="0" failures="0" errors="0"/>',False),
      ("rc3",3,'<testsuite tests="0" failures="0" errors="0"/>',False),
      ("rc4",4,'<testsuite tests="0" failures="0" errors="0"/>',False),
      ("rc5",5,'<testsuite tests="0" failures="0" errors="0"/>',False),
      ("missing_junit",1,None,False),
      ("malformed_junit",1,'<testsuite><testcase>',False),
      ("rc1_zero_structured",1,'<testsuite tests="1" failures="0" errors="0"><testcase classname="tests.c15_persistence.test_x" name="test_x"/></testsuite>',False),
    ]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); failures=[]
        for name,rc,xml,expected in cases:
            p=root/f"{name}.xml"
            if xml is not None: p.write_text(xml,encoding="utf-8")
            out=adjudicate(rc,p); ok=(out==0)
            print(f"SELFTEST name={name} expected_ok={expected} actual_exit={out}")
            if ok!=expected: failures.append((name,out,expected))
        if failures:
            print("SELFTEST_FAILURES="+repr(failures)); return 1
    print("C15_JUNIT_CLASSIFIER_SELFTEST=PASS cases=10"); return 0

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--pytest-exit",type=int); ap.add_argument("--junit",type=Path); ap.add_argument("--self-test",action="store_true"); ns=ap.parse_args()
    if ns.self_test: return self_test()
    if ns.pytest_exit is None or ns.junit is None: ap.error("--pytest-exit and --junit required")
    return adjudicate(ns.pytest_exit,ns.junit)
if __name__=="__main__": raise SystemExit(main())
