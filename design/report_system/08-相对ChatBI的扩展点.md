# 08. 相对 ChatBI 的扩展点

> 本篇只说明报告系统在统一对话协议基线上的扩展点。报告系统自身的正式接口定义仍以 [04-接口契约](04-接口契约.md) 为准。

## 1. 扩展原则

1. 复用统一对话外层包络：`conversationId / chatId / ask / answer / steps / SSE events`
2. 只扩展报告所需载荷，不改写统一对话的总体事件模型
3. 正式新增的重点对象是：
   - `ReportTemplate`
   - `TemplateInstance`
   - `Report DSL`
   - `DocumentGeneration`

## 2. 关键扩展点

### 2.1 Ask 扩展

统一对话基线里，`ask` 只关心追问本身；报告系统新增：

- `reportContext.templateInstance`

作用：

- 前端可直接展示当前模板实例
- 用户修改诉求后可整棵树回传
- 后台据此判定模板骨架是否被破坏
- `Ask.parameters[*].parameter` 与模板参数定义保持字段兼容，避免前后端维护两套参数对象

### 2.2 Answer 扩展

报告系统新增 `REPORT` 载荷：

- `reportId`
- `report`
- `templateInstance`
- `documents`
- `generationProgress`

### 2.3 文档生成扩展

统一对话基线中没有正式的报告文档生成资源；报告系统新增：

- `POST /reports/{reportId}/document-generations`
- `GET /reports/{reportId}/documents/{documentId}/download`

### 2.4 动态参数扩展

模板里的动态参数增加：

- `openSource.url`

同时系统统一约束外部参数候选项协议：

- 请求体：`{"参数id": [三元组]}`
- 响应体：`{"options": [], "defaultValue": []}`

## 3. 对前端的影响

前端需要新增或调整：

1. `TemplateInstance` 树的渲染与编辑
2. `deltaViews` 的生成与回传
3. 报告生成中的流式 `REPORT` 增量渲染
4. 报告详情页对 `report + templateInstance + documents` 的统一承载
