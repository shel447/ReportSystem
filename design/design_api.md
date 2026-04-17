# API 接口设计

## 1. 总体约束

### 1.1 身份头

除 `/rest/dev/*` 外，业务接口统一要求：

```http
X-User-Id: <external-user-id>
```

服务端以该值查找或创建用户镜像，并对会话、消息、报告做隔离。

### 1.2 公开业务面

当前公开业务资源只保留：

- `templates`
- `chat`
- `reports`
- `parameter-options/resolve`

说明：

- 不再暴露 `/instances/*`
- 不再暴露 `/scheduled-tasks/*`
- 不再暴露独立 `/documents/*`
- `TemplateInstance` 是内部核心聚合，不提供独立公开接口

## 2. 报告模板

```text
POST   /rest/chatbi/v1/templates
GET    /rest/chatbi/v1/templates
GET    /rest/chatbi/v1/templates/{id}
PUT    /rest/chatbi/v1/templates/{id}
DELETE /rest/chatbi/v1/templates/{id}
POST   /rest/chatbi/v1/templates/import/preview
GET    /rest/chatbi/v1/templates/{id}/export
```

模板正式结构固定为：

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

约束：

- 不再接受或返回 `report_type`
- 不再接受或返回 `template_type`
- 不再接受或返回模板顶层 `scene`
- 不再接受或返回模板顶层 `outline`
- 不再接受或返回 `content_params / match_keywords / output_formats / schema_version`

导入预解析接口只做：

- 来源识别
- 归一化
- 校验
- 冲突检测

不直接入库。

导出文件名格式：

- `模板名称-YYYYMMDD-HHMMSS.json`

## 3. 统一对话

```text
GET    /rest/chatbi/v1/chat
POST   /rest/chatbi/v1/chat
POST   /rest/chatbi/v1/chat/forks
GET    /rest/chatbi/v1/chat/{session_id}
DELETE /rest/chatbi/v1/chat/{session_id}
```

职责：

- 模板匹配
- 参数提取与追问
- 诉求确认
- 确认生成
- 会话历史与 fork

`POST /rest/chatbi/v1/chat` 同时支持新契约字段：

- `conversationId`
- `chatId`
- `instruction`
- `question`
- `reply`
- `command.name`

若请求头 `Accept: text/event-stream`，返回 SSE 骨架事件。

对话过程中，系统持续维护内部 `TemplateInstance`，并通过 `ask / answer / delta / steps` 返回片段；不会暴露独立模板实例资源。

## 4. 报告

```text
GET /rest/chatbi/v1/reports/{reportId}
GET /rest/chatbi/v1/reports/{reportId}/documents/{documentId}/download
```

`GET /reports/{reportId}` 返回：

```json
{
  "reportId": "rpt_001",
  "status": "completed",
  "template_instance": {},
  "generated_content": {}
}
```

约束：

- `template_instance` 为完整内部模板实例快照
- 文档下载为报告从属能力，只允许 report-scoped 路径
- `POST /rest/chatbi/v1/reports/{reportId}/edit-stream` 仍在待实现专题，本轮未开放

## 5. 动态参数辅助接口

```text
POST /rest/chatbi/v1/parameter-options/resolve
```

说明：

- 这是模板编辑与对话收参使用的辅助公共接口
- 不作为独立业务资源页暴露

响应固定为：

```json
{
  "items": [
    { "label": "总部", "value": "HQ", "query": "HQ" }
  ],
  "meta": {}
}
```

## 6. 开发接口

统一前缀：

```text
/rest/dev/*
```

当前保留：

- 系统设置
- 设计文档查看/下载
- 反馈

这些接口不受 `X-User-Id` 业务隔离约束。
