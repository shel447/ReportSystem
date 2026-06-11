# Runtime 数据库接入

ReportSystem 的正式业务库由平台 Runtime 托管。Backend 不创建正式业务库的 Engine，不解析数据库连接信息，也不在服务启动时执行建表或升级。

## 1. 职责边界

| 层级 | 职责 |
|---|---|
| `runtime.db.TableBase` | 提供正式 ORM 模型统一基类和 metadata |
| `runtime.cache.zenith_instance` | 按实例名提供数据库 Session |
| `infrastructure/persistence/db_ctx.py` | 管理 Session、提交、回滚、关闭和异常日志 |
| Context infrastructure repository | 使用调用方提供的同一个 Session 读写业务数据 |
| application/domain/controller | 不感知 Runtime 数据库实例和 SQLAlchemy Session |

正式实例名固定为 `dtesmartbiservicedb`。开发辅助库和电信演示库不属于该实例，继续由 Backend 本地开发基础设施管理。

## 2. 事务边界

每次 report 或 conversation service scope 创建一个 `db_session(reraise=True)`：

1. Runtime 实例创建 Session。
2. 同一 scope 内的 Repository 共享该 Session。
3. scope 正常退出时统一提交。
4. 发生异常时统一回滚、记录日志并重新抛出。
5. 无论成功失败都关闭 Session。
6. 领域事件只在事务提交完成后发送；回滚时丢弃待发送事件。

Repository 不得自行调用 `commit()`、`rollback()` 或 `close()`。

## 3. 表结构升级

生产环境由 Runtime 或部署流程在 ReportSystem 启动前完成建表和升级。Backend 保留版本化 SQL 和完整 DDL，作为部署资产、结构审查依据和兼容测试输入，但启动流程不执行这些 SQL。

本仓库 `modules/mock-sdk` 是本地 Runtime 替代实现。它将 `dtesmartbiservicedb` 映射到既有 `.runtime/report_system.db`，并在首次创建 Session 时根据 `TableBase.metadata` 补建缺失表。该行为仅服务本地开发，不代表生产升级机制。

## 4. 使用约束

```python
from runtime.db import TableBase

class ReportTemplate(TableBase):
    __tablename__ = "tbl_report_templates"
```

```python
from src.infrastructure.persistence.db_ctx import db_session

with db_session(reraise=True) as session:
    repository = SqlAlchemyTemplateManagementRepository(session)
    repository.create(template)
```
