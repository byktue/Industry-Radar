from __future__ import annotations

import logging
from typing import List

from models import NewsItem, SourceType

logger = logging.getLogger(__name__)


class ScraperAgent:
    """采集层：根据行业关键词抓取最新资讯。"""

    def fetch(self, keyword: str) -> List[NewsItem]:
        # TODO: 接入新闻 API、雪球、巨潮资讯等数据源
        # 下面是占位示例数据
        logger.info(f"[ScraperAgent] Fetching data for keyword: {keyword}")
        
        items = [
            NewsItem(
                title=f"{keyword} 行业预测更新",
                content=f"{keyword} 行业增速预测从 5% 调整到 2%",
                source=SourceType.MEDIA,
                url="https://example.com/report",
                published_at="2026-01-19",
            )
        ]
        
        logger.info(f"[ScraperAgent] Fetched {len(items)} items")
        return items
