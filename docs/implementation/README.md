# ReportSystem 实现设计

本目录记录业务规格的落地方式，并集中维护技术契约。实现文档可以描述模块、服务、数据模型、接口和算法，但不得反向定义业务规格。

## 实现导航

1. [技术契约](contracts/README.md)
2. [模板管理](template-management/README.md)
3. [通用对话](conversation/README.md)
4. [报告生成](report-generation/README.md)
5. [报告管理](report-management/README.md)
6. [前端](frontend/README.md)
7. [文档导出](document-export/README.md)
8. [外部集成](integrations/外部集成实现.md)
9. [智能问数](data-analysis/README.md)
10. [实现变更日志](changelog/README.md)

## 模块映射

后端按 bounded context 组织：

- `contexts/conversation`
- `contexts/report`
- `contexts/data_analysis`
- `infrastructure/{persistence,ai,query,documents,settings}`

依赖方向：

- `conversation` 提供通用场景注册、识别和分发机制，不直接依赖具体业务 context
- `report` 通过系统装配层的 codec 和强类型 handler 注册到 `conversation`
- `data_analysis` 通过系统装配层注册 `query_data` 场景，并向 `report` 提供可复用查询能力
- 系统装配层负责跨 context 的严格 DTO 转换；`conversation` 不读取 `report.application` 或 `report.domain`
- `report` 内部用 `application/domain/infrastructure` 三层组织；模板管理、报告生成和报告管理只在源文件命名上区分，不拆成子 context 目录。
- application 层只能通过 port 访问基础设施

`report.application` 按职责分为：

- `ReportService`：report context 对 router 和其他 context 的唯一总入口
- `ReportScenarioService`：编排报告场景 instruction
- `ReportTemplateService`：模板 CRUD、导入和导出
- `ReportParameterService`：参数提取、补参解释、缺参判断、追问构造和动态候选值解析
- `ReportGenerationService`：模板实例持久化、报告冻结和报告视图
- `ReportDocumentService`：文档生成和 report-scoped 下载

`report.domain` 不使用泛化的 `*Service` 命名。当前由 `ParameterResolver`、`ReportDslCompiler`、`template_instance_builder` 和 `placeholder_renderer` 表达纯领域职责；递归动态结构展开保持在模板实例构建器内部，避免把同一棵实例树拆成互相回调的零散步骤。

`data_analysis` 是独立 bounded context：负责语义数据目录、知识增强、查询生成、安全校验、OneQuery 执行和可视化建议。`report` 不复制这些规则。

禁止 router 直接操作 ORM、application 层直接使用 `Session`，或由基础设施反向定义领域对象。

## 落地约束

- 后端核心对象使用递归 `dataclass`，对外字段通过 alias 映射为 lowerCamelCase。
- `/chat` 流式协议使用 `steps / delta / answer` 三条通道；`delta` 不进入持久化聚合。
- `TemplateInstance` 是报告生成内部聚合，不作为独立公开资源。
- 文档导出只消费正式 Report DSL。
- 运行时校验直接读取 [正式 Schema](contracts/schemas/README.md)。
