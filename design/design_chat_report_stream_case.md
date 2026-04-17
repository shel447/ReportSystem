# 对话制报告接口串联案例（目标态对齐 ChatBI）

## 1. 范围

目标态对外主链路为：

- `POST /rest/chatbi/v1/chat`
- `GET /rest/chatbi/v1/reports/{reportId}`
- `POST /rest/chatbi/v1/reports/{reportId}/document-generations`
- `GET /rest/chatbi/v1/reports/{reportId}/documents/{documentId}/download`

说明：

- 不存在独立 `/instances/*`
- 不存在独立模板实例接口
- 对话协议严格对齐 `design/chatbi/chatbi_优化建议版.md`

## 2. 核心对象

### 2.1 ReportTemplate

```json
{
  "id": "tpl_ops_daily_v1",
  "category": "ops_daily",
  "name": "运维日报模板",
  "description": "面向运维中心的日报模板",
  "parameters": [],
  "catalogs": []
}
```

### 2.2 TemplateInstance

模板实例是内部核心聚合，不独立暴露。目标态以 `catalog -> section` 为主体：

```json
{
  "id": "ti_20260415_0001",
  "schema_version": "ti.v1.0",
  "conversationId": "conv_001",
  "catalogs": [],
  "bindingStatus": {
    "ui": "not_broken"
  },
  "warnings": []
}
```

### 2.3 Report

正式报告主体是 `ReportDsl`：

```json
{
  "basicInfo": {},
  "catalogs": [],
  "layout": {}
}
```

## 3. 主流程

### 步骤 1：用户发送自然语言需求

`POST /rest/chatbi/v1/chat`

系统完成：

- 能力识别
- 模板匹配
- 首轮参数提取
- 初始化内部 `TemplateInstance`
- 返回 `ask` 或 `answer`

### 步骤 2：多轮补参与诉求确认

后续仍然只调用 `/chat`：

- 参数补充写入当前 `TemplateInstance`
- 待追问参数从当前 `TemplateInstance` 树结构计算
- 诉求确认结果更新 `TemplateInstance.catalogs`

### 步骤 3：确认生成

仍然调用 `/chat`，但目标态在参数确认后按 ChatBI 流式事件模型返回“正在生成中的报告”。

系统完成：

- 基于当前 `TemplateInstance` 构建 `ReportDsl`
- 冻结 `ReportInstance`
- 流式返回 `answerType=REPORT`
- 最终产出 `reportId`

### 步骤 4：查看报告

`GET /rest/chatbi/v1/reports/{reportId}`

返回：

- `answerType=REPORT`
- `answer.report`
- `answer.templateInstance`
- `answer.documents`

### 步骤 5：下载文档

`GET /rest/chatbi/v1/reports/{reportId}/documents/{documentId}/download`

文档下载是报告从属能力，不再作为独立资源集合暴露。

### 步骤 6：生成文档

`POST /rest/chatbi/v1/reports/{reportId}/document-generations`

请求体中指定：

- `formats`
- `pdfSource`
- `theme`
- `strictValidation`
