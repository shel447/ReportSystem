# 通用对话实现

## 1. 模块定位

`contexts/conversation` 负责通用会话容器、消息流水、fork 和 SSE 事件输出。它允许业务场景扩展载荷，但不在本模块定义报告模板、参数模型或 Report DSL。

## 2. 应用服务

`ConversationService` 负责：

- 创建、读取和删除会话。
- 记录用户与系统消息。
- 按 `sourceConversationId/sourceChatId` fork 新会话。
- 按顺序输出 `status / step_delta / delta / answer / done`。
- 将业务场景 instruction 分发到对应 handler。

报告生成 instruction 委托给 `report` context 处理。参数提取、补参、诉求确认、模板实例更新和报告冻结的实现规则见 [报告生成实现](../report-generation/README.md)。

## 3. 持久化边界

- `tbl_conversations` 保存会话容器。
- `tbl_chats` 保存消息流水。
- 用户身份统一由请求上下文解析。
- 报告实例只记录来源会话和来源消息，不由会话表反向维护单一报告宿主字段。

## 4. 明确不做

- 不直接读写模板仓储。
- 不直接组装 Report DSL。
- 不直接生成 Office 文档。
- 不把报告场景的阶段状态提升为通用会话状态。
