# 数据模型与持久化映射

> 权威来源：
> - [数据模型与持久化](../report_system/05-数据模型与持久化.md)

## 1. 目标态核心表

- `tbl_users`
- `tbl_conversations`
- `tbl_chats`
- `tbl_report_templates`
- `tbl_template_instances`
- `tbl_report_instances`
- `tbl_report_documents`
- `tbl_export_jobs`
- `tbl_template_semantic_indices`

## 2. 映射原则

- 顶层列只保留元字段
- 详细结构进入 `content`
- `conversation/chat` 是正式物理命名
- 模板、模板实例、报告实例统一使用 `schema_version + content`

## 3. 关键关系

- `tbl_report_instances.template_instance_id` 指向 `tbl_template_instances.id`，且不加唯一约束
- `tbl_report_instances.source_conversation_id/source_chat_id` 表达来源锚点
- `tbl_report_documents` 与 `tbl_export_jobs` 依附 `tbl_report_instances`
