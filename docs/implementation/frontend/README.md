# 前端实现

## 1. 页面边界

前端只保留三条业务主线：

- 模板：`/templates`
- 对话：`/chat`
- 报告：`/reports`

开发支撑页保留：

- 系统设置
- 反馈
- 设计文档查看
- 报告本地设计器：`/reports/:reportId/designer`

## 2. 类型约束

前端类型必须直接映射正式 schema：

- `ReportTemplate`
- `TemplateInstance`
- `Report`
- `ReportAnswer`
- `ChatRequest/ChatResponse`

禁止保留：

- 旧 `sections` 根结构模板草稿
- 旧 `outline_content/generated_content/resolved_view` 运行态投影
- `instance` 独立资源类型

## 3. 模板编辑

模板工作台直接编辑：

- `parameters`
- `catalogs`
- `catalog.sections`
- `section.outline`
- `section.content`

导入预览直接消费 `normalizedTemplate`。

## 4. 对话与报告页

对话页负责：

- 展示 `ask`
- 根据 `ask.status` 判断当前追问是否仍可编辑
- 订阅 `/chat` 的流式事件，并区分：
  - `steps`
  - `delta`
  - 最终 `answer`
- 渲染完整 `templateInstance`
- 回传 `reply.sourceChatId`
  - 值固定取当前 assistant 追问消息的 `chatId`
  - 不允许前端按“当前最后一条消息”或“最近一个 pending ask”自行猜测
- 回传 `reply.parameters`
  - 固定为 `Record<parameterId, Scalar[]>`
  - 单值参数也使用长度为 1 的数组
- 参数值三元组正式使用 `{label, value, query}`
  - UI 展示默认读 `label`
  - 结构化回填时只提交 `value` 数组，不重复回传完整三元组
- 回传 `reply.reportContext.templateInstance`
- 在切换历史会话时，从消息流水中恢复最后一次 `ask/report` 状态

报告页负责：

- 使用 BI Engine 展示正式 `Report DSL`
- 展示随报告返回的完整 `templateInstance`
- 触发文档生成和下载
- 报告中心不依赖独立 `reports list` 接口，而是从最近会话中聚合已生成报告
- 前端模板/实例态类型仅声明 `text/table/chart/composite_table` 四类 presentation block；`paragraph/bullet/kpi/markdown` 不再作为可编辑模板块出现
- 前端必须保留 `text` block 的模板态 `properties.template` 与实例态 `properties.template/properties.content`
- 识别 `composite_table` 编译后的 `compositeTable` 组件，但不在前端自行重写编译逻辑
- 前端类型必须保留普通 `table` block 上的 `properties.mergeColumns/mergeRows` 与 `composite_table` part 上的 `tableLayout.mergeColumns/mergeRows`，展示或编辑时不得自行改写源列 key
- 模板定义已扩展 `properties.preferredType`、普通表格 `properties.columns/showTitle/defaultDisplayRows`、复合表 `tableLayout.columns/showTitle/defaultDisplayRows`；前端类型和渲染接入不在本轮实现范围，后续实现阶段再补齐
- 前端模板类型使用 `dynamic` 表达目录/章节动态展开，不再声明旧 `foreach` 字段；模板编辑页的普通循环输入写入 `dynamic.type = foreach`
- 前端实例态类型使用 `dynamicContext`，不再把 `foreachContext` 作为新响应字段依赖；`custom` 场景需能读取 `dynamicContext.url/nodeType`

补充要求：

- 报告详情页若要支持复杂二次编辑，不能只依赖当前极简 `TemplateInstance`
- `TemplateInstance` 需要直接提供：
  - `template`
  - 完整 `parameters`（含 options/values/runtimeContext）
  - `parameterConfirmation`
  - 完整 `section.content`（含 `presentation.blocks` 与 `composite_table.parts[].runtimeContext`）
  - 基于 `template + section.id/path` 的章节模板稳定回溯能力
- 前端不应再自行猜测“当前模板最新定义”来补齐历史实例缺失信息，否则重新生成结果会漂移
- 对于历史消息中的追问回显，前端应直接信任 `ask.status`，而不是再根据参数确认态二次推断是否可编辑

## 5. BI Engine 前端集成

### 5.1 依赖边界

- `src/frontend/vendor/bi-engine` 以 Git 子模块固定 BI Engine 仓库提交，不复制 Playground 应用代码。
- Vite alias 直接指向子模块中的 `@cloudsop/bi-engine`、`@cloudsop/bi-designer`、`@cloudsop/bi-signal` 源码。
- ReportSystem 的 TypeScript 编译只通过本地轻量声明门面检查本轮使用到的公共入口，不把 BI Engine 仓库内部尚未收敛的类型检查并入 ReportSystem 构建；运行时仍由 Vite 使用子模块源码。
- 不迁移 Playground 的演示列表、场景库、测试按钮、Copilot 验证台或 Ant Design 外壳。

### 5.2 统一预览

- `ReportDslPreview` 是正式报告和对话增量报告的统一预览入口。
- flow 报告递归渲染 `catalogs -> subCatalogs -> sections -> components`，每个组件交给 `BIEngine mode=view`。
- paged 报告使用 BI Designer 公开的 `applyAutoLayoutToDoc` 做一次规范化，再创建共享 editor store；只读预览、编辑和 JSON 下载都从该 store 读取，不再维护预览专用克隆或手写 grid 布局。
- paged 预览按 BI Designer 的页面顺序派生封面、总目录、章节目录、内容页和封底；虚拟页面只用于前端展示，不写入正式 `Report DSL`。
- flow 与 paged 预览都提供只读大纲栏。flow 点击目录或章节时滚动定位内容，paged 点击大纲节点时切换当前幻灯片。
- 类型判断优先读取 `structureType`，缺失时再读取 `basicInfo.reportType`；无法识别时展示明确错误。
- 报告详情页首屏以真实预览为主，导出、结构摘要、模板实例和原始 JSON 放入次级折叠区。

### 5.3 对话增量预览

- 对话页使用 reducer 将 SSE `init_report/add_catalog/add_section` 合并为部分 flow DSL。
- reducer 同时保留 `add_chapter/add_slide/add_section` 的 paged 定位语义，为后续 paged 生成链路预留消费能力。
- `init_report.report.structureType` 是必填字段；历史响应缺失时前端仅按 `flow` 兼容读取。
- 原始 delta 文本只作为折叠调试信息，不作为主要展示。

### 5.4 本地设计器工作台

- `/reports/:reportId/designer` 从报告详情进入，按 DSL 类型选择 `ReportEditor` 或 `PptEditor`。
- 编辑器通过统一 workspace helper 初始化：flow 直接创建 store，paged 先使用 `applyAutoLayoutToDoc` 规范化再创建 store。支持本地编辑、撤销、预览、重置和 DSL JSON 下载。
- 本轮不新增保存接口，不修改冻结后的 `ReportInstance`；存在未导出改动时，离开页面需要提示用户。

### 5.5 视觉样式

- 业务侧栏信息架构保持不变，所有业务页面统一使用窄图标栏；桌面宽度为 `64px`，小屏宽度为 `54px`。
- 页面背景使用浅灰，内容面使用白色，主色使用蓝色，边框使用浅灰分隔。
- 移除装饰性渐变、大圆角、厚阴影和衬线标题；卡片圆角控制在 `4px-8px`。
- 模板列表和报告列表使用紧凑行列表。业务页顶部使用单行工具栏，不再叠加通用大标题、英文 eyebrow 和说明段落。
- 预览大纲桌面默认宽 `220px` 且允许折叠为 `36px`；移动端固定保留约 `132px` 的窄栏。
- 本轮固定浅色主题，不增加明暗切换。

### 5.6 对话工作台

- `/chat` 使用专属工作台布局，不显示通用 `AppHeader` 和 `PageSection` 说明区。
- 桌面端从左到右依次为紧凑业务导航、可折叠会话列表、独立滚动的对话流与固定底部输入框、可收起且可拖动调宽的报告工作区。
- 首个可渲染报告 delta 到达后自动展开报告工作区。正式报告完成前只允许预览；完成后开放本地编辑。
- 报告工作区使用 `预览 / 编辑 / 详情` 三个标签：预览复用 `ReportDslPreview`，编辑按 `structureType` 选择 `ReportEditor` 或 `PptEditor`，详情以折叠区展示模板实例、增量事件和原始 DSL。
- 平板和移动端不并排展示对话与报告区域，改用 `对话 / 报告` 切换；会话列表以抽屉出现。
- 对话输入框固定在消息区底部，支持 Enter 发送、Shift+Enter 换行；助手消息不再套大卡片，用户消息只使用克制的浅灰气泡。

### 5.7 Demo Report DSL 模板

- 前端提供独立 demo 模板 fixture，用于 BI Engine 接入验证，不持久化到后台模板表。
- demo 生成过程允许本地 mock，但输出必须是正式 Report DSL 形状，并通过与 SSE 相同的 reducer 进入预览。
- fixture 至少覆盖 flow、paged、`text/table/chart/compositeTable/markdown`，以及 `line/bar/pie/scatter/radar/gauge/candlestick` 图表。
- paged fixture 的封面和封底使用正式 `cover/backCover` 字段，不再伪装成普通内容 slide；预览和编辑共享同一份 canonical DSL。
- demo 报告完成后允许进入聊天右侧本地编辑，但不提供后台保存或全屏报告路由。

## 6. 已知后续项

- ReportSystem 与 BI Engine 的 Report DSL 镜像需要继续按权威模型核对。
- 当前已知差异位于 `GenerateOutline.items[]` 的 `RequirementItem`：BI Engine 侧包含可选 `options`，并放宽了部分必填约束。本轮前端集成不修改 schema。

## 7. 删除项

- 实例页
- 定时任务页
- 任何面向旧 `/instances`、`/scheduled-tasks` 的 API client 和状态管理
