# 通用对话实现

## 1. 模块定位

`contexts/conversation` 负责通用会话容器、消息流水、fork、追问/答复生命周期、场景注册、场景识别、场景分发和 SSE 事件输出。它允许业务场景使用严格类型扩展载荷，但不在本模块定义报告模板、参数模型或 Report DSL。

## 2. 应用服务

`ConversationService` 负责：

- 创建、读取和删除会话。
- 记录用户与系统消息。
- 按来源会话和来源消息 fork 新会话。
- 创建 `ChatContext`，承载当前会话、消息、用户、instruction、问题、答复和请求元信息。
- 按 `reply.sourceChatId` 精确消费一条 `pending` 追问，并将其状态更新为 `replied`。
- 按顺序输出 `status / step_delta / delta / answer / done`。
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

## 4. 上下文与严格模型

`ChatContext` 只包含所有场景都能理解的公共信息：

- `conversationId/chatId/userId`
- `instruction/question`
- `reply.sourceChatId`
- `scenarioKey/previousScenarioKey/scenarioResolution`
- `requestId/apiVersion`

`ChatAsk` 与 `ChatReply` 是通用追问和答复外壳。`status/mode/type/title/text/sourceChatId` 属于通用字段；报告场景的 `parameters/reportContext` 通过 report application 中的严格 DTO 扩展。不得为了扩展新场景把业务载荷退化成无约束 `dict`。

原始 JSON map 只允许在 HTTP 解析、数据库序列化和场景 codec 解码的短暂边界存在。dispatcher 调用 codec 后，业务 handler 必须只接收本场景的严格 command。

`ChatContext` 不持有 `Parameter`、`TemplateInstance` 或 `ReportDsl`。未来智能问数等场景应定义自己的严格 ask/reply 扩展，并复用相同的追问生命周期。

## 5. 持久化边界

- `tbl_conversations` 保存会话容器。
- `tbl_chats` 保存消息流水和每轮 `scenario_key`。
- `tbl_chats.meta.scenario` 保存识别方式、置信度和延续状态，便于诊断。
- 用户身份统一由请求上下文解析。
- 报告实例只记录来源会话和来源消息，不由会话表反向维护单一报告宿主字段。

## 6. 明确不做

- 不直接读写模板仓储。
- 不提取或判断报告参数。
- 不直接组装 Report DSL。
- 不直接生成 Office 文档。
- 不把报告场景的阶段状态提升为通用会话状态。
- 不提供运行时场景热注册或管理 API。
