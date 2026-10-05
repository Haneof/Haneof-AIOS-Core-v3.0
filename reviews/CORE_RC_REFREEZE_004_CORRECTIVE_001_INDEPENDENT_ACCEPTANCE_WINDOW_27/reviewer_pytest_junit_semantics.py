#!/usr/bin/env python3
from __future__ import annotations
import contextlib, importlib.util, io, json, subprocess, sys, tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
helper=Path(sys.argv[1]); python=sys.argv[2]
spec=importlib.util.spec_from_file_location("candidate_classifier",helper)
mod=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod)
def inspect(label,rc,junit):
    info={"label":label,"pytest_exit":rc,"junit_exists":junit.exists(),"junit_size":junit.stat().st_size if junit.exists() else 0}
    if junit.exists() and junit.stat().st_size:
        root=ET.parse(junit).getroot(); info["root_tag"]=root.tag; info["root_attrib"]=root.attrib
        suites=[]; cases=[]
        for n in root.iter():
            tag=n.tag.split("}")[-1]
            if tag=="testsuite": suites.append(dict(n.attrib))
            if tag=="testcase":
                kids=[x.tag.split("}")[-1] for x in list(n)]
                if "failure" in kids or "error" in kids: cases.append({"attrib":dict(n.attrib),"children":kids})
        info["suite_summaries"]=suites; info["structured_cases"]=cases
    b=io.StringIO()
    with contextlib.redirect_stdout(b): out=mod.adjudicate(rc,junit)
    info["candidate_classifier_exit"]=out; info["candidate_classifier_stdout"]=b.getvalue().splitlines()
    print(json.dumps(info,sort_keys=True))
with tempfile.TemporaryDirectory() as td:
    root=Path(td); base=root/"tests"/"c15_persistence"; base.mkdir(parents=True)
    (base/"test_semantics.py").write_text("import pytest\ndef test_fail(): assert False\n@pytest.fixture\ndef broken(): raise RuntimeError('setup boom')\ndef test_setup_error(broken): pass\n",encoding="utf-8")
    j=root/"normal.xml"; cp=subprocess.run([python,"-m","pytest","-o","addopts=","-q","--tb=no",str(base/"test_semantics.py"),"--junitxml="+str(j)],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT); print("PYTEST_OUTPUT normal",repr(cp.stdout[-1500:])); inspect("ordinary_failure_plus_setup_error",cp.returncode,j)
    (base/"test_bad_syntax.py").write_text("def broken(:\n",encoding="utf-8")
    j=root/"collection.xml"; cp=subprocess.run([python,"-m","pytest","-o","addopts=","-q","--tb=no",str(base/"test_bad_syntax.py"),"--junitxml="+str(j)],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT); print("PYTEST_OUTPUT collection",repr(cp.stdout[-1500:])); inspect("collection_error",cp.returncode,j)
    empty=root/"tests"/"c15_persistence_empty"; empty.mkdir()
    j=root/"notests.xml"; cp=subprocess.run([python,"-m","pytest","-o","addopts=","-q","--tb=no",str(empty),"--junitxml="+str(j)],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT); print("PYTEST_OUTPUT no_tests",repr(cp.stdout[-1200:])); inspect("no_tests",cp.returncode,j)
    j=root/"usage.xml"; cp=subprocess.run([python,"-m","pytest","--definitely-not-a-real-option","--junitxml="+str(j)],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT); print("PYTEST_OUTPUT usage",repr(cp.stdout[-1200:])); inspect("usage_error",cp.returncode,j)
