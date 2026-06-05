# Report Context 实现

`report` 是 ReportSystem 后端的核心业务 Context，承接模板管理、报告生成、报告管理和文档导出适配。本文档目录只描述实现落地方式；业务能力说明见 [报告业务规格](../../specs/report/README.md)。

## 实现导航

1. [模板管理实现](template-management.md)
2. [报告生成实现](generation.md)
3. [报告管理实现](management.md)
4. [文档导出实现](document-export.md)
5. [报告生成业务规则技术参考](business-rules.md)
6. [Document Configuration 技术参考](document-configuration.md)
7. [报告导出 POI 转换实现](poi-exporter.md)

## Context 内职责

`report.application` 按职责分为：

- `ReportService`：report context 对 router 和其他 context 的统一入口。
- `ReportScenarioService`：编排报告场景 instruction。
- `ReportTemplateService`：模板 CRUD、导入和导出。
- `ReportParameterService`：参数提取、补参解释、缺参判断、追问构造和动态候选值解析。
- `ReportGenerationService`：模板实例持久化、报告冻结和报告视图。
- `ReportDocumentService`：文档生成和 report-scoped 下载。
- `ReportFlowProjection`：统一生成报告场景的 step、delta 和 answer 投影，`/chat` router 不再生成报告业务 delta。

`report.domain` 不使用泛化的 `*Service` 命名。当前由 `ParameterResolver`、`ReportDslCompiler`、`template_instance_builder` 和 `placeholder_renderer` 表达纯领域职责。

## 依赖边界

- `conversation` 拥有场景注册协议；report 在 `contexts/report/infrastructure/scenario_registration.py` 中提供 `ReportScenarioRegistrationProvider`，把 report 自己的 codec、handler、instruction 和识别信息封装为 conversation 能理解的注册信息。
- `ReportService.chat()` 是 report 场景进入报告流程的统一入口；所有报告场景均返回可执行 Flow，不再保留同步/流式两套入口。
- report 如需动态参数、Schema 校验、数据查询和文档导出，只依赖 report application 声明的 `ParameterOptionsResolver`、`ReportSchemaValidator`、`DatasetQueryGateway`、`DocumentExportGateway` 等接口；HTTP、JSON Schema 和 Java exporter 只是这些接口的 infrastructure 实现。
- `report` 可接入 `data_analysis` 的查询能力，但接口 owner 是 report 自己声明的 `DatasetQueryGateway`；装配层只接线，不解释查询业务语义。
- `shared/agentflow` 负责流程运行、事件发布、停止信号和指标汇总；report 只声明业务流程。
- 文档导出只消费正式 Report DSL，不反向影响报告生成聚合。
