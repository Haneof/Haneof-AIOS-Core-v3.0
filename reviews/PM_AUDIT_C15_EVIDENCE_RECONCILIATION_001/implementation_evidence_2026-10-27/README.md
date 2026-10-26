# Implementation-side evidence packet — S1 native-tools protocol (2026-10-27)

## 这是什么

这是**实现方（implementer）**提交的证据包，供 `PM-AUDIT-C15-EVIDENCE-RECONCILIATION-001` 的
独立 Reviewer 消费。

## 这不是什么 — 三条硬边界，请勿混淆

1. **这不是独立复核结论。** 本目录下所有文字由实现方撰写，未经独立第三方复核。
   它不构成 `EVIDENCE_SUPPORTED` / `GAPS_CONFIRMED` 之类的 reviewer 裁决。
2. **实现方不自签。** 按治理要求，R1–R9 必须由独立 Reviewer 签署；实现方只负责让复核
   "可消费、可复现、可证伪"，不负责给出复核结论。
3. **不改动冻结物证。** `../BASELINE.json` 及其保护的 git 对象未被本包修改
   （scope 明确写着 `mutate_frozen_evidence: false`）。本包是**新增**文件，不覆盖历史。

## 目录

| 文件 | 内容 |
|---|---|
| [`S1_NATIVE_TOOLS_EVIDENCE.md`](S1_NATIVE_TOOLS_EVIDENCE.md) | 逐项证据：T05 / T06 / T07 / T08 / 接线 / T10，每项给 commit、代码位置、验证命令 |
| [`REPRODUCE.md`](REPRODUCE.md) | 一键复现命令与预期输出，含复现失败时的判读方式 |
| [`verify_native_tools_live.py`](verify_native_tools_live.py) | T10 真实端点取证脚本（原先只在 `/tmp`，现已入库以便复现） |
| [`OPEN_GAPS.md`](OPEN_GAPS.md) | 已知缺口与未核实项 —— Reviewer 应重点challenge 的部分 |

## 结论摘要（实现方主张，待独立复核）

- 根因是**协议不匹配**：provider 未向模型提供它被训练过的原生 `tools` 数组，而是要求模型
  在散文里手写 JSON 块。单变量对照下，同一份提示词换协议后模型第 1 轮即调用工具。
- 原生 tools 已端到端接线并在真实端点跑通（M1/M2/M3 三条硬指标 PASS）。
- T2' 抽取轮**降级为兜底**，不再承担主路径职责。
- 当前工程基线 `41f12c7`，发布姿态 `RELEASE_CANDIDATE`，升级到 FINAL_RELEASE 仍需
  独立 R1–R9 复核通过 + owner 授权。

## 声明

本包中每一项数值均附上产生它的命令。凡本包未能独立核实的事实，一律在
[`OPEN_GAPS.md`](OPEN_GAPS.md) 中显式标注，不以转述充当证据。
