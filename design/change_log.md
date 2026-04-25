# 设计方案 Change Log

本文件记录 `design/` 维度的正式设计方案变更。

记录原则：

- 只记录已经确认采用的设计方案变化
- 聚焦“为什么改、改了什么、影响哪些正式设计文档”
- 不重复记录纯代码实现细节；实现落地请见 [report_system/implementation/change_log.md](report_system/implementation/change_log.md)

## 2026-04-25 删除后路径引用收口

- 变更动机：
  - `docs/` 目录以及 `design/archive/`、`design/chatbi/`、`design/openapi/`、`design/spec.md`、`design/story.md`、`design/deployment_guide.md`、`design/report_sample.md` 已从当前工作树删除。
  - 剩余入口文档不能继续链接或推荐这些已删除材料。
- 设计决策：
  - `README.md` 的仓库结构和文档导航移除 `docs/` 与已删除设计辅助文档。
  - `design/README.md` 只保留 `report_system/`、`report_system/implementation/`、`change_log.md` 和 `biz_requirement.md` 四类入口。
  - `design/report_system/README.md` 的治理规则移除已删除的 `chatbi/openapi/archive` 目录引用，改为说明历史材料已退出主阅读路径。
  - `design/change_log.md` 中历史影响范围里指向已删除文件的 Markdown 链接改为纯文本历史路径，避免形成失效链接。
- 影响范围：
  - [README.md](../README.md)
  - [README.md](README.md)
  - [report_system/README.md](report_system/README.md)
- 风险与后续：
  - `design/biz_requirement.md` 是设计团队原始输入来源，仍保留历史路径文字，不按当前目录结构改写。

## 2026-04-25 非权威文档口径清理

- 变更动机：
  - `design/report_system/` 已明确成为当前方案设计权威来源，但根层摘要、测试文档和历史材料入口仍存在旧路径、旧字段或旧目录名，容易被误读为当前口径。
  - `biz_requirement.md` 需要继续作为设计团队原始输入来源保留，不能按当前实现口径改写。
- 设计决策：
  - 刷新 `design/spec.md` 与 `design/story.md`，只保留当前报告主系统摘要和业务叙事。
  - 更新 `design/README.md`，明确 `biz_requirement.md` 是原始输入来源，历史计划和演示材料只用于追溯。
  - 修正部署说明中的仓库名、路径和 Python 版本要求。
  - 刷新 `docs/testing/functional-use-cases.md`，移除旧 `design/design_*`、旧模板字段、旧实例资源和旧 `generated_content` 口径。
  - 为 `docs/`、`docs/plans/`、`docs/presentations/` 增加入口说明，声明日期型计划和演示资料是历史快照，不作为当前设计依据。
- 影响范围：
  - [README.md](../README.md)
  - [README.md](README.md)
  - `design/spec.md`、`design/story.md`、`design/deployment_guide.md`（后续已删除）
  - `docs/` 下测试、计划和演示材料（后续已删除）
- 风险与后续：
  - 归档目录、历史计划和历史测试报告中的原文仍可能包含旧词汇；这些文档已通过入口说明降级为追溯材料，不再作为当前方案依据。

## 2026-04-22 模板 `dataset.source` 内联数据源

- 变更动机：
  - 现有模板里 `dataset.sourceType = sql` 只通过 `sourceRef` 引用外部 SQL 定义，模板本身不保存 SQL 原文，导致模板导入导出和独立审阅时无法直接看到真实数据源定义。
  - `sql` 与 `api` 两类数据源都需要一个简单、统一、强约束的入口字段，不适合再拆成复杂对象结构。
- 设计决策：
  - `DatasetDefinition` 正式取消 `sourceRef`，统一改为 `source`。
  - `source` 始终是字符串：
    - `sourceType = sql` 时，`source` 保存 SQL 模板
    - `sourceType = api` 时，`source` 保存 API URL
  - SQL 返回字段、API 请求参数、API 响应体都视为外部已约定内容，不在模板中显式配置。
  - SQL 模板占位符语法本轮不做正式标准化；示例中的写法只用于表达“运行时会结合参数实例化”。
- 影响范围：
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/schemas/report-template.schema.json](report_system/schemas/report-template.schema.json)
  - [report_system/examples/report-template.example.json](report_system/examples/report-template.example.json)
- 风险与后续：
  - 如果后续需要规范 SQL 模板占位符语法，应单独追加一轮运行时模板实例化规则设计，而不是在本轮继续扩张 `DatasetDefinition`。

## 2026-04-19 旧 `design/implementation/` 目录归档

- 变更动机：
  - 当前正式实现设计已经完全收敛到 `design/report_system/implementation/`，而 `design/implementation/` 仍作为旧入口残留在根阅读路径里，造成两套实现目录并存的误解。
  - 继续保留该目录在正式入口中，会削弱主设计包“唯一权威设计源”的治理边界。
- 设计决策：
  - 将 `design/implementation/` 整体归档到 `design/archive/legacy-implementation/`。
  - `design/README.md` 的正式实现入口统一切换为 `design/report_system/implementation/README.md`。
  - 历史文档中仍需追溯旧实现映射时，统一从归档目录读取，不再把旧目录作为当前实现设计来源。
- 影响范围：
  - [README.md](README.md)
  - [report_system/README.md](report_system/README.md)
  - [biz_requirement.md](biz_requirement.md)
  - `design/archive/` 下历史归档材料（后续已删除）
- 风险与后续：
  - 若仓库外仍有旧链接直接指向 `design/implementation/*`，需要后续按需补充跳转说明或继续清理引用。
  - 后续新增实现设计只允许进入 `design/report_system/implementation/`，不得在根目录再恢复并行实现目录。

## 2026-04-19 scoped 参数补强

- 关联提交：
  - GitHub PR `#15`
  - merge commit `e8e9371`
- 变更动机：
  - 在上一轮模板/模板实例重构后，核心模型已经允许参数定义出现在模板根、目录、章节多个层级。
  - 但最近一次代码级 review 发现，运行时链路和 UI 交互仍然偏向“只处理根参数”，这会导致 scoped 参数设计虽然存在于 schema 中，却不能稳定参与补参、确认、重新生成。
- 设计决策：
  - 参数作用域正式定义为“根参数 + 目录参数 + 章节参数”统一构成一套可见参数集合。
  - 对话运行时在参数抽取、缺参判断、参数确认、模板实例重建时，都必须基于整棵模板树递归收集参数定义，而不能只读取模板根 `parameters`。
  - 模板实例在用户补参后，最新参数状态必须同时反映到：
    - 顶层 `templateInstance.parameters`
    - 目录级 `catalog.parameters`
    - 章节级 `section.parameters`
  - `multi=true` 的参数不再视为“模型保留但交互降级”，而是正式要求前端支持多值输入/选择。
- 影响范围：
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
- 风险与后续：
  - 运行时真实环境仍依赖 sqlite 本地表结构与当前 ORM 模型一致；若开发环境使用了旧库文件，仍可能出现“设计已更新、运行时报表缺列”的环境性故障。
  - 后续所有设计方案调整，统一继续追加到本文件，不再分散写入其它说明页。

## 2026-04-19 表定义与运行时数据库分离

- 变更动机：
  - `src/backend/report_system.db` 此前被纳入 Git 跟踪，但它本质上是本地运行时自动生成的 SQLite 文件。
  - 当前仓库中的 `report_system.db` 已明显落后于正式 ORM 模型与设计文档，继续把它当作表定义载体，会导致“ORM、设计、实际库文件”三套结构长期漂移。
- 设计决策：
  - 运行时唯一建表来源继续保持为 `src/backend/infrastructure/persistence/models.py` + `Base.metadata.create_all(...)`。
  - 新增受版本管理的 SQL 初始化稿 `src/backend/infrastructure/persistence/schema_init.sql`，用于初始化、审阅与结构比对。
  - `src/backend/report_system.db` 明确降级为本地运行时文件，不再纳入版本跟踪。
  - SQL 初始化稿必须按当前 ORM 目标模型维护，不能再从历史 `report_system.db` 倒推。
- 影响范围：
  - [report_system/05-数据模型与持久化.md](report_system/05-%E6%95%B0%E6%8D%AE%E6%A8%A1%E5%9E%8B%E4%B8%8E%E6%8C%81%E4%B9%85%E5%8C%96.md)
  - `design/archive/legacy-implementation/database_schema.md`（后续已删除）
  - `design/deployment_guide.md`（后续已删除）
  - `src/backend/infrastructure/persistence/schema_init.sql`
- 风险与后续：
  - 当前仍未引入迁移框架，SQL 初始化稿与 ORM 的一致性需要在后续开发中显式维护。
  - 若其它设计文档仍引用已废弃的旧表或旧 `.db` 基线，需要继续按当前目标模型清理。

## 2026-04-19 `/chat` 流式报告增量 `delta`

- 变更动机：
  - 现有 `/chat` 流式协议只有 `steps` 和最终 `answer`，缺少一条专门表达报告内容增量变更的正式通道。
  - 前端若要边生成边渲染目录和章节，只依赖完整 `REPORT` 会造成载荷过重，且执行进度与内容 patch 语义混杂。
- 设计决策：
  - 在 `ChatStreamEvent` 顶层新增可选字段 `delta`，只用于流式报告内容 patch。
  - `steps` 继续只表达执行进度；`answer` 继续只表达最终完整结果。
  - 不新增 SSE 事件类型；`delta` 仍附着在现有统一事件包络上，生成过程通过顶层 `status=running` 判断。
  - `delta.action` 当前先收敛为：`init_report`、`add_catalog`、`add_section`。
  - `delta` 不进入非流式 `ChatResponse` 完成态，也不进入 `GET /reports/{reportId}`。
- 影响范围：
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/08-相对ChatBI的扩展点.md](report_system/08-%E7%9B%B8%E5%AF%B9ChatBI%E7%9A%84%E6%89%A9%E5%B1%95%E7%82%B9.md)
  - `design/chatbi/*` 与 `design/openapi/*`（后续已删除）
- 风险与后续：
  - `delta` 当前只覆盖目录和章节新增；若后续需要章节替换、组件更新、目录删除等动作，需要继续扩充动作枚举。
  - 前端必须明确区分 `steps`、`delta`、`answer` 三条通道，避免再次混淆。

## 2026-04-19 `ask.status` 对话级锁定标识

- 变更动机：
  - 参数确认后的“本轮不可继续修改”属于多轮对话里的消息级语义，不应继续下沉到参数对象自身。
  - 未来不止参数确认，其它类型的追问消息也需要统一表达“已回复、不可继续修改”。
- 设计决策：
  - 在 `Ask` 上新增正式字段 `status`，当前只支持 `pending | replied`。
  - `pending` 表示该追问仍可编辑、可提交；`replied` 表示该追问已经被后续回复消费。
  - `ask.status` 同时进入当前轮 `ChatResponse.ask` 与对话历史消息回显。
  - 保持 `TemplateInstance.parameterConfirmation.confirmed` 原有业务语义，不把参数确认态改造成消息级锁定态。
- 影响范围：
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - [report_system/08-相对ChatBI的扩展点.md](report_system/08-%E7%9B%B8%E5%AF%B9ChatBI%E7%9A%84%E6%89%A9%E5%B1%95%E7%82%B9.md)
  - [report_system/implementation/统一对话实现.md](report_system/implementation/%E7%BB%9F%E4%B8%80%E5%AF%B9%E8%AF%9D%E5%AE%9E%E7%8E%B0.md)
  - [report_system/implementation/前端实现.md](report_system/implementation/%E5%89%8D%E7%AB%AF%E5%AE%9E%E7%8E%B0.md)
  - `design/chatbi/*` 与 `design/openapi/*`（后续已删除）
- 风险与后续：
  - 当前只定义了 `pending | replied`，若后续出现“过期”“被替换”等场景，需要扩展状态枚举。
  - 历史消息回显若仍使用极简消息模型，需要继续把 `ask` 结构纳入正式消息对象。

## 2026-04-19 `reply.sourceChatId` 原始追问定位

- 变更动机：
  - 仅靠 `ask.status` 还不足以让服务端稳定回写“哪一条追问消息已被消费”。
  - 若继续依赖“最近一条待回复 ask”做隐式匹配，在多轮并发交互或历史回放场景下会产生歧义。
- 设计决策：
  - 在结构化 `reply` 上新增 `sourceChatId`，指向被回复的原始 assistant 追问消息。
  - 服务端必须基于 `sourceChatId` 回写对应消息的 `ask.status = replied`。
  - `sourceChatId` 对 `fill_params`、`confirm_params` 都是必填字段，不再允许隐式猜测。
- 影响范围：
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - [report_system/08-相对ChatBI的扩展点.md](report_system/08-%E7%9B%B8%E5%AF%B9ChatBI%E7%9A%84%E6%89%A9%E5%B1%95%E7%82%B9.md)
  - [report_system/implementation/统一对话实现.md](report_system/implementation/%E7%BB%9F%E4%B8%80%E5%AF%B9%E8%AF%9D%E5%AE%9E%E7%8E%B0.md)
  - [report_system/implementation/前端实现.md](report_system/implementation/%E5%89%8D%E7%AB%AF%E5%AE%9E%E7%8E%B0.md)
  - `design/chatbi/*` 与 `design/openapi/*`（后续已删除）
- 风险与后续：
  - 若未来允许一条 `reply` 同时消费多条历史追问，需要把单值 `sourceChatId` 扩展为数组或更通用的 source 引用模型。

## 2026-04-20 `ParameterValue.label` 与 `Reply.parameters` 精简回填

- 变更动机：
  - 原三元组字段名 `display` 与参数定义中的 `label` 并列存在，语义重复且容易引起实现歧义。
  - `Reply.parameters` 继续回传完整参数定义，会让前端重复提交静态结构，放大请求体，并模糊 `ask/templateInstance/reply` 三者的职责边界。
- 设计决策：
  - 正式将 `ParameterValue` 从 `{display, value, query}` 改为 `{label, value, query}`。
  - 模板、模板实例、外部候选值接口、诉求实例化继续复用完整 `ParameterValue` 三元组。
  - `Reply.parameters` 保留字段名，但语义收敛为参数值映射：`Record<parameterId, Scalar[]>`。
  - `fill_params` 允许只提交本轮修改子集；`confirm_params` 必须提交完整已生效值集。
- 影响范围：
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - `design/report_system/schemas/*.json`
  - `design/chatbi/*` 与 `design/openapi/*`（后续已删除）
- 风险与后续：
  - 运行时如果仍按旧 `display` 字段取值，实现阶段必须同步切到 `label`。
  - `Reply.parameters` 既然已经与 `Ask.parameters` 脱钩，后续实现中不得再把两者视为同构 DTO。

## 2026-04-20 `CompositeTable` 模板正式支持

- 变更动机：
  - `Report DSL` 早已支持 `CompositeTable`，但模板定义与编译规则长期只覆盖 `paragraph/table/chart/markdown`，导致 DSL 侧有能力、模板侧没有正式入口。
  - 当前业务已明确需要“设备档案式复合表”，其中基础信息、多个检查结果区块和总结区块都属于同一个复合表组件。
- 设计决策：
  - 在模板 `section.content.presentation.blocks[]` 中正式新增 `type = composite_table`。
  - `composite_table` 采用通用 `parts[]` 结构，不引入业务语义化的固定区块名。
  - `part` 只支持两类来源：
    - `query`：由 `datasetId` 生成普通子表
    - `summary`：模板定义固定总结行，模型只填每行内容，并生成无表头二维表
  - 基础信息也按 `query part` 处理，不再引入第三类 part。
  - 不允许在 `part` 内再嵌套 group；若业务上存在多个分区，直接拆成多个顺序 `part`。
- 影响范围：
  - [report_system/schemas/report-template.schema.json](report_system/schemas/report-template.schema.json)
  - [report_system/examples/report-template.example.json](report_system/examples/report-template.example.json)
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
- 风险与后续：
  - 当前仅完成设计层收敛，后续实现阶段需要同步补齐模板编译器，把 `composite_table` block 真正编译为 DSL `CompositeTable.tables[]`。
  - `summary part` 目前固定为无表头两列表，若后续要支持更复杂的总结表骨架，需要再扩展 `summarySpec`。

## 2026-04-20 接口字段命名统一为 lowerCamelCase

- 变更动机：
  - 公开接口中的字段命名必须保持单一规范，避免固定字段、动态参数键和示例载荷混用蛇形与小驼峰。
- 设计决策：
  - 所有公开接口 JSON 中的固定字段名统一使用 lowerCamelCase。
  - `reply.parameters`、动态参数源请求体这类 map 结构中的参数键，进入公开接口时也必须使用 lowerCamelCase 参数 id。
  - 错误码、枚举值、模板内部引用 id 不因本次调整而改名。
- 影响范围：
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/schemas/parameter-option-source-request.schema.json](report_system/schemas/parameter-option-source-request.schema.json)
  - `design/openapi/*`（后续已删除）
- 风险与后续：
  - 若后续把参数 id 直接暴露到更多公开接口对象中，应继续沿用 lowerCamelCase 口径。

## 2026-04-20 `TemplateInstance` 正式承载 `CompositeTable` 实例态

- 变更动机：
  - 仅调整模板 schema 不足以支撑复杂二次编辑；`TemplateInstance` 若不显式保存 `composite_table.parts[]` 的实例态，前端无法稳定读取复合表内部结构，重新生成也只能回退到模板快照现算。
  - `TemplateInstance` 本身就是“生成前”和“再生成前”的正式上下文，章节内容结构不能只留在模板快照里。
- 设计决策：
  - 在 `TemplateInstance.section` 上正式补 `content` 字段，并保持与模板 `section.content` 同构。
  - `TemplateInstance.section.content.presentation.blocks[]` 正式支持 `type = composite_table`。
  - `composite_table.parts[]` 在实例态保留与模板相同的顺序和结构；每个 `part` 新增 `runtimeContext`。
  - `query part` 通过 `runtimeContext.status/resolvedDatasetId/resolvedQuery/warnings` 记录最小运行态。
  - `summary part` 通过 `runtimeContext.status/resolvedPartIds/prompt/warnings` 记录最小运行态。
  - `section.runtimeContext` 继续只保留章节级执行上下文，不承载复合表结构本身。
- 影响范围：
  - [report_system/schemas/template-instance.schema.json](report_system/schemas/template-instance.schema.json)
  - [report_system/examples/template-instance.example.json](report_system/examples/template-instance.example.json)
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
  - `design/chatbi/*`（后续已删除）
- 风险与后续：
  - 当前只补到 `part` 级运行态，不继续缓存子表单元格结果或最终生成内容。
  - 实现阶段需要保证参数或诉求变化时，只重算受影响 `part.runtimeContext`，而不是破坏整个 `composite_table` 结构。

## 2026-04-21 Report DSL 增强参数与大纲回显

- 变更动机：
  - 生成后的报告需要在前台支持结构化编辑，单靠 `TemplateInstance` 回显不足以支撑“直接基于报告编辑”的场景。
  - 现有 DSL 中 `basicInfo` 和 `GenerateMeta` 只保留了最小元信息，无法直接回显全局参数、章节参数和章节大纲骨架。
- 设计决策：
  - 在 `basicInfo` 中新增 `parameters`，按 `Record<parameterId, Parameter>` 保存全局参数完整定义与当前取值。
  - 在 `GenerateMeta` 中新增 `parameters`，只保存章节本地参数。
  - 在 `GenerateMeta` 中新增 `outline`，包含 `requirement`、`renderedRequirement`、`items`。
  - `OutlineItem` 正式定义为：`id`、`sourceParameterId`、`value`；其中 `value` 是参数三元组中的 `value` 数组。
  - `GenerateMeta.question` 与 `outline.renderedRequirement` 同时保留且独立存在，前端和编译逻辑不得假定二者相等。
- 影响范围：
  - [report_system/schemas/report-dsl.schema.json](report_system/schemas/report-dsl.schema.json)
  - [report_system/examples/report-dsl.example.json](report_system/examples/report-dsl.example.json)
  - [report_system/02-核心业务模型与规范Schema.md](report_system/02-%E6%A0%B8%E5%BF%83%E4%B8%9A%E5%8A%A1%E6%A8%A1%E5%9E%8B%E4%B8%8E%E8%A7%84%E8%8C%83Schema.md)
  - [report_system/03-运行时流程与状态机.md](report_system/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E6%B5%81%E7%A8%8B%E4%B8%8E%E7%8A%B6%E6%80%81%E6%9C%BA.md)
  - [report_system/04-接口契约.md](report_system/04-%E6%8E%A5%E5%8F%A3%E5%A5%91%E7%BA%A6.md)
- 风险与后续：
  - 该调整会扩大 DSL 体积，实现阶段需要避免把 `TemplateInstance` 原样透传进 `Report DSL`。
  - 若后续需要把父 catalog 参数也显式回显到章节级，需要再单独扩展 `GenerateMeta.parameters` 的范围定义。
