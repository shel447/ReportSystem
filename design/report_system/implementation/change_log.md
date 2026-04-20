# 实现设计 Change Log

本文件记录 `design/report_system/implementation/` 维度的实现设计变更。

记录原则：

- 只记录会影响实现分层、运行时职责、数据流或验证策略的设计实现调整
- 聚焦“实现上怎么落、改了哪些实现约束、验证如何变化”
- 不替代代码提交记录；业务方案层变更请见 [../../change_log.md](../../change_log.md)

## 2026-04-19 scoped 参数运行时修复

- 关联提交：
  - GitHub PR `#15`
  - merge commit `e8e9371`
- 背景问题：
  - 代码级 review 暴露出 3 个实现缺口：
    - 对话服务只按模板根参数做抽取和缺参判断
    - 前端只更新顶层 `templateInstance.parameters`
    - `multi=true` 的参数在 UI 上仍被降级为单值输入
- 实现设计调整：
  - `conversation` 应用服务改为递归收集模板根、目录、章节三层参数定义，并在以下环节统一复用：
    - 首轮问题参数抽取
    - 当前实例参数值合并
    - 缺参判断
    - ask 参数回显
  - `report_runtime.domain.services` 增加递归参数收集能力，用于：
    - 计算整棵实例树的有效参数值
    - 在实例物化时把 scoped 参数正确写回目录与章节节点
    - 在 `parameterConfirmation` 中按整棵实例树判断缺参
  - `ChatPage` 前端交互改为：
    - `multi=true + free_text` 使用多行输入控件
    - `multi=true + enum/dynamic` 使用多选控件
    - 提交时同步刷新嵌套在 `catalogs/sections` 下的 scoped 参数状态
- 受影响的实现设计主题：
  - [统一对话实现.md](统一对话实现.md)
  - [报告运行时实现.md](报告运行时实现.md)
  - [总体实现架构.md](总体实现架构.md)
- 验证要求更新：
  - 新增后端测试，锁住 scoped 参数抽取与缺参判断
  - 新增前端测试，锁住多值参数交互与模板实例嵌套参数同步
  - 全量验证基线维持：
    - `python -m pytest src/backend/tests -q`
    - `npm test`
    - `npm run build`
- 后续约束：
  - 从本次开始，所有实现设计调整都统一追加到本文件，不再只散落在专题实现文档中。

## 2026-04-19 `ask.status` 对话级锁定标识

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-04-19 `ask.status` 对话级锁定标识”
- 实现设计调整：
  - `conversation` 的 `Ask` 载荷统一增加 `status`
  - `ConversationService` 在生成新追问时固定写入 `ask.status = pending`
  - 当用户成功提交 `reply` 后，由聊天仓储回写最近一条待处理追问消息，把其 `ask.status` 刷新为 `replied`
  - 前端聊天页只依据 `ask.status` 控制当前追问是否仍可编辑，不再用 `parameterConfirmation.confirmed` 反推消息锁定态
- 验证要求：
  - 后端测试锁住：
    - `POST /chat` 返回的 `ask.status`
    - 历史追问在回复后被刷新为 `replied`
  - 前端测试锁住：
    - `ask.status = replied` 时不再展示可提交编辑器

## 2026-04-19 `/chat` 流式报告增量 `delta`

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-04-19 `/chat` 流式报告增量 `delta`”
- 实现设计调整：
  - `chat` 路由的 SSE 输出改为多事件包络，而不是单次透传完整 `ChatResponse`
  - 流式事件统一使用现有 `message` 通道，顶层增加正式 `ChatStreamEvent` 字段：
    - `eventType`
    - `sequence`
    - `status`
    - `delta?`
    - `answer?`
    - `ask?`
  - `delta.action` 首版只实现：
    - `init_report`
    - `add_catalog`
    - `add_section`
  - `delta` 仅由流式 `/chat` 产生，不进入非流式 `ChatResponse`、`TemplateInstance`、`ReportInstance` 或 `/reports/{reportId}`
  - 前端聊天页新增三条并行通道处理：
    - `steps`
    - `delta`
    - 最终 `answer`
- 验证要求：
  - 后端 SSE 契约测试锁住 `delta` 事件和最终 `answer/done`
  - 前端测试锁住 SSE 解析与增量渲染

## 2026-04-19 表定义与运行时数据库分离

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-04-19 表定义与运行时数据库分离”
- 实现设计调整：
  - 运行时唯一建表来源保持为 `src/backend/infrastructure/persistence/models.py + Base.metadata.create_all(...)`
  - `src/backend/infrastructure/persistence/schema_init.sql` 作为受版本管理的初始化稿，职责仅限初始化、审阅和结构比对
  - `src/backend/report_system.db` 明确降级为本地运行时文件，不再作为设计或结构基线
- 验证要求：
  - 新增测试锁住 `schema_init.sql` 对当前 ORM 表集合的覆盖
  - 新增测试锁住 `.gitignore` 对 `src/backend/report_system.db` 的忽略约束

## 2026-04-19 后端本地 Schema 镜像清理

- 背景问题：
  - `src/backend` 根目录仍保留过期的模板 schema、模板示例和报告 DSL schema 镜像文件。
  - 运行时代码与设计文档同时引用 `src/backend/*.json` 和 `design/report_system/schemas/*.json`，形成双轨定义。
- 实现设计调整：
  - 删除 `src/backend` 根目录下全部历史 JSON schema/示例镜像文件。
  - 后端运行时如需校验 `Report DSL`，统一从 `design/report_system/schemas/report-dsl.schema.json` 读取。
  - 实现文档与设计文档中的 schema 引用统一收口到 `design/report_system/schemas/*`，不再把 `src/backend/*.json` 作为正式契约来源。
- 受影响的实现设计主题：
  - [README.md](README.md)
  - [报告运行时实现.md](报告运行时实现.md)
  - [持久化与表结构实现.md](持久化与表结构实现.md)
- 验证要求：
  - 后端根目录不再保留任何本地 JSON schema 镜像文件。
  - 架构测试锁住 `src/backend/*.json` 清零，防止后续再次引入双轨 schema。

## 2026-04-19 `reply.sourceChatId` 精确回写

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中 `reply.sourceChatId` 要求
- 实现设计调整：
  - `chat` 路由的 `ReplyPayload` 正式增加必填 `sourceChatId`
  - `ConversationService` 不再按“最近一条待回复 ask”做隐式猜测，而是要求 `fill_params`、`confirm_params` 都显式携带 `sourceChatId`
  - 聊天仓储按 `conversation_id + user_id + source_chat_id` 精确定位 assistant 追问消息，并仅在该消息仍为 `ask.status = pending` 时回写为 `replied`
  - 前端聊天页提交 `reply` 时，固定使用当前追问消息自身的 `chatId` 回填 `sourceChatId`
- 受影响的实现设计主题：
  - [统一对话实现.md](统一对话实现.md)
  - [前端实现.md](前端实现.md)
- 验证要求：
  - 后端接口测试锁住 `reply.sourceChatId` 为必填
  - 后端会话测试锁住：只回写 `sourceChatId` 指向的那条追问消息
  - 前端测试锁住：提交 `reply` 时必须带上 `sourceChatId`

## 2026-04-20 `ParameterValue.label` 与 `Reply.parameters` 精简回填

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-04-20 `ParameterValue.label` 与 `Reply.parameters` 精简回填”
- 实现设计调整：
  - `TemplateParameter.values`、动态参数候选值、模板实例参数值三元组统一收敛为 `{label, value, query}`
  - 运行时不再读取或生成 `display` 字段；占位符默认展示通道也从 `display` 切到 `label`
  - `chat` 路由的 `ReplyPayload.parameters` 正式改为 `Record<parameterId, Scalar[]>`
  - 前端提交 `fill_params / confirm_params` 时，只回传参数值映射；服务端基于当前 `TemplateInstance` 中的参数定义与现值，重建新的参数运行态
  - `fill_params` 允许只提交本轮修改子集；`confirm_params` 仍要求 `reportContext.templateInstance` 中体现完整有效参数集
- 受影响的实现设计主题：
  - [统一对话实现.md](统一对话实现.md)
  - [报告运行时实现.md](报告运行时实现.md)
  - [前端实现.md](前端实现.md)
  - [模板目录实现.md](模板目录实现.md)
- 验证要求：
  - 后端测试锁住参数抽取、动态参数解析、`reply.parameters` 路由契约
  - 前端测试锁住 `fill_params` 提交的值映射载荷
  - 搜索确认生产代码不再依赖 `display` 作为正式参数值字段

## 2026-04-20 `composite_table` 模板正式落地

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-04-20 `CompositeTable` 模板正式支持”
- 实现设计调整：
  - 模板前端类型和后端运行时正式接受 `section.content.presentation.blocks[].type = composite_table`
  - `report_runtime` 在 `BuildReportDslService` 中新增 `composite_table -> CompositeTable` 编译规则
  - `query part` 编译为普通数据子表；`summary part` 编译为无表头的静态总结子表
  - `CompositeTable` 只作为 `Report DSL` 组件出现，不单独写回模板实例外的旁路结构
- 受影响的实现设计主题：
  - [模板目录实现.md](模板目录实现.md)
  - [报告运行时实现.md](报告运行时实现.md)
  - [前端实现.md](前端实现.md)
- 验证要求：
  - 后端测试锁住 `composite_table` 模板块成功编译为 DSL `compositeTable`
  - 前端类型与编辑态允许保留 `parts[]` 结构，不再把该 block 视为非法类型

## 2026-04-20 `TemplateInstance.section.content` 与复合表 part 运行态

- 对应设计变更：
  - [../../change_log.md](../../change_log.md) 中“2026-04-20 `TemplateInstance` 正式承载 `CompositeTable` 实例态”
- 实现设计调整：
  - `TemplateInstance.section` 正式补齐 `content`，并保持与模板 `section.content` 同构
  - `instantiate_template_instance` 在实例化章节时，不再只构造 `outline + runtimeContext`，而是同步物化 `section.content.datasets/presentation.blocks`
  - `composite_table.parts[]` 在实例态保留原顺序与结构；`query part`、`summary part` 统一补最小 `runtimeContext`
  - 前端 `TemplateInstance` 类型与报告详情页同步接受并展示 `section.content`
  - `template-instance.schema.json` 与 `template-instance.example.json` 同步收口，保证设计资料包内部自洽
- 受影响的实现设计主题：
  - [统一对话实现.md](统一对话实现.md)
  - [报告运行时实现.md](报告运行时实现.md)
  - [前端实现.md](前端实现.md)
- 验证要求：
  - 后端测试锁住 `TemplateInstance.section.content` 不丢失
  - 后端测试锁住 `query/summary part.runtimeContext` 最小字段
  - 前端测试锁住报告详情页能读取模板实例中的内容块信息
