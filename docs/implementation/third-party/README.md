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

当前 `_third_party/ibis` 仅作为源码资产合入，尚未接入正式查询链路：

- `infrastructure/query` 仍直接使用官方 Ibis 11 和 SQLite backend。
- 智能问数与报告查询行为不因本扩展目录发生变化。
- `_third_party.ibis.ibis_ext` 当前存在已知循环依赖，尚不能作为稳定公共入口直接导入。
- 本轮不修复循环依赖、不切换编译器、不承诺扩展能力可运行。

后续正式接入前，需要先消除循环依赖，补充扩展能力单元测试，并验证生成 SQL 与 OneQuery/DTE SQL 契约兼容。

## 4. 文档导航

- [Ibis 扩展点清单](ibis.md)：按能力组记录当前源码实际扩展行为和升级风险。
- [智能问数实现](../data-analysis/README.md)：说明当前正式查询链路与扩展源码的关系。
