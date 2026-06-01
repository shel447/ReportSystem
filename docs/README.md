# ReportSystem 文档

`docs/` 是 ReportSystem 的唯一文档入口。业务规格与技术实现分开维护：先用业务语言说明系统提供什么能力，再由实现设计和技术契约说明如何落地。

## 阅读入口

1. [业务规格](specs/README.md)
2. [实现设计](implementation/README.md)
3. [技术契约](implementation/contracts/README.md)
4. [开发资料](dev/README.md)
5. [规格变更日志](specs/changelog/README.md)
6. [实现变更日志](implementation/changelog/README.md)

## 目录职责

- `specs/`：面向产品人员和业务用户，描述功能、使用方式、可感知效果和限制。
- `implementation/`：面向研发和集成方，描述模块职责、运行规则、技术契约和验证记录。
- `implementation/contracts/`：集中维护 API、JSON Schema、示例和字段级技术手册。
- `dev/`：开发过程资料，包括测试体系、代码评审、联调脚本和开发态 fixture。

## 维护规则

1. 用户可感知的业务变化先修改 `specs/` 下对应功能说明。
2. 同步追加当年的 [规格变更日志](specs/changelog/README.md)。
3. 技术契约或落地方式变化再修改 `implementation/`。
4. 完成编码和验证后追加当年的 [实现变更日志](implementation/changelog/README.md)。
5. Schema 是结构契约的唯一事实源，代码不得维护镜像副本。
