**版本**: v0.8
**最后更新**: 2026-04-18
**状态**: 报告主系统目标态规格摘要

## 1. 权威来源

本文件是主设计包的规格摘要。完整权威定义见：

- [统一设计包索引](report_system/README.md)

## 2. 核心规格摘要

- 报告主系统的唯一主线：`TemplateDefinition -> TemplateInstance -> Report DSL -> ReportInstance -> DocumentArtifact`
- 模板主结构：`catalogs -> sections`
- 报告主结构：`catalogs -> sections -> components`
- `/chat` 外层协议对齐 ChatBI
- 报告详情与流式报告共用同一份 `ReportAnswer`
- 文档生成接口固定为 `/reports/{reportId}/document-generations`
- PDF 首版通过派生转换生成
- 持久化层统一采用 `schema_version + content`

## 3. 适用范围

本规格只覆盖报告主系统，不再混写：

- 智能问数
- 智能故障
- 定时任务

这些能力仅作为边界能力保留。
