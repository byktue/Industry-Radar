from __future__ import annotations

import json
import logging
import os
from typing import List, Optional

from config import DATA_DIR
from models import NewsItem, ReportSnapshot, now_ts

logger = logging.getLogger(__name__)


class StorageClient:
    """存储层：将快照写入对象存储（此处用本地文件模拟）。
    
    支持：
    1. 历史快照归档（history/ 目录）
    2. 最新数据索引（latest_fetch.json, latest_report.json）
    3. 增量对比支持（提供 old_snapshot 和 new_items 持久化）
    4. 失败保护（采集失败时不覆盖旧数据）
    """

    def __init__(self, base_dir: str = DATA_DIR) -> None:
        self.base_dir = base_dir
        self.history_dir = os.path.join(base_dir, "history")
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.history_dir, exist_ok=True)

    def save_snapshot(self, keyword: str, items: List[NewsItem], success: bool = True) -> str:
        """保存快照到存储层。
        
        Args:
            keyword: 关键词
            items: 抓取的新闻条目
            success: 是否采集成功（失败时不覆盖旧数据）
        
        Returns:
            保存的文件路径
        """
        if not success:
            logger.warning("[StorageClient] Fetch failed, skip saving snapshot to prevent data loss")
            return ""
        
        snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
        
        # 1. 保存到历史目录（按时间戳归档）
        history_filename = f"report_{snapshot.collected_at}.json"
        history_path = os.path.join(self.history_dir, history_filename)
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
        logger.info(f"[StorageClient] Saved history snapshot: {history_path}")
        
        # 2. 保存最新抓取数据（用于增量对比的 new_items）
        latest_fetch_path = os.path.join(self.base_dir, "latest_fetch.json")
        with open(latest_fetch_path, "w", encoding="utf-8") as f:
            json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
        logger.info(f"[StorageClient] Updated latest_fetch.json")
        
        # 3. 更新 current_report.json（用于下次增量对比的 old_snapshot）
        # 注意：只有在成功处理后才更新此文件
        current_report_path = os.path.join(self.base_dir, "current_report.json")
        try:
            # 如果已有 latest_report.json，将其复制为 current_report.json
            latest_report_path = os.path.join(self.base_dir, "latest_report.json")
            if os.path.exists(latest_report_path):
                with open(latest_report_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with open(current_report_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 将当前抓取保存为 latest_report.json（作为下次的 old_snapshot）
            with open(latest_report_path, "w", encoding="utf-8") as f:
                json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
            logger.info(f"[StorageClient] Updated latest_report.json")
        except Exception as e:
            logger.error(f"[StorageClient] Failed to update report indexes: {e}")
        
        return history_path

    def load_latest_snapshot(self) -> Optional[ReportSnapshot]:
        """加载最新快照（用于增量对比的 old_snapshot）。
        
        优先级：
        1. latest_report.json（最新报告）
        2. current_report.json（当前报告）
        3. 历史快照中的最新一个
        """
        # 优先从 latest_report.json 加载
        latest_report_path = os.path.join(self.base_dir, "latest_report.json")
        if os.path.exists(latest_report_path):
            try:
                with open(latest_report_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"[StorageClient] Loaded latest_report.json as old_snapshot")
                return self._dict_to_snapshot(data)
            except Exception as e:
                logger.warning(f"[StorageClient] Failed to load latest_report.json: {e}")
        
        # 其次从 current_report.json 加载
        current_report_path = os.path.join(self.base_dir, "current_report.json")
        if os.path.exists(current_report_path):
            try:
                with open(current_report_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"[StorageClient] Loaded current_report.json as old_snapshot")
                return self._dict_to_snapshot(data)
            except Exception as e:
                logger.warning(f"[StorageClient] Failed to load current_report.json: {e}")
        
        # 最后从历史快照加载
        files = self.list_snapshots()
        if not files:
            logger.info(f"[StorageClient] No previous snapshot found")
            return None
        latest = sorted(files)[-1]
        path = os.path.join(self.history_dir, latest)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"[StorageClient] Loaded history snapshot: {latest}")
        return self._dict_to_snapshot(data)
    
    def load_latest_fetch(self) -> Optional[ReportSnapshot]:
        """加载最新抓取数据（用于增量对比的 new_items）。"""
        latest_fetch_path = os.path.join(self.base_dir, "latest_fetch.json")
        if not os.path.exists(latest_fetch_path):
            logger.info(f"[StorageClient] No latest_fetch.json found")
            return None
        
        try:
            with open(latest_fetch_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"[StorageClient] Loaded latest_fetch.json")
            return self._dict_to_snapshot(data)
        except Exception as e:
            logger.error(f"[StorageClient] Failed to load latest_fetch.json: {e}")
            return None
    
    def load_latest_report(self) -> Optional[ReportSnapshot]:
        """加载最新报告（用于增量对比的 old_snapshot，别名方法）。"""
        return self.load_latest_snapshot()

    def list_snapshots(self) -> List[str]:
        """列出历史快照文件。"""
        if not os.path.isdir(self.history_dir):
            return []
        return [f for f in os.listdir(self.history_dir) if f.startswith("report_") and f.endswith(".json")]

    def _snapshot_to_dict(self, snapshot: ReportSnapshot) -> dict:
        return {
            "keyword": snapshot.keyword,
            "collected_at": snapshot.collected_at,
            "items": [
                {
                    "title": i.title,
                    "content": i.content,
                    "source": i.source.value,
                    "url": i.url,
                    "published_at": i.published_at,
                }
                for i in snapshot.items
            ],
        }

    def _dict_to_snapshot(self, data: dict) -> ReportSnapshot:
        items = [
            NewsItem(
                title=i.get("title", ""),
                content=i.get("content", ""),
                source=i.get("source", "media"),
                url=i.get("url"),
                published_at=i.get("published_at"),
            )
            for i in data.get("items", [])
        ]
        # 兼容 source 字符串
        for item in items:
            if not hasattr(item.source, "value"):
                item.source = item.source  # type: ignore[assignment]
        return ReportSnapshot(
            keyword=data.get("keyword", ""),
            collected_at=data.get("collected_at", ""),
            items=items,
        )
