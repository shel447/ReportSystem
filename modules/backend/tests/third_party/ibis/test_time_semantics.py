from __future__ import annotations

import re

import ibis
import pytest

from src._third_party.ibis.ibis_ext import to_sql


def _time_table():
    source = ibis.table(
        {
            "event_time_long": "int64",
            "event_hour": "int64",
            "event_date_text": "string",
            "reference_time": "timestamp",
            "range_start": "timestamp",
            "range_end": "timestamp",
        },
        name="events",
    )
    return source.mutate(event_time=source.event_time_long.cast("timestamp"))


def _sql(expression) -> str:
    return re.sub(r"\s+", " ", str(to_sql(expression, pretty=False))).strip()


def _assert_filter(table, predicate, left_sql: str) -> str:
    assert predicate.type().is_boolean()
    sql = _sql(table.filter(predicate))
    assert " WHERE " in sql
    assert left_sql in sql
    return sql


@pytest.mark.xfail(
    strict=True,
    reason="UTC-millis comparison against a string scalar currently computes the left field",
)
def test_time_string_literal():
    table = _time_table()

    sql = _assert_filter(
        table,
        table.event_time >= "2026-06-13 10:20:30",
        '"events"."event_time_long" >=',
    )

    assert 'UNIX_TIMESTAMP(\'2026-06-13 10:20:30\') * 1000' in sql


def test_truncate_date():
    table = _time_table()
    operand = ibis.timestamp("2026-06-13 10:20:30").date()

    sql = _assert_filter(table, table.event_time >= operand, '"events"."event_time_long" >=')

    assert "UNIX_TIMESTAMP(CAST('2026-06-13 10:20:30' AS TIMESTAMP)) * 1000" in sql


def test_truncate_week():
    table = _time_table()
    operand = ibis.timestamp("2026-06-13 10:20:30").truncate("W")

    sql = _assert_filter(table, table.event_time >= operand, '"events"."event_time_long" >=')

    assert "UNIX_TIMESTAMP(CAST('2026-06-09 10:20:30' AS TIMESTAMP)) * 1000" in sql


def test_extract_hour():
    table = _time_table()
    operand = ibis.timestamp("2026-06-13 10:20:30").hour()

    sql = _assert_filter(table, table.event_hour >= operand, '"events"."event_hour" >=')

    assert "EXTRACT(HOUR FROM CAST('2026-06-13 10:20:30' AS TIMESTAMP))" in sql


def test_time_to_string():
    table = _time_table()
    operand = ibis.timestamp("2026-06-13 10:20:30").strftime("%Y-%m-%d")

    sql = _assert_filter(table, table.event_date_text >= operand, '"events"."event_date_text" >=')

    assert "TO_CHAR('2026-06-13 10:20:30', 'YYYY-MM-DD')" in sql


def test_time_between():
    table = _time_table()

    sql = _assert_filter(
        table,
        table.event_time.between(
            ibis.timestamp("2026-06-01"),
            ibis.timestamp("2026-06-30"),
        ),
        '"events"."event_time_long" <=',
    )

    assert '"events"."event_time_long" >= UNIX_TIMESTAMP(\'2026-06-01 00:00:00\') * 1000' in sql
    assert '"events"."event_time_long" <= UNIX_TIMESTAMP(\'2026-06-30 00:00:00\') * 1000' in sql


def test_date_from_parts():
    table = _time_table()
    operand = ibis.date(2026, 6, 13)

    sql = _assert_filter(table, table.event_time >= operand, '"events"."event_time_long" >=')

    assert "UNIX_TIMESTAMP('2026-06-13') * 1000" in sql


def test_timestamp_from_parts():
    table = _time_table()
    operand = ibis.timestamp(2026, 6, 13, 10, 20, 30)

    sql = _assert_filter(table, table.event_time >= operand, '"events"."event_time_long" >=')

    assert "UNIX_TIMESTAMP('2026-06-13 10:20:30') * 1000" in sql


def test_time_string_literal_of_datetime_column():
    table = _time_table()

    sql = _assert_filter(
        table,
        table.reference_time >= "2026-06-13 10:20:30",
        '"events"."reference_time" >=',
    )

    assert "'2026-06-13 10:20:30'" in sql


def test_truncate_date_of_datetime_column():
    table = _time_table()
    operand = table.reference_time.date()

    sql = _assert_filter(table, table.event_time >= operand, '"events"."event_time_long" >=')

    assert 'UNIX_TIMESTAMP(DATE_TRUNC(\'DAY\', "events"."reference_time")) * 1000' in sql


def test_truncate_week_of_datetime_column():
    table = _time_table()
    operand = table.reference_time.truncate("W")

    sql = _assert_filter(table, table.event_time >= operand, '"events"."event_time_long" >=')

    assert (
        'UNIX_TIMESTAMP(DATE_TRUNC(\'WEEK\', "events"."reference_time" - INTERVAL \'1\' DAY) '
        "+ INTERVAL '1' DAY) * 1000"
    ) in sql


def test_extract_hour_of_datetime_column():
    table = _time_table()
    operand = table.reference_time.hour()

    sql = _assert_filter(table, table.event_hour >= operand, '"events"."event_hour" >=')

    assert 'EXTRACT(HOUR FROM CAST("events"."reference_time" AS TIMESTAMP))' in sql


def test_time_to_string_of_datetime_column():
    table = _time_table()
    operand = table.reference_time.strftime("%Y-%m-%d")

    sql = _assert_filter(table, table.event_date_text >= operand, '"events"."event_date_text" >=')

    assert 'TO_CHAR("events"."reference_time", \'YYYY-MM-DD\')' in sql


def test_time_between_of_datetime_column():
    table = _time_table()

    sql = _assert_filter(
        table,
        table.event_time.between(table.range_start, table.range_end),
        '"events"."event_time_long" <=',
    )

    assert '"events"."event_time_long" >= UNIX_TIMESTAMP("events"."range_start") * 1000' in sql
    assert '"events"."event_time_long" <= UNIX_TIMESTAMP("events"."range_end") * 1000' in sql


@pytest.mark.xfail(
    strict=True,
    reason="Dynamic date parts currently require compiler string-concatenation helpers",
)
def test_date_from_parts_of_datetime_column():
    table = _time_table()
    operand = ibis.date(
        table.reference_time.year(),
        table.reference_time.month(),
        table.reference_time.day(),
    )

    sql = _assert_filter(table, table.event_time >= operand, '"events"."event_time_long" >=')

    assert "UNIX_TIMESTAMP(" in sql


@pytest.mark.xfail(
    strict=True,
    reason="Dynamic timestamp parts currently require compiler string-concatenation helpers",
)
def test_timestamp_from_parts_of_datetime_column():
    table = _time_table()
    operand = ibis.timestamp(
        table.reference_time.year(),
        table.reference_time.month(),
        table.reference_time.day(),
        table.reference_time.hour(),
        table.reference_time.minute(),
        table.reference_time.second(),
    )

    sql = _assert_filter(table, table.event_time >= operand, '"events"."event_time_long" >=')

    assert "UNIX_TIMESTAMP(" in sql


def test_datetime_comparison():
    table = _time_table()

    sql = _assert_filter(
        table,
        table.event_time >= table.reference_time,
        '"events"."event_time_long" >=',
    )

    assert 'UNIX_TIMESTAMP("events"."reference_time") * 1000' in sql
