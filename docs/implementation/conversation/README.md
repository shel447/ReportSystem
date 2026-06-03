# 通用对话实现

## 1. 模块定位

`contexts/conversation` 负责通用会话、追问/答复生命周期、场景注册、场景识别、场景分发、安全检查和 SSE 事件输出。会话事实源由 AgentCore 托管。它允许业务场景使用严格类型扩展载荷，但不定义报告模板、参数模型或 Report DSL。

运行中流程由 `shared/agentflow` 承载。conversation 只负责启动流程、订阅事件，并把 `step_delta/delta/answer/error` 投影成 `/chat` 响应。

## 2. 应用服务

`ConversationService` 负责：

- 通过 AgentCore 创建、读取和归档会话。
- 使用 `chat/import` 的 upsert 语义更新已消费追问。
- 创建 `ChatContext`，承载当前会话、消息、用户、instruction、问题、答复和请求元信息。
- 按 `reply.sourceChatId` 精确消费一条 `pending` 追问，并将其状态更新为 `replied`。
- 对同步场景直接返回 `ChatResponse`。
- 对 Flow 场景启动 `InMemoryFlowRuntime`，按顺序输出 `status / step_delta / delta / ask / answer / error / done`。
- 接收运行中的取消和补充输入信号，并转发给 `shared/agentflow`。
- 将显式 instruction 或识别出的业务场景分发到对应场景 handler。

## 3. 场景注册、识别和分发

系统内其他业务模块在启动装配阶段向 conversation 注册场景。单个场景声明：

- 稳定 `scenarioKey`
- 展示名称和业务描述
- 支持的 instruction 集合
- 默认 instruction
- 是否允许多轮延续
- 用于本地识别的关键词和示例
- 场景 codec：把入口 JSON 短暂字段解码为本场景的严格 command
- 强类型场景 handler：只接收本场景 command，不直接解释裸 JSON

场景分发顺序固定为：

1. 请求显式携带 instruction 时精确匹配注册场景。
2. 请求回复某条追问时，优先沿用 `reply.sourceChatId` 对应消息的场景。
3. 普通自然语言输入优先尝试延续上一轮 `waiting_user` 场景。
4. 无法延续时，由统一识别器根据所有注册场景的声明做本地可解释评分。
5. 仍无法可靠识别时，返回通用 `clarify_scenario` 追问。

第一版识别器不调用外部模型；后续可通过语义匹配接口接入 embedding 或 LLM。报告场景通过系统装配层的 codec 和 handler 注册，参数提取、补参、诉求确认、模板实例更新和报告冻结的实现规则见 [报告生成实现](../report-generation/README.md)。

场景 handler 可以返回一次性 `ScenarioResult`，也可以返回 Flow。返回 Flow 时，conversation 不理解业务节点，只消费公共事件。

## 4. Agent Flow 边界

`shared/agentflow` 分为两层：

- low level：`FlowGraph / FlowNode / FlowEdge / FlowContext`，表达顺序、条件边、循环、并行分支、汇合和 human-in-loop 节点。
- high level：`SequentialFlow` 和 `ReactFlow`，用于快速组织常见 agent 流程。

Agent Flow 还提供工具调用、提示词组装、节点 hook、checkpoint、拒答和系统主动终止接口。conversation 不直接调用这些接口，只订阅事件并投影为 `/chat` 响应。

首版运行态只保存在内存中，checkpoint 也使用内存 saver，不做服务重启恢复。取消采用协作式信号，节点和外部调用边界主动检查后停止，不强制杀死底层线程或 HTTP 请求。

## 5. 上下文与严格模型

`ChatContext` 只包含所有场景都能理解的公共信息：

- `conversationId/chatId/userId`
- `instruction/question`
- `reply.sourceChatId`
- `scenarioKey/previousScenarioKey/scenarioResolution`
- `requestId/apiVersion`

`ChatAsk` 与 `ChatReply` 是通用追问和答复外壳。`status/mode/type/title/text/sourceChatId` 属于通用字段；报告场景的 `parameters/reportContext` 通过 report application 中的严格 DTO 扩展。不得为了扩展新场景把业务载荷退化成无约束 `dict`。

原始 JSON map 只允许在 HTTP 解析、数据库序列化和场景 codec 解码的短暂边界存在。dispatcher 调用 codec 后，业务 handler 必须只接收本场景的严格 command。

`ChatContext` 不持有 `Parameter`、`TemplateInstance` 或 `ReportDsl`。未来智能问数等场景应定义自己的严格 ask/reply 扩展，并复用相同的追问生命周期。

## 6. 持久化边界

- AgentCore 是会话和轮次的唯一事实源。
- `chat/import` 保存完整 `ChatResp` 与 `meta.scenario`，用于恢复场景轨迹。
- 本地业务库不保存 `tbl_conversations/tbl_chats` 投影。
- 用户身份统一由请求上下文解析。
- 正式业务请求必须携带由上游网关注入的非空 `X-User-Id`；conversation 不维护用户资料。
- 报告实例只记录来源会话和来源消息，不由会话表反向维护单一报告宿主字段。

## 7. 明确不做

- 不直接读写模板仓储。
- 不提取或判断报告参数。
- 不直接组装 Report DSL。
- 不直接生成 Office 文档。
- 不把报告场景的阶段状态提升为通用会话状态。
- 不提供运行时场景热注册或管理 API。
- AgentCore 暂未提供删除和 fork 契约，因此对应公开路由返回 `501 capability_not_available`。
