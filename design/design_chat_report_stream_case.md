# 对话制报告接口串联案例（当前实现基线）

## 1. 范围

当前对外主链路固定为：

- `POST /rest/chatbi/v1/chat`
- `GET /rest/chatbi/v1/reports/{reportId}`
- `GET /rest/chatbi/v1/reports/{reportId}/documents/{documentId}/download`

说明：

- 不存在独立 `/instances/*`
- 不存在独立模板实例接口
- `POST /rest/chatbi/v1/reports/{reportId}/edit-stream` 仍待实现，本轮不变

## 2. 核心对象

### 2.1 ReportTemplate

```json
{
  "id": "tpl_ops_daily_v1",
  "category": "ops_daily",
  "name": "运维日报模板",
  "description": "面向运维中心的日报模板",
  "parameters": [],
  "sections": []
}
```

### 2.2 TemplateInstance

模板实例是内部核心聚合，不独立暴露。它组合模板快照并持续维护运行态：

```json
{
  "id": "ti_20260415_0001",
  "schema_version": "ti.v1.0",
  "base_template": {
    "id": "tpl_ops_daily_v1",
    "category": "ops_daily",
    "name": "运维日报模板",
    "description": "面向运维中心的日报模板",
    "parameters": [],
    "sections": []
  },
  "instance_meta": {},
  "runtime_state": {},
  "resolved_view": {},
  "generated_content": {},
  "fragments": {}
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
- 待追问参数从当前 `TemplateInstance` 填充状态计算
- 诉求确认结果更新 `TemplateInstance.runtime_state / resolved_view`

### 步骤 3：确认生成

仍然调用 `/chat`。

系统完成：

- 基于当前 `TemplateInstance` 生成报告
- 产出 `reportId`
- 返回 `answerType=report_ready`

### 步骤 4：查看报告

`GET /rest/chatbi/v1/reports/{reportId}`

返回：

- `template_instance`
- `generated_content`

### 步骤 5：下载文档

`GET /rest/chatbi/v1/reports/{reportId}/documents/{documentId}/download`

文档下载是报告从属能力，不再作为独立资源集合暴露。
