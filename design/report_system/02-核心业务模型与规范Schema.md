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

## 2. ReportTemplate

正式对象：`ReportTemplate`

关键要求：

- `parameters`、`catalogs` 是模板对象根属性，不再放进 `content`
- 模板是静态资产，不带运行态 `status`
- 参数动态候选项来源统一用 `openSource.url` 描述，不再把方法、请求体、响应体格式散落在模板中

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

## 3. TemplateInstance

正式对象：`TemplateInstance`

关键要求：

- 主体保持 `catalogs -> sections`
- `parameterValues` 统一采用“三元组数组”表示，兼容单值和多值参数
- `deltaViews` 只是局部编辑视图，不是持久化真相
- `templateSkeletonStatus` 同时包含系统内部三态和 UI 二态

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
  "parameterValues": {},
  "catalogs": [],
  "deltaViews": [],
  "templateSkeletonStatus": {
    "internal": "reusable",
    "ui": "not_broken"
  }
}
```

## 4. Report DSL

正式对象：`Report DSL`

关键要求：

- `Report DSL` 直接收编仓库中的正式 DSL Schema，不再手写第二套相似定义
- `catalogs -> sections -> components` 是正式主体
- `reportMeta` 是统一的生成证据、追问、SQL、摘要等补充信息挂载点

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
  "openSource": {
    "url": "https://example.internal/api/network/scopes/options"
  }
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
