# C15-RCC-RES-B-RERUN-002 — State-Loss PM Adjudication

Date: 2026-09-26
Repository: `Haneof/Haneof-AIOS-Core-v3.0`
Reviewed live main: `762d06f628be3665212e034551707005a978bd8a`
Operator incident branch/head: `arena/01a0dc7b-haneof-aios-core-v3-0@eb02f2d215def60164dbff499399b6c96b4e0fbe`

## Verdict

`C15-RCC-RES-B-RERUN-002 = FAILED / INFRASTRUCTURE_STATE_LOSS / NON-CANONICAL`

This is not a semantic Resident failure and not a Core regression verdict.

The released B run was genuinely consumed through cursor-14 reveal, binding, ingest and one production provider dispatch. The canonical run root was then destroyed by the execution platform before any Resident semantic reply, capability execution or durable ACK. Because the live World/release-state/current-event/binding/projection/mailbox archive and possible in-flight World tail are unrecoverable, the exact consumed run cannot be continued or reconstructed with admissible evidence.

## Facts accepted

The operator report establishes:

- exact released run/session were used:
  - `c15-rcc-res-b-rerun-002-65e6e826`
  - `c15-rcc-res-b-session-002-65e6e826`
- pre-run audit was pristine;
- frozen software/Core/A-lineage/environment pins passed;
- sandbox isolation and frozen 158/158 E2E passed;
- cursor 14 was revealed as `c15rcc-014`;
- immutable projection and binding receipt were created and verified;
- ingest committed `obs_c14_fixture_4c492ea152d135960e96c2d1@1`, reaching World revision 99;
- production model work produced request id `50746053bb76440972803d3a9c572fd7`;
- no Resident semantic reply was received;
- no capability was executed;
- no durable ACK occurred;
- the cursor did not advance beyond 14;
- platform restart destroyed the entire canonical `/tmp` run root;
- the exact post-dispatch World tail cannot now be proven.

The operator correctly stopped without rewind/replay.

## Ruling 1 — no replay under RERUN-002

Deterministic reconstruction from canonical A lineage is NOT authorized as continuation of `B-RERUN-002`.

Even though no Resident semantic reply occurred, irreversible run events did occur and the exact post-ingest/post-dispatch bytes are unavailable. Replaying lineage -> init -> reveal -> ingest would create a new execution while falsely retaining the consumed run identity.

The following identity pair is permanently retired and MUST NOT be used again:

- run: `c15-rcc-res-b-rerun-002-65e6e826`
- session: `c15-rcc-res-b-session-002-65e6e826`

The outstanding request id/digest from the failed run is historical evidence only and MUST NOT be answered or re-injected.

## Ruling 2 — canonical A remains valid

No Resident B semantic reply entered the World, no capability was executed, and no B ACK completed. Therefore this incident does not mutate or supersede canonical Phase-A evidence.

PR #205 at exact head `d17ae972ad1d312735c355f775ac024bc4cebdf7` remains the only canonical A handoff.

A future B run may start again from that accepted A boundary, but only as a newly released run/session after the persistence corrective below is accepted.

## Ruling 3 — persistence corrective required before any new B release

New unique READY task:

`C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001`

Scope is operator/release persistence only.

It MUST NOT:
- run a real Resident B;
- reveal the real cursor 14;
- modify `src/aios_core/**`;
- modify the sealed fixture;
- modify PR #205 evidence;
- change Resident cognition semantics or expected answers;
- reuse the retired RERUN-002 run/session/request identities.

It MUST close the concrete infrastructure defect exposed here: the authoritative live run state and required evidence must not exist only on an ephemeral `/tmp` filesystem.

## Corrective acceptance contract

The corrective candidate must provide and mechanically prove all of the following using disposable/synthetic state only:

1. **Non-ephemeral authoritative storage**
   - exact backend/path is named;
   - not `/tmp`, `/var/tmp`, tmpfs, or another platform-ephemeral mount;
   - authoritative World/index/release-state/current-event/binding/projection evidence survive operator process death and environment re-attachment as defined by the execution platform.

2. **Durable cursor barrier before model exposure**
   After reveal/binding/ingest and before a provider request may be relayed to the Resident, the exact recoverable cursor state must be durably checkpointed and digested.

3. **Durable provider relay journal**
   At minimum preserve:
   - cursor/event identity;
   - round;
   - request_id;
   - nonce/request digest/binding digest;
   - exact provider request bytes;
   - relay state such as staged/exposed/reply-staged/applied;
   - exact reply bytes before application.
   Recovery must never fabricate, silently duplicate, or semantically rewrite a Resident reply.

4. **Exactly-once recovery proof**
   Kill/restart probes must cover at least:
   - after reveal but before ingest;
   - after ingest but before provider dispatch;
   - after provider request durably staged but before Resident reply;
   - after reply durably staged but before application;
   - after model/capability work but before ACK.
   Each recovery must converge to the same durable cursor without second reveal, duplicate ingest, duplicate semantic application, or skipped ACK.

5. **Evidence persistence**
   Required projection/binding/mailbox/failure evidence must survive the same failure class. A run cannot depend on transient process-local files for later independent acceptance.

6. **No semantic shortcut**
   Scripts may transport and recover bytes only. They may not choose Resident actions, infer answers, reconstruct lost semantic replies, or substitute fixtures.

7. **Fresh frozen regression**
   The accepted 158-check preflight/E2E and all relevant lifecycle mutation-red probes must remain green, plus new persistence/recovery probes.

## Sequence after corrective

- `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001 = READY`
- `C15-RCC-RES-B-PERSISTENCE-CORRECTIVE-001-INDEPENDENT-ACCEPTANCE = BLOCKED`
- `C15-RCC-RES-B-RELEASE-003 = BLOCKED`
- `C15-RCC-RES-B-RERUN-003 = BLOCKED`
- `C15-RCC-RES-B-ACCEPT-003 = BLOCKED`
- Resident C / evaluator / close / C16 / broad P16 / P17 remain BLOCKED.

Only RELEASE-003 may mint the new exact B run/session identity after the corrective is independently accepted. RELEASE-003 must revalidate the same frozen software/Core/A-lineage and produce a new Resident-safe launch. No identity is minted by this adjudication.

## Historical preservation

The failed RERUN-002 operator report is preserved unchanged at:

`reviews/internal_habitation/c15-rcc/v1/resident/C15-RCC-RES-B-RERUN-002/OPERATOR_STOP_RUN_STATE_TOUCHED_2026-09-26.md`

The incident is not rewritten into a pass and is not deleted after the corrective succeeds.
