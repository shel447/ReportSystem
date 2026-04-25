# 报告系统统一设计包

> 本目录是报告系统的唯一权威设计源。凡是涉及报告主系统的业务边界、核心模型、状态机、接口契约、持久化结构、文档生成链路，均以本设计包为准。

## 1. 适用范围

本设计包只覆盖报告主系统：

- 报告模板
- 统一对话中的报告生成
- `TemplateInstance`
- `Report DSL`
- `ReportInstance`
- 文档生成与下载

不纳入本包主设计的能力：

- `smart_query`
- `fault_diagnosis`
- `scheduler`
- 纯运维、调试、开发辅助接口

## 2. 设计治理规则

1. 本目录是唯一权威设计源。
2. `design/README.md` 是 `design/` 根目录的唯一总入口。
3. `design/report_system/implementation/*.md` 是目标态实现设计，不得再混入偶然实现事实。
4. `design/biz_requirement.md` 只作为设计团队原始输入来源，不反向覆盖本目录的正式设计。
5. 若需要重新生成 OpenAPI 或其它投影材料，必须从本目录的接口契约出发生成，不得手工维护第二套权威定义。
6. 历史入口文档、演示材料和旧计划已从当前设计目录清理，不再参与主阅读路径。

## 3. 核心附件

正式 Schema：

- [schemas/report-template.schema.json](schemas/report-template.schema.json)
- [schemas/template-instance.schema.json](schemas/template-instance.schema.json)
- [schemas/report-dsl.schema.json](schemas/report-dsl.schema.json)
- [schemas/parameter-option-source-request.schema.json](schemas/parameter-option-source-request.schema.json)
- [schemas/parameter-option-source-response.schema.json](schemas/parameter-option-source-response.schema.json)

参考示例：

- [examples/report-template.example.json](examples/report-template.example.json)
- [examples/template-instance.example.json](examples/template-instance.example.json)
- [examples/report-dsl.example.json](examples/report-dsl.example.json)
- [implementation/change_log.md](implementation/change_log.md)

## 4. 阅读顺序

1. [01-统一总览](01-统一总览.md)
2. [02-核心业务模型与规范 Schema](02-核心业务模型与规范Schema.md)
3. [03-运行时流程与状态机](03-运行时流程与状态机.md)
4. [04-接口契约](04-接口契约.md)
5. [05-数据模型与持久化](05-数据模型与持久化.md)
6. [06-文档生成与导出架构](06-文档生成与导出架构.md)
7. [07-迁移兼容与验证](07-迁移兼容与验证.md)
8. [08-相对 ChatBI 的扩展点](08-相对ChatBI的扩展点.md)

## 5. 本轮统一收敛的关键结论

- 报告主系统的唯一主线是：`ReportTemplate -> TemplateInstance -> Report DSL -> ReportInstance -> DocumentArtifact`
- 模板主结构统一为：`catalogs -> (subCatalogs)* -> sections`
- 报告主结构统一为：`catalogs -> (subCatalogs)* -> sections -> components`
- `Report DSL` 是正式领域模型，不是导出阶段临时对象
- `TemplateInstance -> Report DSL` 与“文档生成”都属于应用层能力
- 统一对话接口和报告资源接口返回的报告载荷必须结构等价
- 模板实例的主体保持树状层级，应用层负责平铺 delta 的接收与合并
- `TemplateInstance` 不能只做轻量运行态骨架；为支撑复杂二次编辑与重新生成，后续必须补齐模板快照、参数运行态和章节模板快照能力
- 数据持久化可以使用 `content` 列承载完整对象，但对象本体的正式根结构不能再额外包一层 `content`
