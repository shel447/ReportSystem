# 业务数据库表定义总览

## 1. 说明

本篇集中维护当前后端所有业务表定义。模块文档只引用这里，不重复粘贴整张表。

表定义来源：

- `E:/code/codex_projects/ReportSystemV2/src/backend/infrastructure/persistence/models.py`

## 2. 表清单

| 表名 | 主要维护模块 | 用途 |
|------|--------------|------|
| `report_templates` | `template_catalog` | 模板主数据 |
| `report_instances` | `report_runtime` | 报告实例 |
| `template_instances` | `report_runtime` | 内部生成基线快照 |
| `report_documents` | `report_runtime` | 文档记录 |
| `scheduled_tasks` | `scheduling` | 定时任务 |
| `scheduled_task_executions` | `scheduling` | 定时任务执行记录 |
| `chat_sessions` | `conversation` | 会话与消息历史 |
| `system_settings` | `infrastructure/settings` | Provider 与系统设置 |
| `template_semantic_indices` | `template_catalog` | 模板语义索引 |
| `feedbacks` | `feedback` supporting module | 用户反馈 |

## 3. 表定义

### report_templates

- 表用途：保存报告模板主定义
- 主要维护模块：`template_catalog`
- 主键：`template_id`
- 关键字段：
  - `name`：模板名称
  - `description`：模板说明
  - `report_type / scenario / template_type / scene`：模板业务分类
  - `parameters`：新版参数定义
  - `sections`：新版章节双层结构
  - `content_params / outline`：旧兼容字段
  - `match_keywords`：关键字匹配辅助信息
  - `schema_version`：模板 schema 版本
  - `output_formats`：允许导出格式
  - `version`：模板版本字符串
- 典型写入链路：`templates router -> TemplateCatalogService -> SqlAlchemyTemplateCatalogRepository`
- 典型读取链路：模板列表/详情、模板匹配、实例创建时读取模板

### report_instances

- 表用途：保存用户可见的报告实例
- 主要维护模块：`report_runtime`
- 主键：`instance_id`
- 关键字段：
  - `template_id / template_version`：来源模板
  - `status`：实例状态，例如 `draft / finalized`
  - `input_params`：本次实例输入参数
  - `outline_content`：章节内容结果与调试信息
  - `report_time / report_time_source`：业务报告时间及其来源
  - `created_at / updated_at`：审计时间
- 典型写入链路：
  - 对话确认生成
  - 定时任务 run-now
  - 实例更新字段
- 典型读取链路：实例列表、详情、文档导出、定时任务回源

### template_instances

- 表用途：保存内部生成基线快照
- 主要维护模块：`report_runtime`
- 主键：`template_instance_id`
- 关键字段：
  - `template_id / template_name / template_version`
  - `session_id`：来源对话会话
  - `capture_stage`：当前仍保留阶段字段，现主要用于基线兼容
  - `input_params_snapshot`：确认参数快照
  - `outline_snapshot`：确认大纲 / 执行基线快照
  - `warnings`：生成警告
  - `report_instance_id`：关联实例
- 典型写入链路：对话确认生成后 `capture_generation_baseline()`
- 典型读取链路：实例 baseline、update-chat、fork source 恢复

### report_documents

- 表用途：保存文档元数据
- 主要维护模块：`report_runtime`
- 主键：`document_id`
- 关键字段：
  - `instance_id`：所属实例
  - `template_id`：来源模板
  - `format`：当前主要是 `md`
  - `file_path / file_size`
  - `version`：同一实例同一格式的递增版本
  - `status`
- 典型写入链路：`ReportDocumentService.create_document()`
- 典型读取链路：文档列表、下载、删除

### scheduled_tasks

- 表用途：保存定时任务定义
- 主要维护模块：`scheduling`
- 主键：`task_id`
- 关键字段：
  - `user_id`
  - `source_instance_id / template_id`
  - `schedule_type / cron_expression / timezone`
  - `enabled / status`
  - `auto_generate_doc`
  - `time_param_name / time_format / use_schedule_time_as_report_time`
  - `last_run_at / next_run_at`
  - `total_runs / success_runs / failed_runs`
- 典型写入链路：任务创建、更新、pause/resume、执行统计回写
- 典型读取链路：任务列表、详情、run-now 执行前加载

### scheduled_task_executions

- 表用途：保存定时任务每次执行结果
- 主要维护模块：`scheduling`
- 主键：`execution_id`
- 关键字段：
  - `task_id`
  - `status`
  - `generated_instance_id`
  - `started_at / completed_at`
  - `error_message`
  - `input_params_used`
- 典型写入链路：`run_task_now()` 中记录 success/failure
- 典型读取链路：任务执行记录列表

### chat_sessions

- 表用途：保存统一对话会话与消息历史
- 主要维护模块：`conversation`
- 主键：`session_id`
- 关键字段：
  - `user_id`
  - `title`
  - `messages`：完整消息流与上下文快照
  - `fork_meta`：来源信息
  - `matched_template_id`
  - `instance_id`
  - `status`
  - `created_at / updated_at`
- 典型写入链路：发送消息、fork 新会话、update-chat 创建新会话
- 典型读取链路：会话列表、详情、fork 恢复

### system_settings

- 表用途：保存 Completion / Embedding provider 配置
- 主要维护模块：`infrastructure/settings`
- 主键：`settings_id`，当前固定为 `global`
- 关键字段：
  - `completion_config`
  - `embedding_config`
  - `created_at / updated_at`
- 典型写入链路：系统设置页保存
- 典型读取链路：所有需要 provider config 的 AI 调用

### template_semantic_indices

- 表用途：保存模板语义索引文本和 embedding 向量
- 主要维护模块：`template_catalog`
- 主键：`template_id`
- 关键字段：
  - `semantic_text`
  - `embedding_vector`
  - `embedding_model`
  - `status`
  - `error_message`
  - `updated_at`
- 典型写入链路：模板更新后标记 stale；系统设置重建索引时写入向量
- 典型读取链路：模板语义匹配

### feedbacks

- 表用途：保存用户反馈
- 主要维护模块：`feedback` supporting router
- 主键：`feedback_id`
- 关键字段：
  - `user_ip`
  - `submitter`
  - `content`
  - `priority`
  - `images`
  - `created_at`
- 典型写入链路：反馈页面提交
- 典型读取链路：当前以后端聚合输出和后续运营处理为主

## 4. 表之间的关键关系

- `report_instances.template_id -> report_templates.template_id`
- `template_instances.report_instance_id -> report_instances.instance_id`
- `report_documents.instance_id -> report_instances.instance_id`
- `scheduled_tasks.source_instance_id -> report_instances.instance_id`
- `scheduled_task_executions.task_id -> scheduled_tasks.task_id`
- `chat_sessions.instance_id -> report_instances.instance_id`
- `template_semantic_indices.template_id -> report_templates.template_id`

当前 ORM 层没有显式声明复杂外键关系，模块依赖和引用关系主要在应用层与 repository 层维护。
