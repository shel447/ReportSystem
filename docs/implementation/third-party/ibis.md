# Ibis 扩展点清单

本文记录 `modules/backend/src/_third_party/ibis/` 对 Ibis Framework 和 SQLGlot 的项目级扩展。清单只描述当前源码中已经存在的行为，不表示这些能力已经接入 ReportSystem 正式查询链路。

## 1. 基线与状态

| 项目 | 当前约定 |
|---|---|
| 目标上游版本 | `ibis-framework[sqlite] == 11.0.0` |
| 扩展源码入口 | `modules/backend/src/_third_party/ibis/` |
| 当前接入状态 | **未接入**。`infrastructure/query` 仍使用官方 Ibis 11 和 SQLite backend |
| 已知限制 | `_third_party.ibis.ibis_ext` 存在循环依赖，当前不能作为稳定公共入口直接导入 |
| 本文粒度 | 按行为能力组记录；私有辅助函数归入其支撑的能力组，不逐项罗列 |

预期编译处理链路如下，当前仅作为扩展源码内部设计存在：

```text
Ibis Expression
  -> DTESQLCompiler
  -> SQLGlot AST
  -> DTE SQL Generator
  -> custom optimizer rules
  -> DTE SQL
```

## 2. 扩展分类

扩展分为三类，不能混为同一种能力：

1. **Ibis 核心语法扩展**：改变 Ibis 表达式约束、operation 校验或 compiler visitor 到 SQLGlot AST 的编译语义。
2. **SQLGlot 核心语法扩展**：改变目标 SQL 方言、SQL 文本生成或 AST 优化语义。
3. **周边辅助扩展**：负责串联编译、保存上下文状态和转换异常，本身不定义新的 Ibis/SQLGlot 语法。

所有清单项当前均为 **未接入正式查询链路**。升级风险描述的是未来接入或升级 Ibis/SQLGlot 时必须重点验证的上游兼容点。

## 3. Ibis 核心语法扩展

| 能力组 | 扩展目的与具体行为 | 对应源码符号 | 上游扩展机制 | 当前限制 | 升级风险 |
|---|---|---|---|---|---|
| 表、投影与 Select 编译 | 编译前执行扩展校验；将单独的 `SELECT *` 展开为显式字段；去除投影中的 UTC 毫秒时间转换；无操作 Select 直接返回父查询；禁止 Select 列表中的标量子查询；未绑定表展开为显式字段查询 | `DTESQLCompiler.to_sqlglot`、`visit_UnboundTable`、`visit_Select` | `PostgresCompiler`、Ibis relation operations、SQLGlot Select AST | 标量子查询限制由扩展主动收紧；未验证全部复杂嵌套查询 | `PostgresCompiler.to_sqlglot`、Select visitor 参数及 operation 类型变化 |
| 聚合编译 | `COUNT(DISTINCT *)` 编译为多字段 `ROW` 去重；近似去重退化为普通 distinct count | `visit_CountDistinctStar`、`visit_CountStar`、`visit_ApproxCountDistinct` | Ibis aggregate visitors | 与 Count 别名后处理共同工作，尚未独立验证目标数据源结果 | 聚合 operation 和 aggregate visitor 签名变化 |
| Window 函数 | 将零边界输出为 `CURRENT ROW`；为分析函数补齐排序表达式；对大部分分析函数移除不兼容的 window boundary；保留 First/Last Value 的上游处理 | `visit_WindowBoundary`、`visit_WindowFunction`、`_generate_groups` | Ibis window visitors、SQLGlot Window AST | 行为带有 Spark/DTE 兼容假设，尚未以正式数据源验证 | Ibis window operation 分类、visitor 参数和上游默认边界变化 |
| 比较、空值与布尔语义 | 单列标量子查询的等值比较改写为 `IN`；字段与字面量不等比较包含 `IS NULL`；部分 `NOT` 表达式包含空值分支；时间比较和 `BETWEEN` 可改写为 UTC 毫秒比较 | `visit_Equals`、`visit_NotEquals`、`visit_Not`、`visit_Greater*`、`visit_Less*`、`visit_Between` | Ibis comparison visitors、SQLGlot comparison AST | 多列子查询仍回退到普通等值比较；带时区的 UTC 毫秒时间比较明确不支持 | ScalarSubquery、比较 operation、空值语义和 AST 节点变化 |
| 字符串表达式 | `startswith/endswith` 编译为 `LIKE`，仅支持静态字符串模式；Substring 起始位置从 Ibis 语义转换为 SQL 的一基索引 | `visit_StartsWith`、`visit_EndsWith`、`visit_Substring` | Ibis string visitors | 动态 startswith/endswith 模式主动拒绝 | 字符串 operation 和 visitor 参数变化 |
| UTC 毫秒时间、日期与时间函数 | 将被声明为 timestamp 的 long 字段按 13 位 UTC 毫秒数处理；在比较和时间函数处按需转换，避免在过滤字段上全局包函数；支持日期部件提取、周一周起点、日期构造、时间字面量和投影还原 | `visit_Cast`、`visit_Strftime`、`visit_Extract*`、`visit_DayOfWeek*`、`visit_TimestampTruncate`、`visit_Date`、`visit_TimestampFromYMDHMS`、`visit_DateFromYMD` | Ibis temporal visitors、datatype API、SQLGlot temporal AST | 假设数据库原始值是 UTC 毫秒 long；时区感知 timestamp 不支持相关改写 | Ibis datatype/temporal operation、Cast AST 和上游时间编译语义变化 |
| Ibis 表达式与 operation 校验 | 可安装全局严格比较规则，禁止 Relation 与 Value 直接比较；编译前检测派生表字段泄漏到不可见关系；compiler visitor 中进一步拒绝动态字符串模式、Select 标量子查询和带时区 UTC 毫秒比较 | `apply_syntax_validation_rules`、`strict_comparison`、`compiler_validation.validate`、compiler 中的显式检查 | Ibis expression monkey patch、operation tree 遍历、compiler visitor | `strict_comparison` 会 monkey patch 全局 `Expr.__eq__`；当前未形成隔离机制 | Ibis Expr 比较实现、operation arg 元数据和 relation 可见性模型变化 |

## 4. SQLGlot 核心语法扩展

| 能力组 | 扩展目的与具体行为 | 对应源码符号 | 上游扩展机制 | 当前限制 | 升级风险 |
|---|---|---|---|---|---|
| DTE SQL 方言、函数与类型映射 | 基于 PostgreSQL 方言注册 `dtesql`；关闭单字符串 interval；将 FLOAT/DOUBLE 映射为目标类型；将字符串定位、Substring 和拼接输出为目标 SQL 函数 | `DTESQL`、`DTESQL.Generator`、`DTESQL.Generator.TRANSFORMS`、`TYPE_MAPPING`、`Dialect._classes["dtesql"]` | SQLGlot Dialect、Generator、全局 dialect 注册表 | 使用 SQLGlot 私有全局注册表；尚未验证并发注册和重复导入 | SQLGlot Dialect 注册方式、Generator 常量、类型枚举和 transform API 变化 |
| 紧凑 NOT 语法 | 对 `NOT IN`、`NOT LIKE`、`IS NOT` 生成紧凑操作符形式；对子查询 `NOT IN` 额外保留括号，避免 SQLGlot 将其优化成不兼容的 left join 形式 | `DTESQL.Generator.not_sql`、`in_sql`、`binary` 及 compact-not 辅助逻辑 | SQLGlot Generator 渲染方法和表达式 args | 通过自定义 AST flag 传递状态，依赖 SQLGlot 内部结构 | `Not/In/Like/Is/Binary` 渲染流程及 args 结构变化 |
| `DISTINCT/GROUP BY` 冲突处理 | 当同一 Select 同时存在 distinct 和 group by 时，若当前作用域含聚合则移除 distinct，否则移除 group by；检查时不穿透子查询 | `DTESQL.Generator.select_sql`、聚合作用域检查逻辑 | SQLGlot Select Generator 和 AST 遍历 | 属于目标 SQL 兼容策略，可能改变原始查询表达意图 | Select AST、聚合节点分类和 Generator 渲染顺序变化 |
| `CONNECT BY` 递归语法恢复 | 使用 `__cb__|...` 特殊字段传递 Ibis 无法表达的递归信息；优化阶段识别 `__connect` CTE 并恢复 `START WITH / CONNECT BY NOCYCLE / LEVEL` 查询 | `ConnectBySchema`、`make_up_connect_by` | SQLGlot CTE、Connect/Prior AST 和 optimizer rule | 特殊标记格式属于内部协议；缺少连接条件时直接拒绝 | SQLGlot CTE 合并、Connect/Prior AST 和 optimizer 顺序变化 |
| Count 别名 SQL 优化 | Generator 记录 Count 表达式别名，优化阶段统一添加 `_dte_count_` 前缀，并同步修正外层字段和排序引用 | `DTESQL.Generator.alias_sql`、`rename_count_alias` | SQLGlot Generator、AST transform | 依赖编译上下文状态和 Alias/Column/Identifier 的具体 AST 形态 | Generator 调用顺序、AST 节点结构和 transform 行为变化 |

## 5. 周边辅助扩展

| 能力组 | 辅助职责 | 对应源码符号 | 依赖机制 | 当前限制 | 升级风险 |
|---|---|---|---|---|---|
| 编译入口与优化编排 | 将 Ibis 表达式串联到 DTE compiler、SQLGlot Generator 和 optimizer；普通 SQL 使用默认规则并追加 Count 别名规则，递归 SQL 使用受控规则序列 | `ibis_ext.to_sql`、`optimize_sql`、`custom_optimize_rules` | Ibis compiler、SQLGlot `optimizer.optimize/RULES` | `ibis_ext` 当前存在循环依赖，只能视为设计入口 | Ibis compiler 返回类型、SQLGlot 优化规则签名或默认顺序变化 |
| 编译上下文与别名信息 | 每次编译通过 `ContextVar` 隔离状态；当前状态只记录 Count 表达式别名，供 Generator 与优化规则共享 | `compile_sql_state`、`CompileSqlState`、`SqlLineage` | Python `ContextVar` | 当前所谓 lineage 仅包含 Count 别名辅助信息，不是完整数据血缘 | 编译并发模型以及 Generator 与 optimizer 执行顺序变化 |
| 扩展异常与异常转换 | 扩展不支持语法统一抛出 `UnsupportedSyntaxException`；将 SQLGlot 无法解析表引用的错误改写为更明确的未显式连接或物化提示 | `UnsupportedSyntaxException`、`custom_error_message`、`handle_unresolved_table` | Python exception、SQLGlot `OptimizeError` 消息 | 通过正则匹配上游英文错误文本，较脆弱 | SQLGlot 错误消息格式和异常层级变化 |

## 6. 源码分区

| 分类 | 分区 | 主要职责 |
|---|---|---|
| Ibis 核心语法扩展 | `backends/sql/compilers/compiler.py` | `PostgresCompiler` visitor 覆写与 DTE SQL 编译行为 |
| Ibis 核心语法扩展 | `backends/sql/compilers/compiler_validation.py` | 编译前 operation tree 校验 |
| Ibis 核心语法扩展 | `apis/syntax_validation.py` | 可安装的 Ibis 表达式级严格语法规则 |
| SQLGlot 核心语法扩展 | `backends/sql/sqlglot/dtesql.py` | DTE SQLGlot 方言和 Generator 扩展 |
| SQLGlot 核心语法扩展 | `backends/sql/sqlglot/custom_optimize_rules.py` | `CONNECT BY` 恢复和 Count 别名优化 |
| 周边辅助扩展 | `ibis_ext.py` | 编译入口、编译状态初始化、优化规则选择和优化异常转换 |
| 周边辅助扩展 | `state.py` | 单次编译上下文状态 |
| 周边辅助扩展 | `exceptions.py` | 扩展语法异常 |

## 7. 接入与升级要求

正式接入前必须完成：

1. 消除 `ibis_ext`、DTE 方言和优化规则间的循环依赖。
2. 为清单中的每个能力组补充行为测试和代表性 SQL 快照。
3. 验证生成 SQL 与 OneQuery/DTE SQL 的真实执行结果。
4. 明确全局方言注册和 `Expr.__eq__` monkey patch 的初始化、隔离与销毁策略。
5. 证明官方 Ibis 查询链路与扩展链路能够独立运行。
6. 分别为 Ibis 核心语法扩展、SQLGlot 核心语法扩展和周边辅助扩展建立独立测试集，避免辅助设施测试掩盖语法兼容问题。

升级 Ibis 或 SQLGlot 时，必须逐项复核本清单中的“上游扩展机制”和“升级风险”，不能只以包安装成功作为兼容结论。
