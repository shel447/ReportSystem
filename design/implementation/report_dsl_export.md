# 报告 DSL 导出实现设计

## 1. 目标态代码组织

建议在 `report_runtime` 上下文内新增以下模块：

```text
contexts/report_runtime/
  domain/
    report_dsl.py
    template_instance.py
    document_artifact.py
  application/
    build_template_instance.py
    build_report_dsl.py
    freeze_report_instance.py
    export_report.py
  infrastructure/
    persistence/
    exporter_gateway.py
    pdf_converter.py
    markdown_exporter.py
```

## 2. 分层职责

### 2.1 domain

核心对象：

- `ReportDsl`
- `ReportCatalog`
- `ReportSection`
- `ReportComponent`
- `TemplateInstance`
- `DocumentArtifact`

要求：

- `ReportDsl` 是领域模型，不定义在基础设施层
- `catalog -> section -> component` 是正式结构
- `conversationId / chatId` 是正式命名

### 2.2 application

核心用例：

- `BuildTemplateInstanceService`
- `BuildReportDslService`
- `FreezeReportInstanceService`
- `ExportReportService`

要求：

- `TemplateInstance` 支持树状主体与平铺 delta 互转
- 导出任务创建属于 application 能力
- Java 导出器调用只通过 gateway 完成

### 2.3 infrastructure

核心适配器：

- `SqlAlchemyReportInstanceRepository`
- `SqlAlchemyTemplateInstanceRepository`
- `JavaOfficeExporterGateway`
- `PdfConverterGateway`
- `MarkdownDslExporter`

要求：

- 基础设施层不掌握骨架状态判断逻辑
- 基础设施层不拼装领域 DSL

## 3. 数据模型调整

### 3.1 tbl_template_instances

建议主体结构调整为：

```json
{
  "conversationId": "conv_xxx",
  "catalogs": [],
  "deltaViews": {},
  "warnings": [],
  "bindingStatus": {
    "internal": "reusable",
    "ui": "not_broken"
  }
}
```

### 3.2 tbl_report_instances

建议 `content` 收敛为：

```json
{
  "dsl": {},
  "sourceMeta": {
    "templateId": "tpl_xxx",
    "templateInstanceId": "ti_xxx",
    "sourceConversationId": "conv_xxx",
    "sourceChatId": "chat_xxx"
  },
  "runtimeMeta": {
    "warnings": [],
    "skeletonStatus": "reusable"
  }
}
```

### 3.3 tbl_report_documents

建议新增字段：

- `artifact_kind`
- `source_format`
- `generation_mode`
- `export_job_id`
- `mime_type`
- `error_message`

### 3.4 tbl_export_jobs

建议新增表，字段至少包括：

- `id`
- `report_instance_id`
- `requested_formats`
- `current_format`
- `status`
- `dependency_job_id`
- `started_at`
- `finished_at`
- `error_code`
- `error_message`

## 4. 关键类设计

### 4.1 BuildTemplateInstanceService

职责：

- 接收 `TemplateInstanceTreeDto`
- 接收可选 `TemplateInstanceDeltaDto[]`
- 合并并计算骨架状态

关键方法：

- `apply_tree(...)`
- `apply_delta(...)`
- `assess_skeleton_status(...)`

### 4.2 BuildReportDslService

职责：

- 从 `TemplateInstance` 构建 `ReportDsl`
- 将 `catalogs -> sections` 映射到 `catalogs -> sections -> components`
- 写入 `reportMeta`

关键方法：

- `build_from_template_instance(...)`
- `validate_schema(...)`
- `validate_semantics(...)`

### 4.3 ExportReportService

职责：

- 读取冻结后的 `ReportDsl`
- 创建导出任务
- 路由到 `word / ppt`
- 按依赖触发 `pdf`

关键方法：

- `request_document_generation(...)`
- `poll_export_jobs(...)`
- `register_artifacts(...)`

## 5. Java 导出器适配

建议独立工程：

```text
tools/report-office-exporter/
```

模块建议：

- `model/reportdsl`
- `validation`
- `core`
- `word`
- `ppt`
- `web`

关键契约：

```json
{
  "requestId": "req_xxx",
  "reportId": "rpt_xxx",
  "dslSchemaVersion": "1.0.0",
  "reportDsl": {},
  "options": {
    "theme": "default",
    "strictValidation": true
  }
}
```

说明：

- Java 服务无状态
- 只接收冻结后的 DSL
- 不访问 Python 业务数据库

## 6. PDF 派生策略

首版固定：

- `word -> pdf`
- `ppt -> pdf`

默认规则：

- 报告正文型 PDF 默认从 `word` 派生
- 仅显式请求时才允许从 `ppt` 派生

## 7. 测试设计

至少覆盖：

1. `TemplateInstance` 树与 delta 合并测试
2. `ReportDsl` schema 校验测试
3. `/chat` 中 `REPORT.answer.answer` 与 `GET /reports/{reportId}.answer` 结构一致性测试
4. `word / ppt / pdf` 文档生成链路测试
5. 用户隔离与下载权限测试

## 8. 迁移顺序

建议顺序：

1. 先落 `ReportDsl` 领域模型
2. 再落 `BuildTemplateInstanceService`
3. 再落 `BuildReportDslService`
4. 再让 Markdown 改为消费 DSL
5. 再接 Java `word / ppt`
6. 最后接 `pdf`
