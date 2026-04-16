# 统一对话流式与报告接口对齐迁移计划

## 1. 目标与范围

本计划用于将当前实现中的业务流程与接口定义，对齐到最新《对话制报告接口串联案例（design_chat_report_stream_case.md）》目标口径。

本轮目标：

- 统一对话主入口为 `POST /rest/chatbi/v1/chat`，按 `instruction` 路由能力。
- 统一报告查询与编辑链路：`GET /rest/chatbi/v1/reports/{reportId}` + `POST /rest/chatbi/v1/reports/{reportId}/edit-stream`。
- 统一流式响应骨架：`status + steps + delta + ask + answer`。
- 对齐“模板匹配 -> 参数追问 -> 参数确认 -> 诉求确认 -> 生成报告 -> 编辑诉求重生成”完整流程。

不在本轮范围：

- 新增业务能力（如新模板类型、新生成算法）。
- 变更既定数据隔离策略（`X-User-Id` 体系保持不变）。

## 2. 对齐基线（Source of Truth）

本次迁移以以下文档为目标基线：

- `design/design_chat_report_stream_case.md`（目标态主流程与接口）
- `design/design_api.md`（系统全量 API 索引与约束）
- `design/implementation/conversation.md`（会话编排实现口径）
- `design/implementation/runtime_sequences.md`（关键时序）

对齐原则：

- 业务语义以 `design_chat_report_stream_case.md` 为主。
- 全局接口目录以 `design_api.md` 为准，并反映 stream-case 契约。
- 模块实现文档只描述“已对齐后的实现”，不保留旧口径混写。

## 3. 当前差异快照（现状 vs 目标）

| 主题 | 当前现状 | 目标设计 | 迁移影响 |
| --- | --- | --- | --- |
| `/chat` 交互模式 | 同步 JSON 请求/响应 | 单接口流式 SSE（报告链路全覆盖） | Router、Service、前端消费模型均需调整 |
| `/chat` 入参 | `message/session_id/param_id/command/...` | `conversationId/chatId/instruction/question/reply/command` | 入参模型与状态机事件需要重映射 |
| 报告详情接口 | 以 `/instances/{id}` 为主 | `/reports/{reportId}` 返回 `template_instance + generated_content` | 需要新增报告视图接口或做路径别名 |
| 编辑诉求并重生成 | 现有为命令式回合 | `POST /reports/{id}/edit-stream`（SSE） | 需要定义 patch 契约与增量输出 |
| 流式结构 | 尚无统一 `steps/delta` 协议 | 统一骨架 + ask/answer 互斥 | 需要会话编排输出标准化 |
| 字段命名风格 | 内外部混用 snake_case/camelCase | 外部契约统一 camelCase | DTO 层需做显式映射 |

## 4. 迁移总策略

采用“契约先行 + 双栈兼容 + 分阶段切流”策略：

1. 先冻结目标契约（文档、示例、状态枚举、字段命名）。
2. 再引入兼容层，支持新老请求并存，保证前端可渐进迁移。
3. 最后收口旧字段/旧路径，完成单口径上线。

## 5. 分阶段实施计划

### Phase 0：契约冻结（设计文档收敛）

交付物：

- 统一 `status` 枚举与终态文案（建议统一为 `running|waiting_user|finished|failed|aborted`）。
- 统一 `answer` 字段命名（建议统一 `reportId/templateInstanceId`，去除 snake_case 混用）。
- 明确 `ask` 与 `answer` 互斥规则及异常场景示例。
- 明确 `patches` 协议（操作类型、路径规则、失败语义）。

涉及文档：

- `design/design_chat_report_stream_case.md`
- `design/design_api.md`

完成标准：

- 两份文档无同一字段不同命名、同一状态不同枚举的冲突。

### Phase 1：接口层兼容改造（不改业务语义）

交付物：

- `POST /chat` 支持新请求体（`conversationId/chatId/instruction/question/reply/command`）。
- 保留旧请求字段兼容映射（`message/session_id/param_*` -> 新语义）。
- 支持 SSE 输出骨架；旧调用方可继续走原同步返回（短期兼容）。

建议映射：

- `session_id` -> `conversationId`
- `message` -> `question`
- `command`（字符串）-> `command.name`
- `param_id + param_value/param_values` -> `reply(type=fill_params).parameters`

完成标准：

- 新请求体可贯通首轮匹配、补参、确认生成三阶段。

### Phase 2：会话状态机与报告流程对齐

交付物：

- 统一状态推进：模板匹配 -> 参数追问 -> 参数确认 -> 诉求确认 -> 生成中 -> 生成完成。
- `interaction_mode=form|chat` 在 `ask` 中稳定体现。
- 对话上下文中的“当前等待参数”与“诉求确认中”状态可恢复、可重入。

完成标准：

- 同一会话内多轮补参与确认生成符合 stream-case 示例。

### Phase 3：报告视图接口对齐

交付物：

- 新增或重定向 `GET /rest/chatbi/v1/reports/{reportId}`。
- 返回体稳定包含：`template_instance` + `generated_content`。
- `/instances/{id}` 保持兼容（管理视角），但前台流程切到 `/reports/{id}`。

完成标准：

- 聊天生成完成后可直接跳转并查询报告详情（新口径）。

### Phase 4：编辑诉求流式重生成对齐

交付物：

- `POST /rest/chatbi/v1/reports/{reportId}/edit-stream`。
- 接收 `editMode + patches`，按受影响节点做局部重算与重生成。
- SSE 输出 `steps + delta + answer(report_updated)`。

完成标准：

- 修改诉求后只重生成受影响章节，`instance_meta.revision` 递增。

### Phase 5：文档与实现说明同步

交付物：

- `design/implementation/conversation.md` 与 `runtime_sequences.md` 更新为新链路。
- 清理旧命令名残留（如 `prepare_outline_review/confirm_outline_generation` 仅保留内部兼容说明，不再作为对外主契约）。

完成标准：

- 模块文档仅描述目标态主链路，兼容逻辑集中在“迁移兼容”段。

### Phase 6：收口与下线旧口径

交付物：

- 前端全面切到新请求/响应模型。
- 下线旧字段输出与旧路径依赖（保留最小回退开关）。

完成标准：

- API 文档、前端调用、后端行为三者一致，无双口径。

## 6. 接口迁移映射清单

### 6.1 `/chat` 请求映射

| 旧字段 | 新字段 | 说明 |
| --- | --- | --- |
| `session_id` | `conversationId` | 会话标识对齐 |
| `message` | `question` | 用户输入文本 |
| `preferred_capability` | `instruction` | 报告链路固定 `generate_report` |
| `param_id/param_value/param_values` | `reply.parameters` | 参数提交统一挂载到 `reply` |
| `command` | `command.name` | 命令改为对象表达 |
| `outline_override` | `patches`（edit-stream） | 诉求修改迁移到报告编辑接口 |

### 6.2 `/chat` 响应映射

| 旧字段 | 新字段 | 说明 |
| --- | --- | --- |
| `reply` | `ask/answer` | 中间态与终态分离 |
| `action` | `ask/answer` + `steps` | 行为语义改为结构化事件 |
| `messages` | SSE 连续事件 | 不再一次性回传整段消息历史 |

### 6.3 报告接口路径映射

| 当前路径 | 目标路径 | 迁移策略 |
| --- | --- | --- |
| `GET /instances/{id}` | `GET /reports/{reportId}` | 新增别名或聚合视图，逐步切流 |
| （无） | `POST /reports/{reportId}/edit-stream` | 新增接口，作为诉求编辑唯一入口 |

## 7. 验收与回归测试计划

必须覆盖以下用例：

1. 首轮自然语言输入后模板匹配，并进入参数追问（`ask.mode=form|chat`）。
2. 混合补参（表单 + 自然语言）后进入统一参数确认。
3. 确认生成后持续收到 SSE `steps/status/delta`，终态返回 `report_ready`。
4. 查询 `GET /reports/{id}` 返回模板实例与生成内容。
5. 编辑诉求调用 `edit-stream`，仅受影响章节被更新，返回 `report_updated`。
6. 兼容请求（旧字段）仍可完成主流程，且不会破坏 `X-User-Id` 隔离。

## 8. 风险与缓解

主要风险：

- 新旧字段并存导致状态分支复杂、测试覆盖不足。
- SSE 引入后前端断线重连、重复事件处理不一致。
- `/instances` 与 `/reports` 双路径并存期间产生语义漂移。

缓解策略：

- 先做契约测试，再做实现切换。
- 增加事件去重键（建议 `chatId + stepId/eventSeq`）与终态幂等处理。
- 设定明确下线窗口，避免双口径长期共存。

## 9. 建议排期（设计到联调）

- 第 1 周：Phase 0-1（契约冻结 + 接口兼容入口）
- 第 2 周：Phase 2-3（状态机对齐 + 报告查询路径切换）
- 第 3 周：Phase 4-5（编辑流式重生成 + 文档同步）
- 第 4 周：Phase 6（灰度、回归、下线旧口径）

---

该计划可直接作为开发与联调执行清单；建议由后端、前端、测试三方共用同一验收用例集推进。
