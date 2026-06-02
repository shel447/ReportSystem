# 后端测试用例

后端既有测试按 Context 重新归档。清单使用稳定分类记录测试目标；具体函数级清单由架构审计从源码收集，避免文档因重命名产生虚假遗漏。

| ID | 分类 | 目标 | 实现位置 |
|---|---|---|---|
| BE-CONV | 通用对话 | AgentCore 托管会话、轮次 upsert、追问答复、暂未开放能力与 SSE 契约 | `modules/backend/tests/conversation/` |
| BE-DATA | 智能问数 | NL2SQL 编排、安全检查、查询协议与 BI 可视化建议 | `modules/backend/tests/data_analysis/` |
| BE-REPORT | 报告生成 | 模板、参数、模板实例、Report DSL 和章节重生成 | `modules/backend/tests/report/` |
| BE-INFRA | 基础设施 | 数据库升级、查询、动态数据源、前端托管与文档网关 | `modules/backend/tests/infrastructure/` |
| BE-DEV | 开发辅助 | docs、feedback 和系统设置接口 | `modules/backend/tests/dev_support/` |
| BE-ARCH | 架构审计 | Context 依赖边界、类型契约和测试目录规则 | `modules/backend/tests/architecture/` |

## 文件级清单

清单按测试文件维护。参数化测试的运行实例数可能高于源码中的 `test_*` 函数数。

| 文件 | 源码用例数 | 主要覆盖目标 |
|---|---:|---|
| `tests/architecture/test_architecture_boundaries.py` | 9 | Context、router、compiler 和文档职责边界 |
| `tests/architecture/test_dataclass_alias_contract.py` | 4 | lowerCamelCase 序列化契约 |
| `tests/architecture/test_service_type_contracts.py` | 4 | 应用服务正式类型 |
| `tests/architecture/test_test_catalog.py` | 4 | 测试目录、清单、`.test/` 隔离 |
| `tests/conversation/api/test_chat_contract_api.py` | 8 | `/chat` ask/reply、外部报告交接、SSE、报告与章节 delta |
| `tests/conversation/unit/test_conversation_service.py` | 7 | AgentCore 托管对话、通用追问生命周期、upsert 消费、暂未开放 fork 和异步审计提交 |
| `tests/conversation/unit/test_scenario_dispatch.py` | 6 | 场景注册、显式匹配、多轮延续、本地识别、澄清和无会话指令 |
| `tests/data_analysis/unit/test_data_analysis_service.py` | 2 | 智能问数编排、SQL 安全拒绝和 BI 可视化建议 |
| `tests/data_analysis/infrastructure/test_external_query_gateways.py` | 4 | OneQuery 正式路径、字段元数据、新版查询包络必填字段和用户级 DataCatalog/RAG 缓存 |
| `tests/dev_support/api/test_docs_router.py` | 4 | 文档索引、读取、ZIP 和逃逸防护 |
| `tests/dev_support/api/test_feedback_router.py` | 1 | 反馈 CRUD 与 ZIP |
| `tests/dev_support/api/test_system_settings_router.py` | 4 | 设置读取保存、连接测试和 reindex |
| `tests/features/test_document_export_flow.py` | 2 | Markdown API；Word/PPT 真实 CLI 参数化 E2E |
| `tests/features/test_complex_mock_template_export_flow.py` | 1 | 四份复杂开发模板真实 Word/PPT Office 包闭环 |
| `tests/features/test_template_management_flow.py` | 2 | 模板 CRUD、导入预览、导出 API 闭环和跨用户共享可见性 |
| `tests/infrastructure/persistence/test_persistence_contract.py` | 7 | 业务库、开发库、升级规则和 V004 用户镜像无损移除 |
| `tests/infrastructure/platform/test_platform_runtime.py` | 3 | NodeAgent 分层配置、环境应急覆盖和审计尽力投递 |
| `tests/infrastructure/platform/test_external_dependency_contracts.py` | 37 | 平台外部依赖消费者 Schema、集中示例、AgentCore upsert 与响应扩展兼容 |
| `tests/infrastructure/query/test_query_engine.py` | 4 | Ibis 查询与策略切换 |
| `tests/infrastructure/web/test_frontend_serving.py` | 6 | SPA 托管、正式接口身份校验和开发辅助接口独立性 |
| `tests/infrastructure/web/test_report_document_gateway.py` | 5 | Markdown、下载、PDF 拒绝和 CLI 参数 |
| `tests/report/api/test_parameter_options_router.py` | 2 | 动态参数候选值 API |
| `tests/report/api/test_reports_router.py` | 3 | 报告详情、下载和 PDF `400` |
| `tests/report/api/test_templates_router.py` | 8 | 模板管理 API 契约 |
| `tests/report/contract/test_shared_fixtures.py` | 5 | `testdata/` 模板、Report DSL Schema 与新版数据集响应契约 |
| `tests/report/integration/test_complex_mock_templates.py` | 9 | 复杂开发模板、动态结构展开、SQL/API 数据集、血缘映射、业务失败降级、动态内容和 paged DSL 冻结 |
| `tests/report/integration/test_dynamic_source_service.py` | 3 | 正式动态参数源、同源 URL 解析和身份头 |
| `tests/report/infrastructure/test_generation_repositories.py` | 1 | 正式报告仓储按外部用户身份隐藏跨用户资源 |
| `tests/report/unit/test_report_generation_service.py` | 31 | 模板实例、DSL 编译、数据集告警汇总、动态结构和自定义内容 |
| `tests/report/unit/test_report_document_service.py` | 2 | 文档格式校验、任务记录、列表和下载 |
| `tests/report/unit/test_parameter_resolver.py` | 2 | 参数标量解释和缺参判断纯规则 |
| `tests/report/unit/test_report_scenario_bootstrap.py` | 6 | 外部报告交接、根级参数快照、名称精确定位和非法输入拒绝 |
