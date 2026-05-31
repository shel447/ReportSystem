# 通用对话实现

## 1. 模块定位

`contexts/conversation` 负责通用会话容器、消息流水、fork、追问/答复生命周期和 SSE 事件输出。它允许业务场景使用严格类型扩展载荷，但不在本模块定义报告模板、参数模型或 Report DSL。

## 2. 应用服务

`ConversationService` 负责：

- 创建、读取和删除会话。
- 记录用户与系统消息。
- 按来源会话和来源消息 fork 新会话。
- 创建 `ChatContext`，承载当前会话、消息、用户、instruction、问题、答复和请求元信息。
- 按 `reply.sourceChatId` 精确消费一条 `pending` 追问，并将其状态更新为 `replied`。
- 按顺序输出 `status / step_delta / delta / answer / done`。
- 将业务场景 instruction 分发到对应场景应用服务。

报告生成 instruction 通过 `report` context 的 `ReportService.chat()` 总入口委托给内部场景编排。参数提取、补参、诉求确认、模板实例更新和报告冻结的实现规则见 [报告生成实现](../report-generation/README.md)。

## 3. 上下文与严格模型

`ChatContext` 只包含所有场景都能理解的公共信息：

- `conversationId/chatId/userId`
- `instruction/question`
- `reply.sourceChatId`
- `requestId/apiVersion`

`ChatAsk` 与 `ChatReply` 是通用追问和答复外壳。`status/mode/type/title/text/sourceChatId` 属于通用字段；报告场景的 `parameters/reportContext` 通过 report application 中的严格 DTO 扩展。不得为了扩展新场景把业务载荷退化成无约束 `dict`。

`ChatContext` 不持有 `Parameter`、`TemplateInstance` 或 `ReportDsl`。未来智能问数等场景应定义自己的严格 ask/reply 扩展，并复用相同的追问生命周期。

## 4. 持久化边界

- `tbl_conversations` 保存会话容器。
- `tbl_chats` 保存消息流水。
- 用户身份统一由请求上下文解析。
- 报告实例只记录来源会话和来源消息，不由会话表反向维护单一报告宿主字段。

## 5. 明确不做

- 不直接读写模板仓储。
- 不提取或判断报告参数。
- 不直接组装 Report DSL。
- 不直接生成 Office 文档。
- 不把报告场景的阶段状态提升为通用会话状态。
