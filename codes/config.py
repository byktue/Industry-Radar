# config.py
import os

DATA_DIR = "data"
DEFAULT_KEYWORD = "半导体"

# --- LLM 运行配置 ---
LLM_MODEL = "deepseek-ai/DeepSeek-V3"
LLM_BASE_URL = "https://api.siliconflow.cn/v1"
LLM_TEMPERATURE = 0.1
LLM_MAX_RETRIES = 3

# --- 增强版全行业通用 Prompt ---
# config.py
SYSTEM_PROMPT = """你是一个专业的全行业分析助手。
对比【旧结论】与【新资讯】，识别关键指标变化并输出 JSON 数组。

【核心要求】：
1. 动态对齐：识别语义相同的指标。
2. 深度洞察：请为每个变动增加一个名为 'insight' 的字段，用一句话通俗易懂地解释这个变动意味着什么（不要只是重复数值，要说背后的行业逻辑）。

【输出格式示例】：
[
  {
    "field": "产能利用率",
    "old": "80%",
    "new": "92%",
    "status": "increased",
    "insight": "行业景气度爆发，头部厂家产线已接近满负荷运转。"
  }
]"""

USER_PROMPT_TEMPLATE = """
【旧快照中的已知指标】：
{old_text}

【新采集的行业资讯】：
{new_text}

请识别差异并输出 JSON 列表：
"""