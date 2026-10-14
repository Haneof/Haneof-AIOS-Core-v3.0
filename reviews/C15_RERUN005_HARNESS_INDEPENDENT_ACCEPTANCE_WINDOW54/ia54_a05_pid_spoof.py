#!/usr/bin/env python3
"""IA54-A05 frozen reviewer-owned synthetic caller-PID impersonation.
Candidate source (exact-head blob sha 8411348d1377854d5eee10cf4dd25acc9c8c0b78):
  publisher_service.py:90 command['caller_pid']; :91 os.kill(peer,0);
  :95 if peer!=runner_pid; :99 registered[rid] = command['context'].
Preconditions: unrelated same-UID process has write access to the channel and
knows the live runner PID and an already-published request id/digest.
Expected defense: reject the message unless sender OS identity is the Runner.
Fail criterion: mere inclusion of a real runner PID in untrusted JSON passes
registration gate, accepting attacker-controlled signing context.
This executes the identity decision exactly as written in source in a disposable
process scenario, NOT the full source candidate or Core trusted return.
"""
import json
import os
import subprocess

runner=subprocess.Popen(['sleep','10'])
try:
    runner_pid=runner.pid
    attacker_pid=os.getpid()
    assert attacker_pid!=runner_pid
    malicious={'command':'register','caller_pid':runner_pid,
        'request_id':'req-synthetic-1','request_sha256':'0'*64,
        'context':{'attempt_id':'ATTACKER_SELECTED_CONTEXT','nonce':'ATTACKER_SELECTED_NONCE'}}
    # Exact tested predicate from publisher_service.py lines 90-99:
    peer=int(malicious['caller_pid'])
    os.kill(peer,0)
    if peer==os.getpid():raise ValueError('publisher cannot call itself')
    if malicious['command']=='register':
        if peer!=runner_pid:raise ValueError('only live runner may register requests')
        # A valid durable request/digest is an independent, non-identity
        # precondition; exact checks for those are not exercised here.
        context_that_would_be_registered=malicious['context']
    print(json.dumps({'attack':'IA54-A05-forged-caller-pid',
        'actual_attacker_pid':attacker_pid,'actual_runner_pid':runner_pid,
        'json_claimed_caller_pid':malicious['caller_pid'],
        'claimed_pid_is_alive':True,
        'live_identity_predicate_accepts_attacker':True,
        'untrusted_context_on_registration_path':context_that_would_be_registered,
        'exact_candidate_execution':False,
        'durable_request_digest_precondition_tested':False,
        'core_semantic_application_demonstrated':False},indent=2))
finally:
    runner.terminate();runner.wait(timeout=3)
