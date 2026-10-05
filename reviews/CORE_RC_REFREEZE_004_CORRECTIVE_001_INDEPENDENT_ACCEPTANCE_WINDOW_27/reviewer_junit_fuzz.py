from pathlib import Path
import tempfile, importlib.util, json, sys
spec=importlib.util.spec_from_file_location('c',sys.argv[1])
c=importlib.util.module_from_spec(spec); spec.loader.exec_module(c)

def run(name, rc, xml, should_accept):
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'j.xml'
        if xml is not None:
            p.write_text(xml,encoding='utf-8')
        out=c.adjudicate(rc,p)
        accepted=(out==0)
        return {'name':name,'pytest_rc':rc,'classifier_rc':out,'accepted':accepted,'expected_accept':should_accept,'unexpected':accepted!=should_accept}

D='tests/c15_persistence/test_x.py'
C='tests.c15_persistence.test_x'
I='tests/integration/test_core.py'
CI='tests.integration.test_core'
cases=[]
for rc in (-1,2,3,4,5,6,255):
    cases.append((f'rc_{rc}',rc,'<testsuite tests="0" failures="0" errors="0"/>',False))
cases += [
 ('rc0_clean',0,'<testsuite tests="1" failures="0" errors="0"><testcase file="%s" classname="%s" name="ok"/></testsuite>'%(D,C),True),
 ('rc1_downstream',1,'<testsuite tests="1" failures="1" errors="0"><testcase file="%s" classname="%s" name="x"><failure>boom</failure></testcase></testsuite>'%(D,C),True),
 ('missing',1,None,False),
 ('empty',1,'',False),
 ('malformed',1,'<testsuite><testcase>',False),
 ('xml_namespace_rc1',1,'<testsuite xmlns="urn:x" tests="1" failures="1" errors="0"><testcase file="%s" classname="%s" name="x"><failure>boom</failure></testcase></testsuite>'%(D,C),False),
 ('xml_namespace_rc0_inconsistent_failure',0,'<testsuite xmlns="urn:x" tests="1" failures="1" errors="0"><testcase file="%s" classname="%s" name="x"><failure>boom</failure></testcase></testsuite>'%(D,C),False),
 ('nested_testsuites',1,'<testsuites tests="1" failures="1" errors="0"><testsuite tests="1" failures="1" errors="0"><testcase file="%s" classname="%s" name="x"><failure>boom</failure></testcase></testsuite></testsuites>'%(D,C),True),
 ('duplicate_nested_summary',1,'<testsuites tests="1" failures="1" errors="0"><testsuite tests="1" failures="1" errors="0"><testcase file="%s" classname="%s" name="x"><failure>boom</failure></testcase></testsuite></testsuites>'%(D,C),True),
 ('noninteger_failures',1,'<testsuite tests="1" failures="x" errors="0"><testcase file="%s" classname="%s" name="x"><failure>boom</failure></testcase></testsuite>'%(D,C),False),
 ('summary_failure_no_case',1,'<testsuite tests="1" failures="1" errors="0"><testcase file="%s" classname="%s" name="x"/></testsuite>'%(D,C),False),
 ('failure_case_summary_zero',1,'<testsuite tests="1" failures="0" errors="0"><testcase file="%s" classname="%s" name="x"><failure>boom</failure></testcase></testsuite>'%(D,C),False),
 ('failure_and_error_same_case',1,'<testsuite tests="1" failures="1" errors="1"><testcase file="%s" classname="%s" name="x"><failure>f</failure><error>e</error></testcase></testsuite>'%(D,C),False),
 ('missing_file_classname_ok',1,'<testsuite tests="1" failures="1" errors="0"><testcase classname="%s" name="x"><failure>boom</failure></testcase></testsuite>'%C,True),
 ('missing_classname_file_ok',1,'<testsuite tests="1" failures="1" errors="0"><testcase file="%s" name="x"><failure>boom</failure></testcase></testsuite>'%D,True),
 ('file_class_both_empty',1,'<testsuite tests="1" failures="1" errors="0"><testcase file="" classname="" name="x"><failure>boom</failure></testcase></testsuite>',False),
 ('windows_path',1,'<testsuite tests="1" failures="1" errors="0"><testcase file="tests\\c15_persistence\\test_x.py" classname="%s" name="x"><failure>boom</failure></testcase></testsuite>'%C,True),
 ('leading_dot_slash',1,'<testsuite tests="1" failures="1" errors="0"><testcase file="./%s" classname="%s" name="x"><failure>boom</failure></testcase></testsuite>'%(D,C),True),
 ('absolute_path',1,'<testsuite tests="1" failures="1" errors="0"><testcase file="/repo/%s" classname="%s" name="x"><failure>boom</failure></testcase></testsuite>'%(D,C),False),
 ('traversal_escape',1,'<testsuite tests="1" failures="1" errors="0"><testcase file="tests/c15_persistence/../integration/test_core.py" classname="%s" name="x"><failure>boom</failure></testcase></testsuite>'%CI,False),
 ('evil_prefix',1,'<testsuite tests="1" failures="1" errors="0"><testcase file="tests/c15_persistence_evil/test_x.py" classname="tests.c15_persistence_evil.test_x" name="x"><failure>boom</failure></testcase></testsuite>',False),
 ('classname_spoof',1,'<testsuite tests="1" failures="1" errors="0"><testcase classname="tests.c15_persistence.test_spoof" name="x"><failure>boom</failure></testcase></testsuite>',False),
 ('file_classname_conflict_file_downstream',1,'<testsuite tests="1" failures="1" errors="0"><testcase file="%s" classname="%s" name="x"><failure>boom</failure></testcase></testsuite>'%(D,CI),False),
 ('file_classname_conflict_file_core',1,'<testsuite tests="1" failures="1" errors="0"><testcase file="%s" classname="%s" name="x"><failure>boom</failure></testcase></testsuite>'%(I,C),False),
 ('setup_like_no_mapping',1,'<testsuite tests="1" failures="0" errors="1"><testcase name="setup"><error>boom</error></testcase></testsuite>',False),
 ('multi_downstream_one_core',1,'<testsuite tests="3" failures="3" errors="0"><testcase file="tests/c15_persistence/a.py" classname="tests.c15_persistence.a" name="a"><failure/></testcase><testcase file="tests/c15_persistence/b.py" classname="tests.c15_persistence.b" name="b"><failure/></testcase><testcase file="tests/integration/c.py" classname="tests.integration.c" name="c"><failure/></testcase></testsuite>',False),
]
results=[]
for x in cases:
    print('\n===',x[0],'===')
    results.append(run(*x))
print('\n=== SUMMARY ===')
for r in results:
    print(json.dumps(r,sort_keys=True))
unexpected=[r for r in results if r['unexpected']]
print('UNEXPECTED_COUNT',len(unexpected))
for r in unexpected: print('UNEXPECTED',r['name'],'accepted=',r['accepted'],'classifier_rc=',r['classifier_rc'])
Path(sys.argv[2]).write_text(json.dumps({'results':results,'unexpected':unexpected},indent=2,sort_keys=True))
print('JUNIT_FUZZ_COMPLETED=YES')
raise SystemExit(0)
