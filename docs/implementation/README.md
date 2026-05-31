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
9. [实现变更日志](changelog/README.md)

## 模块映射

后端按 bounded context 组织：

- `contexts/template_catalog`
- `contexts/conversation`
- `contexts/report_runtime`
- `infrastructure/{persistence,ai,query,documents,settings}`

依赖方向：

- `conversation -> template_catalog`
- `conversation -> report_runtime`
- `report_runtime -> template_catalog`
- application 层只能通过 port 访问基础设施

禁止 router 直接操作 ORM、application 层直接使用 `Session`，或由基础设施反向定义领域对象。

## 落地约束

- 后端核心对象使用递归 `dataclass`，对外字段通过 alias 映射为 lowerCamelCase。
- `/chat` 流式协议使用 `steps / delta / answer` 三条通道；`delta` 不进入持久化聚合。
- `TemplateInstance` 是报告生成内部聚合，不作为独立公开资源。
- 文档导出只消费正式 Report DSL。
- 运行时校验直接读取 [正式 Schema](contracts/schemas/README.md)。
