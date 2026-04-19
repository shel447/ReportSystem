# 设计方案 Change Log

本文件记录 `design/` 维度的正式设计方案变更。

记录原则：

- 只记录已经确认采用的设计方案变化
- 聚焦“为什么改、改了什么、影响哪些正式设计文档”
- 不重复记录纯代码实现细节；实现落地请见 [report_system/implementation/change_log.md](report_system/implementation/change_log.md)

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
