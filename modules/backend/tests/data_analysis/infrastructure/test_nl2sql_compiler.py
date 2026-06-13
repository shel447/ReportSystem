from __future__ import annotations

import pytest

from src.contexts.data_analysis.domain.models import Nl2SqlCompileError, Nl2SqlContext
from src.contexts.data_analysis.infrastructure.contextvar import current_fk_whitelist, current_table_config
from src.contexts.data_analysis.infrastructure.nl2sql_compiler import RestrictedIbisNl2SqlCompiler


def _context() -> Nl2SqlContext:
    return Nl2SqlContext(
        question="查询设备健康评分",
        entities=(
            {
                "name": "network_health",
                "fields": [
                    {"name": "device_name", "type": "string"},
                    {"name": "health_score", "type": "double"},
                ],
            },
        ),
    )


def test_compiler_executes_restricted_query_and_compiles_dte_sql():
    sql = RestrictedIbisNl2SqlCompiler().compile(
        source=(
            "def query(config: QueryConfig) -> Expr:\n"
            "    result = config.network_health.filter(config.network_health.health_score < 90)\n"
            "    return result.select('device_name', 'health_score')\n"
        ),
        context=_context(),
    )

    assert 'FROM "network_health"' in sql
    assert '"health_score" < 90' in sql


@pytest.mark.parametrize(
    "source",
    [
        "import os\ndef query(config):\n    return config.network_health",
        "def query(config):\n    return open('/tmp/x')",
        "def query(config):\n    return config.__class__",
        "def query(config):\n    while True:\n        pass",
        "def other(config):\n    return config.network_health",
    ],
)
def test_compiler_rejects_unsafe_or_invalid_generated_source(source):
    with pytest.raises(Nl2SqlCompileError):
        RestrictedIbisNl2SqlCompiler().compile(source=source, context=_context())


def test_compiler_rejects_unselected_logical_entity():
    with pytest.raises(Nl2SqlCompileError, match="Logical entity is not available"):
        RestrictedIbisNl2SqlCompiler().compile(
            source="def query(config):\n    return config.secret_table",
            context=_context(),
        )


def test_compiler_injects_relation_helpers_and_cleans_execution_context():
    context = Nl2SqlContext(
        question="查询设备指标",
        entities=(
            {"name": "device", "fields": [{"name": "id", "type": "string"}]},
            {
                "name": "device_kpi",
                "fields": [
                    {"name": "device_id", "type": "string"},
                    {"name": "score", "type": "double"},
                ],
            },
        ),
        relations=(
            {
                "source": {"entity": "device", "field": "id"},
                "target": {"entity": "device_kpi", "field": "device_id"},
            },
        ),
    )

    sql = RestrictedIbisNl2SqlCompiler().compile(
        source=(
            "def query(config):\n"
            "    return create_device2kpi_wide_table(config.device, config.device_kpi, [])"
            ".select(config.device.id, config.device_kpi.score)\n"
        ),
        context=context,
    )

    assert "JOIN" in sql
    assert current_fk_whitelist.get() == ()
    assert current_table_config.get() is None
