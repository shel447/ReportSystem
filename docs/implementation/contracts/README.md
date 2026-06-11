# 技术契约

- [内部消息契约](messaging.md)

本目录保存 ReportSystem 的技术契约。它服务于前后端开发、外部系统集成、模板配置和运行时校验，不属于面向业务用户的功能说明。

## 导航

1. [API 契约](apis/README.md)
2. [外部依赖接口技术契约](apis/external-dependencies.md)
3. [数据库契约](database/README.md)
4. [JSON Schema 与示例](schemas/README.md)
5. [报告模板字段级手册](manuals/报告模板定义与使用说明书.md)
6. [Report DSL 字段级手册](manuals/报告DSL定义与使用说明书.md)

## 维护原则

- JSON Schema 是结构契约的唯一事实源，代码目录不得复制镜像。
- API 契约描述公开接口和服务端内部协议，不反向定义业务能力。
- 数据库契约描述当前最新表结构和升级规则，执行 SQL 统一由 `upgrades/` 维护。
- 字段级手册用于解释 Schema，不替代业务规格。
- 技术契约变化记录到 [实现变更日志](../changelog/README.md)。
