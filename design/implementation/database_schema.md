# 业务数据库表定义

## 1. 当前实现基线

当前业务库已经按 `tbl_*` 表名落地。围绕公开主链路和内部核心聚合，核心表如下：

- `tbl_users`
- `tbl_chat_sessions`
- `tbl_chat_messages`
- `tbl_report_templates`
- `tbl_template_instances`
- `tbl_report_instances`
- `tbl_report_documents`
- `tbl_system_settings`
- `tbl_template_semantic_indices`
- `tbl_feedbacks`

说明：

- `tbl_scheduled_tasks` 与 `tbl_scheduled_task_executions` 仍可能存在于代码模型中，但当前不属于公开业务面
- `TemplateInstance` 是内部核心聚合，`ReportInstance` 是外部可见报告产物

## 2. 关键建模原则

- 模板只有一套定义，不再使用 `content` 二次包裹
- 模板实例和报告实例继续使用运行态 JSON 承载复杂结构
- 会话与消息拆表
- 文档是报告从属对象，不是独立业务资源

## 3. 表清单

### 3.1 `tbl_report_templates`

用途：静态模板定义主表。

主要维护模块：`template_catalog`

关键字段：

- `id`
- `category`
- `name`
- `description`
- `parameters` JSON
- `sections` JSON
- `created_at`
- `updated_at`
- `created_by`
- `version`

典型写入链路：模板创建、模板更新、模板导入后保存。

典型读取链路：模板列表、模板详情、模板导出、模板匹配、模板实例初始化。

### 3.2 `tbl_template_instances`

用途：内部模板实例聚合。

主要维护模块：`report_runtime`

关键字段：

- `id`
- `template_id`
- `template_name`
- `template_version`
- `session_id`
- `capture_stage`
- `report_instance_id`
- `schema_version`
- `content`
- `created_at`

`content` 典型结构：

- `base_template`
- `runtime_state`
- `resolved_view`
- `generated_content`
- `fragments`

典型写入链路：对话参数收集、诉求确认、确认生成、报告更新。

典型读取链路：报告聚合视图、内部恢复与继续生成。

### 3.3 `tbl_report_instances`

用途：最终报告产物记录。

主要维护模块：`report_runtime`

关键字段：

- `id`
- `template_id`
- `user_id`
- `source_session_id`
- `source_message_id`
- `status`
- `report_time`
- `report_time_source`
- `schema_version`
- `content`
- `created_at`
- `updated_at`

典型写入链路：确认生成报告。

典型读取链路：`GET /rest/chatbi/v1/reports/{reportId}`。

### 3.4 `tbl_report_documents`

用途：报告导出的文档记录。

主要维护模块：`report_runtime`

关键字段：

- `id`
- `instance_id`
- `template_id`
- `format`
- `file_path`
- `file_size`
- `version`
- `status`
- `created_at`

典型写入链路：生成 Markdown 文档。

典型读取链路：报告级下载 `/reports/{reportId}/documents/{documentId}/download`。

### 3.5 `tbl_chat_sessions`

用途：会话容器。

关键字段：

- `id`
- `user_id`
- `title`
- `matched_template_id`
- `fork_meta`
- `status`
- `created_at`
- `updated_at`

### 3.6 `tbl_chat_messages`

用途：消息流水。

关键字段：

- `id`
- `session_id`
- `user_id`
- `role`
- `content`
- `action`
- `meta`
- `seq_no`
- `created_at`

### 3.7 `tbl_template_semantic_indices`

用途：模板语义索引。

关键字段：

- `template_id`
- `semantic_text`
- `embedding_model`
- `embedding_vector`
- `status`
- `error_message`
- `updated_at`

### 3.8 `tbl_users`

用途：业务用户镜像与隔离根。

### 3.9 `tbl_system_settings`

用途：系统与 provider 配置。

### 3.10 `tbl_feedbacks`

用途：反馈记录。
