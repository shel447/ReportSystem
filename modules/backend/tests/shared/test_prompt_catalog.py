from __future__ import annotations

from pathlib import Path

import pytest

from src.infrastructure.prompts import REQUIRED_PROMPTS, initialize_prompt_catalog
from src.shared.prompts import PromptCatalog, PromptEntry


def test_backend_prompt_assets_load_with_required_keys_and_variables():
    catalog = initialize_prompt_catalog()

    assert set(REQUIRED_PROMPTS).issubset(catalog.names())
    for name, variables in REQUIRED_PROMPTS.items():
        assert set(catalog.require(name).variables) == set(variables)


def test_prompt_catalog_is_read_only_and_rejects_missing_variables():
    catalog = PromptCatalog({
        "sample": PromptEntry(
            name="sample",
            description="sample",
            template="hello {name}",
            variables=frozenset({"name"}),
        )
    })

    assert catalog.render("sample", name="ChatBI") == "hello ChatBI"
    with pytest.raises(ValueError, match="Missing prompt variables"):
        catalog.render("sample")


def test_active_application_services_do_not_keep_the_replaced_inline_prompts():
    source_root = Path(__file__).resolve().parents[2] / "src" / "contexts"
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            source_root / "report" / "application" / "parameter_service.py",
            source_root / "data_analysis" / "application" / "services.py",
        )
    )

    assert "把用户问题转换为 JSON，只返回 sql 和 intent_function" not in sources
    assert "根据查询结果给出简洁中文结论" not in sources


def test_prompt_assets_preserve_detailed_business_rules():
    catalog = initialize_prompt_catalog()

    batch_extract = catalog.require("report_parameter.parameter_batch_extract_prompt").template
    single_request = catalog.require("report_parameter.parameter_request_prompt").template
    extract_rule = catalog.require("report_parameter.extract_rule").template
    figure_any = catalog.require("figure.any").template
    column_order = catalog.require("figure.column_order_system").template
    summary = catalog.require("figure.summary_system").template
    rename_column = catalog.require("figure.rename_column_system").template

    assert "如果某个参数无法从问题中提取，不要包含在输出中" in batch_extract
    assert "问题不要太死板，多变一点" in single_request
    assert "如果没有待选值，不要举例说明" in single_request
    assert "用户回答不包含时间时，严禁使用系统当前时间" in extract_rule

    assert "当数值字段个数>=2时" in figure_any
    assert "多实体判断规则" in figure_any
    assert 'like "%a%"' in figure_any
    assert "type: Table | Text | Chart" in figure_any

    assert "保留主体标识字段靠前" in column_order
    assert "displayPriority为never" in column_order
    assert "场景1" in column_order and "场景2" in column_order

    assert "筛选范围、统计口径、排序方式和结果含义" in summary
    assert "禁止**在sql解释中体现该字段" in summary
    assert "**生成summaries**" in summary
    assert "聚合函数列需要体现计算含义" in rename_column
    assert "price*quantity" in rename_column
