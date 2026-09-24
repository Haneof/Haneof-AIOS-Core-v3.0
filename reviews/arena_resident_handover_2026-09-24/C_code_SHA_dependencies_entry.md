# C. 当前实际代码SHA、依赖与启动入口

- 固定底座头: 22b9641f85e0e20f1bd87ed85100a1e268e56dea (PR125交接)
- 当前头: 22b9641f85e0e20f1bd87ed85100a1e268e56dea (继续原固定分支 arena/01a0cf25-haneof-aios-core-v3-0)
- 冻结Core: bcd6bf353126318f9a97076b52ec1740d43f35a4 (src/aios_core tree eed27d58041d)
- accepted A: 3e51f728d7959048b75fea01d405bc837b0e8185 (PR117 arena/01a0cca8)
- 关键文件 SHA256:
  - tools/c15_preflight/transport.py: e13c7c3e54f7899682b593ab7825beef98818aff012d700fc598be1ea80dc50b
  - tools/c15_preflight/driver.py: 9bf0ec92f402ed5ea5165fa0f8cfedd0d025ccf4b0fac6d0828e33fe429eb498
  - tools/c15_preflight/restart.py: 7bc644f37388aa829a60e459827038a8fc78f817a8b96770148b74d0fe991652
  - tools/c15_preflight/audit.py: 8ab0d1bcc27472f360c61ca30fbd4b3b7bbcb7ac726b471b39036aa6a6ef14ac
  - tools/c15_preflight/resident_broker.py: 553612269884935594005385fef3282c463eb8f1c4bbec261141b2d69c4ac6ad
  - tools/c15_preflight/arena_resident_file_exchange.py: (待创建)

- 依赖: Python>=3.12, pip install -e ".[dev]" (pydantic, aiosqlite, etc), PYTHONDONTWRITEBYTECODE=1
- 启动入口:
  - Operator: `PYTHONPATH=src:. python -m tools.c15_preflight.arena_resident_file_exchange --mode operator --write-packet /tmp/resident_packet/request.json --synthetic`
  - Resident: 读取 /tmp/resident_packet/request.json, 写入 /tmp/resident_packet/response.json (按 PROTOCOL.md)
  - Operator收回: `... --read-response /tmp/resident_packet/response.json --validate --execute --trace /tmp/resident_trace/trace.jsonl`
  - 若已有入口，直接复用 tools/c15_preflight/transport.py plain/encode/directive, driver.py, restart.py
  - 若缺入口，仅补最小文件交换入口 (arena_resident_file_exchange.py)
  - 允许人工原样转交，禁止脚本代替AI生成或改写决定
  - 不开发外部模型API，不扩展通用框架
