# 核心运行时序图

## 1. 说明

本篇集中放目标态关键时序图，帮助在阅读代码和设计文档时快速建立调用链全貌。

当前覆盖三条主链路：

- 对话确认生成并流式返回报告
- 报告聚合读取与文档下载
- 基于模板实例来源的会话恢复

---

## 2. 对话确认生成并流式返回报告

适用场景：用户在统一对话中完成模板匹配、参数补充和诉求确认后，点击“确认生成”。

```mermaid
sequenceDiagram
    participant UI as Chat UI
    participant API as /rest/chatbi/v1/chat
    participant Conv as ConversationService
    participant Persist as ConversationPersistenceGateway
    participant State as ConversationStateGateway
    participant Report as ConversationReportGateway
    participant Runtime as Report Runtime Application
    participant LLM as LLM

    UI->>API: POST /rest/chatbi/v1/chat(command=confirm_outline_generation)
    API->>Conv: send_message(data)
    Conv->>Persist: get_conversation(conversationId)
    Conv->>State: restore_state_from_history(chats)
    Conv->>Report: merge_outline_override(templateInstance, outlineOverride)
    Conv->>Report: build_template_instance(...)
    Conv->>Runtime: build_report_dsl(templateInstance)
    Runtime->>LLM: generate sections/components
    Runtime-->>Conv: REPORT stream deltas
    Conv->>Runtime: freeze_report_instance(...)
    Conv->>Persist: save chats + hidden context_state
    Conv-->>API: SSE events(status/step_delta/answer/done)
    API-->>UI: 流式 REPORT
```

关键点：

- `/chat` 在确认生成后按 ChatBI 事件模型流式返回 `REPORT`
- `REPORT` 中同时携带 `report + templateInstance + documents`
- 报告实例冻结晚于首个流式报告骨架返回

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
    Runtime-->>API: report + templateInstance + documents
    API-->>UI: report payload

    UI->>API: GET /rest/chatbi/v1/reports/{reportId}/documents/{documentId}/download
    API->>Runtime: assert_report_belongs_to_user(reportId, user_id)
    API->>Doc: resolve_download(documentId)
    Doc-->>API: file metadata + absolute_path
    API-->>UI: file stream
```

关键点：

- 报告读取统一走 `reports` 聚合接口
- 文档下载路径必须带 `reportId + documentId`
- 详情接口返回正式报告和模板实例，用于支持再次编辑诉求

---

## 4. 文档生成

适用场景：用户在报告详情页请求生成 Word / PPT / PDF。

```mermaid
sequenceDiagram
    participant UI as Report UI
    participant API as /rest/chatbi/v1/reports/{reportId}/document-generations
    participant App as ExportReportService
    participant Repo as ReportInstanceRepository
    participant Java as JavaOfficeExporterGateway
    participant PDF as PdfConversionService
    participant Doc as ReportDocumentService

    UI->>API: POST document-generations(formats=[word,ppt,pdf])
    API->>App: request_generation(reportId, formats, options)
    App->>Repo: load report instance with content.dsl
    App->>Java: export word/ppt from report_dsl
    Java-->>App: artifacts
    App->>PDF: derive pdf if requested
    PDF-->>App: pdf artifact
    App->>Doc: register documents
    App-->>API: jobs + documents
    API-->>UI: generation result
```

---

## 5. 基于模板实例来源的会话恢复

适用场景：用户希望从某份历史报告的模板实例继续编辑诉求。

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
    Fork->>Fork: build new conversation payload
    Fork->>Fork: inject visible review_outline message
    Fork->>Fork: append hidden context_state snapshot
    Fork->>Persist: save new conversation + chats
    Persist-->>Conv: conversation detail payload
    Conv-->>API: fork result
    API-->>UI: new conversationId + chats
```

---

## 6. 阅读建议

建议和以下文档配合阅读：

- [conversation.md](conversation.md)
- [report_runtime.md](report_runtime.md)
- [database_schema.md](database_schema.md)
- [external_interfaces.md](external_interfaces.md)
