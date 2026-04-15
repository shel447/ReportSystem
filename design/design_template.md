# 报告模板模块设计

> 本文档是 [总设计文档 (design.md)](design.md) 的子文档，描述报告模板在当前版本下的数据模型、章节双层结构与配置原则。

> 术语使用约定：本模块文档在业务语义上统一使用“诉求”体系；当出现 `outline`、`OutlineRequirement` 等旧结构名时，仅表示当前结构命名仍沿用历史实现。

---

## 1. 模板定位

报告模板承担两类职责：

- 面向用户表达“这份报告想分析什么”
- 面向系统表达“这份报告如何查询、如何渲染、如何生成内容”

因此，模板章节节点采用**双层共存**模型：

- **诉求层 (`outline`)**
  - 面向用户
  - 使用 `requirement + items[]` 描述章节诉求与表达口径
- **执行层 (`content / datasets / presentation`)**
  - 面向系统
  - 描述数据准备、内容生成和展示方式

两层不是二选一关系，而是同属于同一个章节节点。

---

## 1.1 术语边界

本模块统一使用以下术语：

### 诉求

诉求表示用户希望系统获取并表达的一段信息意图。

它具有以下特征：

- 用户可见
- 用户可改
- 不是最终报告正文
- 会继续驱动执行层生成结果

因此，早期文档中的“诉求”在业务语义上统一收敛为“诉求”。

### 诉求要素

诉求要素表示构成一段诉求的结构化成分。

它可能表示：

- 信息对象
- 查询条件
- 时间范围
- 指标
- 维度
- 阈值
- 排序方式
- 表达偏好

诉求要素不等于模板参数。

### 参数

参数是系统在模板级向用户收集的输入项，解决的是“系统要问用户什么”。

参数与诉求要素的关系是：

- 参数可以为诉求要素赋值
- 诉求要素不一定来自参数
- 有些诉求要素也可能来自默认值、映射规则或 `foreach` 局部变量

### 诉求实例

诉求实例表示在具体参数、局部变量和上下文绑定后形成的具体诉求表达。

它是执行层生成前的直接输入。

### 执行层

执行层表示系统为满足诉求而实际采取的查询、聚合、推理和生成链路。

总结：

- 诉求层回答“要什么”
- 执行层回答“怎么做”

兼容说明：

- 本阶段文档中，`outline`、`OutlineRequirement`、`outline_instance` 等旧名仍可能在结构字段和接口动作中出现
- 但其业务语义统一按“诉求定义 / 诉求实例”理解

---

## 2. 报告模板 (ReportTemplate)

```python
@dataclass
class ReportTemplate:
    id: str
    name: str
    description: str

    report_type: str
    category: str
    schema_version: str
    content: Dict[str, Any]

    created_at: datetime
    updated_at: datetime
    created_by: str
```

### 2.1 顶层字段说明

| 字段 | 作用 |
|------|------|
| `id` | 模板主键 |
| `name / description` | 模板名称与说明 |
| `report_type / category` | 用于模板过滤、排序、检索和基础业务分类 |
| `schema_version` | `content` 的整体结构版本 |
| `content` | 模板完整定义载荷，统一承载参数、章节树、匹配关键词、输出格式等详细结构 |

### 2.2 `content` 的整体结构

在逻辑模型上，模板仍以 `parameters / sections` 为主结构；只是它们在持久化模型中不再拆散到表顶层，而是统一封装到 `content` 中。

推荐结构示意：

```python
{
  "parameters": [...],
  "sections": [...],
  "match_keywords": [...],
  "output_formats": [...],
  "compat": {
    "content_params": [...],
    "outline": [...]
  }
}
```

这样处理的目的：

- 表顶层只保留检索、过滤、排序需要的元字段
- 模板详细定义完全受 `schema_version` 约束
- 后续模板结构演进时，优先升级 `content` schema，而不是频繁改表结构

---

## 3. 模板参数 (TemplateParameter)

```python
@dataclass
class TemplateParameter:
    id: str
    label: str
    input_type: str  # free_text / date / enum / dynamic
    interaction_mode: str  # form / chat
    required: bool
    multi: bool

    description: str
    default: Optional[Any]

    options: Optional[List[Any]]  # 兼容 string 列表与 {key,label} 对象列表
    source: Optional[str]
    value_mode: Optional[str]  # label | key (仅 enum/dynamic)
    value_mapping: Optional[Dict[str, Any]]  # 仅 enum/dynamic，沿用诉求要素映射结构
```

### 3.1 参数设计原则

- 参数是模板级输入，不属于单个章节
- 所有 `required` 参数都必须在对话中显式确认
- 参数支持结构化控件映射：
  - `free_text` -> 文本输入
  - `date` -> 日期控件
  - `enum` -> 单选/多选固定候选
  - `dynamic` -> 由 `source` 提供候选
- 参数收集方式支持：
  - `interaction_mode=form` -> 结构化表单追问
  - `interaction_mode=chat` -> 自然语言追问
- `form` 与 `chat` 可在同一模板中按参数顺序混排
- `multi=true` 主要用于：
  - `foreach` 展开
  - 多对象比较/统计类模板

### 3.2 参数追问模式与统一对话模块的关系

- `interaction_mode` 只定义“下一步如何问用户”，不改变参数的校验规则
- 当某个 `chat` 模式参数处于待收集状态时，用户的自然语言输入优先用于该参数提取
- 若用户显式表达“切到智能问数/智能故障”，统一对话模块仍允许切换任务，但必须先经过确认卡片

### 3.3 参数映射 (value_mode / value_mapping)

为保证“参数收集值 -> 诉求确认值 -> 执行查询值”语义一致，模板参数与诉求要素采用同构映射结构：

- `value_mode`
  - `label`：`value` 默认等于展示值
  - `key`：`value` 优先取稳定 key
- `value_mapping.query`
  - 定义执行层使用的 `query` 值映射
  - `on_unmapped` 默认 `error`

约束范围：

- 仅 `enum` / `dynamic` 参数支持该映射定义
- `free_text` / `date` 不引入映射字段，保持原语义

参数三通道语义固定为：

- `display`：用户可见值
- `value`：稳定语义值（规范值）
- `query`：执行层消费值（必须与真实数据口径对应）

未命中策略：

- 当执行层需要 `query` 且映射未命中时，必须报错阻断
- 不允许回退到 `value` 或 `display`

### 3.4 动态参数数据源接口

当 `input_type=dynamic` 时，模板参数通过 `source` 声明其候选值来源。

#### 模板字段约定

```python
@dataclass
class TemplateParameter:
    ...
    input_type: str  # dynamic
    source: Optional[str]  # e.g. api:/devices/list
    value_mode: Optional[str]  # label | key
    value_mapping: Optional[Dict[str, Any]]  # query 通道映射
```

约束：

- `input_type=dynamic` 时必须配置 `source`
- `source` 表示平台内部登记的数据源标识，而不是前端直连地址
- 前端只调用平台接口，由平台代理外部数据源

#### 前端 -> 平台

- 方法：`POST`
- 路径：`/rest/chatbi/v1/parameter-options/resolve`

请求体：

```json
{
  "template_id": "tpl_xxx",
  "param_id": "device_scope",
  "source": "api:/devices/list",
  "query": "华东",
  "selected_params": {
    "region": "east"
  },
  "limit": 10
}
```

字段规则：

- `template_id`：可选但推荐，用于审计和路由
- `param_id`：必填
- `source`：必填，取模板参数中的 `source`
- `query`：可选，模糊搜索关键字
- `selected_params`：可选，表示当前已解析出的其他参数，用于作为外部源查询上下文
- `limit`：可选，默认 `10`，最大 `50`

响应体：

```json
{
  "items": [
    { "label": "华东一大区", "value": "EAST_1", "query": "EAST_1" },
    { "label": "华东二大区", "value": "EAST_2", "query": ["E2A", "E2B"] }
  ],
  "meta": {
    "source": "api:/devices/list",
    "limit": 10,
    "returned": 2,
    "has_more": false,
    "truncated": false
  }
}
```

说明：

- v1 统一采用 `label/value/query` 候选项结构
- 现有历史 `options: string[]` 仅保留兼容显示入口
- 若同时存在 `choices` 与 `options`，前端优先使用 `choices`

#### 平台 -> 外部数据源

- 方法：`POST`

请求体：

```json
{
  "request_id": "req_xxx",
  "source": "api:/devices/list",
  "query": "华东",
  "context": {
    "template_id": "tpl_xxx",
    "param_id": "device_scope",
    "selected_params": {
      "region": "east"
    }
  },
  "limit": 10
}
```

响应体：

```json
{
  "items": [
    { "label": "华东一大区", "value": "EAST_1", "query": "EAST_1" }
  ],
  "total": 1,
  "has_more": false
}
```

平台归一化规则：

- 平台只接受 `items[].label/value/query`
- `value` 在 v1 只支持标量：`string | number | boolean`
- `query` 在 v1 支持标量或标量数组：`scalar | scalar[]`
- 平台按内部上限对返回结果做二次截断

#### 规格限制

- 默认 `limit=10`
- 最大 `limit=50`
- 请求体上限：`32 KB`
- 响应项总数上限：`50`
- 单项长度建议：
  - `label <= 64`
  - `value <= 128`
  - `query` 标量长度建议 `<= 128`
- 外部调用超时：`3s`
- v1 不自动重试

#### 失败语义

动态参数取值失败时：

- 返回空 `items`
- 携带可重试错误语义
- 不直接打断当前报告对话流程

推荐错误码：

- `PARAM_SOURCE_INVALID`
- `PARAM_SOURCE_TIMEOUT`
- `PARAM_SOURCE_UPSTREAM_ERROR`
- `PARAM_SOURCE_RESPONSE_INVALID`
- `PARAM_SOURCE_LIMIT_EXCEEDED`

---

## 4. 章节双层模型 (TemplateSection)

```python
@dataclass
class TemplateSection:
    title: str
    description: str

    foreach: Optional[ForeachConfig]
    outline: Optional[OutlineRequirement]  # 业务语义：章节诉求定义

    content: Optional[SectionContent]
    subsections: List["TemplateSection"]
```

### 4.1 章节层职责拆分

| 层 | 字段 | 面向对象 | 作用 |
|----|------|----------|------|
| 诉求层 | `outline` | 用户/对话助手 | 组织章节诉求、确认大纲、补齐章节级变量 |
| 执行层 | `content` | 系统运行时 | 查询数据、调用 AI、渲染 Markdown |
| 结构层 | `subsections / foreach` | 两者共享 | 控制章节树与实例化展开 |

### 4.2 变量命名空间

模板运行时统一支持三类占位符：

- `{param_id}`：模板级参数
- `{$var}`：`foreach` 局部变量
- `{@item_id}`：当前章节诉求要素

其中 `{@item_id}` 不仅能出现在章节诉求文本中，也能出现在执行层文本字段里，例如：

- `section.title`
- `section.description`
- `datasets[].source.query`
- `datasets[].source.description`
- `datasets[].source.prompt`
- `presentation.template`

---

## 5. 诉求层 (OutlineRequirement)

```python
@dataclass
class OutlineRequirement:
    requirement: str
    items: List[RequirementItem]
```

```python
@dataclass
class RequirementItem:
    id: str
    type: str
    hint: str
    default: Optional[str]

    # 系统扩展字段
    param_id: Optional[str]
    options: Optional[List[Any]]  # 兼容 string 列表与 {key,label} 对象列表
    source: Optional[str]
    widget: Optional[str]
    multi: Optional[bool]
    value_mode: Optional[str]  # label | key
    value_mapping: Optional[Dict[str, Any]]
```

在业务语义上：

- `OutlineRequirement` = `章节诉求定义`
- `RequirementItem` = `诉求要素`

### 5.1 诉求要素类型

当前系统对齐最新版模板语义，并补充必要的系统扩展配置，常见类型包括：

- `indicator`
- `time_range`
- `scope`
- `threshold`
- `operator`
- `enum_select`
- `number`
- `boolean`
- `free_text`
- `param_ref`

### 5.2 诉求层设计原则

- `requirement` 是用户在大纲确认中直接感知的章节诉求表达
- `items[]` 是章节级诉求要素，不等同于模板全局参数
- `param_ref` 用于把模板参数直接映射为章节诉求要素值
- `param_ref` 绑定参数后，完整继承参数的 `display / value / query`
- `param_ref` 不再单独定义映射规则，避免参数与诉求双源配置冲突
- 诉求要素支持默认值、候选项、动态来源和控件语义
- 诉求要素值区分 `display / value / query` 三类用途，不再假设“展示值等于执行值”
- `options` 兼容两种候选项形态：`["总部", "省公司"]`（历史字符串模式）与 `[{"key":"hq","label":"总部"}]`（推荐 key/label 模式）

### 5.3 作用域规则

- `{param_id}`：全模板可见，语义固定为参数 `display`（用户可见值）
- `{$var}`：当前 `foreach` 节点及其子树可见
- `{@item_id}`：兼容写法，等价于 `{@item_id.display}`
- `{@item_id.display}`：诉求展示值（面向用户可读）
- `{@item_id.value}`：诉求规范值（面向结构化表达，通常是稳定 key）
- `{@item_id.query}`：执行查询值（由 `value_mapping.query` 计算得到）
- 参数占位符不新增 `{param_id.query}` / `{param_id.value}`，执行值必须通过 `param_ref` 进入 `{@item_id.query}`
- 不允许同一路径上的诉求要素 `id` 重名覆盖

### 5.4 值映射 (value_mapping)

为避免执行层与 SQL 语义强绑定，诉求要素统一采用中性值映射定义：

```json
{
  "id": "scope",
  "type": "enum_select",
  "value_mode": "key",
  "options": [
    {"key": "hq", "label": "总部"},
    {"key": "prov", "label": "省公司"}
  ],
  "value_mapping": {
    "query": {
      "by": "key",
      "map": {
        "hq": "HQ",
        "prov": ["P1", "P2"]
      },
      "on_unmapped": "error"
    }
  }
}
```

规则说明：

- `value_mode=key` 时，`{@item_id.value}` 优先取稳定 key；`display` 仍展示 label。
- `value_mapping.query.map` 支持标量和标量数组，兼容等值和 `IN (...)` 场景。
- `on_unmapped` 默认 `error`，避免执行层在未知值上静默退化。
- `query` 通道是执行层通道，不等同于任何单一数据源类型（例如 SQL 只是其一种消费者）。

---

## 6. 执行层 (SectionContent)

```python
@dataclass
class SectionContent:
    datasets: List[SectionDataset]
    presentation: Dict[str, Any]
```

```python
@dataclass
class SectionDataset:
    id: str
    depends_on: List[str]
    source: DatasetSource
```

### 6.1 `source.kind`

当前执行层支持：

- `sql`
- `nl2sql`
- `ai_synthesis`

### 6.2 `presentation.type`

当前展示方式支持：

- `text`
- `value`
- `simple_table`
- `chart`
- `composite_table`

### 6.3 执行层设计原则

- 执行层负责“怎么查、怎么生成、怎么展示”
- 执行层允许显式引用诉求要素 `{@item_id}`
- 执行层本身不直接暴露给普通使用者编辑；在模板工作台中作为章节详情的独立页签维护

---

## 7. 双层映射关系

### 7.1 映射基线

映射关系采用“同章节节点双层共存 + 要素级显式绑定”：

- 一个章节节点同时持有 `outline`（诉求定义）与 `content`
- 执行层通过 `{@item_id.query}` 显式消费执行查询值
- 展示层通过 `{@item_id.display}` 消费可读值
- 运行时对章节诉求求值后，再解析执行层

### 7.2 对话生成时序

```mermaid
sequenceDiagram
    participant User as 用户
    participant Chat as 对话助手
    participant Template as 模板
    participant Runtime as 运行时

    User->>Chat: 确认模板参数
    Chat->>Template: foreach 展开 + 诉求实例化
    Template-->>Chat: 实例级诉求树
    User->>Chat: 修改/确认大纲
    Chat->>Runtime: 注入诉求值
    Runtime->>Runtime: 解析执行层占位符
    Runtime-->>Chat: 生成执行基线
```

### 7.3 结果形态

在实例生成时，系统内部会形成两份相关快照：

- `confirmed_outline`
  - 业务语义：用户确认后的实例级诉求树
- `resolved_execution_baseline`
  - 用诉求值解析后的执行层基线

这两份快照共同构成报告实例的生成基线。

---

## 8. 模板工作台配置原则

模板编辑页按四个工作域组织：

- 基础信息
- 参数定义
- 章节工作台
- 结构预览

其中“章节工作台”内部按章节详情页签拆分为：

- `诉求`
- `执行链路`
- `同步状态`

结构预览支持三个视图：

- `诉求预览`
- `执行预览`
- `模板 JSON`

> JSON 预览是排查与迁移入口，不再作为主编辑方式。

当前模板工作台已为诉求要素提供类型化配置面，常见配置包括：

- `time_range`：时间控件与默认值
- `indicator / scope / enum_select`：固定选项或动态来源
- `param_ref`：绑定模板参数
- `number / threshold / boolean / operator`：专用配置面

---

## 9. 校验规则

模板保存前，前后端共同执行以下关键校验：

- 参数 `id` 唯一
- `enum` 至少有一个选项
- `dynamic` 必须配置 `source`
- `date` 不允许 `multi=true`
- `enum/dynamic` 支持 `value_mode` 与 `value_mapping`；`free_text/date` 不允许声明参数映射字段
- 参数 `value_mapping.query.on_unmapped` 默认 `error`
- `{@item_id}` 必须能在当前章节或祖先章节解析
- `param_ref` 必须绑定已有模板参数
- `param_ref` 绑定后必须继承参数映射，不允许局部覆写 `query` 映射
- `value_mapping.query.by=key` 时，要素候选项必须可产出稳定 key
- `value_mapping.query.map` 的 value 仅允许标量或标量数组
- `value_mapping.query.on_unmapped=error` 时，不允许回退到展示值继续执行
- `input_type=dynamic` 的候选项响应必须包含合法 `query` 值（标量或标量数组）
- `foreach` 禁止嵌套
- `content` 与 `subsections` 互斥
- `datasets.depends_on` 必须无环

---

## 10. Schema 同步项 (实施要求)

以下同步项属于实施阶段必须落地的契约，避免文档与校验器漂移：

- `src/backend/report_template_schema_v2.json`
  - 在 `Parameter` 定义中新增 `value_mode`、`value_mapping`
  - 约束 `value_mode/value_mapping` 仅对 `enum/dynamic` 生效
- `template_catalog` 模板校验
  - 校验 `param_ref` 的映射继承规则（禁止局部覆写）
  - 校验动态参数候选项 `query` 类型
- 动态参数接口适配层
  - 统一接受并透传 `items[].query`
  - 缺失或非法时返回 `PARAM_SOURCE_RESPONSE_INVALID`

---

## 附录

- 模板设计现在以 `parameters / sections` 为主结构
- 旧版 `content_params / outline` 仅保留兼容加载入口
- 单模板导出 JSON 默认导出可迁移定义，不导出运行期系统字段
- 模板导入采用“预解析 -> 编辑确认 -> 手动保存”流程，不支持直接写库
- 当前支持两类导入源：
  - 系统导出的模板 JSON
  - 外部 `ReportTemplate` 风格 JSON
- 当前冲突策略：
  - 无冲突：默认新建副本
  - 单一冲突：允许“新建副本”或“覆盖现有模板”
  - 多重同名冲突：只允许“新建副本”
- 模板导出文件名固定为 `模板名称-YYYYMMDD-HHMMSS.json`

## 实现文档

当前版本的核心技术实现说明见：

- [implementation/template_catalog.md](implementation/template_catalog.md)
- [implementation/database_schema.md](implementation/database_schema.md)
- [implementation/external_interfaces.md](implementation/external_interfaces.md)









