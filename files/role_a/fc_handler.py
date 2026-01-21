"""
阿里云函数计算 (Alibaba Cloud FC) 入口文件

此文件为 Industry-Radar 项目的 Serverless 触发入口，
运行在阿里云函数计算平台上，支持定时触发执行全流程数据采集与分析。
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Dict

# 添加项目代码路径到 sys.path，以便导入 codes 模块
# 注意：在 FC 部署时，需要将整个项目代码上传，或者通过层（Layer）方式引入
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
codes_dir = os.path.join(project_root, 'codes')
sys.path.insert(0, codes_dir)

from codes.orchestrator import run_pipeline
from codes.config import DEFAULT_KEYWORD

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def handler(event: bytes, context: Any) -> str:
    """
    阿里云函数计算标准入口函数
    
    Args:
        event: 触发事件（bytes 或 dict）
            - 定时触发时，event 通常为 JSON 字符串或空 bytes
            - HTTP 触发时，event 包含请求信息
        context: FC 运行时上下文对象，包含请求 ID、函数信息等
        
    Returns:
        str: JSON 格式的响应字符串
        
    环境变量要求：
        - KEYWORD: 可选，行业关键词，默认使用 config.DEFAULT_KEYWORD
        - OSS_ENDPOINT: 阿里云 OSS endpoint (如 oss-cn-hangzhou.aliyuncs.com)
        - OSS_ACCESS_KEY_ID: 阿里云 AccessKey ID
        - OSS_ACCESS_KEY_SECRET: 阿里云 AccessKey Secret
        - OSS_BUCKET_NAME: OSS Bucket 名称
        - OSS_PREFIX: OSS 存储路径前缀，默认为 "industry-radar/"
        - LLM_API_KEY: LLM API Key (用于增量对比)
        - LLM_ENDPOINT: 可选，LLM API endpoint
    """
    request_id = context.request_id if hasattr(context, 'request_id') else 'unknown'
    logger.info(f"[{request_id}] FC function triggered")
    
    # 解析 event
    keyword = DEFAULT_KEYWORD
    try:
        if isinstance(event, bytes):
            if event:
                event_dict = json.loads(event.decode('utf-8'))
                keyword = event_dict.get('keyword', DEFAULT_KEYWORD)
            else:
                logger.info(f"[{request_id}] Empty event, using default keyword")
        elif isinstance(event, dict):
            keyword = event.get('keyword', DEFAULT_KEYWORD)
        else:
            logger.warning(f"[{request_id}] Unexpected event type: {type(event)}")
    except Exception as e:
        logger.warning(f"[{request_id}] Failed to parse event: {e}, using default keyword")
    
    # 从环境变量获取 keyword 覆盖（可选）
    env_keyword = os.environ.get('KEYWORD')
    if env_keyword:
        keyword = env_keyword
        logger.info(f"[{request_id}] Using keyword from environment: {keyword}")
    
    # 验证必需的环境变量
    required_env_vars = [
        'OSS_ACCESS_KEY_ID',
        'OSS_ACCESS_KEY_SECRET', 
        'OSS_BUCKET_NAME'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(f"[{request_id}] {error_msg}")
        return json.dumps({
            'status': 'error',
            'message': error_msg,
            'request_id': request_id
        }, ensure_ascii=False)
    
    # 执行主流程
    try:
        logger.info(f"[{request_id}] Starting pipeline with keyword: {keyword}")
        result = run_pipeline(keyword=keyword)
        
        changes_count = len(result.get('changes', []))
        conflicts_count = len(result.get('conflicts', []))
        
        logger.info(
            f"[{request_id}] Pipeline completed successfully. "
            f"Changes: {changes_count}, Conflicts: {conflicts_count}"
        )
        
        response = {
            'status': 'success',
            'keyword': keyword,
            'changes': changes_count,
            'conflicts': conflicts_count,
            'request_id': request_id
        }
        
        return json.dumps(response, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"[{request_id}] Pipeline failed with error: {str(e)}", exc_info=True)
        
        response = {
            'status': 'error',
            'keyword': keyword,
            'message': str(e),
            'request_id': request_id
        }
        
        return json.dumps(response, ensure_ascii=False)


def local_test():
    """本地调试函数"""
    class MockContext:
        request_id = "local-test-001"
    
    # 模拟定时触发（空 event）
    print("=== Test 1: Empty event (cron trigger) ===")
    result = handler(b'', MockContext())
    print(f"Result: {result}\n")
    
    # 模拟带参数的触发
    print("=== Test 2: Event with keyword ===")
    event_data = json.dumps({'keyword': '芯片'}).encode('utf-8')
    result = handler(event_data, MockContext())
    print(f"Result: {result}\n")


if __name__ == '__main__':
    """
    本地调试运行方式：
    
    1. 设置环境变量（在终端或使用 .env 文件）：
       export OSS_ACCESS_KEY_ID="your_access_key_id"
       export OSS_ACCESS_KEY_SECRET="your_access_key_secret"
       export OSS_BUCKET_NAME="your_bucket_name"
       export OSS_ENDPOINT="oss-cn-hangzhou.aliyuncs.com"
       export KEYWORD="半导体"  # 可选
    
    2. 运行测试：
       python files/role_a/fc_handler.py
    """
    print("Starting local test...\n")
    local_test()
