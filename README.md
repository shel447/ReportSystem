# ReportSystemV2

智能报告系统。当前公开业务面已经收口为三条主链路：`templates`、`chat`、`reports`。

## 1. 项目概览

系统围绕三类公开业务对象运行：

- `报告模板`：静态模板定义，只保留唯一结构 `id/category/name/description/parameters/sections`
- `统一对话`：完整驱动模板匹配、参数收集、诉求确认、报告生成
- `报告`：最终聚合视图，返回完整 `template_instance + generated_content`

当前主流程：

```mermaid
flowchart LR
    A["系统设置"] --> B["报告模板"]
    B --> C["统一对话"]
    C --> D["报告"]
    D --> E["报告级文档下载"]
```

## 2. 当前核心能力

### 2.1 报告生成

- 模板匹配
- 参数收集与确认
- 诉求确认
- 章节级内容生成
- 报告聚合视图
- 报告级 Markdown 下载

### 2.2 统一对话

- 单入口支持三类能力：
  - `report_generation`
  - `smart_query`
  - `fault_diagnosis`
- 单活任务模型
- 会话历史与消息级 fork
- 对话过程中持续维护同一份内部 `TemplateInstance`

### 2.3 模板唯一结构

模板定义只保留一套：

- `id`
- `category`
- `name`
- `description`
- `parameters`
- `sections`

章节节点采用双层模型：

- 用户层：`section.outline.requirement + section.outline.items[]`
- 执行层：`section.content.datasets + presentation`

### 2.4 数据与查询链路

- 内置电信领域样例分析库 `telecom_demo.db`
- 报告生成查询链路支持实验性 `NL -> QuerySpec -> Ibis -> SQL -> SQLite`

## 3. 技术栈

### 前端

- React 18
- TypeScript
- Vite
- React Router
- TanStack Query

### 后端

- FastAPI
- SQLAlchemy
- Pydantic
- HTTPX
- Ibis + SQLite

### 数据

- 系统主库：`src/backend/report_system.db`
- 电信样例分析库：`src/backend/telecom_demo.db`

## 4. 仓库结构

```text
ReportSystemV2/
├─ design/
├─ docs/
├─ src/
│  ├─ backend/
│  └─ frontend/
└─ README.md
```

### 4.1 后端结构

后端按 DDD bounded context 组织：

- `src/backend/contexts/template_catalog`
- `src/backend/contexts/conversation`
- `src/backend/contexts/report_runtime`
- `src/backend/infrastructure`
- `src/backend/shared/kernel`
- `src/backend/routers`

公开业务路由当前只保留：

- `templates`
- `chat`
- `reports`
- `parameter-options`（前端动态参数辅助接口）

`TemplateInstance` 是内部核心聚合，不作为独立公开资源。

## 5. 快速启动

### 5.1 环境要求

- Python 3.11+
- Node.js 18+
- npm

### 5.2 安装依赖

后端：

```powershell
python -m pip install -r src/backend/requirements.txt
```

前端：

```powershell
Set-Location src/frontend
npm install
```

### 5.3 构建前端

```powershell
Set-Location src/frontend
npm run build
```

### 5.4 启动服务

```powershell
python -m uvicorn src.backend.main:app --host 0.0.0.0 --port 8300
```

默认访问地址：

- 应用首页：[http://127.0.0.1:8300](http://127.0.0.1:8300)
- OpenAPI：[http://127.0.0.1:8300/openapi.json](http://127.0.0.1:8300/openapi.json)

接口前缀约定：

- 业务接口：`/rest/chatbi/v1/*`
- 开发接口：`/rest/dev/*`

## 6. 文档导航

### 总体与模块设计

- [整体设计](design/design.md)
- [模板设计](design/design_template.md)
- [API 设计](design/design_api.md)
- [对话制报告接口串联案例](design/design_chat_report_stream_case.md)

### 核心实现文档

- [实现文档索引](design/implementation/index.md)
- [模板目录实现](design/implementation/template_catalog.md)
- [统一对话实现](design/implementation/conversation.md)
- [报告运行时实现](design/implementation/report_runtime.md)
- [数据库表定义总览](design/implementation/database_schema.md)
- [外部接口与用法](design/implementation/external_interfaces.md)

### 产品与需求

- [规格文档](design/spec.md)
- [用户故事](design/story.md)
- [原始需求与按日演进记录](design/biz_requirement.md)

## 7. 当前实现边界

- 报告级编辑流接口 `POST /rest/chatbi/v1/reports/{reportId}/edit-stream` 仍待实现
- 文档导出当前以 Markdown 为主
- 动态参数解析是辅助公共接口，不作为独立业务资源页暴露

## 8. 开发与验证

前端测试：

```powershell
Set-Location src/frontend
npm test
```

前端构建：

```powershell
Set-Location src/frontend
npm run build
```

后端测试：

```powershell
python -m pytest src/backend/tests -q
```
