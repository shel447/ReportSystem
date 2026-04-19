# 文档生成实现映射

> 权威来源：
> - [文档生成与导出架构](../report_system/06-文档生成与导出架构.md)

## 1. 目标模块职责

- `ExportReportService`
- `MarkdownExporter`
- `JavaOfficeExporterGateway`
- `PdfConverterGateway`
- `DocumentRegistry`

## 2. 关键实现点

- Markdown、Word、PPT、PDF 必须都消费冻结后的 `ReportDsl`
- Java 导出器只负责 `docx/pptx`
- PDF 首版为派生格式
- 任务与产物分别由 `tbl_export_jobs` 与 `tbl_report_documents` 记录
