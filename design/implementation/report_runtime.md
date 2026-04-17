# 报告运行时模块设计实现

## 1. 模块定位

`report_runtime` 负责内部模板实例、`ReportDsl`、报告生成和报告聚合视图。它不再向外暴露独立实例资源。

## 2. 代码落点

- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/report_runtime/domain/models.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/report_runtime/domain/services.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/report_runtime/application/services.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/report_runtime/application/creation.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/report_runtime/application/export_services.py`（目标态）
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/report_runtime/infrastructure/repositories.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/report_runtime/infrastructure/gateways.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/report_runtime/infrastructure/outline.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/report_runtime/infrastructure/generation.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/report_runtime/infrastructure/baselines.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/report_runtime/infrastructure/documents.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/report_runtime/infrastructure/exporter_gateway.py`（目标态）
- `E:/code/codex_projects/ReportSystemV2/src/backend/routers/reports.py`

## 3. 核心领域概念

- `ReportInstance`
  - 最终报告产物记录
- `ReportDsl`
  - 冻结后的正式报告领域模型
- `TemplateInstance`
  - 内部核心聚合，贯穿参数收集、诉求确认、生成和更新
  - 主体结构为 `catalog -> section`

## 4. 当前公开面

公开接口只保留：

- `GET /rest/chatbi/v1/reports/{reportId}`
- `POST /rest/chatbi/v1/reports/{reportId}/document-generations`（目标态）
- `GET /rest/chatbi/v1/reports/{reportId}/documents/{documentId}/download`

说明：

- 不再暴露 `/instances/*`
- 不再暴露独立 `/documents/*`
- 模板实例只作为 `reports` 聚合结果的一部分返回

## 5. 关键实现链路

### 5.1 对话驱动模板实例

`conversation` 在 `/chat` 中持续更新同一份 `TemplateInstance`：

- 参数写回 `runtime_state`
- 诉求确认写回 `catalogs`
- 运行时补充信息写回 `binding_status / warnings / delta_views`

### 5.2 生成报告

确认生成后：

1. 读取当前 `TemplateInstance`
2. 通过 application 能力构建 `ReportDsl`
3. 写入 `ReportInstance.content.dsl`
4. 将 `TemplateInstance.report_instance_id` 绑定到最终报告

### 5.3 报告聚合视图

`GET /reports/{reportId}` 返回：

- `answer.report`
- `answer.templateInstance`
- `answer.documents`

### 5.4 文档下载

文档只走报告级路径：

- `/reports/{reportId}/documents/{documentId}/download`

文档生成目标态接口：

- `/reports/{reportId}/document-generations`

## 6. 关联表

- [tbl_report_instances](database_schema.md#tbl_report_instances)
- [tbl_template_instances](database_schema.md#tbl_template_instances)
- [tbl_report_documents](database_schema.md#tbl_report_documents)

## 7. 可替换组件

- 内容生成器
- 查询执行器
- Java Office 导出器
- PDF 派生转换器

替换这些组件时，不应改变 `TemplateInstance` 作为核心聚合的业务职责。
