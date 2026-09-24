# A. operator实际安装、启动、收发、停止命令

# 固定底座: PR125交接头 22b9641f85e0e20f1bd87ed85100a1e268e56dea, 固定分支 arena/01a0cf25-haneof-aios-core-v3-0
# 保持冻结Core bcd6bf353126318f9a97076b52ec1740d43f35a4, accepted A 3e51f728d7959048b75fea01d405bc837b0e8185
# 不用PR126新Core，不用旧B初始化，不合并PR，不触发公开CI真实A工作流 (real-a-import-312.yml 已 if: false 禁用)

# 1. 安装 (Python>=3.12)
python -c 'import sys; assert sys.version_info >= (3,12)'
pip install -e ".[dev]"
find src -type d -name __pycache__ -exec rm -rf {} + || true
export PYTHONDONTWRITEBYTECODE=1

# 2. 启动 - 从accepted A 88/88 13->14边界启动
# 假设已按 audit.py HASHES 验证 /tmp/real_a_original (仅本地已有结果，不在CI重复)
# 或使用合成数据演示 (本轮仅用合成数据完成一次收发核验，不释放正式B事件)
PYTHONPATH=src:. python -m tools.c15_preflight.arena_resident_file_exchange --mode operator --write-packet /tmp/resident_packet/request.json --synthetic

# 3. 收发 - 人工原样转交 (禁止脚本代替AI生成或改写决定)
# Operator已将批准的Runtime输入写入 /tmp/resident_packet/request.json (含 protocol, request_id, kind, input_sha256, input)
# 将该文件原样提供给 fresh Resident 新Arena窗口 (新窗口未接触本实验历史和评审材料)
# Resident窗口AI本人读取后，生成原始directive，写入 /tmp/resident_packet/response.json (需含 request_id/kind/input_sha256/output 绑定)
# Operator收回:
PYTHONPATH=src:. python -m tools.c15_preflight.arena_resident_file_exchange --mode operator --read-response /tmp/resident_packet/response.json --validate --execute --trace /tmp/resident_trace/trace.jsonl

# 4. 停止
# 若发现越界、缺日志、错误回复，立即停止，标记污染，保留现场
# 正常完成一次收发核验后，关闭 Driver, Trace
# 不自行跑真实B/C
