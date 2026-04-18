# 报告运行时实现映射

> 权威来源：
> - [核心业务模型与规范 Schema](../report_system/02-核心业务模型与规范Schema.md)
> - [运行时流程与状态机](../report_system/03-运行时流程与状态机.md)

## 1. 目标模块职责

- `BuildTemplateInstanceService`
- `BuildReportDslService`
- `FreezeReportInstanceService`
- `GetReportViewService`

## 2. 关键实现点

- `TemplateInstance` 是运行态核心聚合
- `ReportDsl` 是正式领域模型
- `ReportInstance.content` 主体是 `ReportDsl`
- `/reports/{reportId}` 返回 `ReportInstanceResource`
