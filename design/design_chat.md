# 对话模块设计

> 本文档是 [总设计文档 (design.md)](design.md) 的子文档，描述统一对话模块在当前版本下的状态模型、能力路由、历史会话与报告生成协同策略。

---

## 1. 模块定位

统一对话模块是系统的默认入口，负责承接三类一级能力：

- `report_generation`：制作报告
- `smart_query`：智能问数
- `fault_diagnosis`：智能故障

该模块的目标不是把三类能力混成同一套业务逻辑，而是提供统一入口、统一历史会话与统一状态恢复机制，同时保证报告生成链路的结构化确认能力不被弱化。

当前实现上，对话模块已经按 DDD 分层收敛：

- `routers/chat.py` 只负责 HTTP 映射
- `contexts/conversation/application` 负责任务推进与状态编排
- `contexts/conversation/infrastructure` 负责会话持久化、legacy 能力适配、AI/模板/文档等技术组件装配

---

## 2. 核心状态模型

### 2.1 ChatSession

```python
@dataclass
class ChatSession:
    session_id: str
    user_id: str
    title: str
    messages: List[Dict[str, Any]]
    fork_meta: Dict[str, Any]
    matched_template_id: Optional[str]
    instance_id: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
```

### 2.2 ContextState v2

统一对话上下文继续以内嵌 `messages[].meta.type=context_state` 的方式持久化，不新增独立任务表。核心结构如下：

```python
{
  "session": {...},
  "active_task": {
    "task_id": str,
    "capability": "report_generation | smart_query | fault_diagnosis",
    "stage": str,
    "progress_state": {"has_progress": bool},
    "context_payload": {...}
  },
  "pending_switch": {
    "from_capability": str,
    "to_capability": str,
    "reason": str,
    "captured_user_message": str
  } | None,
  "flow": {...},
  "report": {...},
  "slots": {...},
  "missing": {...},
  "summary": {...},
  "meta": {...}
}
```

### 2.3 设计原则

- 一个 `ChatSession` 同时只有一个 `active_task`
- 会话历史保留全部消息，但系统只认当前 `active_task`
- `pending_switch` 只承担显式切换确认，不作为任务栈
- 报告任务仍使用 `report/slots/missing` 这组扩展字段承接大纲确认与参数确认

---

## 3. 能力路由

### 3.1 路由输入

能力路由基于以下信号综合判断：

- 用户当前消息
- `preferred_capability`
- 当前 `active_task.capability`
- 当前任务阶段
- 是否携带报告专用命令（选模板、填参数、编辑大纲等）

### 3.2 路由输出

统一路由器内部会产生三种结果：

- `continue_current`
- `switch_capability`
- `ask_switch_confirmation`

### 3.3 切换确认规则

若当前任务已有实质进度，则能力切换必须经过 `confirm_task_switch` 卡片确认。

“已有实质进度”的判断规则：

- 报告生成：模板已锁定、已收集参数、已到参数确认/大纲确认/生成阶段
- 智能问数：已进入澄清或已有结构化查询上下文
- 智能故障：已有澄清问题、诊断结论或证据摘要

### 3.4 与 `interaction_mode=chat` 的优先级关系

当报告流程正在等待 `interaction_mode=chat` 的参数时，下一轮普通自然语言输入优先走**参数提取**，而不是优先走能力切换。

只有出现显式切换意图时，才允许打断当前报告流程，例如：

- `先别做报告了，我想知道昨天华东区域告警最多的三个站点`
- `切到智能故障，帮我看下 1 号站点昨晚是不是出问题了`

该规则的目的，是避免“chat 模式参数追问”被误识别成智能问数或智能故障。

---

## 4. 报告生成任务状态机

报告生成在统一对话模块内部保留完整状态机：

```text
template_matching
-> required_collection
-> review_ready
-> outline_review
-> generating
-> generated
```

### 4.1 参数收集

模板参数支持两种追问方式：

- `interaction_mode=form`
  - 返回 `ask_param` action
  - 前端使用结构化控件
- `interaction_mode=chat`
  - 返回普通助手追问文本
  - 前端不渲染参数面板
  - 用户下一轮自然语言继续走参数提取和校验

`form` 与 `chat` 按模板参数定义顺序混排，不做分组。

### 4.2 大纲确认

参数全部收齐后，系统先生成实例级蓝图树，再进入 `outline_review`：

- 先替换模板参数
- 再展开 `foreach`
- 再为每个章节生成 `outline_instance`

大纲确认页面允许：

- 编辑参数片段
- 编辑非参数静态文本
- 调整节点结构

当用户只改参数片段时，系统保留蓝图结构；当用户修改非参数静态文本时，该节点退化成普通句子节点。

---

## 5. 智能问数与智能故障

### 5.1 智能问数

智能问数采用轻量多轮策略：

- 默认单轮完成
- 信息不足时进入 `clarifying`
- 成功时进入 `answered`

输出当前包含：

- 查询口径摘要
- 结果概览
- 核心结果
- 内部调试上下文（保存在 `context_payload.query_debug`）

### 5.2 智能故障

智能故障也采用轻量多轮策略：

- 默认根据用户描述直接生成诊断摘要
- 信息不足时进入 `clarifying`

输出当前包含：

- 故障现象
- 初步判断
- 风险等级
- 可能原因
- 下一步建议

---

## 6. 会话历史与分支

### 6.1 会话历史

统一对话模块提供会话历史能力：

- `GET /api/chat`：会话摘要列表
- `GET /api/chat/{session_id}`：单会话详情
- `DELETE /api/chat/{session_id}`：删除会话

行为约束：

- 进入 `/chat` 时不自动恢复最近会话
- 也不预创建空会话
- 只有首条真实用户消息发送后才创建 `ChatSession`
- 会话标题由首条用户消息截断生成

### 6.2 消息级 fork

用户可以从历史消息发起新会话分支：

- 从用户消息 fork：
  - 新会话保留该消息
  - 同时把消息内容回填到输入框
- 从助手文本或面板消息 fork：
  - 新会话恢复到该消息之后的结构化状态

### 6.3 报告实例更新

报告实例页的“更新”本质上是基于内部生成基线重开对话：

- 用户先在实例详情预览“确认大纲 / 生成基线”
- 点击“继续到对话助手修改”后，系统创建新会话
- 新会话只注入一个可见的 `review_outline` 节点
- 前后历史消息不回放

该来源在聊天页顶部以“更新来源”展示，而不是“Fork 来源”。

---

## 7. 对外接口关注点

当前与对话模块强相关的接口包括：

- `GET /api/chat`
- `POST /api/chat`
- `GET /api/chat/{session_id}`
- `DELETE /api/chat/{session_id}`
- `POST /api/chat/forks`
- `POST /api/instances/{id}/update-chat`
- `POST /api/instances/{id}/fork-chat`

`POST /api/chat` 当前支持的重要输入字段：

- `preferred_capability`
- `selected_template_id`
- `param_id / param_value / param_values`
- `command`
- `target_param_id`
- `outline_override`

---

## 8. 设计约束

- v1 不做任务栈，不支持“问数后自动回到刚才的报告”
- `interaction_mode=chat` 只改变追问方式，不改变参数校验和确认规则
- 报告任务的大纲确认与生成基线仍然是结构化链路，不退回纯聊天式生成
- 会话栏折叠状态只保存在前端 UI 运行态，不做跨端记忆

---

## 附录

- 对话模块是报告生成、智能问数、智能故障的统一入口，不是报告模块的附属页面
- 对话历史、消息级 fork、实例更新恢复都是统一对话模块的能力，不再单独拆出“模板实例”页面

## 实现文档

当前版本的核心技术实现说明见：

- [implementation/conversation.md](implementation/conversation.md)
- [implementation/external_interfaces.md](implementation/external_interfaces.md)
