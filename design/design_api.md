# API 接口设计

> 本文档是 [总设计文档 (design.md)](design.md) 的子文档，详细描述全量 REST API 接口定义与核心时序图。

---

## 1. 核心 API 时序图

### 1.1 生成报告实例

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant ChatBI as ChatBI 服务
    participant Instance as 实例服务
    participant Data as 数据源
    participant LLM as LLM 服务

    Client->>ChatBI: POST /rest/dte/chatbi/instances
    ChatBI->>Instance: 创建实例请求
    Instance->>Data: 采集数据
    Data-->>Instance: 返回数据
    Instance->>LLM: 批量生成内容
    LLM-->>Instance: 返回生成结果
    Instance-->>ChatBI: 返回实例
    ChatBI-->>Client: 201 Created
```

### 1.2 重新生成某节

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant ChatBI as ChatBI 服务
    participant Instance as 实例服务
    participant LLM as LLM 服务

    Client->>ChatBI: POST /rest/dte/chatbi/instances/{id}/regenerate/{section_id}
    ChatBI->>Instance: 重新生成请求
    Instance->>Instance: 定位到指定 Section
    Instance->>LLM: 重新调用 LLM
    LLM-->>Instance: 返回新内容
    Instance->>Instance: 更新 Section 内容
    Instance-->>ChatBI: 返回更新后的实例
    ChatBI-->>Client: 200 OK
```

### 1.3 生成报告文档

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant ChatBI as ChatBI 服务
    participant Doc as 文档服务
    participant HOFS as 文件存储

    Client->>ChatBI: POST /rest/dte/chatbi/documents
    ChatBI->>Doc: 生成文档请求
    Doc->>Doc: 渲染模板
    Doc->>Doc: 生成 Word/PDF
    Doc->>HOFS: 存储文件
    HOFS-->>Doc: 返回文件路径
    Doc-->>ChatBI: 返回文档信息
    ChatBI-->>Client: 201 Created
```

---

## 2. 报告模板

```
POST   /api/templates              # 创建报告模板
GET    /api/templates              # 列出报告模板
GET    /api/templates/{id}         # 获取模板详情
PUT    /api/templates/{id}         # 更新模板
DELETE /api/templates/{id}         # 删除模板
POST   /api/templates/{id}/clone   # 克隆模板
```

---

## 3. 对话交互

```
GET    /api/chat                   # 列出对话历史会话摘要
POST   /api/chat                   # 发送对话消息
GET    /api/chat/{session_id}      # 获取单个会话历史
DELETE /api/chat/{session_id}      # 删除对话会话
```

> 聊天页进入 `/chat` 时保持空态，不自动恢复最近会话，也不预创建会话。只有首条真实用户消息发送后才创建 `ChatSession`，并以该首条用户消息生成会话标题。
>
> 对话生成链路在“大纲确认”阶段会先形成模板实例快照：`edit_outline` 追加 `outline_saved`，`confirm_outline_generation` 在生成报告实例后追加 `outline_confirmed`。

---

## 4. 模板实例管理

```
GET    /api/template-instances     # 列出模板实例快照（只读）
```

返回摘要字段包括模板名、阶段、参数数、章节节点数、大纲预览以及关联的报告实例 ID（若存在）。

---

## 5. 报告实例管理

```
POST   /api/instances              # 生成报告实例
GET    /api/instances              # 列出报告实例 (新增)
GET    /api/instances/{id}         # 获取实例详情
PUT    /api/instances/{id}         # 更新实例
POST   /api/instances/{id}/regenerate/{section_id}  # 重新生成某节
POST   /api/instances/{id}/finalize  # 确认实例，准备生成文档
```

---

## 6. 报告文档管理

```
POST   /api/documents              # 生成报告文档
GET    /api/documents              # 列出报告文档记录 (兼容历史)
GET    /api/documents/{id}         # 获取文档信息
GET    /api/documents/{id}/download  # 下载文档
DELETE /api/documents/{id}         # 删除文档
GET    /api/instances/{id}/documents  # 列出实例关联的所有文档
```

---

## 7. 数据源管理

```
POST   /api/data-sources           # 注册数据源
GET    /api/data-sources           # 列出数据源
GET    /api/data-sources/{id}      # 获取数据源详情
PUT    /api/data-sources/{id}      # 更新数据源
DELETE /api/data-sources/{id}      # 删除数据源
POST   /api/data-sources/{id}/test  # 测试连接
```

---

## 8. 定时任务管理

```
POST   /api/scheduled-tasks              # 创建定时任务
GET    /api/scheduled-tasks              # 列出定时任务
GET    /api/scheduled-tasks/{id}         # 获取任务详情
PUT    /api/scheduled-tasks/{id}         # 更新任务
DELETE /api/scheduled-tasks/{id}         # 删除任务
POST   /api/scheduled-tasks/{id}/pause   # 暂停任务
POST   /api/scheduled-tasks/{id}/resume  # 恢复任务
POST   /api/scheduled-tasks/{id}/run-now # 立即执行一次

# 查看任务生成的报告实例
GET    /api/scheduled-tasks/{id}/instances  # 查看任务生成的实例列表

# 任务执行记录
GET    /api/scheduled-tasks/{id}/executions  # 查看执行历史
```


---

## 9. 待细化内容

> 以下内容将在后续迭代中逐步细化：

- [ ] 各接口的请求/响应 Body 详细字段定义
- [ ] 分页、排序、过滤的通用查询参数规范
- [ ] 错误码与异常响应格式统一规范
- [ ] WebSocket/SSE 实时推送接口（报告生成进度）

