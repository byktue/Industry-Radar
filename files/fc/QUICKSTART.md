# 快速开始指南

本指南帮助您快速部署和测试行业雷达函数。

## 前置条件

- Python 3.10+
- 阿里云账号
- 已创建 OSS Bucket

## 本地测试（5 分钟）

### 1. 安装依赖

```bash
cd files/fc
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入您的配置
# vim .env
```

### 3. 本地运行

```bash
# 直接运行测试
python fc_handler.py

# 您应该看到类似输出：
# === Test 1: Default keyword ===
# {
#   "status": "success",
#   "keyword": "半导体",
#   ...
# }
```

## 部署到阿里云 FC（10 分钟）

### 方式一：使用 Serverless Devs（推荐）

```bash
# 1. 安装 Serverless Devs
npm install -g @serverless-devs/s

# 2. 配置阿里云账号
s config add

# 3. 编辑 s.yaml，替换 YOUR_ACCOUNT_ID

# 4. 部署
s deploy
```

### 方式二：使用 FC 控制台

详见 [README.md](README.md) 的"部署步骤"章节。

## 验证部署

### 手动触发测试

```bash
# 使用 s 工具调用
s invoke -e '{"keyword": "新能源"}'

# 或使用 curl
curl -X POST https://your-fc-endpoint.fc.aliyuncs.com/invoke \
  -H "Content-Type: application/json" \
  -d '{"keyword": "半导体"}'
```

### 查看日志

```bash
# 实时查看日志
s logs -t --tail
```

## 常见问题

### 1. 导入错误 (ImportError)

**问题**：`ModuleNotFoundError: No module named 'orchestrator'`

**解决方案**：
- 确保在部署时包含了 `codes/` 目录
- 检查 `s.yaml` 中的 `codeUri` 配置
- 确认环境变量 `PYTHONPATH=/code` 已设置

### 2. 权限错误

**问题**：`AccessDenied: You are not authorized to do this action`

**解决方案**：
- 检查 AccessKey 是否正确
- 确认 RAM 角色有 OSS 读写权限
- 查看 FC 日志获取详细错误信息

### 3. 超时错误

**问题**：函数执行超时

**解决方案**：
- 增加超时时间（最大 600 秒）
- 检查网络连接是否正常
- 优化代码性能

## 下一步

- 接入真实数据源（新闻 API、资讯网站）
- 集成 LLM 实现智能增量对比
- 配置告警通知（钉钉/企业微信）
- 部署到生产环境

## 帮助文档

- [完整部署指南](README.md)
- [阿里云 FC 文档](https://help.aliyun.com/product/50980.html)
- [Serverless Devs 文档](https://www.serverless-devs.com/)
