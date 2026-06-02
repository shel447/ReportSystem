# JSON Schema

本目录保存 ReportSystem 的正式 JSON Schema。Schema 是结构契约的唯一事实源，示例只用于说明和测试。

## 正式 Schema

- [report-template.schema.json](report-template.schema.json)
- [template-instance.schema.json](template-instance.schema.json)
- [report-dsl.schema.json](report-dsl.schema.json)
- [parameter-option-source-request.schema.json](parameter-option-source-request.schema.json)
- [parameter-option-source-response.schema.json](parameter-option-source-response.schema.json)
- [onequery-request.schema.json](onequery-request.schema.json)
- [api-dataset-request.schema.json](api-dataset-request.schema.json)
- [dataset-source-response.schema.json](dataset-source-response.schema.json)
- [dynamic-custom-source-request.schema.json](dynamic-custom-source-request.schema.json)
- [dynamic-custom-source-response.schema.json](dynamic-custom-source-response.schema.json)
- [openai-compatible.schema.json](openai-compatible.schema.json)
- [agentcore.schema.json](agentcore.schema.json)
- [guardrail.schema.json](guardrail.schema.json)
- [datacatalog.schema.json](datacatalog.schema.json)
- [knowledge-rag.schema.json](knowledge-rag.schema.json)
- [platform-runtime.schema.json](platform-runtime.schema.json)
- [audit.schema.json](audit.schema.json)
- [data-analysis-answer.schema.json](data-analysis-answer.schema.json)

## 示例

- [report-template.example.json](examples/report-template.example.json)
- [report-template-paged.example.json](examples/report-template-paged.example.json)
- [template-instance.example.json](examples/template-instance.example.json)
- [report-dsl.example.json](examples/report-dsl.example.json)
- [report-dsl-paged.example.json](examples/report-dsl-paged.example.json)
- [external-dependencies.example.json](examples/external-dependencies.example.json)

运行时代码如需校验，必须直接读取本目录文件，不得在代码目录中复制 Schema 镜像。
