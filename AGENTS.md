# ReportSystem Agent Instructions

## 团队契约：设计先行、实现跟随

本项目采用“设计团队先设计，实现团队后实现”的协作流程。所有代理和工程师在修改业务能力时必须遵守以下契约。

### 设计资料的权威位置

- `design/report_system/` 是当前版本的方案设计来源，包含核心业务模型、业务流程、接口契约、数据模型、导出架构等产品与系统方案。
- `design/report_system/implementation/` 是实现设计文档目录，不是源代码目录。这里记录实现团队对当前方案设计的落地设计、模块职责和实现边界。
- `design/change_log.md` 是方案设计层面的变更记录。
- `design/report_system/implementation/change_log.md` 是实现设计、编码和验证层面的变更记录。

### 标准变更流程

1. 设计团队先更新 `design/report_system/*.md` 中相关方案设计文档。
2. 设计团队同步更新 `design/change_log.md`，记录方案设计变更。
3. 实现团队基于已更新的方案设计，先更新 `design/report_system/implementation/*.md` 中相关实现设计文档。
4. 实现团队再进行编码实现。
5. 实现团队完成必要验证后，更新 `design/report_system/implementation/change_log.md`，记录实现、验证结果和重要偏差。

### 实现约束

- 后端核心业务模型和业务流程必须以 `design/report_system/` 下的当前方案设计为准。
- 如果实现过程中发现方案设计缺口、冲突或需要新增行为，先暂停对该行为的代码假设，并更新设计或请求设计澄清，再继续编码。
- 前端可以在需要时推倒重来；前端实现不应反向改变后端核心业务模型和业务流程。
- 实现设计文档应在编码前更新，避免代码先行导致设计文档滞后。
- 文档变更、代码变更和验证记录应保持同一业务意图，不要只改其中一处。
