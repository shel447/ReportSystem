# 智能报告系统安装部署手册

## 1. 文档目的

本文档用于指导 `ReportSystemV2` 在 Windows 环境下完成安装、启动、基础配置与常见问题排查。

本文档覆盖的内容：

- 本地安装
- 服务启动
- 远程访问配置
- 系统设置配置
- 报告生成与 Markdown 导出
- 已知问题与 QA

## 2. 系统组成

当前系统由以下部分组成：

- 后端：FastAPI
- 前端：静态页面，由后端统一提供
- 主业务库：`src/backend/report_system.db`
- 电信样例分析库：`src/backend/telecom_demo.db`
- 文档输出目录：`src/backend/generated_documents/`

关键入口文件：

- 后端入口：[main.py](E:/code/codex_projects/ReportSystemV2/src/backend/main.py)
- 依赖清单：[requirements.txt](E:/code/codex_projects/ReportSystemV2/src/backend/requirements.txt)
- 数据库初始化：[database.py](E:/code/codex_projects/ReportSystemV2/src/backend/database.py)

## 3. 环境要求

建议环境：

- 操作系统：Windows 10 / Windows 11
- Python：建议 `3.14.x`
- Shell：PowerShell
- 网络：如果需要远程访问或真实大模型调用，需要具备外网连接能力

已验证依赖如下：

- `fastapi==0.115.0`
- `uvicorn==0.30.0`
- `sqlalchemy==2.0.30`
- `pydantic==2.7.0`
- `python-multipart==0.0.9`
- `aiofiles==24.1.0`
- `apscheduler==3.10.4`
- `httpx==0.28.1`
- `ibis-framework[sqlite]==12.0.0`

## 4. 目录说明

```text
ReportSystemV2/
├─ design/                         设计与说明文档
├─ src/
│  ├─ backend/
│  │  ├─ main.py                   FastAPI 入口
│  │  ├─ report_system.db          主业务库（自动生成）
│  │  ├─ telecom_demo.db           电信样例库（自动生成）
│  │  ├─ generated_documents/      Markdown 导出目录
│  │  └─ requirements.txt          Python 依赖
│  └─ frontend/
│     ├─ index.html                前端页面
│     └─ favicon.svg               站点图标
└─ .gitignore
```

## 5. 安装步骤

### 5.1 获取代码

```powershell
git clone <your-repo-url>
cd E:\code\codex_projects\ReportSystemV2
```

### 5.2 创建虚拟环境

建议使用虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

如果 PowerShell 阻止脚本执行，可先在当前会话临时放开：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

### 5.3 安装依赖

```powershell
python -m pip install --upgrade pip
pip install -r src\backend\requirements.txt
```

## 6. 启动方式

### 6.1 前台启动

适合开发调试。

```powershell
python -m uvicorn src.backend.main:app --host 0.0.0.0 --port 8300
```

启动后访问：

- 本机：`http://127.0.0.1:8300`
- OpenAPI：`http://127.0.0.1:8300/openapi.json`

### 6.2 后台启动

在部分 PowerShell 会话中，直接 `Start-Process` 可能会导致 `uvicorn` 随父 shell 退出。  
当前已验证稳定的后台启动方式是使用 `Win32_Process.Create`：

```powershell
$cmd = 'cmd /c cd /d E:\code\codex_projects\ReportSystemV2 && C:\Users\Administrator\AppData\Local\Python\pythoncore-3.14-64\python.exe -m uvicorn src.backend.main:app --host 0.0.0.0 --port 8300'
([wmiclass]'Win32_Process').Create($cmd)
```

说明：

- 需要将 Python 路径替换为你本机实际路径
- 该方式在当前环境中已验证能稳定拉起并保持服务

### 6.3 启动验证

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8300/openapi.json'
```

预期结果：

- 能返回 OpenAPI JSON
- 当前版本应为 `1.6.0`

## 7. 首次启动后的自动初始化

服务启动时会自动执行以下动作：

1. 初始化主业务库 `report_system.db`
2. 自动补齐兼容字段，例如模板表中的 `match_keywords`
3. 初始化电信样例库 `telecom_demo.db`
4. 供前端页面统一访问 `/` 和 `/static/*`

说明：

- `telecom_demo.db` 与 `report_system.db` 完全隔离
- `telecom_demo.db` 不存在时会自动建库并灌入样例数据

## 8. 页面访问

浏览器访问：

```text
http://127.0.0.1:8300
```

系统主要页面：

- 对话助手
- 模板管理
- 报告实例
- 文档管理
- 定时任务
- 系统设置
- 提意见

## 9. 系统设置配置

为了启用真实语义匹配与真实大模型调用，需要在页面左下角进入“系统设置”。

配置项包括：

- Completion
  - `base_url`
  - `model`
  - `api_key`
  - `temperature`
  - `timeout_sec`
- Embedding
  - `base_url`
  - `model`
  - `api_key`
  - `timeout_sec`
  - `use_completion_auth`

推荐配置流程：

1. 填写 Completion 参数
2. 填写 Embedding 参数
3. 点击“测试连接”
4. 点击“重建模板索引”
5. 回到对话助手页面验证模板匹配

## 10. 文档生成

当前系统已实现 Markdown 导出。

导出方式：

- 在“文档管理”页面生成 Markdown
- 在报告实例详情中直接点击“生成 Markdown”
- 定时任务在启用 `auto_generate_doc` 时会自动生成 Markdown

文档输出位置：

```text
src/backend/generated_documents/
```

说明：

- 当前只支持 Markdown
- PDF 暂未启用
- `generated_documents/` 已被 `.gitignore` 忽略，不应纳入版本管理

## 11. 远程访问部署

### 11.1 服务监听地址

启动命令必须使用：

```powershell
--host 0.0.0.0 --port 8300
```

如果只监听 `127.0.0.1`，则只能本机访问。

### 11.2 Windows 防火墙放行

如果需要其他机器访问，通常还需要放行 `8300` 端口。

管理员 PowerShell 执行：

```powershell
netsh advfirewall firewall add rule name="ReportSystem-8300" dir=in action=allow protocol=TCP localport=8300
```

说明：

- 该命令需要管理员权限
- 如果未放行，常见表现是“本机可访问，其他机器访问失败”

### 11.3 局域网访问验证

先查看本机 IPv4：

```powershell
ipconfig | findstr /R /C:"IPv4"
```

再从本机或其他设备访问：

```text
http://<your-ip>:8300
```

## 12. 日常运维命令

### 12.1 查看端口监听

```powershell
netstat -ano | findstr :8300
```

### 12.2 查看占用端口的进程

```powershell
Get-Process -Id <PID>
```

### 12.3 停止服务

```powershell
Stop-Process -Id <PID> -Force
```

### 12.4 检查接口是否正常

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8300/openapi.json'
```

## 13. QA / 常见问题

### Q1：页面打开是空白的，或者页签标题乱码，怎么办？

A：

- 先确认当前启动的是最新代码，而不是旧进程
- 再强制刷新浏览器缓存
- 当前代码已修复多处前端乱码问题；如果仍出现，优先排查浏览器缓存是否仍在使用旧静态资源

建议动作：

1. 停掉旧进程
2. 重新启动 `8300`
3. 浏览器执行强制刷新

### Q2：很多中文文案变成乱码，比如欢迎语、placeholder，怎么办？

A：

- 这类问题此前出现在前端文本和文件编码处理不一致时
- 当前代码中的已知乱码文本已经清理
- 如果仍然看到乱码，通常是旧页面缓存或旧进程提供了旧版本静态文件

处理方式：

1. 重启服务
2. 强制刷新浏览器
3. 必要时清除浏览器站点缓存

### Q3：新增接口比如 `/api/system-settings`、`/api/system-settings/test` 返回 404，为什么？

A：

根因通常不是代码没写，而是：

- `8300` 上跑的还是旧版本进程
- 新代码没有实际生效

处理方式：

1. 查 `8300` 端口占用
2. 停掉旧进程
3. 用当前代码重新启动
4. 再访问 `/openapi.json` 确认版本

### Q4：为什么我已经改了代码，但页面行为还是旧的？

A：

常见原因有两个：

- 后端还是旧进程
- 浏览器仍在使用旧静态资源缓存

建议同时做两件事：

1. 重启服务
2. 浏览器强制刷新

### Q5：为什么“系统设置”或“提意见”在某些页面右下角消失了？

A：

- 这类问题此前是侧边栏布局和页面内容高度耦合造成的
- 当前版本已经重构成固定壳层布局，底部区与内容区解耦

如果再次出现：

1. 优先确认是否仍在跑旧前端版本
2. 强制刷新浏览器

### Q6：为什么服务在当前终端里能启动，但一放到后台就访问不了？

A：

这是当前 Windows 会话下最容易踩的坑之一。

原因：

- 某些后台启动方式会让 `uvicorn` 仍然挂在父 shell 生命周期上
- 父 shell 结束后，子进程也会被带走

结论：

- 不要默认相信 `Start-Process` 一定会稳定常驻
- 当前已验证可用的后台方式是 `Win32_Process.Create`

### Q7：为什么本机能访问，其他机器访问不了？

A：

通常是以下原因之一：

- 服务不是以 `0.0.0.0` 启动
- Windows 防火墙没有放行 `8300`
- 访问的是错误的本机 IP

排查顺序：

1. 查启动命令是否包含 `--host 0.0.0.0`
2. 查 `netstat -ano | findstr :8300`
3. 查 `ipconfig`
4. 用管理员权限添加防火墙规则

### Q8：为什么 OpenAPI 里有新接口，但页面上看不到新功能？

A：

说明后端大概率已更新，但前端静态资源未刷新。

处理方式：

- 强制刷新页面
- 必要时清理浏览器缓存

### Q9：为什么系统设置保存后，模板匹配还是不准确？

A：

语义匹配不仅依赖 Completion / Embedding 配置，还依赖模板索引状态。

必须确认：

1. 系统设置已保存
2. 测试连接通过
3. 模板索引已重建
4. 模板本身配置了合理的 `match_keywords`

### Q10：为什么远程端口放行命令执行失败？

A：

如果报错 “The requested operation requires elevation”，说明当前 PowerShell 不是管理员权限。

处理方式：

- 以管理员身份打开 PowerShell
- 重新执行防火墙放行命令

### Q11：启动日志里打印的是 `http://localhost:8000`，但实际我用的是 `8300`，哪个才是对的？

A：

- 实际访问端口以 `uvicorn` 启动参数为准
- 当前部署建议统一使用 `8300`
- 如果代码启动日志仍打印 `8000`，不要按这个值判断服务真实端口

最可靠的确认方式：

- 看实际启动命令
- 看 `netstat -ano | findstr :8300`
- 看 `http://127.0.0.1:8300/openapi.json`

## 14. 部署检查清单

部署完成后，建议逐项核对：

- Python 版本正确
- 依赖安装完成
- `report_system.db` 已生成
- `telecom_demo.db` 已生成
- `http://127.0.0.1:8300/openapi.json` 可访问
- 首页 `http://127.0.0.1:8300` 可访问
- 系统设置可保存
- 系统设置测试连接可用
- 模板索引可重建
- 可成功创建报告实例
- 可成功导出 Markdown

## 15. 结论

当前项目可以按“单机 FastAPI + SQLite + 静态前端”的方式快速部署。  
如果只是开发和演示环境，按本文档步骤即可完成安装与启动。  
如果要做长期稳定运行，建议引入更标准的进程托管方式，例如 Windows 服务、任务计划或专用进程管理器，而不是依赖临时 shell 会话。
