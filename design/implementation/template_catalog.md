# 模板目录模块设计实现

## 1. 模块定位

`template_catalog` 负责模板定义的唯一真相：创建、更新、导入预解析、导出、校验和语义匹配。

## 2. 代码落点

- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/template_catalog/domain/models.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/template_catalog/application/services.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/template_catalog/infrastructure/repositories.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/template_catalog/infrastructure/schema.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/contexts/template_catalog/infrastructure/indexing.py`
- `E:/code/codex_projects/ReportSystemV2/src/backend/routers/templates.py`

## 3. 核心领域概念

- `ReportTemplate`
  - 唯一模板结构：`id/category/name/description/parameters/sections`
- `TemplateMatchResult`
  - 模板匹配结果

## 4. 分层职责

### domain

表达模板领域模型，不依赖 ORM 和 Web 框架。

### application

`TemplateCatalogService` 负责：

- 模板 CRUD
- 导入预解析
- 导出
- 匹配调用装配

### infrastructure

- 仓储映射 `tbl_report_templates`
- schema 校验与归一化
- 语义索引和匹配

### router

`templates.py` 只负责 HTTP 映射。

## 5. 关键实现约束

- 不再维护模板双轨定义
- 不再接受旧模板顶层字段
- `report_template_schema_v2.json` 是唯一模板 schema 基线
- 模板导出、详情、导入预解析都只使用唯一结构
- 模板匹配文本只基于：`name/description/category/parameters/sections`

## 6. 关联表

- [tbl_report_templates](database_schema.md#tbl_report_templates)
- [tbl_template_semantic_indices](database_schema.md#tbl_template_semantic_indices)

## 7. 可替换组件

- SQLAlchemy 仓储
- schema 校验器
- embedding 匹配实现

这些 adapter 可替换，但不改变模板定义本身的业务结构。
