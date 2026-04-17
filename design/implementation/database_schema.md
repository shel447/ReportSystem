# 业务数据库表定义

## 1. 目标态表基线

当前业务库已经按 `tbl_*` 表名落地。围绕公开主链路和内部核心聚合，核心表如下：

- `tbl_users`
- `tbl_chat_sessions`
- `tbl_chat_messages`
- `tbl_report_templates`
- `tbl_template_instances`
- `tbl_report_instances`
- `tbl_report_documents`
- `tbl_export_jobs`
- `tbl_system_settings`
- `tbl_template_semantic_indices`
- `tbl_feedbacks`

说明：

- `TemplateInstance` 是内部核心聚合
- `ReportInstance` 是外部可见报告产物
- `ReportDocument` 是报告从属资源
- `ExportJob` 用于追踪文档生成链路

## 2. 关键建模原则

- 模板只有一套定义，主结构为 `catalogs -> sections`
- 模板实例和报告实例继续使用 JSON 承载复杂结构
- 会话与消息拆表，但设计语义统一为 `conversation / chat`
- 报告实例主体是持久化 `Report DSL`
- 文档是报告从属对象，不是独立业务资源

## 3. 表清单

### 3.1 `tbl_report_templates`

用途：静态模板定义主表。

关键字段：

- `id`
- `category`
- `name`
- `description`
- `parameters`
- `catalogs`
- `created_at`
- `updated_at`
- `created_by`

### 3.2 `tbl_template_instances`

用途：内部模板实例聚合。

关键字段：

- `id`
- `template_id`
- `template_name`
- `conversation_id`
- `capture_stage`
- `report_instance_id`
- `schema_version`
- `content`
- `created_at`

`content` 推荐结构：

- `input_params_snapshot`
- `catalogs`
- `delta_views`
- `binding_status`
- `warnings`

### 3.3 `tbl_report_instances`

用途：最终报告产物记录。

关键字段：

- `id`
- `template_id`
- `user_id`
- `source_conversation_id`
- `source_chat_id`
- `status`
- `report_time`
- `report_time_source`
- `schema_version`
- `content`
- `created_at`
- `updated_at`

`content` 推荐结构：

- `dsl`
- `source_meta`
- `runtime_meta`

### 3.4 `tbl_report_documents`

用途：报告导出的文档记录。

关键字段：

- `id`
- `report_instance_id`
- `artifact_kind`
- `source_format`
- `generation_mode`
- `mime_type`
- `file_path`
- `file_size`
- `status`
- `export_job_id`
- `created_at`

说明：

- `artifact_kind` 支持 `markdown / word / ppt / pdf`
- `pdf` 首版为派生格式

### 3.5 `tbl_export_jobs`

用途：文档生成任务追踪。

关键字段：

- `id`
- `report_instance_id`
- `requested_formats`
- `current_format`
- `status`
- `dependency_job_id`
- `exporter_backend`
- `request_payload_hash`
- `started_at`
- `finished_at`
- `error_code`
- `error_message`

### 3.6 `tbl_chat_sessions`

用途：会话容器。

关键字段：

- `id`
- `user_id`
- `title`
- `fork_meta`
- `status`
- `created_at`
- `updated_at`

说明：

- 表名沿用历史命名
- 业务语义统一按 `conversation` 理解

### 3.7 `tbl_chat_messages`

用途：消息流水。

关键字段：

- `id`
- `conversation_id`
- `user_id`
- `role`
- `content`
- `action`
- `meta`
- `seq_no`
- `created_at`

说明：

- 表名沿用历史命名
- 业务语义统一按 `chat` 理解

### 3.8 `tbl_template_semantic_indices`

用途：模板语义索引。

### 3.9 `tbl_users`

用途：业务用户镜像与隔离根。

### 3.10 `tbl_system_settings`

用途：系统与 provider 配置。

### 3.11 `tbl_feedbacks`

用途：反馈记录。
