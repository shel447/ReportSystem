# 文档导出实现

Report Exporter 位于 `modules/exporter`。它接收 Report DSL 或归一化后的 VDoc，通过 CLI 生成 DOCX 和 PPTX。Markdown 由后端直接生成。PDF 派生转换尚未实现，当前请求会被后端明确拒绝。

业务侧可感知的默认效果和预留选项见 [文档导出业务规格](../../specs/report/document-export.md)。迁移前的完整配置说明保留在 [Document Configuration 技术参考](document-configuration.md)。

## 实现边界

- Java 源码根包：`com.chatbi`
- CLI 入口：`com.chatbi.exporter.CliMain`
- 导出默认配置：`com.chatbi.exporter.conf`
- Report DSL Java 模型：`com.chatbi.report.dsl`
- DOCX/PPTX 渲染：`com.chatbi.exporter.docx`、`com.chatbi.exporter.pptx`
- 后端适配器：`JavaOfficeExporterGateway` 同步执行 `java -jar ... --input ... --output ... --target ...`

Document Configuration 独立于 Report DSL。当前 exporter 使用内置默认值，后续可由边界适配器映射外部可选配置。

## 配置优先级

未来开放外部 Document Configuration 后，文档样式按以下优先级解析：

```text
显式传入的 Document Configuration
  > Report DSL 中的单表展示声明
  > exporter 内置默认值
```

当前尚未开放外部配置入参；没有外部配置时，DSL 明确声明的 `showTitle/showHeader` 应优先，缺失字段再使用 exporter 内置默认。

## 运行时文件边界

- 部署和本地运行默认使用仓库根目录 `.runtime/`。
- 自动化测试通过 `REPORT_SYSTEM_DATA_DIR` 覆盖数据根目录，统一写入仓库根目录 `.test/`。
- Report DSL 临时输入、Markdown、DOCX 和 PPTX 产物均进入当前数据根目录下的 `generated_documents/`，不写入源码目录。
- Maven 标准构建产物仍位于 `modules/exporter/target/`。

## 已知待收敛项

- `showHeader` 当前在归一化层被借用为分页重复表头语义，需要拆分“是否展示表头”和“分页时是否重复表头”。
- `showTitle` 已进入 DSL，但尚未完整接入 DOCX/PPTX 表格渲染。
- 表格最大数据行数当前底层统一兜底为 `200`；目标内置默认值为 Word `200`、PPT `10`。
- 后续实现时，Word 表格标题使用表格前独立标题段落；PPT 表格标题占用表格区域顶部一行，数据表向下收缩。
- PDF 派生转换尚未接入；开放前后端稳定返回校验错误。

完整 POI 转换细节见 [报告导出 POI 转换实现](poi-exporter.md)。
