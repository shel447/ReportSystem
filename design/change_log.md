# 设计方案 Change Log

本文件记录 `design/` 维度的正式设计方案变更。

记录原则：

- 只记录已经确认采用的设计方案变化
- 聚焦“为什么改、改了什么、影响哪些正式设计文档”
- 不重复记录纯代码实现细节；实现落地请见 [report_system/implementation/change_log.md](report_system/implementation/change_log.md)

## 2026-05-29 Report DSL 与 BI Engine 字段契约同步

- 变更动机：
  - Report DSL schema 已手动按 BI Engine 最新模型调整，设计说明需要同步到新的字段口径，避免实现继续依赖旧字段。
- 设计决策：
  - `basicInfo` 与 BI Engine `BasicInfo` 权威模型保持一致，正式字段收敛为资产元信息字段；`title/parameters/createdAt/updatedAt` 不再属于 `basicInfo`。
  - paged `Slide/SlideSection` 不再保留 `description`；页面说明通过组件表达。
  - 字段模型补充 `boolean` 类型，字段展示配置补充 `bitRate/enum/unit` 值格式和 `conditionalFormat` 条件格式；`displayPriority` 允许开放字符串或数字。
  - `ColumnLineageSource.enumValues/ui` 是来源系统字符串快照，结构化枚举与 UI 配置仍在 `Column.enumConfig/uiConfig` 表达。
  - 图表高级配置统一进入 `ChartAdvanceProperties`，包含 `responsive/xAxisLabelMode/sqlExplanation`；`ChartComponent.options` 不作为正式字段。
  - 表格高级配置补充 `sqlExplanation`；`GenerateOutline` 补充 `isBroken`。
- 影响范围：
  - `report_system/报告DSL定义与使用说明书.md`
  - `report_system/02-核心业务模型与规范Schema.md`
  - `report_system/implementation/报告运行时实现.md`
  - `report_system/implementation/外部集成与导出实现.md`

## 2026-05-29 Word 封面首页约束与静态链接目录

- 变更动机：
  - Word 封面中的报告人和报告时间在部分文档中可能被挤到第 2 页，破坏封面信息完整性。
  - 带封面的报告虽然元信息已回到首页，但封面后仍可能因为独立 page-break run 被挤出而多出空白第二页。
  - Word 目录页位置需要适度下移，但默认留白过大会造成目录过度下沉；目录项需要能点击跳转到正文。
  - Word/PPT 导出样式默认值需要与 Report DSL 分离，避免把导出器开关混入报告内容契约。
  - Word 正文中的 catalog 标题如果只靠字号/粗体模拟，无法被 Word 样式、导航窗格和后续目录能力识别为真正标题。
  - catalog 标题成为真实 Heading 后仍需要合适行前距，避免紧贴上一段正文。
- 设计决策：
  - 新增独立 `Document Configuration` 概念，作为生成文档时的可选配置；它不属于 Report DSL，不进入 Report DSL schema。
  - 配置按 `global` 与 `word/ppt/pdf` 文档类型分组；当前 Java exporter 先使用内置默认值，后续再接入外部可选传入。
  - Word 封面必须保证标题、说明、报告人和报告时间都位于首页；封面布局需要预留安全高度，避免文字溢出到下一页。
  - `cover.image` 作为铺满首页的 behind-text anchor 时，不能作为封面表格前的独立正文段落占用首页文本流高度。
  - 封面后的分页控制采用 `pageBreakBefore` 段落，避免空白第二页。
  - Word 封面报告人和报告时间默认位于右下角。
  - Word 目录页增加适度顶部留白，默认 `word.toc.topOffsetRatio = 0.05`。
  - 目录采用静态链接目录：目录项可点击跳转到对应正文 catalog/subCatalog 标题；不显示动态页码，不依赖 Word 更新域。
  - catalog/subCatalog 正文标题必须使用 Word 原生 Heading 样式和 outline level。
  - catalog/subCatalog 正文标题默认写入行前距：一级不少于 360twips，二级及以下不少于 240twips。
  - Word 表格默认不跨页重复 header；无数据表格使用合并数据行显示“无数据”。
- 影响范围：
  - `report_system/06-文档生成与导出架构.md`
  - `report_system/implementation/外部集成与导出实现.md`
  - `report_system/implementation/报告导出POI转换实现.md`

## 2026-05-29 默认页脚与 PPT 页码位置

- 变更动机：
  - 旧默认页脚 `Visual Document OS` 不符合当前产品标识；PPT 页码与页脚文本拼接在左侧，不符合右下角页码习惯。
  - PPT 每页左上角标题拼接报告名称或 header 前缀会造成重复；封面页额外显示左上角标题也不符合封面版式。
- 设计决策：
  - Word/PPT 导出在 `basicInfo.footer` 缺省时默认使用 `ChatBI`。
  - PPT 页码独立渲染在右下角，不再拼接到左侧页脚文本后。
  - PPT 页眉标题只显示当前页标题，封面页不显示左上角页眉标题。
- 影响范围：
  - `report_system/06-文档生成与导出架构.md`
  - `report_system/implementation/外部集成与导出实现.md`
  - `report_system/implementation/报告导出POI转换实现.md`

## 2026-05-29 PPT 表格紧凑默认样式

- 变更动机：
  - 当前 PPT 表格默认字号和行高偏大，一页内放置多个 10 行左右的数据表时容易超出页面或挤占过多空间。
- 设计决策：
  - `Document Configuration` 的 `ppt` 分组新增 `table` 默认配置，用于收敛 PPT 表格字号、行高、内边距和安全区域约束。
  - PPT 普通表格和组合表子表默认使用紧凑行高和较小字号，表格 anchor 限制在幻灯片安全区域内。
  - PPT 表格实际高度计算后做二次安全区收敛；底部越界时优先整体上移，仍放不下再压缩行高。
  - 该配置当前仍只作为 Java exporter 内置默认值，不改变 Report DSL 或导出边界 API。
- 影响范围：
  - `report_system/06-文档生成与导出架构.md`
  - `report_system/implementation/外部集成与导出实现.md`
  - `report_system/implementation/报告导出POI转换实现.md`

## 2026-05-29 Java 导出器按 reportType 判定 Word/PPT

- 变更动机：
  - paged/PPT DSL 在兼容或测试场景中可能同时携带 `catalogs` 等 flow 字段，若导出器只按结构字段判断，会把本应生成 PPT 的 DSL 误归一化为 Word。
- 设计决策：
  - Java Office Exporter 归一化 Report DSL 时优先读取 `basicInfo.reportType` 判定 Word/PPT。
  - `structureType` 只作为 `reportType` 缺失时的第二层语义提示；`content/catalogs` 只作为最后兜底。
  - CLI 自动推断导出目标时，如果 DSL 类型与输出文件扩展名冲突，应直接报错，不再静默生成错误格式。
- 影响范围：
  - `report_system/06-文档生成与导出架构.md`
  - `report_system/implementation/外部集成与导出实现.md`
  - `report_system/implementation/报告导出POI转换实现.md`

## 2026-05-28 CompositeTable 无缝拼接导出

- 变更动机：
  - `compositeTable` 表示多个子表组成的组合表格，导出时应呈现为连续表格，而不是拆成有间距或重叠的独立块。
- 设计决策：
  - `CompositeTable.tables[]` 按顺序纵向拼接；子表允许不同列结构。
  - Word/PPT 导出必须让多个子表总宽度对齐，子表之间不插入默认空白；Word 可使用单个物理表格和 `gridSpan` 保证视觉对齐。
- 影响范围：
  - `report_system/06-文档生成与导出架构.md`
  - `report_system/报告DSL定义与使用说明书.md`
  - `report_system/implementation/外部集成与导出实现.md`
  - `report_system/implementation/报告导出POI转换实现.md`

## 2026-05-28 Word Catalog 目录编号、封面与宽表自适应

- 变更动机：
  - Word 导出需要按 Report DSL 的 `catalogs/subCatalogs` 呈现正式目录层级，而不是把 section 当作目录节点。
  - 表格列数较多时，默认 Word 排版可能被内容撑开并超出页面范围。
  - Word 封面需要背景图片铺满首页，并让标题、报告人、时间等封面信息叠加在明确位置。
- 设计决策：
  - Word 目录与正文标题只根据 `catalogs -> subCatalogs` 自动生成层级编号。
  - `section` 是正式内容承载单元，不进入目录、不渲染 `section.title`。
  - Word 封面采用整页布局；`cover.image` 铺满首页作为背景图，标题、副标题和封面内容叠加在首页不同区域，报告人和时间分两行放在右下角。
  - Word 表格固定在页面可用宽度内，列宽按声明宽度比例压缩，单元格内容允许换行。
- 影响范围：
  - `report_system/06-文档生成与导出架构.md`
  - `report_system/implementation/外部集成与导出实现.md`
  - `report_system/implementation/报告导出POI转换实现.md`

## 2026-05-28 Office Exporter 默认视觉样式优化

- 变更动机：
  - 当前 Word 普通文本块带有文本框边框/底色，PPT 每页上下蓝色装饰线影响报告观感。
- 设计决策：
  - Word 普通文本块按纯正文段落输出，不再呈现文本框边框或浅底。
  - PPT 普通文本框不再呈现边框；默认去除页眉下方和页脚上方的蓝色装饰线，保留页眉、页脚和页码文字。
- 影响范围：
  - `report_system/implementation/外部集成与导出实现.md`

## 2026-05-28 Report DSL Java 模型支持 JSON round-trip

- 变更动机：
  - `com.chatbi.report.dsl` 已作为 Java 侧 Report DSL 契约模型进入 Java Office Exporter，但多态接口字段缺少明确的 JSON 反序列化规则。
  - 外部项目集成该模型时需要直接完成 Report DSL JSON 的序列化和反序列化，而不是只依赖导出器内部 VDoc 归一化链路。
- 设计决策：
  - `com.chatbi.report.dsl` 模型支持 Jackson JSON round-trip。
  - 组件、图表系列、组件布局、值格式和 paged content 使用明确的多态映射。
  - 新增独立 JSON 工具入口，现有 CLI/exporter 读取链路保持不变。
- 影响范围：
  - `report_system/implementation/外部集成与导出实现.md`

## 2026-05-28 Java Office Exporter 切换为 poi-dsl-exporter 实现

- 变更动机：
  - 报告文档生成能力需要对齐 `chat_bi_ui/tools/poi-dsl-exporter` 中已经沉淀的 POI 导出实现，减少两套 Java 导出代码分叉。
- 设计决策：
  - `services/java-office-exporter/src/main/java` 完整替换为 `poi-dsl-exporter/src/main/java/com/chatbi` 源码树。
  - Java 入口切换为 `com.chatbi.exporter.CliMain`，导出器以 CLI/库式编排能力为主。
  - 原 `com.bi.report.generation` HTTP 服务入口与 `com.bi.report.model` 契约模型包不再保留在 Java Office Exporter 中。
- 影响范围：
  - `report_system/implementation/外部集成与导出实现.md`
  - `report_system/implementation/报告导出POI转换实现.md`

## 2026-05-28 Java 侧新增 Report DSL 契约模型

- 变更动机：
  - 报告文档生成能力后续需要迁移到其他项目，迁移目标只消费 Java 代码，不直接复用当前 Python 后端模型。
  - 当前 Java 导出器已有运行时模型，但该模型服务于现有导出流程，不适合作为未来迁移时的独立 Report DSL 契约模型。
- 设计决策：
  - 在 Reporter Java 模块中新增 `com.bi.report.model` 包，按当前 `report-dsl.schema.json` 定义 Report DSL Java 模型。
  - 新模型暂不接入现有导出流程，不替换 `com.bi.report.generation.model`。
  - 多态、开放对象和 schema 未稳定结构在首版 Java 模型中以 `Object`、`Map` 或开放集合表达。
- 影响范围：
  - `report_system/schemas/report-dsl.schema.json`
  - `report_system/implementation/外部集成与导出实现.md`

## 2026-05-26 报告 DSL schema 微调

- 变更动机：
  - `ChartOption` 定义位置不够直观，应紧跟 `Series` 定义之后，与图表相关定义集中放置。
  - 报告需要区分输出类型（PPT/Word/Dashboard），`BasicInfo` 缺少 `reportType` 属性。
  - `BasicInfo.subTitle` 与 `Cover.subTitle` 语义重复，应去掉 `BasicInfo` 中的副本。
  - 表格列需要支持数据血缘追溯能力，`Column` 缺少 `lineageTracing` 和排序 `order` 属性。
- 设计决策：
  - `ChartOption` 从 `ResponsiveConfig` 之后移到 `Series` 之后、`ChartDataProperty` 之前。
  - 新增 `ReportType` 枚举（`PPT | Word | Dashboard`），定义在 `Status` 之后。
  - `BasicInfo` 中 `name` 字段下方新增 `reportType` 属性，引用 `ReportType` 枚举。
  - `BasicInfo` 中删除 `subTitle` 字段；`Cover.subTitle` 保留不动。
  - 在 `EnumValue` 之后新增 `ColumnLineageSource` 和 `ColumnLineageTracing` 两个定义。
  - `Column` 中 `uiConfig` 字段下方新增 `lineageTracing`（引用 `ColumnLineageTracing`）和 `order`（`number`）两个属性。
- 影响范围：
  - `report_system/schemas/report-dsl.schema.json`
  - `report_system/examples/report-dsl.example.json`
  - `report_system/examples/report-dsl-paged.example.json`
  - `report_system/报告DSL定义与使用说明书.md`
  - `report_system/03-运行时流程与状态机.md`
  - `report_system/implementation/报告运行时实现.md`

## 2026-05-26 报告模板 schema 微调

- 变更动机：
  - 报告模板顶层 `id` 和 `parameters` 在实际使用场景中不一定需要在模板定义阶段就提供，强制必填不利于模板草案的渐进式构建。
  - `CompositeTableColumn` 兼容模型已无任何 `$ref` 引用，属于废弃的兼容别名，应清理。
- 设计决策：
  - `report-template.schema.json` 顶层 `required` 数组去掉 `id` 和 `parameters`，保留为可选属性。
  - `report-template.schema.json` `$defs` 中删除 `CompositeTableColumn` 定义。
  - 说明书同步调整：`id` 和 `parameters` 从必填字段表移到可选字段表；删除 `CompositeTableColumn` 兼容说明。
- 影响范围：
  - `report_system/schemas/report-template.schema.json`
  - `report_system/报告模板定义与使用说明书.md`

## 2026-05-26 接口契约文档结构重构

- 变更动机：
  - `04-接口契约.md` 中 Dynamic Custom 外部内容协议被错误地放在 `/chat` 请求契约章节下，但它实际上是独立的外部接口协议，URL 由模板定义。
  - `parameter-options/resolve` 同样是服务端内部调用协议（服务端向模板 `parameter.source` 定义的外部 URL 发起请求），不是客户端直接调用的接口。
  - Dynamic Custom 和 Parameter Options 属于同一大类（服务端内部调用协议），与 `/chat`、`/reports` 等客户端接口需要按大类分开。
  - Dynamic Custom 段落末尾混入了与 `/chat` 响应和 Report DSL 相关的规则（ask 优先级、presentation 属性、表格行合并、图表轴配置等），不属于 Dynamic Custom 协议。
  - `ChatRequest` 的子结构（`reply`、`template`）缺少明确的从属关系说明。
  - `ChatRequest` JSON 示例缺少 `template` 字段。
  - `/chat` 请求契约和响应契约分散在不同顶级章节，应合并到同一 `/chat 契约` 父章节下。
- 设计决策：
  - 整体按两大类重组：`## 2. 客户端接口` 和 `## 3. 服务端内部调用协议`。
  - `## 1. 接口分类总览` 替代原"公开接口面"，按两类列出接口清单，`parameter-options/resolve` 从客户端接口列表中移除。
  - 客户端接口下：`2.1 模板接口`、`2.2 /chat 契约`（请求与响应合并到同一父章节）、`2.3 /reports 契约`。
  - `/chat 契约` 下按"请求"和"响应"两个子章节组织。
  - `POST /chat` 是流式接口，原 `ChatResponse` 与 `ChatStreamEvent` 合并为统一的 `ChatResponse（事件包络）`，每个 SSE 事件都是 ChatResponse。去掉 `sequence`、`requestId`、`apiVersion` 字段。
  - 请求下：ChatRequest 及其子结构（reply、template），标题明确从属关系。
  - 响应下：`ChatResponse（事件包络）` 及四个子结构（`ChatResponse.steps`、`ChatResponse.ask`、`ChatResponse.answer`、`ChatResponse.delta`），标题统一明确从属关系。
  - 链路约束新增 `generate_report_segment` 链路。
  - 服务端内部调用协议下：`3.1 Parameter Options 外部数据源`（排在前面）、`3.2 Dynamic Custom 外部内容生成`。
  - Parameter Options 补充说明：服务端向外部数据源发起请求，前端不直接调用。
  - `ChatRequest` JSON 示例补充 `template` 字段，`template` 子结构 JSON 示例精简为只展示子结构本身。
  - 混入 Dynamic Custom 的 7 条规则迁移到正确位置：`ask.parameters[].priority` 迁入 Ask；presentation 和 DSL 规则迁入 Answer。
- 影响范围：
  - `report_system/04-接口契约.md`

## 2026-05-26 `/chat` 新增 `generate_report_segment` 指令

- 变更动机：
  - 报告生成完成后，用户需要对单个章节的大纲（诉求）进行编辑并重新生成该章节内容，当前只有全量报告生成路径，缺少章节级重新生成能力。
  - 原始需求 `biz_requirement.md` 2.5 节明确要求"用户修改后，可以对局部内容重新生成，更新报告实例"。
- 设计决策：
  - `/chat` 接口 `instruction` 新增 `generate_report_segment`，复用现有对话通道。
  - `ChatRequest` 新增顶层可选字段 `template`，仅在 `generate_report_segment` 时必填，包含 `reportId`、`sectionId`、`outline` 三个子字段。
  - `outline` 复用 `OutlineDefinition` 结构（`requirement` + `renderedRequirement` + `items[]`），用户可编辑后提交。
  - 后端加载已有 `ReportInstance` 与关联 `TemplateInstance`，定位目标章节，应用新大纲，重新构建执行绑定，重新编译章节组件。
  - 返回 `answerType = REPORT_SEGMENT`，载荷只包含 `reportId`、`section`（Report DSL Section 片段）、`generateMeta`（章节生成证据）。
  - 该结果不自动更新 `ReportInstance`，不更新 `TemplateInstance`，不使已有文档产物失效；确认更新接口待后续设计。
  - 流式 `delta` 复用 `add_section` 动作，前端根据 `sectionId` 是否已存在区分"新增"与"替换"语义。
  - 数据查询基于新大纲重新执行，不复用已有查询结果。
- 影响范围：
  - `report_system/04-接口契约.md`
  - `report_system/03-运行时流程与状态机.md`

## 2026-05-15 接口契约补齐 PPT/paged 公开 I/O

- 变更动机：
  - 模板和 Report DSL 已支持 PPT/paged 结构后，接口契约还缺少模板摘要、模板实例、流式增量、报告详情和文档生成接口中的公开 I/O 约束。
- 设计决策：
  - `TemplateSummary` 必须返回 `structureType`；模板详情中 flow 使用 `catalogs -> sections`，paged 使用 `chapters -> slides -> sections`，两者互斥。
  - `reply.reportContext.templateInstance` 在 paged 场景下返回完整 `chapters -> slides -> sections` 实例态结构，确认参数、二次编辑和重新生成不得降级为 flow。
  - `REPORT.answer.report` 中 paged 最小合法结构为 `structureType = "paged" + basicInfo + content`，不得同时返回 `catalogs`；完成态 `/reports/{reportId}` 不新增 paged 专用包络。
  - 流式 `init_report.report` 必须携带 `structureType = flow | paged`，用于前端在收到后续增量前初始化正确的报告骨架。
  - 流式 `delta.action` 扩展为 `init_report | add_catalog | add_chapter | add_slide | add_section`；paged 仅新增 `add_chapter/add_slide`，`add_section` 与 flow 共用并通过定位字段区分。
  - 文档生成中 `ppt` 主要消费 paged Report DSL；`pdfSource` 支持 `word | ppt | null`，paged 报告导出 PDF 可使用 `pdfSource = "ppt"`。
- 影响范围：
  - `report_system/04-接口契约.md`

## 2026-05-14 Report DSL GenerateMeta 参数与大纲结构纠偏

- 变更动机：
  - 上一轮对齐 `GenerateMeta` 时将 `parameters` 和 `outline.items` 过度简化，导致 Report DSL 与模板/实例态核心参数、大纲模型分叉。
- 设计决策：
  - `GenerateMeta.additionalInfos` 保持 canonical 字段名，图表轴配置继续保持 `dataProperties.xAxis/yAxis`。
  - `GenerateMeta.parameters` 恢复为完整模板参数 `Parameter` 结构，不再使用简化参数结构，也不新增 `ParameterOption`。
  - `GenerateMeta.outline` 引用 `GenerateOutline`，其结构复用模板/实例态 `OutlineDefinition + RequirementItem`。
- 影响范围：
  - `report_system/schemas/report-dsl.schema.json`
  - `report_system/examples/report-dsl.example.json`
  - `report_system/报告DSL定义与使用说明书.md`
  - `report_system/02-核心业务模型与规范Schema.md`
  - `report_system/03-运行时流程与状态机.md`
  - `report_system/04-接口契约.md`

## 2026-05-14 Report DSL GenerateMeta 契约对齐

- 变更动机：
  - 对照 BI Engine TypeScript 权威模型后发现 `GenerateMeta` 相关 schema 混入了模板参数、旧 `additionalInfo/content` 和散字段证据，需要优先纠正。
- 设计决策：
  - `GenerateMeta` 公开字段收敛为 `status/question/additionalInfos/outline/parameters`，其中 `status`、`question` 必填。
  - `AdditionalInfo` 必须包含 `type/value`，可选 `name/appendix`；`additionalInfo` 与 `content` 不再作为公开 DSL 字段。
  - `SectionOutline/OutlineItem` 对齐 BI Engine：`outline.items[]` 使用 `id/sourceParameterId/value[]`。
  - `GenerateMeta.parameters` 使用 DSL 专用参数结构 `id/label/required/widget/options`，不复用模板参数结构。
  - 图表轴配置保持项目当前下沉口径：`dataProperties.xAxis/yAxis`。
- 影响范围：
  - `report_system/schemas/report-dsl.schema.json`
  - `report_system/examples/report-dsl.example.json`
  - `report_system/报告DSL定义与使用说明书.md`
  - `report_system/02-核心业务模型与规范Schema.md`
  - `report_system/03-运行时流程与状态机.md`
  - `report_system/04-接口契约.md`

## 2026-05-14 Report DSL 小幅增强与说明书

- 变更动机：
  - 手工更新后的 `report-dsl.schema.json` 增强了 PPT 封底、图表轴配置和行合并命名，需要同步正式设计文档和说明书。
- 设计决策：
  - 新增顶层 `backCover`，用于 paged/PPT 封底配置。
  - 行合并信息统一命名为 `MergeRowInfo`，不再保留额外 `MergeRowConfig` 定义。
  - 图表轴配置迁移到 `ChartDataProperty.xAxis/yAxis`，`ChartComponent` 顶层不再输出 `xAxis/yAxis`。
  - 新增 `报告DSL定义与使用说明书.md`，作为 Report DSL 的使用说明入口。
- 影响范围：
  - `report_system/schemas/report-dsl.schema.json`
  - `report_system/examples/report-dsl.example.json`
  - `report_system/examples/report-dsl-paged.example.json`
  - `report_system/报告DSL定义与使用说明书.md`
  - `report_system/02-核心业务模型与规范Schema.md`
  - `report_system/03-运行时流程与状态机.md`

## 2026-05-13 Report DSL 补齐 BI Engine 字段

- 变更动机：
  - 手工更新后的 `report-dsl.schema.json` 补齐了 BI Engine TypeScript 模型中已有但 schema 内缺失的字段，需要将该 schema 作为正式 DSL 契约合入。
- 设计决策：
  - `BasicInfo` 增加资产字段，例如 `schemaVersion/mode/subTitle/templateId/templateName/remark/createDate/modifyDate/creator/modifier/header/footer/category`。
  - `cover.layoutTemplate` 严格收敛为 `TITLE_TOP | TITLE_CENTER`，旧示例值 `default` 不再合法。
  - `GenerateMeta.additionalInfo` 条目扩展为至少包含 `type`，可携带 `name/value/content/appendix`，实现层兼容读取 `additionalInfos`。
  - 表格列、合并列、图表 series、响应式 chart option、组件 basic/advance properties 按最新 schema 表达。
- 影响范围：
  - `report_system/schemas/report-dsl.schema.json`
  - `report_system/examples/report-dsl.example.json`
  - `report_system/examples/report-dsl-paged.example.json`
  - `report_system/02-核心业务模型与规范Schema.md`
  - `report_system/03-运行时流程与状态机.md`

## 2026-05-12 对齐外部 Dynamic Node v6 模板契约

- 变更动机：
  - 外部动态节点 v6 明确了 flow 与 paged 场景下 custom 节点的适用位置、请求体和响应体，需要避免模板侧继续沿用旧 `nodeType/nodeId/prompt` 口径。
- 设计决策：
  - `dynamic.custom` 模板字段保持 `{type, url}`，不新增 `method/config/dslType`。
  - flow `CatalogDefinition.dynamic.custom` 返回 DSL `Catalog`；flow `SectionDefinition.dynamic.custom` 返回 DSL `Section`。
  - paged `SlideDefinition.dynamic.custom` 返回 DSL `Slide`；paged slide 内 `SectionDefinition.dynamic.custom` 返回 `Components`，也允许返回可转换的 `Section`。
  - `ChapterDefinition.dynamic` 不再允许 `custom`，仅保留 `foreach/foreachCase`。
  - 正式外部调用协议采用 v6 `parameters/templateNode/context` 请求体与 `status/dsl/meta.dslType` 响应体。
- 影响范围：
  - `report_system/schemas/report-template.schema.json`
  - `report_system/schemas/template-instance.schema.json`
  - `report_system/examples/report-template-paged.example.json`
  - `report_system/02-核心业务模型与规范Schema.md`
  - `report_system/03-运行时流程与状态机.md`
  - `report_system/04-接口契约.md`
  - `report_system/报告模板定义与使用说明书.md`

## 2026-05-12 Report DSL PPT 扩展不改变 flow 契约

- 变更动机：
  - PPT/paged 是新增报告结构，上一版从输入 schema 直接同步时误改了 flow 的 `Catalog/Cover/Section/ReportSummary` 既有契约。
- 设计决策：
  - 保留 `Report.structureType` 与 paged `content` 能力。
  - flow 分支继续使用 PPT 扩展前的 `Catalog.name`、`Section.summary`、旧 `Cover/CoverContent`、旧 `SignaturePage/Signer`、旧 `ReportSummary`。
  - paged 分支只通过 `content -> Slide[] | SlideSection[]` 表达 PPT 主体，不反向改变 `catalogs` 分支。
- 影响范围：
  - `report_system/schemas/report-dsl.schema.json`
  - `report_system/examples/report-dsl.example.json`
  - `report_system/examples/report-dsl-paged.example.json`
  - `report_system/02-核心业务模型与规范Schema.md`
  - `report_system/03-运行时流程与状态机.md`

## 2026-05-12 Report DSL 支持 single-root flow/paged 结构

- 变更动机：
  - 报告模板已支持 PPT 分页结构，最终 Report DSL 也需要表达分页/PPT 报告，而不是只支持瀑布流 `catalogs`。
  - DSL 顶层公共信息应复用同一 `Report` 根对象，避免为 flow 与 paged 维护两套相似 schema。
- 设计决策：
  - `Report.structureType` 新增 `flow/paged`，缺省为 `flow`。
  - `flow` 使用 `catalogs + layout`，禁止 `content`。
  - `paged` 使用 `content`，禁止 `catalogs`；`content` 只能整体为 `Slide[]` 或整体为 `SlideSection[]`。
  - flow 的 `Catalog/Section` 契约保持不变；paged 通过新增 `content` 表达页面结构。
  - `GenerateMeta.additionalInfo` 使用新版单数字段名，每项为 `{type, content}`。
  - `cover/signaturePage/summary` 保持旧 flow 契约。
- 影响范围：
  - `report_system/schemas/report-dsl.schema.json`
  - `report_system/examples/report-dsl.example.json`
  - `report_system/examples/report-dsl-paged.example.json`
  - `report_system/02-核心业务模型与规范Schema.md`
  - `report_system/03-运行时流程与状态机.md`
  - `report_system/04-接口契约.md`

## 2026-05-12 报告模板支持 PPT 分页结构

- 变更动机：
  - 现有模板只表达瀑布流目录结构，无法直接承载 PPT 等分页报告的 chapter/slide 页面结构。
- 设计决策：
  - `ReportTemplate.structureType` 新增 `flow/paged`，缺省为 `flow`。
  - `flow` 使用既有 `catalogs -> (subCatalogs)* -> sections`。
  - `paged` 使用新增 `chapters -> slides -> sections`，其中 `sections` 复用现有 `SectionDefinition`。
  - `ChapterDefinition` 支持 `id/title/description/implicit/parameters/dynamic/slides`。
  - `SlideDefinition` 支持 `id/title/subtitle/description/parameters/dynamic/layout/sections`。
  - `SlideLayout` 仅作为设计器和后续 PPT 渲染适配提示，本轮不承诺运行时渲染语义。
- 影响范围：
  - `report_system/schemas/report-template.schema.json`
  - `report_system/schemas/template-instance.schema.json`
  - `report_system/examples/report-template.example.json`
  - `report_system/examples/report-template-paged.example.json`
  - `report_system/02-核心业务模型与规范Schema.md`
  - `report_system/03-运行时流程与状态机.md`
  - `report_system/04-接口契约.md`
  - `report_system/报告模板定义与使用说明书.md`

## 2026-05-12 表格 mergeRows 行合并定义

- 变更动机：
  - 模板表格已支持列合并，还需要声明基于连续相同值的行合并展示规则。
- 设计决策：
  - 普通表格 `PresentationProperty.mergeRows[]` 和复合表 `CompositeTablePartLayout.mergeRows[]` 使用统一 `MergeRowDefinition`。
  - `MergeRowDefinition.column` 引用 `TableComponent.dataProperties.columns[].key`，并读取 `TableComponent.dataProperties.data[]` 中同名字段。
  - `mode` 当前仅支持 `default`，缺省为 `default`；默认逻辑是连续多行相同值合并为一个单元格。
  - Report DSL 的 `MergeRowConfig` 使用 `column` 字段，不再使用 `columnKey`；`startRowIndex` 从 0 起算。
- 影响范围：
  - `report_system/schemas/report-template.schema.json`
  - `report_system/schemas/report-dsl.schema.json`
  - `report_system/examples/report-template.example.json`
  - `report_system/examples/report-dsl.example.json`

## 2026-05-09 Dynamic Custom 外部内容生成

- 变更动机：
  - `dynamic.custom` 不能只作为占位配置，需要支持由外部服务生成目录或章节内容。
  - 章节级 custom 仍需要保留 outline，便于用户在生成前编辑大纲诉求。
- 设计决策：
  - `dynamic.type = custom` 使用显式 `{ "type": "custom", "url": "..." }`，删除原占位 `config`。
  - 目录级 custom 运行时向 `url` 发起 POST 请求，请求 `prompt` 使用目录实例的 `renderedTitle`，响应为完整 Report DSL `Catalog`。
  - 章节级 custom 要求模板中有 `outline`，请求 `prompt` 使用用户可编辑后的 `outline.renderedRequirement`，响应为完整 Report DSL `Section`。
  - 请求参数使用当前节点可见参数，按 `parameterId` 分组，值保持 `ParameterValue` 结构。
- 影响范围：
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - [report_system/报告模板定义与使用说明书.md](report_system/%E6%8A%A5%E5%91%8A%E6%A8%A1%E6%9D%BF%E5%AE%9A%E4%B9%89%E4%B8%8E%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E%E4%B9%A6.md)
  - `report_system/schemas/report-template.schema.json`
  - `report_system/schemas/template-instance.schema.json`
  - `report_system/examples/report-template.example.json`
  - `report_system/examples/template-instance.example.json`

## 2026-05-09 Dynamic/ForeachCase 模板展开结构

- 变更动机：
  - 旧 `foreach` 只能表达“同一内容重复展开”，无法表达“仍按参数多值循环，但不同取值需要不同章节/目录定义”的场景。
  - 该能力本质不是单选 `switch`，而是一种特殊 foreach，因此命名为 `foreachCase`。
- 设计决策：
  - `CatalogDefinition` 与 `SectionDefinition` 的动态展开统一使用 `dynamic` 字段。
  - `dynamic.type` 支持 `foreach`、`foreachCase`、`custom`；`custom` 仅预留。
  - `foreachCase` 使用 `ParameterValue.value` 匹配 `cases[].values`；多选参数逐值展开，未命中时使用 `defaultCase`，无默认分支则跳过该值。
  - 正式 schema 不再接受旧 `foreach` 字段；实现层可兼容读取旧字段并输出 canonical `dynamic`。
  - 模板实例使用 `dynamicContext` 记录展开来源，旧 `foreachContext` 不再作为新实例输出字段。
- 影响范围：
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - [report_system/报告模板定义与使用说明书.md](report_system/%E6%8A%A5%E5%91%8A%E6%A8%A1%E6%9D%BF%E5%AE%9A%E4%B9%89%E4%B8%8E%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E%E4%B9%A6.md)
  - `report_system/schemas/report-template.schema.json`
  - `report_system/schemas/template-instance.schema.json`
  - `report_system/examples/report-template.example.json`
  - `report_system/examples/template-instance.example.json`

## 2026-05-08 参数优先级、移除 Tags 与 Text 属性归并

- 变更动机：
  - 对话生成报告需要按参数重要性分批追问，低优先级参数应推迟到最终确认。
  - 报告模板顶层 `tags` 不再作为当前模板契约字段。
  - `text` block 的文本模板和实例化内容应统一放入 `properties`，避免 block 根部继续膨胀类型专属字段。
- 设计决策：
  - `Parameter.priority` 新增为可选整数，范围 `0-99`，缺省按 `99` 处理；数字越小优先级越高。
  - 缺失必填参数按 `priority` 从小到大追问，同优先级一批追问；`priority = 99` 不单独追问，只在最终确认所有参数时展示并补齐。
  - `priority` 不改变 `required` 语义，最终确认通过前所有必填参数仍必须有值。
  - `ReportTemplate.tags` 从正式 schema 中移除。
  - `PresentationBlock` 与 `TemplateInstancePresentationBlock` 不直接承载 `template/content`；text 使用 `properties.template`，实例态 text 额外使用 `properties.content`。
- 影响范围：
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - [report_system/报告模板定义与使用说明书.md](report_system/%E6%8A%A5%E5%91%8A%E6%A8%A1%E6%9D%BF%E5%AE%9A%E4%B9%89%E4%B8%8E%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E%E4%B9%A6.md)
  - `report_system/schemas/report-template.schema.json`
  - `report_system/schemas/template-instance.schema.json`
  - `report_system/examples/report-template.example.json`
  - `report_system/examples/template-instance.example.json`

## 2026-05-08 Presentation 属性扩展

- 变更动机：
  - 模板 presentation 需要在定义层表达 chart 的首选图表类型。
  - 普通表格和复合表子表需要统一表达列展示、标题显示和默认展示条数。
- 设计决策：
  - `PresentationProperty.preferredType` 仅对 `type = chart` 生效，枚举为 `line/bar/pie/scatter/radar/gauge/candlestick`。
  - 普通 `type = table` 通过 `properties.columns/showTitle/defaultDisplayRows/mergeColumns` 承载表格展示属性。
  - `CompositeTablePartLayout` 同步支持 `columns/showTitle/defaultDisplayRows/mergeColumns`。
  - 新增统一 `TableColumn` 定义；`key/title` 是正式字段，`width/align` 兼容保留但 v1 暂不承诺渲染支持。
  - `showTitle` 只控制标题展示，不改变 `title` 字段；`defaultDisplayRows` 只表示默认展示条数，不截断 dataset 结果。
- 影响范围：
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - [report_system/报告模板定义与使用说明书.md](report_system/%E6%8A%A5%E5%91%8A%E6%A8%A1%E6%9D%BF%E5%AE%9A%E4%B9%89%E4%B8%8E%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E%E4%B9%A6.md)
  - `report_system/schemas/report-template.schema.json`
  - `report_system/schemas/template-instance.schema.json`
  - `report_system/examples/report-template.example.json`
  - `report_system/examples/template-instance.example.json`

## 2026-05-08 Text 模板支持 Dataset 字段引用

- 变更动机：
  - `text.template` 只表达参数引用时，无法把已执行 dataset 的关键指标直接写入文本结论。
  - 文本结论需要同时引用多个 dataset 的执行结果字段，但本轮不进入实现代码调整。
- 设计决策：
  - `text.template` 继续作为唯一承载字段，不新增 `datasetIds`。
  - 新增 dataset 字段引用语法 `{#datasetId.field}`，其中 `datasetId` 指向同一 section 的 `content.datasets[].id`，`field` 使用源数据字段 key。
  - 被引用 dataset 当前按单行结果理解；如果返回多行，默认取第一行对应字段值。
  - JSON Schema 只更新字段说明和示例，不强制校验 dataset 或字段是否存在。
- 影响范围：
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - [report_system/报告模板定义与使用说明书.md](report_system/%E6%8A%A5%E5%91%8A%E6%A8%A1%E6%9D%BF%E5%AE%9A%E4%B9%89%E4%B8%8E%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E%E4%B9%A6.md)
  - `report_system/schemas/report-template.schema.json`
  - `report_system/schemas/template-instance.schema.json`
  - `report_system/examples/report-template.example.json`
  - `report_system/examples/template-instance.example.json`

## 2026-05-08 Presentation Block 类型收敛

- 变更动机：
  - 旧模板 presentation 同时暴露 `paragraph/bullet/kpi/markdown` 等类型，和当前希望优先支持的文本、图表、表格能力不一致。
  - 文本块需要从模板态模板文本和实例态渲染内容两个阶段明确建模。
- 设计决策：
  - 模板/实例态 `presentation.blocks[].type` 收敛为 `text`、`chart`、`table`，并兼容保留既有 `composite_table`。
  - `text` block 模板态必须保存 `template`，实例态必须保存 `template` 与渲染后的 `content`。
  - `paragraph/bullet/kpi/markdown` 不再作为模板/实例态 presentation block 类型支持；Report DSL 内部系统生成的 `markdown` 组件不受影响。
- 影响范围：
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - `report_system/schemas/report-template.schema.json`
  - `report_system/schemas/template-instance.schema.json`

## 2026-04-25 删除后路径引用收口

- 变更动机：
  - `docs/` 目录以及 `design/archive/`、`design/chatbi/`、`design/openapi/`、`design/spec.md`、`design/story.md`、`design/deployment_guide.md`、`design/report_sample.md` 已从当前工作树删除。
  - 剩余入口文档不能继续链接或推荐这些已删除材料。
- 设计决策：
  - `README.md` 的仓库结构和文档导航移除 `docs/` 与已删除设计辅助文档。
  - `design/README.md` 只保留 `report_system/`、`report_system/implementation/`、`change_log.md` 和 `biz_requirement.md` 四类入口。
  - `design/report_system/README.md` 的治理规则移除已删除的 `chatbi/openapi/archive` 目录引用，改为说明历史材料已退出主阅读路径。
  - `design/change_log.md` 中历史影响范围里指向已删除文件的 Markdown 链接改为纯文本历史路径，避免形成失效链接。
- 影响范围：
  - [README.md](../README.md)
  - [README.md](README.md)
  - [report_system/README.md](report_system/README.md)
- 风险与后续：
  - `design/biz_requirement.md` 是设计团队原始输入来源，仍保留历史路径文字，不按当前目录结构改写。

## 2026-04-25 非权威文档口径清理

- 变更动机：
  - `design/report_system/` 已明确成为当前方案设计权威来源，但根层摘要、测试文档和历史材料入口仍存在旧路径、旧字段或旧目录名，容易被误读为当前口径。
  - `biz_requirement.md` 需要继续作为设计团队原始输入来源保留，不能按当前实现口径改写。
- 设计决策：
  - 刷新 `design/spec.md` 与 `design/story.md`，只保留当前报告主系统摘要和业务叙事。
  - 更新 `design/README.md`，明确 `biz_requirement.md` 是原始输入来源，历史计划和演示材料只用于追溯。
  - 修正部署说明中的仓库名、路径和 Python 版本要求。
  - 刷新 `docs/testing/functional-use-cases.md`，移除旧 `design/design_*`、旧模板字段、旧实例资源和旧 `generated_content` 口径。
  - 为 `docs/`、`docs/plans/`、`docs/presentations/` 增加入口说明，声明日期型计划和演示资料是历史快照，不作为当前设计依据。
- 影响范围：
  - [README.md](../README.md)
  - [README.md](README.md)
  - `design/spec.md`、`design/story.md`、`design/deployment_guide.md`（后续已删除）
  - `docs/` 下测试、计划和演示材料（后续已删除）
- 风险与后续：
  - 归档目录、历史计划和历史测试报告中的原文仍可能包含旧词汇；这些文档已通过入口说明降级为追溯材料，不再作为当前方案依据。

## 2026-04-22 模板 `dataset.source` 内联数据源

- 变更动机：
  - 现有模板里 `dataset.sourceType = sql` 只通过 `sourceRef` 引用外部 SQL 定义，模板本身不保存 SQL 原文，导致模板导入导出和独立审阅时无法直接看到真实数据源定义。
  - `sql` 与 `api` 两类数据源都需要一个简单、统一、强约束的入口字段，不适合再拆成复杂对象结构。
- 设计决策：
  - `DatasetDefinition` 正式取消 `sourceRef`，统一改为 `source`。
  - `source` 始终是字符串：
    - `sourceType = sql` 时，`source` 保存 SQL 模板
    - `sourceType = api` 时，`source` 保存 API URL
  - SQL 返回字段、API 请求参数、API 响应体都视为外部已约定内容，不在模板中显式配置。
  - SQL 模板占位符语法本轮不做正式标准化；示例中的写法只用于表达“运行时会结合参数实例化”。
- 影响范围：
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/schemas/report-template.schema.json](report_system/schemas/report-template.schema.json)
  - [report_system/examples/report-template.example.json](report_system/examples/report-template.example.json)
- 风险与后续：
  - 如果后续需要规范 SQL 模板占位符语法，应单独追加一轮运行时模板实例化规则设计，而不是在本轮继续扩张 `DatasetDefinition`。

## 2026-04-19 旧 `design/implementation/` 目录归档

- 变更动机：
  - 当前正式实现设计已经完全收敛到 `design/report_system/implementation/`，而 `design/implementation/` 仍作为旧入口残留在根阅读路径里，造成两套实现目录并存的误解。
  - 继续保留该目录在正式入口中，会削弱主设计包“唯一权威设计源”的治理边界。
- 设计决策：
  - 将 `design/implementation/` 整体归档到 `design/archive/legacy-implementation/`。
  - `design/README.md` 的正式实现入口统一切换为 `design/report_system/implementation/README.md`。
  - 历史文档中仍需追溯旧实现映射时，统一从归档目录读取，不再把旧目录作为当前实现设计来源。
- 影响范围：
  - [README.md](README.md)
  - [report_system/README.md](report_system/README.md)
  - [biz_requirement.md](biz_requirement.md)
  - `design/archive/` 下历史归档材料（后续已删除）
- 风险与后续：
  - 若仓库外仍有旧链接直接指向 `design/implementation/*`，需要后续按需补充跳转说明或继续清理引用。
  - 后续新增实现设计只允许进入 `design/report_system/implementation/`，不得在根目录再恢复并行实现目录。

## 2026-04-19 scoped 参数补强

- 关联提交：
  - GitHub PR `#15`
  - merge commit `e8e9371`
- 变更动机：
  - 在上一轮模板/模板实例重构后，核心模型已经允许参数定义出现在模板根、目录、章节多个层级。
  - 但最近一次代码级 review 发现，运行时链路和 UI 交互仍然偏向“只处理根参数”，这会导致 scoped 参数设计虽然存在于 schema 中，却不能稳定参与补参、确认、重新生成。
- 设计决策：
  - 参数作用域正式定义为“根参数 + 目录参数 + 章节参数”统一构成一套可见参数集合。
  - 对话运行时在参数抽取、缺参判断、参数确认、模板实例重建时，都必须基于整棵模板树递归收集参数定义，而不能只读取模板根 `parameters`。
  - 模板实例在用户补参后，最新参数状态必须同时反映到：
    - 顶层 `templateInstance.parameters`
    - 目录级 `catalog.parameters`
    - 章节级 `section.parameters`
  - `multi=true` 的参数不再视为“模型保留但交互降级”，而是正式要求前端支持多值输入/选择。
- 影响范围：
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
- 风险与后续：
  - 运行时真实环境仍依赖 sqlite 本地表结构与当前 ORM 模型一致；若开发环境使用了旧库文件，仍可能出现“设计已更新、运行时报表缺列”的环境性故障。
  - 后续所有设计方案调整，统一继续追加到本文件，不再分散写入其它说明页。

## 2026-04-19 表定义与运行时数据库分离

- 变更动机：
  - `src/backend/report_system.db` 此前被纳入 Git 跟踪，但它本质上是本地运行时自动生成的 SQLite 文件。
  - 当前仓库中的 `report_system.db` 已明显落后于正式 ORM 模型与设计文档，继续把它当作表定义载体，会导致“ORM、设计、实际库文件”三套结构长期漂移。
- 设计决策：
  - 运行时唯一建表来源继续保持为 `src/backend/infrastructure/persistence/models.py` + `Base.metadata.create_all(...)`。
  - 新增受版本管理的 SQL 初始化稿 `src/backend/infrastructure/persistence/schema_init.sql`，用于初始化、审阅与结构比对。
  - `src/backend/report_system.db` 明确降级为本地运行时文件，不再纳入版本跟踪。
  - SQL 初始化稿必须按当前 ORM 目标模型维护，不能再从历史 `report_system.db` 倒推。
- 影响范围：
  - [report_system/05-数据模型与持久化.md](report_system/05-%E6%95%B0%E6%8D%AE%E6%A8%A1%E5%9E%8B%E4%B8%8E%E6%8C%81%E4%B9%85%E5%8C%96.md)
  - `design/archive/legacy-implementation/database_schema.md`（后续已删除）
  - `design/deployment_guide.md`（后续已删除）
  - `src/backend/infrastructure/persistence/schema_init.sql`
- 风险与后续：
  - 当前仍未引入迁移框架，SQL 初始化稿与 ORM 的一致性需要在后续开发中显式维护。
  - 若其它设计文档仍引用已废弃的旧表或旧 `.db` 基线，需要继续按当前目标模型清理。

## 2026-04-19 `/chat` 流式报告增量 `delta`

- 变更动机：
  - 现有 `/chat` 流式协议只有 `steps` 和最终 `answer`，缺少一条专门表达报告内容增量变更的正式通道。
  - 前端若要边生成边渲染目录和章节，只依赖完整 `REPORT` 会造成载荷过重，且执行进度与内容 patch 语义混杂。
- 设计决策：
  - 在 `ChatStreamEvent` 顶层新增可选字段 `delta`，只用于流式报告内容 patch。
  - `steps` 继续只表达执行进度；`answer` 继续只表达最终完整结果。
  - 不新增 SSE 事件类型；`delta` 仍附着在现有统一事件包络上，生成过程通过顶层 `status=running` 判断。
  - `delta.action` 当前先收敛为：`init_report`、`add_catalog`、`add_section`。
  - `delta` 不进入非流式 `ChatResponse` 完成态，也不进入 `GET /reports/{reportId}`。
- 影响范围：
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/08-相对ChatBI的扩展点.md](report_system/08-%E7%9B%B8%E5%AF%B9ChatBI%E7%9A%84%E6%89%A9%E5%B1%95%E7%82%B9.md)
  - `design/chatbi/*` 与 `design/openapi/*`（后续已删除）
- 风险与后续：
  - `delta` 当前只覆盖目录和章节新增；若后续需要章节替换、组件更新、目录删除等动作，需要继续扩充动作枚举。
  - 前端必须明确区分 `steps`、`delta`、`answer` 三条通道，避免再次混淆。

## 2026-04-19 `ask.status` 对话级锁定标识

- 变更动机：
  - 参数确认后的“本轮不可继续修改”属于多轮对话里的消息级语义，不应继续下沉到参数对象自身。
  - 未来不止参数确认，其它类型的追问消息也需要统一表达“已回复、不可继续修改”。
- 设计决策：
  - 在 `Ask` 上新增正式字段 `status`，当前只支持 `pending | replied`。
  - `pending` 表示该追问仍可编辑、可提交；`replied` 表示该追问已经被后续回复消费。
  - `ask.status` 同时进入当前轮 `ChatResponse.ask` 与对话历史消息回显。
  - 保持 `TemplateInstance.parameterConfirmation.confirmed` 原有业务语义，不把参数确认态改造成消息级锁定态。
- 影响范围：
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - [report_system/08-相对ChatBI的扩展点.md](report_system/08-%E7%9B%B8%E5%AF%B9ChatBI%E7%9A%84%E6%89%A9%E5%B1%95%E7%82%B9.md)
  - [report_system/implementation/统一对话实现.md](report_system/implementation/%E7%BB%9F%E4%B8%80%E5%AF%B9%E8%AF%9D%E5%AE%9E%E7%8E%B0.md)
  - [report_system/implementation/前端实现.md](report_system/implementation/%E5%89%8D%E7%AB%AF%E5%AE%9E%E7%8E%B0.md)
  - `design/chatbi/*` 与 `design/openapi/*`（后续已删除）
- 风险与后续：
  - 当前只定义了 `pending | replied`，若后续出现“过期”“被替换”等场景，需要扩展状态枚举。
  - 历史消息回显若仍使用极简消息模型，需要继续把 `ask` 结构纳入正式消息对象。

## 2026-04-19 `reply.sourceChatId` 原始追问定位

- 变更动机：
  - 仅靠 `ask.status` 还不足以让服务端稳定回写“哪一条追问消息已被消费”。
  - 若继续依赖“最近一条待回复 ask”做隐式匹配，在多轮并发交互或历史回放场景下会产生歧义。
- 设计决策：
  - 在结构化 `reply` 上新增 `sourceChatId`，指向被回复的原始 assistant 追问消息。
  - 服务端必须基于 `sourceChatId` 回写对应消息的 `ask.status = replied`。
  - `sourceChatId` 对 `fill_params`、`confirm_params` 都是必填字段，不再允许隐式猜测。
- 影响范围：
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - [report_system/08-相对ChatBI的扩展点.md](report_system/08-%E7%9B%B8%E5%AF%B9ChatBI%E7%9A%84%E6%89%A9%E5%B1%95%E7%82%B9.md)
  - [report_system/implementation/统一对话实现.md](report_system/implementation/%E7%BB%9F%E4%B8%80%E5%AF%B9%E8%AF%9D%E5%AE%9E%E7%8E%B0.md)
  - [report_system/implementation/前端实现.md](report_system/implementation/%E5%89%8D%E7%AB%AF%E5%AE%9E%E7%8E%B0.md)
  - `design/chatbi/*` 与 `design/openapi/*`（后续已删除）
- 风险与后续：
  - 若未来允许一条 `reply` 同时消费多条历史追问，需要把单值 `sourceChatId` 扩展为数组或更通用的 source 引用模型。

## 2026-04-20 `ParameterValue.label` 与 `Reply.parameters` 精简回填

- 变更动机：
  - 原三元组字段名 `display` 与参数定义中的 `label` 并列存在，语义重复且容易引起实现歧义。
  - `Reply.parameters` 继续回传完整参数定义，会让前端重复提交静态结构，放大请求体，并模糊 `ask/templateInstance/reply` 三者的职责边界。
- 设计决策：
  - 正式将 `ParameterValue` 从 `{display, value, query}` 改为 `{label, value, query}`。
  - 模板、模板实例、外部候选值接口、诉求实例化继续复用完整 `ParameterValue` 三元组。
  - `Reply.parameters` 保留字段名，但语义收敛为参数值映射：`Record<parameterId, Scalar[]>`。
  - `fill_params` 允许只提交本轮修改子集；`confirm_params` 必须提交完整已生效值集。
- 影响范围：
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - `design/report_system/schemas/*.json`
  - `design/chatbi/*` 与 `design/openapi/*`（后续已删除）
- 风险与后续：
  - 运行时如果仍按旧 `display` 字段取值，实现阶段必须同步切到 `label`。
  - `Reply.parameters` 既然已经与 `Ask.parameters` 脱钩，后续实现中不得再把两者视为同构 DTO。

## 2026-04-20 `CompositeTable` 模板正式支持

- 变更动机：
  - `Report DSL` 早已支持 `CompositeTable`，但模板定义与编译规则长期只覆盖 `paragraph/table/chart/markdown`，导致 DSL 侧有能力、模板侧没有正式入口。
  - 当前业务已明确需要“设备档案式复合表”，其中基础信息、多个检查结果区块和总结区块都属于同一个复合表组件。
- 设计决策：
  - 在模板 `section.content.presentation.blocks[]` 中正式新增 `type = composite_table`。
  - `composite_table` 采用通用 `parts[]` 结构，不引入业务语义化的固定区块名。
  - `part` 只支持两类来源：
    - `query`：由 `datasetId` 生成普通子表
    - `summary`：模板定义固定总结行，模型只填每行内容，并生成无表头二维表
  - 基础信息也按 `query part` 处理，不再引入第三类 part。
  - 不允许在 `part` 内再嵌套 group；若业务上存在多个分区，直接拆成多个顺序 `part`。
- 影响范围：
  - [report_system/schemas/report-template.schema.json](report_system/schemas/report-template.schema.json)
  - [report_system/examples/report-template.example.json](report_system/examples/report-template.example.json)
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
- 风险与后续：
  - 当前仅完成设计层收敛，后续实现阶段需要同步补齐模板编译器，把 `composite_table` block 真正编译为 DSL `CompositeTable.tables[]`。
  - `summary part` 目前固定为无表头两列表，若后续要支持更复杂的总结表骨架，需要再扩展 `summarySpec`。

## 2026-04-20 接口字段命名统一为 lowerCamelCase

- 变更动机：
  - 公开接口中的字段命名必须保持单一规范，避免固定字段、动态参数键和示例载荷混用蛇形与小驼峰。
- 设计决策：
  - 所有公开接口 JSON 中的固定字段名统一使用 lowerCamelCase。
  - `reply.parameters`、动态参数源请求体这类 map 结构中的参数键，进入公开接口时也必须使用 lowerCamelCase 参数 id。
  - 错误码、枚举值、模板内部引用 id 不因本次调整而改名。
- 影响范围：
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/schemas/parameter-option-source-request.schema.json](report_system/schemas/parameter-option-source-request.schema.json)
  - `design/openapi/*`（后续已删除）
- 风险与后续：
  - 若后续把参数 id 直接暴露到更多公开接口对象中，应继续沿用 lowerCamelCase 口径。

## 2026-04-20 `TemplateInstance` 正式承载 `CompositeTable` 实例态

- 变更动机：
  - 仅调整模板 schema 不足以支撑复杂二次编辑；`TemplateInstance` 若不显式保存 `composite_table.parts[]` 的实例态，前端无法稳定读取复合表内部结构，重新生成也只能回退到模板快照现算。
  - `TemplateInstance` 本身就是“生成前”和“再生成前”的正式上下文，章节内容结构不能只留在模板快照里。
- 设计决策：
  - 在 `TemplateInstance.section` 上正式补 `content` 字段，并保持与模板 `section.content` 同构。
  - `TemplateInstance.section.content.presentation.blocks[]` 正式支持 `type = composite_table`。
  - `composite_table.parts[]` 在实例态保留与模板相同的顺序和结构；每个 `part` 新增 `runtimeContext`。
  - `query part` 通过 `runtimeContext.status/resolvedDatasetId/resolvedQuery/warnings` 记录最小运行态。
  - `summary part` 通过 `runtimeContext.status/resolvedPartIds/prompt/warnings` 记录最小运行态。
  - `section.runtimeContext` 继续只保留章节级执行上下文，不承载复合表结构本身。
- 影响范围：
  - [report_system/schemas/template-instance.schema.json](report_system/schemas/template-instance.schema.json)
  - [report_system/examples/template-instance.example.json](report_system/examples/template-instance.example.json)
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - `design/chatbi/*`（后续已删除）
- 风险与后续：
  - 当前只补到 `part` 级运行态，不继续缓存子表单元格结果或最终生成内容。
  - 实现阶段需要保证参数或诉求变化时，只重算受影响 `part.runtimeContext`，而不是破坏整个 `composite_table` 结构。

## 2026-04-21 Report DSL 增强参数与大纲回显

- 变更动机：
  - 生成后的报告需要在前台支持结构化编辑，单靠 `TemplateInstance` 回显不足以支撑“直接基于报告编辑”的场景。
  - 现有 DSL 中 `basicInfo` 和 `GenerateMeta` 只保留了最小元信息，无法直接回显全局参数、章节参数和章节大纲骨架。
- 设计决策：
  - 在 `basicInfo` 中新增 `parameters`，按 `Record<parameterId, Parameter>` 保存全局参数完整定义与当前取值。
  - 在 `GenerateMeta` 中新增 `parameters`，只保存章节本地参数。
  - 在 `GenerateMeta` 中新增 `outline`，包含 `requirement`、`renderedRequirement`、`items`。
  - `OutlineItem` 正式定义为：`id`、`sourceParameterId`、`value`；其中 `value` 是参数三元组中的 `value` 数组。
  - `GenerateMeta.question` 与 `outline.renderedRequirement` 同时保留且独立存在，前端和编译逻辑不得假定二者相等。
- 影响范围：
  - [report_system/schemas/report-dsl.schema.json](report_system/schemas/report-dsl.schema.json)
  - [report_system/examples/report-dsl.example.json](report_system/examples/report-dsl.example.json)
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
- 风险与后续：
  - 该调整会扩大 DSL 体积，实现阶段需要避免把 `TemplateInstance` 原样透传进 `Report DSL`。
  - 若后续需要把父 catalog 参数也显式回显到章节级，需要再单独扩展 `GenerateMeta.parameters` 的范围定义。

## 2026-04-27 表格 Presentation 支持合并列定义

- 变更动机：
  - 现有表格 presentation 只能声明源列，无法表达“把多个源列合并为一个展示列”的版式意图。
  - DSL 层已有 `dataProperties.mergeColumns`，模板和实例态需要补齐同名定义并进入运行时编译链路。
- 设计决策：
  - 普通 `presentation.blocks[].type = table` 新增 `properties`，并要求使用 `datasetId` 指向数据集。
  - `PresentationProperty` 当前仅定义 `mergeColumns[]`，且仅对普通 `table` block 生效。
  - `CompositeTablePartLayout` 新增 `mergeColumns[]`，用于 `composite_table` query part 的子表布局。
  - `mergeColumns[]` 固定为 `{title, columns}`；`columns` 使用源数据列 key，至少两个且不重复。
  - `mergeColumns` 只表达展示结构，不修改数据行，也不改变 `columns[]` 中源列的含义。
- 影响范围：
  - [report_system/schemas/report-template.schema.json](report_system/schemas/report-template.schema.json)
  - [report_system/schemas/template-instance.schema.json](report_system/schemas/template-instance.schema.json)
  - [report_system/schemas/report-dsl.schema.json](report_system/schemas/report-dsl.schema.json)
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
- 风险与后续：
  - v1 不做跨字段校验，即不强制 `mergeColumns.columns[]` 必须出现在源数据集或 `tableLayout.columns[]` 中；该约束先由设计文档和模板评审保证。
