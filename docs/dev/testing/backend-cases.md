# 后端测试用例

后端既有测试按 Context 重新归档。清单使用稳定分类记录测试目标；具体函数级清单由架构审计从源码收集，避免文档因重命名产生虚假遗漏。

| ID | 分类 | 目标 | 实现位置 |
|---|---|---|---|
| BE-CONV | 通用对话 | AgentCore 托管会话、轮次 upsert、追问答复、暂未开放能力与 SSE 契约 | `modules/backend/tests/conversation/` |
| BE-SHARED | 公共基础 | Agent Flow 图执行、React、human-in-loop、取消、运行事件、身份和路由权限基础能力 | `modules/backend/tests/shared/` |
| BE-DATA | 智能问数 | NL2SQL 编排、安全检查、查询协议与 BI 可视化建议 | `modules/backend/tests/data_analysis/` |
| BE-REPORT | 报告生成 | 模板、参数、模板实例、Report DSL 和章节重生成 | `modules/backend/tests/report/` |
| BE-INFRA | 基础设施 | 数据库升级、查询、动态数据源、平台外部依赖与文档网关 | `modules/backend/tests/infrastructure/` |
| BE-ARCH | 架构审计 | Context 依赖边界、类型契约和测试目录规则 | `modules/backend/tests/architecture/` |

## 文件级清单

清单按测试文件维护。参数化测试的运行实例数可能高于源码中的 `test_*` 函数数。

| 文件 | 源码用例数 | 主要覆盖目标 |
|---|---:|---|
| `tests/architecture/test_architecture_boundaries.py` | 21 | Context、Controller、Runtime Server、compiler、事务依赖、消息边界和权限注解边界 |
| `tests/architecture/test_dataclass_alias_contract.py` | 4 | lowerCamelCase 序列化契约 |
| `tests/architecture/test_service_type_contracts.py` | 5 | 应用服务正式类型与基础设施 adapter 显式 Protocol 实现 |
| `tests/architecture/test_test_catalog.py` | 4 | 测试目录、清单、`.test/` 隔离 |
| `tests/conversation/api/test_chat_contract_api.py` | 3 | Runtime Controller 健康检查、`/chat` JSON、会话详情与 SSE 事件时序契约 |
| `tests/conversation/infrastructure/test_agentcore_gateway.py` | 3 | AgentCore 上游错误码到 ChatBI 错误码的转换、标准 records/answers 写入和历史读取 |
| `tests/conversation/unit/test_conversation_service.py` | 10 | AgentCore 托管对话、通用追问生命周期、SSE 断开后持久化、运行中会话并发保护、upsert 消费、暂未开放 fork 和异步审计提交 |
| `tests/conversation/unit/test_scenario_dispatch.py` | 6 | 场景注册、显式匹配、多轮延续、本地识别、澄清和无会话指令 |
| `tests/data_analysis/unit/test_data_analysis_service.py` | 7 | 智能问数编排、强类型步骤组合、SQL 安全拒绝、精确查询错误停止后续节点和 BI 可视化建议 |
| `tests/data_analysis/unit/test_step_contracts.py` | 5 | 五个内部子流程 DTO round-trip、必填字段、`intent_function` AST 校验和禁止执行源码 |
| `tests/data_analysis/infrastructure/test_external_query_gateways.py` | 9 | OneQuery 正式路径、完整成功包络、精确业务错误、未知错误兼容语义、必填包络字段、字段元数据和用户级 DataCatalog/RAG 缓存 |
| `tests/features/test_document_export_flow.py` | 1 | 文档生成 Controller 到应用服务的契约 |
| `tests/features/test_complex_mock_template_export_flow.py` | 1 | 四份复杂开发模板真实 Word/PPT Office 包闭环 |
| `tests/features/test_template_management_flow.py` | 2 | 模板 CRUD、导入预览、导出 API 闭环和跨用户共享可见性 |
| `tests/infrastructure/persistence/test_persistence_contract.py` | 7 | 业务库、开发库、升级规则和 V004 用户镜像无损移除 |
| `tests/infrastructure/persistence/test_unit_of_work.py` | 2 | SQLAlchemy Unit of Work 显式提交、异常回滚和 session 关闭 |
| `tests/infrastructure/test_messaging.py` | 2 | 领域事件仅在事务提交后进入统一消息中心，回滚时丢弃 |
| `tests/infrastructure/platform/test_guardrail_gateway.py` | 1 | Guardrail 正式 `/rest/naie/...` 路径和用户身份透传 |
| `tests/infrastructure/platform/test_policy_auth_gateway.py` | 3 | Policy Authentication 正式 POST 报文、逐项判断和拒绝转换 |
| `tests/infrastructure/platform/test_platform_runtime.py` | 3 | NodeAgent 分层配置、环境应急覆盖和审计尽力投递 |
| `tests/infrastructure/platform/test_external_dependency_contracts.py` | 56 | 平台外部依赖消费者 Schema、集中示例、AgentCore upsert、查询响应同构与 Schema 索引完整性 |
| `tests/infrastructure/query/test_query_engine.py` | 4 | Ibis 查询与策略切换 |
| `tests/infrastructure/web/test_report_document_gateway.py` | 5 | Markdown、下载、PDF 拒绝和 CLI 参数 |
| `tests/report/api/test_report_controller.py` | 2 | 报告 Controller 下载和错误转换 |
| `tests/report/api/test_template_controller.py` | 2 | 模板管理 Controller 与 testdata round-trip |
| `tests/report/contract/test_shared_fixtures.py` | 5 | `testdata/` 模板、Report DSL Schema 与新版数据集响应契约 |
| `tests/report/integration/test_complex_mock_templates.py` | 9 | 复杂开发模板、动态结构展开、SQL/API 数据集、血缘映射、业务失败降级、动态内容和 paged DSL 冻结 |
| `tests/report/integration/test_dynamic_source_service.py` | 3 | 正式动态参数源、同源 URL 解析和身份头 |
| `tests/report/infrastructure/test_generation_repositories.py` | 1 | 正式报告仓储按外部用户身份隐藏跨用户资源 |
| `tests/report/unit/test_report_generation_service.py` | 33 | 模板实例、DSL 编译、报告生成领域事件、数据集告警汇总、动态结构和自定义内容 |
| `tests/report/unit/test_report_document_service.py` | 2 | 文档格式校验、任务记录、列表和下载 |
| `tests/report/unit/test_parameter_resolver.py` | 2 | 参数标量解释和缺参判断纯规则 |
| `tests/report/unit/test_report_scenario_bootstrap.py` | 6 | 外部报告交接、根级参数快照、名称精确定位和非法输入拒绝 |
| `tests/report/unit/test_report_scenario_flow.py` | 3 | 报告场景 Flow 接入、同步预览保留和严格 codec |
| `tests/shared/test_http_identity.py` | 2 | 正式用户身份必填和本地开发用户覆盖 |
| `tests/shared/test_authenticated.py` | 2 | Controller 权限注解、鉴权调用和拒绝响应 |
| `tests/shared/test_agentflow_runtime.py` | 13 | Agent Flow 顺序、条件/汇合、真并行、图渲染、指标发布、human-in-loop、取消和系统终止 |
| `tests/shared/test_agentflow_capabilities.py` | 7 | Tool、Prompt、Hook、Checkpoint、拒答、动态追加分支和非法改图拒绝 |
| `tests/shared/test_message_center.py` | 9 | 统一 interaction 契约、消息过滤、无回放、同分区时序、跨分区并行、消费者隔离、Command 定向投递、未处理反馈和生命周期重启 |
