# 持久化实现

完整表结构、ER 图、DDL 和升级规则见 [数据库契约](../contracts/database/README.md)。

## 1. 表结构总览

数据库按用途拆分：

- 正式业务库：`.runtime/report_system.db`
- 开发辅助库：`.runtime/dev_support.db`
- 查询演示库：`.runtime/telecom_demo.db`

表定义载体统一为：

- 业务 ORM：`modules/backend/src/infrastructure/persistence/models.py`
- 开发辅助 ORM：`modules/backend/src/infrastructure/persistence/dev_models.py`
- 可执行升级 SQL：`modules/backend/src/infrastructure/persistence/upgrades/`
- 最新完整表定义：[数据库契约](../contracts/database/README.md)

其中：

- `.runtime/` 为本地自动生成目录，不纳入版本跟踪
- 新安装和后续升级统一执行 `upgrades/`，不再使用单独初始化稿
- 两个应用数据库各自维护 `__db_schema_version`
- 运行时涉及 JSON Schema 校验时，统一直接引用 `docs/implementation/contracts/schemas/*.json`，不在后端源码根目录保留本地镜像文件

主业务表固定为：

- `tbl_users`
- `tbl_conversations`
- `tbl_chats`
- `tbl_report_templates`
- `tbl_template_instances`
- `tbl_report_instances`
- `tbl_report_documents`
- `tbl_export_jobs`

开发辅助表进入独立数据库：

- `dev_system_settings`
- `dev_feedbacks`

## 2. JSON 列规则

- `tbl_report_templates.content` 保存完整 `ReportTemplate`，包含 `structureType` 以及对应的 `catalogs` 或 `chapters`
- `tbl_template_instances.content` 保存完整 `TemplateInstance`，包含 `structureType` 以及对应的 `catalogs` 或 `chapters`
- `tbl_report_instances.content` 保存完整 `Report DSL`

`content` 内部不再额外包一层 `content`。

## 3. 必要元字段

模板：

- `id/category/name/description/schema_version/created_at/updated_at`

模板实例：

- `id/template_id/conversation_id/chat_id/user_id/status/capture_stage/revision/schema_version/created_at/updated_at`

报告实例：

- `id/template_id/template_instance_id/user_id/source_conversation_id/source_chat_id/status/schema_version/created_at/updated_at`

文档：

- `id/report_instance_id/artifact_kind/source_format/generation_mode/mime_type/storage_key/status/error_message`

任务：

- `id/report_instance_id/user_id/current_format/status/dependency_job_id/exporter_backend/request_payload_hash/started_at/finished_at/error_code/error_message`

## 4. 读写约束

- 用户归属业务查询强制带 `user_id`
- 会话消息按 `conversation_id + seq_no` 读取
- 文档下载通过 `report_id + document_id` 双重校验
- 导出任务直接按 `user_id` 隔离；文档产物通过报告实例间接隔离
- 删除历史旧表与旧 ORM，不保留旧 SQLite 兼容升级代码
