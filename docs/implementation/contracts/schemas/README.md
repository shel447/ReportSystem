# JSON Schema

本目录保存 ReportSystem 的正式 JSON Schema。Schema 是结构契约的唯一事实源，示例只用于说明和测试。

## 正式 Schema

- [report-template.schema.json](report-template.schema.json)
- [template-instance.schema.json](template-instance.schema.json)
- [report-dsl.schema.json](report-dsl.schema.json)
- [parameter-option-source-request.schema.json](parameter-option-source-request.schema.json)
- [parameter-option-source-response.schema.json](parameter-option-source-response.schema.json)

## 示例

- [report-template.example.json](examples/report-template.example.json)
- [report-template-paged.example.json](examples/report-template-paged.example.json)
- [template-instance.example.json](examples/template-instance.example.json)
- [report-dsl.example.json](examples/report-dsl.example.json)
- [report-dsl-paged.example.json](examples/report-dsl-paged.example.json)

运行时代码如需校验，必须直接读取本目录文件，不得在代码目录中复制 Schema 镜像。
