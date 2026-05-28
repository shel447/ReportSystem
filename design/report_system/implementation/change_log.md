# 实现设计 Change Log

本文件记录 `design/report_system/implementation/` 维度的实现设计变更。

记录原则：

- 只记录会影响实现分层、运行时职责、数据流或验证策略的设计实现调整
- 聚焦"实现上怎么落、改了哪些实现约束、验证如何变化"
- 不替代代码提交记录；业务方案层变更请见 [../../change_log.md](../../change_log.md)

## 2026-05-28 CompositeTable 无缝拼接导出

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中"2026-05-28 CompositeTable 无缝拼接导出"
- 实现设计调整：
  - `BiEngineDslNormalizer` 保留 `compositeTable` 为单个 VDoc 节点，子表作为 `children` 挂载，不再展开成多个普通 block。
  - DOCX 新增 `compositeTable` renderer，连续渲染多个子表且不插入 gap paragraph；每个子表都使用页面可用总宽度。
  - PPTX 新增 `compositeTable` renderer，使用父布局作为整体区域，按子表行数比例纵向切分高度，并保持所有子表 `x/w` 一致。
- 验证要求：
  - 测试覆盖归一化保留组合节点、DOCX 子表连续且总宽度一致、PPTX 子表同宽且纵向相接。
  - Maven 测试和打包通过，样例 Word/PPT 视觉确认组合表格不再留白或重叠。

## 2026-05-28 Word Catalog 目录编号、封面与宽表自适应

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中"2026-05-28 Word Catalog 目录编号、封面与宽表自适应"
- 实现设计调整：
  - `BiEngineDslNormalizer` 将 flow DSL 归一化为 catalog 树，catalog/subCatalog 带 `outlineNumber/outlineLevel`，section 只保留组件内容。
  - `BiEngineDslNormalizer` 将 `cover.author/date` 拆成独立封面字段，DOCX 封面不再拼接为居中 note。
  - `ReportDocxExporter` 递归渲染 catalog/subCatalog 目录和正文标题，不再输出 section title。
  - `ReportDocxExporter` 使用 `cover.image` 生成相对 page 的 behind-text anchor 图片并铺满首页，再用整页封面画布叠加标题、说明、报告人与时间。
  - DOCX 表格使用固定布局，按页面可用宽度写入 `tblW/tblGrid/tcW`，宽表按列声明宽度比例压缩并降低字号。
- 验证要求：
  - 测试覆盖 catalog 编号、section title 不输出、封面背景图 behind-text 铺满首页、封面左下角报告人/时间、宽表列宽不超过页面可用宽度。
  - Maven 测试和打包通过，样例 Word 视觉确认目录层级与宽表效果。

## 2026-05-28 Office Exporter 默认视觉样式优化

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中"2026-05-28 Office Exporter 默认视觉样式优化"
- 实现设计调整：
  - DOCX text 节点由 1x1 表格样式改为普通段落，去除文本框边框和背景底色。
  - PPTX text 节点不再设置边框线，保留原文本、字体、位置和背景填充。
  - PPTX master header/footer 不再绘制 1px accent 装饰线，页眉、页脚和页码文字保持输出。
- 验证要求：
  - 增加样式回归测试，覆盖 Word 文本不生成额外表格、PPT 文本框不输出边框、PPT 页眉页脚文字保留且不输出 accent 线条。
  - Maven 测试、打包和样例导出通过，并用 Office/WPS 视觉确认。

## 2026-05-28 Report DSL Java 模型 JSON round-trip

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中"2026-05-28 Report DSL Java 模型支持 JSON round-trip"
- 实现设计调整：
  - `com.chatbi.report.dsl` 普通模型类支持 Jackson 忽略未知字段。
  - enum 通过稳定 wire value 序列化和反序列化。
  - `BIEngineComponent`、`Series`、`ComponentLayout`、`ValueFormat` 和 `PagedContentItem` 补齐多态反序列化映射。
  - 新增 `ReportDslJson` 作为契约模型默认 JSON 入口；现有 `DslReader` 与导出运行时不切换。
- 验证要求：
  - 测试覆盖 flow/paged、组件、series、layout、valueFormat、枚举输出和未知字段兼容。
  - Maven 测试与打包通过。

## 2026-05-28 Java Office Exporter 照搬 poi-dsl-exporter

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中"2026-05-28 Java Office Exporter 切换为 poi-dsl-exporter 实现"
- 实现设计调整：
  - `services/java-office-exporter/src/main/java` 替换为 `chat_bi_ui/tools/poi-dsl-exporter/src/main/java/com/chatbi`。
  - Maven shade 入口改为 `com.chatbi.exporter.CliMain`，模块坐标和 JAR 名称暂保持 `java-office-exporter`。
  - 删除旧 `com.bi.report.generation` 运行时和 `com.bi.report.model` 契约模型包，避免同一模块内保留两套导出实现。
- 验证要求：
  - Maven 编译和打包通过。
  - 静态检查确认 `src/main/java` 中只保留 `com/chatbi` Java 源码树。

## 2026-05-28 Java Report DSL 契约模型包

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中"2026-05-28 Java 侧新增 Report DSL 契约模型"
- 实现设计调整：
  - `services/java-office-exporter/src/main/java/com/bi/report/model/` 新增独立 Report DSL Java 模型包。
  - 该模型包按当前 `report-dsl.schema.json` 定义 `ReportDsl`、对象模型和枚举模型，使用 Jackson 注解保留 DSL 字段名。
  - 该模型包暂不被 `com.bi.report.generation.*` 引用，现有导出运行时继续使用 `com.bi.report.generation.model`。
- 验证要求：
  - Java 编译通过。
  - 静态检查确认现有导出包没有引用 `com.bi.report.model`。

## 2026-05-26 报告导出 POI 转换实现文档

- 背景问题：
  - Java Office Exporter 已完成完整实现（30 个类型化模型、DOCX/PPTX 导出器、35 个测试用例），但缺少详细的实现文档说明从 Report DSL 到 POI 对象的完整转换流程。
- 实现设计调整：
  - 新增 `报告导出POI转换实现.md`，核心关注：
    - 架构总览：转换流程图、核心组件职责表
    - 数据模型映射：Report DSL 结构、组件类型体系、关键数据属性
    - Word 文档生成流程：整体结构、封面/目录/章节/组件/签署页/页眉页脚渲染
    - PowerPoint 文档生成流程：幻灯片尺寸、封面/目录/章节/组件渲染
    - 主题系统：ThemeTokens 定义、内置主题、StyleResolver
    - 关键实现细节：页边距、分页符、标题样式、颜色转换
    - 测试覆盖：4 个测试类、35 个测试用例清单
    - 构建与运行：Maven 命令、HTTP API 端点
    - 已知限制与未来改进：图表原生渲染、表格合并、图片支持
- 受影响的实现设计主题：
  - [外部集成与导出实现.md](外部集成与导出实现.md)
- 验证要求：
  - 文档中的代码示例与实际实现一致
  - 文档中的 POI 对象映射表与实际渲染逻辑一致
  - 文档中的测试用例清单与实际测试文件一致

## 2026-05-26 Java 导出器完整实现 (Word + PPT)

- 背景问题：
  - 旧 Java 导出器为单文件骨架实现 (`JavaOfficeExporterServer.java`)，仅生成最小有效 OOXML 文件 (标题+原始 JSON 文本)，无法渲染报告 DSL 的完整结构 (封面/目录/章节/表格/图表/签署页)。
- 实现设计调整：
  - 构建系统从 `javac` 直编切换为 Maven + maven-shade-plugin fat jar。
  - 依赖引入：Apache POI 5.4.0 (poi-ooxml)、Jackson 2.18.2。
  - Java 版本要求从 17 提升至 21。
  - 代码组织从单文件重构为分层架构 (core/model/style/chart/docx/pptx)，共 20+ Java 文件。
  - DOCX 导出 (`ReportDocxExporter`)：封面、目录、递归章节 (Heading1/2/3)、文本/Markdown (粗体/斜体/列表)、表格 (表头着色/交替行/合并)、图表 (XDDF 原生 line/bar/pie + 降级表格)、签署页、页眉/页脚。
  - PPTX 导出 (`ReportPptxExporter`)：封面幻灯片、目录幻灯片、章节标题页、内容页 (文本框/表格/图表)、摘要页、封底，支持 flow 和 paged 两种结构。
  - 图表规范层 (`ChartSpecParser`)：从 ChartComponent.dataProperties 解析 categories/series，line/bar/pie 使用 XDDF 原生图表，其他类型降级为数据表格+说明。
  - 主题系统 (`ThemeTokens + StyleResolver`)：内置 enterprise-light/enterprise-dark 两套主题，支持通过请求 options.theme 切换。
  - HTTP 入口 (`HttpServerMain`) 替换旧 `JavaOfficeExporterServer`，保持 `/health` 和 `/exports/{word|ppt}` 协议不变。
  - Python 端 (`java_office.py`) 更新为 Maven 构建 + `java -jar` 启动，自动检测 JAR 过期并触发构建。
- 受影响的实现设计主题：
  - [外部集成与导出实现.md](外部集成与导出实现.md)
- 验证要求：
  - 安装 JDK 21 + Maven 后执行 `mvn clean package` 构建成功。
  - 启动 Java 服务后 `/health` 返回 ok。
  - 通过 `POST /rest/chatbi/v1/reports/{reportId}/document-generations` 生成 Word/PPT 文件可用 Office 打开。
  - 生成的文档包含封面、目录、章节标题、表格数据、图表 (或降级表格)。

## 2026-05-26 报告 DSL schema 微调

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中"2026-05-26 报告 DSL schema 微调"
- 实现设计调整：
  - `report_runtime.domain.models` 新增 `ReportType` 枚举映射，`ReportBasicInfo` 新增 `report_type` 属性（公开字段 `reportType`），删除 `sub_title` 属性。
  - `report_runtime.domain.models` 新增 `ColumnLineageSource` 和 `ColumnLineageTracing` dataclass，`Column` 新增 `lineage_tracing` 和 `order` 属性。
  - `ChartOption` 定义位置调整不影响运行时模型。
  - 示例文件同步删除 `basicInfo.subTitle`。
- 验证要求：
  - schema 校验覆盖 `reportType` 枚举值、`ColumnLineageSource` 必填字段、`Column.lineageTracing` 引用
  - 后端模型测试覆盖 `ReportBasicInfo` 无 `subTitle`、有 `reportType`
  - flow/paged DSL 示例通过最新 schema

## 2026-05-26 报告模板 schema 微调

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中"2026-05-26 报告模板 schema 微调"
- 实现设计调整：
  - `report-template.schema.json` 顶层 `required` 去掉 `id` 和 `parameters`，后端模板 upsert DTO 和校验逻辑需同步放宽。
  - `CompositeTableColumn` 从 schema `$defs` 中删除。后端待清理项：
    - `template_catalog.domain.models`：删除 `CompositeTableColumn = TableColumn` 别名及 `composite_table_column_from_dict` / `composite_table_column_to_dict` wrapper 函数
    - `report_runtime.domain.models`：删除无用 `CompositeTableColumn` import
    - `tests/test_report_runtime_service.py`：5 处 `CompositeTableColumn` 改为 `TableColumn`
- 验证要求：
  - schema 校验覆盖无 `id` / 无 `parameters` 的模板通过，旧 `CompositeTableColumn` 引用失败
  - 后端代码清理后运行现有测试确认无回归

## 2026-05-26 `generate_report_segment` 章节重新生成实现设计

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中"2026-05-26 `/chat` 新增 `generate_report_segment` 指令"
- 实现设计调整：
  - `ConversationService.send_message` 新增 `generate_report_segment` 分派分支，调用 `_generate_report_segment` 方法。
  - `_generate_report_segment` 负责加载 `ReportInstance` 与关联 `TemplateInstance`，解析 `template` 字段中的 `reportId`、`sectionId`、`outline`，委托 `ReportRuntimeService.preview_section_regeneration` 完成章节编译。
  - `ReportRuntimeService` 新增 `preview_section_regeneration` 方法，复用现有纯函数：
    - 在 `TemplateInstance.catalogs` 树中按 `sectionId` 递归定位 `TemplateInstanceSection`
    - 应用新 `outline`，标记 `user_edited = true`，评估 `skeleton_status`
    - 调用 `build_execution_bindings()` 重建执行绑定
    - 调用 `_build_section_components(section)` 生成新 components、summary、additional_infos
    - 返回 `ReportSection` DSL 片段与 `ReportGenerateMeta`
  - 不持久化 `ReportInstance`、`TemplateInstance`，不使文档产物失效
  - 流式 `delta` 复用 `add_section` 动作
- 验证要求：
  - 后端测试覆盖 `preview_section_regeneration` 的章节定位、大纲应用、绑定重建、组件编译
  - 后端测试覆盖 `REPORT_SEGMENT` 响应结构
  - 后端测试覆盖 `sectionId` 不存在时返回 `SECTION_NOT_FOUND` 错误
  - 后端测试覆盖 `reportId` 不存在或状态非 `available` 时的错误处理

## 2026-05-14 Report DSL GenerateMeta 参数与大纲结构纠偏

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-05-14 Report DSL GenerateMeta 参数与大纲结构纠偏”
- 实现设计调整：
  - 移除 DSL 专用 `ReportParameter/ReportSectionOutline/ReportOutlineItem`，`ReportGenerateMeta.parameters` 恢复使用模板侧 `Parameter`。
  - `ReportGenerateMeta.outline` 恢复使用模板侧 `OutlineDefinition`，公开 schema 定义名为 `GenerateOutline`。
  - `additionalInfos` canonical 输出和旧 `additionalInfo/content` 读取兼容保持不变。
- 验证要求：
  - schema 覆盖完整 `Parameter/RequirementItem` 通过，简化参数和简化 outline item 失败。
  - 后端 round-trip 覆盖完整参数与大纲结构。

## 2026-05-14 Report DSL GenerateMeta 实现对齐

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-05-14 Report DSL GenerateMeta 契约对齐”
- 实现设计调整：
  - `report_runtime.domain.models` 新增 DSL 专用 `ReportParameter/ReportSectionOutline/ReportOutlineItem`，避免 `GenerateMeta` 复用模板参数与模板 outline 模型。
  - `ReportGenerateMeta` canonical 输出 `additionalInfos`，条目输出 `type/value/name/appendix`；模型层兼容读取旧 `additionalInfo`、`content` 和旧散字段 `summary/sql/api/knowledge/prompt`。
  - 运行时 SQL 与 Summary 证据统一写入 `additionalInfos[]`，不再输出 `reportMeta[sectionId].summary`。
- 验证要求：
  - schema 覆盖 `status/question` 必填、旧公开字段失败、TS 风格 `parameters/outline` 通过。
  - 后端测试覆盖新 canonical round-trip 和旧输入兼容读取。

## 2026-05-14 Report DSL 小幅增强实现对齐

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-05-14 Report DSL 小幅增强与说明书”
- 实现设计调整：
  - `report_runtime.domain.models.ReportDsl` 增加 `back_cover`，公开字段为 `backCover`。
  - DSL 行合并模型统一为 `MergeRowInfo`，不再保留额外 `MergeRowConfig` 定义。
  - `ChartDataProperties` 增加 `x_axis/y_axis`，输出到 `dataProperties.xAxis/yAxis`；模型层兼容读取历史顶层 `ChartComponent.xAxis/yAxis`。
  - 新增 Report DSL 说明书，解释 flow/paged、组件、图表、表格和 `reportMeta` 的使用方式。
- 验证要求：
  - flow/paged DSL 示例通过最新 schema。
  - 后端测试覆盖 `backCover`、`MergeRowInfo` 和图表轴配置迁移。

## 2026-05-13 Report DSL BI Engine 字段补齐

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-05-13 Report DSL 补齐 BI Engine 字段”
- 实现设计调整：
  - `report_runtime.domain.models` 补齐 `ReportBasicInfo`、`ReportLayout`、组件 dataProperties、表格列、图表 series/options 与 `ReportAdditionalInfo` 的 from/to dict 透传。
  - `ReportCover.layoutTemplate` 测试数据切换为 `TITLE_TOP/TITLE_CENTER`，旧 `default` 按最新 schema 判定为非法。
  - `ReportGenerateMeta` 继续 canonical 输出 `additionalInfo`，同时兼容读取 `additionalInfos`。
- 验证要求：
  - flow/paged DSL 示例通过最新 schema。
  - 后端测试覆盖新增字段 round-trip、cover 枚举收窄和旧 `additionalInfos` 读取兼容。

## 2026-05-12 外部 Dynamic Node v6 契约对齐

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-05-12 对齐外部 Dynamic Node v6 模板契约”
- 实现设计调整：
  - `report-template.schema.json` 新增 Chapter 专用 dynamic 约束，Chapter 级仅允许 `foreach/foreachCase`，不允许 `custom`。
  - `template-instance.schema.json` 的 `DynamicContext.nodeType` 扩展为 `catalog | section | slide`。
  - paged `SlideDefinition.dynamic.custom` 作为外部页面生成入口，实例态 custom slide 记录 `nodeType=slide`。
  - slide 内 `SectionDefinition.dynamic.custom` 仍记录为 `nodeType=section`，后续 DSL 编译时按 v6 合并到当前 slide 组件集合。
  - 外部请求目标协议从旧 `nodeType/nodeId/prompt` 收敛为 v6 `parameters/templateNode/context`；HTTP gateway 的完整迁移与 paged DSL 合并后续实现。
- 验证要求：
  - schema 覆盖 catalog/section/slide custom、section custom 必须有 outline、Chapter custom 失败。
  - 模型测试覆盖 `DynamicContext.nodeType=slide` round-trip。

## 2026-05-12 Report DSL flow 兼容边界纠偏

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-05-12 Report DSL PPT 扩展不改变 flow 契约”
- 实现设计调整：
  - `ReportCatalog` canonical 输出恢复为 `name`；模型层兼容读取误同步期间出现的 `title`。
  - `ReportSection` 恢复输出 `summary/order`，不把 paged-only 字段写入 flow section。
  - 新增/恢复 `ReportCover/ReportCoverContent` 与 `ReportSignaturePage/ReportSigner` 核心模型。
  - `ReportSummary` 恢复旧 `id/overview` 输出。
  - `BuildReportDslService` 生成的 flow DSL 恢复 `catalogs[].name`、`sections[].summary` 与旧顶层 `summary`。
- 验证要求：
  - schema 覆盖旧 flow payload、旧 cover 结构、custom flow fragment 与 paged content 互斥规则。
  - 后端测试覆盖 flow cover round-trip 与 paged content round-trip。

## 2026-05-12 Report DSL single-root flow/paged 实现

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-05-12 Report DSL 支持 single-root flow/paged 结构”
- 实现设计调整：
  - `report_runtime.domain.models.ReportDsl` 新增 `structure_type/content`，flow 输出 `catalogs + layout`，paged 输出 `content`。
  - 新增 `ReportSlide`、`ReportSlideSection`，支持 paged DSL from/to dict。
  - `ReportCatalog` 维持 flow 旧契约，canonical 输出仍为 `name`。
  - `ReportBasicInfo.schema_version` 内部兼容访问器映射到公开 `version` 字段。
  - `ReportGenerateMeta.additional_infos` 内部字段映射到公开 `additionalInfo`，`ReportAdditionalInfo` 输出 `{type, content}`。
  - `BuildReportDslService` 继续只编译 flow，但生成的 flow DSL 已满足新版 schema；paged 模板到 PPT DSL 的编译后续实现。
- 验证要求：
  - schema 覆盖 flow/paged 条件约束、paged content 不混放、旧 `columnKey` 失败。
  - 后端测试覆盖 flow/paged ReportDsl round-trip、custom fragment 校验、现有 flow 生成回归。

## 2026-05-12 PPT 分页模板结构核心模型

- 背景问题：
  - 模板目录核心模型只支持 flow 的 `catalogs`，无法保存 PPT 设计器需要的分页 chapter/slide 结构。
- 实现设计调整：
  - `template_catalog.domain.models.ReportTemplate` 新增 `structure_type` 与 `chapters`。
  - 新增 `ChapterDefinition`、`SlideDefinition`、`SlideLayout` dataclass，并补齐 from/to dict。
  - `report_runtime.domain.models.TemplateInstance` 新增 `structure_type` 与实例态 `chapters`。
  - 新增 `TemplateInstanceChapter`、`TemplateInstanceSlide` dataclass，并补齐 from/to dict。
  - 模板 upsert DTO 允许 `catalogs` 或 `chapters`，最终结构合法性继续交由正式 JSON Schema 校验。
  - 本轮不修改 `BuildReportDslService` 的 paged 编译逻辑，也不修改 PPT 导出器协议。
- 验证要求：
  - schema 覆盖 flow/paged 条件约束、chapter/slides 必填、flow/paged 入口互斥。
  - 后端测试覆盖模板与实例态 paged 核心模型往返。

## 2026-05-12 表格 mergeRows 行合并实现

- 背景问题：
  - 模板表格已有列合并定义，还需要在模板中表达按连续相同值合并行单元格的展示规则。
- 实现设计调整：
  - `template_catalog.domain.models` 新增 `MergeRowDefinition`，并挂到 `PresentationProperty` 与 `CompositeTablePartLayout`。
  - `report_runtime.domain.models` 新增 `MergeRowConfig`，`TableDataProperties.mergeRows` 输出使用 `column`，不使用 `columnKey`。
  - `BuildReportDslService` 在表格 `data` 已存在时，根据 `mergeRows` 定义计算 `startRowIndex/rowSpan/mergedText/column`。
  - 普通表格编译同时透传 `properties.columns` 到 DSL `dataProperties.columns`，作为 `mergeRows.column` 的列集合。
- 验证要求：
  - schema 覆盖模板 `mergeRows` 和 DSL `column` 字段。
  - 后端测试覆盖模板/DSL 模型往返、连续行合并计算，以及无 `data` 时不输出具体 `mergeRows`。

## 2026-05-09 Dynamic Custom 外部内容运行时实现

- 背景问题：
  - `dynamic.custom` 需要从预留配置升级为可运行的外部内容生成入口。
  - custom 既可能替换目录，也可能替换章节；章节仍要在模板实例中保留可编辑 outline。
- 实现设计调整：
  - `template_catalog.domain.models.DynamicDefinition` 使用显式 `url` 字段，不兼容旧占位 `config`。
  - `report_runtime.domain.models.DynamicContext` 支持 `type=custom`，并记录 `url/nodeType`。
  - 模板实例化阶段不展开 custom，但会在目录或章节实例上保留 custom 上下文。
  - Report DSL 编译阶段通过 `CustomContentGateway` 发起 HTTP POST，目录响应按 `ReportCatalog` 解析，章节响应按 `ReportSection` 解析。
  - custom HTTP 调用位于 application/infrastructure 层，领域服务只负责实例上下文标记。
- 验证要求：
  - schema 覆盖 custom 必填 `url`、禁止 `config`、章节 custom 必须有 outline。
  - 模型测试覆盖 `DynamicDefinition.url` 与 `DynamicContext.custom` round-trip。
  - 运行时测试覆盖目录和章节 custom 请求体、响应替换、非法响应失败。

## 2026-05-09 Dynamic/ForeachCase 实现

- 背景问题：
  - 旧 `foreach` 字段需要收敛为统一 `dynamic` 结构。
  - 模板需要支持特殊 foreach：按参数多值循环，但不同取值可命中不同 case 内容。
- 实现设计调整：
  - `template_catalog.domain.models` 新增 `DynamicDefinition/ForeachCaseDefinition/ForeachCaseBranch` 相关结构。
  - `CatalogDefinition/SectionDefinition` 以 `dynamic` 为 canonical 字段，兼容读取旧 `foreach` 并在输出时收敛为 `dynamic`。
  - `report_runtime.domain.models` 新增 `DynamicContext`，实例态输出 `dynamicContext`，旧 `foreachContext` 仅兼容读取。
  - `report_runtime.domain.services` 负责解释 `dynamic.foreach` 与 `dynamic.foreachCase`，`custom` 暂不做业务展开。
  - 前端类型同步声明 `dynamic` 与 `dynamicContext`，模板编辑页普通循环输入写入 `dynamic.type = foreach`。
- 验证要求：
  - schema 覆盖 `dynamic.foreach/foreachCase/custom` 合法性，以及旧 `foreach` 在新 schema 中失败。
  - 模型测试覆盖旧 `foreach` 输入归并为 canonical `dynamic`。
  - 运行时测试覆盖目录级与章节级 `foreachCase` 的多值、defaultCase 和空展开行为。
  - 运行后端测试与前端类型/构建验证。

## 2026-05-08 参数优先级、移除 Tags 与 Text 属性归并核心模型定义

- 背景问题：
  - 模板参数需要增加追问优先级定义，但本轮不进入对话追问排序业务实现。
  - 模板顶层 `tags` 从当前契约移除。
  - `text` block 的 `template/content` 需要归入 `PresentationProperty`。
- 实现设计调整：
  - `Parameter` dataclass 增加 `priority`，缺省为 `99`，from/to dict 支持 `priority`。
  - `ReportTemplate` dataclass、from/to dict 和模板 upsert DTO 移除 `tags`。
  - `PresentationProperty` 增加 `template/content`。
  - `PresentationBlock` 与 `TemplateInstancePresentationBlock` 不再序列化 direct `template/content`；from dict 兼容旧字段并归并到 `properties`。
  - 为避免本轮改业务实现，核心模型保留 `block.template/block.content` 兼容访问器，映射到 `properties.template/content`。
- 验证要求：
  - schema 验证覆盖 `priority` 边界、顶层 `tags` 禁止、text 的 `properties.template/content` 要求。
  - 模型 round-trip 覆盖 `priority` 缺省、`tags` 不输出、旧 text direct 字段归并。
  - 运行现有后端测试，确认当前业务流程不受核心模型收口影响。

## 2026-05-08 Presentation 属性扩展核心模型定义

- 背景问题：
  - 模板定义层新增 chart 首选类型、普通表格列定义、标题显示和默认展示条数。
  - 复合表子表布局需要复用同一套表格列定义和展示属性。
- 实现设计调整：
  - `template_catalog.domain.models` 新增统一 `TableColumn`，并保留 `CompositeTableColumn` 兼容入口。
  - `PresentationProperty` 补齐 `preferredType/columns/showTitle/defaultDisplayRows/mergeColumns` 的 dataclass 与 from/to dict。
  - `CompositeTablePartLayout` 补齐 `showTitle/defaultDisplayRows`，并让 `columns` 复用 `TableColumn`。
  - 本轮不接入运行时 DSL 编译透传，不更新前端类型和渲染逻辑。
- 验证要求：
  - 静态解析 schema 与 example。
  - 最小 payload 验证 `PresentationProperty` 与 `CompositeTablePartLayout` 新字段 round-trip。
  - 运行现有后端测试，确认兼容入口不破坏当前流程。

## 2026-05-08 Presentation Block 类型收敛实现

- 背景问题：
  - 模板/实例态 presentation 类型需要收敛到 `text/chart/table`，同时短期兼容既有 `composite_table`。
  - `text` block 需要模板态 `template` 与实例态 `content` 的序列化和运行时编译链路。
- 实现设计调整：
  - 模板 schema、实例态 schema、后端 dataclass、前端类型统一声明 `text/table/chart/composite_table`。
  - `report_runtime.domain.services` 在实例化阶段渲染 `properties.template -> properties.content`。
  - `BuildReportDslService` 补齐 `text -> TextComponent`、`chart -> ChartComponent` 编译，保留普通 `table` 与兼容 `composite_table` 编译。
  - Report DSL 后端模型补齐 `TextComponent/TextDataProperties` 与 `ChartComponent/ChartDataProperties` 序列化。
- 验证要求：
  - 后端测试覆盖 text 模板实例化、text/chart DSL 编译、text/chart 序列化往返和 schema 类型约束。
  - 现有普通表格 `mergeColumns` 与 `composite_table` 测试继续通过。

## 2026-04-20 application/domain/infrastructure 函数签名类型收口

- 背景问题：
  - 模板、模板实例、报告 DSL 已经收口为 dataclass，但 `application/domain/infrastructure` 的不少函数参数和返回值仍然沿用 `dict[str, Any]`。
  - 这会让业务阅读者无法仅凭函数签名判断输入输出模型，代码语义仍然依赖字符串 key 和记忆。
- 实现设计调整：
  - 收口原则固定为：
    - 业务函数优先使用正式类型对象
    - 原始 JSON 只留在 HTTP 路由、schema 校验、开放型上下文和表格行数据等边界位置
  - `template_catalog.application`：
    - `create_template/update_template/get_template/export_template/preview_import_template` 统一围绕 `ReportTemplate`、`TemplateImportPreview`、`TemplateSummary`
    - 仓储 `create/update` 不再接受 `dict | ReportTemplate` 双轨输入
  - `report_runtime.application`：
    - `get_report_view/serialize_report_answer/generate_documents/resolve_download` 统一围绕 `ReportView`、`ReportAnswerView`、`DocumentGenerationResult`、`DownloadResolution`
    - `build_report_dsl` 正式要求 `ReportTemplate`，不再在应用层做临时 `dict -> ReportTemplate` 兜底
  - `conversation.application`：
    - `send_message` 正式接收 `ChatCommand`，返回 `ChatResponse`
    - 会话列表/详情/删除/派生统一围绕 `SessionSummary`、`SessionDetail`、`DeleteResult`、`ForkSessionResult`
    - 聊天消息持久化边界统一围绕 `ConversationMessageContent/Action/Meta`
  - `report_runtime.domain.services`：
    - `instantiate_template_instance/collect_template_parameters` 等核心领域函数只接收正式 dataclass，不再接受 `dict | dataclass` 联合输入
  - 路由层职责保持不变：
    - 负责 `JSON <-> dataclass` 转换
    - 不把裸字典继续传入业务服务
- 验证要求：
  - 新增后端测试锁住关键 service/repository 签名必须使用正式类型对象
  - 路由测试和应用服务测试同步改为以正式 dataclass 作为 fake service 输入输出
  - 全量验证基线维持：
    - `python -m pytest src/backend/tests -q`
    - `npm test`
    - `npm run build`

## 2026-04-19 scoped 参数运行时修复

- 关联提交：
  - GitHub PR `#15`
  - merge commit `e8e9371`
- 背景问题：
  - 代码级 review 暴露出 3 个实现缺口：
    - 对话服务只按模板根参数做抽取和缺参判断
    - 前端只更新顶层 `templateInstance.parameters`
    - `multi=true` 的参数在 UI 上仍被降级为单值输入
- 实现设计调整：
  - `conversation` 应用服务改为递归收集模板根、目录、章节三层参数定义，并在以下环节统一复用：
    - 首轮问题参数抽取
    - 当前实例参数值合并
    - 缺参判断
    - ask 参数回显
  - `report_runtime.domain.services` 增加递归参数收集能力，用于：
    - 计算整棵实例树的有效参数值
    - 在实例物化时把 scoped 参数正确写回目录与章节节点
    - 在 `parameterConfirmation` 中按整棵实例树判断缺参
  - `ChatPage` 前端交互改为：
    - `multi=true + free_text` 使用多行输入控件
    - `multi=true + enum/dynamic` 使用多选控件
    - 提交时同步刷新嵌套在 `catalogs/sections` 下的 scoped 参数状态
- 受影响的实现设计主题：
  - [统一对话实现.md](统一对话实现.md)
  - [报告运行时实现.md](报告运行时实现.md)
  - [总体实现架构.md](总体实现架构.md)
- 验证要求更新：
  - 新增后端测试，锁住 scoped 参数抽取与缺参判断
  - 新增前端测试，锁住多值参数交互与模板实例嵌套参数同步
  - 全量验证基线维持：
    - `python -m pytest src/backend/tests -q`
    - `npm test`
    - `npm run build`
- 后续约束：
  - 从本次开始，所有实现设计调整都统一追加到本文件，不再只散落在专题实现文档中。

## 2026-04-19 `ask.status` 对话级锁定标识

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-04-19 `ask.status` 对话级锁定标识”
- 实现设计调整：
  - `conversation` 的 `Ask` 载荷统一增加 `status`
  - `ConversationService` 在生成新追问时固定写入 `ask.status = pending`
  - 当用户成功提交 `reply` 后，由聊天仓储回写最近一条待处理追问消息，把其 `ask.status` 刷新为 `replied`
  - 前端聊天页只依据 `ask.status` 控制当前追问是否仍可编辑，不再用 `parameterConfirmation.confirmed` 反推消息锁定态
- 验证要求：
  - 后端测试锁住：
    - `POST /chat` 返回的 `ask.status`
    - 历史追问在回复后被刷新为 `replied`
  - 前端测试锁住：
    - `ask.status = replied` 时不再展示可提交编辑器

## 2026-04-19 `/chat` 流式报告增量 `delta`

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-04-19 `/chat` 流式报告增量 `delta`”
- 实现设计调整：
  - `chat` 路由的 SSE 输出改为多事件包络，而不是单次透传完整 `ChatResponse`
  - 流式事件统一使用现有 `message` 通道，顶层增加正式 `ChatStreamEvent` 字段：
    - `eventType`
    - `sequence`
    - `status`
    - `delta?`
    - `answer?`
    - `ask?`
  - `delta.action` 首版只实现：
    - `init_report`
    - `add_catalog`
    - `add_section`
  - `delta` 仅由流式 `/chat` 产生，不进入非流式 `ChatResponse`、`TemplateInstance`、`ReportInstance` 或 `/reports/{reportId}`
  - 前端聊天页新增三条并行通道处理：
    - `steps`
    - `delta`
    - 最终 `answer`
- 验证要求：
  - 后端 SSE 契约测试锁住 `delta` 事件和最终 `answer/done`
  - 前端测试锁住 SSE 解析与增量渲染

## 2026-04-19 表定义与运行时数据库分离

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-04-19 表定义与运行时数据库分离”
- 实现设计调整：
  - 运行时唯一建表来源保持为 `src/backend/infrastructure/persistence/models.py + Base.metadata.create_all(...)`
  - `src/backend/infrastructure/persistence/schema_init.sql` 作为受版本管理的初始化稿，职责仅限初始化、审阅和结构比对
  - `src/backend/report_system.db` 明确降级为本地运行时文件，不再作为设计或结构基线
- 验证要求：
  - 新增测试锁住 `schema_init.sql` 对当前 ORM 表集合的覆盖
  - 新增测试锁住 `.gitignore` 对 `src/backend/report_system.db` 的忽略约束

## 2026-04-19 后端本地 Schema 镜像清理

- 背景问题：
  - `src/backend` 根目录仍保留过期的模板 schema、模板示例和报告 DSL schema 镜像文件。
  - 运行时代码与设计文档同时引用 `src/backend/*.json` 和 `design/report_system/schemas/*.json`，形成双轨定义。
- 实现设计调整：
  - 删除 `src/backend` 根目录下全部历史 JSON schema/示例镜像文件。
  - 后端运行时如需校验 `Report DSL`，统一从 `design/report_system/schemas/report-dsl.schema.json` 读取。
  - 实现文档与设计文档中的 schema 引用统一收口到 `design/report_system/schemas/*`，不再把 `src/backend/*.json` 作为正式契约来源。
- 受影响的实现设计主题：
  - [README.md](README.md)
  - [报告运行时实现.md](报告运行时实现.md)
  - [持久化与表结构实现.md](持久化与表结构实现.md)
- 验证要求：
  - 后端根目录不再保留任何本地 JSON schema 镜像文件。
  - 架构测试锁住 `src/backend/*.json` 清零，防止后续再次引入双轨 schema。

## 2026-04-19 `reply.sourceChatId` 精确回写

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中 `reply.sourceChatId` 要求
- 实现设计调整：
  - `chat` 路由的 `ReplyPayload` 正式增加必填 `sourceChatId`
  - `ConversationService` 不再按“最近一条待回复 ask”做隐式猜测，而是要求 `fill_params`、`confirm_params` 都显式携带 `sourceChatId`
  - 聊天仓储按 `conversation_id + user_id + source_chat_id` 精确定位 assistant 追问消息，并仅在该消息仍为 `ask.status = pending` 时回写为 `replied`
  - 前端聊天页提交 `reply` 时，固定使用当前追问消息自身的 `chatId` 回填 `sourceChatId`
- 受影响的实现设计主题：
  - [统一对话实现.md](统一对话实现.md)
  - [前端实现.md](前端实现.md)
- 验证要求：
  - 后端接口测试锁住 `reply.sourceChatId` 为必填
  - 后端会话测试锁住：只回写 `sourceChatId` 指向的那条追问消息
  - 前端测试锁住：提交 `reply` 时必须带上 `sourceChatId`

## 2026-04-20 `ParameterValue.label` 与 `Reply.parameters` 精简回填

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-04-20 `ParameterValue.label` 与 `Reply.parameters` 精简回填”
- 实现设计调整：
  - `TemplateParameter.values`、动态参数候选值、模板实例参数值三元组统一收敛为 `{label, value, query}`
  - 运行时不再读取或生成 `display` 字段；占位符默认展示通道也从 `display` 切到 `label`
  - `chat` 路由的 `ReplyPayload.parameters` 正式改为 `Record<parameterId, Scalar[]>`
  - 前端提交 `fill_params / confirm_params` 时，只回传参数值映射；服务端基于当前 `TemplateInstance` 中的参数定义与现值，重建新的参数运行态
  - `fill_params` 允许只提交本轮修改子集；`confirm_params` 仍要求 `reportContext.templateInstance` 中体现完整有效参数集
- 受影响的实现设计主题：
  - [统一对话实现.md](统一对话实现.md)
  - [报告运行时实现.md](报告运行时实现.md)
  - [前端实现.md](前端实现.md)
  - [模板目录实现.md](模板目录实现.md)
- 验证要求：
  - 后端测试锁住参数抽取、动态参数解析、`reply.parameters` 路由契约
  - 前端测试锁住 `fill_params` 提交的值映射载荷
  - 搜索确认生产代码不再依赖 `display` 作为正式参数值字段

## 2026-04-20 `composite_table` 模板正式落地

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-04-20 `CompositeTable` 模板正式支持”
- 实现设计调整：
  - 模板前端类型和后端运行时正式接受 `section.content.presentation.blocks[].type = composite_table`
  - `report_runtime` 在 `BuildReportDslService` 中新增 `composite_table -> CompositeTable` 编译规则
  - `query part` 编译为普通数据子表；`summary part` 编译为无表头的静态总结子表
  - `CompositeTable` 只作为 `Report DSL` 组件出现，不单独写回模板实例外的旁路结构
- 受影响的实现设计主题：
  - [模板目录实现.md](模板目录实现.md)
  - [报告运行时实现.md](报告运行时实现.md)
  - [前端实现.md](前端实现.md)
- 验证要求：
  - 后端测试锁住 `composite_table` 模板块成功编译为 DSL `compositeTable`
  - 前端类型与编辑态允许保留 `parts[]` 结构，不再把该 block 视为非法类型

## 2026-04-20 `TemplateInstance.section.content` 与复合表 part 运行态

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-04-20 `TemplateInstance` 正式承载 `CompositeTable` 实例态”
- 实现设计调整：
  - `TemplateInstance.section` 正式补齐 `content`，并保持与模板 `section.content` 同构
  - `instantiate_template_instance` 在实例化章节时，不再只构造 `outline + runtimeContext`，而是同步物化 `section.content.datasets/presentation.blocks`
  - `composite_table.parts[]` 在实例态保留原顺序与结构；`query part`、`summary part` 统一补最小 `runtimeContext`
  - 前端 `TemplateInstance` 类型与报告详情页同步接受并展示 `section.content`
  - `template-instance.schema.json` 与 `template-instance.example.json` 同步收口，保证设计资料包内部自洽
- 受影响的实现设计主题：
  - [统一对话实现.md](统一对话实现.md)
  - [报告运行时实现.md](报告运行时实现.md)
  - [前端实现.md](前端实现.md)
- 验证要求：
  - 后端测试锁住 `TemplateInstance.section.content` 不丢失
  - 后端测试锁住 `query/summary part.runtimeContext` 最小字段
  - 前端测试锁住报告详情页能读取模板实例中的内容块信息

## 2026-04-20 模板、模板实例、报告 DSL 递归 dataclass 化

- 背景问题：
  - 代码虽然已经引入 `ReportTemplate`、`TemplateInstance`、`ReportInstance` 顶层 dataclass，但其 `parameters/catalogs/sections/report` 等递归属性仍大量以 `dict/list[dict]` 传播。
  - 这会导致业务层继续依赖字符串 key，领域模型名义上存在，实际上没有真正接管业务结构。
- 实现设计调整：
  - `template_catalog.domain.models` 重写为递归 dataclass 树：
    - `ReportTemplate`
    - `Parameter/ParameterValue/ParameterRuntimeContext`
    - `CatalogDefinition/SectionDefinition/OutlineDefinition/RequirementItem`
    - `DatasetDefinition/PresentationDefinition/PresentationBlock`
    - `CompositeTablePart/SummaryTableSpec/CompositeTablePartLayout`
  - `report_runtime.domain.models` 重写为递归 dataclass 树：
    - `TemplateInstance/TemplateInstanceCatalog/TemplateInstanceSection`
    - `ParameterConfirmation/ForeachContext/ExecutionBinding`
    - `TemplateInstanceSectionContent/TemplateInstancePresentationBlock`
    - `PartRuntimeContext`
    - `ReportDsl/ReportCatalog/ReportSection/ReportBasicInfo`
    - `MarkdownComponent/TableComponent/CompositeTableComponent`
  - 领域层与应用层的正式约束更新为：
    - 业务逻辑只操作 dataclass
    - 仓储负责 `JSON <-> dataclass` 映射
    - 路由层仍保持 JSON 契约，不把 dataclass 直接泄漏到 HTTP 边界
  - `conversation`、`report_runtime`、`template_catalog` 的核心服务全部改为围绕 dataclass 运转，不再把模板、模板实例、报告 DSL 当作裸字典树传递
  - 文档与导出适配器在调用外部系统前统一把 `ReportDsl` 序列化为 JSON，不反向影响领域模型
- 受影响的实现设计主题：
  - [README.md](README.md)
  - [模板目录实现.md](模板目录实现.md)

## 2026-04-20 公开字段 lowerCamelCase 统一改为 dataclass alias 驱动

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-04-20 接口字段命名统一为 lowerCamelCase”
- 实现设计调整：
  - `ReportTemplate`、`TemplateInstance`、`ReportDsl` 及其递归属性在后端领域层继续保持 `snake_case` 属性名，避免把 Python 实现细节强行改成小驼峰。
  - 所有公开 JSON 固定字段名统一通过 `dataclasses.field(metadata={"alias": "lowerCamelCase"})` 声明，不再依赖散落的手写键名字符串作为唯一真相来源。
  - `template_catalog.domain.models`、`report_runtime.domain.models` 的 `to_dict/from_dict` 统一通过 alias 工具读取 field metadata，完成 `snake_case <-> lowerCamelCase` 转换。
  - 仓储、路由、导出边界继续消费公开 JSON 契约，但其字段名来源必须回溯到 dataclass field alias，而不是重复定义第二套映射表。
- 受影响的实现设计主题：
  - [README.md](README.md)
  - [模板目录实现.md](模板目录实现.md)
  - [报告运行时实现.md](报告运行时实现.md)
- 验证要求：
  - 新增后端测试，锁住关键 dataclass 字段的 `metadata.alias`
  - 新增后端测试，锁住模板、模板实例、报告 DSL 的公开序列化结果仍为 lowerCamelCase
  - [统一对话实现.md](统一对话实现.md)
  - [报告运行时实现.md](报告运行时实现.md)
- 验证要求：
  - 新增或更新测试，锁住：
    - `TemplateInstance` 子节点为 dataclass，而不是 `dict`
    - `build_report_dsl` 返回 `ReportDsl` dataclass
    - 仓储与导出边界继续输出合法 JSON 契约
  - 全量验证基线：
    - `python -m pytest src/backend/tests -q`

## 2026-04-27 表格合并列实现

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-04-27 表格 Presentation 支持合并列定义”
- 实现设计调整：
  - `template_catalog.domain.models` 新增 `MergeColumnInfo`，并把 `mergeColumns` 挂到 `CompositeTablePartLayout`。
  - 普通 `PresentationBlock.type = table` 与实例态 `TemplateInstancePresentationBlock` 保留 `properties`，避免实例化后丢失合并列展示意图。
  - 新增 `PresentationProperty`，当前仅定义 `mergeColumns`，且仅对普通 `table` block 生效。
  - `report_runtime.domain.models.TableDataProperties` 新增 `mergeColumns`，序列化为 DSL 的 `dataProperties.mergeColumns`。
  - `BuildReportDslService` 正式编译普通 `table` block，并把普通表格 `properties.mergeColumns` 及复合表 query part 的 `tableLayout.columns/mergeColumns` 透传到 DSL table。
  - 前端模板与对话类型同步加入 `PresentationProperty.mergeColumns` 和 `TableLayout.mergeColumns`。
- 验证要求：
  - 后端测试锁住 `CompositeTablePartLayout` 和 `TableDataProperties` 的 `mergeColumns` round-trip。
  - 后端测试锁住普通 `table` block 和 `composite_table` query part 编译后的 `dataProperties.mergeColumns`。
  - 前端构建需通过 TypeScript 校验。
