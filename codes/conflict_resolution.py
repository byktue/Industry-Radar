from __future__ import annotations

import logging
from typing import Dict, List

from models import ChangeItem, ConflictDecision, SOURCE_WEIGHTS, SourceType

logger = logging.getLogger(__name__)


def _normalize_source(source: any) -> SourceType:
    """标准化来源类型，确保返回 SourceType 枚举。
    
    Args:
        source: 可能是 SourceType 枚举或字符串
        
    Returns:
        SourceType 枚举，默认为 MEDIA
    """
    if isinstance(source, SourceType):
        return source
    # 如果是字符串，尝试转换
    if isinstance(source, str):
        try:
            return SourceType(source)
        except ValueError:
            logger.warning(f"[ConflictResolution] Unknown source type '{source}', defaulting to MEDIA")
    return SourceType.MEDIA


def resolve_conflicts(changes: List[ChangeItem]) -> List[ConflictDecision]:
    """冲突仲裁：当同一字段有多来源冲突时，按权重选择最终结论。
    
    优先级逻辑（硬编码）：
    - 官方公告 (OFFICIAL): Weight = 1.0
    - 权威媒体 (MEDIA): Weight = 0.7
    - 市场传闻 (RUMOR): Weight = 0.3
    
    冲突仲裁规则：
    1. 选择权重最高的来源作为最终结论
    2. 低权重来源标记为"待核实"
    3. 记录仲裁理由
    
    注意：只有存在真正冲突（同一字段多个来源）时才返回决策
    """
    grouped: Dict[str, List[ChangeItem]] = {}
    for c in changes:
        grouped.setdefault(c.field, []).append(c)
    
    logger.info(f"Grouped changes into {len(grouped)} fields")
    
    decisions: List[ConflictDecision] = []
    for field, items in grouped.items():
        # 如果只有一个来源，不是真正的冲突，但仍然返回决策（用于统一处理）
        if len(items) == 1:
            chosen = items[0]
            decisions.append(
                ConflictDecision(
                    field=field,
                    final_value=chosen.new,
                    chosen_source=_normalize_source(chosen.source),
                    pending_sources=[],
                    reason="唯一来源",
                )
            )
            logger.info(f"[ConflictResolution] Field '{field}': single source, no conflict")
            continue
        
        # 多来源冲突：按权重排序
        items_sorted = sorted(
            items,
            key=lambda x: SOURCE_WEIGHTS.get(_normalize_source(x.source), 0.0),
            reverse=True,
        )
        
        chosen = items_sorted[0]
        pending_items = items_sorted[1:]
        
        # 获取权重信息
        chosen_source = _normalize_source(chosen.source)
        chosen_weight = SOURCE_WEIGHTS.get(chosen_source, 0.0)
        
        # 提取待核实来源（低权重来源）
        pending_sources = [_normalize_source(item.source) for item in pending_items]
        
        # 构造仲裁理由
        reason = f"权重最高来源优先 (Weight={chosen_weight})"
        
        if pending_sources:
            pending_names = [s.value for s in pending_sources]
            reason += f"，其他来源待核实: {', '.join(pending_names)}"
        
        logger.info(f"[ConflictResolution] Field '{field}': CONFLICT - chosen={chosen_source.value} "
                   f"(weight={chosen_weight}), pending={len(pending_sources)}")
        
        decisions.append(
            ConflictDecision(
                field=field,
                final_value=chosen.new,
                chosen_source=chosen_source,
                pending_sources=pending_sources,
                reason=reason,
            )
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
