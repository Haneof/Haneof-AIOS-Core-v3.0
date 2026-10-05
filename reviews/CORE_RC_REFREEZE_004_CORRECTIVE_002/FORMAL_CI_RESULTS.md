# Pre-final formal CI results

Full hosted run 37268221493 at ae0ec67fc1c5fe798f51968b322b22bfabdbd782:
- overall SUCCESS
- RC004 exact frozen software / formal gate SUCCESS
- RC004 mandatory exact-pin publisher SUCCESS
- RC004 whole-run identity seal SUCCESS

Fresh carry-forward:
- Full Core: 928 passed
- Window 20 Suite A: 4 probes / 0 failures
- Window 20 Suite B: 7 probes / 0 failures
- Window 17: 14 probes / 0 failures
- Corrective-003 focused security: 214 passed
- real SIGKILL/fresh-process recovery: 9 passed
- clean non-editable wheel/headless: HEADLESS_CLEAN_INSTALL_PASS
- backup/restore/rebuild: BACKUP_RESTORE_ROUTE_B_PASS
- writer/restart/FIX/current-time/SCALE: 52 passed
- C15 classifier self-test: PASS cases=10
- frozen C15 suite: 45 failed / 33 passed, pytest rc=1, downstream-only debt
- open-PR contamination inventory: PASS, relevant_open_prs=22
- terminal tracked mutation: NONE
- terminal checkout credential: NONE
- frozen identities exact

Formal environment:
- CPython 3.12.14
- Pydantic 2.13.5
- pytest 8.4.2
- SQLite 3.45.1
- OpenSSL 3.0.13 30 Jan 2024
- Linux 6.17.0-1022-azure x86_64
- Python executable /home/runner/work/_temp/rc004-formal-venv/bin/python
- aios_core.__file__ /home/runner/work/_temp/aios-rc004-frozen-software/src/aios_core/__init__.py

Artifact:
- id 11327960050
- digest sha256:f6247949cbae7875baea523bba021c64e957182a1eb43c85bb33ec784f88719d

Pre-final pin comment: 203438818

Fresh actual pytest 8.4.2 hosted controls in run 37291221473:
- usage error rc=4
- collection error rc=2
- no-tests rc=5
- ACTUAL_PYTEST_NONTEST_FAIL_CLOSED=PASS

Final exact-head receipts are intentionally external after the tracked evidence freeze.
