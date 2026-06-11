# ChatBI 业务配置中心

## 1. 定位

`ConfigCenter` 是 ReportSystem 进程内的业务配置统一视图。它让业务流程只关注配置含义，不感知配置的具体来源。

配置正本继续由各自 owner 管理：

- Runtime INI 保存部署侧提供的 ChatBI 业务配置。
- NodeAgent appconf 提供平台下发的 ChatBI 业务配置。
- ReportSystem 数据库保存通过本系统既有设置能力写入的 AI 配置。
- 少量历史环境变量作为兼容来源。

`ConfigCenter` 在 `ChatBIServer.initialize()` 中加载一次并生成只读快照。运行期间不轮询、不热更新；正本变化后需要重启服务。

## 2. 配置分类

| 分类 | 配置内容 | 主要消费者 |
|---|---|---|
| `llm` | 默认候选 LLM、候选模型端点和推理参数 | data-analysis |
| `ai` | Embedding 模型、模型服务地址、API Key 和超时 | report |
| `knowledge` | NL2SQL 与知识检索索引、topN、评分阈值、混合检索开关 | data-analysis |
| `dataAnalysis` | 查询策略和智能问数业务默认参数 | data-analysis |

## 3. 核心模型

- `ConfigKey[T]`：声明配置名称、强类型解析器和必填性。
- `ConfigSource`：配置来源协议，返回一个或多个配置键的部分值。
- `ConfigCenter`：按注册顺序读取来源、字段级合并并构建快照。
- `ConfigSnapshot`：不可变配置值、字段来源和脱敏诊断信息。

当前强类型配置：

- `LLMConfiguration`
- `CandidateLLMConfiguration`
- `AIConfiguration`
- `EmbeddingConfiguration`
- `KnowledgeConfiguration`
- `KnowledgeIndexConfiguration`
- `DataAnalysisConfiguration`

业务模块只依赖这些强类型对象，不直接读取 INI、appconf、配置表或环境变量。

## 4. 加载顺序

启动时按以下顺序加载：

1. `DatabaseConfigSource`
2. `RuntimeIniConfigSource`
3. `NodeAgentAppConfigSource`
4. `EnvironmentConfigSource`

同一字段通常只有一个 owner。若出现重复，以后加载的非空显式值覆盖先加载值，并记录最终来源。

来源暂时不可用时记录启动告警。若最终缺少 Embedding 配置、默认 LLM 名称或默认候选，ConfigCenter 初始化失败。候选模型的 `modelName/baseUrl` 和知识索引允许暂时为空，由实际使用该配置的流程在调用前校验。

旧数据库和历史环境变量中的 Completion 配置只作为兼容输入转换为候选 LLM，不再是业务模块读取 Completion 配置的入口。数据库兼容值最先加载，因此 NodeAgent 或 Runtime INI 提供的新 `llm` 配置会覆盖它；显式环境配置仍具有最高优先级。

## 5. 敏感配置

Embedding API Key 等敏感字段可以保存在内存快照中供内部调用，但：

- 不进入普通日志。
- 不进入异常详情。
- 诊断输出只显示是否已配置和脱敏值。
- 配置对象的 `repr` 不显示明文密钥。

## 6. 配置清单

| 配置键 | 类型 | 默认值 | 正本来源 | 必填 | 敏感 |
|---|---|---|---|---|---|
| `llm.defaultLlm` | string | 无 | appconf / INI / env 兼容 | 是 | 否 |
| `llm.inferParams` | object | `{}` | appconf / INI / env 兼容 | 否 | 否 |
| `llm.candidateLlms.<name>.modelName` | string | `""` | appconf / INI / env 兼容 | 使用时必填 | 否 |
| `llm.candidateLlms.<name>.baseUrl` | string | `""` | appconf / INI / env 兼容 | 使用时必填 | 否 |
| `llm.candidateLlms.<name>.inferParams` | object | `{}` | appconf / INI / env 兼容 | 否 | 否 |
| `ai.embedding.baseUrl` | string | 无 | DB / appconf / INI | 是 | 否 |
| `ai.embedding.model` | string | 无 | DB / appconf / INI | 是 | 否 |
| `ai.embedding.apiKey` | string | 无 | DB / appconf / INI | 是 | 是 |
| `knowledge.index.chatbi_klg_nl2chart_cus_global` | string | `""` | appconf / INI / env 兼容 | 使用时必填 | 否 |
| `knowledge.index.chatbi_klg_nl2chart_cus_custom` | string | `""` | appconf / INI / env 兼容 | 使用时必填 | 否 |
| `knowledge.index.chatbi_sql_few_shot` | string | `""` | appconf / INI / env 兼容 | 使用时必填 | 否 |
| `knowledge.index.chatbi_klg_report_template` | string | `""` | appconf / INI / env 兼容 | 使用时必填 | 否 |
| `knowledge.nl2sql.indexName` | string | `nl2sql_cache` | appconf / INI | 否 | 否 |
| `knowledge.nl2sql.esTopN` | integer | `5` | appconf / INI | 否 | 否 |
| `knowledge.nl2sql.vsTopN` | integer | `5` | appconf / INI | 否 | 否 |
| `knowledge.rankTopN` | integer | `3` | appconf / INI | 否 | 否 |
| `knowledge.scoreThreshold` | number | `0.5` | appconf / INI | 否 | 否 |
| `knowledge.enableHybridResults` | boolean | `true` | appconf / INI | 否 | 否 |
| `dataAnalysis.queryStrategy` | string | `single_pass` | appconf / INI / env 兼容 | 否 | 否 |

## 7. 候选 LLM 与推理参数

```yaml
llm:
  default_llm: qwen3_32b
  infer_params:
    stream: true
  candidate_llms:
    qwen3_32b:
      model_name: qwen3-32b
      base_url: /v1
      infer_params:
        stream: true
```

ConfigCenter 读取配置来源已经展开的映射，不解释 YAML anchor。推理参数按“调用时显式参数、候选参数、全局参数”的优先级合并。

Completion 通过 `runtime.client._session.GLOBAL_HTTP_SESSION` 调用候选模型 HTTP 端点。`stream=true` 时 infrastructure gateway 聚合流式增量并关闭响应，向 application 保持原有 Completion 返回结构。
