# 设计方案 Change Log

本文件记录 `design/` 维度的正式设计方案变更。

记录原则：

- 只记录已经确认采用的设计方案变化
- 聚焦“为什么改、改了什么、影响哪些正式设计文档”
- 不重复记录纯代码实现细节；实现落地请见 [report_system/implementation/change_log.md](report_system/implementation/change_log.md)

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
  - [archive/README.md](archive/README.md)
  - [archive/legacy-implementation/README.md](archive/legacy-implementation/README.md)
  - [archive/legacy-entrypoints/README.md](archive/legacy-entrypoints/README.md)
  - [report_system/README.md](report_system/README.md)
  - [archive/legacy-entrypoints/design.md](archive/legacy-entrypoints/design.md)
  - [biz_requirement.md](biz_requirement.md)
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
  - [archive/legacy-implementation/database_schema.md](archive/legacy-implementation/database_schema.md)
  - [report_system/05-数据模型与持久化.md](report_system/05-%E6%95%B0%E6%8D%AE%E6%A8%A1%E5%9E%8B%E4%B8%8E%E6%8C%81%E4%B9%85%E5%8C%96.md)
  - [deployment_guide.md](deployment_guide.md)
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
  - [chatbi/02-核心协议对象.md](chatbi/02-%E6%A0%B8%E5%BF%83%E5%8D%8F%E8%AE%AE%E5%AF%B9%E8%B1%A1.md)
  - [chatbi/03-运行时交互流程.md](chatbi/03-%E8%BF%90%E8%A1%8C%E6%97%B6%E4%BA%A4%E4%BA%92%E6%B5%81%E7%A8%8B.md)
  - [chatbi/05-报告系统扩展映射.md](chatbi/05-%E6%8A%A5%E5%91%8A%E7%B3%BB%E7%BB%9F%E6%89%A9%E5%B1%95%E6%98%A0%E5%B0%84.md)
  - `design/openapi/reportsystem-openapi*.yaml|json`
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
  - [chatbi/02-核心协议对象.md](chatbi/02-%E6%A0%B8%E5%BF%83%E5%8D%8F%E8%AE%AE%E5%AF%B9%E8%B1%A1.md)
  - `design/openapi/reportsystem-openapi*.yaml|json`
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
  - [chatbi/02-核心协议对象.md](chatbi/02-%E6%A0%B8%E5%BF%83%E5%8D%8F%E8%AE%AE%E5%AF%B9%E8%B1%A1.md)
  - `design/openapi/reportsystem-openapi*.yaml|json`
- 风险与后续：
  - 若未来允许一条 `reply` 同时消费多条历史追问，需要把单值 `sourceChatId` 扩展为数组或更通用的 source 引用模型。
