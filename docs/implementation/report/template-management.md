# 模板目录实现

字段级结构以 [报告模板 Schema](../contracts/schemas/report-template.schema.json) 和 [模板技术手册](../contracts/manuals/报告模板定义与使用说明书.md) 为准。

## 1. 模块定位

`report` context 中的模板管理源文件负责静态模板资产的完整生命周期：

- 模板校验
- 模板导入预览
- 模板 CRUD
- 模板导出
- 模板匹配索引准备

## 2. 正式模型

唯一正式对象为 `ReportTemplate`，根结构固定为：

- `id`
- `category`
- `name`
- `description`
- `schemaVersion`
- `structureType`
- `parameters`
- `catalogs` 或 `chapters`

其中：

- 参数定义直接采用 `report-template.schema.json#/$defs/Parameter`
- `Parameter.priority` 是 `0-99` 的整数，缺省按 `99` 处理；本轮只补模型定义，不接入对话追问排序业务实现
- 参数值三元组统一为 `{label, value, query}`，模板目录侧不再保留 `display`
- `structureType` 缺省为 `flow`；flow 结构固定为 `catalogs -> (subCatalogs)* -> sections`
- `structureType = paged` 时使用 `chapters -> slides -> sections`，`sections` 复用既有 `SectionDefinition`
- `ChapterDefinition` 和 `SlideDefinition` 只进入模板契约和核心模型；运行时实例化、DSL 编译和 PPT 渲染适配后续实现
- `ChapterDefinition.dynamic` 仅允许 `foreach/foreachCase` 这类结构展开，不允许 `custom`
- `SlideDefinition.dynamic.custom` 允许用于 paged 外部页面生成，外部响应目标为 Report DSL `Slide`；slide 内 `SectionDefinition.dynamic.custom` 响应目标为 `Components` 或可转换为组件集合的 `Section`
- `SlideLayout` 只作为设计器和后续 PPT 渲染适配提示，当前不承诺渲染语义
- 目录、章节和分页页面的动态展开统一采用 `dynamic` 字段；`type` 支持 `foreach/foreachCase/custom`，但 Chapter 级不支持 `custom`
- `foreachCase` 是特殊 foreach，不是单选 switch；它按参数每个取值匹配 case，并使用 case 中不同的 `subCatalogs/sections` 定义生成内容
- `custom` 使用显式 `url` 字段，不再保留占位 `config`；章节级 custom 仍必须提供 `outline` 以支持用户编辑大纲；正式外部协议采用 v6 `parameters/templateNode/context` 请求体与 `status/dsl/meta.dslType` 响应体
- 后端核心模型保留旧 `ForeachDefinition` 兼容入口，但正式序列化只输出 `dynamic`
- `outline.requirement + outline.items` 是模板层诉求骨架
- 静态模板顺序由数组位置定义，不再维护 `order`
- `section.content.presentation.blocks[]` 当前支持 `text`、`table`、`chart`，并兼容保留 `composite_table`
- `text` block 模板态必须在 `properties.template` 保存文本模板；实例态渲染结果保存在 `properties.content`
- `PresentationBlock` 与 `TemplateInstancePresentationBlock` 不直接序列化 `template/content`
- `chart` block 通过 `properties.preferredType` 承载首选图表类型，当前取值跟随 DSL 图表族 `line/bar/pie/scatter/radar/gauge/candlestick`
- 普通 `table` block 通过 `properties` 承载展示属性；当前包含 `columns/showTitle/defaultDisplayRows/mergeColumns/mergeRows`
- `composite_table.parts[].tableLayout` 继续承载复合表子表布局，包含 `columns/showTitle/defaultDisplayRows/mergeColumns/mergeRows`
- `columns[]` 统一采用 `TableColumn`；`key/title` 是正式字段，`width/align` 为兼容保留字段，v1 暂不承诺渲染支持
- `showTitle` 只控制标题展示，不改变 `title` 字段；`defaultDisplayRows` 只表示默认展示条数，不截断 dataset 结果
- `mergeColumns[]` 固定为 `{title, columns}`；`columns` 是至少两个互不重复的源数据列 key
- `mergeRows[]` 固定为 `{column, mode}`；`column` 对应表格 `columns[].key`，`mode` 当前仅支持 `default`
- 后端领域实现上，以上结构必须全部以递归 `dataclass` 表达，不允许再以 `parameters: list[dict]`、`catalogs: list[dict]`、`chapters: list[dict]` 这种形式悬空
- dataclass 内部属性名保持 `snake_case`；所有公开 JSON 固定字段名统一通过 `field(metadata={"alias": "lowerCamelCase"})` 声明，再由序列化边界读取 alias 输出
- `ReportTemplate` 顶层不再定义 `tags`

## 3. 应用层职责

当前代码中，模板目录能力通过 report context 的 `ReportService` 总入口暴露，内部由两个职责明确的 service 收口：

### 3.1 `ReportTemplateService`

承担以下功能职责：

- `create_template`
  - 校验正式模板 payload
  - 调用 repository 创建模板
  - 返回正式模板详情对象
- `update_template`
  - 校验 Query 参数 `templateId` 与 payload `id` 一致
  - 校验正式模板 payload
  - 更新模板并返回正式模板详情对象
- `delete_template`
  - 删除静态模板资产
- `get_template`
  - 读取单个正式模板详情
- `list_templates`
  - 返回模板列表页所需摘要，不重复返回完整 `parameters/catalogs/chapters`
- `export_template`
  - 读取正式模板并返回等价 JSON 与导出文件名
- `preview_import_template`
  - 接收对象或 JSON 文本
  - 归一化并校验后返回 `normalizedTemplate + warnings`
- `serialize_detail`
  - 把领域对象投影为路由层 DTO

应用层补充约束：

- `ReportTemplateService` 的输入输出边界仍是 JSON 契约
- 但 service 内部拿到的 `ReportTemplate` 必须已经是递归 dataclass
- repository 不得把 `ReportTemplate.parameters/catalogs/chapters` 继续还原成裸字典后再向上返回

### 3.2 `ReportParameterService`

承担以下功能职责：

- 从用户自然语言中提取已出现的报告参数值
- 合并结构化补参答复，判断必填参数是否仍有缺失
- 构造报告场景的补参追问或诉求确认追问
- 读取模板参数中的 `source`
- 调用本地 demo 源或远端 HTTP 数据源
- 执行请求体大小限制、超时限制和响应 schema 校验
- 输出正式 `options/defaultValue/meta` 结构
  - 其中候选值固定为 `{label, value, query}`

应用层必须保证：

- 读写前后都严格满足模板 schema
- 导入预览只返回 `normalizedTemplate + warnings`
- 导入预览、模板提取、正式落库共享同一套规范化与校验器
- 不做旧字段别名吸收
- 旧 `foreach` 字段只允许在核心模型兼容层吸收，应用层对外返回必须是 `dynamic`
- 动态参数响应不合法时直接在应用层拦截，不把脏数据放进对话层

模板校验至少要覆盖：

- 参数 id 全局唯一
- section id 全局唯一
- 每个 catalog 至少拥有 `subCatalogs` 或 `sections` 之一
- 静态模板中不允许再出现 `order`

## 4. 基础设施职责

- `SqlAlchemyReportTemplateRepository`
- `JsonSchemaTemplateValidator`
- `EmbeddingTemplateIndexGateway`

索引文本只允许由下列字段构成：

- `title`
- `description`
- `category`
- `parameters[*]`
- `catalogs[*].title` 递归目录标题模板，实例态产出 `renderedTitle`
- `catalogs[*]` 递归章节 `outline.requirement`

## 5. 对外接口映射

- `POST /templates`
- `GET /templates`
- `GET /templates/detail?templateId={id}`
- `PUT /templates/detail?templateId={id}`
- `DELETE /templates/detail?templateId={id}`
- `POST /templates/import/preview`
- `GET /templates/export?templateId={id}`

模板详情、创建、更新、导出必须返回同一份正式 `ReportTemplate`。
