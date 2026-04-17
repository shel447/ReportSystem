# 定时任务模块实现（归档）

## 1. 状态说明

`scheduling` 相关代码当前未挂载公开路由，不属于公开主链路实现文档范围。

公开业务面当前以以下路由为准：

- `/rest/chatbi/v1/templates/*`
- `/rest/chatbi/v1/chat*`
- `/rest/chatbi/v1/reports/*`
- `/rest/chatbi/v1/parameter-options/resolve`

---

## 2. 保留价值

本文件保留的目的仅为后续恢复专题时提供上下文：

- 历史领域模型与仓储设计
- run-now 语义与执行记录结构
- 报告时间映射思路

当前版本不对这些能力提供公开契约承诺。

---

## 3. 恢复时建议

若后续恢复调度能力，建议先完成：

1. 新版 API 契约设计并并入 `design_api.md`
2. 与 `reports` 聚合模型的对象边界重审
3. 调度失败重试和幂等策略定义
4. 与用户隔离、配额治理、审计字段的一致性校验
