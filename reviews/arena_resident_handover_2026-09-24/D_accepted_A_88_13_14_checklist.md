# D. 从accepted A的88/88、13→14边界启动的核对清单

- 固定底座: 22b9641f85e0e20f1bd87ed85100a1e268e56dea, 分支 arena/01a0cf25-haneof-aios-core-v3-0
- 冻结Core: bcd6bf353126318f9a97076b52ec1740d43f35a4
- accepted A: 3e51f728d7959048b75fea01d405bc837b0e8185, 来源 reviews/internal_habitation/c15-rcc/v1/runs/resident-a-final-rerun-20260923/
- HASHES验证 (audit.py):
  - private_world.sqlite: 9ff2b13cc1ec6e4d61a7910b4177ed3e1f25cfc47df8e18481a0199dd1aad395
  - world_index.sqlite: 55282a61d714f732f1b10fa6b450853f8425b5c9f741090fcaad0f1e673a6643
  - release_state.json, restart_state.json, ARTIFACT_MANIFEST.json 匹配 manifest
- World/index: 88/88 (final_world_revision 88, final_index_watermark 88, watermark() == current_world_revision())
- Release边界: last_acked_sequence 13, next_sequence 14, pending_reveal None, receipts长度13, 无B14-22, 无ACK/B完成
- Restart: 13字段 RESTART_KEYS, session_id 新, conversation_turn_index 重置, clock 机械, synthetic=False 时为 FORMAL_A_VERIFIED
- Driver: 从 staging 导入，private_world.sqlite, world_index.sqlite, release_state.json, restart_state.json, trace.jsonl, mechanical_restart.json 完整, completed_sequence 13, world_revision 88, index_watermark 88
- 禁止: 不用PR126新Core，不用旧B初始化，不合并PR，不触发公开CI真实A工作流 (real-a-import-312.yml if: false)
- 启动必需链核对 (合成数据):
  1. 输出批准Runtime输入: plain(RuntimeSnapshot) 仅7字段, protocol c15-resident-broker-v1, input_sha256 匹配
  2. 接收Arena AI本人原始directive: response.json 含 request_id/kind/input_sha256/output 绑定，未被脚本改写
  3. 校验请求绑定: response 的 request_id/kind/input_sha256 == request 的对应值
  4. 经正常Runtime执行合法能力: directive() 验证后，FusedTurnRuntime 执行 capability_calls, 保留Core合法能力调用
  5. 返回执行结果并记录原始trace: trace.jsonl 追加 kind, at, world_revision, previous, data, sha256, fsync

- 只用独立合成数据完成一次收发核验，不要提前释放正式B事件
