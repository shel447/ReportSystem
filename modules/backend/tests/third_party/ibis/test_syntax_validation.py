from __future__ import annotations

import ibis
import pytest
from ibis.expr.types.core import Expr

from src._third_party.ibis.apis.syntax_validation import strict_comparison
from src._third_party.ibis.exceptions import UnsupportedSyntaxException


@pytest.fixture
def strict_comparison_rule():
    original_eq = Expr.__eq__
    strict_comparison()
    try:
        yield
    finally:
        Expr.__eq__ = original_eq


def test_table_and_column_comparison_is_rejected(strict_comparison_rule):
    table = ibis.table({"id": "int64"}, name="devices")

    with pytest.raises(
        UnsupportedSyntaxException,
        match="Comparison between 'Relation' and 'Value' is not supported",
    ):
        table == table.id

    with pytest.raises(
        UnsupportedSyntaxException,
        match="Comparison between 'Relation' and 'Value' is not supported",
    ):
        table.id == table
