# Backend 第三方扩展层

`modules/backend/src/_third_party/` 保存 ReportSystem 对第三方 Python 库的项目级扩展源码。扩展层用于承载上游库暂未提供、但项目后续可能需要的适配能力；它不是上游库源码镜像，也不替代正式依赖声明。

## 1. 使用边界

- `_third_party` 可被 Backend 各层直接导入，但调用方必须明确自己依赖的是 ReportSystem 扩展，而不是上游库的正式公共 API。
- 不得直接修改虚拟环境或安装目录中的第三方包；项目扩展统一维护在 `_third_party`。
- 扩展代码可以依赖上游库内部 API，因此升级对应第三方依赖前必须进行兼容审查。
- 新增扩展时应按第三方库名称建立独立子目录，避免不同库的扩展实现互相耦合。
- `_third_party` 不承载 ReportSystem 业务规则；业务规则仍归属对应 Context。

## 2. Ibis 扩展

当前仅包含 `_third_party/ibis`，目标依赖版本为 `ibis-framework[sqlite] == 11.0.0`。

Ibis 扩展明确区分 Ibis 核心语法扩展、SQLGlot 核心语法扩展和周边辅助扩展。各能力组的上游扩展机制、对应源码符号、具体行为、限制与升级风险统一维护在 [Ibis 扩展点清单](ibis.md)。

## 3. 当前接入状态

当前 `_third_party/ibis` 已接入智能问数 NL2SQL 编译链路：

- data-analysis infrastructure 受限执行模型生成的 Ibis `query(config)`，并调用
  `_third_party.ibis.ibis_ext.to_sql()` 编译 DTE SQL。
- application/domain 不直接依赖 `_third_party`；扩展编译器只作为 infrastructure
  对 application-owned 接口的实现。
- `infrastructure/query` 的历史演示查询仍使用官方 SQLite backend，并复用统一执行入口。

升级 Ibis 或 SQLGlot 时，必须按扩展点清单逐项验证编译行为，并使用真实
OneQuery/DTE SQL 环境确认生成 SQL 兼容性。

## 4. 文档导航

- [Ibis 扩展点清单](ibis.md)：按能力组记录当前源码实际扩展行为和升级风险。
- [智能问数实现](../data-analysis/README.md)：说明当前正式查询链路与扩展源码的关系。
