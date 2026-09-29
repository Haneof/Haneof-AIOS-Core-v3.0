# Revision 3 — additions and result

Revision 3 = revision 2 sources plus one new probe required by the task text §7(c)
("concurrent distinct publication self-consistency — stale-prefix ID computed outside
the lock"). No revision-2 expectation was changed; the revision-2 result (49/49) remains
valid evidence for the unchanged probes.

- New probe: `test_ra01_stale_prefix_identity_outside_lock_fails_closed`.
  Two processes derive a request identity from the same empty prefix (sequence 1) for
  *different* bodies and publish concurrently with those explicit identities. Contract
  expectation: exactly one dispatch; the loser fails closed — no artifact file and no
  ledger record under its stale identity; durable bytes are the winner's exact bytes.
- Sources: `probes_v3/` (50 probes); freeze `probes_v3/REVIEWER_PROBE_FREEZE_v3.json`
  (enumeration sha `fdad15300e65e069eea365dfdd3af8e3a2f0a3fe3fdc2d43ef5ddef440730ad9`,
  source hash-list sha `0d299c288169e27a9068c15e9cbd3a2e8da372f6c815e640b84695c235c1db29`).
- Result: **50 passed / 0 failed, rc=0, 153.50 s** (`raw/reviewer_probes_v3.raw.txt`).
- Collected enumeration identical to the frozen enumeration (50 IDs,
  `raw/reviewer_probes_v3_enumeration.diff` empty).
- Post-run source hashes identical to the frozen hashes
  (`raw/reviewer_probes_v3_integrity.json`).

## Freeze/commit ordering disclosure (revisions 2 and 3)

The binding rule is that expectations are frozen — and can be shown not to have been
tuned — before any candidate behavior is observed:

| Revision | Freeze artifact written | First execution | Freeze file committed |
| --- | --- | --- | --- |
| 1 (`probes/`) | before | before | **before** (`d0d893c`) |
| 2 (`probes_v2/`) | 10:30:0x (before) | 10:31–10:32 | after (`b83d5ee`), with the raw results |
| 3 (`probes_v3/`) | 10:36:41 (before) | 10:37–10:39 | after (this publication), with the raw results |

For revisions 2 and 3 the freeze artifact existed on disk (with its recorded
`frozen_utc` and file mtime) before the first execution, and the post-run source hashes
are byte-identical to the frozen hashes, which is the auditable proof that no
expectation was changed after candidate behavior was seen. The commit ordering for
revisions 2 and 3 is disclosed here rather than claimed to have been ideal.
