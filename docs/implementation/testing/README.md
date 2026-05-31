# 测试体系

ReportSystem 的测试围绕业务 Context、稳定测试数据和隔离运行目录组织。测试既验证单个规则，也验证从 HTTP API 到持久化和文档导出的业务闭环。

## 分层

| 层级 | 目标 | 主要位置 |
|---|---|---|
| 单元测试 | 验证 conversation、report 和基础设施中的独立规则 | `modules/backend/tests/{conversation,report,infrastructure}/` |
| API 测试 | 验证 REST/SSE 契约、用户隔离和错误响应 | `modules/backend/tests/**/api/` |
| 特性 E2E | 从公开 API 验证完整用户场景 | `modules/backend/tests/features/` |
| Exporter 测试 | 验证 Report DSL 读取、CLI、DOCX 和 PPTX 结构 | `modules/exporter/src/test/java/` |
| 架构审计 | 验证模块依赖和测试文档清单完整性 | `modules/backend/tests/architecture/` |

## 测试数据

- `testdata/` 保存 Python 与 Java 共用的稳定 JSON 输入和外部响应 mock。
- `modules/backend/tests/support/builders.py` 负责按场景组合模板、报告和持久化对象。
- `.test/` 保存每轮测试生成的数据库、日志、临时 DSL 和 Office 文档；它不纳入 Git。

## 运行目录隔离

`.runtime/` 只属于部署和开发运行。测试必须设置：

```text
REPORT_SYSTEM_DATA_DIR=.test/runs/<run-id>
```

后端测试的 `conftest.py` 会在导入应用前设置独立目录。需要保留失败产物排查时可设置：

```text
REPORT_SYSTEM_KEEP_TEST_OUTPUTS=1
```

## 运行命令

```bash
cd modules/backend
uv sync --dev
uv run pytest tests -m "not exporter_e2e" -q
uv run pytest tests -m exporter_e2e -q

cd ../exporter
mvn test -q
mvn package -q -DskipTests
```

稳定用例清单见：

- [后端用例](backend-cases.md)
- [Exporter 用例](exporter-cases.md)
- [特性 E2E 用例](feature-e2e-cases.md)
