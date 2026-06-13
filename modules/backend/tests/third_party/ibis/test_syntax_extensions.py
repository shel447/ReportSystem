from __future__ import annotations

import re

import ibis
import pytest
from sqlglot import exp

from src._third_party.ibis.backends.sql.sqlglot.dtesql import DTESQL  # noqa: F401
from src._third_party.ibis.exceptions import UnsupportedSyntaxException
from src._third_party.ibis.ibis_ext import to_sql


def _table():
    return ibis.table(
        {
            "id": "int64",
            "name": "string",
            "other_name": "string",
            "event_time": "timestamp",
            "event_time_long": "int64",
        },
        name="devices",
    )


def _sql(expression) -> str:
    return re.sub(r"\s+", " ", str(to_sql(expression, pretty=False))).strip()


def _dialect_sql(expression: exp.Expression) -> str:
    return re.sub(r"\s+", " ", expression.sql(dialect="dtesql")).strip()


def test_is_not_null():
    sql = _dialect_sql(exp.not_(exp.Is(this=exp.column("name"), expression=exp.Null())))

    assert sql == "name IS NOT NULL"


def test_not_in():
    sql = _dialect_sql(exp.not_(exp.column("id").isin(1, 2)))

    assert sql == "id NOT IN (1, 2)"


def test_not_like():
    sql = _dialect_sql(
        exp.not_(
            exp.Like(
                this=exp.column("name"),
                expression=exp.Literal.string("core%"),
            )
        )
    )

    assert sql == "name NOT LIKE 'core%'"


def test_instr():
    table = _table()

    sql = _sql(table.select(table.name.find("core").name("position")))

    assert 'INSTR("devices"."name", \'core\') - 1 AS "position"' in sql


def test_time_interval():
    table = _table()

    sql = _sql(table.select((table.event_time + ibis.interval(days=1)).name("next_day")))

    assert '"event_time" + INTERVAL \'1\' DAY AS "next_day"' in sql


def test_unfold_select_star():
    table = _table()

    sql = _sql(table)

    assert "SELECT *" not in sql
    for column in table.columns:
        assert f'"devices"."{column}" AS "{column}"' in sql


def test_long_2_timestamp_field():
    table = _table().mutate(timestamp_value=lambda value: value.event_time_long.cast("timestamp"))

    sql = _sql(table.select("timestamp_value"))

    assert 'SELECT "devices"."event_time_long" AS "timestamp_value"' in sql
    assert "FROM_UNIXTIME" not in sql


def test_select_subquery_scalar_unsupported():
    table = _table()
    other = ibis.table({"id": "int64"}, name="sites")

    with pytest.raises(
        UnsupportedSyntaxException,
        match="Scalar subqueries in the SELECT clause are not supported",
    ):
        _sql(table.select(other.id.as_scalar().name("site_id")))


def test_rename_alias():
    table = _table()

    sql = _sql(table.select(table.id.name("device_id")))

    assert '"devices"."id" AS "device_id"' in sql


@pytest.mark.xfail(
    strict=True,
    reason="NOT IN subquery is currently optimized into LEFT JOIN ... IS NULL",
)
def test_not_in_subquery():
    table = _table()
    other = ibis.table({"id": "int64"}, name="sites")

    sql = _sql(table.filter(~table.id.isin(other.id)))

    assert '"devices"."id" NOT IN (' in sql
    assert "LEFT JOIN" not in sql


def test_substring():
    table = _table()

    sql = _sql(table.select(table.name.substr(1, 3).name("short_name")))

    assert 'SUBSTRING("devices"."name", 2, 3) AS "short_name"' in sql


def test_logical_not_like():
    table = _table()

    sql = _sql(table.filter(~table.name.like("core%")))

    assert '"name" IS NULL OR "devices"."name" NOT LIKE \'core%\'' in sql


def test_logical_not_equal():
    table = _table()

    sql = _sql(table.filter(~(table.id == 1)))

    assert '"devices"."id" <> 1 OR "devices"."id" IS NULL' in sql


def test_logical_not_in():
    table = _table()

    sql = _sql(table.filter(~table.id.isin([1, 2])))

    assert '"id" IS NULL OR "devices"."id" NOT IN (1, 2)' in sql


@pytest.mark.xfail(
    strict=True,
    reason="Logical NOT NULL currently loses the filter predicate during optimization",
)
def test_logical_not_null():
    table = _table()

    sql = _sql(table.filter(~table.name.isnull()))

    assert " WHERE " in sql
    assert '"name" IS NOT NULL' in sql


def test_to_sql_rewrites_string_concat_to_concat_function():
    table = _table()

    sql = _sql(table.select((table.name + table.other_name).name("display_name")))

    assert 'CONCAT("devices"."name", "devices"."other_name") AS "display_name"' in sql
    assert " || " not in sql


def test_to_sql_rewrites_nested_string_concat_to_nested_concat_function():
    table = _table()

    sql = _sql(table.select((table.name + table.other_name + ibis.literal("!")).name("display_name")))

    assert 'CONCAT(CONCAT("devices"."name", "devices"."other_name"), \'!\') AS "display_name"' in sql
    assert " || " not in sql


def test_to_sql_rewrites_timestamp_string_concat_to_concat_function():
    table = _table()

    sql = _sql(table.select((table.event_time.cast("string") + table.name).name("display_name")))

    assert 'CONCAT(CAST("devices"."event_time" AS VARCHAR), "devices"."name") AS "display_name"' in sql
    assert " || " not in sql


def test_to_sql_rejects_dynamic_startswith_patterns():
    table = _table()

    with pytest.raises(UnsupportedSyntaxException, match="dynamic startswith"):
        _sql(table.filter(table.name.startswith(table.other_name)))


def test_to_sql_rejects_dynamic_endswith_patterns():
    table = _table()

    with pytest.raises(UnsupportedSyntaxException, match="dynamic endswith"):
        _sql(table.filter(table.name.endswith(table.other_name)))
