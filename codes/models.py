from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class SourceType(str, Enum):
    OFFICIAL = "official"
    MEDIA = "media"
    RUMOR = "rumor"


SOURCE_WEIGHTS = {
    SourceType.OFFICIAL: 1.0,
    SourceType.MEDIA: 0.7,
    SourceType.RUMOR: 0.3,
}


@dataclass
class NewsItem:
    title: str
    content: str
    source: SourceType
    url: Optional[str] = None
    published_at: Optional[str] = None


@dataclass
class ReportSnapshot:
    keyword: str
    collected_at: str
    items: List[NewsItem] = field(default_factory=list)


@dataclass
class ChangeItem:
    field: str
    old: str
    new: str
    status: str
    source: SourceType
    confidence: float = 0.0


@dataclass
class ConflictDecision:
    field: str
    final_value: str
    chosen_source: SourceType
    pending_sources: List[SourceType] = field(default_factory=list)
    reason: str = ""


def now_ts() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

# models.py
@dataclass
class ChangeItem:
    field: str
    old: str
    new: str
    status: str
    source: SourceType
    insight: str = ""  # 新增：存储 AI 对变动的通俗化解读
    confidence: float = 0.0

@dataclass
class ConflictDecision:
    field: str
    final_value: str
    chosen_source: SourceType
    pending_sources: List[SourceType] = field(default_factory=list)
    reason: str = ""  # 这里将存储最终采纳的 insight