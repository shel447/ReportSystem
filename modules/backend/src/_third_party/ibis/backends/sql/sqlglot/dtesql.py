from __future__ import annotations

from typing import List, Union

import sqlglot.expressions as exp
from sqlglot import Dialect
from sqlglot.dialects import postgres

from ....state import CompileSqlState, compile_sql_state

def _substring_sql(self: postgres.Postgres.Generator, expression: exp.Substring) -> str:
    this = self.sql(expression, "this")
    start = self.sql(expression, "start")
    length = self.sql(expression, "length")
    return f"SUBSTRING({this}, {start}, {length})"

class DTESQL(postgres.Postgres):
    class Generator(postgres.Postgres.Generator):
        SINGLE_STRING_INTERVAL = False
        TRANSFORMS = {
            **postgres.Postgres.Generator.TRANSFORMS,
            exp.StrPosition: lambda self, e: f"INSTR({self.sql(e, 'this')}, {self.sql(e, 'substr')})",
            exp.Substring: _substring_sql,
            exp.DPipe: lambda self, expression: self.func("CONCAT", expression.this, expression.expression),
        }

        TYPE_MAPPING = {
            **postgres.Postgres.Generator.TYPE_MAPPING,
            exp.DataType.Type.FLOAT: "FLOAT",
            exp.DataType.Type.DOUBLE: "DOUBLE",
        }

        _COMPACT_NOT_FLAG = "_is_compact_not"
        # 操作符前面加NOT。比如：not in、not like
        _PREVIOUS_COMPAT_NOT_OPERATION_SCOPE = (exp.In, exp.Like)
        # 操作符后面加NOT。比如：is not
        _SUBSEQUENT_COMPAT_NOT_OPERATION_SCOPE = (exp.Is,)
        # 所有需要加NOT的操作符
        _COMPAT_NOT_OPERATION_SCOPE = _PREVIOUS_COMPAT_NOT_OPERATION_SCOPE + _SUBSEQUENT_COMPAT_NOT_OPERATION_SCOPE

        def not_sql(self, expression: exp.Not) -> str:
            if isinstance(expression.this, exp.Paren) and isinstance(
                expression.this.this, self._COMPAT_NOT_OPERATION_SCOPE
            ):
                return self._expression_with_compact_not_flag(expression.this)
            elif isinstance(expression.this, self._COMPAT_NOT_OPERATION_SCOPE):
                return self._expression_with_compact_not_flag(expression)

            return super().not_sql(expression)

        def in_sql(self, expression: exp.In) -> str:
            _is_compact_not_in = self._not_identifier(expression)
            if _is_compact_not_in:
                query = expression.args.get("query")
                unnest = expression.args.get("unnest")
                field = expression.args.get("field")
                is_global = " GLOBAL" if expression.args.get("is_global") else ""

                if query:
                    # 额外加一层()，使sqlglot不要把not in改写为left join ... is null的写法，因为当子查询里有DISTINCT时，
                    # onequery会报错，而修改sqlglot优化规则，侵入性强成本较高
                    in_sql = f"({self.sql(query)})"
                elif unnest:
                    in_sql = self.in_unnest_op(unnest)
                elif field:
                    in_sql = self.sql(field)
                else:
                    in_sql = (
                        f"({self.expressions(expression, dynamic=True, new_line=True, skip_first=True,skip_last=True)})"
                    )

                return f"{self.sql(expression, 'this')}{is_global}{_is_compact_not_in} IN {in_sql}"

            return super().in_sql(expression)

        def binary(self, expression: exp.Binary, op: str) -> str:
            sqls: List[str] = []
            stack: List[Union[str, exp.Expression]] = [expression]
            binary_type = type(expression)

            while stack:
                node = stack.pop()

                if isinstance(node, binary_type) and type(node) is binary_type:
                    op_func = node.args.get("operator")
                    if op_func:
                        op = f"OPERATOR({self.sql(op_func)})"

                    stack.append(node.right)
                    stack.append(
                        f" {self.maybe_comment(self._format_op_with_not(expression, op), comments=node.comments)} "
                    )
                    stack.append(node.left)
                else:
                    sqls.append(self.sql(node))

            return "".join(sqls)

        def alias_sql(self, expression: exp.Alias) -> str:
            alias = self.sql(expression, "alias")
            if isinstance(expression.this, exp.Count):
                try:
                    _state: CompileSqlState = compile_sql_state.get()
                    _state.lineage.count_expr_alias.add(self._trim_identifier(alias))
                except LookupError:
                    pass  # standalone usage without Ibis compile context

            return super().alias_sql(expression)

        def _trim_identifier(self, identifier: str):
            return identifier.replace('"', "")

        def _expression_with_compact_not_flag(self, expression):
            new_exp = expression.this.copy()
            new_exp.args.setdefault(self._COMPACT_NOT_FLAG, True)
            return f"{self.sql(new_exp)}"

        def _format_op_with_not(self, expression, op: str):
            if isinstance(expression, self._PREVIOUS_COMPAT_NOT_OPERATION_SCOPE):
                return f"{self._not_identifier(expression)} {op}"
            elif isinstance(expression, self._SUBSEQUENT_COMPAT_NOT_OPERATION_SCOPE):
                return f"{op} {self._not_identifier(expression)}"
            else:
                return op

        def _not_identifier(self, expression):
            return " NOT" if expression.args.get(self._COMPACT_NOT_FLAG) else ""

        # -----------------------------------------------------------------------
        # DISTINCT / GROUP BY conflict resolution
        # -----------------------------------------------------------------------

        @staticmethod
        def _has_agg_in_scope(node: exp.Expression) -> bool:
            """
            递归检查当前节点是否包含聚合函数 (如 COUNT, SUM, MAX 等)。
            【关键】：遇到子查询 (Select, Subquery, Union) 直接停止向下，防止误判。
            """
            if not isinstance(node, exp.Expression):
                return False
            if isinstance(node, exp.AggFunc):
                return True
            if isinstance(node, (exp.Select, exp.Subquery, exp.Union)):
                return False
            for val in node.args.values():
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, exp.Expression) and DTESQL.Generator._has_agg_in_scope(item):
                            return True
                elif isinstance(val, exp.Expression):
                    if DTESQL.Generator._has_agg_in_scope(val):
                        return True
            return False

        def _check_select_has_agg(self, select_node: exp.Select) -> bool:
            """
            检查当前 Select 块的直接作用域内（SELECT, HAVING, ORDER BY）是否有聚合函数。
            """
            for expr in select_node.expressions:
                if self._has_agg_in_scope(expr):
                    return True
            if self._has_agg_in_scope(select_node.args.get("having")):
                return True
            if self._has_agg_in_scope(select_node.args.get("order")):
                return True
            return False

        def select_sql(self, expression: exp.Select, **kwargs) -> str:
            has_distinct = expression.args.get("distinct")
            has_group = expression.args.get("group")
            if has_distinct and has_group:
                has_agg = self._check_select_has_agg(expression)
                original_distinct = expression.args["distinct"]
                original_group = expression.args["group"]
                try:
                    if has_agg:
                        expression.set("distinct", None)
                    else:
                        expression.set("group", None)
                    return super().select_sql(expression, **kwargs)
                finally:
                    if has_agg:
                        expression.set("distinct", original_distinct)
                    else:
                        expression.set("group", original_group)
            return super().select_sql(expression, **kwargs)

Dialect._classes["dtesql"] = DTESQL
