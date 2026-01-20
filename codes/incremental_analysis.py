import os
import json
import re
from typing import List, Optional
from langchain_openai import ChatOpenAI
from models import ChangeItem, NewsItem, ReportSnapshot, SourceType, ConflictDecision, SOURCE_WEIGHTS
from config import (
    SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, 
    LLM_MODEL, LLM_BASE_URL, LLM_TEMPERATURE, LLM_MAX_RETRIES
)

# API 密钥配置
api_key = os.getenv("SILICONFLOW_API_KEY", "sk-zieigdeeconidojrwencrdvsejqfxaoqvbxeqbsrxmqinlna")

llm = ChatOpenAI(
    api_key=api_key,
    base_url=LLM_BASE_URL,
    model=LLM_MODEL,
    max_retries=LLM_MAX_RETRIES,
    temperature=LLM_TEMPERATURE
)


def _clamp(value: float, low: float = 0.2, high: float = 0.95) -> float:
    return max(low, min(high, value))


def _compute_dynamic_confidence(
    change: dict,
    default_source: SourceType,
    new_items: List[NewsItem],
) -> float:
    """根据来源权重、来源丰富度及 LLM 反馈动态计算置信度。

    优先使用 LLM 返回的 confidence（若有），并与来源信息融合。
    """
    llm_conf_raw = change.get("confidence")
    llm_conf = None
    try:
        if llm_conf_raw is not None:
            llm_conf = float(llm_conf_raw)
    except (TypeError, ValueError):
        llm_conf = None

    # 来源权重
    source_weight = float(SOURCE_WEIGHTS.get(default_source, 0.5))

    # 来源丰富度：采集条数、来源多样性、证据完备度（url/时间）
    total = max(len(new_items), 1)
    count_score = min(1.0, total / 3)

    distinct_sources = len({i.source for i in new_items if i.source is not None})
    source_div_score = min(1.0, distinct_sources / 3)

    evidence_hits = 0
    for item in new_items:
        if item.url:
            evidence_hits += 1
        if item.published_at:
            evidence_hits += 1
    evidence_score = evidence_hits / (2 * total)

    computed = (
        0.45 * source_weight
        + 0.30 * source_div_score
        + 0.15 * count_score
        + 0.10 * evidence_score
    )

    if llm_conf is not None:
        return _clamp(0.6 * llm_conf + 0.4 * computed)
    return _clamp(computed)

def robust_json_parse(text: str) -> list:
    """JSON 强力提取与修复函数"""
    try:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r'^```json\s*|```$', '', text, flags=re.MULTILINE)
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        if match:
            try:
                clean_json = re.sub(r',\s*\]', ']', match.group())
                return json.loads(clean_json)
            except: pass
    return []

def incremental_compare(old_snapshot: Optional[ReportSnapshot], new_items: List[NewsItem]) -> List[ChangeItem]:
    """对比新旧数据并生成带洞察的变动项"""
    if not new_items:
        return []

    old_text = "尚未记录历史指标。"
    if old_snapshot and old_snapshot.items:
        old_text = "\n".join([f"- {i.title}: {i.content}" for i in old_snapshot.items])
    
    new_text = "\n".join([f"[{i.source.value}] {i.title}: {i.content}" for i in new_items])

    try:
        response = llm.invoke([
            ("system", SYSTEM_PROMPT),
            ("user", USER_PROMPT_TEMPLATE.format(old_text=old_text, new_text=new_text))
        ])
        
        raw_changes = robust_json_parse(response.content)
        changes: List[ChangeItem] = []

        default_source = new_items[0].source
        for c in raw_changes:
            confidence = _compute_dynamic_confidence(c, default_source, new_items)
            changes.append(ChangeItem(
                field=str(c.get("field", "未知指标")),
                old=str(c.get("old", "N/A")),
                new=str(c.get("new", "N/A")),
                status=str(c.get("status", "changed")),
                insight=str(c.get("insight", "指标发生变动，请关注。")),
                source=default_source,
                confidence=confidence,
            ))
        return changes
    except Exception as e:
        print(f"AI 增量分析失败: {e}")
        return []

def generate_global_summary(keyword: str, decisions: List[ConflictDecision]) -> str:
    """基于所有仲裁后的决策，生成全局通俗综述"""
    if not decisions:
        return f"针对 {keyword} 行业，本次巡检未发现显著的指标变动。"

    # 汇总上下文供 AI 总结
    summary_context = "\n".join([
        f"- {d.field}: 变为 {d.final_value}。专家分析: {d.reason}" 
        for d in decisions
    ])

    prompt = f"""你是一个首席行业分析师。请针对以下 {keyword} 行业的变动写一段 100 字以内的全局总结。
    要求：通俗易懂，点出行业整体趋势（利好/利空/震荡），直击要害。
    
    【变动清单】：
    {summary_context}"""
    
    try:
        response = llm.invoke([("user", prompt)])
        return response.content.strip()
    except Exception:
        return "行业发生多项变动，整体处于调整期，建议持续关注核心指标。"