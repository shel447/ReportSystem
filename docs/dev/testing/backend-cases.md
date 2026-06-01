# 后端测试用例

后端既有测试按 Context 重新归档。清单使用稳定分类记录测试目标；具体函数级清单由架构审计从源码收集，避免文档因重命名产生虚假遗漏。

| ID | 分类 | 目标 | 实现位置 |
|---|---|---|---|
| BE-CONV | 通用对话 | 会话、消息、追问答复、fork 与 SSE 契约 | `modules/backend/tests/conversation/` |
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
| `tests/conversation/api/test_chat_contract_api.py` | 7 | `/chat` ask/reply、SSE、报告与章节 delta |
| `tests/conversation/unit/test_conversation_service.py` | 6 | 通用追问生命周期、场景分发和 fork 轨迹保留 |
| `tests/conversation/unit/test_scenario_dispatch.py` | 6 | 场景注册、显式匹配、多轮延续、本地识别、澄清和无会话指令 |
| `tests/dev_support/api/test_docs_router.py` | 4 | 文档索引、读取、ZIP 和逃逸防护 |
| `tests/dev_support/api/test_feedback_router.py` | 1 | 反馈 CRUD 与 ZIP |
| `tests/dev_support/api/test_system_settings_router.py` | 4 | 设置读取保存、连接测试和 reindex |
| `tests/features/test_document_export_flow.py` | 2 | Markdown API；Word/PPT 真实 CLI 参数化 E2E |
| `tests/features/test_complex_mock_template_export_flow.py` | 1 | 四份复杂开发模板真实 Word/PPT Office 包闭环 |
| `tests/features/test_template_management_flow.py` | 1 | 模板 CRUD、导入预览和导出 API 闭环 |
| `tests/infrastructure/persistence/test_persistence_contract.py` | 6 | 业务库、开发库和升级规则 |
| `tests/infrastructure/query/test_query_engine.py` | 4 | Ibis 查询与策略切换 |
| `tests/infrastructure/web/test_frontend_serving.py` | 5 | SPA 托管和用户镜像 |
| `tests/infrastructure/web/test_report_document_gateway.py` | 5 | Markdown、下载、PDF 拒绝和 CLI 参数 |
| `tests/report/api/test_parameter_options_router.py` | 2 | 动态参数候选值 API |
| `tests/report/api/test_reports_router.py` | 3 | 报告详情、下载和 PDF `400` |
| `tests/report/api/test_templates_router.py` | 8 | 模板管理 API 契约 |
| `tests/report/contract/test_shared_fixtures.py` | 2 | `testdata/` 模板与 Report DSL Schema |
| `tests/report/integration/test_complex_mock_templates.py` | 6 | 复杂开发模板、动态结构展开、SQL/API 数据集、动态内容和 paged DSL 冻结 |
| `tests/report/integration/test_dynamic_source_service.py` | 3 | 正式动态参数源、同源 URL 解析和身份头 |
| `tests/report/unit/test_report_generation_service.py` | 30 | 模板实例、DSL 编译、动态结构和自定义内容 |
| `tests/report/unit/test_report_document_service.py` | 2 | 文档格式校验、任务记录、列表和下载 |
| `tests/report/unit/test_parameter_resolver.py` | 2 | 参数标量解释和缺参判断纯规则 |
