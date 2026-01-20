# 角色 A（架构）实现总结

本文档总结了"角色 A（架构）"任务的完整实现，包括触发层、存储层、冲突仲裁和可靠性特性。

## 实现概览

### 1. 阿里云函数计算 (FC) 触发层

**位置**: `files/fc/`

#### 核心文件

- **fc_handler.py**: FC 入口函数
  - 实现 `handler(event, context)` 标准签名
  - 支持定时触发和手动触发
  - 完整的异常处理和日志记录
  - 本地调试支持（`local_test()` 函数）
  
- **s.yaml**: Serverless Devs 部署配置
  - 定时触发器配置（6 位 Cron 表达式）
  - 环境变量配置
  - 函数参数配置（内存、超时等）

- **README.md**: 完整的部署指南（6KB+）
  - 环境变量配置说明
  - 部署步骤（Serverless Devs / 手动部署）
  - 定时触发器配置
  - 本地调试方法
  - 常见问题排查

- **QUICKSTART.md**: 快速开始指南
  - 5 分钟本地测试
  - 10 分钟云端部署

- **.env.example**: 环境变量模板
  - 所有必需和可选的环境变量
  - 安全配置示例

- **requirements.txt**: Python 依赖
  - oss2>=2.18.0 (阿里云 OSS SDK)
  - requests>=2.31.0 (HTTP 请求)

#### 定时触发配置

默认 Cron 表达式：`0 0 */6 * * *`（每 6 小时执行一次）

支持的触发方式：
1. 定时触发（Timer Trigger）
2. HTTP 触发（可传入自定义参数）
3. 手动触发（测试用）

### 2. 增强的存储层

**文件**: `codes/storage_layer.py`

#### 新功能

1. **历史快照归档**
   - 自动保存到 `history/` 目录
   - 文件名格式：`report_YYYYMMDD_HHMMSS.json`
   - 永久保留，不会被覆盖

2. **最新数据索引**
   - `latest_fetch.json`: 最新抓取的原始数据（new_items）
   - `latest_report.json`: 最新报告（用于下次对比的 old_snapshot）
   - `current_report.json`: 备份快照（上一次的报告）

3. **增量对比支持**
   - `load_latest_snapshot()`: 加载旧快照（用于对比）
   - `load_latest_fetch()`: 加载最新抓取数据
   - `load_latest_report()`: 别名方法

4. **失败保护机制**
   - `save_snapshot(success=True/False)` 参数
   - 采集失败时不保存数据，保护旧数据不被覆盖
   - 详细的日志记录

#### 文件结构

```
data/
├── history/
│   ├── report_20260120_100000.json
│   ├── report_20260120_160000.json
│   └── ...
├── latest_fetch.json       # 最新抓取（new_items）
├── latest_report.json      # 最新报告（old_snapshot）
└── current_report.json     # 备份快照
```

### 3. 冲突仲裁增强

**文件**: `codes/conflict_resolution.py`

#### 优先级逻辑（硬编码）

| 来源类型 | 权重 | 说明 |
|---------|------|------|
| OFFICIAL（官方公告） | 1.0 | 最高优先级 |
| MEDIA（权威媒体） | 0.7 | 中等优先级 |
| RUMOR（市场传闻） | 0.3 | 最低优先级 |

#### 仲裁规则

1. **多来源冲突**
   - 选择权重最高的来源作为最终结论
   - 低权重来源标记为"待核实"（pending_sources）
   - 记录详细的仲裁理由

2. **单一来源**
   - 直接采纳，标记为"唯一来源"
   - 不存在待核实来源

3. **输出格式**
   ```python
   ConflictDecision(
       field="市场规模",
       final_value="115亿",
       chosen_source=SourceType.OFFICIAL,
       pending_sources=[SourceType.MEDIA, SourceType.RUMOR],
       reason="权重最高来源优先 (Weight=1.0)，其他来源待核实: media, rumor"
   )
   ```

#### 辅助函数

- `_normalize_source(source)`: 标准化来源类型，确保返回 SourceType 枚举

### 4. 配置管理

**文件**: `codes/config.py`

#### 环境变量（全部支持）

**必需配置**:
- `OSS_ACCESS_KEY_ID`: 阿里云 OSS AccessKey ID
- `OSS_ACCESS_KEY_SECRET`: 阿里云 OSS AccessKey Secret
- `OSS_ENDPOINT`: OSS Endpoint 地址
- `OSS_BUCKET`: OSS Bucket 名称
- `OSS_PREFIX`: OSS 对象存储前缀

**可选配置**:
- `DATA_DIR`: 本地数据目录（默认：`data`）
- `DEFAULT_KEYWORD`: 默认监控关键词（默认：`半导体`）
- `LLM_API_KEY`: LLM API 密钥
- `LLM_MODEL`: LLM 模型名称（默认：`qwen-max`）
- `LLM_ENDPOINT`: LLM API 端点
- `ALERT_WEBHOOK`: 告警 Webhook 地址

**安全性**:
- ✅ 所有敏感信息从环境变量读取
- ✅ 无硬编码密钥
- ✅ 所有默认值为安全占位符

### 5. 可靠性特性

**文件**: `codes/orchestrator.py`

#### 核心特性

1. **重试机制**
   - 采集失败时自动重试（最多 3 次）
   - 指数退避（可配置）
   - 记录每次重试的详细日志

2. **失败保护**
   - 采集失败时不覆盖旧数据
   - 区分真正的失败和合法的空结果
   - 保证数据一致性

3. **异常处理**
   - 全流程异常捕获
   - 分阶段错误处理（采集、对比、仲裁、存储）
   - 不会因单个阶段失败而中断整个流程

4. **日志记录**
   - 每个模块都有详细的日志
   - 统一的日志格式：`[ModuleName] Message`
   - 包含请求 ID、时间戳等上下文信息

#### 日志示例

```
[Pipeline] Starting pipeline for keyword: 半导体
[Pipeline] Attempt 1/3: Fetching data...
[ScraperAgent] Fetching data for keyword: 半导体
[ScraperAgent] Fetched 1 items
[Pipeline] Fetch succeeded, got 1 items
[Pipeline] Loading old snapshot for comparison...
[StorageClient] Loaded latest_report.json as old_snapshot
[Pipeline] Old snapshot loaded: 1 items from 20260120_071259
[Pipeline] Performing incremental comparison...
[IncrementalAnalysis] Comparing old snapshot (1 items) with new items (1 items)
[IncrementalAnalysis] Found 1 changes
[Pipeline] Found 1 changes
[Pipeline] Resolving conflicts...
[ConflictResolution] Field '增长率': single source, no conflict
[Pipeline] Resolved 1 conflicts
[Pipeline] Saving snapshot...
[StorageClient] Saved history snapshot: /path/to/history/report_20260120_071347.json
[StorageClient] Updated latest_fetch.json
[StorageClient] Updated current_report.json from latest_report.json
[StorageClient] Updated latest_report.json
[Pipeline] Snapshot saved: /path/to/history/report_20260120_071347.json
[Pipeline] Pipeline completed successfully
```

### 6. 其他改进

1. **代码质量**
   - 使用 pathlib 进行路径处理
   - 提取辅助函数减少重复代码
   - 完善的类型注解和文档字符串

2. **.gitignore**
   - 排除数据文件（data/）
   - 排除构建产物（__pycache__/）
   - 排除敏感文件（.env）

3. **文档**
   - 完整的部署指南
   - 快速开始指南
   - 环境变量模板
   - 代码注释和文档字符串

## 使用示例

### 本地测试

```bash
# 1. 安装依赖
cd files/fc
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 3. 运行测试
python fc_handler.py
```

### 部署到 FC

```bash
# 使用 Serverless Devs
cd files/fc
s deploy
```

### 手动触发

```bash
# 使用 s 工具
s invoke -e '{"keyword": "新能源"}'

# 使用 curl
curl -X POST https://your-fc-endpoint.fc.aliyuncs.com/invoke \
  -H "Content-Type: application/json" \
  -d '{"keyword": "半导体"}'
```

## 测试结果

所有功能已通过本地测试：

- ✅ FC handler 执行（默认和自定义关键词）
- ✅ 存储层（历史快照 + 最新索引）
- ✅ 冲突仲裁（优先级逻辑）
- ✅ 失败保护（数据不被覆盖）
- ✅ 代码安全（CodeQL 0 个告警）

## 后续优化建议

1. **数据源接入**
   - 接入真实的新闻 API
   - 支持多数据源并行采集

2. **LLM 集成**
   - 实现智能增量对比
   - 接入 Qwen-Max 或 GPT-4o

3. **告警通知**
   - 集成钉钉/企业微信机器人
   - 支持邮件/短信告警

4. **可观测性**
   - 接入 Prometheus/Grafana
   - 添加 Trace 和 Metrics

5. **性能优化**
   - 使用 OSS SDK 替换本地文件
   - 实现分布式锁避免竞态条件
   - 添加缓存层

## 相关文档

- [FC 部署指南](files/fc/README.md)
- [快速开始](files/fc/QUICKSTART.md)
- [环境变量配置](files/fc/.env.example)
- [Serverless Devs 配置](files/fc/s.yaml)

## 支持

如有问题，请查看：
- [阿里云 FC 文档](https://help.aliyun.com/product/50980.html)
- [Serverless Devs 文档](https://www.serverless-devs.com/)
- 项目 Issues
