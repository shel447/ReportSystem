**版本**: v0.7
**最后更新**: 2026-04-17
**状态**: 目标态规格基线

---

## 目录

1. [产品概述](#1-产品概述)
2. [目标态规格](#2-目标态规格)
3. [约束与行为边界](#3-约束与行为边界)
4. [DFX 规格基线](#4-dfx-规格基线)
5. [待支持特性清单](#5-待支持特性清单)
6. [修订历史](#6-修订历史)

---

## 1. 产品概述

### 1.1 产品定位

智能报告系统是一个以**报告生成**为主能力的统一智能助手，同时集成：

- 智能问数
- 智能故障
- 报告文档生成与下载

### 1.2 核心价值

| 价值维度 | 说明 |
|---------|------|
| 统一入口 | 同一对话入口承接报告、问数、故障三类能力 |
| 结构化确认 | 参数收集、诉求确认、确认生成保证链路可追踪 |
| 模板主轴清晰 | 模板与模板实例保留 `catalogs -> sections` 目录/章节语义 |
| 正式报告模型 | 报告实例主体为持久化 `Report DSL` |
| 文档闭环 | 同一份 Report DSL 驱动 Markdown / Word / PPT / PDF |
| 用户隔离 | 业务接口统一使用 `X-User-Id` 做数据隔离 |

---

## 2. 目标态规格

### 2.1 系统设置

- 支持 Completion / Embedding 全局配置
- 支持连接测试
- 支持模板语义索引重建
- 未配置系统设置时，对话生成与真实调用链路会明确报错，不回退 mock

### 2.2 报告模板

- 创建、编辑、删除、克隆、导出单模板 JSON
- 模板主结构采用：
  - 顶层：`id / category / name / description / parameters / catalogs`
  - 章节诉求：`outline.requirement + outline.items[]`
  - 执行链路：`content.datasets + presentation`
- 参数支持：
  - `free_text / date / enum / dynamic`
  - `interaction_mode = form | chat`
  - `value_mapping.query`
- 模板导入预解析支持：
  - 来源识别
  - 归一化
  - 校验
  - 冲突检测

### 2.3 统一对话模块

- `/chat` 默认空态，不自动恢复最近会话，也不预创建会话
- 首条真实用户消息发送后才创建 `conversation`
- 支持三类一级能力：
  - `report_generation`
  - `smart_query`
  - `fault_diagnosis`
- 采用单活任务模型：
  - 一个会话同一时刻只有一个 `active_task`
  - 任务切换需要确认
- 支持会话历史：
  - 新建会话
  - 切换会话
  - 删除会话
  - 消息级 fork

### 2.4 报告生成对话

- 模板匹配
- 参数收集
- 诉求确认
- 流式生成报告

参数收集支持混合模式：

- `form` 参数：返回 `ask_param`
- `chat` 参数：返回自然语言追问文本
- 同一模板内按参数顺序混排

诉求确认支持：

- 实例级目录/章节树展示
- 参数片段 inline 编辑
- 非参数文本编辑后节点可能导致骨架破坏
- `foreach` 展开
- 结构化诉求值注入执行链路

### 2.5 报告与文档

公开接口：

- `GET /rest/chatbi/v1/reports/{reportId}`
- `POST /rest/chatbi/v1/reports/{reportId}/document-generations`
- `GET /rest/chatbi/v1/reports/{reportId}/documents/{documentId}/download`

`GET /reports/{reportId}` 目标态返回：

- `reportId`
- `status`
- `report`
- `templateInstance`
- `documents`

说明：

- `report` 是正式 `Report DSL`
- `templateInstance` 用于支持报告诉求二次编辑和重新生成
- 文档生成接口不把类型写入 URL，而在请求体中声明 `formats`

### 2.6 动态参数辅助接口

公开接口：

- `POST /rest/chatbi/v1/parameter-options/resolve`

当前支持：

- 参数来源 `api:/...`（本地动态源）
- 参数来源 `http(s)://...`（外部动态源）
- 候选项统一输出：`items[].label / value / query`

### 2.7 智能问数与智能故障

- 智能问数：
  - 统一由对话模块路由进入
  - 返回结构化摘要和查询调试上下文
- 智能故障：
  - 返回故障现象、初步判断、风险等级、原因、建议
- 两者都支持在报告流程中显式切换

---

## 3. 约束与行为边界

### 3.1 公开业务资源边界

`/rest/chatbi/v1/*` 目标态公开业务面只保留：

- `templates`
- `chat`
- `reports`
- `parameter-options/resolve`

当前不公开：

- `/instances/*`
- `/scheduled-tasks/*`
- `/documents/*`

### 3.2 报告生成

- 所有 `required` 参数都必须显式确认
- 诉求确认统一发生在确认生成之前
- 模板实例 (`TemplateInstance`) 作为内部核心聚合持续维护，不提供独立公开资源
- 文档下载仅支持 report-scoped 路径
- PDF 首版通过 Word/PPT 派生转换生成

### 3.3 统一对话模块

- v1 不支持任务栈
- 问数后不会自动回到之前报告任务
- 当 `chat` 模式参数待收集时，普通自然语言优先作为参数答案
- 只有显式切换意图才允许中断当前报告流程

### 3.4 对话契约兼容

`POST /chat` 目标态对齐 ChatBI 契约：

- `conversationId`
- `chatId`
- `instruction`
- `question`
- `reply`
- `command.name`

当 `Accept: text/event-stream` 时，报告生成阶段以 ChatBI 事件模型流式返回 `REPORT`。

---

## 4. DFX 规格基线

### 4.1 统一错误响应

- 统一错误响应只覆盖失败场景，不改成功响应包裹方式
- 统一字段：
  - `error.code`
  - `error.category`
  - `error.message`
  - `error.details`
  - `error.retryable`
  - `error.request_id`

### 4.2 HTTP 状态码边界

- `400` 参数/结构非法
- `404` 资源不存在
- `409` 状态冲突、阶段不匹配
- `413` 请求体或业务对象规模超限
- `429` 接口限流
- `502` 上游依赖错误
- `503` 服务不可用或配置未就绪

### 4.3 接口治理

- 列表接口统一支持：
  - `page`
  - `page_size`
  - `sort_by`
  - `sort_order`
- 默认 `page_size = 20`
- 最大 `page_size = 100`
- 限流分级：
  - 读接口：`120 req/min/user`
  - 普通写接口：`30 req/min/user`
  - 重计算接口：`10 req/min/user`
  - 下载接口：`30 req/min/user`

### 4.4 容量上限

- 通用 JSON 请求体：`1 MB`
- 模板总 JSON：`512 KB`
- 模板参数数：`<= 50`
- 模板章节总节点数：`<= 200`
- 单章节诉求要素数：`<= 20`
- 单章节 datasets 数：`<= 10`
- 实例参数快照 JSON：`<= 128 KB`
- 单实例总 JSON：`<= 5 MB`
- 单文档文件：`<= 20 MB`
- 动态参数请求体：`<= 32 KB`
- 动态参数单次 `limit`：`<= 50`

### 4.5 数据保留策略

- 模板、报告、文档、会话历史默认长期保留
- 首版不自动做业务数据老化清理
- 通过调试信息摘要化、样本行限制、预览截断控制存储膨胀

---

## 5. 待支持特性清单

| 特性 ID | 特性名称 | 描述 | 优先级 | 当前状态 |
|--------|---------|------|--------|---------|
| TG-001 | 任务栈与挂起恢复 | 报告中途切问数/故障后可恢复原任务 | Medium | 未实现 |
| TG-002 | 会话分支树可视化 | 图形化展示 fork 关系与来源 | Medium | 未实现 |
| TM-001 | 模板版本管理 | 支持模板版本回滚与比较 | Medium | 未实现 |
| TM-002 | 模板导入落库策略可视化 | 在导入预解析后提供覆盖/副本策略指引 | Low | 未实现 |
| RP-001 | 报告章节级再生成 | 对报告或模板实例局部 section 重新生成 | Medium | 设计中 |
| RP-002 | 报告差异对比 | 对比两个报告版本或两个分支差异 | Medium | 未实现 |
| DOC-001 | Java Office 导出器接入 | Word / PPT 导出闭环 | High | 设计中 |
| DOC-002 | PDF 派生转换 | Word / PPT 转 PDF | High | 设计中 |
| DFX-001 | 统一异常中间件 | 运行时统一错误响应、错误码和 request_id 注入 | Medium | 未实现 |
| DFX-002 | 运行时接口限流 | 落地接口族分级限流器 | Medium | 未实现 |

---

## 6. 修订历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v0.7 | 2026-04-17 | Codex | 将规格从当前实现基线刷新为目标态规格，统一到 ChatBI 对齐、Report DSL 主体、模板 `catalogs -> sections`、以及文档生成闭环 |
