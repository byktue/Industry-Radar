from __future__ import annotations

import json
import logging
import os
import shutil
from typing import List, Optional

from config import DATA_DIR
from models import NewsItem, ReportSnapshot, now_ts

logger = logging.getLogger(__name__)


class StorageClient:
    """存储层：将快照写入对象存储（此处用本地文件模拟）。
    
    支持以下存储结构：
    - history/{timestamp}/: 历史归档目录
      - fetch.json: 原始抓取数据
      - report.json: 分析报告快照
    - latest_fetch.json: 最新抓取的原始数据
    - current_report.json: 当前报告（用于增量对比的旧快照）
    """

    def __init__(self, base_dir: str = DATA_DIR) -> None:
        self.base_dir = base_dir
        self.history_dir = os.path.join(self.base_dir, "history")
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.history_dir, exist_ok=True)

    def save_fetch_data(self, keyword: str, items: List[NewsItem]) -> str:
        """保存原始抓取数据到 latest_fetch.json
        
        Args:
            keyword: 关键词
            items: 抓取的新闻条目列表
            
        Returns:
            str: 保存的文件路径
        """
        snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
        path = os.path.join(self.base_dir, "latest_fetch.json")
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
            logger.info(f"Saved fetch data to {path}")
            return path
        except Exception as e:
            logger.error(f"Failed to save fetch data: {e}")
            raise
    
    def save_current_report(self, keyword: str, items: List[NewsItem]) -> str:
        """保存当前报告到 current_report.json（用于下次增量对比）
        
        Args:
            keyword: 关键词
            items: 新闻条目列表
            
        Returns:
            str: 保存的文件路径
        """
        snapshot = ReportSnapshot(keyword=keyword, collected_at=now_ts(), items=items)
        path = os.path.join(self.base_dir, "current_report.json")
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
            logger.info(f"Saved current report to {path}")
            return path
        except Exception as e:
            logger.error(f"Failed to save current report: {e}")
            raise
    
    def save_snapshot(self, keyword: str, items: List[NewsItem]) -> str:
        """保存完整快照（兼容旧接口）
        
        此方法会同时：
        1. 保存到 latest_fetch.json
        2. 保存到 current_report.json
        3. 归档到 history/{timestamp}/
        
        Args:
            keyword: 关键词
            items: 新闻条目列表
            
        Returns:
            str: 历史归档目录路径
        """
        timestamp = now_ts()
        snapshot = ReportSnapshot(keyword=keyword, collected_at=timestamp, items=items)
        
        # 保存到 latest_fetch.json
        self.save_fetch_data(keyword, items)
        
        # 保存到 current_report.json
        self.save_current_report(keyword, items)
        
        # 归档到 history/{timestamp}/
        history_path = os.path.join(self.history_dir, timestamp)
        os.makedirs(history_path, exist_ok=True)
        
        # 保存 fetch.json
        fetch_file = os.path.join(history_path, "fetch.json")
        with open(fetch_file, "w", encoding="utf-8") as f:
            json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
        
        # 保存 report.json（与 fetch.json 相同，为未来扩展预留）
        report_file = os.path.join(history_path, "report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)
        
        logger.info(f"Archived snapshot to {history_path}")
        return history_path

    def load_latest_fetch(self) -> Optional[ReportSnapshot]:
        """加载最新抓取数据（latest_fetch.json）
        
        Returns:
            Optional[ReportSnapshot]: 快照对象，如果文件不存在则返回 None
        """
        path = os.path.join(self.base_dir, "latest_fetch.json")
        if not os.path.exists(path):
            logger.info("latest_fetch.json not found")
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._dict_to_snapshot(data)
        except Exception as e:
            logger.error(f"Failed to load latest fetch: {e}")
            return None
    
    def load_current_report(self) -> Optional[ReportSnapshot]:
        """加载当前报告（current_report.json）用于增量对比
        
        Returns:
            Optional[ReportSnapshot]: 快照对象，如果文件不存在则返回 None
        """
        path = os.path.join(self.base_dir, "current_report.json")
        if not os.path.exists(path):
            logger.info("current_report.json not found")
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._dict_to_snapshot(data)
        except Exception as e:
            logger.error(f"Failed to load current report: {e}")
            return None
    
    def load_latest_snapshot(self) -> Optional[ReportSnapshot]:
        """加载最新快照（兼容旧接口）
        
        优先从 current_report.json 加载，如不存在则从历史目录加载最新的
        
        Returns:
            Optional[ReportSnapshot]: 快照对象
        """
        # 优先读取 current_report.json
        snapshot = self.load_current_report()
        if snapshot:
            return snapshot
        
        # 兼容旧格式：从 report_*.json 文件加载
        files = self.list_snapshots()
        if not files:
            # 尝试从历史目录加载
            return self._load_latest_from_history()
        
        latest = sorted(files)[-1]
        path = os.path.join(self.base_dir, latest)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._dict_to_snapshot(data)
        except Exception as e:
            logger.error(f"Failed to load latest snapshot from {path}: {e}")
            return None
    
    def _load_latest_from_history(self) -> Optional[ReportSnapshot]:
        """从 history 目录加载最新快照"""
        if not os.path.isdir(self.history_dir):
            return None
        
        timestamps = [d for d in os.listdir(self.history_dir) 
                     if os.path.isdir(os.path.join(self.history_dir, d))]
        if not timestamps:
            return None
        
        latest_ts = sorted(timestamps)[-1]
        report_path = os.path.join(self.history_dir, latest_ts, "report.json")
        
        if not os.path.exists(report_path):
            return None
        
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._dict_to_snapshot(data)
        except Exception as e:
            logger.error(f"Failed to load from history: {e}")
            return None

    def list_snapshots(self) -> List[str]:
        if not os.path.isdir(self.base_dir):
            return []
        return [f for f in os.listdir(self.base_dir) if f.startswith("report_") and f.endswith(".json")]

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
