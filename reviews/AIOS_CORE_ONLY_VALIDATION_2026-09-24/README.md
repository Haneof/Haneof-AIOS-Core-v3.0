# 十项 Core 修复：独立源码复验

## 结论

原始修复提交 `d1466deaab8dc6d5795fcd7e4f6e5a8720727a63` 可以独立作为 Core 修复候选，
不需要先集成 PR125。其直接父提交是本轮复查仍在 main 的
`849bfd41c623fb336b392a3e6e933cfad93620e9`。原修复仅 17 个文件，
其中 12 个 Core 文件、1 个专项测试文件、4 个历史证据文件。
本轮没有发现需要继续改写 Core 的失败；新增内容仅为独立验证脚本和证据。

## 本轮实际运行

在独立非 Git 目录从指定提交导出 132 个 Python/config 文件，没有复制任何仓库 fixture 数据。
使用 Python 3.12.11 / pytest 8.4.2 / pydantic 2.13.5 / SQLite 3.40.1。
Python 由官方 v3.12.11 源码本地构建，未构建可选 SSL/ctypes 模块；依赖用离线 wheel 安装。
这不是网络/provider 集成环境。

| 范围 | 实际结果 |
|---|---:|
| Core：unit + runtime + integration | 409 passed，0 failed/error/skipped |
| 十项 BUG 专项（包含于上行） | 42 passed，0 failed/error/skipped |
| 默认公开测试 collection（不执行测试体） | 501 项 |
| 全部适用公开合成测试（含 409 Core + 83 habitation） | 492 passed，0 failed/error/skipped |
| 仓库 fixture 依赖项 | 9 项明确排除，NOT_TESTED，不计入通过 |

9 项排除不是为了消除失败：7 项 fixture/catalog 检验、1 项 fixture 回放、1 项读取 fixture 的 evaluator 测试，
会读取禁止接触的仓库 resident/oracle 数据。逐项 node ID 记录在 manifest 和 execution 中。
同文件中仅使用临时合成数据的路径穿越测试仍执行。
**没有运行完整 501 项默认套件，不称“默认全绿”。** 原来的 507 和 PR126 的 644 均未挪作本轮结果。

脚本要求源码 SHA-256 清单完全匹配；实际 collection 与执行集合必须精确相差这 9 项，
不接受缺失、重复、skip、失败或错误。运行前清空进程环境，禁止网络连接、子进程，
限制 Python 文件访问到导出源码、临时结果、解释器及标准时区表。
这只是合成验证的防误触措施，**不是 OS 隔离认证**。

首轮增强防误触脚本误拦标准库 `/usr/share/zoneinfo/UTC`，导致 17 项失败；
保留 `harness-attempt-1.xml`，修正为允许标准 `zoneinfo.TZPATH` 后完整复跑通过。
没有修改 Core 或测试断言来消除这些失败。最终脚本加入源码清单校验后再次完整复跑通过。

## 复跑

在有 Python 3.12、pytest 8.x、pydantic 2.x 的环境中，只从原始提交导出
`src/**/*.py`、`tests/**/*.py`、`pyproject.toml` 到独立目录；不要导出 fixture 或封存数据。
导出目录必须与 `source-files.json` 完全一致。然后：

```sh
python3.12 verify_public.py /path/to/source-export /path/to/results --collect-only
python3.12 verify_public.py /path/to/source-export /path/to/results
# 两步都须退出 0。第二步会比对第一步 collection 并拒绝任何失败/错误/跳过。
```

原始 Core 子树：`7db4f72e7b3c29c74082f9984141159f8f1d6071`。
42 项测试 Git blob：`e4ce7c223452e04fa10f9cb0bbcf787fe4feb00e`。
完整逐文件 SHA-256、JUnit、collection、逐测试阶段结果均随附；测试后导出源码校验未变化。
所有工作区原有 17 个修复文件与原提交逐字节相同，历史证据未重写。

## 尚未完成的边界

- 本轮为 Core-only 软件候选复验，不评价 PR125 后续 operator 变化或组合 CI。
- PR125/126 未合并、未重定向、未关闭；没有新建 PR，没有向 main 写入。
- 正式隔离、真实 A/B/C 均 NOT_TESTED；Resident BLOCKED，launchable=false。
- 历史冻结锚点、`audit.verify_core` 不变，不为改变后的 Core 签发新冻结证明。
- **用户的最终目标仍未完成：需获准集成后，核验 main 最终 SHA、内容及对应测试。**
  原始 17 文件候选不依赖 PR125；不要通过只改 PR126 base 将组合链伪装成 Core-only。
