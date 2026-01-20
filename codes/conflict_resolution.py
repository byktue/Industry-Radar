from __future__ import annotations

import logging
from typing import Dict, List

from models import ChangeItem, ConflictDecision, SOURCE_WEIGHTS, SourceType

logger = logging.getLogger(__name__)


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

    decisions: List[ConflictDecision] = []
    for field, items in grouped.items():
        # 如果只有一个来源，不是真正的冲突，但仍然返回决策（用于统一处理）
        if len(items) == 1:
            chosen = items[0]
            decisions.append(
                ConflictDecision(
                    field=field,
                    final_value=chosen.new,
                    chosen_source=chosen.source if isinstance(chosen.source, SourceType) else SourceType.MEDIA,
                    pending_sources=[],
                    reason="唯一来源",
                )
            )
            logger.info(f"[ConflictResolution] Field '{field}': single source, no conflict")
            continue
        
        # 多来源冲突：按权重排序
        items_sorted = sorted(
            items,
            key=lambda x: SOURCE_WEIGHTS.get(
                x.source if isinstance(x.source, SourceType) else SourceType.MEDIA,
                0.0
            ),
            reverse=True,
        )
        
        chosen = items_sorted[0]
        pending_items = items_sorted[1:]
        
        # 获取权重信息
        chosen_weight = SOURCE_WEIGHTS.get(
            chosen.source if isinstance(chosen.source, SourceType) else SourceType.MEDIA,
            0.0
        )
        
        # 提取待核实来源（低权重来源）
        pending_sources = []
        for item in pending_items:
            source = item.source if isinstance(item.source, SourceType) else SourceType.MEDIA
            pending_sources.append(source)
        
        # 构造仲裁理由
        chosen_source = chosen.source if isinstance(chosen.source, SourceType) else SourceType.MEDIA
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
