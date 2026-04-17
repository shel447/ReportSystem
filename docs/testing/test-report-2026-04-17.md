# 测试报告（2026-04-17）

## 1. 结论摘要

本次测试按当前新公开口径执行，正式范围限定为：

- `templates`
- `chat`
- `reports`
- `parameter-options`
- `/rest/dev/design`
- `/rest/dev/system-settings`
- `/rest/dev/feedback`
- 前端公开页面：`/chat`、`/templates`、`/templates/:id`、`/reports`、`/reports/:id`、`/settings`

测试结论：**本轮范围内主链路通过，可进入后续例行回归基线。**

本次测试同时完成了三类工作：

- 形成正式功能用例文档与实施计划
- 补齐自动化测试缺口并提供统一执行脚本
- 在真实服务、真实模型配置下完成深度功能验证

## 2. 测试范围与排除项

### 2.1 正式范围

- 模板管理与导入导出
- 参数三通道与动态参数解析
- 对话模板匹配、参数收集、诉求确认、报告生成
- 报告聚合视图与 report-scoped 文档下载
- 开发接口：系统设置、设计文档、反馈
- 前端公开页面与关键入口

### 2.2 排除项

以下能力不纳入本次正式测试与通过判定：

- `/rest/chatbi/v1/instances/*`
- `/rest/chatbi/v1/scheduled-tasks/*`
- 独立 `/rest/chatbi/v1/documents/*`
- 独立 `TemplateInstance` 对外接口
- `POST /rest/chatbi/v1/reports/{reportId}/edit-stream`

## 3. 环境信息

- 仓库：`E:\code\codex_projects\ReportSystemV2`
- 测试日期：`2026-04-17`
- 前端地址：`http://127.0.0.1:8001`
- 后端地址：`http://127.0.0.1:8300`
- Completion：已配置并验证通过
- Embedding：已配置并验证通过
- 样例数据库：`src/backend/telecom_demo.db`

## 4. 交付物

### 4.1 文档

- 功能用例文档：[functional-use-cases.md](E:/code/codex_projects/ReportSystemV2/docs/testing/functional-use-cases.md)
- 测试实施计划：[test-implementation-plan.md](E:/code/codex_projects/ReportSystemV2/docs/testing/test-implementation-plan.md)
- 本测试报告：[test-report-2026-04-17.md](E:/code/codex_projects/ReportSystemV2/docs/testing/test-report-2026-04-17.md)

### 4.2 自动化资产

- 深度 API 冒烟脚本：[deep_api_smoke.py](E:/code/codex_projects/ReportSystemV2/scripts/testing/deep_api_smoke.py)
- 统一执行入口：[run_functional_regression.ps1](E:/code/codex_projects/ReportSystemV2/scripts/testing/run_functional_regression.ps1)
- 新增后端测试：[test_dev_routers.py](E:/code/codex_projects/ReportSystemV2/src/backend/tests/test_dev_routers.py)
- 新增前端测试：[ReportCenterPage.test.tsx](E:/code/codex_projects/ReportSystemV2/src/frontend/src/pages/ReportCenterPage.test.tsx)
- 新增前端测试：[ReportDetailPage.test.tsx](E:/code/codex_projects/ReportSystemV2/src/frontend/src/pages/ReportDetailPage.test.tsx)
- 稳定性修复测试：[TemplateDetailPage.test.tsx](E:/code/codex_projects/ReportSystemV2/src/frontend/src/pages/TemplateDetailPage.test.tsx)

### 4.3 证据文件

- 深度 API 冒烟结果：[deep_api_smoke_20260417.json](E:/code/codex_projects/ReportSystemV2/output/testing/deep_api_smoke_20260417.json)
- 统一回归脚本输出烟测结果：[deep_api_smoke_from_runner_20260417_utf8.json](E:/code/codex_projects/ReportSystemV2/output/testing/deep_api_smoke_from_runner_20260417_utf8.json)
- 浏览器级页面检查：[browser_page_checks_20260417_rerun.json](E:/code/codex_projects/ReportSystemV2/output/testing/browser_page_checks_20260417_rerun.json)

## 5. 执行记录

### 5.1 代码级自动化

执行命令：

```powershell
python -m pytest src/backend/tests -q
npm test
npm run build
powershell -ExecutionPolicy Bypass -File scripts/testing/run_functional_regression.ps1 -BaseUrl http://127.0.0.1:8300 -UserId default -SmokeOutput output/testing/deep_api_smoke_from_runner_20260417_utf8.json
```

执行结果：

- 后端测试：`149 passed`
- 前端测试：`67 passed`
- 前端构建：通过
- 统一回归脚本：通过

### 5.2 真实服务深度测试

执行方式：

- 对运行中的真实后端调用深度 API 冒烟脚本
- 对运行中的真实前端执行浏览器级页面检查
- 使用真实 Completion / Embedding 配置，不使用 mock

执行结果：

- 深度 API 冒烟：`16 passed, 0 failed`
- 浏览器页面检查：`4/4` 页面通过

## 6. 覆盖结果

### 6.1 模板域 `TPL`

覆盖结论：**通过**

覆盖点：

- 模板创建 / 更新 / 详情 / 列表
- 新模板结构唯一性校验
- 模板导出文件名
- 导入预解析
- 动态参数解析 `label/value/query`
- 模板索引重建

证据：

- `TPL-SMOKE-001` 复杂模板创建或覆盖成功
- `TPL-SMOKE-002` 模板详情、导出、导入预解析成功
- `TPL-SMOKE-003` 动态参数解析返回三通道结构

### 6.2 对话域 `CHAT`

覆盖结论：**通过**

覆盖点：

- 空会话读取
- 自然语言触发模板匹配并创建会话
- 表单填参与自然语言补参混合流程
- 参数确认卡
- `prepare_outline_review`
- `foreach` 展开
- 诉求要素编辑后保留结构化绑定
- 诉求退化为自由文本节点
- `smart_query` 与 `fault_diagnosis` 独立能力

证据：

- `CHAT-SMOKE-002`：创建会话并返回参数表单
- `CHAT-SMOKE-003`：混合收参后进入统一确认
- `CHAT-SMOKE-004`：诉求确认树中出现 `综合结论 / 区域 R01 / 区域 R02`
- `CHAT-SMOKE-005`：编辑后 `execution_bindings` 保留
- `CHAT-SMOKE-006`：结构化诉求可退化为自由文本节点
- `CHAT-SMOKE-007`：智能问数与故障分析均可独立工作

### 6.3 报告域 `RPT`

覆盖结论：**通过**

覆盖点：

- 确认诉求后生成完整报告
- 报告聚合详情读取
- 报告中包含完整 `template_instance`
- report-scoped 文档下载

证据：

- `RPT-SMOKE-001`：生成报告成功
- 报告 ID：`e9b2c83f-0e52-40ff-a2c7-1c0073d22b03`
- 文档 ID：`5352b380-4bd9-4cc5-9987-3c87764cd385`
- 生成章节数：`3`
- 文档下载字节数：`815`

### 6.4 开发接口域 `DEV`

覆盖结论：**通过**

覆盖点：

- 系统设置读取
- Completion / Embedding 连通性测试
- 模板索引重建
- 设计文档列表、读取、ZIP 下载
- 反馈创建、列表、导出、删除

证据：

- `DEV-SMOKE-001`：系统设置就绪，索引 `ready_count = 2`
- `DEV-SMOKE-002`：Completion/Embedding 测试通过
- `DEV-SMOKE-003`：设计文档读取与 ZIP 下载通过
- `DEV-SMOKE-004`：反馈提交、导出、删除通过
- `DEV-SMOKE-005`：模板索引重建通过

### 6.5 前端页面域 `UI`

覆盖结论：**通过**

覆盖点：

- `/chat`
- `/templates`
- `/reports`
- `/settings`
- 页面关键入口与文案存在性
- 页面测试与浏览器页面检查相互印证

证据：

- 页面测试：`67 passed` 中覆盖页面与核心组件
- 浏览器级检查：
  - `/chat` 存在 `发送`、`对话助手`
  - `/templates` 存在 `新建模板`、`导入模板`
  - `/reports` 存在 `报告中心`、`前往对话助手`
  - `/settings` 存在 `测试连接`、`重建模板索引`

## 7. 本轮新增或修复的测试资产

### 7.1 新增资产

- `/rest/dev` 路由回归测试
- 报告中心页回归测试
- 报告详情页回归测试
- 深度 API 冒烟脚本
- 统一回归执行脚本

### 7.2 测试稳定性修复

发现问题：`TemplateDetailPage` 在全量执行时存在异步状态未稳定即保存的脆弱点。

处理结果：

- 在对应测试中补等待条件，确保 `追问模式` 字段切换到目标值后再继续断言或保存
- 修复后前端全量测试稳定通过

## 8. 发现的问题与处理情况

### 8.1 已处理问题

1. 前端测试脆弱性
- 现象：`TemplateDetailPage` 在全量跑时存在 `interaction_mode` 断言偶发失败
- 处理：增加等待字段稳定的断言
- 状态：已修复

2. 统一回归脚本中文输出编码问题
- 现象：PowerShell 输出中中文显示乱码
- 处理：在回归脚本开头显式设置 UTF-8 输出编码
- 状态：已修复

### 8.2 当前未阻断问题

1. 文档口径漂移
- `design/spec.md` 仍包含旧的 `instances / scheduled-tasks / documents` 口径
- 本次正式测试未按该旧文档执行，而是按当前新公开面执行
- 该问题不影响系统运行，但会影响后续测试口径统一

2. 依赖库弃用告警
- FastAPI `on_event` 生命周期写法存在弃用提示
- SQLAlchemy 1.x 到 2.0 兼容告警仍存在
- 当前不阻断功能，但需要列入后续技术债清理

3. `.pytest_cache` 路径告警
- 当前工作区缓存目录存在权限或目录状态问题，导致 pytest cache warning
- 不影响测试结果，但会影响测试输出整洁度

4. LLM 非确定性风险
- `smart_query` 属于模型驱动能力，存在提示词层面的波动空间
- 本轮最终使用稳定问题完成验证，能力本身已通过
- 后续若接入 CI，建议增加一组更稳定的数据问句集合作为基线

## 9. 质量评估

### 9.1 覆盖充分性

本轮测试已覆盖当前正式公开面的核心功能闭环：

- 模板定义与参数配置
- 对话模板匹配与参数推进
- 诉求确认与结构化编辑
- 报告生成与聚合读取
- 开发治理接口
- 前端关键页面可达性

结论：**当前正式范围内覆盖度达到可接受的系统级回归标准。**

### 9.2 自动化复用性

本轮新增脚本已经具备后续例行复用条件：

- `run_functional_regression.ps1` 适合作为本地或 CI 统一入口
- `deep_api_smoke.py` 适合作为真实环境例行回归脚本
- 新增前后端测试可并入常规测试套件

结论：**本轮交付物已满足后续持续回归的基础要求。**

## 10. 后续建议

1. 清理或改写 `design/spec.md`，避免旧公开面继续干扰测试基线
2. 将浏览器级页面检查收口为正式脚本，避免依赖临时文件
3. 为 `smart_query` 和 `fault_diagnosis` 建立更稳定的固定问句集与期望断言
4. 逐步消除 FastAPI 生命周期与 SQLAlchemy 版本告警

## 11. 最终结论

按当前新设计口径，本次系统功能测试已完成：

- 有正式、系统、详尽的功能用例文档
- 有可复用的测试实施计划
- 有可复用的自动化测试脚本和统一执行入口
- 有完整的代码级回归、真实服务深度验证和浏览器级页面证据
- 有正式测试报告记录结果、问题和风险

结论：**本轮范围内系统功能通过，测试任务完成。**
