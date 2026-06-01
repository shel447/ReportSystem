# 特性 E2E 用例

| ID | 特性 | 场景 | 状态 |
|---|---|---|---|
| E2E-TPL | 模板管理 | 创建、列表、详情、更新、导入预览、导出、删除和非法 Schema | 已建立主闭环 |
| E2E-CONV | 通用对话 | 会话创建、历史、详情、删除、fork 和用户隔离 | 持续补齐 |
| E2E-RPT | 报告生成 | 参数追问、确认、正式报告和章节重新生成 | 持续补齐 |
| E2E-DOC-MD | Markdown 导出 | 通过 API 生成隔离目录产物；任务复用和下载继续扩展 | 已建立主入口 |
| E2E-DOC-OFFICE | Word/PPT 导出 | 真实 Java CLI、下载和 OOXML 结构校验 | 已建立跨模块入口 |
| E2E-RPT-MOCK | 复杂报告联调 | 使用独立 mock-server 完成 2 份 flow Word 与 2 份 paged PPT 冻结和导出 | 已建立完整闭环 |
| E2E-DOC-PDF | PDF 导出 | 请求 PDF 返回明确 `400` | 已定义 |
| E2E-DEV | 开发辅助 | docs、feedback CRUD/ZIP、系统设置读取保存、连接测试和 reindex | 已建立主闭环 |
