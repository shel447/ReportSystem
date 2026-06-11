# 外部依赖接口技术契约

本文件集中描述 ReportSystem 为适配生产平台而主动调用的外部依赖。模板作者可配置的 `Parameter Options`、`Dynamic Custom` 与 `API Dataset` 扩展点仍见 [API 技术契约](README.md#3-模板声明型外部扩展协议)。

## 1. 通用约束

### 1.1 调用方式

- 除 OpenAI Compatible 外，平台接口默认通过统一平台 HTTP Client 调用。
- 平台接口默认使用 `Content-Type: application/json`。
- 涉及用户业务数据的调用必须携带可信身份头：

```http
X-User-Id: <external-user-id>
```

- 平台统一认证信息由部署环境提供；存在时通过 `Authorization` 传递。
- HTTP 错误、超时、非 JSON 响应或非 JSON object 响应统一视为上游调用失败。
- 本文件只定义 ReportSystem 发送和消费的字段。平台响应可以增加扩展字段。

### 1.2 Schema 与示例

模块级消费者 Schema 位于 [schemas](../schemas/README.md)，集中示例位于 [external-dependencies.example.json](../schemas/examples/external-dependencies.example.json)。

| 模块 | Schema |
|---|---|
| OpenAI Compatible | [openai-compatible.schema.json](../schemas/openai-compatible.schema.json) |
| AgentCore | [agentcore.schema.json](../schemas/agentcore.schema.json) |
| Guardrail | [guardrail.schema.json](../schemas/guardrail.schema.json) |
| DataCatalog | [datacatalog.schema.json](../schemas/datacatalog.schema.json) |
| Knowledge/RAG | [knowledge-rag.schema.json](../schemas/knowledge-rag.schema.json) |
| NodeAgent | [nodeagent.schema.json](../schemas/nodeagent.schema.json) |
| Audit | [audit.schema.json](../schemas/audit.schema.json) |
| OneQuery | [onequery.schema.json](../schemas/onequery.schema.json) |
| DataCatalog Metadata Sync | [metadata-sync.schema.json](../schemas/metadata-sync.schema.json) |

模板声明型 API Dataset 协议见 [API 技术契约：API Dataset 外部数据源](README.md#33-api-dataset-外部数据源)。

### 1.3 Policy Authentication

Policy Authentication 用于 ReportSystem 公开业务接口的前置权限校验。

```http
POST /rest/plat/priv/v1/policy/authentication
```

请求：

```json
{
  "userId": "user_001",
  "requests": [
    {"requestId": "generated-request-id", "action": "dte.bi.chat.edit"}
  ]
}
```

响应按请求顺序返回逐项结果：

```json
{
  "results": [
    {"result": true}
  ]
}
```

任一 `result=false` 时 ReportSystem 抛出 `auth failed`，对外返回 HTTP 403 与 `chatbi.base.permission.denied`，并异步投递安全审计。超时、HTTP 错误、结果数量不匹配和非法报文均 fail-closed。

## 2. OpenAI Compatible

OpenAI Compatible 服务用于模板语义召回、参数提取、诉求整理、内容生成和智能问数。地址、模型和凭证由系统设置提供，认证头使用：

```http
Authorization: Bearer <api-key>
```

### 2.1 对话补全

```http
POST {baseUrl}/chat/completions
```

请求字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `model` | `string` | 是 | 模型名称 |
| `messages` | `object[]` | 是 | 对话消息；每项至少包含 `role/content` |
| `temperature` | `number` | 是 | 采样温度 |
| `max_tokens` | `integer` | 否 | 最大输出 token 数 |

响应至少包含：

```json
{
  "model": "mock-chat",
  "choices": [
    {
      "message": {
        "content": "生成结果"
      }
    }
  ]
}
```

`content` 可以是字符串，也可以是带 `text` 的内容块数组。

### 2.2 向量化

```http
POST {baseUrl}/embeddings
```

请求包含 `model` 和字符串数组 `input`。响应 `data[]` 中每项必须包含数值数组 `embedding`。

## 3. AgentCore

AgentCore 是会话和轮次的事实源。ReportSystem 创建会话和轮次，将完整回答 upsert 到 AgentCore，并从 AgentCore 查询历史。

所有 AgentCore 调用必须携带 `X-User-Id`。

### 3.1 创建会话

```http
POST /rest/naie/aiagentcore/v1/conversation
```

请求：

```json
{
  "title": "网络运行日报",
  "description": "生成总部网络运行日报"
}
```

响应至少包含 `conversationId`。

### 3.2 创建轮次

```http
POST /rest/naie/aiagentcore/v1/chat/create
```

请求包含 `conversationId/question`，响应至少包含 `chatId`。

### 3.3 归档或更新轮次

```http
POST /rest/naie/aiagent/v1/chat/import
```

该接口具有 **upsert** 语义：同一 `conversationId + chatId` 再次提交时覆盖该轮已归档内容。写入结构与 AgentCore 历史查询的单条 `records[]` 保持核心一致：一条记录表示一轮对话，`question` 是用户主动提问，`answers[]` 按时间顺序保存系统回答片段。

```json
{
  "conversationId": "conv_001",
  "chatId": "chat_001",
  "question": "生成总部网络运行日报",
  "askTime": 1780368000000,
  "answers": [
    {
      "type": "TEXT",
      "content": "已收到请求，正在分析报告诉求。",
      "answerTime": 1780368000100
    },
    {
      "type": "PIU",
      "content": "{\"piuName\":\"ReportGenerationPIU\",\"answers\":{\"steps\":[{\"stepId\":\"step_root\",\"title\":\"生成总部网络运行日报\",\"type\":\"directory\",\"status\":\"running\"}],\"ask\":null,\"delta\":[],\"answer\":null,\"errors\":[]}}",
      "answerTime": 1780368000300
    }
  ]
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `conversationId` | `string` | 是 | 会话 ID |
| `chatId` | `string` | 是 | 本轮对话 ID |
| `question` | `string` | 是 | 用户主动发起的提问或确认动作说明 |
| `askTime` | `number/string` | 是 | 用户提问时间；生产推荐毫秒时间戳 |
| `answers` | `object[]` | 是 | 系统回答片段，按时间顺序排列 |

`Answer` 字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `type` | `TEXT \| PIU` | 是 | `TEXT` 为可直接展示文本；`PIU` 为前端组件渲染内容 |
| `content` | `string` | 是 | TEXT 时为文本；PIU 时为 JSON 字符串 |
| `answerTime` | `number/string` | 是 | 回答片段产生时间；生产推荐毫秒时间戳 |

`type=PIU` 时，`content` 反序列化后固定包含：

```json
{
  "piuName": "ReportGenerationPIU",
  "answers": {
    "steps": [],
    "ask": null,
    "delta": [],
    "answer": null,
    "errors": []
  }
}
```

其中每条外层 `answers[]` 记录只承载一种有效内容：某条记录可以是进度 `steps`，也可以是追问 `ask`、增量 `delta`、最终 `answer` 或错误 `errors`；不会把一轮流程的所有有效内容塞进同一个 PIU `content`。

### 3.4 查询会话历史

```http
POST /rest/naie/aiagentcore/v2/chat/history
```

请求包含 `conversationId/pageNum/pageSize`。响应使用 `records[]` 返回轮次；每项使用与 `chat/import` 相同的核心结构：`chatId/question/askTime/answers[]`。

### 3.5 查询单轮详情

```http
GET /rest/naie/aiagentcore/v1/chat/detail/{chatId}
```

响应结构与历史查询中的单条 `records[]` 一致。

### 3.6 查询会话列表

```http
GET /rest/naie/aiagentcore/v1/conversations?pageNum=1&pageSize=20
```

标准响应使用 `records[]`。每项包含 `conversationId`，并可携带 `title/status/updatedAt/lastMessagePreview`。

### 3.7 兼容读取说明

正式写入始终使用上述标准结构。为读取既有平台历史数据，适配器兼容以下非标准变体：

- 会话列表记录容器兼容 `records/results/data`，`data.results` 也可读取。
- 会话或轮次主键兼容历史字段 `id`。
- `answers` 正式结构为数组；历史读取兼容 JSON 字符串和带 `content.answers` 的旧包装结构。
- `question` 兼容字符串、JSON 字符串和内容块数组。

这些变体只用于历史兼容，不作为新接入方的推荐协议。

## 4. Guardrail

Guardrail 在用户问题、最终回答和 SQL/Python 执行前进行安全检查。业务流程默认按 fail-closed 处理非法响应。

### 4.1 问题检查

```http
POST /rest/naie/guardrail/v1/question/check
```

```json
{
  "questions": ["帮我生成网络日报"]
}
```

### 4.2 回答检查

```http
POST /rest/naie/guardrail/v1/answer/check
```

```json
{
  "answers": ["网络运行状态整体稳定。"]
}
```

问题和回答检查响应：

```json
{
  "checkResults": [
    {
      "isLegal": true,
      "response": ""
    }
  ]
}
```

### 4.3 应用内容检查

```http
POST /rest/naie/guardrail/v1/application-sec/check
```

请求包含 `type/content`，其中 `type` 标识内容类型，例如 `sql` 或 `python`。

```json
{
  "status": false,
  "error_msg": ""
}
```

`status = true` 表示命中风险并阻断执行。

## 5. OneQuery

当系统执行 SQL/UQL 时调用：

```http
POST /rest/dte/v1/onequery/uql/query
```

请求包含渲染后的 `query` 和运行 `context`。响应使用 `retCode/retInfo/data.columns/data.results` 包络：

```json
{
  "retCode": 0,
  "retInfo": "",
  "data": {
    "columns": {
      "health_score": {
        "type": "double",
        "lineageTracing": {
          "type": "original",
          "sources": [
            {
              "dataSourceName": "network_health",
              "dataSourceType": "logicalEntity",
              "field": "health_score",
              "businessName": "Health Score",
              "businessName_cn": "健康评分",
              "enumValues": "",
              "ui": ""
            }
          ]
        }
      }
    },
    "results": [
      {
        "health_score": 96
      }
    ]
  }
}
```

规则：

- `retCode/retInfo` 必填；consumer 保留原始 `retCode`，不得通过整数转换丢失前导零。
- 整数 `0` 或字符串 `"0"` 表示成功，此时必须返回 `data.columns/data.results`。
- `retCode != 0` 表示业务失败；报告生成场景降级为空数据并记录告警，智能问数场景返回明确错误。
- 字符串 `"04003"` 表示数据源不支持 `CONNECT BY`，智能问数映射为 `chatbi.data_analysis.query.unsupported_syntax`。
- 字符串 `"04023"` 表示查询字段不存在，智能问数映射为 `chatbi.data_analysis.query.field_not_found`。
- 上述两个精确错误不可重试，智能问数停止后续图表、总结和聚合节点；错误详情保留 `upstreamCode/retInfo/sql`。
- HTTP 错误、超时和非法结构属于上游调用失败。
- 开启 `context["lineage.tracing.enable"]` 时，每列必须返回非空血缘来源。

正式结构见 [onequery.schema.json](../schemas/onequery.schema.json)。

## 6. DataCatalog

DataCatalog 为智能问数提供实体、数据集和逻辑关系元数据。所有调用携带 `X-User-Id`，缓存必须按用户隔离。

| 用途 | 方法与路径 | 请求或查询参数 | 消费的响应字段 |
|---|---|---|---|
| 查询逻辑实体列表 | `POST /rest/odae/v3/datacatalog/model/logicalentities/list` | `pageSize/pageNo/filter.includeSchemaOfParent` | `retCode/retInfo/data.results` |
| 查询逻辑实体 | `GET /rest/odae/v3/datacatalog/model/logicalentity` | `logicalEntityName` | `data` |
| 查询数据集 | `GET /rest/odae/v3/datacatalog/model/datasets/{name}` | 路径参数 `name` | `data` |
| 查询逻辑关系列表 | `POST /rest/dte/v2/datacatalog/product/model/logicalrelations/query` | `pageSize/pageNo/filter` | `retCode/retInfo/data.results` |
| 查询逻辑关系 | `GET /rest/dte/v2/datacatalog/product/model/logicalrelation` | `name` | `retCode/retInfo/data` |

列表请求示例：

```json
{
  "pageSize": 100,
  "pageNo": 1,
  "filter": {
    "includeSchemaOfParent": true
  }
}
```

实体、数据集和关系对象由平台定义，ReportSystem 将其作为开放 JSON object 消费。

### 6.1 Metadata Sync 辅助刷新

Metadata Sync 是 DataCatalog 的辅助特性。ReportSystem 周期检查元数据版本；版本变化时清理 DataCatalog 与 RAG 缓存。

```http
GET /rest/entassistantservice/v1/chatbi/package/register/process
```

响应至少包含可比较的 `version` 或 `process`。正式结构见 [metadata-sync.schema.json](../schemas/metadata-sync.schema.json)。

## 7. Knowledge / RAG

Knowledge/RAG 为智能问数提供知识片段和 NL2SQL 样例。所有调用携带 `X-User-Id`；多索引检索缓存按用户和查询文本隔离。

### 7.1 查询知识

```http
GET /rest/naie/knwl/v1/knowledge
```

查询参数由业务场景提供，响应读取 `knowledgeList[]`。

### 7.2 单索引知识检索

```http
POST /rest/naie/rag/v1/retriever-klg
```

请求包含 `query/ragIndex/extensions/esTopN/vsTopN/rankTopN`，响应读取 `recommends[]`。

### 7.3 多索引检索

```http
POST /rest/naie/rag/v1/retriever
```

请求包含 `query/rankTopN/ragIndexes/ranking_options/enableHybridResults`，响应读取 `recommends[]`。

## 8. NodeAgent 配置

```http
GET /rest/nodeagent/v2/csi/appconf?watch=false
```

响应是开放配置对象。ReportSystem 在启动阶段读取其中 `chatbi.llm`、`chatbi.ai.embedding`、`chatbi.knowledge` 和 `chatbi.dataAnalysis`，合并到进程内 ConfigCenter。平台服务地址和 HTTP 基础设施配置由 `runtime.client` SDK 负责，不从该响应读取。

正式结构见 [nodeagent.schema.json](../schemas/nodeagent.schema.json)。

## 9. Audit

Audit 接收异步、尽力投递的审计事件。投递失败只记录日志，不阻塞主业务。

```http
POST /rest/plat/audit/v1/logs
POST /rest/plat/audit/v1/seculogs
```

公共请求字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `operation` | `string` | 是 | 操作名称 |
| `detail` | `string` | 是 | 操作详情 |
| `userId` | `string` | 是 | 外部用户标识 |
| `targetObj` | `string` | 是 | 操作对象，可为空字符串 |
| `source` | `string` | 是 | 来源系统，默认 `ReportSystem` |
| `terminal` | `string` | 是 | 终端类型，默认 `server` |
| `result` | `string` | 是 | 结果，默认 `SUCCESSFUL` |
| `level` | `string` | 是 | 级别，默认 `INFORMATION` |
| `dateTime` | `integer` | 是 | UTC epoch milliseconds |

操作审计发送到 `/logs`，安全审计发送到 `/seculogs`。请求体不携带内部字段 `kind`。
