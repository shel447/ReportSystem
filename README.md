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
- 报告级 Word/PPT/Markdown 文档导出与下载；PDF 暂未开放

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
- BI Engine / BI Designer（Git 子模块）

### 后端

- 平台 `runtime.server` SDK（本地由 `modules/mock-sdk` 提供）
- SQLAlchemy
- Pydantic
- HTTPX
- Ibis + SQLite
- Java 21（文档导出 CLI）

### 数据

- 系统主库：`.runtime/report_system.db`
- 开发辅助库：`.runtime/dev_support.db`
- 电信样例分析库：`.runtime/telecom_demo.db`
- 数据库结构随启动过程按 `modules/backend/src/infrastructure/persistence/upgrades/` 自动升级

## 4. 仓库结构

```text
ReportSystem/
├─ docs/
├─ modules/
│  ├─ backend/
│  ├─ frontend/
│  ├─ exporter/
│  ├─ mock-sdk/        # 平台 runtime.server 的本地开发实现
│  └─ mock-server/     # 可选开发态外部系统替身
└─ README.md
```

### 4.1 后端结构

后端按 DDD bounded context 组织：

- `modules/backend/src/contexts/conversation`
- `modules/backend/src/contexts/report`
- `modules/backend/src/infrastructure`
- `modules/backend/src/shared/kernel`
- `modules/backend/src/controllers`

公开业务路由当前只保留：

- `templates`
- `chat`
- `reports`

`TemplateInstance` 是内部核心聚合，不作为独立公开资源。

文档导出服务单独落在：

- `modules/exporter`

## 5. 快速启动

### 5.1 环境要求

- Python 3.11+
- Node.js 18+
- npm

### 5.2 安装依赖

后端：

```powershell
Set-Location modules/backend
uv sync --dev
```

前端：

```powershell
git submodule update --init --recursive
Set-Location modules/frontend
npm install
```

BI Engine 源码固定在 `modules/frontend/vendor/bi-engine`。升级时先在子模块中检出目标提交，再提交父仓库中的子模块指针变更：

```powershell
git -C modules/frontend/vendor/bi-engine fetch origin
git -C modules/frontend/vendor/bi-engine checkout <commit>
git add modules/frontend/vendor/bi-engine
```

### 5.3 构建前端

```powershell
Set-Location modules/frontend
npm run build
```

### 5.4 启动服务

```powershell
Set-Location modules/backend
uv run python -m runtime.server --module src --host 0.0.0.0 --port 8300
```

本地联调时，如果没有上游网关注入 `X-User-Id`，可显式设置 `REPORT_DEV_USER_ID` 作为开发用户，例如 `REPORT_DEV_USER_ID=pycharm-check`。未设置该变量时，正式业务接口仍会要求请求携带可信用户身份。

默认访问地址：

- 健康检查：[http://127.0.0.1:8300/rest/chatbi/healthcheck](http://127.0.0.1:8300/rest/chatbi/healthcheck)

接口前缀约定：

- 业务接口：`/rest/chatbi/v1/*`

### 5.5 可选：启动开发态 Mock 外部服务

生产环境中的动态参数、业务查询和 Dynamic Custom 由独立外部业务服务提供。联调和演示时可以显式启动可插拔 mock-server：

```bash
cd modules/mock-server
uv sync --dev
uv run uvicorn mock_server.main:app --app-dir src --host 127.0.0.1 --port 8310
```

另开终端导入开发态复杂模板并配置 mock AI：

```bash
python3 scripts/setup_mock_demo.py
```

应用启动不会自动导入演示数据。

## 6. 文档导航

### 业务规格

- [文档总入口](docs/README.md)
- [规格设计索引](docs/specs/README.md)
- [报告业务](docs/specs/report/README.md)
- [通用对话](docs/specs/conversation/README.md)
- [智能问数](docs/specs/data-analysis/README.md)

### 实现设计与技术契约

- [实现设计索引](docs/implementation/README.md)
- [技术契约](docs/implementation/contracts/README.md)
- [API 契约](docs/implementation/contracts/apis/README.md)
- [JSON Schema 与示例](docs/implementation/contracts/schemas/README.md)
- [Report Context 实现](docs/implementation/report/README.md)
- [前端实现](docs/implementation/frontend/README.md)
- [开发测试体系](docs/dev/testing/README.md)

### 变更记录

- [规格变更日志](docs/specs/changelog/README.md)
- [实现变更日志](docs/implementation/changelog/README.md)

## 7. 当前实现边界

- 报告级编辑流接口 `POST /rest/chatbi/v1/reports/edit-stream?reportId={reportId}` 仍待实现
- Word/PPT 导出由 `modules/exporter` 提供，Markdown 由后端生成；PDF 暂未开放
- 动态参数解析是辅助公共接口，不作为独立业务资源页暴露

## 8. 开发与验证

前端测试：

```powershell
Set-Location modules/frontend
npm test
```

前端构建：

```powershell
Set-Location modules/frontend
npm run build
```

后端测试：

```powershell
Set-Location modules/backend
uv run pytest tests -q
```

需要执行真实 Java Office 导出闭环时：

```powershell
Set-Location modules/backend
uv run pytest tests -m exporter_e2e -q
```

Mock 外部服务测试：

```bash
Set-Location modules/mock-server
uv sync --dev
uv run pytest -q
```
