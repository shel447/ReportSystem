# ChatBI 业务配置中心

## 1. 定位

`ConfigCenter` 是 ReportSystem 进程内的业务配置统一视图。它解决的是“业务流程只关心配置含义，不关心配置从哪里读取”，不是把所有配置正本迁移到一张表，也不是平台通信配置中心。

配置正本继续由各自 owner 管理：

- Runtime INI 保存部署侧提供的 ChatBI 业务配置。
- NodeAgent appconf 提供平台下发的 ChatBI 业务配置。
- ReportSystem 数据库保存通过本系统既有设置能力写入的 AI 配置。
- 少量历史环境变量作为兼容来源。

`ConfigCenter` 在 `ChatBIServer.initialize()` 中加载一次并生成只读快照。运行期间不轮询、不热更新；正本变化后需要重启服务。

## 2. 边界

首版纳入：

| 分类 | 配置内容 | 主要消费者 |
|---|---|---|
| `ai` | Completion/Embedding 模型、模型服务地址、API Key、温度、超时 | report、data-analysis |
| `knowledge` | NL2SQL 与知识检索索引、topN、评分阈值、混合检索开关 | data-analysis |
| `dataAnalysis` | 查询策略和智能问数业务默认参数 | data-analysis |

明确不纳入：

- Report 专属配置和 Document Configuration。
- AgentCore、Guardrail、OneQuery、DataCatalog、RAG、Audit、NodeAgent 等平台服务地址。
- 平台认证、连接池、代理、TLS、通用 HTTP 超时和重试。
- Runtime host、port、module、数据目录等进程 bootstrap 参数。
- 模板声明的 Parameter Options、Dynamic Custom 和 API Dataset URL。

平台 HTTP 统一由外置 `runtime.client` SDK 处理。ReportSystem 只传 `/rest/...` 相对接口路径，不读取、不拼接平台 base URL。

## 3. 核心模型

- `ConfigKey[T]`：声明配置名称、强类型解析器和必填性。
- `ConfigSource`：配置来源协议，返回一个或多个配置键的部分值。
- `ConfigCenter`：按注册顺序读取来源、字段级合并并构建快照。
- `ConfigSnapshot`：不可变配置值、字段来源和脱敏诊断信息。

当前强类型配置：

- `AIConfiguration`
- `KnowledgeConfiguration`
- `DataAnalysisConfiguration`

业务模块只依赖这些强类型对象，不直接读取 INI、appconf、配置表或环境变量。

## 4. 加载顺序

启动时按以下顺序加载：

1. `RuntimeIniConfigSource`
2. `NodeAgentAppConfigSource`
3. `DatabaseConfigSource`
4. `EnvironmentConfigSource`

同一字段通常只有一个 owner。若出现重复，以后加载的非空显式值覆盖先加载值，并记录最终来源。

来源暂时不可用时记录启动告警。若最终缺失必填配置，ConfigCenter 初始化失败；可选知识检索和数据分析配置使用代码定义的明确默认值。

## 5. 敏感配置

API Key 等敏感字段可以保存在内存快照中供内部调用，但：

- 不进入普通日志。
- 不进入异常详情。
- 诊断输出只显示是否已配置和脱敏值。
- 配置对象的 `repr` 不显示明文密钥。

## 6. Runtime Client

平台接口通过共享 Session 调用：

```python
from requests import Session
from runtime.client._session import GLOBAL_HTTP_SESSION

session: Session = GLOBAL_HTTP_SESSION
response = session.post(url="/rest/...", headers={}, json=payload)
```

流式响应必须在 `finally` 中关闭。生产 Runtime SDK 负责平台地址解析、共享连接和底层认证；`modules/mock-sdk` 只提供本地开发兼容实现。Infrastructure adapter 仍拥有具体协议解析、用户身份透传、业务降级和 `chatbi.*` 错误转换。

## 7. 配置清单

| 配置键 | 类型 | 默认值 | 正本来源 | 必填 | 敏感 |
|---|---|---|---|---|---|
| `ai.completion.baseUrl` | string | 无 | DB / appconf / INI | 是 | 否 |
| `ai.completion.model` | string | 无 | DB / appconf / INI | 是 | 否 |
| `ai.completion.apiKey` | string | 无 | DB / appconf / INI | 是 | 是 |
| `ai.completion.temperature` | number | `0.2` | DB / appconf / INI | 否 | 否 |
| `ai.completion.timeoutSeconds` | integer | `60` | DB / appconf / INI | 否 | 否 |
| `ai.embedding.baseUrl` | string | 复用 Completion | DB / appconf / INI | 条件必填 | 否 |
| `ai.embedding.model` | string | 无 | DB / appconf / INI | 是 | 否 |
| `ai.embedding.apiKey` | string | 复用 Completion | DB / appconf / INI | 条件必填 | 是 |
| `knowledge.nl2sql.indexName` | string | `nl2sql_cache` | appconf / INI | 否 | 否 |
| `knowledge.nl2sql.esTopN` | integer | `5` | appconf / INI | 否 | 否 |
| `knowledge.nl2sql.vsTopN` | integer | `5` | appconf / INI | 否 | 否 |
| `knowledge.rankTopN` | integer | `3` | appconf / INI | 否 | 否 |
| `knowledge.scoreThreshold` | number | `0.5` | appconf / INI | 否 | 否 |
| `knowledge.enableHybridResults` | boolean | `true` | appconf / INI | 否 | 否 |
| `dataAnalysis.queryStrategy` | string | `single_pass` | appconf / INI / env 兼容 | 否 | 否 |
