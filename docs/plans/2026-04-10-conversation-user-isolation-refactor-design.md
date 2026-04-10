# 会话模型、用户隔离与报告归属重构设计

## 1. 目标

本设计用于收敛统一对话、用户隔离和报告归属三类长期存在的模型冲突。

当前主要问题：

- `chat_sessions` 同时承载会话容器、消息流水、任务状态和单实例反向关联，职责过重
- `messages` 以内嵌 JSON 方式保存，不利于检索、追溯、增量迁移和消息级来源锚点表达
- `user_id` 只零散出现在少数表中，无法作为统一数据隔离根
- 报告实例是会话产物之一，但当前又反向挂到会话上，语义不稳定

本轮设计目标：

1. 引入用户镜像表，作为业务数据隔离根
2. 将会话容器与消息流水拆开
3. 将报告来源锚点直接定义到报告实例
4. 明确请求头用户身份契约
5. 形成可迁移、可回填、可兼容历史数据的实施方案

## 2. 目标模型

### 2.1 会话与消息

- `session`
  - 只表示会话容器
  - 保存标题、状态、fork 来源、所属用户
- `message`
  - 表示真实消息流水
  - 同时承载可见消息与隐藏 `context_state`
  - 顺序由 `seq_no` 保证

这里不新增 `dialogue` 表。

原因：

- 真实用户对话经常被其它话题打断
- “一次独立对话”的边界不稳定
- 若强行引入 `dialogue`，实现阶段仍要频繁做拆分/合并决策，反而增加歧义

因此本轮采用两层模型：

- `session -> message`

逻辑上的“某次对话”通过消息锚点、`context_state` 和报告来源字段表达，而不是单独落一张物理表。

### 2.2 用户镜像

- 新增 `tbl_users`
- `id` 直接使用外部用户 ID
- 服务端从请求头 `X-User-Id` 获取身份
- 收到请求时按 `id` 查找或创建镜像记录

### 2.3 报告归属

- `report_instances` 直接记录：
  - `user_id`
  - `source_session_id`
  - `source_message_id`
- 会话不再反向挂 `instance_id`

这意味着：

- 一个会话可以产出多份报告
- 一份报告实例最多有一个来源会话锚点
- 报告实例是会话产物，而不是会话状态字段

## 3. 表结构收敛

### 3.1 新增表

#### `tbl_users`

- `id`
- `display_name`
- `status`
- `profile_json`
- `created_at`
- `updated_at`
- `last_seen_at`

#### `tbl_chat_messages`

- `id`
- `session_id`
- `user_id`
- `role`
- `content`
- `action`
- `meta`
- `seq_no`
- `created_at`

### 3.2 调整表

#### `tbl_chat_sessions`

保留：

- `id`
- `user_id`
- `title`
- `fork_meta`
- `status`
- `created_at`
- `updated_at`

移除：

- `messages`
- `matched_template_id`
- `instance_id`

#### `tbl_report_instances`

新增：

- `user_id`
- `source_session_id`
- `source_message_id`

来源消息语义固定为：

- 生成发生前最后一条可见用户消息

不使用：

- 内部 `confirm_outline_generation` 空消息
- `review_outline` 助手消息

#### `tbl_report_documents`

- 本轮不新增 `user_id`
- 通过 `instance_id -> report_instance.user_id` 间接归属

#### `tbl_template_instances`

- 继续保留 `session_id`
- 不新增业务级 `user_id`
- 在 `update-chat / fork-sources / fork-chat` 中作为历史兼容回退来源

## 4. 用户隔离规则

### 4.1 用户身份来源

统一采用请求头：

```http
X-User-Id: <external-user-id>
```

规则：

- 不信任 body/query 中的 `user_id`
- 业务查询统一以 Header 身份为准
- 服务端负责将 Header 值映射为 `tbl_users.id`

### 4.2 强隔离对象

本轮强制纳入用户隔离的对象：

- 会话
- 消息
- 报告实例
- 定时任务
- 后续报告素材

本轮不单独加 `user_id` 的对象：

- 报告文档
- 内部生成基线

它们通过所属实例间接完成隔离。

### 4.3 模板归属

- 模板仍按系统共享资产处理
- 本轮不做用户私有模板

## 5. 接口与行为影响

### 5.1 会话接口

- 会话列表/详情仍返回 `messages`
- 但 `messages` 改为从 `tbl_chat_messages` 组装
- 会话返回中不再包含：
  - `instance_id`

`matched_template_id` 不再作为会话持久字段。

如后续需要展示当前报告任务上下文，应从最新 `context_state` 派生，而不是写回 `tbl_chat_sessions`。

### 5.2 报告实例接口

新增输出字段：

- `user_id`
- `source_session_id`
- `source_message_id`

### 5.3 恢复与分支

- `update-chat`
- `fork-sources`
- `fork-chat`

统一规则：

1. 优先使用 `report_instances.source_session_id`
2. 若为空，回退 `template_instances.session_id`

## 6. 迁移方案

### 6.1 迁移顺序

1. 新增 `tbl_users`
2. 新增 `tbl_chat_messages`
3. 为 `tbl_report_instances` 增加 `user_id/source_session_id/source_message_id`
4. 将历史 `chat_sessions.messages` 回填至 `tbl_chat_messages`
5. 依据 `chat_sessions.user_id` 回填消息 `user_id`
6. 依据 baseline/session/task 回填实例归属和来源
7. 新代码切换到消息表读写
8. 废弃并移除 `chat_sessions.messages / matched_template_id / instance_id`

### 6.2 历史回填规则

#### 历史消息

- `seq_no` 按原 JSON 数组顺序生成
- 保留原 `message_id`
- 包括隐藏 `context_state` 消息

#### 历史实例 `user_id`

优先级：

1. 来源会话的 `user_id`
2. 来源定时任务的 `user_id`
3. 无法判定时记为迁移异常，人工处理

不采用：

- 默认回填 `default`

#### 历史实例 `source_session_id`

优先级：

1. 已存在 baseline 的 `template_instances.session_id`
2. 无 baseline 时为空

#### 历史实例 `source_message_id`

- 历史数据允许为空
- 不做不可靠猜测性回填

## 7. 验收基线

1. 同一用户只能看到自己的会话、消息、实例、任务
2. 同一会话可生成多份报告，不再受单实例反向挂载限制
3. 对话生成的报告必须带：
   - `user_id`
   - `source_session_id`
   - `source_message_id`
4. 定时任务生成的报告必须带 `user_id`，但来源会话字段为空
5. 文档访问必须通过实例归属校验用户，不允许裸文档跨用户访问
6. 旧会话消息迁移后顺序和 `message_id` 保持一致

## 8. 本轮不做

- 用户私有模板
- 独立 `dialogue` 表
- 文档表直接增加 `user_id`
- 基线表直接增加 `user_id`
- 从历史消息中推断并强行补齐全部 `source_message_id`
