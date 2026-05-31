# Exporter 测试用例

| ID | 分类 | 目标 | 实现位置 |
|---|---|---|---|
| EX-DSL | DSL 契约 | Jackson round-trip 与 BI Engine DSL 归一化 | `modules/exporter/src/test/java/com/chatbi/report/dsl/` |
| EX-DOCX | Word | 封面、目录、标题、宽表、空表和组合表格 | `modules/exporter/src/test/java/com/chatbi/exporter/` |
| EX-PPTX | PPT | 页眉页脚、页码、紧凑表格、图表和组合表格 | `modules/exporter/src/test/java/com/chatbi/exporter/` |
| EX-CLI | CLI | `--target auto`、格式冲突和文件生成 | `modules/exporter/src/test/java/com/chatbi/exporter/` |

## 文件级清单

| 文件 | 用例数 | 主要覆盖目标 |
|---|---:|---|
| `src/test/java/com/chatbi/exporter/OfficeExporterStyleTest.java` | 18 | DOCX、PPTX、组合表格、目录、封面、表格和 CLI |
| `src/test/java/com/chatbi/report/dsl/ReportDslJsonTest.java` | 2 | Java DSL model Jackson round-trip |
