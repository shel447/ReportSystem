# 报告模板模块设计

## 1. 模板定位

模板是静态业务定义，不是运行态对象。系统只保留一套模板定义，作为模板目录、模板匹配、模板实例初始化和 Report DSL 构建的唯一来源。

## 2. 正式模板结构

`ReportTemplate` 目标态主结构固定为：

```json
{
  "id": "tpl_ops_daily_v1",
  "category": "ops_daily",
  "name": "运维日报模板",
  "description": "面向运维中心的日报模板",
  "parameters": [],
  "catalogs": []
}
```

约束：

- `category` 是唯一分类字段
- `description` 是模板说明
- 模板主结构保留“章节目录”概念，因此顶层使用 `catalogs`
- 不再以 `sections/subsections` 作为模板主轴
- 模板详细定义统一收敛在 `content` 概念之外的正式结构里，不再引入第二套顶层 DSL

## 3. 目录与章节模型

模板主结构为：

```text
catalogs -> sections
```

语义边界：

- `catalog`
  - 表示章节目录
  - 负责表达报告组织顺序和业务分组
- `section`
  - 表示可被确认、可被编辑、可被生成的内容节
  - 同时承载诉求层与执行层

每个 `section` 内部保留双层结构：

- `outline`
  - `requirement`
  - `items[]`
- `content`
  - `datasets[]`
  - `presentation`

说明：

- `outline` 是章节级容器
- `requirement` 是单句诉求
- `item` 是诉求要素
- `component` 不属于模板正式主结构，它是报告生成后的运行结果形态

## 4. 模板参数

参数定义位于 `parameters[]`。当前支持：

- `free_text`
- `date`
- `enum`
- `dynamic`

并支持：

- `interaction_mode = form | chat`
- `value_mode = label | key`
- `value_mapping.query`

参数与诉求要素通过 `param_ref` 关联，运行时统一收敛为三通道：

- `display`
- `value`
- `query`

补充规则：

- 当数据源方式是 SQL 时，蓝图侧看到的值与 SQL 实际使用值可能不同，因此映射能力必须定义在通用值映射层，而不是耦合成 `sql_mapping`
- 外部数据源参数解析必须遵循统一请求方法、请求体、响应体与容量限制规范，正式定义见 [design_report_dsl_export.md](design_report_dsl_export.md) 与 [design_api.md](design_api.md)

## 5. 模板实例的继承与偏移

模板实例不是第二套模板定义。

`TemplateInstance.base_template` 只需要保存模板快照的必要字段：

- `id`
- `category`
- `name`
- `description`
- `parameters`
- `catalogs`

模板实例目标态原则：

- 主体尽可能保持 `catalogs -> sections`
- application 层支持平铺 delta 输入输出
- 平铺 delta 只是交互视图，不是持久化真相

## 6. 模板诉求骨架可用度

系统内部维护三态：

- `reusable`
- `conditionally_reusable`
- `broken`

UI 只暴露二态：

- `not_broken`
- `broken`

判定规则：

- 修改槽位值：不影响骨架可用度
- 保留结构化诉求，但局部自由化：可能降为 `conditionally_reusable`
- 破坏关键诉求骨架：降为 `broken`

前台职责：

- 只回传完整结构和必要 delta
- 不负责判断“是否还能局部适用模板”

后台职责：

- 基于完整树结构评估骨架状态
- 将 UI 二态与内部三态同时维护

## 7. 导入导出

- 导入采用“预解析 -> 进入编辑器 -> 用户手动保存”
- 导出返回正式模板结构
- 导出文件名格式为 `模板名称-YYYYMMDD-HHMMSS.json`

## 8. 与 Report DSL 的关系

- 模板负责定义“用户想得到什么”和“系统准备如何获取”
- 模板实例负责表达“这次对话确认后的诉求与执行基线”
- `Report DSL` 负责表达“已经冻结、可导出、可归档的正式报告”

因此：

- 模板主结构是 `catalogs -> sections`
- `Report DSL` 主结构是 `catalogs -> sections -> components`
