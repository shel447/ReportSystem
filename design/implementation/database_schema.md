# 数据模型与持久化映射

> 权威来源：
> - [数据模型与持久化](../report_system/05-数据模型与持久化.md)
> - [schema_init.sql](../../src/backend/infrastructure/persistence/schema_init.sql)

## 0. 表定义载体

- 运行时唯一建表来源：`src/backend/infrastructure/persistence/models.py` + `Base.metadata.create_all(...)`
- 受版本管理的 SQL 初始化稿：`src/backend/infrastructure/persistence/schema_init.sql`
- 本地运行时数据库文件：`src/backend/report_system.db`

说明：

- `report_system.db` 只作为本地 SQLite 运行时文件，不再纳入版本跟踪
- `schema_init.sql` 用于初始化、审阅和结构比对，不作为第二套运行时权威
- 若 `schema_init.sql` 与 ORM 不一致，以当前 ORM 目标模型为准并同步修正 SQL 稿

## 1. 目标态核心表

- `tbl_users`
- `tbl_conversations`
- `tbl_chats`
- `tbl_report_templates`
- `tbl_template_instances`
- `tbl_report_instances`
- `tbl_report_documents`
- `tbl_export_jobs`
- `tbl_system_settings`
- `tbl_feedbacks`

## 2. 映射原则

- 顶层列只保留元字段
- 详细结构进入 `content`
- `conversation/chat` 是正式物理命名
- 模板、模板实例、报告实例统一使用 `schema_version + content`

## 3. 关键关系

- `tbl_report_instances.template_instance_id` 指向 `tbl_template_instances.id`，且不加唯一约束
- `tbl_report_instances.source_conversation_id/source_chat_id` 表达来源锚点
- `tbl_report_documents` 与 `tbl_export_jobs` 依附 `tbl_report_instances`
