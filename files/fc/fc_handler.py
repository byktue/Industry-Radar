"""
阿里云函数计算 (Alibaba Cloud Function Compute) 入口文件

此文件为 FC 的主入口，实现定时触发的行业雷达监控任务。
支持：
1. 定时触发（通过 Cron 表达式配置）
2. 手动触发（通过事件参数传入 keyword）
3. 完整的异常捕获与日志记录
4. 采集失败时的保护机制
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

# 添加 codes 目录到 Python 路径
# 预期文件结构: files/fc/fc_handler.py -> codes/
FILE_DIR = Path(__file__).parent
REPO_ROOT = FILE_DIR.parent.parent
CODES_DIR = REPO_ROOT / "codes"
sys.path.insert(0, str(CODES_DIR))

from orchestrator import run_pipeline  # noqa: E402
from config import DEFAULT_KEYWORD  # noqa: E402

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Any, context: Any) -> Dict[str, Any]:
    """
    阿里云 FC 入口函数
    
    Args:
        event: 触发器传入的事件对象，支持：
            - 定时触发：event 可能为空或包含触发器信息
            - HTTP 触发：event 包含 HTTP 请求信息
            - 手动触发：可自定义 event 参数
        context: FC 运行时上下文对象，包含请求 ID、函数信息等
    
    Returns:
        包含执行结果的字典
    """
    # 提取请求信息
    request_id = getattr(context, "request_id", "unknown")
    logger.info(f"[FC Handler] Request ID: {request_id}")
    logger.info(f"[FC Handler] Event: {event}")
    
    # 解析关键词参数
    keyword = DEFAULT_KEYWORD
    try:
        if isinstance(event, dict):
            keyword = event.get("keyword", DEFAULT_KEYWORD)
        elif isinstance(event, (str, bytes)):
            # 处理 HTTP 触发场景：event 可能是 JSON 字符串
            event_data = json.loads(event) if isinstance(event, str) else json.loads(event.decode("utf-8"))
            keyword = event_data.get("keyword", DEFAULT_KEYWORD)
    except Exception as e:
        logger.warning(f"[FC Handler] Failed to parse event, using default keyword: {e}")
    
    logger.info(f"[FC Handler] Pipeline starting with keyword: {keyword}")
    
    # 执行主流程
    try:
        result = run_pipeline(keyword=keyword)
        
        # 记录执行结果
        changes_count = len(result.get("changes", []))
        conflicts_count = len(result.get("conflicts", []))
        
        logger.info(f"[FC Handler] Pipeline completed successfully")
        logger.info(f"[FC Handler] Changes detected: {changes_count}")
        logger.info(f"[FC Handler] Conflicts resolved: {conflicts_count}")
        
        # 构造返回结果
        response = {
            "status": "success",
            "keyword": keyword,
            "request_id": request_id,
            "summary": {
                "changes": changes_count,
                "conflicts": conflicts_count,
            },
            "details": {
                "changes": [
                    {
                        "field": c.field,
                        "old": c.old,
                        "new": c.new,
                        "status": c.status,
                        "source": c.source.value if hasattr(c.source, "value") else str(c.source),
                        "confidence": c.confidence,
                    }
                    for c in result.get("changes", [])
                ],
                "conflicts": [
                    {
                        "field": d.field,
                        "final_value": d.final_value,
                        "chosen_source": d.chosen_source.value if hasattr(d.chosen_source, "value") else str(d.chosen_source),
                        "pending_sources": [
                            s.value if hasattr(s, "value") else str(s) for s in d.pending_sources
                        ],
                        "reason": d.reason,
                    }
                    for d in result.get("conflicts", [])
                ],
            },
        }
        
        return response
        
    except Exception as e:
        # 异常捕获与日志记录
        logger.error(f"[FC Handler] Pipeline failed: {type(e).__name__}: {str(e)}", exc_info=True)
        
        # 返回失败状态，但不抛出异常（避免 FC 重试）
        return {
            "status": "error",
            "keyword": keyword,
            "request_id": request_id,
            "error": {
                "type": type(e).__name__,
                "message": str(e),
            },
        }


def local_test():
    """本地调试函数"""
    # 模拟 FC context 对象
    class MockContext:
        request_id = "local-test-123"
    
    # 测试场景1：默认关键词
    print("=== Test 1: Default keyword ===")
    event1 = {}
    result1 = handler(event1, MockContext())
    print(json.dumps(result1, ensure_ascii=False, indent=2))
    
    # 测试场景2：自定义关键词
    print("\n=== Test 2: Custom keyword ===")
    event2 = {"keyword": "新能源"}
    result2 = handler(event2, MockContext())
    print(json.dumps(result2, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    # 本地调试时直接执行
    local_test()
