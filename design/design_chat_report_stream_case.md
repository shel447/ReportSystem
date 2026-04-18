# 对话制报告接口串联案例

> 本案例文档完全派生自主设计包，不再单独定义新的返回结构。

## 1. 参考来源

- [运行时流程与状态机](report_system/03-运行时流程与状态机.md)
- [接口契约](report_system/04-接口契约.md)

## 2. 串联结论

1. 用户通过 `/chat` 发起 `generate_report`
2. 系统在 `/chat` 中完成模板匹配、参数收集、诉求确认
3. 确认生成后，系统通过统一对话 SSE 事件流式返回 `REPORT.answer.answer`
4. 报告完成后，`GET /reports/{reportId}` 返回同一份 `answer`
5. 文档生成统一通过 `POST /reports/{reportId}/document-generations`
6. 文档下载统一通过 `GET /reports/{reportId}/documents/{documentId}/download`

## 3. 特别约束

- 不存在独立 `/instances/*`
- 不存在独立模板实例接口
- 不存在独立报告再生成接口
- 模板选择是 `fill_params` 的一个特例
- 诉求确认通过 `confirm_params + ask.reportContext.templateInstance` 表达
