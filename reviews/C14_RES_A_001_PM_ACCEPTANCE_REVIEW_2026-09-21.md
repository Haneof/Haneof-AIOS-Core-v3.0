# C14-RES-A-001 Independent PM Acceptance Review

> Date: 2026-09-21  
> Verdict: **PASS**  
> Evaluated main: `87e52bceea4ee94b823200388a4f79b1b94eb1f3`  
> Evidence PR: #75  
> Evidence head: `cb9b56b7039272d932158f33bfe979eff6749c9b`  
> Evidence branch: `arena/01a0c473-haneof-aios-core-v3-0`

## 1. Independent evidence verification

PM independently verified the evidence at the exact PR head rather than relying on the Resident's final report.

Observed facts:

- PR #75 is evidence-only and remains unmerged.
- Diff from evaluated main contains no `src/aios_core/**` changes and no governance changes.
- Git history is sequential: setup, cursor 1 through cursor 24, handoff freeze, then one docs-only report-format patch.
- Release state contains exactly 24 receipts with sequences 1..24 and event ids `c14resv2-001..024`.
- Final release state is Phase A with `last_acked_sequence=24`, `next_sequence=25`, and `pending_reveal=null`.
- No Phase-B event id `c14resv2-025..036` appears in the PR diff.
- No Resident-visible Phase-B design content was found in the PR diff.
- Final World reports revision 166, index watermark 166, index lag 0, pending wakes 0, 24 fixture Observations, and 43 Summaries.
- The exact PR head workflow run `35622456805` completed successfully on `cb9b56b...`.

## 2. Actual Resident semantics

The checkpoint bridge is mechanical. It serializes exact `RuntimeSnapshot` and `DimensionSummaryInput`, waits for Resident-written files, executes the exact requested capability calls, and persists results.

Independent review found no:

- keyword-to-cognition mapping;
- occurrence-count program rule;
- automatic search target selection;
- generated Claim text;
- generated Summary text;
- pseudo-LLM;
- batch future directives.

The Resident made semantic choices checkpoint-by-checkpoint.

## 3. Positive cross-dimensional cognition

At the first durable cognition write, the Resident did not convert a Summary directly into a Claim.

The Resident first executed normal read capabilities across multiple dimensions, including:

- `dim:work_outcome`;
- `dim:schedule`;
- `dim:device_activity`;
- `dim:conversation`.

It then created one cautious hypothesis Claim grounded in nine pinned Observation revisions, not Summary refs.

The Claim remained hypothesis-level with confidence 0.5 and expressed an association/conditional interpretation rather than claiming universal causation or personality.

This satisfies the Phase-A requirement that durable cognition emerge from inspected cross-dimensional reality evidence rather than Summary-only self-proof.

## 4. Revision and mixed-lineage handling

A later C14 opportunity contained both AI-cognition-derived and new reality-derived material.

The RuntimeSnapshot showed:

- MIXED lineage for the AI-cognition-containing member;
- REALITY lineage for the new user observation;
- exact non-Summary grounding leaves;
- no unresolved provenance;
- `summary_is_semantic_conclusion=false`;
- `summary_is_sufficient_evidence_by_itself=false`.

The Resident revised the existing Claim to revision 2 using a new EvidenceSet containing ten pinned Observation refs.

This is accepted as evidence-grounded revision, not AI self-confirmation.

## 5. Matched negative / silence behavior

The Resident repeatedly declined to create cognition when evidence was insufficient.

Notably, the repeated sleep/early-wake line remained without a durable Claim, and later counter-context caused the Resident to discard a tentative narrow sleep pattern rather than promote it.

This is materially different from deterministic `N occurrences -> trait/preference` behavior.

Silence operated as a real outcome, not as an error path.

## 6. Qualification before handoff

The final collaborative-work facts were persisted at cursors 22..24.

No due C14 opportunity existed after the final cursor because the relevant summary window had not closed. The Resident did not force a Claim revision merely to satisfy the test.

That behavior is accepted. The new facts remain durable for the fresh Resident-B runtime.

## 7. Fresh handoff

Accepted handoff facts:

- World SHA256: `sha256:0ee338aa8f2845bb376610da3c450e09ff9cc8bec5184ca60608b2465d7ba72f`
- release-state SHA256: `sha256:e922d268fbb11364a7bb558aed60b88e7a3c075032f4fa4e1c47a84de3f765f1`
- semantic-trace SHA256: `sha256:16f9ae3bf8316b7ea1bf560c3da572a42ff550d909746d0db7fe8abbdaac3eb8`
- manifest SHA256: `sha256:2da4d5ab4113ef36d736fa64f21013f36110d28190a092abb57074bdbaf13853`
- current durable cognition: one Claim at revision 2
- cursor 25 not revealed.

Resident B must receive the exact pinned World/release-state artifacts, not a prose explanation of the cognition.

## 8. Non-blocking provenance/environment notes

Two limitations are recorded but do not invalidate Phase-A semantic evidence:

1. The Arena environment used Python 3.11.2 while `pyproject.toml` declares `requires-python >=3.12`. The Resident disclosed this rather than hiding it. The exercised Core path completed coherently and no divergence was observed. Resident B should use Python 3.12+ when available.
2. The Resident declared itself GPT-5.6 Sol, but the platform did not expose a signed provider/session model identifier. Therefore exact model identity is not independently attested by repository evidence. This does not invalidate the proof that a real external Resident window made checkpoint decisions, but cross-model claims must not rely on the declared string alone.

## 9. Decision

`C14-RES-A-001 = PASS`.

The evidence PR should remain pinned by exact head SHA for now rather than being merged into main. This avoids unnecessarily placing the private World DB and the Resident's full semantic trace on the ordinary runtime branch and keeps Resident B blind to Phase-A prose evidence.

Resident B may not yet start. PM found a narrow Phase-B test-infrastructure issue: the blind fixture adapter persists conversation events as fixture Observations, while constitutional `FusedTurnRuntime.run_turn` separately persists the current user utterance as the canonical conversation Observation. Naively using both would duplicate the same user utterance in World and could distort later evidence.

A narrow preflight task must close that transport boundary without changing Core semantics or fixture content.
