# Independent Acceptance — C15-RCC-RES-A-RERUN-004

**ACCEPTANCE_FAIL / blocker=2**

Review-only / evidence-only / **DO NOT MERGE**. This is not an implementation PR,
not Resident execution, not RC recertification, and not permission to resume any
downstream work. No changes to #273, #263 or #265; no merge, evaluator, B/C run,
or persistence corrective work was performed.

## Identity and authority

Role: Independent Fresh Resident A Evidence Acceptance Reviewer.

- Candidate: PR #273, `f251e9c0026a0f97fdee20397936cb5e3b18c61c`.
- Parent: `0b17c7f35697dc4a24b731185868d29967efcf58`.
- Tree: `fd312286b7b83cd550ecc49d72b78656e6e91b71`.
- Software: `f20f2edfa7af00d0286493fd15196ca9503bc315`.
- Core: `9adcbe07fa84d70d3fcd65724f8e6c53ad6b8623`.
- Tests: `7e33b5ef8432370234965d3ccd61248c703c4019`.
- Freshly fetched main at start and at final technical revalidation:
  `589e0347b646ade6eeb7f09cfa6f511fba99c1ef`; not assumed permanent.
- PR head unchanged and OPEN/unmerged at final revalidation.
- Session-fixed review branch: `arena/01a0e903-haneof-aios-core-v3-0`.
  It is used exclusively for review evidence; no alternate branch was created.

Read the dispatched independent-acceptance prompt in full, A-004 execution
prompt, Resident A contract, current board/checkpoint control entry, and RC-003
integration receipt. Prior A cognition was not opened or used as expected
answers. No hidden chain-of-thought was requested. Release adapter/hash code
was inspected as a reviewer, without running release or opening sealed fixture
payloads or evaluator material.

Below, `E/` means the directory at the exact candidate:
`reviews/internal_habitation/c15-rcc/v1/resident/runs/a004-27bb1fb3da404f4d/`.
All original-file citations are pinned to that candidate, not the review branch.

## Blocker IA-A004-01 — cursor 1 not-submitted justification does not prove non-dispatch

**Paths:** `E/receipts/cursor_01_turn_recovery.json`,
`E/decision_requests/req-0001-model_directive-13f2b448.json`,
`E/decision_responses/req-0001-model_directive-13f2b448.json`,
`E/decision_requests/req-0002-model_directive-983ede97.json`,
`E/logs/decision_chain.jsonl`, `E/runner.py` (`ResidentBridge._exchange`).
Also frozen Core `src/aios_core/runtime/turn_runtime.py:1278-1302`,
`src/aios_core/runtime/background_attempt.py:1257-1313`.

**Reproduction:** Run the frozen probes below. Inspect `recovery1`, the first
two entries of `decision_audit`, the recovery receipt, and the source excerpts
in `raw/source-inspection.txt`.

**Observed:** The first request was written at
`2026-09-28T16:34:23.994159+00:00`. Its response file contains a fully semantic
`commit_ai_world_claim` directive, but no `request_id` echo. The second request
at `16:39:30.169868+00:00` reuses the same Core attempt ID
`bgattempt_261339075d7c14c6bb32a353eb8f6a39` and repeats that semantic claim.
The recovery statement infers non-submission from null provider/request/meter/
fingerprint fields and an echo-validation error. However:

1. The bridge writes the request and waits for a Resident-produced response
   **before** validating that echo. This is a post-request validation failure,
   not affirmative proof that the semantic handler was never invoked.
2. The frozen runtime explicitly marks dispatch and binds the request before
   handler invocation. `reconcile_not_submitted` accepts operator evidence text;
   the resulting state label does not independently establish that evidence.
3. All successful local responses also lack provider identity. Null fields
   cannot distinguish no dispatch from a dispatched anonymous handler whose
   response was rejected before Core acceptance/metering.
4. The first complete semantic response is positive evidence inconsistent with
   treating missing provider fields as proof of no Resident decision.

**Expected:** Durable evidence of a genuinely unsubmitted first model attempt,
or an independently supported, contract-valid recovery classification for an
already invoked local semantic handler. "No directive applied" is not the same
as "not submitted".

**Binding:** Independent prompt §9 explicitly requires non-submission to be
proved, not asserted. §8 requires real decision provenance. This finding does
not assert duplicate World effects: the frozen World has one canonical first
USER observation, one first-turn assistant output and one initial claim
revision; a later claim revision is legitimate cursor-3 lineage. The problem
is the evidence/legal basis for retry, not demonstrated duplicate cognition.

**Minimal corrective scope:** PM/author must supply genuinely contemporaneous
boundary evidence and a defensible recovery adjudication, or commission a
fresh run with correct handshake/recovery capture under a separately authorized
task. A prose rewrite or declaring provider IDs absent cannot establish the
missing fact. Reviewer made no repair and does not authorize altering #273.

## Blocker IA-A004-02 — cursor 10 exact reply predating reconciliation is unproved

**Paths:** `E/decision_requests/req-0032-model_directive-9002a5bb.json`,
`E/decision_responses/req-0032-model_directive-9002a5bb.json`,
`E/logs/decision_chain.jsonl`, `E/logs/runner.log`,
`E/receipts/cursor_10_turn_recovery.json`, `E/exports/turn_executions.jsonl`,
`E/world.db` (attempts, turn execution and assistant observation).

**Reproduction:** Inspect probe `recovery10` and `decision_inventory`; search
the entire decision chain for request 0032 and compare recovery evidence to
the frozen response and assistant observation.

**Observed:** Request 0032 was logged at
`2026-09-28T16:56:26.670452+00:00`. There is no `response_read` event for it,
no response-created timestamp/receipt, and no separate contemporaneous
response-write/commit chronology in the package. The response JSON contains
only request ID and directive. The next cursor-10 run starts at
`17:00:34.893955+00:00` and finishes already reconciled.

Round 0 is metered and claim `clm_e2d2b8bdbe0a23130e3ad85b` is durable once.
Round 1 `bgattempt_4933387f54a0962be4a9936c30e37b13` remains `in_doubt`,
`JSONDecodeError`, with no response fingerprint/meter. The recovery receipt
asserts that exact reply bytes already existed, but supplies no independently
ordered capture establishing that fact. Final digests match:

- response: `b43589c2c13b3c30686e121b9f3c049b5ad9ff4fe50804a779db00b1797c37a1`;
- reply: `eb7cd7c20aa662715d15d7977d72fad653dbbfe74055e5a88e224705b3c78e3a`;
- assistant: `obs_conv_ai_0b440b106fa95aedec9a9f64@1`.

Those equalities prove final consistency, **not creation-before-reconciliation**.
The assistant's timestamps are virtual event time, not wall-clock write
chronology. Git stores the final package, not local file write order. A partial
JSON read does not establish what the eventual complete reply bytes were.

**Expected:** A durable, ordered local response capture/hash tied to the current
Resident before assistant commit/reconciliation, plus the recovery transition
record. Provider provenance is NOT demanded: a truthful local capture can
provide this evidence without fabricating provider identity.

**Binding:** Independent prompt §10 says recovery depending on unverifiable
after-the-fact prose must FAIL. §8 also forbids post-hoc response creation.
The package cannot exclude that alternative. This is an evidentiary failure,
not an accusation that fabrication actually occurred.

**Minimal corrective scope:** Preserve and provide pre-existing contemporaneous
response/recovery records if they exist; otherwise obtain a separately approved
fresh run with atomic, durably ordered response publication. Recomputing the
same final hash or adding a retrospective timestamp cannot cure chronology.
No model reinvocation or duplicate effect was observed in the supplied ledger;
that does not establish the missing pre-recovery binding.

## Complete review matrix

### Evidence-only / frozen implementation / environment

Git object checks match all requested pins. Candidate parent diff is exactly
189 files, all under E; zero source/test/tool/governance edits. Runner selects
repository-local `src` and calls real Core classes, not an embedded semantic
engine. The package asserts a detached frozen checkout; identity pins are
consistent, but no independent captured module `__file__`/runtime source-tree
attestation is present. Do not turn source consistency into stronger historical
execution proof. This uncertainty reinforces the evidence limitations; it is
not counted as an additional independent blocker.

Actual reviewer environment: CPython 3.11.2, SQLite 3.40.1,
Linux 6.1.158+ x86_64/glibc 2.36. Probes use stdlib only; no Pydantic import or
Resident runtime execution. Run identity records Python 3.12.14; README claims
Pydantic 2.13.5 and SQLite 3.40.1. These historical environment assertions are
not independently measured by the frozen artifacts. SQLite integrity checks
succeed here. No requirement to match formal RC SQLite 3.45.1 was invented.

### Freshness / contamination / future isolation

World begins with cursor-1 canonical USER at revision 1, no preceding seed
objects. Fresh run/session/conversation identifiers agree across identity,
requests, receipts and World. No old A-ID, evaluator or expected-answer lexical
hits in the 100 decision files. No later cursor event ID, ingested object ID or
complete later payload appears in earlier requests. Capabilities in the runner
are chosen from response files, not keyword/fixture rules. Snapshots and
capability histories inspected across user, review, summaries, watch wakes,
derivation and retries do not show B/C payloads or future release-state.

Limits: a lexical scan and a final World cannot prove what an external Resident
session never read. There is no full host-session/tool access audit in this
package. We did not read old A transcripts to perform answer matching. Prefix
`obs_c14_fixture_` is the canonical adapter's naming convention, not by itself
old Resident contamination. No positive material semantic reuse was established.

Runner catches up virtual review ticks after current event ingestion. In
particular cursor 13 runs a review labelled November 5 with cursor-13 reality
already released on November 6. This is not a later-*cursor* leak, but should
not be represented as an actually executed November-5 historical review.
No clock advance beyond final released timestamp was found.

### Cursor / ACK / freeze / World / index

All 13 receipts are contiguous, exact and backed by durable object/revision/
World revision; payload and projection hashes independently match 13/13.
Canonical USER session and monotonic indices match 7/7, without duplicate USER
observations. PLATFORM values match their released projection. Missing standalone
ACK stdout for some USER steps is not counted as missing ACK: the durable
release receipt chain is complete. State is A, last ACK 13, next 14, pending
null; no cursor-14 event artifact exists. This proves the supplied artifact
boundary, not an unlogged negative about all possible host actions.

World and index independently open with SQLite integrity `ok`; max World
revision is 89 and search watermark 89. Current objects: 22 observations,
3 claims, 2 communication experiences, 1 operation experience, 3 tasks,
20 wakes, 11 summaries, 4 evidence sets, 70 dependencies. Recovery outputs and
claim revisions are not duplicated in the stored lineage. No index lag.

All 188 MANIFEST entries match. MANIFEST itself was independently hashed;
all six FREEZE artifact references and 26 checkpoint/step references match.
All 98 chain request/response digest entries match (50 requests, 48 responses).
All 50 request and 50 response files, DBs, release/runtime states and recovery
receipts were independently SHA-256 hashed. No candidate hash mismatch found.
Hash equality does not repair the two missing-boundary proofs.

### 50 decisions / provenance / semantic lineage

Inventory: 39 model-directive requests + 11 dimension-summary requests.
37 successful model responses are metered with unknown usage, all provider /
model / request / token fields null and usage_complete false. Provider receipt
and request-binding exports are empty for this local path; no fake provider
identity or R6/replacement-model claim is inferred. Local handlers are explicitly
allowed by frozen Core. Provider absence alone is NOT a blocker.

Reviewed all response directives and their serialized chains. Examples:
1–5 claim creation and forward revision; 6–7 grounded accepted communication;
8–9 / 18–19 review read then silence; 10–14 / 20–21 / 46–49 summaries;
17 / 22 / 50 derivation silence; 23–25 search/watch/status;
26–30 failure inspection, invalid task-type rejection then corrected legal
capability, waiting-evidence; 33–38 success inspection and rejected direct
completion followed by legal ready/running/completed transitions; 39–42 user
feedback and watch cleanup; 43–45 review and operation experience.

These chains support input/output responsiveness and no scripted fixture
answers in the frozen runner. They do not, by themselves, authenticate the
external file writer as the declared session or establish the two failed
handshakes' chronology. Do not claim all 50 choices independently authenticated.

Claims track visible user boundaries; forward revision retains evidence.
Communication accepted status follows explicit user feedback. Operation
experience cites failure and success observations rather than only task
completion. No Claim quota found. Nonblocking quality discrepancy: summary
response 0049 describes four user/assistant pairs with confused times, while
that day contains three canonical pairs plus two wake-delivery observations
(eight observations total). It must not be used as a substitute for exact
conversation provenance. README says four cursor-6 summaries; durable evidence
shows five. These do not constitute another material durable Claim blocker.

### Attention watches / canonical plumbing

Frozen `FusedTurnRuntime.reality_ingest` listener is precisely
`attention_watches.evaluate_observation`. Runner replays that method over new
Observation revisions ordered by World revision, after legal ingest. Matching
and state transitions remain inside Core; watches are Resident-authored and
stored as Core tasks, not a separate truth store. At cursor 9, ingest precedes
wake revision 46; at cursor 11, ingest precedes wake revision 58. Both watches
are one-shot and transition to ready, then Resident closes them. No duplicate
wake effect or changed predicate was observed.

The replay watermark is transport state, not semantic classification. It can
scan old observations on first use and is not a general proof of equivalence
under arbitrary crash/restart or newly-created-watch scenarios. For this exact
run no matching pre-watch release observation was re-triggered. The code also
contains a mechanical virtual-time dispatcher; no alternative semantic
scheduler/truth store was found. Calling the accepted Core watch evaluator
is compatible with the contract's mandated external mechanical ingest path
for this observed sequence; it is not evidence of normal listener delivery
at ingest instant and not general scheduler certification.

### Wake / Review / Summary / derivation completion

Independent enumeration is preserved in `raw/followup.jsonl` (`due_work`,
`final_lifecycle`), not inferred from README completion language:

- Four daily review opportunities: Nov 3/4/5/6 at 17:05 UTC. First three have
  completed review wakes; fourth is durably suppressed, not completed work.
- Dimension summary commits: cursor 6 = 5, cursor 7 = 2, cursor 13 = 4;
  11 total. Intermediate jobs are unchanged/skipped rather than new completions.
- Derivation member wakes merge into three completed bundles at cursors 6, 7,
  13; merged members are not individually miscounted as model runs.
- Watch wakes at 9 and 11 are completed. Three tasks are completed. Final
  wake states consist of completed, merged and suppressed; no pending due task
  or wake remains in the supplied final World.
- No artificial forward clock jump beyond `2026-11-06T19:10:00+00:00`.

This checks stored lifecycle completeness, not historical provenance of the
external semantic writer. It does not reverse the recovery blockers.

## Reproduction and harness corrections

Extract only E from exact candidate with `git archive` into an external scratch
directory, then (from repository root):

```sh
sha256sum -c reviews/independent/c15-a004-acceptance/PROBE.sha256
python reviews/independent/c15-a004-acceptance/probe.py "$EXTRACTED_E" > probe.jsonl
python reviews/independent/c15-a004-acceptance/probe_followup.py "$EXTRACTED_E" probe.jsonl > followup.jsonl
```

Probe sources were hashed **before first execution**. `PROBE_FREEZE.txt` records
enumeration, base source revision and time. Candidate pin and actual environment
are also in raw output. Both executions exited successfully; stderr files are
preserved. No Resident execution is involved.

Corrections preserved rather than erased:

- Initial shell discovery twice supplied `/home/user` instead of repository cwd;
  git/gh returned "not a git repository". Successful fresh fetch followed; no
  repository content changed in those failed discovery calls.
- Exploratory SQLite schema inspection used `mode=ro` without `immutable=1`,
  creating scratch `world.db-shm`/`world.db-wal` sidecars outside Git. Hence v1
  coverage reports those extra scratch files. They are not in the exact
  189-file candidate. Probes themselves use immutable read-only connections.
- v1's tentative event `payload_hash` used absent key `payload` (hash of null),
  NOT the release field `resident_visible_payload`; do not call those values
  candidate mismatches. Additive followup independently checks UTF-8 text and
  canonical projection with 13/13 matches. Original v1 is unchanged.
- An exploratory pretty-printer assumed early checkpoints all had
  `attention_watch_receipts` and raised KeyError; subsequent enumeration uses
  `.get`. Neither probe raw result nor candidate was overwritten by that error.

## Publication and stop

Formal report, frozen probes, hashes, raw results, recovery timeline, source
inspection and final PR revalidation are published together on the review-only
branch. The exact review commit is the commit containing this report; the
review PR body and comment on #273 pin its full SHA (avoiding a self-referential
commit hash inside its own tree). Review PR is draft / evidence-only / DO NOT
MERGE. Publication failure must yield EVIDENCE_PUBLICATION_BLOCKED, not a
completed gate. After successful publication, stop immediately.
