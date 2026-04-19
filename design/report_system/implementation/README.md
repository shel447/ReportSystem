# Report System Implementation

> 本目录是 `design/report_system` 的目标态实现说明。所有实现都必须直接投影主设计包的正式模型与接口契约，不再引入兼容层、兜底映射或历史双轨定义。

## 阅读顺序

1. [总体实现架构](./总体实现架构.md)
2. [模板目录实现](./模板目录实现.md)
3. [统一对话实现](./统一对话实现.md)
4. [报告运行时实现](./报告运行时实现.md)
5. [持久化与表结构实现](./持久化与表结构实现.md)
6. [前端实现](./前端实现.md)
7. [外部集成与导出实现](./外部集成与导出实现.md)
8. [change_log.md](./change_log.md)

## 落地约束

- 以 `design/report_system/schemas/*.json` 为唯一结构约束。
- `src/backend` 根目录不得再存放 schema 或示例 JSON 镜像；运行时代码如需校验，必须直接引用 `design/report_system/schemas/*.json`。
- 后端公开接口只保留 `templates / chat / reports / parameter-options`；`/rest/dev/*` 属于支撑接口，不反向定义主业务模型。
- 领域主线固定为 `ReportTemplate -> TemplateInstance -> Report DSL -> ReportInstance -> DocumentArtifact`。
- `TemplateInstance` 是核心运行态聚合。参数收集、诉求实例化、delta 合并、报告生成都围绕同一份模板实例推进。
- `/chat` 流式协议按 `steps / delta / answer` 三条通道实现；`delta` 只属于流式事件，不进入持久化聚合。
- 数据库允许删表重建，因此实现中不得保留任何旧结构向新结构的转换映射。

## Application Service 导航

实现文档中的 application service 按模块拆分说明：

- `template_catalog`
  - [模板目录实现](./模板目录实现.md)
- `conversation`
  - [统一对话实现](./统一对话实现.md)
- `report_runtime`
  - [报告运行时实现](./报告运行时实现.md)

每篇文档都必须回答两件事：

- 该模块有哪些 application service
- 每个 service 负责的业务边界、输入输出和禁止承担的职责是什么
