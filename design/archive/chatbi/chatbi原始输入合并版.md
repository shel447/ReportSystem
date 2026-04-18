# ChatBI 接口定义（原始输入合并版）

> 说明：本文件按用户提供的两批内容进行**合并整理**，仅做 Markdown 排版与章节归并，**不主动修正其中的命名差异、状态枚举冲突、示例不一致等问题**。  
> 用途：作为“原始输入留档版”供评审、比对、追溯。
>
> 本文件不是报告系统当前权威契约。报告系统当前正式契约以 [../report_system/04-接口契约.md](../report_system/04-接口契约.md) 为准。

## 1. 基本信息

- 服务名：ChatBI
- 接口：`POST /rest/dte/smartbi/v1/chat`
- 能力说明：
  - 对话接口支持根据用户问题自动识别任务类型
  - 也支持明确操作指令完成具体任务
  - 支持上传附件进行对话问答
- 同步方式说明：
  - 一个对话发起后，ChatBI 前后端采用增量消息的方式持续同步对话状态数据
  - 最终得到的完整数据结构就是“全量对话响应”
  - 过程中同步的是“增量对话响应”

## 2. 请求体定义（ChatRequest）

扩展请求体，支持携带附件、指定操作指令。

具体定义，见对话“请求体响应体模型定义”。

### 2.1 字段定义

| 字段名 | 数据类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| conversationId | string | 是 | 会话ID |
| chatId | string | 是 | 对话ID |
| question | string | **是** | 用户问题。**对于部分操作指令，用户问题可为空。相关的指令清单：['extract_report_template']** |
| instruction | string | 否 | 明确的操作指令，白名单管理，当前支持范围：['extract_report_template'] |
| reply | Reply | 否 | 当前一轮系统恢复是补充参数、确认参数表单时，表单信息配置完成后通过 reply 返回给系统 |
| attachments | List<Attachment> | 否 | 附件清单。接口预留接收多个附件，但是当前约束仅支持一个附件 |

### 2.2 用户答复（Reply）

| 字段名 | 数据类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| type | string | 是 | 答复类型，['fill_params', 'confirm_params'] |
| parameters | Map<string, object> | 否 | 确认的参数取值 |
| command | Command | 否 | 除了参数信息 wai ，附带的命令指令 |

parameters 示例（没有第一层 parameters）：

```json
{
  "parameters": {
    "report_date": "2026-04-15",
    "scope": "HQ"
  }
}
```

### 2.3 附件（Attachment）

| 字段名 | 数据类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| type | string | 是 | 文件类型，['word'] |
| name | string | 是 | 文件名，带后缀 |
| content | string | 是 | 附件二进制内容的 base64 文本 |

## 3. 全量对话响应体（ChatResponse）

扩展响应体，支持“追问报告参数”、“确认报告参数”。

### 3.1 字段定义

| 字段名 | 数据类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| conversationId | string | 是 | 会话ID |
| chatId | string | 是 | 对话ID |
| question | string | 是 | 用户问题 |
| steps | List<Step> | 否 | 对话回答的推理步骤 |
| status | enum | 是 | 对话状态。取值：[running, finished, failed, aborted]。running：对话仍在进行中；finished：对话完成，输出结果或系统追问；failed：对话异常结束；aborted：对话被人为终止 |
| answer | Answer | 否 | 对话回答结果 |
| ask | Ask | 否 | 追问。追问时，对话状态为 finished |
| suggestions | List<string> | 否 | 推荐下一问的候选项 |
| usage | Usage | 否 | 资源使用 |
| errors | List<Error> | 否 | 对话发生的错误 |

### 3.2 推理步骤（Step）

| 字段名 | 数据类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| stepId | string | 是 | 步骤ID |
| step | string | 是 | 步骤名称。取值：['REASONING', 'QUERY', 'PREPARE_ANSWER'] |
| title | string | 是 | 步骤标题 |
| status | string | 是 | 步骤状态。取值：[running, finished, failed, aborted] |
| contentType | string | 是 | 内容类型。取值：['PLAINTEXT', ''] |
| content | string | 是 | 步骤具体内容 |
| subSteps | List<Step> | 否 | 子步骤 |
| startTime | long | 是 | 起始时间 |
| endTime | long | 是 | 结束时间 |
| costTime | long | 是 | 耗时 |

### 3.3 回答结果（Answer）

| 字段名 | 数据类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| answerType | string | 是 | 结果内容类型。取值：['CHART', 'PLAINTEXT', 'REPORT', '**REPORT_TEMPLATE**'] |
| answer | ReportOutline \| ... | 是 | 结果内容，根据 answerType 有不同的内容 |

### 3.4 追问（Ask）

| 字段名 | 数据类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| mode | string | 是 | 追问形式。取值：['plaintext', 'report_definition', 'form'] |
| type | string | 是 | 追问阶段。取值：['fill_params', 'confirm_params'] |
| text | string | 否 | 追问一句话。mode 取 plaintext 时必填 |
| parameters | List<Parameter> | 否 | 追问哪些参数。对于自然语言追问，也有这个信息 |
| ... |  |  | 后续支持识别其它追问场景扩展此处 |

parameters 示例（没有第一层 parameters）：

```json
{
  "parameters": [
    {
      "id": "report_date",
      "label": "报告日期",
      "inputType": "date",
      "value": "2026-04-15"
    },
    {
      "id": "scope",
      "label": "范围",
      "inputType": "enum",
      "value": "hq",
      "display": "总部",
      "options": [
        { "label": "总部", "value": "HQ" },
        { "label": "华东", "value": "EAST_CHINA" },
        { "label": "华南", "value": "SOUTH_CHINA" }
      ]
    }
  ]
}
```

### 3.5 资源用量（Usage）

| 字段名 | 数据类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| schema | List<Schema> | 否 | 使用到的元数据 |

### 3.6 对话错误（Error）

| 字段名 | 数据类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| key | string | 是 | 错误键 |
| code | string | 是 | 错误编码 |
| detail | Map<string, string> | 否 | 当错误键为 'schema.notexists' 时：`{"datasourceType":"","datasourceName":"","fieldName":""}`；其它情况下暂时没有定义 |

### 3.7 元数据（Schema）

| 字段名 | 数据类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| name | string | 是 | 元数据名称 |
| type | string | 是 | 元数据类型，取值：[entity, view] |

## 4. 增量对话响应体（ChatResponse）

与“全量对话响应”的差异仅在于 steps 部分，故此处仅列出差异点。

### 4.1 字段定义

| 字段名 | 数据类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| conversationId | string | 是 | 会话ID |
| chatId | string | 是 | 对话ID |
| steps | List<IncrementStep> | 否 | 对话回答的推理步骤 |
| ... |  |  | 对话响应的其它字段 |

### 4.2 增量步骤（IncrementStep）

| 字段名 | 数据类型 | 是否必填 | 描述 |
| --- | --- | --- | --- |
| stepId | string | 是 | 步骤ID |
| **parentStepId** | **string** | **否** | **上一级步骤ID** |
| step | string | 是 | 步骤名称。取值：['REASONING', 'QUERY', 'PREPARE_ANSWER'] |
| title | string | 是 | 步骤标题 |
| status | string | 是 | 步骤状态。取值：[running, finished, failed, aborted] |
| contentType | string | 是 | 内容类型。取值：['PLAINTEXT', ''] |
| content | string | 是 | 步骤具体内容 |
| subSteps | List<Step> | 否 | 子步骤 |
| startTime | long | 是 | 起始时间 |
| endTime | long | 是 | 结束时间 |
| costTime | long | 是 | 耗时 |

## 5. 补充场景与示例数据

### 5.1 根据用户问题生成报告场景，请求示例

#### 5.1.1 开始制作报告请求示例

```json
{
  "conversationId": "",
  "chatId": "",
  "question": "帮我制作xxx报告",
  "instruction": "generate_report"
}
```

> 注：示例注释原文为“从对话生成报告 - 指令”。

#### 5.1.2 补充报告参数 - 自然语言形式

```json
{
  "conversationId": "",
  "chatId": "",
  "question": "站点要门店1、门店2的",
  "instruction": "generate_report"
}
```

#### 5.1.3 补充报告参数 - 表单形式

```json
{
  "conversationId": "conv_001",
  "chatId": "chat_002",
  "instruction": "generate_report",
  "question": "先用今天，总部范围。",
  "reply": {
    "type": "fill_params",
    "parameters": {
      "report_date": "2026-04-15",
      "scope": "HQ"
    }
  }
}
```

### 5.2 根据对话历史生成报告请求示例

```json
{
  "conversationId": "",
  "chatId": "",
  "question": "已选择n个对话，生成报告:\n1、xxx\2、xxx ...",
  "instruction": "generate_report",
  "histories": [
    {
      "chatId": ""
    }
  ]
}
```

> 注：示例注释原文为“固定这句话，n就是选中的条数”。

### 5.3 对话提取报告模板请求示例

```json
{
  "conversationId": "4d973b33-3dbd-467c-88ca-0f1f574be861",
  "chatId": "5775f839-4b58-47a8-b31c-e23aac9ebd74",
  "question": "xxx",
  "instruction": "extract_report_template",
  "attachments": [
    {
      "type": "word",
      "name": "资产统计报告.docx",
      "content": "xxxx"
    }
  ]
}
```

### 5.4 对话生成报告定义响应示例

#### case 1：匹配命中模板，追问参数

```json
{
  "conversationId": "conv_001",
  "chatId": "chat_001",
  "status": "waiting_user",
  "steps": [
    {
      "stepId": "s1",
      "parentStepId": null,
      "name": "意图识别",
      "contentType": "text",
      "content": "识别为智能报告"
    },
    {
      "stepId": "s2",
      "parentStepId": null,
      "name": "模板匹配",
      "contentType": "json",
      "content": { "templateId": "tpl_ops_daily_v1", "score": 0.93 }
    }
  ],
  "ask": {
    "mode": "form",
    "title": "请填写参数",
    "type": "fill_params",
    "parameters": [
      { "id": "report_date", "label": "报告日期", "inputType": "date", "required": true },
      {
        "id": "scope",
        "label": "范围",
        "inputType": "enum",
        "required": true,
        "options": [
          { "label": "总部", "value": "HQ" },
          { "label": "华东", "value": "EAST_CHINA" },
          { "label": "华南", "value": "SOUTH_CHINA" }
        ]
      }
    ]
  }
}
```

#### case 2：已完成所有必要参数填写，进行确认

```json
{
  "status": "waiting_user",
  "ask": {
    "mode": "form",
    "type": "confirm",
    "parameters": [
      {
        "id": "report_date",
        "label": "报告日期",
        "inputType": "date",
        "value": "2026-04-15"
      },
      {
        "id": "scope",
        "label": "范围",
        "inputType": "enum",
        "value": "hq",
        "display": "总部",
        "options": [
          { "label": "总部", "value": "HQ" },
          { "label": "华东", "value": "EAST_CHINA" },
          { "label": "华南", "value": "SOUTH_CHINA" }
        ]
      }
    ]
  }
}
```

#### case 3：确认参数，返回生成报告结果

- 响应内容复用：4.4、生成报告 ER 接口 的响应，流式打印
- 原文示例内容：

```text
当前的流式响应报告生成过程
```

## 6. 原始完整响应体示例

```json
{
  "conversationId": "4d973b33-3dbd-467c-88ca-0f1f574be861",
  "chatId": "5775f839-4b58-47a8-b31c-e23aac9ebd74",
  "question": "查询离线网络设备的名称、MAC、sn",
  "steps": [
    {
      "step": "REASONING",
      "stepId": "x",
      "title": "思考并构建查询逻辑",
      "contentType": "PLAINTEXT",
      "status": "aborted",
      "content": "",
      "startTime": "",
      "endTime": "",
      "costTime": "",
      "subSteps": [
        {
          "step": "",
          "stepId": "x1",
          "title": "用户提问分类",
          "contentType": "PLAINTEXT",
          "status": "aborted",
          "content": "3加速度快放假爱斯达克看风景时考虑的副驾驶的框架考虑",
          "startTime": "",
          "endTime": "",
          "subSteps": null
        }
      ]
    },
    {
      "step": "QUERY",
      "stepId": "",
      "title": "执行查询，获取符合条件的数据"
    },
    {
      "step": "PREPARE_ANSWER",
      "stepId": "",
      "title": "渲染数据分析结果",
      "contentType": "",
      "content": "",
      "startTime": "",
      "endTime": "",
      "subSteps": null
    }
  ],
  "status": "finished",
  "ask": {
    "mode": "report_definition",
    "reportDefinition": {}
  },
  "usage": {
    "schema": [
      {
        "type": "entity",
        "name": "EntNetworkElement"
      }
    ]
  },
  "error": {},
  "answer": {},
  "suggestions": [
    "查询离线网络设备信息",
    "查询网络设备离线的数量"
  ]
}
```

## 7. 备注

当前“原始输入合并版”中，仍保留如下可能存在的原始差异或冲突（未修订）：

1. `instruction` 在表格中仅列出 `extract_report_template`，但补充示例中新增了 `generate_report`
2. `status` 在表格中仅列出 `running/finished/failed/aborted`，但补充示例中出现了 `waiting_user`
3. `ask.type` 原始定义为 `confirm_params`，补充示例中出现 `confirm`
4. `steps` 中原始字段为 `step/title`，补充示例中出现 `name`
5. `contentType` 原始枚举为 `PLAINTEXT`，补充示例中出现 `text/json`
6. 错误字段同时出现过 `errors` 与 `error`
7. 原始定义没有 `histories`，补充示例中新增了 `histories`
8. 原始定义中的 `report_definition/reportDefinitions` 与示例中的 `reportDefinition` 命名存在差异
