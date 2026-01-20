# 阿里云函数计算 (FC) 部署指南

本目录包含阿里云函数计算的部署文件和配置说明。

## 文件说明

- `fc_handler.py`: FC 入口文件，实现 handler(event, context) 函数
- `requirements.txt`: Python 依赖包列表
- `fc_config.yaml`: FC 函数配置示例（可选）
- `README.md`: 本文档

## 环境变量配置

在 FC 控制台配置以下环境变量（**请勿硬编码到代码中**）：

### 必需环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `OSS_ACCESS_KEY_ID` | 阿里云 OSS AccessKey ID | `LTAI5t...` |
| `OSS_ACCESS_KEY_SECRET` | 阿里云 OSS AccessKey Secret | `xxx...` |
| `OSS_ENDPOINT` | OSS Endpoint 地址 | `oss-cn-hangzhou.aliyuncs.com` |
| `OSS_BUCKET` | OSS Bucket 名称 | `industry-radar-data` |
| `OSS_PREFIX` | OSS 对象存储前缀 | `reports/` |
| `DEFAULT_KEYWORD` | 默认监控关键词 | `半导体` |

### 可选环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `LLM_API_KEY` | LLM API 密钥（用于增量对比） | `sk-...` |
| `LLM_MODEL` | LLM 模型名称 | `qwen-max` / `gpt-4o` |
| `LLM_ENDPOINT` | LLM API 端点 | `https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation` |
| `ALERT_WEBHOOK` | 告警 Webhook 地址（钉钉/企业微信） | `https://oapi.dingtalk.com/robot/send?access_token=...` |

## 部署步骤

### 1. 准备工作

#### 1.1 安装阿里云 CLI 工具

```bash
# 安装 Serverless Devs
npm install -g @serverless-devs/s

# 配置阿里云账号
s config add
```

按提示输入：
- AccountID
- AccessKeyID
- AccessKeySecret
- Region (如 cn-hangzhou)

#### 1.2 创建 OSS Bucket

在阿里云 OSS 控制台创建 Bucket：
- 名称：`industry-radar-data`（或自定义）
- 区域：选择与 FC 相同区域
- 存储类型：标准存储
- 访问控制：私有

### 2. 函数部署

#### 2.1 方式一：使用 Serverless Devs 部署（推荐）

创建 `s.yaml` 配置文件：

```yaml
edition: 1.0.0
name: industry-radar
access: default

services:
  industry-radar-fc:
    component: fc
    props:
      region: cn-hangzhou
      service:
        name: industry-radar-service
        description: 行业雷达监控服务
        logConfig: auto
        role: acs:ram::YOUR_ACCOUNT_ID:role/aliyunfcdefaultrole
      function:
        name: radar-handler
        description: 行业雷达定时巡检函数
        runtime: python3.10
        codeUri: ./
        handler: fc_handler.handler
        timeout: 600
        memorySize: 512
        instanceConcurrency: 1
        environmentVariables:
          OSS_ACCESS_KEY_ID: ${env(OSS_ACCESS_KEY_ID)}
          OSS_ACCESS_KEY_SECRET: ${env(OSS_ACCESS_KEY_SECRET)}
          OSS_ENDPOINT: ${env(OSS_ENDPOINT)}
          OSS_BUCKET: ${env(OSS_BUCKET)}
          OSS_PREFIX: ${env(OSS_PREFIX)}
          DEFAULT_KEYWORD: ${env(DEFAULT_KEYWORD)}
          PYTHONPATH: /code
      triggers:
        - name: timer-trigger
          type: timer
          config:
            cronExpression: "0 0 */6 * * *"  # 每6小时执行一次
            enable: true
            payload: '{"keyword": "半导体"}'
```

部署命令：

```bash
# 进入 files/fc 目录
cd files/fc

# 部署函数
s deploy
```

#### 2.2 方式二：使用 FC 控制台手动部署

1. 登录阿里云 FC 控制台
2. 创建服务：`industry-radar-service`
3. 创建函数：
   - 函数名称：`radar-handler`
   - 运行环境：Python 3.10
   - 函数入口：`fc_handler.handler`
   - 超时时间：600 秒
   - 内存规格：512 MB
4. 上传代码：
   - 将 `fc_handler.py` 和 `../../codes/` 目录打包成 zip
   - 上传至 FC
5. 配置环境变量（见上文）
6. 添加定时触发器（见下文）

### 3. 配置定时触发器

#### 3.1 Cron 表达式说明

FC 定时触发器使用 6 位 Cron 表达式：`秒 分 时 日 月 周`

示例：

| 表达式 | 说明 |
|--------|------|
| `0 0 */6 * * *` | 每 6 小时执行一次（0点、6点、12点、18点） |
| `0 0 9 * * *` | 每天上午 9:00 执行 |
| `0 0 9,18 * * *` | 每天 9:00 和 18:00 执行 |
| `0 30 8 * * 1-5` | 工作日（周一至周五）8:30 执行 |
| `0 0 */4 * * *` | 每 4 小时执行一次 |

#### 3.2 在控制台配置

1. 进入函数详情页
2. 点击"触发器"标签
3. 添加触发器：
   - 触发器类型：定时触发器
   - 名称：`timer-trigger`
   - Cron 表达式：`0 0 */6 * * *`
   - 触发消息：`{"keyword": "半导体"}`（可选）
   - 启用触发器：是

### 4. 本地调试

#### 4.1 准备环境

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量（测试用）
export OSS_ACCESS_KEY_ID="your_key_id"
export OSS_ACCESS_KEY_SECRET="your_key_secret"
export OSS_ENDPOINT="oss-cn-hangzhou.aliyuncs.com"
export OSS_BUCKET="industry-radar-data"
export OSS_PREFIX="reports/"
export DEFAULT_KEYWORD="半导体"
```

#### 4.2 本地运行测试

```bash
# 方式1：直接运行
python fc_handler.py

# 方式2：使用 s local 工具
s local invoke -e '{"keyword": "新能源"}'
```

#### 4.3 使用 fun local 调试（可选）

```bash
# 安装 fun
npm install -g @alicloud/fun

# 本地调用
fun local invoke -e '{"keyword": "半导体"}'
```

## 函数参数说明

### event 参数

定时触发器可通过 `payload` 传递参数：

```json
{
  "keyword": "半导体"
}
```

HTTP 触发器可通过请求体传递：

```bash
curl -X POST https://your-fc-endpoint.fc.aliyuncs.com/invoke \
  -H "Content-Type: application/json" \
  -d '{"keyword": "新能源"}'
```

### 返回值

成功时：

```json
{
  "status": "success",
  "keyword": "半导体",
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "summary": {
    "changes": 3,
    "conflicts": 1
  },
  "details": {
    "changes": [...],
    "conflicts": [...]
  }
}
```

失败时：

```json
{
  "status": "error",
  "keyword": "半导体",
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "error": {
    "type": "ValueError",
    "message": "..."
  }
}
```

## 日志查看

### 在 FC 控制台查看

1. 进入函数详情页
2. 点击"日志查询"标签
3. 查看函数执行日志

### 使用 CLI 查看

```bash
# 查看最近 10 条日志
s logs -t

# 实时跟踪日志
s logs -t --tail
```

## 监控告警

### 配置告警规则

在云监控（CloudMonitor）中配置告警：

1. 监控项：
   - 函数错误次数
   - 函数执行时间
   - 函数调用次数
2. 告警条件：
   - 错误次数 > 0
   - 执行时间 > 300 秒
3. 通知方式：
   - 短信
   - 邮件
   - 钉钉机器人

### 自定义告警

在代码中实现告警逻辑：

```python
import requests

def send_alert(message: str):
    """发送钉钉告警"""
    webhook = os.getenv("ALERT_WEBHOOK")
    if webhook:
        requests.post(webhook, json={
            "msgtype": "text",
            "text": {"content": message}
        })
```

## 费用估算

以每 6 小时执行一次，每次执行 30 秒为例：

- 调用次数：4 次/天 × 30 天 = 120 次/月
- 计算时长：120 次 × 30 秒 = 3600 秒 ≈ 1 小时
- 内存：512 MB

**费用**（按量付费）：
- 调用次数费用：免费（每月前 100 万次免费）
- 计算费用：约 0.01 元/月
- **总计**：< 0.1 元/月（几乎免费）

## 故障排查

### 常见问题

1. **函数执行超时**
   - 增加超时时间（最大 600 秒）
   - 优化代码性能

2. **内存不足**
   - 增加内存规格（最大 32 GB）

3. **依赖包导入失败**
   - 检查 requirements.txt
   - 使用层（Layer）管理依赖

4. **OSS 权限错误**
   - 检查 AccessKey 是否正确
   - 确认 Bucket 权限配置

5. **环境变量未生效**
   - 在 FC 控制台检查环境变量配置
   - 重新部署函数

### 日志分析

关键日志标识：

- `[FC Handler] Request ID`: 请求 ID
- `[FC Handler] Pipeline starting`: 流程开始
- `[FC Handler] Pipeline completed`: 流程成功
- `[FC Handler] Pipeline failed`: 流程失败
- `[StorageClient]`: 存储层日志
- `[ScraperAgent]`: 采集层日志

## 最佳实践

1. **环境分离**：使用不同的服务/函数区分开发、测试、生产环境
2. **版本管理**：使用 FC 版本和别名功能管理版本
3. **预留实例**：高频调用场景下使用预留实例降低冷启动延迟
4. **并发控制**：设置合理的实例并发度（建议 1）
5. **日志分级**：使用 INFO/WARNING/ERROR 分级记录日志
6. **监控告警**：配置完善的监控和告警机制
7. **成本优化**：按需调整内存规格和超时时间

## 参考资料

- [阿里云函数计算文档](https://help.aliyun.com/product/50980.html)
- [Serverless Devs 文档](https://www.serverless-devs.com/fc/readme)
- [定时触发器配置](https://help.aliyun.com/document_detail/68172.html)
- [Python Runtime 文档](https://help.aliyun.com/document_detail/74756.html)
