# API 实现

公开业务路由由 FastAPI router 负责协议适配，业务规则下沉到对应 application service。

公开接口和服务端内部协议的完整报文见 [API 技术契约](../contracts/apis/README.md)。

| 路由 | 实现入口 | 应用服务 |
|---|---|---|
| `templates` | `routers/templates.py` | `template_catalog` |
| `parameter-options` | `routers/parameter_options.py` | `template_catalog` |
| `chat` | `routers/chat.py` | `conversation` |
| `reports` | `routers/reports.py` | `report_runtime` |

开发辅助接口位于 `/rest/dev/*`，不反向定义业务模型。文档浏览接口使用 `/rest/dev/docs`：

- 递归列出 `docs/` 下的 Markdown 和 JSON 文档资产。
- 读取嵌套 Markdown、Schema 和示例 JSON。
- 按原目录结构打包下载 ZIP。
- 使用根目录约束拒绝目录逃逸。
