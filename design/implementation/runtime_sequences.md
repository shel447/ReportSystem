# 核心运行时序图

## 1. 说明

本篇集中放当前后端公开主链路的关键时序图，帮助在阅读代码时快速建立调用链全貌。

当前覆盖三条主链路：

- 对话确认生成
- 报告聚合读取与文档下载
- 基于模板实例来源的会话恢复

---

## 2. 对话确认生成

适用场景：用户在统一对话中完成模板匹配、参数补充和诉求确认后，点击“确认生成”。

```mermaid
sequenceDiagram
    participant UI as Chat UI
    participant API as /rest/chatbi/v1/chat
    participant Conv as ConversationService
    participant Persist as ConversationPersistenceGateway
    participant State as ConversationStateGateway
    participant Report as ConversationReportGateway
    participant Runtime as ReportInstanceCreationService
    participant Baseline as capture_template_instance
    participant Doc as create_markdown_document

    UI->>API: POST /rest/chatbi/v1/chat(command=confirm_outline_generation)
    API->>Conv: send_message(data)
    Conv->>Persist: get_session(session_id)
    Conv->>State: restore_state_from_history(messages)
    Conv->>Report: merge_outline_override(pending_outline, outline_override)
    Conv->>Report: resolve_outline_execution_baseline(outline)
    Conv->>Report: resolve source_session_id + source_message_id
    Conv->>Report: create_instance(template_id, user_id, input_params, outline_override, source_session_id, source_message_id)
    Report->>Runtime: create_instance(...)
    Runtime-->>Report: created instance payload
    Conv->>Report: capture_template_instance(...)
    Report->>Baseline: write template_instances snapshot
    Conv->>Report: create_markdown_document(instance_id)
    Report->>Doc: render markdown + persist report_documents
    Conv->>State: persist_state_to_history(...)
    Conv->>Persist: save messages into chat_messages
    Conv->>Persist: save session container only
    Conv-->>API: reply + download_document action
    API-->>UI: assistant message + document metadata
```

关键点：

- 对话模块不直接写 `report_instances` 或 `report_documents`，统一经 `ConversationReportGateway` 转入 `report_runtime`
- 诉求编辑结果先解析成执行基线，再创建实例
- 生成成功后会同步固化内部模板实例与 Markdown 文档

---

## 3. 报告聚合读取与文档下载

适用场景：前端在报告页查看聚合结果，并下载指定文档。

```mermaid
sequenceDiagram
    participant UI as Report UI
    participant API as /rest/chatbi/v1/reports
    participant Runtime as ReportRuntimeService
    participant Doc as ReportDocumentService

    UI->>API: GET /rest/chatbi/v1/reports/{reportId}
    API->>Runtime: get_report_view(reportId, user_id)
    Runtime-->>API: reportId + template_instance + generated_content
    API-->>UI: report payload

    UI->>API: GET /rest/chatbi/v1/reports/{reportId}/documents/{documentId}/download
    API->>Runtime: get_report_view(reportId, user_id)
    API->>Doc: resolve_download(documentId)
    Doc-->>API: file metadata + absolute_path
    API-->>UI: markdown file stream
```

关键点：

- 报告读取统一走 `reports` 聚合接口，不再暴露 `instances` 公开接口
- 文档下载路径必须带 `reportId + documentId`，不再走独立 `/documents/*`

---

## 4. 基于模板实例来源的会话恢复

适用场景：用户希望从某份历史生成基线继续对话修改。

```mermaid
sequenceDiagram
    participant UI as Chat UI
    participant API as /rest/chatbi/v1/chat/forks
    participant Conv as ConversationService
    participant Fork as ConversationForkGateway
    participant Persist as ConversationPersistenceGateway

    UI->>API: POST /rest/chatbi/v1/chat/forks(source_kind=template_instance)
    API->>Conv: fork_session(data)
    Conv->>Fork: fork_from_template_instance(...)
    Fork->>Persist: load template_instance snapshot
    Fork->>Fork: build new chat session payload
    Fork->>Fork: inject visible assistant review_outline message
    Fork->>Fork: append hidden context_state snapshot
    Fork->>Persist: save new session + chat_messages
    Persist-->>Conv: session detail payload
    Conv-->>API: fork result
    API-->>UI: new session_id + messages
```

关键点：

- 当前公开恢复入口统一走 `POST /chat/forks`
- 恢复会话不回放完整历史，只注入可继续编辑的诉求确认节点与隐藏上下文快照

---

## 5. 阅读建议

建议和以下文档配合阅读：

- [conversation.md](conversation.md)
- [report_runtime.md](report_runtime.md)
- [database_schema.md](database_schema.md)
- [external_interfaces.md](external_interfaces.md)
