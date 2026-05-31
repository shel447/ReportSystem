# Report DSL Schema 说明文档

> 对应文件：`docs/implementation/contracts/schemas/report-dsl.schema.json`
> Schema 标题：`Report`
> JSON Schema 版本：Draft 2020-12
> 本文用于解释报告 DSL schema 的设计含义、字段结构、约束规则，并给出使用示例说明。

---

## 1. Schema 总览

Report DSL 是报告生成后的**冻结内容结构**。它不是模板，也不是对话运行态，而是导出器、预览页和后续结构化编辑共同消费的正式报告对象。

从整体结构看，一个 Report DSL 大致可以理解为：

```text
Report
├── structureType        flow | paged，缺省为 flow
├── basicInfo            报告基础信息与资产元数据
├── cover                可选封面
├── backCover            可选封底，主要用于 paged/PPT
├── signaturePage        可选签署页
├── catalogs             flow 报告主体
│   └── sections
│       └── components
├── content              paged/PPT 报告主体，Slide[] 或 SlideSection[]
├── summary              可选报告摘要
├── reportMeta           生成证据与补充信息
└── layout               flow 默认布局
```

顶层对象通过 `structureType` 区分两类报告：

- `flow` 或缺省：使用 `catalogs + layout`，禁止 `content`。
- `paged`：使用 `content`，禁止 `catalogs`。

---

## 2. 顶层 Report 结构

### 2.1 必填与条件字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `basicInfo` | object | 报告基础信息，必填 |
| `structureType` | `"flow" | "paged"` | 报告结构类型，缺省为 `flow` |
| `catalogs` | array | flow 报告主体，flow 时必填 |
| `layout` | object | flow 报告布局，flow 时必填 |
| `content` | array | paged/PPT 报告主体，paged 时必填 |

`flow` 与 `paged` 的主体入口互斥：

```json
{
  "structureType": "flow",
  "basicInfo": { "id": "rpt_001" },
  "catalogs": [],
  "layout": { "type": "grid" }
}
```

```json
{
  "structureType": "paged",
  "basicInfo": { "id": "rpt_ppt_001" },
  "content": []
}
```

### 2.2 可选顶层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `cover` | object | 封面配置 |
| `backCover` | object | 封底配置，主要用于 paged/PPT |
| `signaturePage` | object | 签署页配置 |
| `summary` | object | 报告摘要 |
| `reportMeta` | object | 生成证据、参数、大纲、SQL、API 等补充信息 |

---

## 3. basicInfo

`basicInfo` 保存报告资产和展示所需的基础信息。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 报告唯一标识 |
| `schemaVersion` | string | BI Engine 资产结构版本，当前固定为 `1.0.0` |
| `mode` | `"draft" | "published"` | 报告资产模式 |
| `status` | `Running | Success | Aborted | Failed` | DSL 内部状态 |
| `name` | string | 报告名称 |
| `reportType` | `PPT | Word | Dashboard` | 报告类型 |
| `description` | string | 报告说明 |
| `templateId` | string | 来源模板 ID |
| `templateName` | string | 来源模板名称 |
| `version` | string | 报告内容版本 |
| `createDate` / `modifyDate` | string | BI Engine 资产时间字段 |
| `creator` / `modifier` | string | 创建人与修改人 |
| `header` / `footer` | string | 文档页眉/页脚文本 |
| `category` / `remark` | string | 分类与备注 |

`status` 是 DSL 内部状态，不等同于接口层报告资源状态。

`basicInfo` 字段与 BI Engine `BasicInfo` 权威模型保持一致；`title/parameters/createdAt/updatedAt` 不再作为 Report DSL `basicInfo` 的正式字段。报告标题由 `cover.title`、目录标题或具体页面标题承担，参数快照由 `reportMeta[*].parameters` 按生成节点保存。

---

## 4. flow 主体

flow 报告使用 `catalogs -> sections -> components`。

### 4.1 Catalog

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 目录唯一标识 |
| `name` | string | 目录展示名 |
| `subCatalogs` | array | 子目录 |
| `sections` | array | 章节 |

flow 的目录字段保持既有契约，目录展示名使用 `name`，不是 `title`。

### 4.2 Section

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 章节唯一标识 |
| `title` | string | 章节标题 |
| `order` | number | 章节顺序 |
| `components` | array | 章节组件 |
| `summary` | object | 章节摘要 |

`components` 是章节最终展示内容，不再包含模板实例的运行态字段。

---

## 5. paged/PPT 主体

paged 报告使用 `content`。`content` 只能整体为 `Slide[]` 或整体为 `SlideSection[]`，不建议混放，schema 会拒绝混合数组。

### 5.1 Slide

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 页面唯一标识 |
| `title` | string | 页面标题 |
| `layout` | object | 页面布局 |
| `components` | array | 页面组件 |

### 5.2 SlideSection

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 页面分组 ID |
| `type` | `"section"` | 固定值 |
| `title` | string | 分组标题 |
| `slides` | array | 分组内页面 |

`Slide` 和 `SlideSection` 不再定义 `description`；页面说明类文本应通过 `text` 组件表达。

### 5.3 backCover

`backCover` 与 BI Engine `PPT.backCover` 对齐，用于表达封底。

```json
{
  "backCover": {
    "image": "https://example.test/assets/back-cover.png",
    "text": "Thank You"
  }
}
```

`image` 可为 URL 或 base64 字符串；`text` 是封底展示文本。

---

## 6. 布局

`layout` 描述页面或组件布局。

| 字段 | 类型 | 说明 |
|---|---|---|
| `type` | `grid | flex | absolute` | 布局类型 |
| `autoLayout` | boolean | 是否启用自动布局 |
| `grid` | object | 栅格配置 |

`grid` 常用字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `cols` | number | 栅格列数 |
| `rowHeight` | number | 行高 |
| `gap` | number | 间距 |

---

## 7. 组件

`BIEngineComponent` 当前支持：

- `text`
- `table`
- `chart`
- `markdown`
- `compositeTable`

组件公共字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 组件唯一标识 |
| `type` | string | 组件类型 |
| `layout` | object | 组件布局 |
| `basicProperties` | object | 基础展示属性 |
| `advanceProperties` | object | 高级展示属性 |
| `interactions` | array | 交互配置 |
| `dataProperties` | object | 数据属性 |

---

## 8. TextComponent

文本组件使用：

```json
{
  "id": "text_overview",
  "type": "text",
  "dataProperties": {
    "dataType": "static",
    "content": "总部网络整体运行平稳。"
  }
}
```

`TextDataProperty` 必须包含 `dataType` 和 `content`。

---

## 9. TableComponent

表格组件使用 `TableDataProperty`。

关键字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `dataType` | `static | datasource | api` | 数据来源类型 |
| `sourceId` | string | 数据源 ID |
| `columns` | array | 表格列定义 |
| `data` | array | 静态数据 |
| `mergeColumns` | array | 列合并定义 |
| `mergeRows` | array | 行合并渲染信息 |
| `hasMerge` | boolean | 是否存在合并展示 |

### 9.1 Column

| 字段 | 类型 | 说明 |
|---|---|---|
| `key` | string | 数据字段 key |
| `title` | string | 展示列名 |
| `sortable` | boolean | 是否可排序 |
| `filterable` | boolean | 是否可筛选 |
| `width` | string/number | 列宽 |
| `type` | `string/long/int/timestamp/double/float/boolean/enum` | 字段类型 |
| `enumConfig` | array | 枚举值配置 |
| `uiConfig` | object | 字段展示配置 |
| `lineageTracing` | object | 字段血缘信息 |

`uiConfig.valueFormat` 支持 `time/number/percentage/byte/bitRate/enum/unit`。`uiConfig.conditionalFormat` 用于定义条件格式规则，当前包含数值比较、区间判断、文本色调和字重等展示提示。`displayPriority` 支持 `high/normal/low/never`，也允许自定义字符串或数字以兼容 BI Engine 字段配置。

`ColumnLineageSource.enumValues` 和 `ui` 是来源系统中的字符串快照；如需结构化枚举或 UI 展示配置，应在列级 `enumConfig` 和 `uiConfig` 中表达。

### 9.2 MergeColumnInfo

```json
{
  "title": "指标信息",
  "columns": ["metric_name", "metric_value"],
  "isMergeValue": false
}
```

`columns` 至少包含两个字段 key，且不能重复。

### 9.3 MergeRowInfo

```json
{
  "startRowIndex": 0,
  "rowSpan": 2,
  "column": "scope_name",
  "mergedText": "总部网络"
}
```

`MergeRowInfo` 是 DSL 中唯一正式的行合并信息定义；不再额外保留 `MergeRowConfig`。

---

## 10. ChartComponent

图表组件使用 `ChartDataProperty`。图表轴配置位于 `dataProperties.xAxis/yAxis`，不是组件顶层字段。

```json
{
  "id": "chart_availability",
  "type": "chart",
  "advanceProperties": {
    "eChartOption": { "legend": { "show": true } },
    "responsive": { "aspectRatio": 1.6 },
    "xAxisLabelMode": "truncate",
    "sqlExplanation": "查询近 7 天核心可用率趋势。"
  },
  "dataProperties": {
    "dataType": "static",
    "series": [
      {
        "type": "line",
        "name": "可用率",
        "encode": { "x": "stat_date", "y": "availability_rate" }
      }
    ],
    "xAxis": { "type": "category", "name": "日期" },
    "yAxis": { "type": "value", "name": "可用率" }
  }
}
```

`series` 支持 `line/bar/pie/scatter/radar/gauge/candlestick`。不同图表类型的 `encode` 字段不同，必须按 schema 对应分支填写。

图表高级展示配置统一位于 `advanceProperties`，不再在 `ChartComponent` 顶层使用 `options`。`responsive.levels[*].size` 支持 `compact/normal/wide`；`responsive` 不再需要 `enabled` 字段。

表格高级展示配置位于 `TableComponent.advanceProperties`，除 `showHeader/showTitle/pagination` 外，还可保存 `sqlExplanation` 作为 chat 模式查询解释文本。

---

## 11. CompositeTableComponent

复合表组件使用：

```json
{
  "id": "composite_metrics",
  "type": "compositeTable",
  "tables": [],
  "dataProperties": {
    "dataType": "static",
    "title": "复合表"
  }
}
```

`tables[]` 内部复用 `TableComponent`。导出时按数组顺序纵向拼接多个子表；子表可以拥有不同列结构，但 Word/PPT 输出必须保持组合表格的总宽度对齐，子表之间不插入额外空白。

---

## 12. reportMeta

`reportMeta` 以节点 ID 为 key，保存生成证据。

```json
{
  "reportMeta": {
    "section_summary": {
      "status": "Success",
      "question": "分析总部网络总体运行态势。",
      "additionalInfos": [
        {
          "type": "SQL",
          "name": "核心指标 SQL",
          "value": "select * from network_metrics",
          "appendix": "demo"
        }
      ],
      "outline": {
        "requirement": "分析 {@scope} 的总体运行态势。",
        "renderedRequirement": "分析总部网络的总体运行态势。",
        "isBroken": false,
        "items": [
          {
            "id": "scope",
            "label": "分析对象",
            "kind": "parameter_ref",
            "required": true,
            "sourceParameterId": "scope",
            "values": [
              { "label": "总部网络", "value": "hq-network", "query": "scope_id = 'hq-network'" }
            ]
          }
        ]
      },
      "parameters": {
        "scope": {
          "id": "scope",
          "label": "分析对象",
          "inputType": "enum",
          "required": true,
          "multi": false,
          "interactionMode": "form",
          "options": [
            { "label": "总部网络", "value": "hq-network", "query": "scope_id = 'hq-network'" }
          ]
        }
      }
    }
  }
}
```

`GenerateMeta` 对齐 BI Engine TS 模型，只公开 `status/question/additionalInfos/outline/parameters`。`status` 与 `question` 必填；SQL、Prompt、Summary、API、Knowledge 等生成证据统一进入 `additionalInfos[]`。

`outline` 的 schema 定义名为 `GenerateOutline`，结构复用模板/实例态的 `OutlineDefinition + RequirementItem`；`parameters` 复用完整模板参数结构，不使用简化参数结构。

`additionalInfos[]` 每项必须包含 `type/value`，可包含 `name/appendix`。模型层可兼容读取历史 `additionalInfo` 或 `content` 输入，但新输出必须使用 `additionalInfos` 与 `value`。

---

## 13. 示例文件

参考示例：

- [examples/report-dsl.example.json](../schemas/examples/report-dsl.example.json)：flow 报告示例。
- [examples/report-dsl-paged.example.json](../schemas/examples/report-dsl-paged.example.json)：paged/PPT 报告示例。

使用建议：

1. 先根据 `structureType` 判断读取 `catalogs` 还是 `content`。
2. 导出器只消费 Report DSL，不读取 TemplateInstance。
3. 组件渲染以 `type + dataProperties` 为主，布局与样式由 `layout/basicProperties/advanceProperties` 辅助。
4. 图表轴配置读取 `dataProperties.xAxis/yAxis`。
5. 行合并只识别 `MergeRowInfo` 结构。
