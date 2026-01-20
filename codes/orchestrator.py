from __future__ import annotations

import logging
from typing import Dict, List

from scraper_layer import ScraperAgent
from storage_layer import StorageClient
from incremental_analysis import incremental_compare
from conflict_resolution import resolve_conflicts
from models import ChangeItem, ConflictDecision

logger = logging.getLogger(__name__)


def run_pipeline(keyword: str) -> Dict[str, List]:
    """主流程编排：采集 -> 增量对比 -> 冲突仲裁 -> 存储快照
    
    增强特性：
    1. 全流程异常捕获
    2. 采集失败时不覆盖旧数据
    3. 详细日志记录
    
    Args:
        keyword: 行业关键词
        
    Returns:
        Dict[str, List]: 包含 changes 和 conflicts 的字典
        
    Raises:
        Exception: 在关键步骤失败时抛出异常
    """
    logger.info(f"Starting pipeline for keyword: {keyword}")
    
    scraper = ScraperAgent()
    storage = StorageClient()
    
    # 1. 采集新数据（带异常保护）
    try:
        logger.info("Step 1: Fetching new items...")
        new_items = scraper.fetch(keyword=keyword)
        logger.info(f"Fetched {len(new_items)} items")
        
        if not new_items:
            logger.warning("No items fetched, aborting pipeline")
            return {
                "changes": [],
                "conflicts": [],
            }
        
        # 保存原始抓取数据（即使后续步骤失败也要保存）
        storage.save_fetch_data(keyword=keyword, items=new_items)
        
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}", exc_info=True)
        # 采集失败时不继续执行，保护旧数据不被覆盖
        raise Exception(f"Data fetching failed: {e}")
    
    # 2. 加载旧快照用于增量对比
    try:
        logger.info("Step 2: Loading old snapshot for comparison...")
        old_snapshot = storage.load_current_report()
        if old_snapshot:
            logger.info(f"Loaded old snapshot with {len(old_snapshot.items)} items")
        else:
            logger.info("No old snapshot found, this might be the first run")
    except Exception as e:
        logger.error(f"Failed to load old snapshot: {e}", exc_info=True)
        old_snapshot = None
    
    # 3. 增量对比
    try:
        logger.info("Step 3: Performing incremental comparison...")
        changes: List[ChangeItem] = incremental_compare(old_snapshot, new_items)
        logger.info(f"Found {len(changes)} changes")
    except Exception as e:
        logger.error(f"Incremental comparison failed: {e}", exc_info=True)
        changes = []
    
    # 4. 冲突仲裁
    try:
        logger.info("Step 4: Resolving conflicts...")
        conflicts: List[ConflictDecision] = resolve_conflicts(changes)
        logger.info(f"Resolved {len(conflicts)} conflicts")
    except Exception as e:
        logger.error(f"Conflict resolution failed: {e}", exc_info=True)
        conflicts = []
    
    # 5. 保存新快照（包括归档和更新 current_report）
    try:
        logger.info("Step 5: Saving new snapshot...")
        storage.save_snapshot(keyword=keyword, items=new_items)
        logger.info("Snapshot saved successfully")
    except Exception as e:
        logger.error(f"Failed to save snapshot: {e}", exc_info=True)
        # 即使保存失败，也返回分析结果
    
    logger.info("Pipeline completed successfully")
    
    return {
        "changes": changes,
        "conflicts": conflicts,
    }
