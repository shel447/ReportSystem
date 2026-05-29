# 02. 核心业务模型与规范 Schema

## 1. 使用规则

本篇不再只写概要结构，而是明确给出开发可直接使用的正式 JSON Schema 和参考示例。

正式 Schema 文件：

- [schemas/report-template.schema.json](schemas/report-template.schema.json)
- [schemas/template-instance.schema.json](schemas/template-instance.schema.json)
- [schemas/report-dsl.schema.json](schemas/report-dsl.schema.json)
- [schemas/parameter-option-source-request.schema.json](schemas/parameter-option-source-request.schema.json)
- [schemas/parameter-option-source-response.schema.json](schemas/parameter-option-source-response.schema.json)

参考示例文件：

- [examples/report-template.example.json](examples/report-template.example.json)
- [examples/template-instance.example.json](examples/template-instance.example.json)
- [examples/report-dsl.example.json](examples/report-dsl.example.json)
- [examples/report-dsl-paged.example.json](examples/report-dsl-paged.example.json)

原则：

1. Schema 是正式约束，示例只是参考。
2. 开发、测试、导入导出、文档生成都必须围绕这些 Schema 工作。
3. 代码实现如需引用 Schema，统一直接引用本目录下的正式文件，不再在 `src/backend` 维护镜像副本。
4. `Report DSL` 必须严格遵循 [schemas/report-dsl.schema.json](schemas/report-dsl.schema.json)。
5. Report DSL 使用说明见 [报告DSL定义与使用说明书.md](报告DSL定义与使用说明书.md)。

## 2. ReportTemplate

正式对象：`ReportTemplate`

关键要求：

- `parameters` 是模板对象根属性，不再放进 `content`
- `structureType` 声明模板结构类型，缺省为 `flow`
- `structureType = flow` 使用 `catalogs -> (subCatalogs)* -> sections`
- `structureType = paged` 使用 `chapters -> slides -> sections`，用于 PPT 等分页报告结构
- 模板是静态资产，不带运行态 `status`
- 参数动态候选项来源统一用 `source` 描述，类型是 URL 字符串；不再把方法、请求体、响应体格式散落在模板中
- 所有参数都必须显式声明 `multi`；候选值来源由是否存在 `source` 决定
- flow 模板支持多层目录：每个 `catalog` 下可以同时存在 `subCatalogs` 与 `sections`
- paged 模板的 `ChapterDefinition` 支持 `parameters/dynamic`，但 `dynamic` 仅允许 `foreach/foreachCase`；`SlideDefinition` 支持 `parameters/dynamic/layout`，其中 `dynamic.custom` 返回 Report DSL `Slide`，`sections` 继续复用现有 `SectionDefinition`
- 目录、章节和分页页面的动态展开统一由 `dynamic` 承载；`dynamic.type` 支持 `foreach`、`foreachCase`、`custom`，但 Chapter 级不支持 `custom`
- `catalog.title` 支持在一句话目录标题中直接使用参数槽位；目录标题渲染不经过单独的大模型生成任务。`section` 不再定义标题，只保留诉求定义。
- 参数可定义在模板根部、目录或章节上；参数 `id` 在同一模板内必须全局唯一
- `section` 中保留 `outline.requirement + outline.items`，不要把模板层的诉求骨架改写成 `requirement.text`
- 模板中的目录、子目录、章节、页面顺序由数组位置定义，静态模板不再维护 `order`
- `dataset` 的数据源统一写在 `source` 中，不再使用 `sourceRef`

分页报告结构示例：

```json
{
  "structureType": "paged",
  "chapters": [
    {
      "id": "chapter_overview",
      "title": "整体概览",
      "slides": [
        {
          "id": "slide_kpi_overview",
          "title": "核心指标概览",
          "layout": {
            "layoutId": "title_content",
            "variant": "kpi_grid"
          },
          "sections": []
        }
      ]
    }
  ]
}
```

若分页报告没有显式分节，系统可补一个默认隐式章节：

```json
{
  "id": "__default__",
  "title": "",
  "implicit": true,
  "slides": []
}
```

### 2.1 数据集数据源定义

`DatasetDefinition` 正式收敛为：

- `id`
- `sourceType`
- `source`

`source` 始终是字符串，但语义随 `sourceType` 变化：

- `sql`
  - `source` 直接保存 SQL 模板
  - 模板运行时结合参数实例化为最终 SQL
  - 不在模板中显式声明返回列结构
- `api`
  - `source` 直接保存 API URL
  - 不在模板中显式声明请求参数和响应体结构

约束：

1. 不再使用 `sourceRef`
2. 不引入复杂 `source` 对象
3. SQL 模板占位符语法本轮不做正式约束；示例中的占位写法只用于表达“这里会结合参数实例化”

### 2.2 参数定义采用渐进式统一模型

参数不应在模板、模板实例、对话 ask/reply、报告详情页中各自发明一套结构。
正式设计应统一复用同一组“参数”核心模型，只是在不同阶段字段完整度不同。

统一原则：

1. 参数定义
   - 至少包括：`id/label/description/inputType/required/multi/interactionMode`
2. 带候选值的参数
   - `参数定义 + options`
3. 带外部数据源的参数
   - `参数定义 + source`
4. 已赋值参数
   - `参数定义 + values`
5. 完整运行态参数
   - `参数定义 + options + values + runtimeContext`

建议统一抽象为：

- `Parameter`
  - 基础定义字段
  - 可选补充：
    - `options`
    - `values`
    - `runtimeContext`
- `ParameterConfirmation`
  - 参数补齐/确认的聚合状态

对应关系：

| 场景 | 应复用的统一参数模型 |
|---|---|
| `ReportTemplate.parameters` | `Parameter[]` |
| `TemplateInstance.parameters` | `Parameter[]` |
| `catalog.parameters / section.parameters` | `Parameter[]` |
| `Ask.parameters` | `Parameter[]` |
| `Reply.parameters` | `Record<parameterId, Scalar[]>` |
| 报告详情页再编辑 | `Parameter[]` |

硬规则：

- “参数定义”和“参数赋值”不能再做成两套完全不同的业务结构
- 候选值是参数模型的自然扩展，不应被设计成脱离参数的独立异构结构
- 动态参数、枚举参数、已赋值参数，只是统一参数模型在不同阶段的不同完整度

### 2.3 诉求定义也采用渐进式统一模型

诉求与诉求项也应遵循同样原则。

不应：

- 模板里定义一套 `outline.items`
- 模板实例里再定义另一套完全不同的 `outline.items`

应统一为：

- `Outline`
  - `requirement`
  - `renderedRequirement`
  - `items`
- `RequirementItem`
  - `id/label/kind/required/multi/sourceParameterId/widget/defaultValue/values/valueSource`

对应关系：

| 场景 | 应复用的统一诉求模型 |
|---|---|
| 模板 `section.outline` | `Outline` |
| 模板实例 `section.outline` | `Outline` |
| 再编辑页显示诉求 | `Outline` |
| 生成输入冻结 | `Outline` |

硬规则：

- 模板层是“定义态”
- 模板实例层是“实例态/已解析态”
- 二者必须复用同一套 `Outline/RequirementItem` 核心模型，只允许实例态比定义态多 `renderedRequirement/values/valueSource` 等字段

模板顶层示例：

```json
{
  "id": "tpl_network_daily",
  "category": "network_operations",
  "name": "网络运行日报",
  "description": "面向网络运维中心的统一日报模板。",
  "schemaVersion": "template.v3",
  "parameters": [],
  "catalogs": []
}
```

### 2.4 历史模板顶层结构与当前结构对照

历史模板 `v2` 的顶层结构是：

```json
{
  "id": "...",
  "category": "...",
  "name": "...",
  "description": "...",
  "parameters": [],
  "sections": []
}
```

当前模板顶层结构是：

```json
{
  "id": "...",
  "category": "...",
  "name": "...",
  "description": "...",
  "schemaVersion": "...",
  "parameters": [],
  "catalogs": []
}
```

完整对照如下：

| 历史字段 | 当前字段 | 变化类型 | 说明 |
|---|---|---|---|
| `id` | `id` | 保留 | 无本质变化 |
| `category` | `category` | 保留 | 无本质变化 |
| `name` | `name` | 保留 | 无本质变化 |
| `description` | `description` | 保留 | 无本质变化 |
| 无 | `schemaVersion` | 新增 | 用于显式标识模板结构版本 |
| `parameters` | `parameters` | 保留但内部升级 | 参数结构从旧 `input_type/source/value_mapping` 收敛为统一参数模型与 `source` 口径 |
| `sections` | `catalogs -> (subCatalogs)* -> sections` | 重构 | 把“章节树”提升为“目录树 + 章节”正式模型 |
| 无 | `createdAt/updatedAt` | 新增可选 | 属于模板资产元信息 |

参数层详细对照：

| 历史参数字段 | 当前参数字段 | 说明 |
|---|---|---|
| `input_type` | `inputType` | 命名统一 camelCase |
| `interaction_mode=chat` | `interactionMode=natural_language` | 术语收敛 |
| `source` | `source` | 外部数据源定义简化为 URL 字符串 |
| `value_mode=label/key` | 已取消 | 展示值、实际值、查询值统一由 `ParameterValue` 承载 |
| `value_mapping.query` | 由 `ParameterValue.query` + 运行时上下文承担 | 不再把值映射逻辑散落在模板参数定义里 |
| `options=[string/object]` | `options=[ParameterValue]` | 候选值结构统一 |

参数优先级规则：

- `Parameter.priority` 是 `0-99` 的整数，数字越小追问优先级越高；`0` 最高，`99` 最低
- `priority` 是可选字段，缺省按 `99` 处理
- 对话生成报告时，缺失必填参数按 `priority` 从小到大追问；同一优先级的一批参数一起追问
- `priority = 99` 的参数不单独追问，只在最终确认所有参数的环节一起展示和补齐
- `priority` 不改变 `required` 语义；`required = true` 且 `priority = 99` 的参数在最终确认通过前仍必须有值

结构层详细对照：

| 历史结构 | 当前结构 | 说明 |
|---|---|---|
| `sections[*].subsections` | `catalogs[*].subCatalogs / sections` | 正式引入“目录”业务概念 |
| `Catalog.title / Section.outline.requirement` | `Catalog.title / Section.outline.requirement` | 目录负责展示标题，章节负责内容诉求 |
| `foreach.param` | `dynamic.parameterId` | 旧循环字段归并到统一 `dynamic` 结构 |

动态结构规则：

- `dynamic.type = foreach`：按 `parameterId` 对应参数的每个取值重复展开同一目录或章节模板，`as` 表示当前循环变量别名。
- `dynamic.type = foreachCase`：仍然是 foreach 语义，但每个参数取值会先按 `ParameterValue.value` 匹配 `cases[].values`，再使用命中的 case 内容展开。
- `foreachCase` 的目录级 case 可定义 `subCatalogs` 和/或 `sections`；章节级 case 通过 `sections` 定义章节变体，用于替换当前占位 section。
- 多选参数会按用户选择值逐个展开；多个值命中同一 case 时，每个值仍生成一次，只是复用同一 case 内容模板。
- 未命中 case 时使用 `defaultCase`；没有 `defaultCase` 时，该参数值不生成内容。
- `dynamic.type = custom` 表示由外部服务生成当前目录、章节、分页页面或页面内组件内容，模板定义保持 `{ "type": "custom", "url": "..." }`。
- flow 目录级 `custom` 返回 `meta.dslType = "Catalog"`，`dsl` 是完整 Report DSL `Catalog` 片段。
- flow 章节级 `custom` 必须保留 `outline`，用于用户编辑大纲；返回 `meta.dslType = "Section"`，`dsl` 是完整 Report DSL `Section` 片段。
- paged slide 级 `custom` 返回 `meta.dslType = "Slide"`，`dsl` 是完整 Report DSL `Slide` 片段；模板中的 `sections` 可为空数组。
- paged slide 内 section 级 `custom` 必须保留 `outline`；推荐返回 `meta.dslType = "Components"`，也允许返回 `meta.dslType = "Section"` 后转换为组件集合并入当前 slide。
- Chapter 级不支持 `custom`，只允许 `foreach/foreachCase` 这类结构展开。
- v6 `custom` 请求体由 `parameters/templateNode/context` 组成；`parameters` 为当前节点可见参数，按 `parameterId` 分组，值保持 `ParameterValue` 结构；旧 `nodeType/nodeId/prompt` 不再作为正式协议。
- 新 schema 不再接受旧 `foreach` 字段；实现层可兼容读取旧字段并输出 canonical `dynamic`。

结论：

- 历史模板顶层并不“错”，但它缺少“目录”这一层正式业务概念
- 当前版本在顶层结构上是正确演进方向
- 真正还需要继续收敛的，不是把顶层改回 `sections`，而是把“参数模型”“诉求模型”做成跨模板/实例/接口可复用的一套渐进式模型

## 3. TemplateInstance

正式对象：`TemplateInstance`

关键要求：

- 主体由 `structureType` 决定：flow 保持 `catalogs -> (subCatalogs)* -> sections`，paged 使用 `chapters -> slides -> sections`
- 模板实例根部、目录、章节中的 `parameters` 都统一复用同一套参数模型
- 若用户未显式赋值，则先取参数 `defaultValue` 后再写入对应参数对象的 `values`
- `TemplateInstance.parameters` 与接口层 `Ask.parameters` 使用完全相同的数据形状
- `Reply.parameters` 只保留参数值映射，不再回传参数定义
- 模板实例中的目录、章节也保留各自定义的 `parameters`
- 动态参数候选项写入参数对象的 `options`
- 参数确认聚合态写入 `parameterConfirmation`
- `section.outline.items[].values` 也统一保留 `ParameterValue` 数组，不提前把多值拼成 SQL 字符串
- 模板实例只维护每次操作后的最新状态，不记录变更轨迹
- 顶层模板骨架状态不单独持久化；如需整体状态，由服务端基于各 `section.skeletonStatus` 聚合
- 模板实例允许保留物化后的顺序字段，用于 `dynamic` 展开后的稳定排序与后续冻结
- 模板实例使用 `dynamicContext` 记录展开来源；`foreach/foreachCase` 包含 `type/parameterId/itemValue/caseId`，`custom` 包含 `type/url/nodeType`；旧 `foreachContext` 不再作为新实例输出字段

模板实例顶层示例：

```json
{
  "id": "ti_20260418_001",
  "schemaVersion": "template-instance.v2",
  "templateId": "tpl_network_daily",
  "conversationId": "conv_20260418_001",
  "status": "confirmed",
  "captureStage": "confirm_params",
  "revision": 3,
  "parameters": [],
  "catalogs": []
}
```

### 3.1 与历史 `TemplateInstance v1` 的能力对照

历史版本曾包含：

- `base_template`
- `instance_meta`
- `runtime_state`
- `resolved_view`
- `generated_content`
- `fragments`

当前 `TemplateInstance v2` 已保留或替代的部分：

- `instance_meta.status/revision/conversation_id/chat_id`
  - 已由 `status/captureStage/revision/conversationId/chatId/createdAt/updatedAt` 承担
- `outline_runtime.current_outline_instance`
  - 已由 `catalogs -> (subCatalogs)* -> sections -> outline` 主体承担
- 多层目录
  - 当前版本已显著强于旧版

经本轮重构后，`TemplateInstance` 已补足复杂二次编辑与重新生成所需的最小正式能力：

1. `template`
   - 实例冻结时必须保存完整模板快照
   - 后续二次编辑和重新生成都以该快照为准，不回读线上最新模板
2. 统一 `parameters`
   - 根参数、目录参数、章节参数都复用同一套 `Parameter` 模型
   - 参数定义、候选值、实际取值、运行态来源都在同一对象中渐进展开
3. `parameterConfirmation`
   - 统一表达缺失参数、确认状态、确认时间
   - 不再依赖隐式阶段字段猜测“是否已确认”
4. `outline`
   - 模板定义与模板实例统一复用 `outline.requirement + outline.items`
   - 实例只补 `renderedRequirement/items[].values/items[].valueSource`
5. 章节模板只读回溯能力
   - 当前不单独落 `sectionTemplateSnapshots`
   - 通过 `template + 全局唯一 section.id + 稳定目录树` 回溯实例当时使用的章节模板定义
6. `section.content`
   - 实例态必须保留章节内容结构视图，不能只依赖模板快照里的原始定义
   - `composite_table` 至少落到 `parts[] + part.runtimeContext`，保证复合表可二次编辑和稳定重生成

不建议直接回归为正式领域模型主体的历史对象：

- `generated_content`
  - 这部分应沉淀到 `Report DSL / ReportInstance`
- `fragments`
  - 更适合作为前后端派生视图或缓存片段，不应回升为核心领域字段
- `resolved_view`
  - 其价值真实存在，但应重组为“可派生稳定投影”，而不是与主体重复存储的大块镜像

### 3.2 当前正式补强要求

为支持“调整诉求取值 -> 再次生成报告”的复杂二次编辑，当前正式 `TemplateInstance` 至少具备以下能力：

- `template`
  - 冻结模板结构、参数定义、目录树和章节模板骨架
- 统一 `parameters`
  - 在同一参数对象上表达：定义、候选值、取值、运行态来源
- `parameterConfirmation`
  - 稳定记录缺失参数、确认状态、确认时间
- `catalogs -> (subCatalogs)* -> sections -> outline`
  - 树状主体既服务编辑，也服务重新生成
- `section.content`
  - 章节内容结构在实例态必须可直接读取，尤其是 `presentation.blocks[]`
- `composite_table.parts[].runtimeContext`
  - 复合表子区块的最小运行态必须持久化到实例，而不是只在内存里临时计算

设计原则：

- `TemplateInstance` 仍以树状主体为核心
- `TemplateInstance.section.content` 是正式实例化视图，不是可随意省略的派生缓存
- `template` 与运行态补强字段是为了保证可编辑性和可复现性，不是把旧版镜像结构原样搬回来
- `Report DSL` 仍然是正式报告内容主体；`TemplateInstance` 只负责“生成前”和“再生成前”的完整编辑上下文

### 3.3 历史字段对照与当前归宿

| 历史字段 | 当前状态 | 能力是否仍需要 | 当前归宿建议 |
|---|---|---|---|
| `base_template` | 已重构回正式模型 | 需要 | `template` |
| `instance_meta` | 已被顶层元字段替代 | 部分需要 | 保持 `status/captureStage/revision/conversationId/chatId/createdAt/updatedAt` |
| `runtime_state.parameter_runtime.definitions` | 已并入统一参数模型 | 需要 | `Parameter[]` |
| `runtime_state.parameter_runtime.candidate_snapshots` | 已并入统一参数模型 | 需要 | `Parameter[].options/runtimeContext` |
| `runtime_state.parameter_runtime.selections` | 已并入统一参数模型 | 需要 | `Parameter[].values/runtimeContext` |
| `runtime_state.parameter_runtime.confirmation` | 已补回正式模型 | 需要 | `parameterConfirmation` |
| `runtime_state.outline_runtime.current_outline_instance` | 已被树状主体替代 | 部分需要 | `catalogs -> (subCatalogs)* -> sections -> outline` |
| `resolved_view.parameters` | 已被统一 `Parameter[]` 替代 | 部分需要 | 不单独回滚，可派生 |
| `resolved_view.outline` | 已被 `outline` 树替代 | 部分需要 | 不单独回滚，可派生 |
| `resolved_view.sections[].section_template` | 不单独存储 | 需要 | `template + section.id/path` 回溯 |
| `generated_content` | 已迁往报告侧 | 不需要回归模板实例 | 保持在 `Report DSL / ReportInstance` |
| `fragments` | 已删除 | 不应回归为正式领域字段 | 如有需要，作为派生 UI 视图处理 |

## 4. Report DSL

正式对象：`Report DSL`

关键要求：

- `Report DSL` 直接收编仓库中的正式 DSL Schema，不再手写第二套相似定义
- 其结构必须严格等于 [schemas/report-dsl.schema.json](schemas/report-dsl.schema.json)
- `Report DSL` 使用单一 `Report` 根对象，顶层通过 `structureType` 区分结构：
  - `flow` 或缺省：使用 `catalogs + layout`
  - `paged`：使用 `content`
- flow 的正式主体是 `catalogs -> (subCatalogs)* -> sections -> components`
- paged/PPT 的正式主体是 `content`，其数组只能整体为 `Slide[]` 或整体为 `SlideSection[]`，不得混放
- `reportMeta` 是统一的生成证据、追问、SQL、摘要等补充信息挂载点
- `Report DSL.basicInfo.status` 属于 DSL 内部状态，和接口层 `ReportAnswer.status` 不是同一组枚举
- `Report DSL` 需要保留足够的参数配置和大纲配置，以支持前台对已生成报告进行结构化编辑
- 当前 schema 与 BI Engine TypeScript 模型口径保持对齐：`basicInfo` 采用 `schemaVersion/mode/status/name/reportType/description/templateId/templateName/remark/version/createDate/modifyDate/creator/modifier/header/footer/category`，不再把 `title/parameters/createdAt/updatedAt` 作为正式字段
- 字段类型支持 `boolean`；字段展示配置支持 `valueFormat = time/number/percentage/byte/bitRate/enum/unit`、条件格式 `conditionalFormat`、开放式 `displayPriority`
- `ColumnLineageSource.enumValues` 与 `ui` 是来源系统字符串快照；结构化枚举和展示配置分别进入 `Column.enumConfig` 与 `Column.uiConfig`
- 图表展示配置位于 `ChartAdvanceProperties`，包含 `eChartOption/centerText/subCenterText/responsive/xAxisLabelMode/sqlExplanation`；`ChartComponent.options` 不作为正式公开字段
- 表格展示配置位于 `TableAdvanceProperties`，包含 `showHeader/showTitle/pagination/sqlExplanation`
- `ResponsiveConfig` 只包含 `levels/aspectRatio/minHeight`，`ResponsiveSize` 为 `compact/normal/wide`
- `backCover` 是 paged/PPT 封底配置，公开结构为 `{image?, text?}`
- 表格行合并信息统一命名为 `MergeRowInfo`，字段仍为 `startRowIndex/rowSpan/column/mergedText`
- 图表轴配置位于 `ChartDataProperty.xAxis/yAxis`，不再作为 `ChartComponent` 顶层字段输出

当前业务 profile：

- Schema 全量能力以 `report-dsl.schema.json` 为准
- 但当前报告系统首版只启用其中一个正式子集：
  - 当前运行时仍生成 `structureType = flow` 的目录结构：`catalogs -> (subCatalogs)* -> sections`
  - PPT/paged 扩展不得改变 flow 的 `Catalog/Section/Cover/SignaturePage/ReportSummary` 既有契约；flow 目录仍使用 `Catalog.name`
  - `structureType = paged` 的 `content -> slides/sections` 已进入 DSL 契约和核心模型，模板 paged 结构到 PPT DSL 的编译后续实现
  - 模板/实例态 `presentation.blocks[].type`：正式支持 `text`、`table`、`chart`，并兼容保留 `composite_table`
  - DSL 组件：继续允许系统生成的 `markdown` 组件承载章节说明；模板 presentation 不再直接使用 `markdown` block
  - `CompositeTable` 已作为正式模板能力启用，但只通过 `presentation.blocks[].type = composite_table` 产出
  - `cover`、`signaturePage` 为可选能力，不是所有报告都必须生成；`cover.layoutTemplate` 当前严格取 `TITLE_TOP | TITLE_CENTER`

`Report DSL` 的结构化编辑增强规则：

- `basicInfo` 不再保存 `parameters`
  - 全局参数如需进入冻结报告，应由生成节点的 `GenerateMeta.parameters` 或后续独立编辑上下文承载
  - 避免在 `basicInfo` 中混入运行态参数，保持其只表达 BI Engine 资产元信息
- `GenerateMeta.parameters`
  - 只保存该章节本地参数
  - 结构为 `Record<parameterId, Parameter>`
  - 不重复放全局参数，也不放父 catalog 参数
  - 复用模板参数结构，包含 `inputType/multi/interactionMode/priority/defaultValue/options/values/runtimeContext/source`
- `GenerateMeta.outline`
  - 正式保存章节诉求骨架与实例化结果
  - schema 定义名为 `GenerateOutline`
  - 包含：`requirement`、`renderedRequirement`、`isBroken`、`items`
  - `items[]` 复用完整 `RequirementItem` 结构
- `GenerateMeta.question`
  - 继续保留
  - 与 `outline.renderedRequirement` 并存
  - 二者允许不同值，前端和编译逻辑不得假定相等
- `GenerateMeta.additionalInfos`
  - 使用 BI Engine TS 模型中的复数字段名 `additionalInfos`
  - 每项必须包含 `type/value`，可包含 `name/appendix`
  - `additionalInfo` 与 `content` 仅作为模型层旧输入兼容，不作为公开 schema 字段

`GenerateMeta.outline.items[*]` 规则：

- 使用完整 `RequirementItem`，至少包含 `id/label/kind/required`
- `sourceParameterId` 关联上级参数 id
- `values[]` 使用参数三通道结构 `label/value/query` 保存冻结后的诉求取值

`CompositeTable` 的模板支持规则：

- `presentation.blocks[].type` 当前只正式支持 `text`、`table`、`chart`，并兼容保留 `composite_table`
- `paragraph`、`bullet`、`kpi`、`markdown` 不再作为模板 presentation block 类型使用
- `text` block 的文本字段统一保存在 `properties` 下，模板态必须保存 `properties.template`；实例态必须保存 `properties.template` 和渲染后的 `properties.content`
- `PresentationBlock` 与 `TemplateInstancePresentationBlock` 不直接承载 `template/content` 字段
- `properties.template` 支持两类引用：
  - `{$parameterId}`：引用当前 section 可见参数，按文本展示口径默认读取参数 `label`
  - `{#datasetId.field}`：引用同一 section 内 `content.datasets[].id = datasetId` 的执行结果字段，`field` 使用源数据字段 key
- 一个 `properties.template` 可以引用多个 dataset 字段；当前版本约束被引用 dataset 按单行结果理解，若实际返回多行，默认取第一行对应字段值
- JSON Schema 只校验 `properties.template` 是字符串，不校验 `{#datasetId.field}` 是否存在；dataset 和字段有效性由后续业务校验器或实现阶段处理
- `CompositeTable` 只作为 `section.content.presentation.blocks[]` 的一种 block 类型出现
- 一个 `composite_table` block 由 `parts[]` 组成
- 每个 `part` 只支持两类来源：
  - `query`：与普通表格一致，由 `datasetId` 生成子表
  - `summary`：模板定义固定总结行，模型只填每行内容，最终仍落成无表头二维表
- 基础信息也归为 `query part`，不单独引入第三类 part
- 不在 `part` 内再做 group；若业务上需要多个分区，就拆成多个顺序 `part`

表格布局规则：

- 普通 `presentation.blocks[].type = table` 必须使用 `datasetId` 指向数据集，并通过 `properties` 承载展示属性
- `PresentationProperty.preferredType` 仅对 `type = chart` 生效，用于声明图表首选展示类型；当前枚举为 `line/bar/pie/scatter/radar/gauge/candlestick`
- `PresentationProperty.columns[]` 仅对 `type = table` 的普通表格块生效，使用统一 `TableColumn` 定义
- `TableColumn.key` 是 dataset 执行结果中的字段 key，`TableColumn.title` 是表格展示列名
- `TableColumn.width` 与 `TableColumn.align` 为兼容保留字段，v1 暂不承诺渲染支持
- `PresentationProperty.showTitle` 仅控制普通表格是否显示 `title`，不改变 `title` 字段本身
- `PresentationProperty.defaultDisplayRows` 是普通表格默认展示数据条数，只作为展示提示，不截断 dataset 结果
- 普通表格的 `properties.mergeColumns[]` 用于声明合并列，结构为 `{title, columns}`
- 普通表格的 `properties.mergeRows[]` 用于声明行合并，结构为 `{column, mode}`；`column` 引用 `TableComponent.dataProperties.columns[].key`，并读取 `TableComponent.dataProperties.data[]` 中同名字段
- `mergeRows.mode` 当前仅支持 `default`，缺省为 `default`；默认逻辑是连续多行相同值合并为一个单元格
  - `title` 是合并之后展示的列名称
  - `columns` 是源数据列 key 数组，至少包含两个互不重复的列 key
  - 一个表格可以声明多个合并列，按数组顺序展示
- `composite_table.parts[].tableLayout.columns[]` 与普通表格的 `properties.columns[]` 使用同一套 `TableColumn` 定义
- `composite_table.parts[].tableLayout.showTitle/defaultDisplayRows/mergeColumns[]/mergeRows[]` 与普通表格的同名展示属性语义一致
- `mergeColumns` 只影响展示结构，不修改数据行，也不改变 `columns[]` 中源列的含义
- `mergeRows` 不改变数据排序、不修改数据行；报告 DSL 输出已计算的 `{startRowIndex, rowSpan, mergedText, column}`，其中 `startRowIndex` 从 0 起算

`TemplateInstance` 对 `CompositeTable` 的正式承载规则：

- `TemplateInstance.section.content.presentation.blocks[]` 也必须支持 `type = composite_table`
- 实例态 `text` block 保留模板定义字段 `id/type/title/properties.template/description`，并额外保存渲染后的 `properties.content`
- 实例态普通 `table` block 也必须保留 `datasetId/properties`，供二次编辑与重新生成复用
- 实例态 `composite_table` block 保留模板定义字段：`id/type/title/description/parts[]`
- `parts[]` 在实例态继续保留同样的顺序和结构，不做运行时重排
- `query part`
  - 保留模板定义：`id/title/sourceType/datasetId/tableLayout`
  - 通过 `part.runtimeContext` 记录最小运行态：`status/resolvedDatasetId/resolvedQuery/warnings`
- `summary part`
  - 保留模板定义：`id/title/sourceType/summarySpec`
  - 通过 `part.runtimeContext` 记录最小运行态：`status/resolvedPartIds/prompt/warnings`
- `section.runtimeContext` 只保留章节级执行上下文，不承载复合表结构本身

报告 DSL 顶层示例：

```json
{
  "structureType": "flow",
  "basicInfo": {},
  "catalogs": [],
  "layout": {},
  "reportMeta": {}
}
```

分页/PPT DSL 顶层示例：

```json
{
  "structureType": "paged",
  "basicInfo": {},
  "content": [
    {
      "id": "slide_overview",
      "layout": {"type": "grid", "grid": {"cols": 12, "rowHeight": 24}},
      "components": []
    }
  ]
}
```

## 5. 动态参数外部数据源协议

### 5.1 模板中的声明方式

模板中只保留：

```json
{
  "source": "/rest/parameter-options/network/scopes"
}
```

### 5.2 外部请求体规范

正式 Schema：

- [schemas/parameter-option-source-request.schema.json](schemas/parameter-option-source-request.schema.json)

请求体统一格式：

```json
{
  "scope": [
    {
      "label": "总部网络",
      "value": "hq-network",
      "query": "scope_id = 'hq-network'"
    }
  ],
  "reportDate": [
    {
      "label": "2026-04-18",
      "value": "2026-04-18",
      "query": "2026-04-18"
    }
  ]
}
```

约束：

- 键名是参数 id，且进入公开接口时必须使用 lowerCamelCase
- 值是三元组数组
- 统一采用 `POST`
- 单次返回上限、超时、鉴权等运行约束由系统统一治理，不再写入模板
- 当参数支持多值时，请求中继续传三元组数组；不要提前拼接成逗号串或 SQL 片段

### 5.3 外部响应体规范

正式 Schema：

- [schemas/parameter-option-source-response.schema.json](schemas/parameter-option-source-response.schema.json)

响应体统一格式：

```json
{
  "options": [
    {
      "label": "总部网络",
      "value": "hq-network",
      "query": "scope_id = 'hq-network'"
    }
  ],
  "defaultValue": []
}
```

## 6. 统一约束总结

1. 业务正式模型以本目录的 JSON Schema 为准。
2. API 契约和持久化结构要投影这些模型，不得反向定义第二套对象。
3. 模板定义中的动态候选项数据源协议已经标准化，模板里不再声明方法和报文结构。
4. 模板层与实例层统一复用 `outline.requirement + outline.items`；实例态只额外补 `renderedRequirement/values/valueSource`。
5. 多值参数与多值诉求项在运行态统一保留 `ParameterValue` 数组；展示层默认用 `、` 拼接 `label`，执行层默认由 `runtimeContext.bindings` 按 `multiValueQueryMode = in` 生成最终查询表达式。
6. 参数作用域采用“节点定义、向下继承可见”：章节可见自身参数，目录可见自身及祖先参数，模板根参数全局可见。
7. `section.id` 在单份模板内必须全局唯一；`catalog.id` 也建议全局唯一。`reportMeta` 和流式进度都依赖这一点维持稳定定位。
