# Agent Flow 公共流程框架

`shared/agentflow` 是后端公共基础模块，不属于 `conversation`、`report` 或 `data_analysis` 任一业务 Context。它负责流程编排、事件发布、工具调用、提示词组装、checkpoint、hook、取消、运行中输入和拒答。

## 分层

- Low level：`FlowGraph / FlowNode / FlowEdge / FlowContext`。用于表达顺序、条件、循环、并行分支、汇合、human-in-loop 和运行中追加后续分支。
- High level：`SequentialFlow / ReactFlow`。用于快速组织常见 agent 流程；后续新模式也应编译为 low level graph。
- Runtime：`InMemoryFlowRuntime`。首版只保证单进程实时运行；checkpoint 通过 `CheckpointSaver` 抽象保存，默认实现为 `InMemoryCheckpointSaver`。

## 事件模型

流程节点通过 `FlowContext` 发出统一事件：

- `emit_step()`：阶段进展。
- `emit_delta()`：业务增量，例如报告 DSL 片段。
- `emit_answer()`：最终结果。
- `emit_error()`：错误。
- `call_tool()`：发出 `tool_call/tool_result` 事件并返回工具输出。
- `save_checkpoint()`：保存 checkpoint 并发出 checkpoint 事件。
- `refuse()`：发出拒答结果并结束流程。
- `request_terminate()`：由系统主动终止流程。

`conversation` 订阅这些事件并投影为 `/chat` 响应。内部 `tool_call/tool_result/checkpoint` 事件对外按 `step_delta` 透出，并携带 `toolCall/toolResult/checkpoint` 可选字段，避免前端必须支持新的 `eventType`。

## Tool 与 Prompt

- 工具必须先注册到 `ToolRegistry`，节点只能通过 `FlowContext.call_tool(name, arguments)` 调用。
- 工具执行结果统一封装为 `ToolResult`；失败时节点收到异常，流程发出可追踪事件。
- 提示词通过 `PromptTemplate` 和 `PromptAssembler` 组装；框架不绑定具体 LLM gateway。

## Hook

Runtime 可配置全局 hook，节点也可配置局部 hook。Hook 支持：

- `before_node / after_node`
- `on_error`
- `before_tool / after_tool`

Hook 返回 `HookDecision` 控制流程：`continue`、`skip`、`terminate`、`refuse`。业务规则应优先写在业务 Context 中，hook 适合做横切能力，例如审计、调试、限流、统一安全拦截。

## Checkpoint

`CheckpointSaver` 是唯一持久化接口：

- `save(checkpoint)`
- `list(run_id)`
- `latest(run_id)`

首版使用 `InMemoryCheckpointSaver`。后续若需要数据库恢复，只替换 saver，不改变业务节点和 `conversation` 接入方式。

## 动态节点

运行中节点可以调用 `add_node()` 和 `add_edge()` 追加后续分支：

- 只能追加尚未执行的新节点。
- 边的 source 可以是当前节点或未完成节点。
- 不允许指向已完成节点，不允许修改已完成部分，也不重跑已完成节点。
- 调度器在当前节点完成后重新读取 outgoing edges，因此新分支会自然进入后续执行。

## 当前限制

- Runtime 为内存态，不支持服务重启后的恢复。
- 取消是协作式取消，节点和外部调用边界需要主动检查信号。
- 不支持分布式调度、跨进程事件订阅或运行时删除节点。
- checkpoint 保存状态快照，不等价于完整执行恢复。
