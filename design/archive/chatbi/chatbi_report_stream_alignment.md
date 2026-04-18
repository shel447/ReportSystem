# ChatBI 报告流式对齐专题

> 本文档只说明报告系统如何复用 ChatBI 的 SSE 事件模型进行流式报告生成。

## 1. 权威来源

- [运行时流程与状态机](../report_system/03-运行时流程与状态机.md)
- [接口契约与 ChatBI 对齐](../report_system/04-接口契约.md)

## 2. 对齐结论

- 不新增 `report_delta` 事件类型
- 报告增量统一通过 `eventType = answer` 返回
- SSE 事件类型继续使用：
  - `status`
  - `step_delta`
  - `ask`
  - `answer`
  - `error`
  - `done`

## 3. 生成骨架

1. `status(running)`
2. `step_delta(build_template_instance)`
3. `answer(REPORT skeleton)`
4. `step_delta(section finished)`
5. `answer(REPORT partial)`
6. `answer(REPORT completed)`
7. `done`

## 4. 关键约束

- `/chat` 流结束时返回的最终 `REPORT.answer.answer`
- 与 `/reports/{reportId}` 返回体中的 `answer`
- 必须结构等价
