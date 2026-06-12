# ReportSystem 实现设计

本目录记录业务规格的落地方式，并集中维护技术契约。实现文档可以描述模块、服务、数据模型、接口和算法，但不得反向定义业务规格。

## 实现导航

1. [技术契约](contracts/README.md)
2. [统一消息中心](messaging/README.md)
3. [Agent Flow 公共流程框架](agentflow/README.md)
4. [ChatBI 业务配置中心](configuration/README.md)
5. [Report Context 实现](report/README.md)
6. [通用对话](conversation/README.md)
7. [前端](frontend/README.md)
8. [外部集成](integrations/外部集成实现.md)
9. [智能问数](data-analysis/README.md)
10. [实现变更日志](changelog/README.md)
11. [Runtime Server 与 Controller 适配](web-adapter.md)
12. [日志实现](logging/README.md)
13. [Runtime 数据库接入](persistence/runtime-db.md)
14. [Runtime Schedule 接入](scheduling/README.md)

## 模块映射

后端按 bounded context 组织：

- `contexts/conversation`
- `contexts/report`
- `contexts/data_analysis`
- `shared/agentflow`
- `shared/messaging`
- `shared/configuration`
- `shared/kernel`
- `infrastructure/{persistence,ai,query,documents,settings}`

用户管理属于平台外部模块。ReportSystem 不实现用户 context，不保存用户档案，只消费网关注入的可信 `X-User-Id` 作为不透明数据归属键。

依赖方向：

- `conversation` 提供通用场景注册、识别和分发机制，不直接依赖具体业务 context
- `shared/messaging` 提供全系统统一消息包络、发布、订阅和定向 command；AgentFlow、业务 context、conversation、审计和指标均通过该中心协作
- `shared/agentflow` 提供公共流程运行、Flow 事件预处理、工具调用、提示词组装、hook、checkpoint、拒答和取消；处理后的消息发布到 `shared/messaging`
- `shared/kernel` 提供公开错误模型、用户身份解析、`@authenticated` 权限注解和统一日志门面；平台鉴权的 HTTP 实现位于 infrastructure
- `shared/configuration` 提供 ChatBI 业务配置的强类型只读视图；配置正本仍由 Runtime INI、NodeAgent appconf 或数据库等来源拥有
- `conversation` 拥有场景注册协议；`report` 和 `data_analysis` 在各自 context 内提供 registration provider、codec 和 handler 实现
- `data_analysis` 拥有查询、数据目录和知识检索相关业务接口；`report` 如需查询能力，只依赖自己声明的数据查询接口，由装配层接入对应实现
- 顶层装配只收集各 context 暴露的 composition builder 和 provider，不拼接业务 DTO，不解释业务场景语义
- `report` 内部用 `application/domain/infrastructure` 三层组织；模板管理、报告生成和报告管理只在源文件命名上区分，不拆成子 context 目录。
- application/domain 声明并拥有它们需要的业务接口；infrastructure 只提供实现，不反向定义业务接口
- 正式业务 ORM 继承 `runtime.db.TableBase`，service scope 通过 persistence infrastructure 的 `db_session` 共享 Runtime Session；开发辅助库保持独立
- 进程级后台周期任务使用 `runtime.schedule`；业务模块不直接引入第三方调度框架

`report.application` 按职责分为：

- `ReportService`：report context 对 Controller 和其他 context 的唯一总入口
- `ReportScenarioService`：编排报告场景 instruction
- `ReportTemplateService`：模板 CRUD、导入和导出
- `ReportParameterService`：参数提取、补参解释、缺参判断、追问构造和动态候选值解析
- `ReportGenerationService`：模板实例持久化、报告冻结和报告视图
- `ReportDocumentService`：文档生成和 report-scoped 下载
- `ReportFlowProjection`：把报告场景结果投影为 step、delta 和 answer 事件

`report.domain` 不使用泛化的 `*Service` 命名。当前由 `ParameterResolver`、`ReportDslCompiler`、`template_instance_builder` 和 `placeholder_renderer` 表达纯领域职责；递归动态结构展开保持在模板实例构建器内部，避免把同一棵实例树拆成互相回调的零散步骤。

`data_analysis` 是独立 bounded context：负责语义数据目录、知识增强、查询生成、安全校验、OneQuery 执行和可视化建议。`report` 不复制这些规则。

Controller 方法可以直接接收 Tornado `RequestHandler`，但不得操作 ORM、依赖 `Session/get_db` 或把 RequestHandler 传入 application/domain。正式业务库由 Runtime 提供，数据库 session、仓储实现和事务生命周期由 infrastructure 管理。

## 落地约束

- 后端核心对象使用递归 `dataclass`，对外字段通过 alias 映射为 lowerCamelCase。
- `/chat` 流式协议使用 `step_delta / delta / answer / error` 通道；运行中事件由 `shared/agentflow` 产生，`delta` 不进入持久化聚合。
- `TemplateInstance` 是报告生成内部聚合，不作为独立公开资源。
- 文档导出只消费正式 Report DSL。
- 运行时校验通过 report context 拥有的 `ReportSchemaValidator` 接口接入 [正式 Schema](contracts/schemas/README.md)。
