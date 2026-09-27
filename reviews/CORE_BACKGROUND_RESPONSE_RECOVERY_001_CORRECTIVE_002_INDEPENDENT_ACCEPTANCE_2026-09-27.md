# CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE

Publication type: durable review evidence for a COMPLETED fresh Independent Acceptance.
This document publishes previously completed fresh Independent Acceptance evidence.
It does not modify or re-accept a new implementation candidate.

Task
`CORE-BACKGROUND-RESPONSE-RECOVERY-001-CORRECTIVE-002-INDEPENDENT-ACCEPTANCE`

Tested exact candidate
`227327c657788efb1b5de1bc26e69c35c900a85e`

Verdict
`ACCEPTANCE_PASS`

Blocker count
`0`

Final disposition
`READY_FOR_PM_INTEGRATION`

Independent reviewer 未 merge PR #219，未修改 candidate implementation。

«Independent Acceptance 的 PASS 只适用于该 exact implementation identity.»

---

## 1. Tested exact implementation identity

| object | value |
|---|---|
| tested exact candidate | `227327c657788efb1b5de1bc26e69c35c900a85e` |
| mandatory parent | `72aed7eddf22d0d7f05e53bb3bd46ed28554f7fc` (verified match) |
| tree | `01dfa445414543aab41e1b74b813bbff80b21c5c` (verified match) |
| PR | Haneof/Haneof-AIOS-Core-v3.0 #219 (OPEN / UNMERGED) |
| PR #219 head at acceptance and at publication | `227327c657788efb1b5de1bc26e69c35c900a85e` (no candidate drift) |

The PASS applies ONLY to this exact implementation identity (SHA + parent + tree).
Any later governance-only/evidence-only head is not a tested exact implementation
and must not be presented as re-accepted.

Delta of the candidate against its mandatory parent: 9 files (4 `src/**`,
5 `tests/**`), implementation only; frozen 12-probe byte-identical.

## 2. Exact environment (fresh IA's own formal environment)

- CPython `3.12.14`
- Pydantic `2.13.5`
- pytest `8.4.2`

Record: this was the environment the Independent Acceptance itself executed in
(built in the review sandbox and used for every run below), not merely a citation
of the PM CI gate (p16-convergence-gate run 36307032411 / job 108585586234).
See `CORE_BACKGROUND_RESPONSE_RECOVERY_001_CORRECTIVE_002_INDEPENDENT_ACCEPTANCE/environment.txt`.

## 3. Frozen 12-probe evidence

- Frozen authenticity probe SHA-256: `35cba59f318b752ed872821961296f35810443c61db6fd98c8c8f5eee4215225` — independently re-verified at publication time.
- Git blob: `6f0c3850368475e166d28d0a6df4b86b610d2c60` — identical at RED freeze (`a7678f9b…`), mandatory parent (`72aed7ed…`) and the tested exact candidate (`227327c…`).
- Result: `12/12 GREEN` (collected 12).

Declared:
- probe bytes 未修改；
- RED freeze 到 implementation exact 保持 byte-identical；
- reviewer 未通过改 expected outcome 获得 GREEN。

Raw execution log of the 12/12 run: `ARTIFACT_NOT_RECOVERABLE` (never captured to
file during the acceptance session); static hash/blob verification is durable
(`frozen-probe-verification.txt`), and the same frozen test file is included in
the preserved raw full-suite run.

## 4. Fresh adversarial suite evidence

Suite location (originals preserved verbatim, publication copies under
`.../INDEPENDENT_ACCEPTANCE/adversarial-rev1/` and `.../adversarial-rev2/`).

### Rev1 — `ABANDONED_WITH_RECORD / HARNESS_DEFECTS_ONLY`

- frozen then executed
- collected: `49`
- result: `40 passed / 9 failed`
- the 9 failures were finally classified as: `PROBE_HARNESS_DEFECT` (probe
  setup/API-signature/assertion-scope errors; source-revalidated before each
  classification — see `classification.md`)
- rev1 已废弃但保留历史；未删除；不描述为 implementation failure；原文件未被覆盖。

Rev1 combined manifest SHA-256: `eee5ba3307d06b735cd6e127f773787e7081a36389c859647ec83e5c5d18bc51`
(re-verified at publication: all 11 files match `probe_sha256_rev1.txt`).

### Rev2 — frozen and executed

- frozen manifest SHA-256 (combined): `8ebdce5dbe8bb10e3cc6210399279cc679393d9f70e5b5fd878f0f91f028874e`
  (re-verified at publication: all 11 files match `probe_sha256_rev2.txt`)
- collected: `49`
- execution result: `49/49 GREEN`

Persisted: probe files, SHA256 manifests (per-file + combined), collect-only
output, execution output, environment information. All published probe bytes are
the original frozen artifacts (matched against their manifests at publication);
no suite was regenerated to substitute for the originals.

## 5. Focused / full-suite evidence

| batch | command target | result |
|---|---|---|
| focused trusted-return/runtime/recovery | `test_background_model_attempt.py`, `test_cognitive_runtime_trusted_return.py`, `..._corrective_002_recovery.py` | `17 GREEN` |
| Core response recovery integration | `..._001.py`, `..._001_corrective_001.py` | `43 GREEN` |
| full suite | `pytest -q` | `763 passed in 252.50s` (Python 3.12.14) |

Original raw pytest outputs preserved: `full-suite.txt` (summary run) and
`full-suite-raw.txt`. Focused-batch raw console logs: `ARTIFACT_NOT_RECOVERABLE`
(see `focused.txt`); both batches are covered by the preserved full-suite raw run.

## 6. Key acceptance conclusions

### A. Proof forgeability — `CLOSED`
Without knowledge of the store-private authority secret, the external
staging/recovery caller cannot construct a trusted-return proof that Core accepts.
Tried and fail-closed: forged HMAC; arbitrary proof strings; the complete
Corrective-001 style self-consistent forged bundle (relay echo + self-consistent
directive bytes + self-computed fingerprint/payload hash + evidence) plus proof;
nested-field mutation with recomputed fingerprint; silence/terminal substitution;
byte-identical payload with mismatched claimed fingerprint/hash; missing proof.
All rejected before any downstream mutation (adversarial A1–A8).

### B. Exact payload binding — `CONFIRMED`
The receipt HMAC binds the exact payload SHA-256 in addition to full identity.
Failed attacks: response mutation; capability list mutation; capability argument
mutation (incl. nested values); provenance mutation; provider/model/request-id
mutation; semantically-equivalent-but-byte-different payload (non-canonical
re-encoding); mismatched claimed fingerprint/hash (A3–A7, B6).

### C. Cross-identity replay — `ALL REJECTED BEFORE DOWNSTREAM MUTATION`
cross-attempt (B1), cross-work (B2, B5, H1), cross-work-kind (B3), cross-subject
(B4), cross-round (B1), cross-provider/model/request identity (B6). Every replay
failed before staging/attempt mutation/metering/capability/output.

### D. Ordering — `CONFIRMED`
Trusted-return authentication runs before provenance recording, metering,
capability execution, output, and World effects. On authentication failure:
zero downstream mutation, zero metering, zero output, zero capability effect;
staging failures leave the durable state byte-identical (F1–F3). The trusted
receipt is durable before response-provenance recording (F3).

### E. Crash / restart — real subprocess + SIGKILL
All three crash-point scenarios executed with real `os.kill(SIGKILL)` subprocesses:
1. SIGKILL after receipt commit, before provenance recording: receipt durable
   across death; provenance/metering untouched at death; restart + external
   staging + recovery with **zero provider redispatch**; exact response recovered
   with byte-exact payload; **metering exactly once**; **output exactly once** (i1).
2. SIGKILL after durable staging, before application: recovery re-verifies the
   persisted proof and applies exactly once; a second recovery pass duplicates
   nothing (i2).
3. SIGKILL immediately after the first capability commit: replay produces the
   World effect **exactly once** (single task, still revision 1) and exactly one
   metering row for the recovered attempt (i3).
Author-side SIGKILL suites also GREEN (focused/integration batches).

### F. Durable tamper — `FAIL_CLOSED`
With full attacker write access to the runtime DB (minus the HMAC key row), each
tamper below was applied and then restart/recovery was attempted; every case
failed closed with zero World mutation, zero metering mutation, zero output
mutation: receipt proof; receipt payload SHA; receipt provider; receipt model;
receipt request ID; receipt attempt/work/subject/round binding (incl. outbound
fingerprint and relay id); staged proof; staged payload; staged payload SHA;
staged response fingerprint; attempt provenance (D1–D8).

### G. Authority lifecycle — `CONFIRMED`
- fresh DB authority creation: exactly one durable 256-bit key (E1)
- restart retains the same authority (E1)
- backup/restore preserves receipt validity (E5)
- missing authority fails closed; a re-initialized replacement key never
  validates old receipts (E3)
- invalid hex fails closed (E4)
- invalid length (short/long/empty) fails closed (E4)
- historical NULL-proof migration shape fails closed: old-schema staged rows
  remain unusable after the ALTER-added nullable column (D6)
- multiple runtime instances share the same durable store authority;
  cross-instance receipts verify (E2); concurrent initialization yields one row (E6)

### H. Historical blockers

| blocker | status |
|---|---|
| Historical IA-BLK-001 cross-work exact-response transplant | `CLOSED / NO REGRESSION` |
| Historical IA-BLK-002 recursive duplicate JSON semantic keys (last-key-wins) | `CLOSED / NO REGRESSION` (object_pairs_hook rejects duplicates recursively, incl. nested usage/provenance/capability-call/capability-argument objects) |
| Corrective-001 blocker: trusted provider-return exact-byte authenticity | `CLOSED` (durable HMAC receipt bound to exact bytes; staging/recovery re-verify the persisted proof) |

## 7. Residual trust-boundary limitation (preserved as-is)

«持有底层 trusted store/runtime 对象的进程内 trusted code 可以调用内部 receipt
minting path，或直接读取 SQLite 中保存的 HMAC authority secret。»

Ruling: `NON_BLOCKING TRUST-ROOT LIMITATION`

Reasons:
- store 本身属于 trusted runtime boundary；
- external staging/recovery/reconcile public boundary 不暴露 secret（receipt reader
  只输出可复制 proof，不输出 key；无 getter/serialization/repr/exception/evidence/
  log/model-input 泄漏路径）；
- 无 key durable tamper 已验证 fail closed；
- backup/restore 可继续验证原 receipt，本身要求 authority 与 durable store 一起迁移。

This limitation is recorded exactly as characterized; it is not deleted, not
described as "absolutely no key access path exists", and not escalated to a
blocker without new exploit evidence.

## 8. Repository mutation scope (this publication)

- review/evidence content only, under `reviews/**`
- zero `src/**` changes; zero candidate-test changes; zero frozen 12-probe changes
- PR #219 implementation branch (`arena/01a0dcf6-haneof-aios-core-v3-0`) untouched
- evidence published from the Arena-pinned review session branch
  `arena/01a0e211-haneof-aios-core-v3-0` (instead of a `review/...-20260927`
  named branch, because this session is pinned to that branch name)

## 9. Disposition

`READY_FOR_PM_INTEGRATION`

PR #219 仍未 merge；其 merge conflict 不属于本窗口处理范围。下一步应进入独立的
integration-conflict-resolution / PM integration preparation，不得直接进入
CORE-RC-REFREEZE-002。
