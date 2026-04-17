# 对话模块设计

> 本文档是 [总设计文档 (design.md)](design.md) 的子文档，描述统一对话模块的状态模型、能力路由、历史会话与报告生成协同策略。

> 术语使用约定：对话模块重点描述阶段推进与交互行为，因此保留 `outline_review`、`outline_instance` 等兼容阶段名或结构名；它们的业务语义统一按“诉求确认 / 诉求实例”理解。

---

## 1. 模块定位

统一对话模块是系统的默认入口，负责承接三类一级能力：

- `report_generation`
- `smart_query`
- `fault_diagnosis`

该模块的目标不是把三类能力混成同一套业务逻辑，而是提供统一入口、统一会话历史、统一状态恢复机制，并保证报告生成链路的结构化确认能力不被弱化。

当前目标态分层：

- `routers/chat.py` 只负责 HTTP 映射
- `contexts/conversation/application` 负责任务推进与状态编排
- `contexts/conversation/infrastructure` 负责会话持久化、AI/模板/报告等技术组件装配

---

## 2. 核心状态模型

### 2.1 Conversation

```python
@dataclass
class Conversation:
    id: str
    user_id: str
    title: str
    fork_meta: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
```

`Conversation` 只表示会话容器，不内嵌消息历史，也不反向挂报告实例。

### 2.2 Chat

```python
@dataclass
class Chat:
    id: str
    conversation_id: str
    user_id: str
    role: str
    content: str
    action: Optional[Dict[str, Any]]
    meta: Dict[str, Any]
    seq_no: int
    created_at: datetime
```

说明：

- 消息从会话中拆出，独立形成消息流水
- 可见消息与隐藏 `context_state` 都存为消息记录
- 消息顺序以 `seq_no` 为准

### 2.3 ContextState v2

统一对话上下文继续以内嵌 `chat.meta.type=context_state` 的方式持久化，不新增独立任务表。核心结构如下：

```python
{
  "conversation": {...},
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
  "report": {...},
  "slots": {...},
  "missing": {...},
  "summary": {...},
  "meta": {...}
}
```

### 2.4 设计原则

- 一个 `Conversation` 同时只有一个 `active_task`
- 会话历史保留全部消息，但系统只认当前 `active_task`
- `Conversation` 只承载容器元信息；消息历史由 `Chat` 明细承载
- `pending_switch` 只承担显式切换确认，不作为任务栈
- 会话不再反向挂单个报告实例；报告实例直接记录其来源对话与来源聊天锚点

---

## 3. 能力路由

### 3.1 路由输入

能力路由基于以下信号综合判断：

- 用户当前消息
- `preferred_capability`
- 当前 `active_task.capability`
- 当前任务阶段
- 是否携带报告专用命令

### 3.2 路由输出

统一路由器内部产生三种结果：

- `continue_current`
- `switch_capability`
- `ask_switch_confirmation`

### 3.3 切换确认规则

若当前任务已有实质进度，则能力切换必须经过 `confirm_task_switch` 卡片确认。

“已有实质进度”的判断规则：

- 报告生成：模板已锁定、已收集参数、已到参数确认/诉求确认/生成阶段
- 智能问数：已进入澄清或已有结构化查询上下文
- 智能故障：已有澄清问题、诊断结论或证据摘要

### 3.4 与 `interaction_mode=chat` 的优先级关系

当报告流程正在等待 `interaction_mode=chat` 的参数时，下一轮普通自然语言输入优先走**参数提取**，而不是优先走能力切换。

只有出现显式切换意图时，才允许打断当前报告流程。

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
  - 返回 `ask_param`
  - 前端使用结构化控件
- `interaction_mode=chat`
  - 返回普通助手追问文本
  - 用户下一轮自然语言继续走参数提取和校验

`form` 与 `chat` 按模板参数定义顺序混排。

### 4.2 诉求确认

参数全部收齐后，系统先生成实例级目录/章节树，再进入 `outline_review`：

- 先替换模板参数
- 再展开 `foreach`
- 再为每个 `section` 生成诉求实例

诉求确认页允许：

- 编辑参数片段
- 编辑非参数静态文本
- 调整节点结构

规则：

- 只改槽位值，不影响模板诉求骨架可用度
- 修改非参数静态文本或结构时，由后台评估骨架是否被破坏

### 4.3 确认生成后的输出

按 [design_chat_report_stream_case.md](design_chat_report_stream_case.md) 的目标态流程：

- 用户确认参数并点击生成后
- `/rest/chatbi/v1/chat` 进入流式返回
- 流中返回 `answerType=REPORT`
- `answer.answer` 同时携带：
  - `report`
  - `templateInstance`
  - `documents`
  - `generationProgress`

说明：

- 对话接口返回的是“正在生成过程中的报告”
- 报告详情接口返回的是“已经生成完成的报告”
- 二者主语义一致，区别只在于是否流式以及生成状态

---

## 5. 会话历史与分支

### 5.1 会话历史

统一对话模块提供会话历史能力：

- `GET /rest/chatbi/v1/chat`
- `GET /rest/chatbi/v1/chat/{conversationId}`
- `DELETE /rest/chatbi/v1/chat/{conversationId}`

行为约束：

- 进入 `/chat` 时不自动恢复最近会话
- 也不预创建空会话
- 只有首条真实用户消息发送后才创建 `Conversation`
- 会话标题由首条用户消息截断生成
- 会话详情中的 `chats` 由消息表按 `conversation_id + seq_no` 组装返回

### 5.2 消息级 fork

用户可以从历史消息发起新会话分支：

- 从用户消息 fork：
  - 新会话保留该消息
  - 同时把消息内容回填到输入框
- 从助手文本或面板消息 fork：
  - 新会话恢复到该消息之后的结构化状态

### 5.3 报告实例更新

报告页中的“继续修改”本质上是基于内部模板实例重开对话：

- 报告详情返回 `templateInstance`
- 用户基于该 `templateInstance` 二次编辑诉求
- 再通过对话入口发起更新会话
- 新会话只注入一个可见的 `review_outline` 节点
- 前后历史消息不回放

该来源在聊天页顶部以“更新来源”展示，而不是“Fork 来源”。

---

## 6. 对外接口关注点

当前与对话模块强相关的接口包括：

- `GET /rest/chatbi/v1/chat`
- `POST /rest/chatbi/v1/chat`
- `GET /rest/chatbi/v1/chat/{conversationId}`
- `DELETE /rest/chatbi/v1/chat/{conversationId}`
- `POST /rest/chatbi/v1/chat/forks`

说明：

- 报告更新/分支复用统一通过 `POST /rest/chatbi/v1/chat/forks` 完成
- 不再公开 `instances` 路径下的历史更新/分支接口
- 对外接口定义严格对齐 ChatBI 外层协议，报告相关扩展见 [chatbi/chatbi_report_extension.md](chatbi/chatbi_report_extension.md)

统一用户身份约束：

- 业务接口从请求头 `X-User-Id` 获取用户身份
- 不信任 body/query 中的 `user_id`

`POST /rest/chatbi/v1/chat` 关键输入字段：

- `conversationId`
- `chatId`
- `instruction`
- `question`
- `reply`
- `command.name`
- `selectedTemplateId`
- `targetParamId`
- `outlineOverride`

---

## 7. 设计约束

- v1 不做任务栈，不支持“问数后自动回到刚才的报告”
- `interaction_mode=chat` 只改变追问方式，不改变参数校验和确认规则
- 报告任务的诉求确认与生成基线仍然是结构化链路，不退回纯聊天式生成
- 本轮不引入独立 `dialogue` 物理表；对话业务边界由消息流水和任务状态共同表达

## 实现文档

- [implementation/conversation.md](implementation/conversation.md)
- [implementation/external_interfaces.md](implementation/external_interfaces.md)
