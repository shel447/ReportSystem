# Agent Flow 流程拼装 Skill

当你需要为 ReportSystem 新增或验证一个对话式业务流程时，使用本 Skill。目标是快速把诉求拼成可运行的 `shared/agentflow` 流程，并能通过 `/chat` 实时返回进展、增量、最终答案、错误、取消和运行中输入。

## 选择流程形态

1. 简单固定步骤：使用 `SequentialFlow`。
2. 需要 reason / act / observe / decide 循环：使用 `ReactFlow`。
3. 需要条件分支、并行、汇合、动态追加节点：直接构造 `FlowGraph`。

不要把业务状态放进 `conversation`。业务 Context 只通过场景 handler 返回 Flow，conversation 只启动 Flow、订阅事件并投影为 `/chat` 响应。

## 节点编写规范

节点函数只接收 `FlowContext`：

```python
def node(context):
    context.emit_step(code="report.parameters", title="解析参数")
    context.check_cancelled()
    context.state["parameters"] = {"scope": "hq"}
```

节点可以使用：

- `emit_step()`：进度。
- `emit_delta()`：局部业务变更。
- `emit_answer()`：最终结果。
- `wait_for_input()`：human-in-loop。
- `call_tool()`：工具调用。
- `render_prompt()`：提示词组装。
- `save_checkpoint()`：保存 checkpoint。
- `refuse()`：拒答并结束。
- `request_terminate()`：系统主动终止。
- `add_node()/add_edge()`：运行中追加后续分支。

## 工具调用

工具先注册：

```python
registry = ToolRegistry([
    ToolSpec(name="query", handler=lambda args: {"rows": []}),
])
runtime = InMemoryFlowRuntime(tool_registry=registry)
```

节点调用：

```python
rows = context.call_tool("query", {"sql": "select 1"})
```

工具事件会自动进入 `/chat` SSE，前端可以把它当作进度调试信息展示。

## 提示词组装

```python
template = PromptTemplate(
    name="summary",
    messages=[
        PromptMessage(role="system", content="你是{role}"),
        PromptMessage(role="user", content="总结{topic}"),
    ],
)
messages = context.render_prompt(template, {"role": "报告助手", "topic": "网络日报"})
```

Prompt 组装不调用 LLM。LLM 调用应作为业务 gateway 或 tool 单独注入。

## Hook

Hook 适合做横切逻辑：

```python
class GuardHook:
    def before_node(self, hook_context):
        if hook_context.state.get("blocked"):
            return HookDecision.refuse("输入不满足安全要求")
        return HookDecision.continue_()
```

优先使用 hook 做审计、安全、调试和限流，不要把具体报告参数规则写进 hook。

## Checkpoint

首版使用内存 checkpoint：

```python
saver = InMemoryCheckpointSaver()
runtime = InMemoryFlowRuntime(checkpoint_saver=saver)
```

节点中：

```python
context.save_checkpoint(reason="after_dataset")
```

后续接数据库时只替换 saver，不改节点代码。

## 动态追加分支

只追加后续分支，不修改已完成节点：

```python
def plan_sections(context):
    for section_id in context.state["section_ids"]:
        context.add_node(FlowNode(id=f"generate_{section_id}", handler=make_section_node(section_id)))
        context.add_edge(FlowEdge(source="plan_sections", target=f"generate_{section_id}"))
```

动态节点 id 必须唯一；不能把边指向已完成节点。

## 验证清单

- 单测覆盖正常完成、取消、拒答、工具失败、checkpoint 和 human-in-loop。
- SSE 测试确认事件能被 conversation 投影，不新增前端必须识别的 `eventType`。
- 业务测试确认失败或拒答不会写入最终业务实例。
