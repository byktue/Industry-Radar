#!/bin/bash
# 本地调试脚本
# 用于快速测试 FC handler 功能

# 设置环境变量
export OSS_ACCESS_KEY_ID="${OSS_ACCESS_KEY_ID:-test_key_id}"
export OSS_ACCESS_KEY_SECRET="${OSS_ACCESS_KEY_SECRET:-test_secret}"
export OSS_BUCKET_NAME="${OSS_BUCKET_NAME:-test-bucket}"
export OSS_ENDPOINT="${OSS_ENDPOINT:-oss-cn-hangzhou.aliyuncs.com}"
export OSS_PREFIX="${OSS_PREFIX:-industry-radar/}"
export KEYWORD="${KEYWORD:-半导体}"
export DATA_DIR="${DATA_DIR:-./data}"

# 打印配置
echo "===== 本地调试配置 ====="
echo "OSS_BUCKET_NAME: $OSS_BUCKET_NAME"
echo "OSS_ENDPOINT: $OSS_ENDPOINT"
echo "KEYWORD: $KEYWORD"
echo "DATA_DIR: $DATA_DIR"
echo "========================"
echo ""

# 运行 FC handler
echo "Running FC handler..."
python files/role_a/fc_handler.py

# 显示生成的文件
echo ""
echo "===== 生成的文件 ====="
if [ -d "$DATA_DIR" ]; then
    echo "Data directory contents:"
    find "$DATA_DIR" -type f -o -type d | sort
else
    echo "Data directory not found: $DATA_DIR"
fi
