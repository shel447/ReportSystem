# Agent Flow 流程拼装 Skill

当你需要为 ReportSystem 新增、验证或重构一个对话式业务流程时，使用本 Skill。目标是快速拼出可运行的 `shared/agentflow` 流程，并能通过 `/chat` 实时返回进展、增量、最终答案、错误、拒答和停止状态。

## 先判断边界

1. 这是业务流程吗？放在业务 Context 中声明 Flow，例如 `report` 或未来 `data_analysis`。
2. 这是原子能力吗？封装为 Tool，例如查询、检索、LLM 调用、导出调用。
3. 这是可复用的多步骤业务能力吗？封装为 Subflow，例如“数据分析子流程”“章节生成子流程”。
4. 不要把业务状态放进 `conversation`。conversation 只负责会话、场景分发、启动 Flow、订阅事件和投影 `/chat`。

## 选择流程形态

- 简单固定步骤：使用 `SequentialFlow`。
- 需要 `reason / act / observe / decide` 循环：使用 `ReactFlow`。
- 需要条件分支、循环、并行、汇合、动态追加节点：直接构造 `FlowGraph`。
- 高层流程最终都应 `to_graph()`，不要创建旁路运行器。
- 多个互不依赖节点连接到同一个上游节点时，runtime 会用线程池并行执行；下游汇合节点等待所有无条件前置节点完成。
- 并行节点失败时，已启动节点会先完成，未启动下游会被跳过，最终统一失败。

## 节点编写规范

节点函数只接收 `FlowContext`：

```python
def resolve_parameters(context):
    context.emit_step(
        code="report.parameters.resolve",
        title="解析报告参数",
        parent_step_id="report.generate",
        step_path=["report", "generate", "parameters"],
    )
    context.check_cancelled()
    context.set_state("parameters", {"scope": "hq"})
```

常用能力：

- `emit_step()`：发进度，必须尽量提供 `parent_step_id` 和 `step_path`。
- `emit_delta()`：发业务增量，报告 delta 尽量提供统一 `parent`。
- `emit_answer()`：发最终结果。父流程通常只发一次最终 answer。
- `emit_ask()`：形成持久化追问。
- `call_tool()`：调用原子工具。
- `call_subflow()`：调用多步骤子流程。
- `render_prompt()`：组装提示词。
- `save_checkpoint()`：保存 checkpoint。
- `refuse()`：拒答并结束。
- `request_terminate()`：系统主动终止。
- `add_node()/add_edge()`：运行中追加后续分支。
- `get_state()/set_state()/update_state()/mutate_state()`：并行节点中优先使用的线程安全状态读写。
- `record_metric()`：记录自定义资源或质量指标。

## 并行章节示例

```python
graph = FlowGraph(start="plan_sections")
graph.add_node(FlowNode(id="plan_sections", handler=plan_sections))
graph.add_node(FlowNode(id="section_a", handler=make_section_node("a")))
graph.add_node(FlowNode(id="section_b", handler=make_section_node("b")))
graph.add_node(FlowNode(id="join_sections", handler=join_sections))
graph.add_edge(FlowEdge(source="plan_sections", target="section_a"))
graph.add_edge(FlowEdge(source="plan_sections", target="section_b"))
graph.add_edge(FlowEdge(source="section_a", target="join_sections"))
graph.add_edge(FlowEdge(source="section_b", target="join_sections"))
```

章节节点写共享状态时使用：

```python
context.mutate_state("sections", [], lambda items: items.append(section_dsl))
```

不要在并行节点里对同一个 list/dict 做裸写，除非业务方自己持有锁。

## Tool

工具用于原子能力：

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

工具事件自动进入 `/chat` SSE：`toolCall/toolResult` 会作为 `step_delta` 附加字段展示。

## Subflow

子流程用于复用多步骤业务流程：

```python
def build_section_flow(args):
    return SequentialFlow(
        FlowNode(id="query", handler=query_node),
        FlowNode(id="summarize", handler=summarize_node),
    ).to_graph()

registry = SubflowRegistry([
    SubflowSpec(name="section_generation", build_graph=build_section_flow),
])
runtime = InMemoryFlowRuntime(subflow_registry=registry)
```

父流程调用：

```python
result = context.call_subflow(
    "section_generation",
    {"sectionId": "section_1"},
    alias="section_1_generation",
)
```

规则：

- 子流程 step 会加 alias 命名空间，并携带 `sourceSubflow`。
- 子流程 delta 会带 `source: { type: "subflow", alias, callId }`。
- 子流程 answer 默认不覆盖父流程最终 answer，而是转成 `subflow_result` delta，并写入父流程 state。
- 只有显式 `SubflowEventPolicy(bubble_answer=True)` 才允许子流程 answer 冒泡为父流程 answer。
- 子流程错误默认传播；需要捕获时用 `SubflowEventPolicy(error_policy="capture")`。

## Prompt

Prompt 只组装消息，不调用 LLM：

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

LLM 调用应通过业务 gateway 或 tool 注入。

## Hook

Hook 适合横切逻辑：

```python
class GuardHook:
    def before_node(self, hook_context):
        if hook_context.state.get("blocked"):
            return HookDecision.refuse("输入不满足安全要求")
        return HookDecision.continue_()
```

优先使用 hook 做审计、安全、调试和限流，不要把报告参数规则写进 hook。

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

后续接数据库时只替换 saver，不改节点代码。公开 `/chat` 不暴露内部 `runId`。

## 流程图打印

使用 Mermaid 打印 build 前后流程图：

```python
artifact = FlowGraphRenderer().build_artifact(flow, title="report-generation")
print(artifact.before_mermaid)
print(artifact.after_mermaid)
```

新增复杂流程前，建议把 `after_mermaid` 粘到设计文档或 PR 描述中，确认条件边、并行分支和汇合节点是否符合预期。

## Metrics

流程结束时 runtime 会通过 `MetricsCenter` 发布一次资源用量通知。默认是 `NoopMetricsSink`，不会发送到外部系统。

节点可以记录自定义指标：

```python
context.record_metric("section_count", 3, tags={"template": "network-daily"})
```

内置采集包括：

- 流程耗时。
- 启动节点数和失败节点数。
- DataCatalog 逻辑实体去重数量。
- OpenAI-compatible 输出 token 数。

不要在业务流程中直接写 Kafka。需要消息通道时，实现新的 `MetricsSink` 并注入 `MetricsCenter`。

## 动态追加分支

只追加后续分支，不修改已完成节点：

```python
def plan_sections(context):
    for section_id in context.state["section_ids"]:
        context.add_node(FlowNode(id=f"generate_{section_id}", handler=make_section_node(section_id)))
        context.add_edge(FlowEdge(source="plan_sections", target=f"generate_{section_id}"))
```

动态节点 id 必须唯一；不能把边指向已完成节点。

## 对话协作

- 停止当前运行中对话：前端调用 `POST /chat/{chatId}/stop`。
- 普通追加输入：前端本地排队，上一轮 `done` 后通过 `/chat` 创建新 chat。
- 结构化追问答复：继续通过 `/chat reply.sourceChatId` 创建新 chat。
- 不要向前端暴露 `runId`。

## 验证清单

- 单测覆盖正常完成、取消、拒答、工具失败、checkpoint、subflow 和 dynamic graph。
- 并行测试确认耗时低于串行、事件 `sequence` 单调递增、失败策略符合“收集失败”。
- 图测试确认 Mermaid 能展示 build 前后流程图。
- Metrics 测试确认成功、失败、取消都能发布终态指标，sink 失败不影响业务结果。
- SSE 测试确认事件能被 conversation 投影，不新增前端必须识别的新 `eventType`。
- 业务测试确认取消、失败或拒答不会写入最终业务实例。
- 子流程测试至少覆盖：answer 不覆盖父流程、重复调用不串事件、错误传播或捕获。
- step 测试确认 `parentStepId/stepPath`；delta 测试确认统一 `parent` 与旧定位字段双写。
