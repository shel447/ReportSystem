# 智能问数实现

## 1. Context 定位

`contexts/data_analysis` 是数据分析 bounded context。它既承载 `/chat` 下的 `query_data` 场景，也为报告生成提供查询执行能力。

## 2. 分层职责

- domain：`QuerySpec`、数据列、查询结果、知识上下文、可视化建议和 `DATA_ANALYSIS` 答案。
- application：编排 DataCatalog、Knowledge、LLM、SQL 安全检查、OneQuery 和可视化建议；定义外部能力 ports。
- infrastructure：屏蔽外部接口路径、报文和错误码差异。

## 3. 智能问数流程

1. 根据问题加载 DataCatalog 元数据。
2. 使用 Knowledge 多索引检索召回 NL2SQL 样例。
3. 通过 LLM 生成 `QuerySpec + SQL`。
4. 通过 Guardrail 校验 SQL。
5. 调用 OneQuery 执行查询。
6. 将结果映射为字段元数据、表格和 BI Engine 图表组件。
7. 通过 LLM 生成结论。

Knowledge 不可用时降级为空上下文；DataCatalog、SQL 安全检查或 OneQuery 失败时停止本次智能问数。

DataCatalog 和 Knowledge/RAG 的缓存键必须包含 `userId`。平台配置缓存可以全局共享，但任何可能受用户数据权限影响的元数据或检索结果不得跨用户复用。

DataCatalog 逻辑实体使用量属于业务/平台指标，由 data-analysis 的 DataCatalog 适配器在 AgentFlow 上下文中记录自定义去重指标：

```text
datacatalog.logical_entity.used
```

指标 key 使用逻辑实体名称或平台返回的稳定标识。AgentFlow 不理解 DataCatalog 或逻辑实体含义，只在终态 metrics 的 `uniqueCounts` 中透传该 metric name 的去重数量。

## 4. 报告复用

报告的 `sql/api` 数据集通过 `DataQueryService` 使用同一份查询执行和字段元数据映射。报告场景对 OneQuery 业务失败保留既有空数据降级；独立 `query_data` 场景返回明确错误。

模板中的 `llm/compose` 数据集暂不启用，等待模板侧正式定义查询生成和组合规则。
