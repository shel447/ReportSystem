# ReportSystem

智能报告系统。当前公开业务面已经收口为三条主链路：`templates`、`chat`、`reports`。

## 1. 项目概览

系统围绕三类公开业务对象运行：

- `报告模板`：静态模板定义，只保留唯一结构 `id/category/name/description/schemaVersion/parameters/catalogs`
- `统一对话`：完整驱动模板匹配、参数收集、诉求确认、报告生成
- `报告`：最终聚合视图，返回完整 `templateInstance + report DSL + documents`

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
- 报告级 Word/PPT/PDF/Markdown 文档导出与下载

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
- `schemaVersion`
- `catalogs`

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
- Java 17（文档导出服务）

### 数据

- 系统主库：`src/backend/report_system.db`
- 电信样例分析库：`src/backend/telecom_demo.db`

## 4. 仓库结构

```text
ReportSystem/
├─ design/
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

文档导出服务单独落在：

- `services/java-office-exporter`

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

### 当前权威设计

- [设计文档总入口](design/README.md)
- [报告系统统一设计包](design/report_system/README.md)
- [接口契约](design/report_system/04-接口契约.md)
- [数据模型与持久化](design/report_system/05-数据模型与持久化.md)

### 当前实现设计

- [实现设计索引](design/report_system/implementation/README.md)
- [总体实现架构](design/report_system/implementation/总体实现架构.md)
- [模板目录实现](design/report_system/implementation/模板目录实现.md)
- [统一对话实现](design/report_system/implementation/统一对话实现.md)
- [报告运行时实现](design/report_system/implementation/报告运行时实现.md)
- [持久化与表结构实现](design/report_system/implementation/持久化与表结构实现.md)

### 产品与需求

- [原始需求输入](design/biz_requirement.md)

## 7. 当前实现边界

- 报告级编辑流接口 `POST /rest/chatbi/v1/reports/{reportId}/edit-stream` 仍待实现
- Word/PPT/PDF 导出由 `services/java-office-exporter` 提供
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
