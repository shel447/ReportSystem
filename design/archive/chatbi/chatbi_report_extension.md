# ChatBI 报告扩展专题

> 本文档只说明报告系统如何在 ChatBI 外层协议不变的前提下扩展报告相关载荷。

## 1. 权威来源

- [接口契约与 ChatBI 对齐](../report_system/04-接口契约.md)
- [核心业务模型与规范 Schema](../report_system/02-核心业务模型与规范Schema.md)

## 2. 扩展原则

- 不改 ChatBI 外层请求字段
- 不改 ChatBI 外层响应字段
- 仅在 `ask` 与 `answer` 的报告载荷部分做兼容式扩展
- 不额外定义第二套对话协议

## 3. 报告扩展点

### 3.1 Ask 扩展

在 `confirm_params` 阶段，扩展：

```json
{
  "reportContext": {
    "templateInstance": {}
  }
}
```

### 3.2 Answer 扩展

在 `answerType = REPORT` 时，扩展：

```json
{
  "reportId": "rpt_001",
  "status": "generating",
  "report": {},
  "templateInstance": {},
  "documents": [],
  "generationProgress": {}
}
```

### 3.3 Report 资源扩展

`GET /reports/{reportId}` 返回的 `answer` 必须与 `/chat` 中 `REPORT.answer.answer` 结构等价。

## 4. 扩展清单

- `ask.reportContext.templateInstance`
- `REPORT.answer.answer.report`
- `REPORT.answer.answer.templateInstance`
- `REPORT.answer.answer.documents`
- `REPORT.answer.answer.generationProgress`
- `POST /reports/{reportId}/document-generations`
