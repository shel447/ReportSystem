# DFX 接口治理与统一异常设计

> 本文档是 [总设计文档 (design.md)](design.md) 的子文档，描述系统在当前版本下的接口治理、统一异常、错误码、容量规格与数据保留策略。

---

## 1. 模块定位

本专题解决的问题不是“新增一个业务能力”，而是为现有所有 API 提供统一的对外治理基线，重点包括：

- 错误响应格式统一
- 错误码体系统一
- 分页、排序、限流与容量规格统一
- 数据保留与老化策略统一

本轮定位为**设计与规格收敛**，不直接实现运行时中间件、限流器或清理任务。

---

## 2. 统一错误响应模型

### 2.1 设计原则

- 只统一**错误响应**，不改现有成功响应载荷
- 错误契约优先服务 API 稳定性，前端提示文案在此基础上映射
- 错误码必须能脱离中文文案独立使用
- 不把上游大报文和敏感信息直接透传到客户端

### 2.2 统一响应结构

```json
{
  "error": {
    "code": "INSTANCE_SECTION_INDEX_INVALID",
    "category": "validation_error",
    "message": "章节索引非法。",
    "details": {
      "section_index": 12
    },
    "retryable": false,
    "request_id": "req_01HT..."
  }
}
```

### 2.3 字段说明

| 字段 | 含义 |
|------|------|
| `error.code` | 稳定错误码，供前后端、测试和日志系统使用 |
| `error.category` | 错误类别，用于快速归类和统计 |
| `error.message` | 面向调用方的可读错误文案 |
| `error.details` | 非必填，放结构化上下文，不放敏感内容 |
| `error.retryable` | 是否建议调用方重试 |
| `error.request_id` | 请求级唯一标识，便于排障 |

### 2.4 分类体系

- `validation_error`
- `not_found`
- `conflict`
- `state_invalid`
- `quota_exceeded`
- `rate_limited`
- `upstream_error`
- `service_unavailable`
- `internal_error`

### 2.5 HTTP 状态码边界

| HTTP | 使用边界 |
|------|----------|
| `400` | 参数缺失、结构非法、业务输入不合法 |
| `404` | 资源不存在 |
| `409` | 状态冲突、阶段不匹配、不可 fork/不可更新 |
| `413` | 请求体或业务对象规模超限 |
| `429` | 接口限流 |
| `502` | 上游 AI / 外部依赖错误 |
| `503` | 系统配置不完整、服务暂不可用 |

---

## 3. 错误码体系

### 3.1 命名空间

- `COMMON_*`
- `TEMPLATE_*`
- `CHAT_*`
- `INSTANCE_*`
- `DOCUMENT_*`
- `TASK_*`
- `SETTINGS_*`

### 3.2 典型错误场景

#### 3.2.1 通用

| 错误码 | 类别 | 说明 |
|--------|------|------|
| `COMMON_REQUEST_INVALID` | `validation_error` | 请求结构非法 |
| `COMMON_BODY_TOO_LARGE` | `validation_error` | 请求体超限 |
| `COMMON_RESOURCE_TOO_LARGE` | `validation_error` | 业务对象规模超限 |
| `COMMON_RATE_LIMITED` | `rate_limited` | 命中限流 |
| `COMMON_INTERNAL_ERROR` | `internal_error` | 未分类内部错误 |

#### 3.2.2 模板

| 错误码 | 类别 | 说明 |
|--------|------|------|
| `TEMPLATE_NOT_FOUND` | `not_found` | 模板不存在 |
| `TEMPLATE_SCHEMA_INVALID` | `validation_error` | schema 校验失败 |
| `TEMPLATE_PARAM_ID_DUPLICATED` | `validation_error` | 参数 ID 重复 |
| `TEMPLATE_OUTLINE_REFERENCE_INVALID` | `validation_error` | 章节引用或诉求要素引用失效 |
| `TEMPLATE_EXPORT_TARGET_NOT_FOUND` | `not_found` | 导出目标模板不存在 |

#### 3.2.3 对话

| 错误码 | 类别 | 说明 |
|--------|------|------|
| `CHAT_SESSION_NOT_FOUND` | `not_found` | 会话不存在 |
| `CHAT_TEMPLATE_NOT_FOUND` | `not_found` | 匹配或选择的模板不存在 |
| `CHAT_PARAM_INVALID` | `validation_error` | 参数值非法 |
| `CHAT_TASK_SWITCH_CONFIRM_REQUIRED` | `state_invalid` | 当前任务切换需要确认 |
| `CHAT_FORK_SOURCE_INVALID` | `conflict` | fork 来源无效 |
| `CHAT_UPDATE_BASELINE_NOT_FOUND` | `not_found` | 更新来源基线不存在 |

#### 3.2.4 实例

| 错误码 | 类别 | 说明 |
|--------|------|------|
| `INSTANCE_NOT_FOUND` | `not_found` | 实例不存在 |
| `INSTANCE_TEMPLATE_NOT_FOUND` | `not_found` | 创建实例时模板不存在 |
| `INSTANCE_SECTION_INDEX_INVALID` | `validation_error` | 章节索引非法 |
| `INSTANCE_BASELINE_NOT_FOUND` | `not_found` | 生成基线不存在 |
| `INSTANCE_REGENERATE_FAILED` | `upstream_error` | 重生成失败 |
| `INSTANCE_FORK_SOURCE_NOT_FOUND` | `not_found` | 来源消息或来源会话缺失 |

#### 3.2.5 文档

| 错误码 | 类别 | 说明 |
|--------|------|------|
| `DOCUMENT_NOT_FOUND` | `not_found` | 文档记录不存在 |
| `DOCUMENT_INSTANCE_NOT_FOUND` | `not_found` | 生成文档时实例不存在 |
| `DOCUMENT_FILE_NOT_FOUND` | `not_found` | 文档记录存在但物理文件丢失 |
| `DOCUMENT_GENERATION_FAILED` | `upstream_error` | 文档生成失败 |
| `DOCUMENT_DELETE_FAILED` | `internal_error` | 文档删除失败 |

#### 3.2.6 定时任务

| 错误码 | 类别 | 说明 |
|--------|------|------|
| `TASK_NOT_FOUND` | `not_found` | 任务不存在 |
| `TASK_SOURCE_INSTANCE_NOT_FOUND` | `not_found` | 源报告实例不存在 |
| `TASK_USER_QUOTA_EXCEEDED` | `quota_exceeded` | 用户任务数超过上限 |
| `TASK_GLOBAL_QUOTA_EXCEEDED` | `quota_exceeded` | 全局任务数超过上限 |
| `TASK_SCHEDULE_INVALID` | `validation_error` | cron 或调度配置非法 |
| `TASK_RUN_FAILED` | `upstream_error` | 立即执行失败 |

#### 3.2.7 系统设置

| 错误码 | 类别 | 说明 |
|--------|------|------|
| `SETTINGS_NOT_CONFIGURED` | `service_unavailable` | 系统设置未配置完整 |
| `SETTINGS_AUTH_FAILED` | `upstream_error` | 认证失败 |
| `SETTINGS_TIMEOUT` | `upstream_error` | 上游超时 |
| `SETTINGS_INDEX_REBUILD_FAILED` | `upstream_error` | 模板索引重建失败 |
| `SETTINGS_PROVIDER_INVALID` | `validation_error` | 配置内容不合法 |

---

## 4. API 接口治理规格

### 4.1 列表接口统一查询参数

所有列表类接口统一收敛到以下查询参数设计：

- `page`
- `page_size`
- `sort_by`
- `sort_order`

默认策略：

- 默认 `page_size = 20`
- 最大 `page_size = 100`
- 默认排序按 `created_at desc` 或模块主时间字段 `desc`

### 4.2 接口族分级限流

| 接口族 | 说明 | 规格 |
|--------|------|------|
| 读接口 | 列表、详情、设计文档读取 | `120 req/min/user` |
| 普通写接口 | 创建、更新、删除、暂停、恢复、clone | `30 req/min/user` |
| 重计算接口 | 聊天生成、实例创建、章节重生成、`run-now`、文档生成、系统设置测试/重建索引 | `10 req/min/user` |
| 下载接口 | 文档下载等二进制输出 | `30 req/min/user` |

> 说明：这是接口规格设计，不代表当前版本已经有运行时限流器。

### 4.3 请求体与业务对象规模上限

| 对象 | 上限 |
|------|------|
| 通用 JSON 请求体 | `1 MB` |
| 模板总 JSON | `512 KB` |
| 模板参数数 | `<= 50` |
| 模板章节总节点数 | `<= 200` |
| 单章节诉求要素数 | `<= 20` |
| 单章节 datasets 数 | `<= 10` |
| 实例 `input_params` JSON | `<= 128 KB` |
| 实例章节数 | `<= 300` |
| 单章节内容 | `<= 64 KB` |
| 单实例总 JSON | `<= 5 MB` |
| Markdown 文档文件 | `<= 5 MB` |

### 4.4 查询链路的既有上限

当前查询相关规格继续保留并纳入统一约束：

- 调试样本行数 `<= 10`
- 查询建议结果行数 `<= 50`
- 查询修复重试次数 `<= 3`

---

## 5. 数据保留与老化策略

### 5.1 首版原则

首版采用**整体长期保留**：

- 报告模板：默认长期保留
- 报告实例：默认长期保留
- 报告文档：默认长期保留
- 对话会话历史：默认长期保留
- 定时任务：默认长期保留
- 任务执行记录：默认长期保留

### 5.2 有界存储策略

虽然不自动清理核心业务数据，但仍通过“有界存储”控制膨胀：

- 不存完整上游响应报文
- 调试区只保留：
  - 摘要
  - 样本行
  - 错误摘要
  - 编译 SQL / Ibis / QuerySpec 等必要链路信息
- 预览字段、会话摘要、标题统一截断

### 5.3 文档文件策略

- 文档记录存在，则物理文件保留
- 删除文档记录时，同步删除物理文件
- 不额外保留“孤儿文件”长期存在

### 5.4 运行产物边界

以下内容不纳入正式业务保留语义：

- `report_system.db` 之外的本地运行缓存
- `__pycache__`
- 浏览器自动化缓存
- 构建缓存与本地临时日志

这些内容继续通过 `.gitignore` 与运行环境治理。

---

## 6. 与现有模块的衔接

### 6.1 与 API 文档的关系

- `design_api.md` 记录实际接口与交互流程
- 本文档提供其上层统一治理规则

### 6.2 与实例/文档模块的关系

- `design_instance.md` 负责说明实例、文档与生成基线的数据模型
- 本文档只补充：
  - 错误语义
  - 对象上限
  - 保留策略

### 6.3 与统一对话模块的关系

- `design_chat.md` 负责会话状态机、能力路由、参数追问
- 本文档补充：
  - 聊天错误分类
  - 会话历史的保留原则
  - 对话生成相关接口的限流级别

---

## 7. 待定专题：定时任务中的时间语义重构

### 7.1 当前现状

当前定时任务只有基础联动能力：

- `time_param_name`
- `time_format`
- `report_time`

这能表达“执行时间写回某个时间参数”和“执行时间写入报告时间”，但还不能清楚表达：

- 任务执行时间
- 报告时间
- 报告数据时间范围

三者之间的关系。

### 7.2 当前问题

当前创建任务时，用户很难直接理解：

- 哪个时间是“任务什么时候跑”
- 哪个时间是“这份报告代表哪一天/哪个时点”
- 哪个时间范围是“报告实际覆盖的数据窗口”

### 7.3 后续专题方向

后续专题固定沿以下方向展开：

- 模板声明 `time_slots`
- 定时任务绑定时间槽位并选择预置策略
- 同时保留：
  - `report_time`
  - `data_time_start`
  - `data_time_end`

该专题独立推进，不与当前 DFX 首版混合实现。

---

## 8. 实施边界

本轮仅完成：

- 设计文档收敛
- 规格与契约统一
- 错误码、限流、容量、保留策略的文档化

本轮不完成：

- 统一异常中间件实现
- 限流器实现
- 自动清理任务实现
- 定时任务时间语义重构实现


