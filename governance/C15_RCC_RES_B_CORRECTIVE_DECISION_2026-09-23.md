# C15 Resident B corrective acceptance decision

Task: `C15-RCC-RES-B-CORRECTIVE-001`
Date: 2026-09-23
Access: **PM / OPERATOR ONLY — not Resident-visible**
Decision: **PR #121 candidate NOT ACCEPTED; fresh B requires operator preflight and independent release**

## 1. Authority and activation

This is one governance/acceptance task authorized by the project owner. It updates the project map, task board and checkpoint; it does not execute a Resident, amend the constitution, or change Core/fixture semantics.

**Integration barrier:** this decision and its queue changes become authoritative only when the governance PR containing this file is merged into `main`. An unmerged branch, chat message or prepared prompt does not release a new experiment. Until integration, treat this as a proposed corrective decision; do not start another B run using the obsolete READY row. After integration, select work from the live-main board.

### 2026-09-24 owner-requested process clarification

Routine governance-document review and integration may be performed by the authoring PM in this same window. This is **PM self-review**, not independent review. A new AI window is not a prerequisite for merging maps, task status and this ruling. The previous request for an independent integration window was unnecessary and is withdrawn. Check exact scope, evidence, current PR CI and actual merge result; respect branch protection and never use an administrator bypass. If protection requires another approval, report that real requirement rather than inventing a process gate.

This clarification does not relax fresh-context blindness, independence from the experiment implementer where explicitly required, Resident evidence acceptance, or C15 independent semantic evaluation. Do not treat self-review of this governance PR as any of those experiments or verdicts. Integration and its status receipt remain the same governance task, not permission to execute the next task.

Reviewed live main: `ed07b5890909ae09cb2a0849729662b4235c1e3b`.

- Frozen Core: `bcd6bf353126318f9a97076b52ec1740d43f35a4`.
- Accepted A: PR #117 @ `3e51f728d7959048b75fea01d405bc837b0e8185`.
- Reviewed B: PR #121 @ `b6e5ac939bef83615292bcf9b9099d76737d82b0`.
- #117 and #121 heads were rechecked unchanged when preparing this decision.
- Report: `reviews/C15_RCC_RES_B_001_PM_CORRECTIVE_REVIEW_2026-09-23.md`.

This supersedes **only** the old unconditional B-start authorization in `C15_FINAL_RELEASE_DECISION_2026-09-23.md`. Accepted A, its hashes, the Core freeze and C15 R1–R9 semantics remain unchanged.

## 2. Candidate disposition

`C15-RCC-RES-B-001 = FAILED` **for the submitted candidate's execution-evidence acceptance**, not a judgment that AIOS Core cannot support cognitive continuity.

PR #121 becomes **OPEN / UNMERGED / PINNED / NON-CANONICAL / DIAGNOSTIC**. Do not edit, replace, repair in place, squash, merge, or delete its evidence. PR #117 remains the sole accepted A handoff. No World from #121 may initialize the canonical replacement run or Resident C.

Facts supporting non-acceptance:

- B World is at revision 97, but revisions 89–97 contain only nine input Observations.
- B operations contain five mechanical ingest commits and four canonical user-input commits; no new assistant-delivery records or due-work state changes are present.
- Metering contains only A-era calls; no B-session model call appears.
- The submitted index watermark is 88, not 97.
- Ten submitted files contain summaries of claimed behavior but no contemporaneous RuntimeSnapshot/directive/capability-result chain or B runtime checkpoint.

There is **no Claim quota**. Zero new Claims is legal and is not grounds for rejection. Legal silence/retention must still have its real execution path recorded. Fixture-provided outcomes do not prove a Resident performed the preceding behavior.

This is not an R1–R9 semantic verdict or an allegation about unsubmitted activity. If independently verifiable, already-existing contemporaneous artifacts later appear, PM may open a separate evidence-reconsideration task pinned to their provenance. No retroactive prose, reconstructed model decisions, or index catch-up may be represented as the historical run. Such reconsideration is not implicitly authorized by this decision.

## 3. Recovery path and one-window tasks

```text
C15-RCC-RES-B-CORRECTIVE-001         this governance decision
  -> C15-RCC-RES-B-PREFLIGHT-001     non-blind operator; transport/evidence only
  -> C15-RCC-RES-B-RELEASE-001       independent PM; inspect isolation and release
  -> C15-RCC-RES-B-RERUN-001         genuinely fresh blind Resident B
  -> C15-RCC-RES-B-ACCEPT-001        independent execution-evidence acceptance
  -> C15-RCC-MODEL-ATTEST-001        operator/PM; trusted identity readiness
  -> C15-RCC-RES-C-001              distinct-model Resident, only if released
  -> C15-RCC-EVAL-001 -> C15-RCC-CLOSE-001
  -> C16 -> broad P16 -> P17
```

After this governance change is integrated, the unique next READY task is **`C15-RCC-RES-B-PREFLIGHT-001`**. All later tasks stay BLOCKED until their dependencies are accepted and written to main. Never execute two of these roles in the same model context. An operator who has seen reports/fixture internals cannot become the blind Resident.

### Preflight scope and exit evidence

The operator may reuse existing audited transport/ingest/runtime code, but must not reuse A's selected directives, answers, prose, checkpoints containing semantic decisions, or B's failed run. No second runtime, cognition DB, semantic rule engine or replay of prior model outputs.

Deliver a **transport-only**, model-agnostic adapter and a mechanically auditable run package specification:

1. Restore exact immutable accepted-A World/index/release-state bytes into a new run directory; verify declared hashes and A boundary before initialization. Inspect legally required restart state separately; do not smuggle transcripts or expected cognition in it. Do not modify source artifacts.
2. Prove the executable Core source tree equals the frozen anchor. Governance-only main changes are allowed; semantic Core changes require separate governance. Use Python 3.12+ as required by the package.
3. Drive only the existing `FusedTurnRuntime`/`CognitiveRuntime`, canonical user ingest, ordinary user `run_turn`, clock/index/Summary/Wake/Review paths. Keep subject/session/turn/text/time consistent. No ad-hoc direct SQLite reasoning or fabricated RuntimeSnapshot.
4. At every genuine model request, pause and expose the current RuntimeSnapshot/capability catalog to the Resident. Transport only the Resident's explicit directive/summary response; never default to a semantic answer, select a Claim, or silently substitute a fake model.
5. Capture input snapshots, actual submitted directives, tool requests/results/errors, user-facing output, due-work/resume state, model-call metering, and World revision references **as execution happens**. Only observable outputs/structured decisions are needed; do not request hidden chain-of-thought. Missing provider token/identity telemetry stays explicitly unknown, never fabricated.
6. Enforce one-event release/ingest/ack and completion of the legally due processing at that timestamp before requesting the next event. Respect existing budgets and scheduling; record legitimate future/budget-deferred work rather than force-draining it or silently skipping it.
7. Freeze final World, synchronized/rebuilt index, restart state, release receipts, execution trace and a hash manifest. Verify World/index watermark consistency and receipt-to-durable-write binding. Use a WAL-safe frozen snapshot; do not omit uncheckpointed SQLite changes.
8. Use only disposable synthetic input for mechanical smoke/negative checks. **Do not reveal or run real B cursors 14–22 in preflight; do not inspect C's future.** No real Resident semantic execution in this task.
9. Document actual access isolation. An isolated Resident interface must not expose repository reports, Git history/PR metadata, sealed fixture/evaluator contents, operator scripts or out-of-band A summaries. A prompt saying “don't read” alone is not proof of isolation. If the platform only offers a full-repository coding window, document this limitation and remain BLOCKED pending an explicitly accepted execution arrangement; do not claim strong isolation.
10. Produce `operator_manifest`, `resident_packet_manifest`, exact entry commands, scope diff, mechanical-check evidence and an independent-release checklist. Safe packet contains only its mechanical manifest, authorized session interface and Resident-safe instruction; durable semantic content reaches the model via normal AIOS capabilities/context, not a prewritten handoff dump.

Preflight must also inventory available trusted A/B identity evidence **before new B runs** so it is not lost. If exact model identity cannot be proven, record UNKNOWN and preserve that limitation; it does not authorize a false R6 PASS. Never ask for credentials in prompts or logs.

Preflight does not release itself: after evidence is submitted and accepted into main, only `C15-RCC-RES-B-RELEASE-001` becomes READY. That new independent PM pins the operator revision and safe packet, verifies no semantic shortcuts, verifies access boundaries and required mechanical checks, and releases one unique run ID/session with the frozen A handoff. Any setup edits invalidate the packet pin and require re-review.

### Fresh B and later acceptance

The fresh Resident receives only the separately approved safe instruction and mechanical packet. It must never receive this decision, the PM review, #121 reports, the task board, the checkpoint, or “what to do differently” guidance. It executes cursors 14–22 only and then stops; summaries and all semantic decisions come from the model, not the operator.

The operator may report **RUN_COMPLETE / AWAITING_INDEPENDENT_ACCEPTANCE**, never C15 PASS. Private run evidence remains external/evidence-only and must not enter main with source/governance. The independent acceptance task validates provenance, completeness and execution boundaries; R1–R9 semantic judgments remain reserved for `C15-RCC-EVAL-001`.

### Model identity gate

`C15-RCC-MODEL-ATTEST-001` must bind trustworthy platform/provider identity evidence to the relevant A/B and intended C run/session. A configured `model` string, model self-description, different window, or manually authored signature is not sufficient. If the execution environment cannot prove a different model family/provider, report `INSUFFICIENT_EVIDENCE`, do not release C as satisfying the replacement-model gate, and keep R6 non-VALID. Any alternate protocol needs a new ruling; no second identity database is authorized.

## 4. Deferred PM risks — not additional active work

- **CI-120:** run `35844880234` failed at zero-Core-diff proof, exit 128; preceding fixture/runtime/conversation checks succeeded. Exact failure root cause remains unconfirmed because full log retrieval failed. No blanket CI waiver. Integration of this corrective PR requires its own checks and review; a green new run does not erase the old failure. See risk register for later owner/task activation.
- **SCALE:** the open #112 report is not accepted scale evidence. Current Claim traversal is a risk to characterize later, not permission to refactor frozen cognition paths now.
- **TRACKING:** old open Issues/PRs are not authority to redo merged fixes or merge evidence branches. Preserve historical entries, but route only by the current top-of-board queue.

## 5. Scope and stopping condition

This window may record the PM review/decision, update navigation and status, prepare separated role prompts, publish the governance PR and annotate #121 without changing its head. It must stop before preflight implementation, Resident execution, C identity experimentation or C16 work.

No tests or Resident experiment are run locally in this governance task. Existing GitHub CI results and read-only raw-artifact queries are cited as such; newly triggered PR CI must be reported separately. Main completion is not claimed until the governance PR is actually merged.
