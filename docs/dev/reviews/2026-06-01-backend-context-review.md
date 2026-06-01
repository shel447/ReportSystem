# Backend DDD Context 划分评审

**日期**：2026-06-01
**评审分支**：`master`
**评审 Commit**：`64aba7d3149c7737e12f7d4f3103d53d7d51c4d3`
**处理分支**：`master`
**处理 Commit**：`cdbf2af03ee43a97871c73987bd477cf4d957c77`
**评审范围**：`modules/backend/src/contexts/`
**评审人**：Claude Code
**状态**：已闭环

## 1. 当前结构

```
contexts/
  conversation/
    domain/          ← 空目录，无任何领域模型
    application/     ← ConversationService (315行), models, errors
    infrastructure/  ← SqlAlchemyConversationRepository, SqlAlchemyChatRepository
  report/
    domain/          ← template_models, generation_models, template_instance_builder, parameter_resolver, placeholder_renderer
    application/     ← ReportService (100行), ReportScenarioService (274行), ReportGenerationService (856行),
                       ReportParameterService (242行), ReportTemplateService (97行), ReportDocumentService (37行)
    infrastructure/  ← 5个 repository, 3个 gateway
```

## 2. 发现的问题

### 2.1 conversation domain 层为空

`conversation/domain/` 目录存在但无任何代码。会话、消息、fork 等核心领域概念全部放在 `application/models.py` 中：

- `ChatCommand`、`ChatContext`、`ChatResponse`、`ChatAsk`、`ChatAnswerEnvelope` — 聊天协议的值对象
- `SessionSummary`、`SessionDetail`、`SessionMessage` — 会话视图模型
- `ForkSessionCommand`、`ForkSessionResult` — fork 操作模型
- `ConversationMessageContent`、`ConversationMessageAction`、`ConversationMessageMeta` — 消息结构

这些是领域概念，应当下沉到 `domain/` 层，application 层只做编排。当前的空目录说明设计意图存在但未完成实现。

### 2.2 ReportGenerationService 是上帝类 (856 行)

承担了过多职责：

| 职责 | 大约行数 | 所属层 | 问题 |
|------|---------|--------|------|
| TemplateInstance 持久化 | ~40 行 | application | 正确 |
| Report DSL 编译 (`build_report_dsl` + 所有 `_build_*` helper) | ~500 行 | **应为 domain service** | 纯领域逻辑放错了层 |
| 文档生成编排 | ~80 行 | application | 正确 |
| 文档下载解析 | ~10 行 | application | 正确 |
| Section 重新生成预览 | ~50 行 | application | 正确 |
| JSON Schema 校验 | ~30 行 | infrastructure gateway | 校验逻辑散落 |

核心问题是 `build_report_dsl`（将 `TemplateInstance` 编译为 `ReportDsl`）是纯领域逻辑——无任何 I/O、无数据库访问、无外部依赖。把它放在 application 层导致：

- 领域逻辑无法脱离 infrastructure 独立进行单元测试
- application 层变成了事实上的 domain service
- 编译函数全部是模块级私有函数（`_build_report_catalog`、`_build_section_components` 等），无法被其他上下文复用
- 与 `template_instance_builder.py`（domain 层）形成了不对称——template → instance 在 domain，instance → dsl 在 application

### 2.3 ReportDocumentService 是贫血对象 (37 行)

```python
class ReportDocumentService:
    def generate_documents(self, ...):
        return self.generation_service.generate_documents(...)

    def resolve_download(self, ...):
        return self.generation_service.resolve_download(...)
```

完全是透传，不包含任何自有逻辑。文档导出涉及多个外部依赖（Java exporter 子进程、文件系统、export job 追踪），是一个独立的业务能力，但当前实现全部委派给 `ReportGenerationService`。

### 2.4 ScenarioService 跨 context 职责模糊

`ConversationService.chat()` 直接理解 report 领域的指令语义：

```python
# conversation/application/services.py
def chat(self, *, data: ChatCommand, user_id: str) -> ChatResponse:
    instruction = data.instruction or "generate_report"
    if instruction == "extract_report_template":  # report 领域知识泄漏到 conversation
        ...
    result = self.report_service.chat(...)
```

Conversation context 承担了路由 report 指令的职责，但没有明确的 Anti-Corruption Layer（ACL）。`_response_from_scenario_result` 和 `_chat_response_from_payload` 本质上是 ACL 的转换逻辑，但被写成了 `ConversationService` 的私有函数，导致：

- conversation context 直接 import report 领域类型（`ReportScenarioCommand`、`report_ask_payload_from_dict`、`report_scenario_answer_from_dict`）
- 未来新增业务场景（如 `fault_diagnosis`）时，ConversationService 需要 import 更多外部 context 的类型
- 两个 context 之间的耦合没有明确的契约边界

### 2.5 ParameterService 职责边界不清

参数提取、合并、校验的逻辑分散在两处：

- `application/parameter_service.py` — `extract_values()`（含正则、选项匹配、HTTP 调用）、`merge_reply_values()`、`build_ask()`、`resolve_options()`
- `domain/template_instance_builder.py` — `merge_parameter_values()`、`instantiate_template_instance()`、`collect_instance_parameters()`

`extract_values()` 包含 HTTP 调用（应用层关注点），但 `merge_parameter_values()` 是纯值对象合并（领域层关注点）。两者的边界靠函数调用隐式划分，没有显式的领域服务来封装"参数合并规则"。

### 2.6 缺少统一的 instruction 路由

Instruction 分发逻辑散落在两处：

- `ConversationService.chat()` — 处理 `extract_report_template` 的特殊路径（不需要 conversation）
- `ReportScenarioService.handle()` — 处理 `generate_report`、`generate_report_segment`

当新增 instruction 类型时，开发者需要同时理解两个文件中分散的路由逻辑。

## 3. 改进建议

### 3.1 [高优先级] 提取 ReportDslCompiler 为领域服务

在 `report/domain/` 下新建 `report_compiler.py`：

```
report/domain/
  report_compiler.py    # 新增：将 TemplateInstance 编译为 ReportDsl
  template_instance_builder.py  # 已有：将 ReportTemplate 实例化为 TemplateInstance
```

```python
class ReportDslCompiler:
    """将已确认的 TemplateInstance 编译为正式 ReportDsl。纯领域逻辑，无 I/O 依赖。"""

    def compile(
        self,
        *,
        template: ReportTemplate,
        template_instance: TemplateInstance,
        custom_content_provider: CustomContentProvider,  # 接口，不是具体实现
    ) -> ReportDsl:
        ...
```

影响：
- 从 `ReportGenerationService` 移走 ~500 行代码
- 编译器可脱离数据库和外部服务独立单测
- 形成对称的领域服务层次：`TemplateInstanceBuilder`（template → instance）、`ReportDslCompiler`（instance → dsl）

### 3.2 [高优先级] 填补 conversation domain 层

```
conversation/domain/
  chat_command.py       # ChatCommand 值对象
  chat_context.py       # ChatContext 值对象
  chat_response.py      # ChatResponse, ChatAsk, ChatAnswerEnvelope
  session.py            # SessionSummary, SessionDetail, SessionMessage
  message.py            # MessageContent, MessageAction, MessageMeta 值对象
  fork.py               # ForkSessionCommand, ForkSessionResult
```

application 层保留 `ConversationService` 做编排，领域模型下沉。`application/models.py` 中对 report 的转换逻辑（`report_ask_payload_from_dict` 等）移到 ACL。

### 3.3 [中优先级] 引入 Anti-Corruption Layer

在 conversation 和 report 之间加一层薄适配器：

```
conversation/infrastructure/
  report_chat_adapter.py  # 新增：conversation ↔ report 的翻译层
```

```python
class ReportChatAdapter:
    """将 report context 的概念翻译为 conversation context 的概念。"""

    def to_chat_response(self, result: ReportScenarioResult, ...) -> ChatResponse:
        ...

    def to_scenario_command(self, data: ChatCommand) -> ReportScenarioCommand:
        ...

    def chat_response_from_payload(self, payload: dict) -> ChatResponse:
        ...
```

影响：
- `ConversationService` 不再直接 import report 领域类型
- 未来新增业务场景（如 `fault_diagnosis`）时只需新增 adapter，不改 conversation 核心逻辑
- `_response_from_scenario_result`、`_chat_response_from_payload` 等私有函数成为有明确职责的类

### 3.4 [中优先级] 充实 ReportDocumentService

把文档生成的编排逻辑从 `ReportGenerationService` 移到 `ReportDocumentService`：

```python
class ReportDocumentService:
    """报告文档生成与下载的应用服务。"""

    def generate_documents(
        self,
        *,
        report_id: str,
        user_id: str,
        formats: list[str],
        ...
    ) -> DocumentGenerationResult:
        # 从 ReportGenerationService 移过来的 ~80 行编排逻辑
        report_view = self.generation_service.get_report_view(...)
        # ...export job 创建、document gateway 调用、结果组装...
```

影响：
- `ReportGenerationService` 聚焦在 "冻结实例 → 报告" 核心链路
- 文档导出作为独立业务能力有明确的服务归属
- 职责边界更清晰：generation 负责报告内容，document 负责文件产物

### 3.5 [低优先级] 统一 instruction 路由

当前两处路由逻辑收口到一处。两种方案：

**方案 A**：让 `ReportScenarioService.handle()` 处理所有 instruction，包括 `extract_report_template`。`ConversationService.chat()` 始终走"确保会话 → 委派 report_service.chat() → 组装响应"的路径。

**方案 B**：在 application 层引入 `InstructionRouter`，显式维护 instruction → handler 的映射。

建议方案 A，改动更小且不引入新概念。

### 3.6 [低优先级] 梳理 ParameterService 与 TemplateInstanceBuilder 的边界

明确的划分：

- **领域层** (`template_instance_builder.py`)：参数值合并规则、必填校验、foreach 展开、执行绑定构建
- **应用层** (`parameter_service.py`)：从自然语言提取参数值（正则、HTTP 选项解析）、构建 Ask 响应、编排"提取 → 合并 → 构建实例"流程

当前 `parameter_service.py` 中的 `extract_values()` 包含 HTTP 调用（`resolve_options`），这表明它已经是应用层行为。但 `merge_reply_values()` 是纯值对象转换，可以下沉到 domain。

## 4. 优先级汇总

| 优先级 | 改进项 | 影响范围 | 风险 |
|--------|-------|---------|------|
| 高 | 提取 ReportDslCompiler 为领域服务 | `report/domain/` 新增，`generation_service.py` 瘦身 | 低：纯函数提取，不改变行为 |
| 高 | 填补 conversation domain 层 | `conversation/domain/` 新增文件 | 低：纯模型移动 |
| 中 | 引入 Anti-Corruption Layer | `conversation/infrastructure/` 新增 | 中：改变 import 关系 |
| 中 | 充实 ReportDocumentService | `generation_service.py` → `document_service.py` | 低：编排逻辑迁移 |
| 低 | 统一 instruction 路由 | `conversation/services.py` + `scenario_service.py` | 中：改变控制流 |
| 低 | 梳理 ParameterService 边界 | `parameter_service.py` + `template_instance_builder.py` | 低：函数移动 |

## 5. 处理记录

处理提交范围：`64aba7d` → `cdbf2af`（4 个提交：`f8cc0da`、`3024a9f`、`4b6b3fc`、`cdbf2af`）

### 5.1 [高] 提取 ReportDslCompiler 为领域服务 ✅

**处理结果**：已采纳。新建 `report/domain/report_dsl_compiler.py`（449 行），`ReportDslCompiler` 类负责将 `TemplateInstance` 编译为 `ReportDsl`。`ReportGenerationService` 从 856 行缩减到 213 行，变为纯编排层，委托编译器处理所有 DSL 构建。形成对称的领域服务层次：`TemplateInstanceBuilder`（template → instance）、`ReportDslCompiler`（instance → dsl）。

### 5.2 [高] 填补 conversation domain 层 ✅

**处理结果**：已采纳。新建 `conversation/domain/models.py`（120 行），包含 `ScenarioTrace`、`ChatContext`、`ForkSource`、`ConversationMessageContent`、`ConversationMessageAction`、`ConversationMessageMeta` 等核心领域模型。`application/models.py` 瘦身，仅保留应用边界类型（`ChatCommand`、`ChatResponse`、`SessionSummary` 等），通过 import 引用领域模型，不再重复定义。

### 5.3 [中] 引入 Anti-Corruption Layer ✅

**处理结果**：已采纳，且实现超出预期。团队引入了通用场景调度框架而非简单的 ACL：

- `conversation/application/scenarios.py` — `ScenarioRegistry` + `ScenarioRecognizer` + `ScenarioDispatchService`，实现可注册、可扩展的场景分发
- `infrastructure/scenarios/report_conversation.py` — `ReportConversationScenarioHandler` + `ReportConversationScenarioCodec`，作为 report ↔ conversation 的唯一翻译点
- `ConversationService` 不再直接导入任何 report 领域类型，零领域耦合
- 未来新增业务场景（如 `fault_diagnosis`）只需新增 `ScenarioRegistration`，不改 conversation 核心逻辑

### 5.4 [中] 充实 ReportDocumentService ✅

**处理结果**：已采纳。`document_service.py` 从 37 行透传增长到 104 行。`ReportDocumentService` 现在直接注入 `document_repository`、`export_job_repository`、`document_gateway`，实现完整的文档生成编排：格式验证、去重检测、导出作业依赖链管理、下载解析。`ReportGenerationService` 聚焦"冻结实例 → 报告"核心链路。

### 5.5 [低] 统一 instruction 路由 ✅

**处理结果**：已采纳。`ScenarioDispatchService.resolve()` 实现统一路由，按优先级：显式指令 → 回复链追踪 → 连续性追踪 → 识别器启发式。`ConversationService.chat()` 不再包含硬编码的 `if instruction == "..."` 分支，全部通过 `ScenarioDispatchService` 分发。

### 5.6 [低] 梳理 ParameterService 与 TemplateInstanceBuilder 的边界 ✅

**处理结果**：已采纳。`parameter_service.py` 重写后边界清晰：

- 领域层：`ParameterResolver`、`template_instance_builder.py` 中的合并/展开/校验逻辑
- 应用层：`parameter_service.py` 编排提取 → 合并 → 构建实例流程
- `ParameterOptionsGateway` 通过注入获得，脱离 HTTP 实现细节
- 新增 `parameter_options.py`（infrastructure）封装 HTTP 选项解析

## 6. 不在本次评审范围内

- 前端架构
- exporter 模块
- API 路由设计
- 数据库 schema 设计
- 测试覆盖率和测试策略
- 性能优化
