【新开任务窗口：28】

Formal task：

`CORE-RC-REFREEZE-004-CORRECTIVE-002`

Repository：

`Haneof/Haneof-AIOS-Core-v3.0`

WINDOW：

`28`

你的角色：

**RC Freeze Gate Corrective Engineer**

你不是：

- PM
- Independent Acceptance Reviewer
- Core product corrective engineer
- C15 persistence/operator corrective engineer
- Resident A / B / C
- evaluator
- public release operator
- UI / hardware engineer

你的唯一任务：

> 修复 Window 27 Fresh Independent Acceptance 已确认、PM 已裁定为 BINDING 的两个剩余 RC freeze formal-gate blocker：IA27-BLK-001 与 IA27-BLK-002。

本轮不是重新做 RC freeze，也不是修 frozen Core。

完成后只能停在：

`REVIEW_READY`
`READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE`
`DO NOT MERGE`

不得自验收。
不得 merge。

==================================================
0. Fresh remote ground truth
==================================================

开始必须：

`git fetch --all --prune`

通过 GitHub API / git fresh verify：

- live main
- PR #325
- PR #328
- PR #330
- PR #332
- PR #333
- task board
- checkpoint
- Window 25 PM adjudication
- Window 27 release contract
- Window 27 final evidence
- Window 27 PM adjudication

PM adjudication 时 main：

`5fc78a84d0cf1ccdfe0185ba2cc2f8c7fdeff5c4`

不要把这个 SHA 当永久基线。

必须 fresh 获取。

读取并确认：

`CORE-RC-REFREEZE-004-CORRECTIVE-002 = READY`

==================================================
1. Failed candidate — immutable
==================================================

Window 26 / Window 27 failed Corrective-001 candidate：

PR #330

branch：

`release/core-rc-refreeze-004-corrective-001-window26`

exact head：

`2380121639865b1bd29176cf944f5a20afe4112d`

parent：

`04c37f7dd8ba6f20e1c67dad43c0f21087f51eeb`

tree：

`72d3cd0da849fae3b1cbfdfb7ae995528e1cfd71`

必须保持：

`OPEN / UNMERGED / DO NOT MERGE`

禁止：

- 在 #330 branch 上继续施工
- amend
- rebase
- squash
- force-push
- rewrite
- merge #330

必须从 exact failed head `23801216...` 创建一个新的 corrective branch。

推荐：

`release/core-rc-refreeze-004-corrective-002-window28`

必须 append-only。

==================================================
2. Window 27 review evidence
==================================================

Canonical final Window 27 evidence：

PR #333

`REVIEW_ONLY / DO NOT MERGE`

publication head：

`6e63505175aca3114592a40dd01b1d8bfb95c01f`

tree：

`3a782cd4239404017d16fb5399ce19157f94b341`

verdict：

`ACCEPTANCE_FAIL / blocker=2`

Binding：

`IA27-BLK-001`
`IA27-BLK-002`

Secondary corroborating review：

PR #332

`REVIEW_ONLY / DO NOT MERGE`

head：

`4b3db8d9f60a2374ed5b7deaca707d185cf1157f`

tree：

`1e177efb19eecdce71781279b1ddd64231a8c86c`

PR #332 independently corroborates TOCTOU only.

不得修改 #332 / #333 evidence。

==================================================
3. Frozen software MUST NOT CHANGE
==================================================

Frozen software remains：

`1cee3c5ad12f4b9098232bae11b51df786c5eb2f`

Required immutable identities：

root tree：
`70b2711258567863ea0d93025a6a07e39631726a`

Core tree：
`16f1487e291b009c55bee402abfd79fdacbae960`

tests tree：
`9db1bfa08143bc99fe03836e2752ee6e05694eb6`

frozen workflows tree：
`72cde9d2dc2b35d071bfa36c954dac2faff4a803`

pyproject blob：
`b38833c7537fa60d5c2f02ed4bb19158d8995a11`

不得修改：

`src/**`

产品 `tests/**`

`tools/**`

`pyproject.toml`

C15 implementation

Resident state/evidence

==================================================
4. Corrective-002 strict scope
==================================================

允许修改：

`.github/workflows/core-rc-refreeze-004-formal-gate.yml`

允许新增：

`reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/**`

默认禁止修改历史：

`reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001/**`

因为它是 failed candidate historical evidence。

如果需要新的 classifier/helper：

放在：

`reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/probes/**`

并让 workflow 使用新 helper。

不要覆盖 Corrective-001 helper。

==================================================
5. RED-FIRST
==================================================

施工前必须 fresh reproduce 两个 blocker。

禁止只复制 Window 27 report。

--------------------------------
IA27-BLK-001
--------------------------------

从 canonical Window 27 PR #333 exact review commit fresh extract：

`reviews/CORE_RC_REFREEZE_004_CORRECTIVE_001_INDEPENDENT_ACCEPTANCE_WINDOW_27/reviewer_junit_fuzz.py`

expected git blob：

`d734f7dcaf7a72f35dee859181fb1789e12066a2`

必须 fresh hash/pin。

在 failed candidate `23801216...` 上运行并证明至少以下 false-accept 仍存在：

- namespaced rc0 hidden structured failure
- summary zero + failing testcase
- failure + error on same testcase
- `tests/c15_persistence/../integration/test_core.py`
- classname-only spoof
- file/classname conflict

保留原始 RED。

--------------------------------
IA27-BLK-002
--------------------------------

从 PR #333 fresh extract：

`reviewer_toctou_probe.py`

expected git blob：

`dfdc91aa76555913e1713a4d0a38e0686e54446f`

并读取 PR #332 real GitHub control run：

`37262331480`

必须机械确认 failed candidate：

terminal equality 之后 branch drift，

old run 仍可以：

- Job A SUCCESS
- publisher SUCCESS
- overall SUCCESS

保留 RED。

==================================================
6. IA27-BLK-001 repair contract
==================================================

Corrective-002 classifier 必须 fail-closed。

不得继续使用：

`raw string startswith("tests/c15_persistence/")`

作为 authoritative mapping。

必须解决：

1. XML namespace ambiguity
2. path canonicalization
3. `..` traversal
4. absolute path
5. file/classname identity conflict
6. classname-only spoof / ambiguous identity
7. summary counter inconsistency
8. testcase 同时 failure + error
9. nested/duplicate suite ambiguity
10. malformed/noninteger counters
11. setup/collection-like unmappable structured error
12. multiple downstream + one non-downstream

推荐但不强制具体实现：

- 定义一个严格、可机械验证的 pytest-JUnit profile；
- 对 XML tag 使用 namespace-aware / explicit local-name handling，或直接拒绝非允许 namespace；
- 路径做 canonical lexical validation；
- 任何 `..` component / absolute path / ambiguous separator 直接 reject；
- file 与 classname 同时存在时，两者必须一致地证明 downstream identity；
- file 缺失时，不得仅凭“看起来 downstream 的 classname”无条件接受；
- 可使用 fresh `pytest --collect-only` 生成 authoritative downstream test identity inventory，再将 JUnit testcase identity 绑定到该 inventory；
- 允许改变 JUnit family/profile，只要 formal path 与 reviewer adversarial cases 都机械 fail-closed。

关键要求：

Window 27 canonical 35-case fuzz matrix必须：

`0 false accepts`

作者不能把六个已确认 case 重新定义为“out of contract”。

真实：

`tests/c15_persistence/**`

仍应在普通 rc=1 + downstream-only failures 时得到：

`C15_OPERATOR_ADAPTATION_REQUIRED_BEFORE_RESIDENT`

不得为了 GREEN 去修 C15。

==================================================
7. JUnit structural consistency
==================================================

至少机械保证：

- rc=0：
  - structured failure count = 0
  - structured error count = 0
  - declared counters必须一致

- rc=1：
  - 至少一个 structured failure/error
  - 每个 structured failure/error 必须 canonical + unambiguous downstream
  - aggregate/declaration 与 observed structured elements 必须一致

以下必须拒绝：

- namespaced hidden failure
- declared 0 / observed failure
- declared failure / no failure testcase
- failure + error same testcase
- duplicate/nested contradictory counters
- unknown/unmappable testcase
- path traversal
- conflicting file/classname

==================================================
8. IA27-BLK-002 repair contract
==================================================

目标不是“再加一个 terminal grep”。

Binding property：

> 如果 canonical candidate branch 在 formal validity/publication 完成之前发生任何 head drift，旧 candidate run 不得仍被视为 overall-successful canonical formal evidence。

必须关闭：

Job A terminal check → artifact upload → Job A completion → Job B publisher → overall completion

之间的 race。

允许重新设计 workflow mechanics，但不得改 frozen software。

可考虑组合：

- canonical-branch push concurrency with `cancel-in-progress:true`;
- publisher-side fresh canonical remote-head check;
- publisher publication 前后 identity check;
- 将 final validity/pin publication放到能够观察 formal run completed state 的独立 post-run workflow；
- 其他能被真实 race control 机械证明的设计。

不要仅靠静态字符串证明。

==================================================
9. Real GitHub TOCTOU closure test — mandatory
==================================================

必须创建 disposable control branch/workflow，真实复现 race。

至少测试：

A. branch 不漂移：
- current run succeeds
- exact pin succeeds

B. terminal check 后 / artifact 前漂移

C. artifact 后 / Job A completion 前漂移

D. Job A completion后 / publisher 前漂移

E. publisher过程中漂移

对于 B-E：

旧 SHA 不得同时获得：

`overall SUCCESS + valid mandatory exact pin`

如果 implementation 采用 cancellation：

旧 run 必须 canceled/fail，不能 SUCCESS。

如果 implementation 采用 post-run pin validator：

stale run 可以机械测试完，但必须没有 valid canonical pin，且 RC acceptance logic 必须要求 post-run validator success。

必须 durable 记录真实 GitHub run ids、old SHA、new SHA、结论。

==================================================
10. Preserve already-closed credential property
==================================================

不得回归：

Job A：

`contents: read`

checkout：

`persist-credentials:false`

candidate-controlled execution不得获得 write token。

如果设计新增 workflow/job：

任何执行 candidate/repository-owned code 的 job必须 read-only。

write-capable publisher/validator：

- no checkout
- no candidate code
- no candidate helper
- no repository sourced script

==================================================
11. Preserve IA25-BLK-003 closure
==================================================

Mandatory publisher仍必须：

HTTP 201 only success。

以下必须 nonzero：

200 / 202 / 204 / 301 / 302 / 400 / 401 / 403 / 404 / 409 / 422 / 429 / 500

curl transport failure必须 nonzero。

不得恢复：

`test "$code" = "201" || cat response`

型吞错。

==================================================
12. Formal gate success semantics
==================================================

最终 canonical acceptance evidence 必须机械绑定：

- exact candidate SHA
- canonical branch
- frozen software SHA
- exact formal run
- exact current branch head
- successful gate
- successful mandatory pin/validator

任何 stale-run identity必须不可被当成 READY。

==================================================
13. Carry-forward full RC gate
==================================================

Final exact candidate必须 fresh 重跑：

- Full Core：0 fail / 0 error
- W20 Suite A：4/0
- W20 Suite B：7/0
- W17：14/0
- Corrective-003 security
- real SIGKILL/fresh process
- clean non-editable wheel/headless
- backup/restore/rebuild
- writer/restart
- FIX-001/002/003
- current-time
- SCALE
- real C15 downstream suite with corrected classifier
- open-PR contamination
- frozen identities
- protected drift
- credential isolation
- TOCTOU real controls
- publisher failure controls

不得只跑 workflow unit tests。

==================================================
14. Formal environment
==================================================

必须：

CPython `3.12.14`

Pydantic `2.13.5`

pytest `8.4.2`

记录：

SQLite
OpenSSL
OS
kernel
architecture
Python executable
`aios_core.__file__`

==================================================
15. Corrective-002 evidence
==================================================

新增：

`reviews/CORE_RC_REFREEZE_004_CORRECTIVE_002/**`

至少：

- GROUND_TRUTH.md
- FAILED_CANDIDATE_IDENTITY.md
- WINDOW27_REVIEW_IDENTITY.md
- RED_FIRST.md
- BLK001_JUNIT_FAIL_CLOSED_REPAIR.md
- BLK002_WHOLE_RUN_IMMUTABILITY_REPAIR.md
- CARRY_FORWARD_CLOSED_PROPERTIES.md
- WORKFLOW_SECURITY_AUDIT.md
- TOCTOU_REAL_CONTROL.md
- SCOPE_AUDIT.md
- FORMAL_CI_RESULTS.md
- FINAL_HANDOFF.md
- probes/**
- raw/**
- SHA256SUMS

==================================================
16. New candidate
==================================================

禁止 reuse PR #330。

必须新 branch / 新 PR。

推荐 branch：

`release/core-rc-refreeze-004-corrective-002-window28`

新 PR：

`OPEN / non-draft / UNMERGED / DO NOT MERGE`

PR body必须关联：

- failed #330
- canonical Window 27 review #333
- corroborating #332
- IA27-BLK-001 closure
- IA27-BLK-002 closure

并明确：

`NO CORE IMPLEMENTATION CHANGE`
`NO C15 IMPLEMENTATION CHANGE`
`NO RESIDENT`

==================================================
17. Final exact-head discipline
==================================================

所有 tracked evidence必须在 final formal CI 前 commit。

然后冻结 exact head。

跑 hosted formal。

formal完成后禁止再做 evidence-only commit。

post-run receipts只能通过：

PR body / comment / external pin

不得移动 candidate head。

必须最终证明：

local head
remote branch head
PR head
formal run head
validity/pin head

全部 exact。

==================================================
18. Prohibited
==================================================

严格禁止：

修改 #330
merge #330
修改 #332/#333
merge review PR
修 frozen Core
修 C15 implementation
恢复 local self-trust
Independent Acceptance
PM Integration
Resident A/B/C
evaluator
public release/tag
UI/hardware

==================================================
19. Exit
==================================================

只有两个 binding blocker都关闭，

且 full RC gate / real race controls / exact pin全部通过，

才能输出：

`CORE-RC-REFREEZE-004-CORRECTIVE-002 = REVIEW_READY`

`READY_FOR_FRESH_INDEPENDENT_ACCEPTANCE`

`DO NOT MERGE`

必须报告：

fresh main
failed #330 identity
Window27 #333 identity
#332 corroborating identity
new branch/PR
new head/parent/tree
scope diff
BLK001 RED→GREEN
35-case fuzz 0 false accepts
real C15 classifier result
BLK002 RED→GREEN
real GitHub TOCTOU control run ids/results
credential model
publisher model
closed-property regression
full RC results
formal environment
artifact
external validity pin
candidate drift check

然后停止。

不得自验收。
不得 merge。
