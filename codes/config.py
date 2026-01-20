from __future__ import annotations

import os

# 数据目录配置
DATA_DIR = os.environ.get("DATA_DIR", "data")

# 默认关键词
DEFAULT_KEYWORD = os.environ.get("KEYWORD", "半导体")

# 触发配置（用于 Serverless 平台的 cron 触发器）
CRON_EXAMPLE = "0 */6 * * *"  # 每 6 小时

# OSS 配置（从环境变量读取）
OSS_ENDPOINT = os.environ.get("OSS_ENDPOINT", "")
OSS_ACCESS_KEY_ID = os.environ.get("OSS_ACCESS_KEY_ID", "")
OSS_ACCESS_KEY_SECRET = os.environ.get("OSS_ACCESS_KEY_SECRET", "")
OSS_BUCKET_NAME = os.environ.get("OSS_BUCKET_NAME", "")
OSS_PREFIX = os.environ.get("OSS_PREFIX", "industry-radar/")

# LLM 配置（从环境变量读取）
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_ENDPOINT = os.environ.get("LLM_ENDPOINT", "")

# LLM 提示词模板（占位）
LLM_COMPARE_PROMPT = (
    "请对比以下两段信息，识别数值或结论变化，"
    "输出 JSON 数组，字段包含 field/old/new/status/source。\n"
    "旧结论: {old}\n新资讯: {new}"
)
