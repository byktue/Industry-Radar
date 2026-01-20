# 阿里云函数计算 (FC) 部署指南

## 概述

本目录包含 Industry-Radar 项目的阿里云函数计算（Alibaba Cloud Function Compute）部署文件和配置。

## 目录结构

```
files/role_a/
├── fc_handler.py          # FC 入口函数
├── README.md              # 本文件，部署说明
└── fc_config_example.yml  # FC 配置示例（待创建）
```

## 环境变量配置

在阿里云 FC 控制台配置以下环境变量：

### 必需环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `OSS_ACCESS_KEY_ID` | 阿里云 AccessKey ID | `LTAI5t...` |
| `OSS_ACCESS_KEY_SECRET` | 阿里云 AccessKey Secret | `xxx...` |
| `OSS_BUCKET_NAME` | OSS Bucket 名称 | `industry-radar` |

### 可选环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OSS_ENDPOINT` | OSS Endpoint | `oss-cn-hangzhou.aliyuncs.com` |
| `OSS_PREFIX` | OSS 存储路径前缀 | `industry-radar/` |
| `KEYWORD` | 行业关键词 | `半导体` |
| `LLM_API_KEY` | LLM API Key | - |
| `LLM_ENDPOINT` | LLM API Endpoint | - |
| `LOG_LEVEL` | 日志级别 | `INFO` |

## 定时触发配置

### Cron 表达式示例

在 FC 控制台创建定时触发器，配置 Cron 表达式：

```
# 每 6 小时执行一次
0 */6 * * *

# 每天凌晨 2 点执行
0 2 * * *

# 每周一上午 9 点执行
0 9 * * 1

# 每天早中晚三次（8:00, 14:00, 20:00）
0 8,14,20 * * *
```

### 触发器配置步骤

1. 登录阿里云 FC 控制台
2. 选择对应的服务和函数
3. 点击「触发器」标签
4. 点击「创建触发器」
5. 触发器类型选择「定时触发器」
6. 输入 Cron 表达式
7. 配置触发消息（可选，JSON 格式）：
   ```json
   {
     "keyword": "半导体"
   }
   ```

## 部署步骤

### 方式一：通过 FC 控制台部署

1. **创建服务**
   - 登录阿里云 FC 控制台
   - 创建新服务，命名如 `industry-radar-service`
   - 配置日志服务（推荐）

2. **创建函数**
   - 运行环境：`Python 3.9` 或 `Python 3.10`
   - 函数入口：`fc_handler.handler`
   - 内存规格：建议 512MB 或以上
   - 超时时间：建议 300 秒（5 分钟）

3. **上传代码**
   - 方式 A：将整个项目打包为 zip，上传
     ```bash
     cd /path/to/Industry-Radar
     zip -r industry-radar.zip codes/ files/ -x "*.pyc" -x "__pycache__/*"
     ```
   - 方式 B：使用 OSS 存储代码包（推荐大于 50MB 的包）

4. **配置环境变量**
   - 在函数配置页面添加上述必需环境变量

5. **配置触发器**
   - 按照「定时触发配置」章节添加定时触发器

### 方式二：使用 Serverless Devs 工具部署

1. **安装 Serverless Devs**
   ```bash
   npm install -g @serverless-devs/s
   ```

2. **配置密钥**
   ```bash
   s config add
   # 按提示输入 AccessKey ID 和 Secret
   ```

3. **创建配置文件** `s.yaml`：
   ```yaml
   edition: 1.0.0
   name: industry-radar
   access: default
   
   services:
     industry-radar:
       component: fc
       props:
         region: cn-hangzhou
         service:
           name: industry-radar-service
           description: Industry Radar Intelligence Agent
           logConfig:
             project: industry-radar-logs
             logstore: function-logs
         function:
           name: industry-radar-pipeline
           description: Main pipeline function
           runtime: python3.9
           codeUri: ./
           handler: files.role_a.fc_handler.handler
           memorySize: 512
           timeout: 300
           environmentVariables:
             OSS_ACCESS_KEY_ID: ${env(OSS_ACCESS_KEY_ID)}
             OSS_ACCESS_KEY_SECRET: ${env(OSS_ACCESS_KEY_SECRET)}
             OSS_BUCKET_NAME: ${env(OSS_BUCKET_NAME)}
             OSS_ENDPOINT: oss-cn-hangzhou.aliyuncs.com
             KEYWORD: 半导体
         triggers:
           - name: timer-trigger
             type: timer
             config:
               cronExpression: 0 */6 * * *
               enable: true
   ```

4. **部署**
   ```bash
   # 设置环境变量
   export OSS_ACCESS_KEY_ID="your_key_id"
   export OSS_ACCESS_KEY_SECRET="your_key_secret"
   export OSS_BUCKET_NAME="your_bucket"
   
   # 部署到云端
   s deploy
   ```

## 本地调试

### 前置准备

1. **安装依赖**
   ```bash
   cd /path/to/Industry-Radar
   pip install -r requirements.txt  # 如果有的话
   ```

2. **设置环境变量**
   
   创建 `.env` 文件或在终端设置：
   ```bash
   export OSS_ACCESS_KEY_ID="your_access_key_id"
   export OSS_ACCESS_KEY_SECRET="your_access_key_secret"
   export OSS_BUCKET_NAME="your_bucket_name"
   export OSS_ENDPOINT="oss-cn-hangzhou.aliyuncs.com"
   export KEYWORD="半导体"
   ```

### 运行测试

```bash
# 直接运行 fc_handler.py
python files/role_a/fc_handler.py
```

### 使用 FC Local 工具调试

```bash
# 安装 fc-local
pip install fc-local

# 运行本地调试
fun local invoke -f industry-radar-pipeline
```

## OSS 存储结构

函数运行时会在 OSS 中创建以下目录结构：

```
{OSS_PREFIX}/
├── history/                    # 历史快照
│   ├── 20260120_080000/
│   │   ├── fetch.json         # 原始抓取数据
│   │   └── report.json        # 分析报告
│   └── 20260120_140000/
│       ├── fetch.json
│       └── report.json
├── latest_fetch.json          # 最新抓取数据
└── current_report.json        # 当前报告（用于增量对比）
```

## 日志查看

### FC 控制台查看

1. 进入函数详情页
2. 点击「日志查询」标签
3. 选择时间范围查看执行日志

### 使用 SLS 日志服务

如果配置了日志服务，可以在 SLS 控制台进行高级查询：

```sql
* | select * from log where request_id = 'xxx'
```

## 监控和告警

### 配置告警规则

1. 进入云监控控制台
2. 选择函数计算监控
3. 创建告警规则：
   - 函数执行失败次数 > 3
   - 函数执行错误率 > 10%
   - 函数执行时间 > 240秒

### 钉钉告警推送

在告警规则中配置通知方式，选择钉钉机器人 Webhook。

## 故障排查

### 常见问题

1. **"Missing required environment variables" 错误**
   - 检查环境变量是否在 FC 控制台正确配置
   - 确认变量名拼写正确

2. **"No module named 'codes'" 错误**
   - 确认代码包包含完整的 `codes/` 目录
   - 检查 `fc_handler.py` 中的 `sys.path` 设置

3. **OSS 访问权限错误**
   - 确认 AccessKey 有 OSS 读写权限
   - 检查 Bucket 名称和 Endpoint 是否正确

4. **函数超时**
   - 增加函数超时时间（建议 300 秒以上）
   - 优化采集和分析逻辑，减少执行时间

### 调试技巧

1. **增加日志输出**
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info("Debug info here")
   ```

2. **使用 FC 内置的 context**
   ```python
   print(f"Request ID: {context.request_id}")
   print(f"Function name: {context.function_name}")
   ```

3. **本地模拟 FC 环境**
   - 使用 `fun local` 工具
   - 或直接运行 `fc_handler.py` 的 `local_test()` 函数

## 性能优化建议

1. **使用函数实例预留**
   - 对于频繁执行的函数，配置实例预留避免冷启动

2. **优化代码包大小**
   - 只打包必要的依赖
   - 使用层（Layer）管理公共依赖

3. **并发控制**
   - 合理设置函数并发度
   - 避免对下游服务造成压力

4. **使用 VPC**
   - 如果需要访问 VPC 内资源，配置 VPC 网络

## 安全建议

1. **AccessKey 管理**
   - 不要在代码中硬编码 AccessKey
   - 定期轮换 AccessKey
   - 使用 RAM 角色授权（推荐）

2. **最小权限原则**
   - 为函数分配最小必要权限
   - 只授予 OSS 特定 Bucket 的读写权限

3. **敏感信息保护**
   - 使用 FC 环境变量加密功能
   - 或使用 KMS 加密敏感配置

## 参考资料

- [阿里云函数计算文档](https://help.aliyun.com/product/50980.html)
- [Serverless Devs 工具](https://www.serverless-devs.com/)
- [Python Runtime 说明](https://help.aliyun.com/document_detail/56316.html)
- [定时触发器配置](https://help.aliyun.com/document_detail/68172.html)
