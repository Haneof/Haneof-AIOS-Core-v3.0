#!/usr/bin/env python3
from __future__ import annotations
import contextlib, importlib.util, io, json, tempfile, sys
from pathlib import Path
helper_path=Path(sys.argv[1])
spec=importlib.util.spec_from_file_location("candidate_classifier",helper_path)
mod=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod)
CASES=[]
def add(name,rc,xml,expect_accept,class_): CASES.append(dict(name=name,rc=rc,xml=xml,expect_accept=expect_accept,class_=class_))
clean='<testsuite tests="1" failures="0" errors="0"><testcase file="tests/c15_persistence/test_ok.py" classname="tests.c15_persistence.test_ok" name="test_ok"/></testsuite>'
for rc in (-1,2,3,4,5,6,255): add(f"rc_{rc}",rc,clean,False,"exit_code")
add("rc0_clean",0,clean,True,"baseline")
add("rc1_downstream",1,'<testsuite tests="1" failures="1" errors="0"><testcase file="tests/c15_persistence/test_x.py" classname="tests.c15_persistence.test_x" name="test_x"><failure>boom</failure></testcase></testsuite>',True,"baseline")
add("missing_junit",1,None,False,"structure"); add("empty_junit",1,"",False,"structure"); add("malformed_xml",1,"<testsuite><testcase>",False,"structure")
add("namespace_rc1",1,'<testsuite xmlns="urn:x" tests="1" failures="1" errors="0"><testcase file="tests/c15_persistence/test_x.py" classname="tests.c15_persistence.test_x" name="test_x"><failure>boom</failure></testcase></testsuite>',False,"namespace")
add("namespace_rc0_hidden_failure",0,'<testsuite xmlns="urn:x" tests="1" failures="1" errors="0"><testcase file="tests/integration/test_core.py" name="x"><failure>boom</failure></testcase></testsuite>',False,"namespace")
add("nested_consistent",1,'<testsuites tests="1" failures="1" errors="0"><testsuite tests="1" failures="1" errors="0"><testcase file="tests/c15_persistence/test_x.py" name="x"><failure/></testcase></testsuite></testsuites>',True,"nested")
add("nested_summary_conflict",1,'<testsuites tests="1" failures="0" errors="0"><testsuite tests="1" failures="1" errors="0"><testcase file="tests/c15_persistence/test_x.py" name="x"><failure/></testcase></testsuite></testsuites>',False,"summary_integrity")
add("noninteger_failures",1,'<testsuite tests="1" failures="x" errors="0"><testcase file="tests/c15_persistence/test_x.py" name="x"><failure/></testcase></testsuite>',False,"summary_integrity")
add("summary_failure_without_case",1,'<testsuite tests="1" failures="1" errors="0"><testcase file="tests/c15_persistence/test_x.py" name="x"/></testsuite>',False,"summary_integrity")
add("failing_case_summary_zero",1,'<testsuite tests="1" failures="0" errors="0"><testcase file="tests/c15_persistence/test_x.py" name="x"><failure/></testcase></testsuite>',False,"summary_integrity")
add("same_case_failure_and_error",1,'<testsuite tests="1" failures="1" errors="1"><testcase file="tests/c15_persistence/test_x.py" name="x"><failure/><error/></testcase></testsuite>',False,"summary_integrity")
add("missing_file_classname_downstream",1,'<testsuite tests="1" failures="1" errors="0"><testcase classname="tests.c15_persistence.test_x" name="x"><failure/></testcase></testsuite>',True,"pytest_xunit2")
add("missing_classname_file_downstream",1,'<testsuite tests="1" failures="1" errors="0"><testcase file="tests/c15_persistence/test_x.py" name="x"><failure/></testcase></testsuite>',True,"mapping")
add("file_and_classname_empty",1,'<testsuite tests="1" failures="1" errors="0"><testcase file="" classname="" name="x"><failure/></testcase></testsuite>',False,"mapping")
add("windows_path",1,'<testsuite tests="1" failures="1" errors="0"><testcase file="tests\\c15_persistence\\test_x.py" name="x"><failure/></testcase></testsuite>',True,"mapping")
add("leading_dot_slash",1,'<testsuite tests="1" failures="1" errors="0"><testcase file="./tests/c15_persistence/test_x.py" name="x"><failure/></testcase></testsuite>',True,"mapping")
add("absolute_path",1,'<testsuite tests="1" failures="1" errors="0"><testcase file="/tmp/tests/c15_persistence/test_x.py" name="x"><failure/></testcase></testsuite>',False,"mapping")
add("dotdot_traversal",1,'<testsuite tests="1" failures="1" errors="0"><testcase file="tests/c15_persistence/../integration/test_core.py" name="x"><failure/></testcase></testsuite>',False,"mapping")
add("evil_prefix",1,'<testsuite tests="1" failures="1" errors="0"><testcase file="tests/c15_persistence_evil/test_x.py" name="x"><failure/></testcase></testsuite>',False,"mapping")
add("file_classname_conflict",1,'<testsuite tests="1" failures="1" errors="0"><testcase file="tests/c15_persistence/test_x.py" classname="tests.integration.test_core" name="x"><failure/></testcase></testsuite>',False,"mapping_conflict")
add("non_downstream_setup_error",1,'<testsuite tests="1" failures="0" errors="1"><testcase file="tests/integration/conftest.py" classname="tests.integration.conftest" name="setup"><error/></testcase></testsuite>',False,"setup_collection")
add("mixed_two_downstream_one_core",1,'<testsuite tests="3" failures="3" errors="0"><testcase file="tests/c15_persistence/a.py" name="a"><failure/></testcase><testcase file="tests/c15_persistence/b.py" name="b"><failure/></testcase><testcase file="tests/runtime/c.py" name="c"><failure/></testcase></testsuite>',False,"mixed")
rows=[]
with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    for case in CASES:
        p=root/(case["name"]+".xml")
        if case["xml"] is not None: p.write_text(case["xml"],encoding="utf-8")
        b=io.StringIO()
        with contextlib.redirect_stdout(b): out=mod.adjudicate(case["rc"],p)
        actual=(out==0)
        row={"name":case["name"],"class":case["class_"],"pytest_exit":case["rc"],"expected_accept":case["expect_accept"],"actual_accept":actual,"classifier_exit":out,"match":actual==case["expect_accept"],"stdout":b.getvalue().splitlines()}
        rows.append(row); print(json.dumps(row,sort_keys=True))
m=[r for r in rows if not r["match"]]
print(f"REVIEWER_JUNIT_FUZZ total={len(rows)} mismatches={len(m)}")
for r in m: print("MISMATCH",r["name"],"expected_accept",r["expected_accept"],"actual_accept",r["actual_accept"])
