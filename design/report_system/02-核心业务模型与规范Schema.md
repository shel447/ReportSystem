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

原则：

1. Schema 是正式约束，示例只是参考。
2. 开发、测试、导入导出、文档生成都必须围绕这些 Schema 工作。
3. 若 `/src/backend` 中的历史 Schema 与本目录冲突，以本目录为准；后续代码实现再回收旧定义。
4. `Report DSL` 必须严格遵循 [src/backend/report.schema.json](E:/code/codex_projects/ReportSystemV2/src/backend/report.schema.json)；本目录中的 `report-dsl.schema.json` 只是该契约的镜像副本，供设计文档、校验脚本和开发联调直接引用。

## 2. ReportTemplate

正式对象：`ReportTemplate`

关键要求：

- `parameters`、`catalogs` 是模板对象根属性，不再放进 `content`
- 模板是静态资产，不带运行态 `status`
- 参数动态候选项来源统一用 `source` 描述，类型是 URL 字符串；不再把方法、请求体、响应体格式散落在模板中
- 所有参数都必须显式声明 `multi`；候选值来源由是否存在 `source` 决定
- 模板支持多层目录：每个 `catalog` 下可以同时存在 `subCatalogs` 与 `sections`
- `catalog.title` 支持在一句话目录标题中直接使用参数槽位；目录标题渲染不经过单独的大模型生成任务。`section` 不再定义标题，只保留诉求定义。
- 参数可定义在模板根部、目录或章节上；参数 `id` 在同一模板内必须全局唯一
- `section` 中保留 `outline.requirement + outline.items`，不要把模板层的诉求骨架改写成 `requirement.text`
- 模板中的目录、子目录、章节顺序由数组位置定义，静态模板不再维护 `order`

### 2.1 参数定义采用渐进式统一模型

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
| `Reply.parameters` | `Parameter[]` |
| 报告详情页再编辑 | `Parameter[]` |

硬规则：

- “参数定义”和“参数赋值”不能再做成两套完全不同的业务结构
- 候选值是参数模型的自然扩展，不应被设计成脱离参数的独立异构结构
- 动态参数、枚举参数、已赋值参数，只是统一参数模型在不同阶段的不同完整度

### 2.2 诉求定义也采用渐进式统一模型

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

### 2.3 历史模板顶层结构与当前结构对照

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
| 无 | `tags` | 新增可选 | 用于筛选、搜索、运营管理 |
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

结构层详细对照：

| 历史结构 | 当前结构 | 说明 |
|---|---|---|
| `sections[*].subsections` | `catalogs[*].subCatalogs / sections` | 正式引入“目录”业务概念 |
| `Catalog.title / Section.outline.requirement` | `Catalog.title / Section.outline.requirement` | 目录负责展示标题，章节负责内容诉求 |
| `foreach.param` | `foreach.parameterId` | 命名统一 |

结论：

- 历史模板顶层并不“错”，但它缺少“目录”这一层正式业务概念
- 当前版本在顶层结构上是正确演进方向
- 真正还需要继续收敛的，不是把顶层改回 `sections`，而是把“参数模型”“诉求模型”做成跨模板/实例/接口可复用的一套渐进式模型

## 3. TemplateInstance

正式对象：`TemplateInstance`

关键要求：

- 主体保持 `catalogs -> (subCatalogs)* -> sections`
- 模板实例根部、目录、章节中的 `parameters` 都统一复用同一套参数模型
- 若用户未显式赋值，则先取参数 `defaultValue` 后再写入对应参数对象的 `values`
- `TemplateInstance.parameters` 与接口层 `Ask.parameters/Reply.parameters` 使用完全相同的数据形状
- 模板实例中的目录、章节也保留各自定义的 `parameters`
- 动态参数候选项写入参数对象的 `options`
- 参数确认聚合态写入 `parameterConfirmation`
- `section.outline.items[].values` 也统一保留 `ParameterValue` 数组，不提前把多值拼成 SQL 字符串
- 模板实例只维护每次操作后的最新状态，不记录变更轨迹
- 顶层模板骨架状态不单独持久化；如需整体状态，由服务端基于各 `section.skeletonStatus` 聚合
- 模板实例允许保留物化后的顺序字段，用于 `foreach` 展开后的稳定排序与后续冻结

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

1. `templateSnapshot`
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
   - 通过 `templateSnapshot + 全局唯一 section.id + 稳定目录树` 回溯实例当时使用的章节模板定义

不建议直接回归为正式领域模型主体的历史对象：

- `generated_content`
  - 这部分应沉淀到 `Report DSL / ReportInstance`
- `fragments`
  - 更适合作为前后端派生视图或缓存片段，不应回升为核心领域字段
- `resolved_view`
  - 其价值真实存在，但应重组为“可派生稳定投影”，而不是与主体重复存储的大块镜像

### 3.2 当前正式补强要求

为支持“调整诉求取值 -> 再次生成报告”的复杂二次编辑，当前正式 `TemplateInstance` 至少具备以下能力：

- `templateSnapshot`
  - 冻结模板结构、参数定义、目录树和章节模板骨架
- 统一 `parameters`
  - 在同一参数对象上表达：定义、候选值、取值、运行态来源
- `parameterConfirmation`
  - 稳定记录缺失参数、确认状态、确认时间
- `catalogs -> (subCatalogs)* -> sections -> outline`
  - 树状主体既服务编辑，也服务重新生成

设计原则：

- `TemplateInstance` 仍以树状主体为核心
- `templateSnapshot` 与运行态补强字段是为了保证可编辑性和可复现性，不是把旧版镜像结构原样搬回来
- `Report DSL` 仍然是正式报告内容主体；`TemplateInstance` 只负责“生成前”和“再生成前”的完整编辑上下文

### 3.3 历史字段对照与当前归宿

| 历史字段 | 当前状态 | 能力是否仍需要 | 当前归宿建议 |
|---|---|---|---|
| `base_template` | 已重构回正式模型 | 需要 | `templateSnapshot` |
| `instance_meta` | 已被顶层元字段替代 | 部分需要 | 保持 `status/captureStage/revision/conversationId/chatId/createdAt/updatedAt` |
| `runtime_state.parameter_runtime.definitions` | 已并入统一参数模型 | 需要 | `Parameter[]` |
| `runtime_state.parameter_runtime.candidate_snapshots` | 已并入统一参数模型 | 需要 | `Parameter[].options/runtimeContext` |
| `runtime_state.parameter_runtime.selections` | 已并入统一参数模型 | 需要 | `Parameter[].values/runtimeContext` |
| `runtime_state.parameter_runtime.confirmation` | 已补回正式模型 | 需要 | `parameterConfirmation` |
| `runtime_state.outline_runtime.current_outline_instance` | 已被树状主体替代 | 部分需要 | `catalogs -> (subCatalogs)* -> sections -> outline` |
| `resolved_view.parameters` | 已被统一 `Parameter[]` 替代 | 部分需要 | 不单独回滚，可派生 |
| `resolved_view.outline` | 已被 `outline` 树替代 | 部分需要 | 不单独回滚，可派生 |
| `resolved_view.sections[].section_template` | 不单独存储 | 需要 | `templateSnapshot + section.id/path` 回溯 |
| `generated_content` | 已迁往报告侧 | 不需要回归模板实例 | 保持在 `Report DSL / ReportInstance` |
| `fragments` | 已删除 | 不应回归为正式领域字段 | 如有需要，作为派生 UI 视图处理 |

## 4. Report DSL

正式对象：`Report DSL`

关键要求：

- `Report DSL` 直接收编仓库中的正式 DSL Schema，不再手写第二套相似定义
- 其结构必须严格等于 [src/backend/report.schema.json](E:/code/codex_projects/ReportSystemV2/src/backend/report.schema.json)
- `catalogs -> (subCatalogs)* -> sections -> components` 是正式主体
- `reportMeta` 是统一的生成证据、追问、SQL、摘要等补充信息挂载点
- `Report DSL.basicInfo.status` 属于 DSL 内部状态，和接口层 `ReportAnswer.status` 不是同一组枚举

当前业务 profile：

- Schema 全量能力以 `report.schema.json` 为准
- 但当前报告系统首版只启用其中一个正式子集：
  - 目录：`catalogs -> (subCatalogs)* -> sections`
  - 组件：优先使用 `text`、`table`、`chart`、`markdown`
  - `CompositeTable` 属于保留能力，首版不作为模板编译目标
  - `cover`、`signaturePage` 为可选能力，不是所有报告都必须生成

报告 DSL 顶层示例：

```json
{
  "basicInfo": {},
  "catalogs": [],
  "layout": {}
}
```

## 5. 动态参数外部数据源协议

### 5.1 模板中的声明方式

模板中只保留：

```json
{
  "source": "https://example.internal/api/network/scopes/options"
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
      "display": "总部网络",
      "value": "hq-network",
      "query": "scope_id = 'hq-network'"
    }
  ],
  "report_date": [
    {
      "display": "2026-04-18",
      "value": "2026-04-18",
      "query": "2026-04-18"
    }
  ]
}
```

约束：

- 键名是参数 id
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
      "display": "总部网络",
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
5. 多值参数与多值诉求项在运行态统一保留 `ParameterValue` 数组；展示层默认用 `、` 拼接 `display`，执行层默认由 `runtimeContext.bindings` 按 `multiValueQueryMode = in` 生成最终查询表达式。
6. 参数作用域采用“节点定义、向下继承可见”：章节可见自身参数，目录可见自身及祖先参数，模板根参数全局可见。
7. `section.id` 在单份模板内必须全局唯一；`catalog.id` 也建议全局唯一。`reportMeta` 和流式进度都依赖这一点维持稳定定位。
