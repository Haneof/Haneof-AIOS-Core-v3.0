# Session Memory Anchor — updated 2026-09-21 (post segment_001)

## State: SEGMENT_001 完成并已冻结推送
- Live run 全绿:63/63 events, world rev 166, clock 7/14T15:45Z, verify+decoy PASS, commit `f37c0cf` 已 push(分支 arena/01a0c1e0-haneof-aios-core-v3-0)。
- 报告:`REPORT_arena-cy-p16-001.md`(首轮冻结稿;含 F-001..F-014、INC-01/02、RESTART1/2、年度最小量对照、护栏实测表)。
- 无存活进程。io/ 为 restart2 后编号(seq 1–29);restart1 前 34 个决策在 `io/archive_r1/`,restart1 现场在 `io/archive_r2/`(含 error.json)。trace.jsonl 的 decision_sha256 链为唯一权威。

## 续跑入口(segment_002 待用户指令)
- 世界继承点:她 7/14 进山半月无信号;渡=waiting_result(老纪v3意见将以现实事件进账)、广阳岛@7/23查水文站→7/29±窗、老纪6000@7/20兜底;7/31 姑妈店关门=她"要在"日,不派活。
- 下段缺口:20+轮长对话×2、Goal 面、Action/Outcome 计数、F-011 回归用例(core 改动需用户批准:numeric series 幂等键应含 batch digest)。
- 若继续:新建 segments/segment_002/,events.jsonl 时钟从 7/14T16:00Z 起;runner 同一命令换 --segment;io/ 全新。

## Resident 纪律(血的,已进报告)
1. 证据 id 只许整行复制(检索结果/run_state/查库),永不字符串拼接(3次被 Core 拒)。
2. decision JSON 写完必须 `python -c "json.load"` 自检再落盘(炸过一次全链)。
3. 引用弹药只装"已发生"的;未来推断必须带"如果";写完查时态(INC-02)。
4. Summary/对话无修订面 → 当场收回是唯一纠错通道;持久对象错误用 overlay claim。
5. 唤醒后先 read_execution_world 再 transition(F-005);每次 transition 显式带 next_wake_at(F-006)。
6. 摘要提交前核对窗口内 source 是否支持每个带日期的断言(INC-01 自检规则)。
7. decision 文件存在≠未消费;以 pending.json 的 seq 为唯一信号。
