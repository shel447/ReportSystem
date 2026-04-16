# 报告模板模块设计

## 1. 模板定位

模板是静态业务定义，不是运行态对象。当前系统只保留一套模板定义，作为模板目录、模板匹配和内部模板实例的唯一来源。

## 2. 唯一模板结构

`ReportTemplate` 正式结构固定为：

```json
{
  "id": "tpl_ops_daily_v1",
  "category": "ops_daily",
  "name": "运维日报模板",
  "description": "面向运维中心的日报模板",
  "parameters": [],
  "sections": []
}
```

约束：

- `category` 是唯一分类字段
- `description` 是模板说明
- 不再使用模板顶层 `scene`
- 不再使用 `report_type / template_type / schema_version`
- 不再使用 `content_params / match_keywords / output_formats`
- 不再使用模板顶层 `outline`

## 3. 章节双层模型

每个章节节点保留双层结构：

- `section.outline`
  - `requirement`
  - `items[]`
- `section.content`
  - `datasets[]`
  - `presentation`

语义边界：

- `outline` 是章节级容器
- `requirement` 是单句诉求
- `item` 是诉求要素

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

## 5. 导入导出

- 导入采用“预解析 -> 进入编辑器 -> 用户手动保存”
- 导出直接返回唯一模板结构
- 导出文件名格式为 `模板名称-YYYYMMDD-HHMMSS.json`

## 6. 与模板实例的关系

模板实例不是第二套模板定义。

`TemplateInstance.base_template` 必须组合一份同构模板快照，仅保存：

- `id`
- `category`
- `name`
- `description`
- `parameters`
- `sections`
