# 外部接口与用法

## 1. 说明

本篇只说明**系统依赖的外部接口或外部边界**，不说明本系统自己的 REST API。

当前分两类：

- 外部 HTTP 接口
- 外部依赖型技术接口 / 边界

## 2. 外部 HTTP 接口

### 2.1 OpenAI 兼容 Completion API

#### 接口定位

- 用途：统一的文本生成、结构化 JSON 生成、问数规划、参数抽取、故障诊断
- 外部路径：`/chat/completions`
- 当前适配入口：
  - `E:/code/codex_projects/ReportSystemV2/src/backend/infrastructure/ai/openai_compat.py`
  - `OpenAICompatGateway.chat_completion()`

#### 当前代码入口

主要调用点：

- `conversation/infrastructure/responses.py`
  - 通用对话回复
- `conversation/infrastructure/parameters.py`
  - chat 模式参数提取
- `conversation/infrastructure/capabilities.py`
  - 智能问数、故障诊断、能力级回复
- `report_runtime/infrastructure/generation.py`
  - 章节内容生成、v2 诉求生成
- `infrastructure/query/engine.py`
  - QuerySpec 规划、Ibis 代码生成
- `routers/system_settings.py`
  - Completion 连通性测试

#### 典型调用场景

- 报告生成中的章节内容生成
- `interaction_mode=chat` 参数追问场景的参数提取
- `smart_query` / `fault_diagnosis`
- 查询规划与 Ibis 代码生成
- 系统设置页的 completion 测试

#### 请求示例结构

```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "你是报告生成助手。"},
    {"role": "user", "content": "请输出章节内容。"}
  ],
  "temperature": 0.2,
  "max_tokens": 900
}
```

#### 响应示例结构

网关当前只依赖这一条读取路径：

```json
{
  "choices": [
    {
      "message": {
        "content": "...模型返回文本..."
      }
    }
  ],
  "model": "gpt-4o-mini"
}
```

如果 `content` 不是字符串而是 OpenAI-style content list，网关会把其中的 `text` 片段拼接成最终文本。

#### 超时 / 错误 / 重试策略

- 超时：由 `ProviderConfig.timeout_sec` 控制，默认 60 秒
- 重试：`OpenAICompatGateway` 本身**不做自动重试**
- 错误处理：
  - 非 2xx：抛出 `AIRequestError`
  - 非 JSON：抛出 `AIRequestError`
  - 返回结构缺失：抛出 `AIRequestError`
- 业务层映射：
  - 有的模块映射为 `ValidationError`
  - 有的模块映射为 `UpstreamError`
  - router 层最终可能转成 `400 / 502`

#### 配置来源

- `system_settings.completion_config`
- 构建入口：
  - `E:/code/codex_projects/ReportSystemV2/src/backend/infrastructure/settings/system_settings.py`
  - `build_completion_provider_config()`

#### 当前约束与边界

- 要求供应商兼容 OpenAI Chat Completions 语义
- 当前没有 stream 模式
- 当前没有统一重试 / 退避 / 熔断
- 上游错误透传较多，适合后续纳入统一 DFX 错误码体系

### 2.2 OpenAI 兼容 Embedding API

#### 接口定位

- 用途：模板语义索引构建和模板匹配召回
- 外部路径：`/embeddings`
- 当前适配入口：
  - `E:/code/codex_projects/ReportSystemV2/src/backend/infrastructure/ai/openai_compat.py`
  - `OpenAICompatGateway.create_embedding()`

#### 当前代码入口

主要调用点：

- `template_catalog/infrastructure/indexing.py`
  - 模板语义索引重建
  - 模板匹配时生成 query vector
- `routers/system_settings.py`
  - Embedding 连通性测试

#### 典型调用场景

- 模板更新后手动或批量重建 `template_semantic_indices`
- 对话首轮或模板匹配阶段，根据用户消息向量检索模板候选

#### 请求示例结构

```json
{
  "model": "text-embedding-3-small",
  "input": [
    "生成设备巡检日报",
    "巡检模板语义文本"
  ]
}
```

#### 响应示例结构

网关当前只依赖：

```json
{
  "data": [
    {"embedding": [0.1, 0.2, 0.3]}
  ]
}
```

#### 超时 / 错误 / 重试策略

- 与 Completion 共用同一 HTTP 客户端策略
- 无自动重试
- 返回结构缺失或 embedding 不是列表时抛 `AIRequestError`

#### 配置来源

- `system_settings.embedding_config`
- 构建入口：`build_embedding_provider_config()`

#### 当前约束与边界

- 要求返回顺序与输入顺序一致
- 当前 embedding 向量直接存到 `template_semantic_indices.embedding_vector` JSON 列中
- 当前没有接入独立向量库，匹配仍在应用内完成

## 3. 外部依赖型技术接口 / 边界

### 3.1 SQLite 样例分析库

#### 接口定位

- 用途：为智能问数、章节证据查询、Ibis 编译执行提供样例业务数据
- 当前代码入口：
  - `E:/code/codex_projects/ReportSystemV2/src/backend/infrastructure/demo/telecom.py`
  - `E:/code/codex_projects/ReportSystemV2/src/backend/infrastructure/demo/dynamic_sources.py`

#### 典型调用场景

- `query/engine.py` 执行编译后的 SQL
- `query/section_evidence.py` 执行章节证据查询
- `dynamic_sources.py` 提供动态枚举候选
- `rendering.py` 中的一些直接样例数据读取

#### 使用方式

- 数据库路径由 `get_demo_db_path()` 返回
- 读连接通过 `open_demo_connection()` 或直接 `sqlite3.connect()` 创建
- schema registry 由 `get_schema_registry()` / `get_schema_registry_text()` 提供给 prompt 和 planner

#### 错误与约束

- 当前主要用本地文件 SQLite，不做连接池
- 连接失败或 SQL 执行失败直接抛出 sqlite3 异常，再由上层包装成业务错误
- 当前样例库是演示用途，不承担大规模并发能力

### 3.2 Ibis 编译到 SQL

#### 接口定位

- 用途：实验性查询链路 `NL -> QuerySpec -> Ibis -> SQL -> SQLite`
- 当前代码入口：
  - `E:/code/codex_projects/ReportSystemV2/src/backend/infrastructure/query/engine.py`
  - `E:/code/codex_projects/ReportSystemV2/src/backend/infrastructure/query/section_evidence.py`

#### 典型调用场景

- 智能问数
- 报告章节的数据准备/证据查询
- benchmark 跑数

#### 使用方式

- 先由 LLM 输出 QuerySpec JSON 或直接输出 Ibis 代码
- 通过 AST 白名单校验限制 Python 语法和 Ibis 可调用方法
- 使用 `ibis.sqlite.connect(get_demo_db_path())` 编译成 SQL
- 再在 SQLite 上实际执行并回收 sample rows 与 row_count

#### 错误与约束

- 当前只支持 SQLite backend
- 只允许有限的 Ibis 方法白名单
- 结果行数建议上限 50，sample rows 固定最多 10
- planner/codegen 都依赖上游 Completion API

### 3.3 Markdown 文档文件落盘

#### 接口定位

- 用途：把报告实例导出为 Markdown 文件并登记到 `report_documents`
- 当前代码入口：
  - `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/report_runtime/infrastructure/documents.py`

#### 典型调用场景

- 对话确认生成后的自动 Markdown 创建
- 报告聚合视图中的文档下载

#### 使用方式

- `create_markdown_document(db, instance_id)`
- 当前格式归一化只支持 `md / markdown`
- 文件写入后创建 `ReportDocument` 记录
- 下载时通过 `resolve_document_absolute_path()` 解析物理路径

#### 错误与约束

- 当前只支持 Markdown，不支持 PDF/Word
- 文件系统写入失败会直接中断创建
- 数据库记录和物理文件都需要存在，下载才算可用
- 当前没有对象存储或远程文件仓库抽象

## 4. 外部接口配置与装配总览

| 接口 / 边界 | 配置来源 | 主要入口 |
|-------------|----------|----------|
| Completion API | `system_settings.completion_config` | `OpenAICompatGateway.chat_completion()` |
| Embedding API | `system_settings.embedding_config` | `OpenAICompatGateway.create_embedding()` |
| SQLite demo DB | 本地文件路径 `telecom_demo.db` | `demo/telecom.py` |
| Ibis compile | Python 依赖 `ibis-framework[sqlite]` | `query/engine.py` |
| Markdown file storage | 本地文件系统 | `report_runtime/infrastructure/documents.py` |

## 5. 当前实现边界

- 当前外部接口统一适配主要集中在 `OpenAICompatGateway`，还没有更细粒度的 provider abstraction
- Completion/Embedding 都采用同步 `httpx.Client`，没有 async client、streaming 和统一重试
- SQLite/Ibis 链路仍是单机样例型实现
- 文档存储仍是本地文件系统，不适合直接外推为生产对象存储方案
