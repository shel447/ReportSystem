# 内部消息契约

本契约描述 ReportSystem 进程内 MessageCenter 的消息包络，不是公开 HTTP API。

| 字段 | 类型 | 说明 |
|---|---|---|
| `messageId` | string | 全局唯一消息标识 |
| `kind` | `event \| command` | 消息语义 |
| `channel` | `interaction \| domain \| observability \| control` | 消息频道 |
| `topic` | string | 稳定主题 |
| `source` | string | 生产方 |
| `occurredAt` | number | Unix 时间戳 |
| `partitionKey` | string | MessageCenter 保序分区 |
| `correlationId` | string? | 同一业务链路关联标识 |
| `causationId` | string? | 直接原因消息标识 |
| `sequence` | integer | MessageCenter 分区内最终顺序 |
| `sourceSequence` | integer? | 生产方内部顺序 |
| `payload` | typed object | 主题对应的强类型载荷 |

标准主题：

- `interaction.status/step/delta/ask/answer/error/done`
- `observability.audit.requested`
- `observability.metrics.recorded`
- `observability.consumer.failed`
- `observability.command.unhandled`
- `control.agentflow.cancel`
- `control.agentflow.terminate`
- `domain.<context>.<fact>`

Command 不允许广播订阅。发送 command 返回 `queued + commandId`，执行结果由目标处理方发布后续 event；目标不存在时由 MessageCenter 发布 `observability.command.unhandled`。

## Interaction 载荷

所有 `interaction.*` 主题使用统一 `InteractionEvent`，其字段为 `eventType/status/step/delta/ask/answer/error/toolCall/toolResult/refusal/checkpoint/sourceSubflow`。`step` 使用 `InteractionStep`，包含 `stepId/title/status/detail/parentStepId/stepPath`。

`InteractionEvent` 不属于 AgentFlow。Flow 事件由 `FlowEventProcessor` 转换后发布，非 Flow 业务模块也可以直接发布，conversation 对两类生产方使用同一套 SSE 与持久化投影。
