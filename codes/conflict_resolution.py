from __future__ import annotations

import logging
from typing import Dict, List

from models import ChangeItem, ConflictDecision, SOURCE_WEIGHTS, SourceType

logger = logging.getLogger(__name__)


def resolve_conflicts(changes: List[ChangeItem]) -> List[ConflictDecision]:
    """冲突仲裁：当同一字段有多来源冲突时，按权重选择最终结论。
    
    冲突仲裁优先级逻辑：
    - 官方公告 (Official) Weight=1.0
    - 权威媒体 (Media) Weight=0.7
    - 市场传闻 (Rumor) Weight=0.3
    
    规则：
    1. 同一字段有多个来源时，选择权重最高的作为最终结论
    2. 其他低权重来源标记为"待核实"
    3. 如果只有一个来源，直接采纳
    
    Args:
        changes: 变化项列表
        
    Returns:
        List[ConflictDecision]: 冲突仲裁决策列表
    """
    if not changes:
        logger.info("No changes to resolve")
        return []
    
    # 按字段分组
    grouped: Dict[str, List[ChangeItem]] = {}
    for c in changes:
        grouped.setdefault(c.field, []).append(c)
    
    logger.info(f"Grouped changes into {len(grouped)} fields")
    
    decisions: List[ConflictDecision] = []
    for field, items in grouped.items():
        # 按权重排序（从高到低）
        items_sorted = sorted(
            items,
            key=lambda x: _get_source_weight(x.source),
            reverse=True,
        )
        
        chosen = items_sorted[0]
        chosen_source = _normalize_source(chosen.source)
        chosen_weight = SOURCE_WEIGHTS.get(chosen_source, 0.0)
        
        # 低权重来源标记为"待核实"
        pending = []
        for item in items_sorted[1:]:
            pending.append(_normalize_source(item.source))
        
        # 构建决策理由
        if len(items_sorted) == 1:
            reason = f"唯一来源: {chosen_source.value} (权重={chosen_weight})"
        else:
            reason = (
                f"权重最高来源优先: {chosen_source.value} (权重={chosen_weight})。"
                f"待核实来源: {', '.join([s.value for s in pending])}"
            )
        
        decisions.append(
            ConflictDecision(
                field=field,
                final_value=chosen.new,
                chosen_source=chosen_source,
                pending_sources=pending,
                reason=reason,
            )
        )
        
        logger.info(
            f"Resolved conflict for field '{field}': "
            f"chosen={chosen_source.value}, pending={len(pending)}"
        )
    
    return decisions


def _get_source_weight(source: SourceType | str) -> float:
    """获取来源权重
    
    Args:
        source: 来源类型（SourceType 或字符串）
        
    Returns:
        float: 权重值
    """
    normalized = _normalize_source(source)
    return SOURCE_WEIGHTS.get(normalized, 0.0)


def _normalize_source(source: SourceType | str) -> SourceType:
    """规范化来源类型
    
    Args:
        source: 来源（SourceType 或字符串）
        
    Returns:
        SourceType: 规范化的来源类型
    """
    if isinstance(source, SourceType):
        return source
    
    # 字符串转换为 SourceType
    try:
        return SourceType(source)
    except ValueError:
        logger.warning(f"Unknown source type: {source}, defaulting to MEDIA")
        return SourceType.MEDIA
