from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text(encoding='utf-8')
terminal=s.index('      - name: Terminal immutability and protected-drift gate')
upload=s.index('      - name: Upload complete RC004 evidence bundle')
publisher=s.index('  rc004-mandatory-pin-publisher:')
pub=s[publisher:]
jobA=s[s.index('  rc004-freeze-gate:'):publisher]
assert terminal < upload < publisher
assert 'TERMINAL_REMOTE_HEAD_MISMATCH' in jobA
assert 'ls-remote' not in pub and 'TERMINAL_REMOTE_HEAD_MISMATCH' not in pub
assert "if: ${{ needs.rc004-freeze-gate.result == 'success' }}" in pub
exact='2380121639865b1bd29176cf944f5a20afe4112d'; drift='deadbeef'*5
remote=exact
github_sha=exact
terminal_pass=(remote==github_sha)
remote=drift
artifact_upload_success=True
job_a_success=terminal_pass and artifact_upload_success
job_b_runs=job_a_success
http_code='201'
publisher_success=job_b_runs and http_code=='201'
overall_success=job_a_success and publisher_success
print(f'terminal_before_upload={terminal < upload}')
print('publisher_remote_recheck=false')
print(f'terminal_pass={terminal_pass}')
print(f'remote_after_terminal={remote}')
print(f'job_a_success_after_drift={job_a_success}')
print(f'job_b_runs_after_drift={job_b_runs}')
print(f'publisher_success_after_drift={publisher_success}')
print(f'overall_success_after_drift={overall_success}')
if overall_success:
    print('TOCTOU_FALSE_GREEN_REPRODUCED=YES')
    raise SystemExit(0)
raise SystemExit(1)
