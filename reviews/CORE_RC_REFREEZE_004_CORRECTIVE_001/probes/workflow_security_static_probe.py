#!/usr/bin/env python3
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text(encoding="utf-8")
g0=s.index("  rc004-freeze-gate:"); p0=s.index("  rc004-mandatory-pin-publisher:")
g=s[g0:p0]; p=s[p0:]
checks={
"gate_read_only":"permissions:\n      contents: read\n      pull-requests: read" in g and "contents: write" not in g,
"checkout_no_persist":"persist-credentials: false" in g,
"dispatch_pinned":"WORKFLOW_DISPATCH_REF_REJECTED" in g,
"c15_structured":"c15_junit_classifier.py" in g and '--junit "$junit"' in g,
"c15_rc_reject":"C15_PYTEST_EXIT_NOT_ADMISSIBLE" in g,
"terminal_remote":"TERMINAL_REMOTE_HEAD_MISMATCH" in g,
"terminal_diff":'git -C "$RC004_TARGET" diff --quiet --' in g and 'git -C "$RC004_TARGET" diff --cached --quiet --' in g,
"terminal_fresh_main":"refs/remotes/rc004/terminal-main" in g,
"publisher_needs":"needs: rc004-freeze-gate" in p,
"publisher_write":"permissions:\n      contents: write" in p,
"publisher_no_checkout":"actions/checkout" not in p,
"publisher_no_candidate":"reviews/" not in p and "python " not in p,
"publisher_non201":'if [ "$code" != "201" ]; then' in p and "exit 1" in p,
"old_bypass_absent":'test "$code" = "201" || cat' not in s,
}
names=["Corrective-001 workflow security regressions","Fresh complete Core regression","Fresh extract and run frozen Window 20 A/B and Window 17 reviewer probes","Corrective-003 trust-root, alternate-mint, replay/conflict, supersession, and partial-commit checks","Real SIGKILL and fresh-process recovery","Clean non-editable wheel install and headless lifecycle","Backup restore rebuild and trusted-return authority preservation","Writer restart historical FIX current-time and no-second-truth-store spot checks","C15 structured JUnit classifier regression matrix","Fresh C15 downstream compatibility debt classification","Fresh open-PR contamination inventory","Runtime source manifest and SHA256 evidence index"]
checks["terminal_after_candidate"]=s.index("      - name: Terminal immutability and protected-drift gate")>max(s.index("      - name: "+n) for n in names)
for k,v in checks.items(): print(f"{k}={str(v).lower()}")
if not all(checks.values()): raise SystemExit("WORKFLOW_SECURITY_STATIC=FAIL")
print("WORKFLOW_SECURITY_STATIC=PASS")
