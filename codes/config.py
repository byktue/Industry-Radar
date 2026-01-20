from __future__ import annotations

import os

# 数据存储配置（优先使用环境变量）
DATA_DIR = os.getenv("DATA_DIR", "data")
DEFAULT_KEYWORD = os.getenv("DEFAULT_KEYWORD", "半导体")

# OSS 配置（用于云端存储）
OSS_ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID", "")
OSS_ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET", "")
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "")
OSS_BUCKET = os.getenv("OSS_BUCKET", "")
OSS_PREFIX = os.getenv("OSS_PREFIX", "reports/")

# 触发配置（用于 Serverless 平台的 cron 触发器）
CRON_EXAMPLE = "0 0 */6 * * *"  # 每 6 小时（6位 Cron 表达式：秒 分 时 日 月 周）

# LLM 配置（用于增量对比）
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-max")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "")

# 告警配置（用于故障通知）
ALERT_WEBHOOK = os.getenv("ALERT_WEBHOOK", "")

# LLM 提示词模板（占位）
LLM_COMPARE_PROMPT = (
    "请对比以下两段信息，识别数值或结论变化，"
    "输出 JSON 数组，字段包含 field/old/new/status/source。\n"
    "旧结论: {old}\n新资讯: {new}"
)
