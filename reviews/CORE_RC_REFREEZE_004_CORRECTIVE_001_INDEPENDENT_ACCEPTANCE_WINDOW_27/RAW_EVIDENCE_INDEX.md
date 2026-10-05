# Window 27 Raw Evidence Index

## Gate attack — run 37263834648
Artifact `11326130132` — SHA-256 `0e26d296a3bd554eaeef32e4f938e777d1d7301cd2956b5e911c562a292ab01a`

```
HISTORICAL_BLK002_REPRO=PASS
old_publisher_exit=0

UNEXPECTED_COUNT 6
UNEXPECTED xml_namespace_rc0_inconsistent_failure accepted=True classifier_rc=0
UNEXPECTED failure_case_summary_zero accepted=True classifier_rc=0
UNEXPECTED failure_and_error_same_case accepted=True classifier_rc=0
UNEXPECTED traversal_escape accepted=True classifier_rc=0
UNEXPECTED classname_spoof accepted=True classifier_rc=0
UNEXPECTED file_classname_conflict_file_downstream accepted=True classifier_rc=0

terminal_before_upload=True
publisher_remote_recheck=false
terminal_pass=True
remote_after_terminal=deadbeefdeadbeefdeadbeefdeadbeefdeadbeef
job_a_success_after_drift=True
job_b_runs_after_drift=True
publisher_success_after_drift=True
overall_success_after_drift=True
TOCTOU_FALSE_GREEN_REPRODUCED=YES

read_token_write_http=403 curl_rc=0
Resource not accessible by integration
PUBLISHER_FAULT_PROBE=PASS
final_candidate=2380121639865b1bd29176cf944f5a20afe4112d
```

## Frozen probes — run 37263834686
Artifact `11325900599` — SHA-256 `315e60dbb8327eca240bf7645cbdf90eb35af74c019d7f8ce0d93aa8e754c7a3`

```
A sha256=ec1dc5c2c5406d5d9e74825f62e0a17fb80f8ebd6dc250817fa048511ce292b5
SUMMARY | probes=4 failures=0
B sha256=769242465817f31734661ba7ba9c3d5f7d06b8d3f5235d72d2026956d9b98eb1
SUMMARY | probes=7 failures=0
W17 sha256=a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3
SUMMARY | probes=14 failures=0
```

## Core carry-forward — run 37263834603
Artifact `11326130664` — SHA-256 `f28239fee935988d17caa79f6ae8861d8969d10870b09efc6bc4c1caae5ec8f9`

```
python=3.12.14
pydantic=2.13.5
pytest=8.4.2
aios_core.__file__=/home/runner/work/_temp/frozen/src/aios_core/__init__.py
928 passed
214 passed
9 passed
HEADLESS_CLEAN_INSTALL_PASS
BACKUP_RESTORE_ROUTE_B_PASS
52 passed
45 failed, 33 passed
pytest_exit=1
REVIEWER_C15_REAL_JUNIT_ALL_DOWNSTREAM=PASS
final_candidate=2380121639865b1bd29176cf944f5a20afe4112d
```

Downloaded JUnit parse:
- Core: 928 tests / 0 failures / 0 errors
- C15: 78 tests / 45 failures / 0 errors

## Window 26 formal artifact
Artifact `11309495093` — server/local SHA-256 `02415a0457af3aec5cb50d5195120202aae2c9cb23d3c81cbefaf867b7d216e0`

Downloaded and inspected. Internal runtime SHA index: 32 entries / 0 mismatches.

Mandatory exact-pin comment: `203380647`.
