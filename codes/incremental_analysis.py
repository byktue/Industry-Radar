from __future__ import annotations

import logging
from typing import List, Optional

from models import ChangeItem, NewsItem, ReportSnapshot

logger = logging.getLogger(__name__)


def incremental_compare(old_snapshot: Optional[ReportSnapshot], new_items: List[NewsItem]) -> List[ChangeItem]:
    """增量对比：将旧结论与新资讯对比，抽取变化字段。"""
    if not old_snapshot:
        logger.info(f"[IncrementalAnalysis] No old snapshot, skipping comparison")
        return []

    logger.info(f"[IncrementalAnalysis] Comparing old snapshot ({len(old_snapshot.items)} items) "
               f"with new items ({len(new_items)} items)")
    
    # TODO: 调用 LLM，实现字段级变化抽取
    # 这里先提供占位逻辑（仅示例，不做真实对比）
    changes: List[ChangeItem] = []
    for item in new_items:
        if "5%" in item.content and "2%" in item.content:
            changes.append(
                ChangeItem(
                    field="增长率",
                    old="5%",
                    new="2%",
                    status="decreased",
                    source=item.source,
                    confidence=0.5,
                )
            )
    
    logger.info(f"[IncrementalAnalysis] Found {len(changes)} changes")
    return changes
