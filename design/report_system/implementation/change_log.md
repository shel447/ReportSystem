# 实现设计 Change Log

本文件记录 `design/report_system/implementation/` 维度的实现设计变更。

记录原则：

- 只记录会影响实现分层、运行时职责、数据流或验证策略的设计实现调整
- 聚焦“实现上怎么落、改了哪些实现约束、验证如何变化”
- 不替代代码提交记录；业务方案层变更请见 [../../change_log.md](../../change_log.md)

## 2026-04-19 scoped 参数运行时修复

- 关联提交：
  - GitHub PR `#15`
  - merge commit `e8e9371`
- 背景问题：
  - 代码级 review 暴露出 3 个实现缺口：
    - 对话服务只按模板根参数做抽取和缺参判断
    - 前端只更新顶层 `templateInstance.parameters`
    - `multi=true` 的参数在 UI 上仍被降级为单值输入
- 实现设计调整：
  - `conversation` 应用服务改为递归收集模板根、目录、章节三层参数定义，并在以下环节统一复用：
    - 首轮问题参数抽取
    - 当前实例参数值合并
    - 缺参判断
    - ask 参数回显
  - `report_runtime.domain.services` 增加递归参数收集能力，用于：
    - 计算整棵实例树的有效参数值
    - 在实例物化时把 scoped 参数正确写回目录与章节节点
    - 在 `parameterConfirmation` 中按整棵实例树判断缺参
  - `ChatPage` 前端交互改为：
    - `multi=true + free_text` 使用多行输入控件
    - `multi=true + enum/dynamic` 使用多选控件
    - 提交时同步刷新嵌套在 `catalogs/sections` 下的 scoped 参数状态
- 受影响的实现设计主题：
  - [统一对话实现.md](统一对话实现.md)
  - [报告运行时实现.md](报告运行时实现.md)
  - [总体实现架构.md](总体实现架构.md)
- 验证要求更新：
  - 新增后端测试，锁住 scoped 参数抽取与缺参判断
  - 新增前端测试，锁住多值参数交互与模板实例嵌套参数同步
  - 全量验证基线维持：
    - `python -m pytest src/backend/tests -q`
    - `npm test`
    - `npm run build`
- 后续约束：
  - 从本次开始，所有实现设计调整都统一追加到本文件，不再只散落在专题实现文档中。
