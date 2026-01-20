from __future__ import annotations

import logging
from typing import Dict, List

from scraper_layer import ScraperAgent
from storage_layer import StorageClient
from incremental_analysis import incremental_compare
from conflict_resolution import resolve_conflicts
from models import ChangeItem, ConflictDecision

logger = logging.getLogger(__name__)


def run_pipeline(keyword: str, max_retries: int = 3) -> Dict[str, List]:
    """主流程编排：采集 -> 增量对比 -> 冲突仲裁 -> 存储快照
    
    Args:
        keyword: 监控关键词
        max_retries: 采集失败时的最大重试次数
    
    Returns:
        包含 changes 和 conflicts 的字典
    
    可靠性保障：
    1. 采集失败时不覆盖旧数据
    2. 全流程异常捕获
    3. 采集失败时的重试机制
    4. 详细的日志记录
    """
    logger.info(f"[Pipeline] Starting pipeline for keyword: {keyword}")
    
    scraper = ScraperAgent()
    storage = StorageClient()

    # 1. 采集阶段（带重试）
    new_items = None
    fetch_success = False
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"[Pipeline] Attempt {attempt}/{max_retries}: Fetching data...")
            new_items = scraper.fetch(keyword=keyword)
            
            if new_items:
                fetch_success = True
                logger.info(f"[Pipeline] Fetch succeeded, got {len(new_items)} items")
                break
            else:
                logger.warning(f"[Pipeline] Fetch returned empty result")
        except Exception as e:
            logger.error(f"[Pipeline] Fetch attempt {attempt} failed: {type(e).__name__}: {str(e)}")
            if attempt == max_retries:
                logger.error(f"[Pipeline] All {max_retries} fetch attempts failed")
                # 采集失败，返回空结果，不覆盖旧数据
                return {
                    "changes": [],
                    "conflicts": [],
                }
    
    if not new_items:
        logger.warning(f"[Pipeline] No items fetched, pipeline terminated")
        return {
            "changes": [],
            "conflicts": [],
        }

    # 2. 增量对比阶段
    try:
        logger.info(f"[Pipeline] Loading old snapshot for comparison...")
        old_snapshot = storage.load_latest_snapshot()
        
        if old_snapshot:
            logger.info(f"[Pipeline] Old snapshot loaded: {len(old_snapshot.items)} items from {old_snapshot.collected_at}")
        else:
            logger.info(f"[Pipeline] No old snapshot found, this is the first run")
        
        logger.info(f"[Pipeline] Performing incremental comparison...")
        changes: List[ChangeItem] = incremental_compare(old_snapshot, new_items)
        logger.info(f"[Pipeline] Found {len(changes)} changes")
    except Exception as e:
        logger.error(f"[Pipeline] Incremental comparison failed: {type(e).__name__}: {str(e)}")
        # 对比失败不影响数据保存，返回空变化
        changes = []

    # 3. 冲突仲裁阶段
    try:
        logger.info(f"[Pipeline] Resolving conflicts...")
        conflicts: List[ConflictDecision] = resolve_conflicts(changes)
        logger.info(f"[Pipeline] Resolved {len(conflicts)} conflicts")
    except Exception as e:
        logger.error(f"[Pipeline] Conflict resolution failed: {type(e).__name__}: {str(e)}")
        # 仲裁失败不影响数据保存，返回空冲突
        conflicts = []

    # 4. 存储阶段（仅在采集成功时保存）
    try:
        logger.info(f"[Pipeline] Saving snapshot...")
        saved_path = storage.save_snapshot(keyword=keyword, items=new_items, success=fetch_success)
        if saved_path:
            logger.info(f"[Pipeline] Snapshot saved: {saved_path}")
        else:
            logger.warning(f"[Pipeline] Snapshot not saved (fetch_success={fetch_success})")
    except Exception as e:
        logger.error(f"[Pipeline] Failed to save snapshot: {type(e).__name__}: {str(e)}")
        # 存储失败不影响结果返回

    logger.info(f"[Pipeline] Pipeline completed successfully")
    return {
        "changes": changes,
        "conflicts": conflicts,
    }
