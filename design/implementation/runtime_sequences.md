# 核心运行时序图

## 1. 说明

本篇集中放当前后端最关键的运行时序图，帮助在阅读代码时先建立调用链全貌，再进入各 bounded context 的实现细节。

当前先覆盖三条主链路：

- 对话确认生成
- 定时任务 run-now
- 报告实例 update-chat

---

## 2. 对话确认生成

适用场景：用户在统一对话中完成模板匹配、参数补充和大纲确认后，点击“确认生成”。

```mermaid
sequenceDiagram
    participant UI as Chat UI
    participant API as /api/chat
    participant Conv as ConversationService
    participant Persist as ConversationPersistenceGateway
    participant State as ConversationStateGateway
    participant Report as ConversationReportGateway
    participant Runtime as ReportInstanceCreationService
    participant Baseline as capture_generation_baseline
    participant Doc as create_markdown_document

    UI->>API: POST /api/chat(command=confirm_outline_generation)
    API->>Conv: send_message(data)
    Conv->>Persist: get_session(session_id)
    Conv->>State: restore_state_from_history(messages)
    Conv->>Report: merge_outline_override(pending_outline, outline_override)
    Conv->>Report: resolve_outline_execution_baseline(outline)
    Conv->>Report: create_instance(template_id, input_params, outline_override)
    Report->>Runtime: create_instance(...)
    Runtime->>Runtime: load template
    alt v2 template
        Runtime->>Runtime: generate_v2_from_outline / generate_v2
    else legacy template
        Runtime->>Runtime: expand outline / generate sections
    end
    Runtime-->>Report: created instance payload
    Conv->>Report: capture_generation_baseline(...)
    Report->>Baseline: write template_instances snapshot
    Conv->>Report: create_markdown_document(instance_id)
    Report->>Doc: render markdown + persist report_documents
    Conv->>State: persist_state_to_history(...)
    Conv->>Persist: save_session(messages, matched_template_id, instance_id)
    Conv-->>API: reply + download_document action
    API-->>UI: assistant message + document metadata
```

关键点：

- 对话模块不直接写 `report_instances` 或 `report_documents` 表，而是通过 `ConversationReportGateway` 进入 `report_runtime`
- 生成前的大纲编辑结果先被解析成实例级执行基线，再创建实例
- 生成成功后会同时固化 `template_instances` 内部快照和 Markdown 文档

---

## 3. 定时任务 run-now

适用场景：用户在定时任务页手动点击“立即执行”。

```mermaid
sequenceDiagram
    participant UI as Tasks UI
    participant API as /api/scheduled-tasks/{id}/run
    participant App as SchedulingService
    participant TaskRepo as ScheduledTaskRepository
    participant Runtime as ScheduledInstanceCreationGateway
    participant ReportApp as ScheduledReportRunService
    participant Doc as ReportDocumentService
    participant ExecRepo as TaskExecutionRepository

    UI->>API: POST run-now
    API->>App: run_task_now(task_id)
    App->>TaskRepo: get(task)
    App->>App: compute actual_run_time / scheduled_time
    App->>App: build override params from time_param_name/time_format
    App->>Runtime: create_instance_from_schedule(template_id, source_instance_id, override_params, report_time)
    Runtime->>ReportApp: create_instance_from_schedule(...)
    ReportApp->>ReportApp: merge source instance params + override params
    ReportApp->>ReportApp: create_instance(...)
    ReportApp-->>Runtime: created instance payload
    alt instance created successfully
        App->>ExecRepo: record_success(task_id, instance_id, input_params_used, started_at)
        App->>TaskRepo: record_success(task_id, actual_run_time)
        opt auto_generate_doc = true
            App->>Doc: create_document(instance_id, markdown)
            Doc-->>App: document_id
        end
        App-->>API: executed + instance_id + optional document_id
    else instance creation failed
        App->>ExecRepo: record_failure(task_id, input_params_used, error_message, started_at)
        App->>TaskRepo: record_failure(task_id, actual_run_time)
        App-->>API: propagate error
    end
```

关键点：

- `scheduling` 自己不生成报告内容，只负责任务规则、时间映射和执行记录
- `scheduled_time` 当前在 `run-now` 场景下等于 `actual_run_time`
- `report_time` 是否写入实例，取决于 `use_schedule_time_as_report_time`

---

## 4. 报告实例 update-chat

适用场景：用户在报告实例页点击“更新”，希望基于确认大纲恢复到对话助手继续修改。

```mermaid
sequenceDiagram
    participant UI as Instance Detail UI
    participant API as /api/instances/{id}/update-chat
    participant Conv as ConversationService
    participant Persist as ConversationPersistenceGateway
    participant Fork as ConversationForkGateway
    participant Baseline as template_instances
    participant SessionRepo as chat_sessions

    UI->>API: POST update-chat
    API->>Conv: update_session_from_instance(instance_id)
    Conv->>Persist: get_generation_baseline(instance_id)
    Persist->>Baseline: query by report_instance_id
    Baseline-->>Conv: generation baseline
    Conv->>Fork: update_session_from_generation_baseline(template_instance)
    Fork->>Fork: build new chat session payload
    Fork->>Fork: inject single visible assistant review_outline message
    Fork->>Fork: append hidden context_state snapshot
    Fork->>SessionRepo: persist new chat session
    SessionRepo-->>Fork: new session_id + messages
    Fork-->>Conv: chat session detail payload
    Conv-->>API: prefetched session payload
    API-->>UI: session detail
    UI->>UI: navigate to /chat?session_id=... with prefetchedSession
```

关键点：

- `update-chat` 不回放原始整段对话，只恢复一个可继续编辑的大纲确认节点
- 恢复依据是 `template_instances` 中的内部生成基线，而不是当前实例正文反推
- 前端拿到的是完整 `ChatSessionDetail`，这样跳转 `/chat` 后可以立即渲染，不必再等待二次拉取

---

## 5. 阅读建议

建议和以下文档配合阅读：

- [conversation.md](conversation.md)
- [report_runtime.md](report_runtime.md)
- [scheduling.md](scheduling.md)
- [database_schema.md](database_schema.md)
- [external_interfaces.md](external_interfaces.md)
