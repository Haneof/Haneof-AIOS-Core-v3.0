# 十项 Core 修复：主干集成与最终软件验收

**结果：已完成本次十项 BUG 的主干集成及合入后软件验收，不是候选交付。**

- 用户明确授权本窗口集成 main，同时保留其他工作，不合入 PR125/126 的组合链。
- 独立 PR：[#127](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/pull/127)，已于 2026-09-24T02:23:29Z 合并。
- 实际 main SHA：`6924d8b50cf08eb632f9cfa513a3cc49faad0c72`。
- 合并父提交：原 main `849bfd41c623fb336b392a3e6e933cfad93620e9`、候选 `ba3ed05ec751f80b890aed2dfc2be12ec80d597d`。
- main 完整文件树与已审查候选完全一致。相对旧 main，仅原修复 17 文件和独立验证 10 文件改变。
  其中功能范围仍是 12 Core 文件 + 1 个专项测试文件，其余为证据；无 operator 代码、fixture、共享工作流或冻结锚点修改。

## 在实际 main SHA 上重新执行

合并后重新 fetch，直接从 main 的上述 SHA 导出 132 个 Python/config 文件到独立非 Git 目录，
没有复用候选导出目录；未导出仓库 fixture 数据。Python 3.12.11 / pytest 8.4.2 /
pydantic 2.13.5 / SQLite 3.40.1。

| 合入后本地范围 | 结果 |
|---|---:|
| Core unit/runtime/integration | 409 passed，0 failure/error/skip |
| 十项 BUG 专项（包含于 Core） | 42 passed，0 failure/error/skip |
| 默认测试 collection | 501 |
| 允许执行的公开合成测试（含 Core + 83 habitation） | 492 passed，0 failure/error/skip |
| 仓库 fixture 依赖项 | 9 项明确排除，未在本地执行 |

公开合成执行使用 main 内的哈希校验脚本；前后逐文件哈希相同；collection 与实际执行集合精确比对。
9 项排除与前轮边界一致，完整 node ID 在 manifest。没有把 492 声称为本地默认全量通过。
每个 BUG 的归属通过数：A01=4、A02=1、A03=3、A04=9、A05=4、A06=2、A07=13、A08=1、A09=5、A10=2。
这是 42 个独立用例、44 次 BUG 归属（两个用例联合覆盖 A01/A03），不重复累计测试总数。

## 实际 main 的 GitHub CI

- 合并前 PR127：42/42 checks SUCCESS。
- 合并后 main 上述 SHA：**23/23 workflows、46/46 checks SUCCESS**。
- [默认完整回归 workflow](https://github.com/Haneof/Haneof-AIOS-Core-v3.0/actions/runs/35947043535)：
  job `107467211750` 的 `Run full AIOS Core and P16 regression suite` 成功，workflow 原命令为 `pytest -q`，未修改。
- 核对的是 main 的 push 运行及实际 SHA，不是 PR 的临时 merge ref。
- CI 日志压缩包下载遇到 EOF，API 元数据和步骤状态均已核对；**不虚构 CI 的精确测试条数**。
  本地精确计数由随附 JUnit 和 collection 独立证明。

## 保全与边界

- PR125 仍 OPEN、base main。本轮开始其 head 为 `996638c90a0b167a228c90cb5020b0ebbe0643da`，
  最终复查已由外部工作推进至 `d2058bfc1f089d743aea3c323f1c91c4ba7e85ff`；本窗口未写入、未覆盖或合并该分支。
- PR126 仍 OPEN，head `8e31deca02a5062d7bb9ffe6dd840abbaaf6970e`，原 base 不变。
- 两者的分支、PR 内容和组合证据未被本窗口修改；未改共享 CI、canonical anchor 或 `audit.verify_core`。
- 本地未提交的动画及原审计目录保持原状，没有读取动画内容。
- 正式隔离、真实 A/B/C 仍 NOT_TESTED；Resident BLOCKED、launchable=false，不是 Resident 上线批准。
- 本验收记录是合并后的旁证，保存于本会话分支并在 PR127 留言；不为写入自身而再改变已验收 main SHA。

`source-export.json` 记录完整树、Core 树、测试 blob、132 文件 SHA-256 和全部变更路径；
`core.xml`、`bugs.xml`、`public.xml` 为这次合入后的新结果；CI 与 PR 状态也随附。
前轮历史证据原样保留，不把历史“未合入”的记录改写为当时已完成。
