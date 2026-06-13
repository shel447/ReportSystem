# JSON Schema 契约索引

本目录保存 ReportSystem 的正式 JSON Schema。Schema 是结构契约的唯一事实源，示例只用于阅读和测试，不替代 Schema。

## 1. 如何使用

本目录有两类 Schema：

- **根 Schema**：直接校验完整 JSON 对象，例如 [report-template.schema.json](report-template.schema.json)。
- **Fragment 集合**：一个文件中保存同一外部模块的多组 Request / Response，通过 `schema.json#/$defs/FragmentName` 引用，例如 [agentcore.schema.json#/$defs/ImportChatRequest](agentcore.schema.json#/$defs/ImportChatRequest)。

使用状态：

| 状态 | 含义 |
|---|---|
| 运行时校验 | 生产调用链会直接读取 Schema 校验数据 |
| 契约测试 | 通过自动化测试约束适配器边界；运行时由强类型模型或适配器执行等价校验 |
| 文档契约 | 用于公开说明结构，暂未在生产路径重复校验 |

运行时代码如需校验，必须直接读取本目录文件，不得在代码目录复制 Schema 镜像。

## 2. 报告核心模型

| Schema | 校验对象 | 类型 | 使用状态 | 说明与示例 |
|---|---|---|---|---|
| [report-template.schema.json](report-template.schema.json) | 静态报告模板资产 | 根 Schema | 运行时校验 | [模板字段手册](../manuals/报告模板定义与使用说明书.md)、[flow 示例](examples/report-template.example.json)、[paged 示例](examples/report-template-paged.example.json) |
| [template-instance.schema.json](template-instance.schema.json) | 对话中的模板运行态快照 | 根 Schema | 运行时校验 | [示例](examples/template-instance.example.json) |
| [report-dsl.schema.json](report-dsl.schema.json) | 冻结后的正式 Report DSL | 根 Schema + fragment | 运行时校验 | [DSL 字段手册](../manuals/报告DSL定义与使用说明书.md)、[flow 示例](examples/report-dsl.example.json)、[paged 示例](examples/report-dsl-paged.example.json) |

Report DSL 常用 fragment：

| Fragment | 用途 |
|---|---|
| [report-dsl.schema.json#/$defs/Catalog](report-dsl.schema.json#/$defs/Catalog) | flow 报告目录片段 |
| [report-dsl.schema.json#/$defs/Section](report-dsl.schema.json#/$defs/Section) | 报告章节片段 |
| [report-dsl.schema.json#/$defs/Slide](report-dsl.schema.json#/$defs/Slide) | paged 报告页面片段 |
| [report-dsl.schema.json#/$defs/BIEngineComponent](report-dsl.schema.json#/$defs/BIEngineComponent) | BI Engine 组件片段 |

## 3. 模板声明型扩展点

以下接口由模板声明外部实现 URL。详细调用规则见 [API 技术契约：模板声明型外部扩展协议](../apis/README.md#3-模板声明型外部扩展协议)。

| 扩展点 | Request | Response | 使用状态 | 用途 |
|---|---|---|---|---|
| Parameter Options | [parameter-option-source-request.schema.json](parameter-option-source-request.schema.json) | [parameter-option-source-response.schema.json](parameter-option-source-response.schema.json) | Response 运行时校验 | 为动态参数返回候选项和默认值 |
| Dynamic Custom | [dynamic-custom-source-request.schema.json](dynamic-custom-source-request.schema.json) | [dynamic-custom-source-response.schema.json](dynamic-custom-source-response.schema.json) | Response 运行时校验 | 按模板节点生成 Catalog、Section、Slide 或 Components 片段 |
| API Dataset | [api-dataset.schema.json#/$defs/ApiDatasetRequest](api-dataset.schema.json#/$defs/ApiDatasetRequest) | [api-dataset.schema.json#/$defs/ApiDatasetResponse](api-dataset.schema.json#/$defs/ApiDatasetResponse) | 契约测试 | 按模板 `dataset.source` 查询业务数据 |

## 4. 智能问数与平台查询

| 接口或模型 | Request | Response | 使用状态 | 用途与详细文档 |
|---|---|---|---|---|
| OneQuery | [onequery.schema.json#/$defs/OneQueryRequest](onequery.schema.json#/$defs/OneQueryRequest) | [onequery.schema.json#/$defs/OneQueryResponse](onequery.schema.json#/$defs/OneQueryResponse) | 契约测试 | 执行 SQL/UQL；见 [外部依赖接口技术契约](../apis/external-dependencies.md#5-onequery) |
| DATA_ANALYSIS Answer | - | [data-analysis-answer.schema.json](data-analysis-answer.schema.json) | 文档契约 | `data_analysis` 场景返回给前端的答案模型，不是外部 HTTP 调用 |

OneQuery 与 API Dataset 的响应都使用 `retCode/retInfo/data.columns/data.results` 包络，但分别定义在各自 Schema 中。两份契约保持独立可读，并由测试保证同构结构不会漂移。

## 5. 平台外部依赖

以下接口由生产平台定义，ReportSystem 主动适配。详细路径、身份头和失败语义见 [外部依赖接口技术契约](../apis/external-dependencies.md)。

### 5.1 OpenAI Compatible

Schema：[openai-compatible.schema.json](openai-compatible.schema.json)

| 调用 | Request | Response | 使用状态 |
|---|---|---|---|
| 对话补全 | [ChatCompletionRequest](openai-compatible.schema.json#/$defs/ChatCompletionRequest) | [ChatCompletionResponse](openai-compatible.schema.json#/$defs/ChatCompletionResponse) | 契约测试 |
| 向量化 | [EmbeddingRequest](openai-compatible.schema.json#/$defs/EmbeddingRequest) | [EmbeddingResponse](openai-compatible.schema.json#/$defs/EmbeddingResponse) | 契约测试 |

### 5.2 AgentCore

Schema：[agentcore.schema.json](agentcore.schema.json)

| 调用 | Request | Response | 使用状态 |
|---|---|---|---|
| 创建会话 | [CreateConversationRequest](agentcore.schema.json#/$defs/CreateConversationRequest) | [CreateConversationResponse](agentcore.schema.json#/$defs/CreateConversationResponse) | 契约测试 |
| 创建轮次 | [CreateChatRequest](agentcore.schema.json#/$defs/CreateChatRequest) | [CreateChatResponse](agentcore.schema.json#/$defs/CreateChatResponse) | 契约测试 |
| 归档或 upsert 轮次 | [ImportChatRequest](agentcore.schema.json#/$defs/ImportChatRequest) | [ImportChatResponse](agentcore.schema.json#/$defs/ImportChatResponse) | 契约测试 |
| 查询历史 | [HistoryRequest](agentcore.schema.json#/$defs/HistoryRequest) | [HistoryResponse](agentcore.schema.json#/$defs/HistoryResponse) | 契约测试 |
| 查询轮次详情 | [GetChatDetailRequest](agentcore.schema.json#/$defs/GetChatDetailRequest) | [ChatDetailResponse](agentcore.schema.json#/$defs/ChatDetailResponse) | 契约测试 |
| 查询会话列表 | [ConversationListRequest](agentcore.schema.json#/$defs/ConversationListRequest) | [ConversationListResponse](agentcore.schema.json#/$defs/ConversationListResponse) | 契约测试 |

### 5.3 Guardrail

Schema：[guardrail.schema.json](guardrail.schema.json)

| 调用 | Request | Response | 使用状态 |
|---|---|---|---|
| 问题检查 | [QuestionCheckRequest](guardrail.schema.json#/$defs/QuestionCheckRequest) | [LegalCheckResponse](guardrail.schema.json#/$defs/LegalCheckResponse) | 契约测试 |
| 回答检查 | [AnswerCheckRequest](guardrail.schema.json#/$defs/AnswerCheckRequest) | [LegalCheckResponse](guardrail.schema.json#/$defs/LegalCheckResponse) | 契约测试 |
| SQL/Python 内容检查 | [ApplicationSecurityRequest](guardrail.schema.json#/$defs/ApplicationSecurityRequest) | [ApplicationSecurityResponse](guardrail.schema.json#/$defs/ApplicationSecurityResponse) | 契约测试 |

### 5.4 DataCatalog 与元数据刷新

Schema：[datacatalog.schema.json](datacatalog.schema.json)、[logical-entity.schema.json](logical-entity.schema.json)、[metadata-sync.schema.json](metadata-sync.schema.json)

| 调用 | Request | Response | 使用状态 |
|---|---|---|---|
| 查询逻辑实体列表 | [ListLogicalEntitiesRequest](datacatalog.schema.json#/$defs/ListLogicalEntitiesRequest) | [ListLogicalEntitiesResponse](datacatalog.schema.json#/$defs/ListLogicalEntitiesResponse) | 契约测试 |
| 查询逻辑实体 | [GetLogicalEntityRequest](datacatalog.schema.json#/$defs/GetLogicalEntityRequest) | [GetLogicalEntityResponse](datacatalog.schema.json#/$defs/GetLogicalEntityResponse) | 运行时校验 + 契约测试 |
| 查询数据集 | [GetDatasetRequest](datacatalog.schema.json#/$defs/GetDatasetRequest) | [GetDatasetResponse](datacatalog.schema.json#/$defs/GetDatasetResponse) | 契约测试 |
| 查询逻辑关系列表 | [ListLogicalRelationsRequest](datacatalog.schema.json#/$defs/ListLogicalRelationsRequest) | [ListLogicalRelationsResponse](datacatalog.schema.json#/$defs/ListLogicalRelationsResponse) | 契约测试 |
| 查询逻辑关系 | [GetLogicalRelationRequest](datacatalog.schema.json#/$defs/GetLogicalRelationRequest) | [GetLogicalRelationResponse](datacatalog.schema.json#/$defs/GetLogicalRelationResponse) | 契约测试 |
| 检查元数据刷新版本 | [PackageRegisterProcessRequest](metadata-sync.schema.json#/$defs/PackageRegisterProcessRequest) | [PackageRegisterProcessResponse](metadata-sync.schema.json#/$defs/PackageRegisterProcessResponse) | 契约测试 |

Metadata Sync 是 DataCatalog 的辅助刷新特性：版本变化时清理 DataCatalog 与 Knowledge/RAG 缓存。

[logical-entity.schema.json](logical-entity.schema.json) 是单个逻辑实体详情的根 Schema。实体列表只返回候选摘要并要求稳定 `name`；NL2SQL 选中候选后逐个请求详情，并严格校验双语名称、描述、字段业务类型、扩展属性和基础数据类型。数据集与逻辑关系继续按开放对象消费。

### 5.5 Knowledge / RAG

Schema：[knowledge-rag.schema.json](knowledge-rag.schema.json)

| 调用 | Request | Response | 使用状态 |
|---|---|---|---|
| 查询知识 | [QueryKnowledgeRequest](knowledge-rag.schema.json#/$defs/QueryKnowledgeRequest) | [QueryKnowledgeResponse](knowledge-rag.schema.json#/$defs/QueryKnowledgeResponse) | 契约测试 |
| 单索引检索 | [RetrieveKnowledgeRequest](knowledge-rag.schema.json#/$defs/RetrieveKnowledgeRequest) | [RetrieveKnowledgeResponse](knowledge-rag.schema.json#/$defs/RetrieveKnowledgeResponse) | 契约测试 |
| 多索引检索 | [RetrieveMultiIndexRequest](knowledge-rag.schema.json#/$defs/RetrieveMultiIndexRequest) | [RetrieveMultiIndexResponse](knowledge-rag.schema.json#/$defs/RetrieveMultiIndexResponse) | 契约测试 |

### 5.6 NodeAgent

Schema：[nodeagent.schema.json](nodeagent.schema.json)

| 调用 | Request | Response | 使用状态 |
|---|---|---|---|
| 读取应用配置快照 | [AppConfigRequest](nodeagent.schema.json#/$defs/AppConfigRequest) | [AppConfigResponse](nodeagent.schema.json#/$defs/AppConfigResponse) | 契约测试 |

### 5.7 Audit

Schema：[audit.schema.json](audit.schema.json)

| 调用 | Request | Response | 使用状态 |
|---|---|---|---|
| 操作审计 | [AuditEventRequest](audit.schema.json#/$defs/AuditEventRequest) | [AuditResponse](audit.schema.json#/$defs/AuditResponse) | 契约测试 |
| 安全审计 | [AuditEventRequest](audit.schema.json#/$defs/AuditEventRequest) | [AuditResponse](audit.schema.json#/$defs/AuditResponse) | 契约测试 |

## 6. 示例

| 示例 | 对应 Schema | 用途 |
|---|---|---|
| [report-template.example.json](examples/report-template.example.json) | `report-template.schema.json` | flow 报告模板 |
| [report-template-paged.example.json](examples/report-template-paged.example.json) | `report-template.schema.json` | paged 报告模板 |
| [template-instance.example.json](examples/template-instance.example.json) | `template-instance.schema.json` | 对话中的模板实例 |
| [report-dsl.example.json](examples/report-dsl.example.json) | `report-dsl.schema.json` | flow Report DSL |
| [report-dsl-paged.example.json](examples/report-dsl-paged.example.json) | `report-dsl.schema.json` | paged Report DSL |
| [external-dependencies.example.json](examples/external-dependencies.example.json) | 平台外部依赖与查询 Schema | 外部接口消费者契约示例 |
