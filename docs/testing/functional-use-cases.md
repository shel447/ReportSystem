# 功能用例文档

## 1. 文档目的

本文档基于当前系统设计与主干实现，定义本轮正式功能测试的用例基线、覆盖范围和详细用例。本文档服务于三类目标：

- 为本轮深入系统测试提供统一执行基线
- 为后续例行自动化回归提供稳定的用例索引
- 为测试报告中的覆盖声明提供可追溯依据

## 2. 测试基线

### 2.1 设计基线

当前正式设计基线采用以下文档：

- `design/design_api.md`
- `design/design_chat_report_stream_case.md`
- `design/design_template.md`
- `design/design_chat.md`
- `design/implementation/template_catalog.md`
- `design/implementation/conversation.md`
- `design/implementation/report_runtime.md`
- `design/implementation/external_interfaces.md`

### 2.2 正式测试范围

本轮正式测试范围按当前新口径执行，只覆盖以下公开业务面与开发面：

- `templates`
- `chat`
- `reports`
- `parameter-options`
- `/rest/dev/design`
- `/rest/dev/system-settings`
- `/rest/dev/feedback`
- 前端公开页面：`/chat`、`/templates`、`/templates/:id`、`/reports`、`/reports/:id`、`/settings`

### 2.3 不纳入正式范围

以下能力视为已下线或待实现，不纳入本轮正式用例与通过判定：

- `/rest/chatbi/v1/instances/*`
- `/rest/chatbi/v1/scheduled-tasks/*`
- 独立 `/rest/chatbi/v1/documents/*`
- 独立 `TemplateInstance` 公开接口
- `POST /rest/chatbi/v1/reports/{reportId}/edit-stream`

## 3. 测试组织结构

测试用例按五个测试域组织：

- `TPL`：模板目录与模板定义
- `CHAT`：统一对话与会话编排
- `RPT`：报告聚合与文档下载
- `DEV`：开发接口与系统治理能力
- `UI`：前端页面与公开导航

## 4. 数据与环境前提

### 4.1 环境前提

- 前端服务可通过 `8001` 或后端静态托管访问
- 后端服务可通过 `8300` 访问
- `Completion` 与 `Embedding` 已配置完成
- 样例分析库 `src/backend/telecom_demo.db` 可用

### 4.2 测试数据原则

- 公开 API 深度冒烟统一使用固定 `X-User-Id`
- 模板测试使用固定模板 ID，可重复创建或覆盖
- 反馈测试数据可创建后删除
- 报告生成链路允许保留测试报告记录，但需在报告中说明

## 5. 覆盖矩阵

| 测试域 | 关注点 | 主要接口或页面 | 用例编号 |
|---|---|---|---|
| `TPL` | 唯一模板定义、导入导出、动态参数、schema 合规 | `/templates*` `/parameter-options/resolve` `/templates` 页面 | `TPL-001` 至 `TPL-011` |
| `CHAT` | 模板匹配、参数提取、表单/自然语言追问、诉求确认、任务切换、fork | `/chat*` `/chat` 页面 | `CHAT-001` 至 `CHAT-018` |
| `RPT` | 报告聚合视图、模板实例聚合、文档下载、用户隔离 | `/reports*` `/reports` 页面 | `RPT-001` 至 `RPT-006` |
| `DEV` | 系统设置、设计文档、反馈、索引重建、连通性测试 | `/rest/dev/*` `/settings` 页面 | `DEV-001` 至 `DEV-010` |
| `UI` | 导航、页面加载、关键操作入口、交互反馈 | 各公开页面 | `UI-001` 至 `UI-008` |

## 6. 详细用例

### 6.1 模板目录与参数解析

#### `TPL-001` 模板列表返回唯一模板摘要

- 目标：验证模板列表仅返回新模板结构摘要，不泄露旧字段
- 前置条件：系统中至少存在一个模板
- 步骤：
1. 调用 `GET /rest/chatbi/v1/templates`
2. 检查每个模板项字段
- 预期结果：
1. 返回 `id/name/description/category`
2. 返回 `parameter_count/top_level_section_count`
3. 不返回 `report_type/template_type/scene/content_params/schema_version`

#### `TPL-002` 创建符合新结构的模板

- 目标：验证模板创建仅接受唯一模板结构
- 前置条件：模板 ID 未被占用
- 步骤：
1. 调用 `POST /rest/chatbi/v1/templates`
2. 请求体仅包含 `id/category/name/description/parameters/sections`
- 预期结果：
1. 返回 `200`
2. 响应中的模板结构与提交结构一致
3. 模板详情可再次读取

#### `TPL-003` 旧模板顶层字段被拒绝

- 目标：验证模板双轨定义已清理
- 前置条件：无
- 步骤：
1. 调用 `POST /rest/chatbi/v1/templates`
2. 在请求体中注入 `report_type`、`scene` 或顶层 `outline`
- 预期结果：
1. 返回 `400`
2. 明确提示结构不合法或 schema 校验失败

#### `TPL-004` 模板详情与更新保持唯一结构

- 目标：验证详情读取与更新后结构稳定
- 前置条件：存在一个可编辑模板
- 步骤：
1. 调用 `GET /rest/chatbi/v1/templates/{id}`
2. 修改 `description/category/sections`
3. 调用 `PUT /rest/chatbi/v1/templates/{id}`
- 预期结果：
1. 更新后再次读取字段完全一致
2. 不出现旧字段回写

#### `TPL-005` 模板删除生效

- 目标：验证模板删除主链路
- 前置条件：存在一个临时模板
- 步骤：
1. 调用 `DELETE /rest/chatbi/v1/templates/{id}`
2. 再次读取该模板
- 预期结果：
1. 删除接口返回成功
2. 再次读取返回 `404`

#### `TPL-006` 模板导出文件名与结构正确

- 目标：验证导出文件名格式与导出 JSON 结构
- 前置条件：存在一个模板
- 步骤：
1. 调用 `GET /rest/chatbi/v1/templates/{id}/export`
2. 检查 `Content-Disposition` 与 JSON 体
- 预期结果：
1. 文件名格式为 `模板名称-YYYYMMDD-HHMMSS.json`
2. JSON 体只含新模板结构

#### `TPL-007` 模板导入预解析支持系统导出模板

- 目标：验证系统导出模板可重新导入为草稿
- 前置条件：已取得一份模板导出 JSON
- 步骤：
1. 调用 `POST /rest/chatbi/v1/templates/import/preview`
2. 传入导出 JSON 与文件名
- 预期结果：
1. 返回 `normalized_template/source_kind/warnings/conflict`
2. `source_kind = system_export`
3. 不直接入库

#### `TPL-008` 模板导入预解析支持外部模板归一化

- 目标：验证外部模板结构可被归一化
- 前置条件：准备一份外部 `ReportTemplate` 风格 JSON
- 步骤：
1. 调用导入预解析接口
2. 检查归一化后的模板草稿
- 预期结果：
1. 返回 `source_kind = external_report_template`
2. 返回的新模板草稿满足唯一模板结构

#### `TPL-009` 参数三通道定义生效

- 目标：验证参数支持 `display/value/query`
- 前置条件：模板中存在 `enum` 或 `dynamic` 参数
- 步骤：
1. 创建或更新包含 `value_mode/value_mapping` 的模板
2. 读取详情
- 预期结果：
1. 参数定义保留 `value_mode/value_mapping`
2. `free_text/date` 参数不得携带上述字段

#### `TPL-010` 动态参数解析返回 `label/value/query`

- 目标：验证参数解析辅助接口正式协议
- 前置条件：存在 `api:/regions/list` 或 `api:/sites/list`
- 步骤：
1. 调用 `POST /rest/chatbi/v1/parameter-options/resolve`
- 预期结果：
1. 返回 `items[]`
2. 每项包含 `label/value/query`
3. `meta` 中包含 `limit/returned/has_more/truncated`

#### `TPL-011` 动态参数异常路径受控

- 目标：验证超限和非法源处理
- 前置条件：无
- 步骤：
1. `limit > 50` 调用接口
2. 使用非法 `source`
3. 模拟外部 HTTP 源缺少 `query`
- 预期结果：
1. 超限返回 `400`
2. 非法源返回 `400`
3. 非法上游返回空 `items` 和明确错误语义

### 6.2 统一对话

#### `CHAT-001` 空会话列表可正常返回

- 目标：验证 `/chat` 初始可用
- 前置条件：该测试用户下无会话
- 步骤：
1. 调用 `GET /rest/chatbi/v1/chat`
- 预期结果：
1. 返回空列表
2. 不自动创建会话

#### `CHAT-002` 首条消息创建会话

- 目标：验证会话惰性创建规则
- 前置条件：用户不存在活动会话
- 步骤：
1. 调用 `POST /rest/chatbi/v1/chat`
2. 发送首条真实消息
- 预期结果：
1. 返回新的 `session_id` 或 `conversationId`
2. 会话标题由首条消息衍生

#### `CHAT-003` 自然语言自动匹配模板

- 目标：验证模板匹配主链路
- 前置条件：存在可匹配模板并已完成语义索引
- 步骤：
1. 发送带模板语义的自然语言请求
- 预期结果：
1. 会话命中目标模板或返回候选模板
2. 会话记录中保存 `matched_template_id`

#### `CHAT-004` 候选模板选择路径可用

- 目标：验证歧义匹配时的显式选择
- 前置条件：存在多个候选模板
- 步骤：
1. 发送会触发歧义匹配的消息
2. 检查候选面板
3. 提交所选模板
- 预期结果：
1. 返回 `show_template_candidates`
2. 选择后继续进入参数收集

#### `CHAT-005` `form` 参数返回结构化面板

- 目标：验证 `interaction_mode=form`
- 前置条件：模板含 `form` 参数
- 步骤：
1. 启动报告对话
2. 观察待追问参数返回
- 预期结果：
1. 返回 `ask_param` 或 contract `ask.mode=form`
2. 提供参数 ID、标签、输入类型、候选项

#### `CHAT-006` `chat` 参数返回自然语言追问

- 目标：验证 `interaction_mode=chat`
- 前置条件：模板含 `chat` 参数
- 步骤：
1. 完成前置参数收集
2. 进入 `chat` 模式参数
- 预期结果：
1. 不返回结构化参数卡片
2. 助手通过自然语言追问该参数

#### `CHAT-007` 混合参数按定义顺序推进

- 目标：验证 `form/chat` 混排不被重排
- 前置条件：模板参数顺序包含 `form -> form -> chat -> form`
- 步骤：
1. 启动对话
2. 逐轮完成收参
- 预期结果：
1. 系统严格按模板参数顺序推进
2. 不出现“先表单后聊天”的分组行为

#### `CHAT-008` 首轮参数抽取自动落入模板实例

- 目标：验证自然语言中的已明示参数可被自动识别
- 前置条件：模板含可从首轮消息识别的参数
- 步骤：
1. 首条消息中显式包含部分参数值
2. 查看后续待追问参数
- 预期结果：
1. 已识别参数不再重复追问
2. 待追问集合只包含未识别参数

#### `CHAT-009` 参数确认后可生成诉求确认树

- 目标：验证 `review_params -> prepare_outline_review`
- 前置条件：必填参数已全部收集
- 步骤：
1. 完成参数收集
2. 触发生成诉求确认树
- 预期结果：
1. 返回 `review_outline`
2. 返回 `params_snapshot`
3. 创建或更新内部 `TemplateInstance`

#### `CHAT-010` `foreach` 诉求展开正确

- 目标：验证 `foreach` 节点按参数值展开
- 前置条件：模板章节配置 `foreach`
- 步骤：
1. 使用多值参数完成收集
2. 生成诉求确认树
- 预期结果：
1. 节点按参数值逐项展开
2. 展开标题与动态元数据正确

#### `CHAT-011` 诉求要素行内修改后保留结构化节点

- 目标：验证只修改要素值时仍保持结构化诉求
- 前置条件：节点存在 `requirement_instance.items`
- 步骤：
1. 修改某个 `item` 的值
2. 提交 `edit_outline`
- 预期结果：
1. 节点仍保留 `requirement_instance`
2. `execution_bindings` 仍存在
3. 执行层引用的模板继续可复用

#### `CHAT-012` 修改整句诉求退化为自由文本节点

- 目标：验证结构化节点退化规则
- 前置条件：存在结构化诉求节点
- 步骤：
1. 修改非参数文本，或显式设为 `outline_mode=freeform`
2. 提交 `edit_outline`
- 预期结果：
1. 节点退化为 `freeform_leaf`
2. 去除 `requirement_instance` 与结构化绑定

#### `CHAT-013` 确认生成后产出报告与文档

- 目标：验证报告主链路
- 前置条件：诉求确认树准备完成
- 步骤：
1. 提交 `confirm_outline_generation`
- 预期结果：
1. 生成最终报告
2. 返回 `reportId`
3. 返回报告级文档下载信息

#### `CHAT-014` 报告生成后模板实例完整聚合

- 目标：验证 `TemplateInstance` 贯穿整个流程
- 前置条件：已生成报告
- 步骤：
1. 调用 `GET /rest/chatbi/v1/reports/{reportId}`
- 预期结果：
1. 返回完整 `template_instance`
2. 其中包含 `base_template/runtime_state/resolved_view/generated_content`

#### `CHAT-015` SSE 骨架可用

- 目标：验证 `Accept: text/event-stream` 路径
- 前置条件：无
- 步骤：
1. 以 `Accept: text/event-stream` 调用 `/chat`
- 预期结果：
1. 返回 `text/event-stream`
2. 至少包含 `event: message`

#### `CHAT-016` 会话 fork 可用

- 目标：验证消息级 fork
- 前置条件：存在含用户消息或助手面板消息的会话
- 步骤：
1. 调用 `POST /rest/chatbi/v1/chat/forks`
2. 指定来源会话和消息
- 预期结果：
1. 生成新会话
2. 保留 fork 元信息
3. 草稿消息和上下文恢复正确

#### `CHAT-017` 显式任务切换需确认

- 目标：验证单活任务模型
- 前置条件：当前会话处于报告任务中且存在待完成步骤
- 步骤：
1. 中途询问智能问数或故障问题
- 预期结果：
1. 返回 `confirm_task_switch`
2. 明确 `from_capability/to_capability`

#### `CHAT-018` 智能问数与故障诊断仍可独立工作

- 目标：验证 `/chat` 统一入口的其余两类能力
- 前置条件：系统设置已准备完成
- 步骤：
1. 分别以 `smart_query` 与 `fault_diagnosis` 发送问题
- 预期结果：
1. 返回非空助手回复
2. 不触发报告模板主链路

### 6.3 报告聚合

#### `RPT-001` 报告详情返回聚合视图

- 目标：验证报告详情只提供聚合视图
- 前置条件：存在已生成报告
- 步骤：
1. 调用 `GET /rest/chatbi/v1/reports/{reportId}`
- 预期结果：
1. 返回 `reportId/status/template_instance/generated_content`
2. 不跳转到独立实例接口

#### `RPT-002` 报告下载使用 report-scoped 路径

- 目标：验证文档下载路径收口
- 前置条件：报告存在文档
- 步骤：
1. 调用 `GET /rest/chatbi/v1/reports/{reportId}/documents/{documentId}/download`
- 预期结果：
1. 返回 Markdown 文件
2. MIME 类型正确

#### `RPT-003` 报告不存在返回 `404`

- 目标：验证不存在资源处理
- 前置条件：无
- 步骤：
1. 读取不存在的 `reportId`
- 预期结果：
1. 返回 `404`

#### `RPT-004` 文档不存在返回 `404`

- 目标：验证 report-scoped 下载的资源校验
- 前置条件：存在报告但文档 ID 不存在
- 步骤：
1. 访问不存在的文档
- 预期结果：
1. 返回 `404`

#### `RPT-005` 用户隔离生效

- 目标：验证 `X-User-Id` 业务隔离
- 前置条件：某报告属于用户 A
- 步骤：
1. 使用用户 B 访问该报告
- 预期结果：
1. 返回 `404` 或不可见

#### `RPT-006` 最终报告包含完整生成内容

- 目标：验证最终报告正文已聚合写回
- 前置条件：报告生成成功
- 步骤：
1. 获取报告详情
2. 检查 `generated_content.sections/documents`
- 预期结果：
1. `sections` 非空
2. `documents` 非空

### 6.4 开发接口与治理

#### `DEV-001` 获取系统设置

- 目标：验证系统设置可读取
- 前置条件：无
- 步骤：
1. 调用 `GET /rest/dev/system-settings`
- 预期结果：
1. 返回 `completion/embedding/is_ready/index_status`

#### `DEV-002` 更新系统设置

- 目标：验证系统设置保存
- 前置条件：具备可写配置
- 步骤：
1. 调用 `PUT /rest/dev/system-settings`
- 预期结果：
1. 返回新配置
2. 索引状态变为待重建或更新

#### `DEV-003` Completion 与 Embedding 连通性测试

- 目标：验证外部模型接口连通性
- 前置条件：对应配置完整
- 步骤：
1. 调用 `POST /rest/dev/system-settings/test`
- 预期结果：
1. 返回 `completion` 与 `embedding` 测试结果

#### `DEV-004` 模板语义索引重建

- 目标：验证重建路径和错误处理
- 前置条件：存在模板，Embedding 配置完成
- 步骤：
1. 调用 `POST /rest/dev/system-settings/reindex`
- 预期结果：
1. 返回重建成功信息与索引状态

#### `DEV-005` 设计文档列表读取

- 目标：验证设计文档目录浏览
- 前置条件：`design/` 目录存在
- 步骤：
1. 调用 `GET /rest/dev/design`
- 预期结果：
1. 返回 Markdown 文档列表

#### `DEV-006` 单个设计文档读取

- 目标：验证设计文档查看能力
- 前置条件：存在指定设计文档
- 步骤：
1. 调用 `GET /rest/dev/design/{filename}`
- 预期结果：
1. 返回文档名和内容

#### `DEV-007` 设计文档 ZIP 下载

- 目标：验证设计文档打包下载
- 前置条件：设计目录存在 Markdown 文件
- 步骤：
1. 调用 `GET /rest/dev/design/download.zip`
- 预期结果：
1. 返回 ZIP
2. 压缩包中包含设计文档

#### `DEV-008` 反馈提交与列表

- 目标：验证意见反馈基础链路
- 前置条件：无
- 步骤：
1. 调用 `POST /rest/dev/feedback/`
2. 调用 `GET /rest/dev/feedback/`
- 预期结果：
1. 成功写入反馈
2. 列表可见新反馈

#### `DEV-009` 反馈 ZIP 导出

- 目标：验证反馈导出与图片资产打包
- 前置条件：至少存在一条含图片的反馈
- 步骤：
1. 调用 `GET /rest/dev/feedback/export.zip`
- 预期结果：
1. 返回 ZIP
2. ZIP 中包含 `feedbacks_report.md` 与图片资产

#### `DEV-010` 反馈删除

- 目标：验证反馈删除操作
- 前置条件：存在目标反馈
- 步骤：
1. 调用 `DELETE /rest/dev/feedback/{feedback_id}`
- 预期结果：
1. 删除成功
2. 列表中不再出现该反馈

### 6.5 前端公开页面

#### `UI-001` 路由收口正确

- 目标：验证只暴露正式页面
- 前置条件：前端已构建
- 步骤：
1. 打开 `/chat`、`/templates`、`/reports`、`/settings`
2. 打开未知路径
- 预期结果：
1. 正式路径可访问
2. 未知路径回落到 `/chat`

#### `UI-002` 模板列表页提供导入与新建入口

- 目标：验证模板入口完整性
- 前置条件：前端已启动
- 步骤：
1. 打开 `/templates`
- 预期结果：
1. 可见 `导入模板`
2. 可见 `新建模板`

#### `UI-003` 模板详情页支持保存与导出

- 目标：验证模板编辑工作台主动作
- 前置条件：存在一个模板
- 步骤：
1. 打开模板详情
2. 修改基础信息
3. 触发保存和导出
- 预期结果：
1. 保存成功
2. 导出链接正确

#### `UI-004` 对话页历史与发送链路可用

- 目标：验证前端对话页主交互
- 前置条件：系统设置就绪
- 步骤：
1. 打开 `/chat`
2. 发送消息
3. 检查会话历史、发送状态、动作面板
- 预期结果：
1. 消息可发送
2. 历史会话可切换
3. 动作面板能渲染参数和诉求确认

#### `UI-005` 报告中心页不暴露实例概念

- 目标：验证公开语义收口
- 前置条件：无
- 步骤：
1. 打开 `/reports`
- 预期结果：
1. 页面引导用户从对话进入报告详情
2. 不展示实例列表入口

#### `UI-006` 报告详情页显示模板实例与生成结果

- 目标：验证聚合视图页面
- 前置条件：存在报告
- 步骤：
1. 打开 `/reports/{reportId}`
- 预期结果：
1. 可见模板实例
2. 可见生成结果

#### `UI-007` 设置页提供保存、测试、重建索引

- 目标：验证系统设置主操作反馈
- 前置条件：无
- 步骤：
1. 打开 `/settings`
2. 点击保存、测试连接、重建模板索引
- 预期结果：
1. 操作反馈以内联消息显示

#### `UI-008` 反馈入口位于应用壳头部

- 目标：验证反馈入口收口到统一壳
- 前置条件：无
- 步骤：
1. 打开任一页面
- 预期结果：
1. 顶部可见反馈入口
2. 不在侧边栏底部重复放置

## 7. 用例与自动化映射

| 资产类型 | 覆盖内容 | 对应资产 |
|---|---|---|
| 后端自动化测试 | 路由、应用服务、结构校验 | `src/backend/tests/*.py` |
| 前端自动化测试 | 页面、路由、API 适配、组件交互 | `src/frontend/src/**/*.test.tsx` |
| 深度 API 冒烟 | 跨接口真实主链路 | `scripts/testing/deep_api_smoke.py` |
| 统一执行入口 | 例行回归 | `scripts/testing/run_functional_regression.ps1` |

## 8. 通过标准

- 关键主链路无阻断缺陷：
  - 模板 CRUD/导入导出
  - 对话模板匹配与参数收集
  - 诉求确认与报告生成
  - 报告聚合视图与文档下载
- 自动化资产可重复执行
- 测试报告中明确记录覆盖范围、未覆盖项、风险与证据
