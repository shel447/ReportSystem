from __future__ import annotations

from datetime import date as pydate
from datetime import datetime as pydatetime
from decimal import Decimal

from functools import partial

from ibis.backends.sql.compilers import PostgresCompiler
from ibis.backends.sql.compilers.base import NULL, STAR
from ibis.backends.sql.rewrites import (
    FirstValue,
    LastValue,
)
import ibis.expr.datatypes as dt
import ibis.expr.operations as ops
import ibis.expr.schema as sch
from ibis.expr.datatypes.core import Temporal
from ibis.expr.operations.generic import Cast
from ibis.expr.operations.relations import Field
from ibis.expr.operations.subqueries import ScalarSubquery


from sqlglot import exp
import sqlglot as sg
import sqlglot.expressions as sge

from ..sqlglot.dtesql import DTESQL
from ....exceptions import UnsupportedSyntaxException
from . import compiler_validation

TIMEZONE_AWARE_EPOCH_MILLIS_ERROR = (
    "DSQL does not support timezone-aware timestamp fields in epoch-millis comparisons"
)


def _is_epoch_millis_timestamp_cast(op: ops.Node) -> bool:
    return (
        isinstance(op, ops.Cast)
        and op.arg.dtype.is_integer()
        and op.to.is_timestamp()
    )


def _epoch_millis_source_op(
    op: ops.Node, *, _seen: set[ops.Node] | None = None
) -> ops.Node | None:
    if _is_epoch_millis_timestamp_cast(op):
        return op.arg

    if not isinstance(op, ops.Field):
        return None

    if _seen is None:
        _seen = set()
    if op in _seen:
        return None
    _seen.add(op)

    values = getattr(op.rel, "values", None)
    if values is None or op.name not in values:
        return None

    value = values[op.name]
    if value is op:
        return None

    return _epoch_millis_source_op(value, _seen=_seen)


def _is_temporal_dtype(dtype) -> bool:
    return dtype.is_timestamp() or dtype.is_date()


def _timestamp_timezone(dtype) -> str | None:
    if not dtype.is_timestamp():
        return None
    return getattr(dtype, "timezone", None)


def _is_timezone_aware_timestamp_dtype(dtype) -> bool:
    return dtype.is_timestamp() and _timestamp_timezone(dtype) is not None


def _is_sql_int_literal(expression: sge.Expression, value: int) -> bool:
    return (
        isinstance(expression, sge.Literal)
        and not expression.is_string
        and str(expression.this) == str(value)
    )


def _is_anonymous_function(expression: sge.Expression, name: str) -> bool:
    return (
        isinstance(expression, sge.Anonymous)
        and expression.name.upper() == name.upper()
    )

class DTESQLCompiler(PostgresCompiler):
    __slots__ = ()

    dialect = DTESQL

    def to_sqlglot(self, expr, *, limit=None, params=None):
        compiler_validation.validate(expr.as_table().op())
        sql = super().to_sqlglot(expr, limit=limit, params=params)

        if isinstance(sql, sge.Select):
            expressions = sql.args.get("expressions") or []
            if len(expressions) == 1 and isinstance(expressions[0], sge.Star):
                sql.set(
                    "expressions",
                    self._star_fields(expr.as_table().schema().names, sql),
                )
            for select in sql.find_all(sge.Select):
                select.set(
                    "expressions",
                    [self._rewrite_epoch_millis_projection(expr) for expr in select.expressions],
                )

        return sql

    def visit_CountDistinctStar(self, op, *, where, arg):
        # use a tuple because postgres doesn't accept COUNT(DISTINCT a, b, c, ...)
        # this turns the expression into COUNT(DISTINCT ROW(a, b, c, ...))
        row = sge.Tuple(expressions=list(map(partial(sg.column, quoted=self.quoted), op.arg.schema.keys())))
        return self.agg.count(sge.Distinct(expressions=[row]), where=where)

    def visit_CountStar(self, op, *, arg, where):
        return self.agg.count(STAR, where=where)

    def visit_ApproxCountDistinct(self, op, *, arg, where):
        return self.agg.count(sge.Distinct(expressions=[arg]), where=where)

    def visit_WindowBoundary(self, op, *, value, preceding):
        if isinstance(op.value, ops.Literal) and op.value.value == 0:
            value = "CURRENT ROW"
            side = None
        else:
            side = "PRECEDING" if preceding else "FOLLOWING"
        return {"value": value, "side": side}

    def visit_WindowFunction(self, op, *, func, group_by, order_by, **kwargs):
        if isinstance(op.func, ops.Analytic) and not isinstance(op.func, (FirstValue, LastValue)):
            # spark disallows specifying boundaries for most window functions
            if order_by:
                order = sge.Order(expressions=order_by)
            else:
                # pyspark requires an order by clause for most window functions
                order = sge.Order(expressions=[NULL])
            return sge.Window(this=func, partition_by=group_by, order=order)
        else:
            if order_by:
                order = sge.Order(expressions=order_by)
            else:
                # pyspark requires an order by clause for most window functions
                order = sge.Order(expressions=[op.func.arg])
            return super().visit_WindowFunction(op, func=func, group_by=group_by, order_by=order, **kwargs)

    @staticmethod
    def _generate_groups(groups):
        return groups

    def visit_StartsWith(self, op, *, arg, start):
        if not isinstance(start, sge.Literal) or not start.is_string:
            raise UnsupportedSyntaxException("Does not support dynamic startswith patterns")

        like_expr = f"{start.name}%"
        return arg.like(like_expr)

    def visit_EndsWith(self, op, *, arg, end):
        if not isinstance(end, sge.Literal) or not end.is_string:
            raise UnsupportedSyntaxException("Does not support dynamic endswith patterns")

        like_expr = f"%{end.name}"
        return arg.like(like_expr)

    def visit_Equals(self, op: ops.Equals, *, left, right):
        # 检查右操作数是否是一个 Ibis Table (代表子查询)
        is_subquery = isinstance(op.right, ScalarSubquery)
        if is_subquery:
            # 关键检查：获取子查询的 schema，并判断其列数是否为 1
            num_columns = len(op.right.rel.schema.names)

            if num_columns == 1:
                # 如果子查询只有一列，则将其翻译为 IN 子句
                right_expr = right.this if isinstance(right, sge.Subquery) else right
                return sge.In(this=left, expressions=[right_expr])
            else:
                # 如果子查询有多列，回退到原始的 `=` 行为。
                # 这生成的 SQL 在数据库层面很可能会报错，但这是对 `Equals` 操作的忠实翻译。
                # 避免了生成一个语法上就错误的 IN 语句。
                return sge.EQ(this=left, expression=right)

        return sge.EQ(this=left, expression=right)

    def visit_NotEquals(self, op: ops.NotEquals, *, left, right):
        is_left_column_right_literal = isinstance(left, exp.Column) and isinstance(right, exp.Literal)
        is_left_literal_right_column = isinstance(left, exp.Literal) and isinstance(right, exp.Column)
        if is_left_column_right_literal or is_left_literal_right_column:
            column = left if isinstance(left, exp.Column) else right
            return sge.Or(
                this=sge.NEQ(this=left, expression=right),
                expression=sge.Is(this=column, expression=sge.Null()),
            )
        return sge.NEQ(this=left, expression=right)

    def visit_Not(self, op, *, arg):
        if isinstance(arg, sge.Filter):
            return sge.Filter(this=sg.not_(arg.this, copy=False), expression=arg.expression)

        if isinstance(arg.this, exp.Column):
            return sge.Or(
                this=sg.not_(sge.paren(arg, copy=False)), expression=sge.Is(this=arg.this, expression=sge.Null())
            )
        return sg.not_(sge.paren(arg, copy=False))

    def visit_Greater(self, op, *, left, right):
        return self._rewrite_temporal_binop(op, sge.GT, left, right)

    def visit_GreaterEqual(self, op, *, left, right):
        return self._rewrite_temporal_binop(op, sge.GTE, left, right)

    def visit_Less(self, op, *, left, right):
        return self._rewrite_temporal_binop(op, sge.LT, left, right)

    def visit_LessEqual(self, op, *, left, right):
        return self._rewrite_temporal_binop(op, sge.LTE, left, right)

    def visit_Between(self, op, *, arg, lower_bound, upper_bound):
        if not (
                _epoch_millis_source_op(op.arg) is not None
                and _is_temporal_dtype(op.arg.dtype)
                and _is_temporal_dtype(op.lower_bound.dtype)
                and _is_temporal_dtype(op.upper_bound.dtype)
        ):
            return super().visit_Between(op, arg=arg, lower_bound=lower_bound, upper_bound=upper_bound)

        self._ensure_supported_epoch_millis_temporal_operands(
            op.arg,
            op.lower_bound,
            op.upper_bound,
        )

        return sge.Between(
            this=self._operand_to_epoch_millis(op.arg, arg),
            low=self._operand_to_epoch_millis(op.lower_bound, lower_bound),
            high=self._operand_to_epoch_millis(op.upper_bound, upper_bound),
        )

    def _star_fields(self, names, relation):
        table = getattr(relation, "alias_or_name", None)

        if not table and isinstance(relation, sge.Select):
            source = relation.args.get("from_")
            source = None if source is None else source.this
            table = getattr(source, "alias_or_name", None)

        return [sg.column(name, table=table or None, quoted=self.quoted, copy=False) for name in names]

    def timestamp_to_milliseconds(self, timestamp_expr):
        return sge.Mul(
            this=sge.Anonymous(this="unix_timestamp", expressions=[timestamp_expr]),
            expression=exp.Literal.number(1000),
        )

    def _all_timestamp_type(self, op):
        return isinstance(op.left.dtype, Temporal) and isinstance(op.right.dtype, Temporal)

    def _is_timestamp_column(self, column):
        # 识别时间字段。注意是最原始的时间字段，而不是经过变换后的时间表达式
        return isinstance(column, Field) or isinstance(column, Cast) and isinstance(column.arg, Field)

    def visit_ExtractWeekOfYear(self, op, *, arg):
        real_timestamp = self._millis_to_timestamp(op, arg)
        return self.f.extract("week", real_timestamp)

    def visit_DayOfWeekIndex(self, op, *, arg):
        real_timestamp = self._millis_to_timestamp(op, arg)
        return self.cast(self.f.extract("dow", real_timestamp) + 6, dt.int16) % 7

    def visit_DayOfWeekName(self, op, *, arg):
        import string

        real_timestamp = self._millis_to_timestamp(op, arg)
        return self.f.trim(self.f.to_char(real_timestamp, "Day"), string.whitespace)

    def visit_Strftime(self, op, *, arg, format_str):
        arg = self._restore_epoch_millis_timestamp(op.arg, arg)
        return super().visit_Strftime(op, arg=arg, format_str=format_str)

    def visit_ExtractEpochSeconds(self, op, *, arg):
        arg = self._restore_epoch_millis_timestamp(op.arg, arg)
        return super().visit_ExtractEpochSeconds(op, arg=arg)

    def visit_ExtractYear(self, op, *, arg):
        arg = self._restore_epoch_millis_timestamp(op.arg, arg)
        return super().visit_ExtractYear(op, arg=arg)

    def visit_ExtractMonth(self, op, *, arg):
        arg = self._restore_epoch_millis_timestamp(op.arg, arg)
        return super().visit_ExtractMonth(op, arg=arg)

    def visit_ExtractDay(self, op, *, arg):
        arg = self._restore_epoch_millis_timestamp(op.arg, arg)
        return super().visit_ExtractDay(op, arg=arg)

    def visit_ExtractHour(self, op, *, arg):
        arg = self._restore_epoch_millis_timestamp(op.arg, arg)
        return super().visit_ExtractHour(op, arg=arg)

    def visit_ExtractMinute(self, op, *, arg):
        arg = self._restore_epoch_millis_timestamp(op.arg, arg)
        return super().visit_ExtractMinute(op, arg=arg)

    def visit_ExtractSecond(self, op, *, arg):
        arg = self._restore_epoch_millis_timestamp(op.arg, arg)
        return super().visit_ExtractSecond(op, arg=arg)

    def visit_TimestampTruncate(self, op, *, arg, unit):
        arg = self._restore_epoch_millis_timestamp(op.arg, arg)
        if unit.short == "W":
            return self._monday_week_start(arg)
        return super().visit_TimestampTruncate(op, arg=arg, unit=unit)

    def visit_UnboundTable(self, op, *, name: str, schema: sch.Schema, namespace: ops.Namespace) -> sg.Table:
        table_ref = sg.table(name, db=namespace.database, catalog=namespace.catalog, quoted=self.quoted)

        fields = [sg.column(col_name, quoted=self.quoted) for col_name in schema.names]
        return sg.select(*fields).from_(table_ref)

    def visit_Cast(self, op, *, arg, to):
        """
        不要在全局去把long cast timestamp，后续在使用的地方在逐个去转换。虽然这样的适配成本很高~~
        原因是过滤条件中，如果时间字段被函数包裹时，onequery无法路由到物理表

        约束：
        本函数运行成功和结果正确需遵循两个约束：timestamp字段实际数据库类型是long、该long值等于13位的utc毫秒数
        """

        from_ = op.arg.dtype
        if isinstance(from_, exp.Literal) and (to.is_timestamp() or to.is_date()):
            return arg

        if _is_epoch_millis_timestamp_cast(op):
            return self._epoch_millis_to_timestamp(arg, to)

        if op.arg.dtype.is_timestamp() and (to.is_date() or to.is_time()):
            arg = self._restore_epoch_millis_timestamp(op.arg, arg)

        return super().visit_Cast(op, arg=arg, to=to)

    def visit_Select(self, op, *, parent, selections, predicates, qualified, sort_keys, distinct):
        if selections and any(isinstance(selection, exp.Subquery) for selection in selections.values()):
            raise UnsupportedSyntaxException("Scalar subqueries in the SELECT clause are not supported.")

        if not (selections or predicates or qualified or sort_keys or distinct):
            return parent

        result = parent

        if selections:
            if op.is_star_selection():
                fields = self._star_fields(op.schema.names, parent)
            else:
                fields = self._cleanup_names(selections)
            result = sg.select(*fields, copy=False).from_(result, copy=False)

        if predicates:
            result = result.where(*predicates, copy=False)

        if qualified:
            result = result.qualify(*qualified, copy=False)

        if sort_keys:
            result = result.order_by(*sort_keys, copy=False)

        if distinct:
            result = result.distinct()

        return result

    def visit_Substring(self, op, *, arg, start, length):
        start += 1
        if length is None:
            return self.f.substring(arg, start)
        return self.f.substring(arg, start, length)

    def visit_DefaultLiteral(self, op, *, value, dtype):
        if dtype.is_date():
            return self._string_literal(value.isoformat())
        if dtype.is_timestamp():
            return self._string_literal(self._format_temporal_literal(value, is_timestamp=True))
        if dtype.is_time():
            return self.cast(self._format_temporal_literal(value, is_timestamp=False), dtype)
        return super().visit_DefaultLiteral(op, value=value, dtype=dtype)

    def visit_Date(self, op, *, arg):
        arg = self._restore_epoch_millis_timestamp(op.arg, arg)
        return self.f.date_trunc("day", arg)

    def _millis_to_timestamp(self, op, arg):
        """
        把long类型的utc毫秒数转换为timestamp

        example:
            CAST(FROM_UNIXTIME(CAST("alarmrecord"."occurUtc" AS DOUBLE) / 1000) AS TIMESTAMP)
        """

        if self._is_timestamp_column(op.arg):
            ts_seconds = exp.Div(this=arg, expression=exp.Literal.number(1000))
            unixtime_str = exp.Anonymous(this="from_unixtime", expressions=[ts_seconds])
            return exp.cast(unixtime_str, to=exp.DataType(this=exp.DataType.Type.TIMESTAMP))

        return arg

    def visit_TimestampFromYMDHMS(self, op, *, year, month, day, hours, minutes, seconds):
        if all(isinstance(node, ops.Literal) for node in (op.year, op.month, op.day, op.hours, op.minutes, op.seconds)):
            second_int, microseconds = self._coerce_timestamp_parts(self._literal_node_value(op.seconds))
            literal_timestamp = pydatetime(
                int(self._literal_node_value(op.year)),
                int(self._literal_node_value(op.month)),
                int(self._literal_node_value(op.day)),
                int(self._literal_node_value(op.hours)),
                int(self._literal_node_value(op.minutes)),
                second_int,
                microseconds,
            )
            return self._string_literal(
                self._format_temporal_literal(literal_timestamp, is_timestamp=True),
            )

        timestamp_text = self._concat_sql(
            self._stringify_sql(year),
            sge.Literal.string("-"),
            self._zero_pad_sql_part(month, 2),
            sge.Literal.string("-"),
            self._zero_pad_sql_part(day, 2),
            sge.Literal.string(" "),
            self._zero_pad_sql_part(hours, 2),
            sge.Literal.string(":"),
            self._zero_pad_sql_part(minutes, 2),
            sge.Literal.string(":"),
            self._timestamp_second_sql_part(op.seconds, seconds),
        )
        return self.cast(timestamp_text, dt.timestamp)

    def visit_DateFromYMD(self, op, *, year, month, day):
        if all(isinstance(node, ops.Literal) for node in (op.year, op.month, op.day)):
            literal_date = pydate(
                int(self._literal_node_value(op.year)),
                int(self._literal_node_value(op.month)),
                int(self._literal_node_value(op.day)),
            )
            return self._string_literal(literal_date.isoformat())

        date_text = self._concat_sql(
            self._stringify_sql(year),
            sge.Literal.string("-"),
            self._zero_pad_sql_part(month, 2),
            sge.Literal.string("-"),
            self._zero_pad_sql_part(day, 2),
        )
        return self.cast(date_text, dt.date)

    def _epoch_millis_to_timestamp(self, arg: sge.Expression, to) -> sge.Expression:
        seconds = self.binop(sge.Div, arg, sge.convert(1000))
        return self.cast(sg.func("FROM_UNIXTIME", seconds), to)

    @staticmethod
    def _literal_node_value(node: ops.Node):
        return node.value if isinstance(node, ops.Literal) else None

    @staticmethod
    def _coerce_timestamp_parts(second_value) -> tuple[int, int]:
        second_decimal = Decimal(str(second_value))
        second_int = int(second_decimal)
        micros = int((second_decimal - second_int) * Decimal("1000000"))
        if micros >= 1000000:
            second_int += 1
            micros -= 1000000
        return second_int, micros

    @staticmethod
    def _day_interval() -> sge.Interval:
        return sge.Interval(this=sge.Literal.string("1"), unit=sge.Var(this="DAY"))

    def _monday_week_start(self, arg: sge.Expression) -> sge.Expression:
        day_interval = self._day_interval()
        shifted = self.binop(sge.Sub, arg.copy(), day_interval.copy())
        week_start = self.f.date_trunc("week", shifted)
        return self.binop(sge.Add, week_start, day_interval)

    def _timestamp_second_sql_part(self, operand: ops.Node, expression: sge.Expression) -> sge.Expression:
        if operand.dtype.is_integer():
            return self._zero_pad_sql_part(expression, 2)

        second_text = self._stringify_sql(expression)
        if operand.dtype.is_floating():
            return self.if_(
                self.binop(sge.LT, expression.copy(), sge.convert(10)),
                self._concat_sql(sge.Literal.string("0"), second_text.copy()),
                second_text,
            )

        return second_text

    def _unwrap_epoch_millis_timestamp(self, expression: sge.Expression) -> sge.Expression | None:
        if not isinstance(expression, sge.Cast):
            return None

        to = expression.to
        if not isinstance(to, sge.DataType) or to.this != sge.DataType.Type.TIMESTAMP:
            return None

        inner = expression.this
        if not _is_anonymous_function(inner, "FROM_UNIXTIME") or len(inner.expressions) != 1:
            return None

        division = inner.expressions[0]
        if not isinstance(division, sge.Div) or not _is_sql_int_literal(division.expression, 1000):
            return None

        return division.this.copy()

    def _timestamp_to_epoch_millis(self, expression: sge.Expression) -> sge.Expression:
        raw = self._unwrap_epoch_millis_timestamp(expression)
        if raw is not None:
            return raw

        seconds = sg.func("UNIX_TIMESTAMP", expression.copy())
        return self.binop(sge.Mul, seconds, sge.convert(1000))

    def _operand_to_epoch_millis(self, operand: ops.Node, expression: sge.Expression) -> sge.Expression:
        if _epoch_millis_source_op(operand) is not None:
            raw = self._unwrap_epoch_millis_timestamp(expression)
            return raw if raw is not None else expression.copy()

        return self._timestamp_to_epoch_millis(expression)

    def _restore_epoch_millis_timestamp(self, operand: ops.Node, expression: sge.Expression) -> sge.Expression:
        if _epoch_millis_source_op(operand) is None:
            return expression

        if self._unwrap_epoch_millis_timestamp(expression) is not None:
            return expression

        return self._epoch_millis_to_timestamp(expression.copy(), operand.dtype)

    @staticmethod
    def _format_temporal_literal(value, *, is_timestamp: bool) -> str:
        timespec = "microseconds" if getattr(value, "microsecond", 0) else "seconds"
        if is_timestamp:
            return value.isoformat(sep=" ", timespec=timespec)
        return value.isoformat(timespec=timespec)

    @staticmethod
    def _string_literal(value: str) -> sge.Literal:
        return sge.Literal.string(value)

    def _rewrite_epoch_millis_projection(self, expression: sge.Expression) -> sge.Expression:
        if isinstance(expression, sge.Alias):
            raw = self._unwrap_epoch_millis_timestamp(expression.this)
            if raw is None:
                return expression

            rewritten = expression.copy()
            rewritten.set("this", raw)
            return rewritten

        raw = self._unwrap_epoch_millis_timestamp(expression)
        return raw if raw is not None else expression

    def _ensure_supported_epoch_millis_temporal_operands(self, *operands: ops.Node) -> None:
        if any(_is_timezone_aware_timestamp_dtype(operand.dtype) for operand in operands):
            raise UnsupportedSyntaxException(TIMEZONE_AWARE_EPOCH_MILLIS_ERROR)

    def _should_rewrite_temporal_comparison(self, left_op: ops.Node, right_op: ops.Node) -> bool:
        if not (
                (_epoch_millis_source_op(left_op) is not None or _epoch_millis_source_op(right_op) is not None)
                and _is_temporal_dtype(left_op.dtype)
                and _is_temporal_dtype(right_op.dtype)
        ):
            return False

        self._ensure_supported_epoch_millis_temporal_operands(left_op, right_op)
        return True

    def _rewrite_temporal_binop(self, op, sg_cls, left, right):
        if not self._should_rewrite_temporal_comparison(op.left, op.right):
            return self.binop(sg_cls, left, right)

        return sg_cls(
            this=self._operand_to_epoch_millis(op.left, left),
            expression=self._operand_to_epoch_millis(op.right, right),
        )
