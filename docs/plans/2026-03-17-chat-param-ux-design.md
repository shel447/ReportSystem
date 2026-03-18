# 对话模板匹配提示与日期控件优化设计

日期：2026-03-17

## 背景
当前对话流程在模板自动匹配后直接进入补参提示，但用户无法在同一条消息中看到“已匹配模板”的明确提示；同时补参控件对日期类参数使用普通文本输入，体验不符合预期。

## 目标
- 在同一条补参消息中展示已匹配的模板名称。
- 日期类参数使用日期控件输入。

## 非目标
- 不改变模板匹配逻辑。
- 不引入新的参数校验规则。
- 不调整候选模板交互与排序。

## 方案概述
采用“action 元数据 + 前端渲染”的方式：后端在 `ask_param` action 中附带 `template_name`，前端在补参区顶部展示“已匹配模板：XXX”。日期控件由参数 `input_type` 判断（`input_type == "date"`）。

## 架构与组件
- 后端：
  - `chat_flow_service.build_ask_param_action` 添加 `template_name`（来自 `state.report.template_name`）。
  - `/api/chat` 流程不新增额外消息，仅透传 action 字段。
- 前端：
  - `ask_param` UI 增加模板提示行。
  - 参数输入控件根据 `param.input_type` 渲染 `type="date"` 或 `type="text"`。

## 数据流
1. 用户输入“制作设备巡检报告”。
2. 后端模板匹配成功并锁定模板。
3. 缺参时返回 `ask_param` action，包含 `param` 与 `template_name`。
4. 前端在同一条消息内：
   - 展示“已匹配模板：XXX”。
   - 渲染补参控件。
5. 用户补参后继续流程直至生成报告。

## 接口与兼容性
- `ask_param` action 新增字段：`template_name`（可选）。
- 若前端未使用该字段，仍保持兼容。

## 错误处理
- `template_name` 为空时不展示提示行。
- 未识别的 `input_type` 回退为文本输入。

## 测试策略
- 后端单测：`build_ask_param_action` 返回 `template_name`。
- 前端渲染：`input_type == date` 时输入控件类型为 `date`。
- 回归：缺参流程与模板匹配流程不受影响。
